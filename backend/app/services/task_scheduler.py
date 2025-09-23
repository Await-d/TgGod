"""
任务调度器服务
基于APScheduler实现完整的Cron调度功能
支持多种调度类型：interval、cron、daily、weekly、monthly
包含任务持久化、错过任务处理、任务依赖和优先级支持
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List, Callable
import json
import threading
from concurrent.futures import ThreadPoolExecutor

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.executors.pool import ThreadPoolExecutor as APSThreadPoolExecutor
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, EVENT_JOB_MISSED
from apscheduler.jobstores.base import ConflictingIdError
from apscheduler import events

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, text

from ..models.rule import DownloadTask
from ..database import get_db, engine
from ..utils.db_optimization import optimized_db_session
from ..core.logging_config import get_logger
from ..core.service_locator import service_locator, create_service_proxy

# 使用高性能批处理日志记录器
logger = get_logger(__name__, use_batch=True)


class TaskDependencyManager:
    """任务依赖管理器"""
    
    def __init__(self):
        self.dependencies: Dict[str, List[str]] = {}
        self.completed_tasks: set = set()
        self.failed_tasks: set = set()
        
    def add_dependency(self, task_id: str, depends_on: List[str]):
        """添加任务依赖"""
        self.dependencies[task_id] = depends_on
        
    def can_execute(self, task_id: str) -> bool:
        """检查任务是否可以执行（所有依赖都已完成）"""
        if task_id not in self.dependencies:
            return True
            
        depends_on = self.dependencies[task_id]
        for dep_task in depends_on:
            if dep_task in self.failed_tasks:
                return False
            if dep_task not in self.completed_tasks:
                return False
                
        return True
        
    def mark_completed(self, task_id: str):
        """标记任务完成"""
        self.completed_tasks.add(task_id)
        
    def mark_failed(self, task_id: str):
        """标记任务失败"""
        self.failed_tasks.add(task_id)
        
    def reset_task(self, task_id: str):
        """重置任务状态"""
        self.completed_tasks.discard(task_id)
        self.failed_tasks.discard(task_id)


class TaskPriorityQueue:
    """任务优先级队列"""
    
    def __init__(self):
        self.queue: List[Dict[str, Any]] = []
        self.lock = threading.Lock()
        
    def add_task(self, task_id: str, priority: int = 0, metadata: Optional[Dict] = None):
        """添加任务到队列"""
        with self.lock:
            self.queue.append({
                'task_id': task_id,
                'priority': priority,
                'added_at': datetime.now(timezone.utc),
                'metadata': metadata or {}
            })
            # 按优先级排序（高优先级在前）
            self.queue.sort(key=lambda x: (-x['priority'], x['added_at']))
            
    def get_next_task(self) -> Optional[Dict[str, Any]]:
        """获取下一个待执行任务"""
        with self.lock:
            if self.queue:
                return self.queue.pop(0)
            return None
            
    def remove_task(self, task_id: str):
        """从队列中移除任务"""
        with self.lock:
            self.queue = [task for task in self.queue if task['task_id'] != task_id]
            
    def get_queue_status(self) -> List[Dict[str, Any]]:
        """获取队列状态"""
        with self.lock:
            return self.queue.copy()


class AdvancedTaskScheduler:
    """高级任务调度器"""
    
    def __init__(self):
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.dependency_manager = TaskDependencyManager()
        self.priority_queue = TaskPriorityQueue()
        # 使用服务代理避免循环导入
        self.task_execution_service = create_service_proxy('task_execution_service')
        self.running = False
        self.missed_job_handler_enabled = True
        self._executor = ThreadPoolExecutor(max_workers=4)

        # 配置APScheduler
        self._setup_scheduler()
        
    def _setup_scheduler(self):
        """设置APScheduler调度器"""
        try:
            # 配置jobstore（使用数据库持久化）
            jobstores = {
                'default': SQLAlchemyJobStore(engine=engine, tablename='apscheduler_jobs')
            }
            
            # 配置executors
            executors = {
                'default': AsyncIOExecutor(),
                'threadpool': APSThreadPoolExecutor(20)
            }
            
            # 调度器配置
            job_defaults = {
                'coalesce': True,  # 合并错过的任务
                'max_instances': 3,  # 最大并发实例数
                'misfire_grace_time': 300  # 错过任务的宽限时间（秒）
            }
            
            # 创建调度器
            self.scheduler = AsyncIOScheduler(
                jobstores=jobstores,
                executors=executors,
                job_defaults=job_defaults,
                timezone='UTC'
            )
            
            # 添加事件监听器
            self.scheduler.add_listener(self._job_executed_listener, EVENT_JOB_EXECUTED)
            self.scheduler.add_listener(self._job_error_listener, EVENT_JOB_ERROR)
            self.scheduler.add_listener(self._job_missed_listener, EVENT_JOB_MISSED)
            
            logger.info("APScheduler调度器配置完成", 
                       jobstores=list(jobstores.keys()), 
                       executors=list(executors.keys()))
            
        except Exception as e:
            logger.error("设置APScheduler调度器失败", error=str(e), error_type=type(e).__name__)
            raise
            
    async def start(self):
        """启动调度器"""
        if self.running:
            logger.warning("调度器已在运行中", scheduler_state="running")
            return
            
        try:
            # 通过服务定位器获取任务执行服务
            execution_service = service_locator.get('task_execution_service')
            if execution_service:
                try:
                    # 确保服务已初始化
                    if hasattr(execution_service, 'initialize') and not getattr(execution_service, '_initialized', False):
                        await execution_service.initialize()
                    logger.info("任务执行服务获取成功", service_type="TaskExecutionService")
                except Exception as e:
                    logger.error("任务执行服务初始化失败", error=str(e), error_type=type(e).__name__)
            else:
                logger.warning("任务执行服务未注册，调度器将以有限功能模式运行", mode="limited")
            
            # 启动APScheduler
            self.scheduler.start()
            self.running = True
            
            # 恢复未完成的调度任务
            await self._restore_scheduled_tasks()
            
            logger.info("高级任务调度器启动成功", 
                       scheduler_running=self.scheduler.running,
                       job_count=len(self.scheduler.get_jobs()))
            
        except Exception as e:
            logger.error("启动调度器失败", error=str(e), error_type=type(e).__name__)
            raise
            
    async def stop(self):
        """停止调度器"""
        if not self.running:
            return
            
        try:
            logger.info("停止高级任务调度器", final_state="stopping")
            
            # 停止APScheduler
            if self.scheduler and self.scheduler.running:
                self.scheduler.shutdown(wait=True)
                
            self.running = False
            
            # 关闭线程池
            self._executor.shutdown(wait=True)
            
            logger.info("高级任务调度器已停止")
            
        except Exception as e:
            logger.error("停止调度器时出错", error=str(e), error_type=type(e).__name__)
            
    async def _restore_scheduled_tasks(self):
        """恢复数据库中的调度任务到APScheduler"""
        try:
            with optimized_db_session() as db:
                # 查找所有活跃的循环任务
                recurring_tasks = db.query(DownloadTask).filter(
                    and_(
                        DownloadTask.task_type == 'recurring',
                        DownloadTask.is_active == True,
                        DownloadTask.schedule_type.isnot(None)
                    )
                ).all()
                
                restored_count = 0
                for task in recurring_tasks:
                    try:
                        await self._add_task_to_scheduler(task)
                        restored_count += 1
                    except Exception as e:
                        logger.error(f"恢复任务 {task.id} 到调度器失败", 
                                   task_id=task.id, error=str(e))
                        
                logger.info(f"恢复了 {restored_count} 个调度任务到APScheduler")
                
        except Exception as e:
            logger.error("恢复调度任务失败", error=str(e), error_type=type(e).__name__)
            
    async def _add_task_to_scheduler(self, task: DownloadTask):
        """将数据库任务添加到APScheduler"""
        if not task.schedule_type or not task.schedule_config:
            return
            
        job_id = f"download_task_{task.id}"
        
        try:
            # 移除现有的同名任务（如果存在）
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                
            # 根据调度类型创建触发器
            trigger = self._create_trigger(task.schedule_type, task.schedule_config)
            if not trigger:
                logger.warning(f"无法为任务 {task.id} 创建触发器")
                return
                
            # 添加任务到调度器
            self.scheduler.add_job(
                func=self._execute_scheduled_task,
                trigger=trigger,
                args=[task.id],
                id=job_id,
                name=f"DownloadTask_{task.id}_{task.name}",
                replace_existing=True,
                max_instances=1,
                coalesce=True
            )
            
            logger.info(f"任务 {task.id} 已添加到APScheduler", 
                       job_id=job_id, schedule_type=task.schedule_type)
            
        except ConflictingIdError:
            logger.warning(f"任务 {job_id} 已存在于调度器中")
        except Exception as e:
            logger.error(f"添加任务 {task.id} 到调度器失败", 
                        task_id=task.id, error=str(e), error_type=type(e).__name__)
            raise
            
    def _create_trigger(self, schedule_type: str, schedule_config: Dict[str, Any]):
        """根据配置创建APScheduler触发器"""
        try:
            if schedule_type == 'interval':
                # 间隔调度：{"interval": 3600, "unit": "seconds"}
                interval = schedule_config.get('interval', 3600)
                unit = schedule_config.get('unit', 'seconds')
                
                kwargs = {}
                if unit == 'seconds':
                    kwargs['seconds'] = interval
                elif unit == 'minutes':
                    kwargs['minutes'] = interval
                elif unit == 'hours':
                    kwargs['hours'] = interval
                elif unit == 'days':
                    kwargs['days'] = interval
                else:
                    kwargs['seconds'] = interval
                    
                return IntervalTrigger(**kwargs)
                
            elif schedule_type == 'daily':
                # 每日调度：{"hour": 9, "minute": 0}
                hour = schedule_config.get('hour', 9)
                minute = schedule_config.get('minute', 0)
                
                return CronTrigger(hour=hour, minute=minute)
                
            elif schedule_type == 'weekly':
                # 每周调度：{"weekday": 1, "hour": 9, "minute": 0} (0=Monday)
                weekday = schedule_config.get('weekday', 1)
                hour = schedule_config.get('hour', 9)
                minute = schedule_config.get('minute', 0)
                
                return CronTrigger(day_of_week=weekday, hour=hour, minute=minute)
                
            elif schedule_type == 'monthly':
                # 每月调度：{"day": 1, "hour": 9, "minute": 0}
                day = schedule_config.get('day', 1)
                hour = schedule_config.get('hour', 9)
                minute = schedule_config.get('minute', 0)
                
                return CronTrigger(day=day, hour=hour, minute=minute)
                
            elif schedule_type == 'cron':
                # 完整Cron表达式：{"expression": "0 9 * * 1-5"}
                cron_expression = schedule_config.get('expression', '0 9 * * *')
                
                # 解析cron表达式
                parts = cron_expression.split()
                if len(parts) != 5:
                    logger.warning(f"无效的cron表达式格式: {cron_expression}")
                    return None
                    
                minute, hour, day, month, day_of_week = parts
                
                # 创建CronTrigger
                return CronTrigger(
                    minute=minute,
                    hour=hour,
                    day=day,
                    month=month,
                    day_of_week=day_of_week
                )
                
        except Exception as e:
            logger.error(f"创建触发器失败", 
                        schedule_type=schedule_type, 
                        schedule_config=schedule_config,
                        error=str(e))
            return None
            
        return None
        
    async def _execute_scheduled_task(self, task_id: int):
        """执行调度任务（APScheduler回调）"""
        try:
            # 检查任务依赖
            task_key = f"task_{task_id}"
            if not self.dependency_manager.can_execute(task_key):
                logger.info(f"任务 {task_id} 依赖未满足，跳过执行")
                return
                
            with optimized_db_session() as db:
                task = db.query(DownloadTask).filter(DownloadTask.id == task_id).first()
                if not task:
                    logger.error(f"任务 {task_id} 不存在")
                    return
                    
                # 检查是否达到最大执行次数
                if task.max_runs and task.run_count >= task.max_runs:
                    logger.info(f"任务 {task_id} 已达到最大执行次数 {task.max_runs}，停用调度")
                    task.is_active = False
                    db.commit()
                    
                    # 从调度器中移除
                    job_id = f"download_task_{task_id}"
                    if self.scheduler.get_job(job_id):
                        self.scheduler.remove_job(job_id)
                    return
                    
                # 更新执行统计
                task.run_count += 1
                task.last_run_time = datetime.now(timezone.utc)
                task.status = 'pending'
                task.progress = 0
                task.downloaded_messages = 0
                task.total_messages = 0
                task.error_message = None
                
                db.commit()
                
                logger.info(f"执行调度任务 {task_id}: {task.name}，第 {task.run_count} 次执行")
                
                # 启动任务执行
                if self.task_execution_service:
                    await self.task_execution_service.start_task(task_id)
                    self.dependency_manager.mark_completed(task_key)
                else:
                    logger.warning(f"任务执行服务不可用，跳过任务 {task_id} 的执行")
                    self.dependency_manager.mark_failed(task_key)
                    
        except Exception as e:
            logger.error(f"执行调度任务 {task_id} 时出错", 
                        task_id=task_id, error=str(e), error_type=type(e).__name__)
            self.dependency_manager.mark_failed(f"task_{task_id}")
            
    async def schedule_task(self, task_id: int, schedule_type: str, schedule_config: Dict[str, Any], 
                           max_runs: Optional[int] = None, priority: int = 0,
                           dependencies: Optional[List[int]] = None) -> bool:
        """为任务设置调度"""
        try:
            with optimized_db_session() as db:
                task = db.query(DownloadTask).filter(DownloadTask.id == task_id).first()
                if not task:
                    logger.error(f"任务 {task_id} 不存在")
                    return False
                    
                # 更新任务调度配置
                task.task_type = 'recurring'
                task.schedule_type = schedule_type
                task.schedule_config = schedule_config
                task.is_active = True
                task.max_runs = max_runs
                task.run_count = 0
                
                db.commit()
                
                # 添加到APScheduler
                await self._add_task_to_scheduler(task)
                
                # 设置任务依赖
                if dependencies:
                    task_key = f"task_{task_id}"
                    dep_keys = [f"task_{dep_id}" for dep_id in dependencies]
                    self.dependency_manager.add_dependency(task_key, dep_keys)
                    
                # 添加到优先级队列
                self.priority_queue.add_task(
                    task_id=str(task_id), 
                    priority=priority,
                    metadata={'schedule_type': schedule_type}
                )
                
                logger.info(f"为任务 {task_id} 设置调度成功", 
                           schedule_type=schedule_type, 
                           priority=priority,
                           dependencies=dependencies)
                return True
                
        except Exception as e:
            logger.error(f"设置任务 {task_id} 调度时出错", 
                        task_id=task_id, error=str(e), error_type=type(e).__name__)
            return False
            
    async def cancel_task_schedule(self, task_id: int) -> bool:
        """取消任务调度"""
        try:
            with optimized_db_session() as db:
                task = db.query(DownloadTask).filter(DownloadTask.id == task_id).first()
                if not task:
                    return False
                    
                # 更新数据库
                task.task_type = 'once'
                task.schedule_type = None
                task.schedule_config = None
                task.is_active = False
                task.next_run_time = None
                
                db.commit()
                
                # 从APScheduler中移除
                job_id = f"download_task_{task_id}"
                if self.scheduler.get_job(job_id):
                    self.scheduler.remove_job(job_id)
                    
                # 从优先级队列中移除
                self.priority_queue.remove_task(str(task_id))
                
                # 重置依赖状态
                task_key = f"task_{task_id}"
                self.dependency_manager.reset_task(task_key)
                
                logger.info(f"取消任务 {task_id} 的调度成功")
                return True
                
        except Exception as e:
            logger.error(f"取消任务 {task_id} 调度时出错", 
                        task_id=task_id, error=str(e), error_type=type(e).__name__)
            return False
            
    async def get_scheduled_tasks(self) -> List[Dict[str, Any]]:
        """获取所有调度任务的状态"""
        try:
            with optimized_db_session() as db:
                tasks = db.query(DownloadTask).filter(
                    DownloadTask.task_type == 'recurring'
                ).all()
                
                result = []
                for task in tasks:
                    job_id = f"download_task_{task.id}"
                    job = self.scheduler.get_job(job_id) if self.scheduler else None
                    
                    task_info = {
                        'id': task.id,
                        'name': task.name,
                        'schedule_type': task.schedule_type,
                        'schedule_config': task.schedule_config,
                        'next_run_time': job.next_run_time.isoformat() if job and job.next_run_time else None,
                        'last_run_time': task.last_run_time.isoformat() if task.last_run_time else None,
                        'is_active': task.is_active,
                        'run_count': task.run_count,
                        'max_runs': task.max_runs,
                        'status': task.status,
                        'scheduler_job_exists': job is not None
                    }
                    
                    result.append(task_info)
                    
                return result
                
        except Exception as e:
            logger.error("获取调度任务状态时出错", error=str(e), error_type=type(e).__name__)
            return []
            
    async def get_job_statistics(self) -> Dict[str, Any]:
        """获取任务统计信息"""
        try:
            jobs = self.scheduler.get_jobs() if self.scheduler else []
            queue_status = self.priority_queue.get_queue_status()
            
            return {
                'total_jobs': len(jobs),
                'active_jobs': len([job for job in jobs if job.next_run_time]),
                'pending_in_queue': len(queue_status),
                'scheduler_running': self.scheduler.running if self.scheduler else False,
                'dependency_stats': {
                    'total_dependencies': len(self.dependency_manager.dependencies),
                    'completed_tasks': len(self.dependency_manager.completed_tasks),
                    'failed_tasks': len(self.dependency_manager.failed_tasks)
                }
            }
            
        except Exception as e:
            logger.error("获取任务统计信息时出错", error=str(e), error_type=type(e).__name__)
            return {}
            
    def _job_executed_listener(self, event):
        """任务执行成功监听器"""
        logger.info("调度任务执行成功", 
                   job_id=event.job_id, 
                   scheduled_run_time=event.scheduled_run_time,
                   retval=str(event.retval) if event.retval else None)
                   
    def _job_error_listener(self, event):
        """任务执行错误监听器"""
        logger.error("调度任务执行失败", 
                    job_id=event.job_id,
                    scheduled_run_time=event.scheduled_run_time,
                    exception=str(event.exception),
                    traceback=event.traceback)
                    
    def _job_missed_listener(self, event):
        """任务错过执行监听器"""
        if self.missed_job_handler_enabled:
            logger.warning("调度任务错过执行", 
                          job_id=event.job_id,
                          scheduled_run_time=event.scheduled_run_time)
            
            # 可以在这里实现错过任务的补偿逻辑
            # 例如：立即执行错过的任务或记录到特殊队列中
            
    async def handle_missed_jobs(self, strategy: str = 'reschedule'):
        """处理错过的任务"""
        if strategy == 'reschedule':
            # 重新调度所有错过的任务
            logger.info("重新调度错过的任务")
            await self._restore_scheduled_tasks()
        elif strategy == 'execute_now':
            # 立即执行所有错过的任务
            logger.info("立即执行错过的任务")
            # 实现立即执行逻辑
        else:
            logger.warning(f"未知的错过任务处理策略: {strategy}")


# 保持向后兼容的简化版TaskScheduler
class TaskScheduler:
    """简化版任务调度器（向后兼容）"""
    
    def __init__(self):
        self.advanced_scheduler = AdvancedTaskScheduler()
        
    async def start(self):
        return await self.advanced_scheduler.start()
        
    async def stop(self):
        return await self.advanced_scheduler.stop()
        
    async def schedule_task(self, task_id: int, schedule_type: str, schedule_config: Dict[str, Any], 
                           max_runs: Optional[int] = None) -> bool:
        return await self.advanced_scheduler.schedule_task(
            task_id, schedule_type, schedule_config, max_runs
        )
        
    async def cancel_task_schedule(self, task_id: int) -> bool:
        return await self.advanced_scheduler.cancel_task_schedule(task_id)
        
    async def get_scheduled_tasks(self) -> List[Dict[str, Any]]:
        return await self.advanced_scheduler.get_scheduled_tasks()


# 创建全局调度器实例
task_scheduler = AdvancedTaskScheduler()

# 保持向后兼容
simple_task_scheduler = TaskScheduler()