"""
任务调度器服务
支持多种调度类型：interval、cron、daily、weekly、monthly
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
# from crontab import CronTab  # 暂时注释，使用简化版本
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ..models.rule import DownloadTask
from ..database import get_db
from ..utils.db_optimization import optimized_db_session
# TaskExecutionService将在需要时延迟导入，避免循环导入

logger = logging.getLogger(__name__)

class TaskScheduler:
    """任务调度器"""
    
    def __init__(self):
        self.running = False
        self.scheduler_task = None
        self.task_execution_service = None  # 延迟初始化
        self.check_interval = 60  # 每60秒检查一次
        
    async def start(self):
        """启动调度器"""
        if self.running:
            logger.warning("调度器已在运行中")
            return
            
        logger.info("启动任务调度器")
        self.running = True
        
        try:
            # 延迟导入TaskExecutionService避免循环导入
            if not self.task_execution_service:
                from .task_execution_service import TaskExecutionService
                self.task_execution_service = TaskExecutionService()
            
            # 确保task_execution_service已初始化
            await self.task_execution_service.initialize()
            logger.info("任务执行服务初始化成功")
        except ImportError as e:
            logger.error(f"无法导入任务执行服务: {e}")
            logger.warning("调度器将以有限功能模式运行")
            self.task_execution_service = None
        except Exception as e:
            logger.error(f"任务执行服务初始化失败: {e}")
            logger.warning("调度器将以有限功能模式运行")
            # 不阻止调度器启动，但标记服务不可用
            self.task_execution_service = None
        
        # 启动调度器循环
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())
        
    async def stop(self):
        """停止调度器"""
        if not self.running:
            return
            
        logger.info("停止任务调度器")
        self.running = False
        
        if self.scheduler_task:
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass
                
    async def _scheduler_loop(self):
        """调度器主循环"""
        while self.running:
            try:
                await self._check_and_execute_tasks()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                logger.info("调度器循环被取消")
                break
            except Exception as e:
                logger.error(f"调度器循环出错: {e}")
                await asyncio.sleep(self.check_interval)
                
    async def _check_and_execute_tasks(self):
        """检查并执行到期的任务"""
        try:
            with optimized_db_session() as db:
                # 查找需要执行的任务
                now = datetime.now(timezone.utc)
                
                # 查询条件：
                # 1. 任务类型为循环任务
                # 2. 任务处于激活状态
                # 3. 任务未在运行中
                # 4. 下次执行时间已到或为空（需要重新计算）
                tasks_to_run = db.query(DownloadTask).filter(
                    and_(
                        DownloadTask.task_type == 'recurring',
                        DownloadTask.is_active == True,
                        DownloadTask.status.in_(['pending', 'completed', 'failed']),
                        or_(
                            DownloadTask.next_run_time <= now,
                            DownloadTask.next_run_time.is_(None)
                        )
                    )
                ).all()
                
                for task in tasks_to_run:
                    await self._execute_scheduled_task(task, db)
                    
        except Exception as e:
            logger.error(f"检查任务时出错: {e}")
            
    async def _execute_scheduled_task(self, task: DownloadTask, db: Session):
        """执行调度任务"""
        try:
            # 检查是否达到最大执行次数
            if task.max_runs and task.run_count >= task.max_runs:
                logger.info(f"任务 {task.id} 已达到最大执行次数 {task.max_runs}，停用调度")
                task.is_active = False
                db.commit()
                return
                
            # 更新执行次数和最后执行时间
            task.run_count += 1
            task.last_run_time = datetime.now(timezone.utc)
            
            # 计算下次执行时间
            next_run = self._calculate_next_run_time(task)
            task.next_run_time = next_run
            
            # 重置任务状态为pending
            task.status = 'pending'
            task.progress = 0
            task.downloaded_messages = 0
            task.total_messages = 0
            task.error_message = None
            
            db.commit()
            
            logger.info(f"执行调度任务 {task.id}: {task.name}，下次执行时间: {next_run}")
            
            # 启动任务执行
            if self.task_execution_service:
                await self.task_execution_service.start_task(task.id)
            else:
                logger.warning(f"任务执行服务不可用，跳过任务 {task.id} 的执行")
            
        except Exception as e:
            logger.error(f"执行调度任务 {task.id} 时出错: {e}")
            
    def _calculate_next_run_time(self, task: DownloadTask) -> Optional[datetime]:
        """计算下次执行时间"""
        if not task.schedule_type or not task.schedule_config:
            return None
            
        now = datetime.now(timezone.utc)
        schedule_config = task.schedule_config
        
        try:
            if task.schedule_type == 'interval':
                # 间隔调度：{"interval": 3600, "unit": "seconds"} 
                interval_seconds = schedule_config.get('interval', 3600)
                unit = schedule_config.get('unit', 'seconds')
                
                if unit == 'minutes':
                    interval_seconds *= 60
                elif unit == 'hours':
                    interval_seconds *= 3600
                elif unit == 'days':
                    interval_seconds *= 86400
                    
                return now + timedelta(seconds=interval_seconds)
                
            elif task.schedule_type == 'daily':
                # 每日调度：{"hour": 9, "minute": 0}
                hour = schedule_config.get('hour', 9)
                minute = schedule_config.get('minute', 0)
                
                next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if next_run <= now:
                    next_run += timedelta(days=1)
                return next_run
                
            elif task.schedule_type == 'weekly':
                # 每周调度：{"weekday": 1, "hour": 9, "minute": 0} (0=Monday)
                weekday = schedule_config.get('weekday', 1)
                hour = schedule_config.get('hour', 9)
                minute = schedule_config.get('minute', 0)
                
                days_ahead = weekday - now.weekday()
                if days_ahead <= 0:  # Target day already happened this week
                    days_ahead += 7
                    
                next_run = now + timedelta(days=days_ahead)
                next_run = next_run.replace(hour=hour, minute=minute, second=0, microsecond=0)
                return next_run
                
            elif task.schedule_type == 'monthly':
                # 每月调度：{"day": 1, "hour": 9, "minute": 0}
                day = schedule_config.get('day', 1)
                hour = schedule_config.get('hour', 9)
                minute = schedule_config.get('minute', 0)
                
                # 计算下个月的同一天
                if now.month == 12:
                    next_month = now.replace(year=now.year + 1, month=1, day=day, 
                                           hour=hour, minute=minute, second=0, microsecond=0)
                else:
                    next_month = now.replace(month=now.month + 1, day=day, 
                                           hour=hour, minute=minute, second=0, microsecond=0)
                return next_month
                
            elif task.schedule_type == 'cron':
                # Cron表达式：{"expression": "0 9 * * 1-5"} 
                # 暂时使用简化版本，只支持基本的每日cron
                cron_expression = schedule_config.get('expression', '0 9 * * *')
                # 简化处理：假设是 "minute hour * * *" 格式
                parts = cron_expression.split()
                if len(parts) >= 2:
                    try:
                        minute = int(parts[0])
                        hour = int(parts[1])
                        next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                        if next_run <= now:
                            next_run += timedelta(days=1)
                        return next_run
                    except (ValueError, IndexError):
                        logger.warning(f"无效的cron表达式: {cron_expression}")
                        return None
                
        except Exception as e:
            logger.error(f"计算任务 {task.id} 下次执行时间出错: {e}")
            
        return None
        
    async def schedule_task(self, task_id: int, schedule_type: str, schedule_config: Dict[str, Any], 
                           max_runs: Optional[int] = None) -> bool:
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
                
                # 计算下次执行时间
                next_run = self._calculate_next_run_time(task)
                task.next_run_time = next_run
                
                db.commit()
                
                logger.info(f"为任务 {task_id} 设置调度，类型: {schedule_type}，下次执行: {next_run}")
                return True
                
        except Exception as e:
            logger.error(f"设置任务 {task_id} 调度时出错: {e}")
            return False
            
    async def cancel_task_schedule(self, task_id: int) -> bool:
        """取消任务调度"""
        try:
            with optimized_db_session() as db:
                task = db.query(DownloadTask).filter(DownloadTask.id == task_id).first()
                if not task:
                    return False
                    
                task.task_type = 'once'
                task.schedule_type = None
                task.schedule_config = None
                task.is_active = False
                task.next_run_time = None
                
                db.commit()
                
                logger.info(f"取消任务 {task_id} 的调度")
                return True
                
        except Exception as e:
            logger.error(f"取消任务 {task_id} 调度时出错: {e}")
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
                    result.append({
                        'id': task.id,
                        'name': task.name,
                        'schedule_type': task.schedule_type,
                        'schedule_config': task.schedule_config,
                        'next_run_time': task.next_run_time.isoformat() if task.next_run_time else None,
                        'last_run_time': task.last_run_time.isoformat() if task.last_run_time else None,
                        'is_active': task.is_active,
                        'run_count': task.run_count,
                        'max_runs': task.max_runs,
                        'status': task.status
                    })
                    
                return result
                
        except Exception as e:
            logger.error(f"获取调度任务状态时出错: {e}")
            return []

# 创建全局调度器实例
task_scheduler = TaskScheduler()