"""
Mock任务执行服务

当Telegram服务不可用时，提供模拟的任务执行功能，
主要用于测试和演示任务管理功能。
"""

import asyncio
import logging
import time
from typing import Dict, List
from ..models.rule import DownloadTask
from ..utils.db_optimization import optimized_db_session
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class MockTaskExecutionService:
    """Mock任务执行服务 - 用于测试"""
    
    def __init__(self):
        self.running_tasks: Dict[int, asyncio.Task] = {}
        self.mock_tasks: Dict[int, Dict] = {}  # 存储模拟任务状态
        self._initialized = True
        
    async def initialize(self):
        """初始化服务"""
        logger.info("Mock任务执行服务初始化完成")
        return True
    
    async def start_task(self, task_id: int) -> bool:
        """启动任务 - Mock版本"""
        try:
            logger.info(f"Mock启动任务 {task_id}")
            
            # 更新数据库中的任务状态
            with optimized_db_session() as db:
                task = db.query(DownloadTask).filter(DownloadTask.id == task_id).first()
                if not task:
                    logger.error(f"任务 {task_id} 不存在")
                    return False
                
                task.status = "running"
                task.progress = 0
                task.error_message = None
                db.commit()
            
            # 启动模拟任务
            mock_task = asyncio.create_task(self._mock_execute_task(task_id))
            self.running_tasks[task_id] = mock_task
            
            logger.info(f"Mock任务 {task_id} 启动成功")
            return True
            
        except Exception as e:
            logger.error(f"Mock启动任务 {task_id} 失败: {e}")
            return False
    
    async def pause_task(self, task_id: int) -> bool:
        """暂停任务 - Mock版本"""
        try:
            logger.info(f"Mock暂停任务 {task_id}")
            
            if task_id in self.running_tasks:
                self.running_tasks[task_id].cancel()
                del self.running_tasks[task_id]
            
            # 更新数据库状态
            with optimized_db_session() as db:
                task = db.query(DownloadTask).filter(DownloadTask.id == task_id).first()
                if task:
                    task.status = "paused"
                    db.commit()
            
            logger.info(f"Mock任务 {task_id} 暂停成功")
            return True
            
        except Exception as e:
            logger.error(f"Mock暂停任务 {task_id} 失败: {e}")
            return False
    
    async def stop_task(self, task_id: int) -> bool:
        """停止任务 - Mock版本"""
        try:
            logger.info(f"Mock停止任务 {task_id}")
            
            if task_id in self.running_tasks:
                self.running_tasks[task_id].cancel()
                del self.running_tasks[task_id]
            
            # 更新数据库状态
            with optimized_db_session() as db:
                task = db.query(DownloadTask).filter(DownloadTask.id == task_id).first()
                if task:
                    task.status = "failed"
                    task.error_message = "任务被手动停止"
                    db.commit()
            
            logger.info(f"Mock任务 {task_id} 停止成功")
            return True
            
        except Exception as e:
            logger.error(f"Mock停止任务 {task_id} 失败: {e}")
            return False
    
    async def _mock_execute_task(self, task_id: int):
        """模拟任务执行"""
        try:
            logger.info(f"开始模拟执行任务 {task_id}")
            
            # 模拟执行过程，逐步更新进度
            for progress in range(0, 101, 10):
                # 检查任务是否被取消
                if task_id not in self.running_tasks:
                    logger.info(f"Mock任务 {task_id} 已被取消")
                    return
                
                # 更新进度
                with optimized_db_session() as db:
                    task = db.query(DownloadTask).filter(DownloadTask.id == task_id).first()
                    if task:
                        task.progress = progress
                        task.downloaded_messages = int(task.total_messages * progress / 100) if task.total_messages else progress
                        db.commit()
                
                logger.info(f"Mock任务 {task_id} 进度: {progress}%")
                
                # 模拟处理时间
                await asyncio.sleep(2)
            
            # 任务完成
            with optimized_db_session() as db:
                task = db.query(DownloadTask).filter(DownloadTask.id == task_id).first()
                if task:
                    task.status = "completed"
                    task.progress = 100
                    task.completed_at = datetime.now(timezone.utc)
                    db.commit()
            
            # 清理运行中任务记录
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
            
            logger.info(f"Mock任务 {task_id} 执行完成")
            
        except asyncio.CancelledError:
            logger.info(f"Mock任务 {task_id} 被取消")
            return
        except Exception as e:
            logger.error(f"Mock任务 {task_id} 执行失败: {e}")
            
            # 标记任务失败
            with optimized_db_session() as db:
                task = db.query(DownloadTask).filter(DownloadTask.id == task_id).first()
                if task:
                    task.status = "failed"
                    task.error_message = f"模拟执行失败: {str(e)}"
                    db.commit()
            
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
    
    def get_running_tasks(self) -> List[int]:
        """获取正在运行的任务列表"""
        return list(self.running_tasks.keys())
    
    def is_task_running(self, task_id: int) -> bool:
        """检查任务是否正在运行"""
        return task_id in self.running_tasks

# 创建Mock服务实例
mock_task_execution_service = MockTaskExecutionService()