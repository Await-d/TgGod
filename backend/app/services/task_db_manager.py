"""
任务执行专用数据库优化工具
专门处理任务执行过程中的数据库访问优化
"""
import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import Any, Callable, Optional, Dict, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError
from ..database import SessionLocal
from ..utils.db_optimization import optimized_db_session

logger = logging.getLogger(__name__)

class TaskDatabaseManager:
    """任务专用数据库管理器，优化并发访问和锁定处理"""
    
    def __init__(self):
        self.active_sessions: Dict[str, Session] = {}
        self.session_lock = asyncio.Lock()
        self.retry_delays = [0.1, 0.3, 0.7, 1.5, 3.0, 6.0, 10.0]  # 递增延迟
        
    @asynccontextmanager
    async def get_task_session(self, task_id: int, operation_type: str = "default"):
        """
        获取任务专用数据库会话
        
        Args:
            task_id: 任务ID
            operation_type: 操作类型 (progress, log, completion等)
        """
        session_key = f"task_{task_id}_{operation_type}"
        max_retries = self._get_max_retries_by_type(operation_type)
        
        session = None
        retry_count = 0
        
        while retry_count <= max_retries:
            try:
                async with self.session_lock:
                    # 检查是否有复用的会话
                    if session_key in self.active_sessions:
                        session = self.active_sessions[session_key]
                        if session.is_active:
                            yield session
                            break
                        else:
                            # 清理无效会话
                            del self.active_sessions[session_key]
                
                # 创建新会话
                session = SessionLocal()
                
                # 根据操作类型设置会话参数
                if operation_type == "progress":
                    # 进度更新使用更快的事务模式
                    session.execute("PRAGMA journal_mode=WAL;")
                    session.execute("PRAGMA synchronous=NORMAL;")
                elif operation_type == "batch_query":
                    # 批量查询优化
                    session.execute("PRAGMA cache_size=20000;")
                    session.execute("PRAGMA temp_store=MEMORY;")
                
                async with self.session_lock:
                    self.active_sessions[session_key] = session
                
                yield session
                
                if session.in_transaction():
                    session.commit()
                break
                
            except OperationalError as e:
                error_msg = str(e).lower()
                
                if any(keyword in error_msg for keyword in ['database is locked', 'timeout', 'busy']):
                    retry_count += 1
                    
                    if session:
                        try:
                            session.rollback()
                        except:
                            pass
                        finally:
                            session.close()
                            async with self.session_lock:
                                if session_key in self.active_sessions:
                                    del self.active_sessions[session_key]
                    
                    if retry_count <= max_retries:
                        delay = self.retry_delays[min(retry_count - 1, len(self.retry_delays) - 1)]
                        logger.warning(f"任务{task_id} {operation_type}操作数据库锁定，{delay:.1f}秒后重试 (尝试 {retry_count}/{max_retries})")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        logger.error(f"任务{task_id} {operation_type}操作达到最大重试次数")
                        raise
                else:
                    # 非锁相关错误，直接抛出
                    raise
                    
            except Exception as e:
                if session:
                    try:
                        session.rollback()
                    except:
                        pass
                raise
                
            finally:
                if session:
                    try:
                        session.close()
                    except:
                        pass
                    finally:
                        async with self.session_lock:
                            if session_key in self.active_sessions:
                                del self.active_sessions[session_key]
    
    def _get_max_retries_by_type(self, operation_type: str) -> int:
        """根据操作类型获取最大重试次数"""
        retry_config = {
            "progress": 15,      # 进度更新最重要，重试次数最多
            "log": 8,           # 日志写入中等重要
            "completion": 12,   # 任务完成状态重要
            "batch_query": 20,  # 批量查询可能耗时较长，需要更多重试
            "default": 10
        }
        return retry_config.get(operation_type, 10)
    
    async def batch_progress_update(self, updates: List[Dict[str, Any]]):
        """批量更新进度，减少数据库访问次数"""
        if not updates:
            return
        
        try:
            async with self.get_task_session(0, "progress") as session:
                from ..models.rule import DownloadTask
                
                for update in updates:
                    task_id = update.get('task_id')
                    if not task_id:
                        continue
                        
                    task = session.query(DownloadTask).filter(DownloadTask.id == task_id).first()
                    if task:
                        if 'progress' in update:
                            task.progress = update['progress']
                        if 'downloaded_messages' in update:
                            task.downloaded_messages = update['downloaded_messages']
                        if 'status' in update:
                            task.status = update['status']
                
                session.commit()
                logger.debug(f"批量更新了 {len(updates)} 个任务的进度")
                
        except Exception as e:
            logger.error(f"批量进度更新失败: {e}")
    
    async def quick_status_update(self, task_id: int, status: str, error_message: str = None):
        """快速状态更新，用于任务完成或失败"""
        try:
            async with self.get_task_session(task_id, "completion") as session:
                from ..models.rule import DownloadTask
                from datetime import datetime, timezone
                
                task = session.query(DownloadTask).filter(DownloadTask.id == task_id).first()
                if task:
                    task.status = status
                    if status == "completed":
                        task.progress = 100
                        task.completed_at = datetime.now(timezone.utc)
                    elif status == "failed" and error_message:
                        task.error_message = error_message
                
                session.commit()
                logger.debug(f"快速更新任务 {task_id} 状态为 {status}")
                
        except Exception as e:
            logger.error(f"快速状态更新失败: {e}")
    
    async def cleanup_sessions(self):
        """清理所有活跃会话"""
        async with self.session_lock:
            for session_key, session in list(self.active_sessions.items()):
                try:
                    if session.is_active:
                        session.close()
                except:
                    pass
                del self.active_sessions[session_key]
            
            logger.info(f"已清理所有数据库会话")

# 全局任务数据库管理器实例
task_db_manager = TaskDatabaseManager()