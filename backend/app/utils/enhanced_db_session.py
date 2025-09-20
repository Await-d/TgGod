"""增强的数据库会话管理器

提供带有连接池监控、自动重试、泄漏检测的数据库会话管理功能。

主要功能:
- 智能会话管理
- 连接泄漏检测
- 自动重试机制
- 性能监控
- 事务管理优化

Author: TgGod Team
Version: 1.0.0
"""

import time
import uuid
import logging
import threading
import traceback
from contextlib import contextmanager
from typing import Optional, Any, Callable, Dict
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError, DisconnectionError, TimeoutError
from sqlalchemy import text

from ..database import SessionLocal
from ..services.connection_pool_monitor import get_pool_monitor

logger = logging.getLogger(__name__)

class SessionTracker:
    """会话跟踪器"""

    def __init__(self):
        self.active_sessions: Dict[str, Dict] = {}
        self.session_stats: Dict[str, Any] = {
            'total_created': 0,
            'total_closed': 0,
            'total_leaked': 0,
            'total_errors': 0
        }
        self.lock = threading.Lock()

    def track_session(self, session_id: str, context: str = ""):
        """跟踪会话"""
        with self.lock:
            self.active_sessions[session_id] = {
                'created_at': datetime.now(),
                'context': context,
                'stack_trace': traceback.format_stack()
            }
            self.session_stats['total_created'] += 1

    def untrack_session(self, session_id: str):
        """取消跟踪会话"""
        with self.lock:
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
                self.session_stats['total_closed'] += 1

    def check_leaks(self, max_age_seconds: int = 300) -> list:
        """检查会话泄漏"""
        leaks = []
        cutoff_time = datetime.now() - timedelta(seconds=max_age_seconds)

        with self.lock:
            for session_id, info in list(self.active_sessions.items()):
                if info['created_at'] < cutoff_time:
                    leaks.append({
                        'session_id': session_id,
                        'age_seconds': (datetime.now() - info['created_at']).total_seconds(),
                        'context': info['context'],
                        'created_at': info['created_at'].isoformat()
                    })

        if leaks:
            self.session_stats['total_leaked'] += len(leaks)
            logger.warning(f"检测到 {len(leaks)} 个可能的会话泄漏")

        return leaks

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self.lock:
            return {
                **self.session_stats,
                'active_sessions': len(self.active_sessions),
                'oldest_session_age': self._get_oldest_session_age()
            }

    def _get_oldest_session_age(self) -> Optional[float]:
        """获取最老会话的年龄（秒）"""
        if not self.active_sessions:
            return None

        oldest_time = min(info['created_at'] for info in self.active_sessions.values())
        return (datetime.now() - oldest_time).total_seconds()

# 全局会话跟踪器
session_tracker = SessionTracker()

@contextmanager
def enhanced_db_session(
    autocommit: bool = True,
    max_retries: int = 3,
    timeout: float = 30.0,
    context: str = ""
):
    """
    增强的数据库会话管理器

    Args:
        autocommit: 是否自动提交
        max_retries: 最大重试次数
        timeout: 会话超时时间（秒）
        context: 会话上下文信息（用于调试）

    Yields:
        数据库会话
    """
    session_id = str(uuid.uuid4())
    session = None
    start_time = time.time()
    monitor = get_pool_monitor()

    try:
        # 跟踪会话创建
        session_tracker.track_session(session_id, context)

        session = _create_session_with_retry(max_retries, timeout)

        # 记录连接获取时间
        checkout_time = time.time() - start_time
        monitor.record_query_time(checkout_time)

        yield session

        # 自动提交事务
        if autocommit and session.in_transaction():
            session.commit()

    except Exception as e:
        # 记录错误
        monitor.record_connection_error()
        session_tracker.session_stats['total_errors'] += 1

        # 回滚事务
        if session and session.in_transaction():
            try:
                session.rollback()
            except Exception as rollback_error:
                logger.error(f"会话回滚失败: {rollback_error}")

        logger.error(f"数据库会话错误 [{session_id}]: {e}")
        raise

    finally:
        # 清理会话
        if session:
            try:
                session.close()
            except Exception as close_error:
                logger.error(f"会话关闭失败: {close_error}")

        # 取消跟踪
        session_tracker.untrack_session(session_id)

        # 记录总执行时间
        total_time = time.time() - start_time
        if total_time > 10.0:  # 记录慢会话
            logger.warning(f"慢会话 [{session_id}]: {total_time:.2f}秒, 上下文: {context}")

def _create_session_with_retry(max_retries: int, timeout: float) -> Session:
    """带重试的会话创建"""
    retry_count = 0

    while retry_count <= max_retries:
        try:
            session = SessionLocal()

            # 测试连接
            session.execute(text("SELECT 1"))

            return session

        except (OperationalError, DisconnectionError, TimeoutError) as e:
            error_msg = str(e).lower()

            # 检查是否是可重试的错误
            if any(keyword in error_msg for keyword in ['database is locked', 'timeout', 'busy', 'connection']):
                retry_count += 1

                if session:
                    try:
                        session.close()
                    except:
                        pass

                if retry_count <= max_retries:
                    # 指数退避策略
                    wait_time = min(0.1 * (2 ** retry_count), 2.0)
                    logger.warning(f"数据库连接失败，{wait_time:.2f}秒后重试 (尝试 {retry_count}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"数据库连接达到最大重试次数: {e}")
                    raise
            else:
                # 非可重试错误，直接抛出
                raise

        except Exception as e:
            logger.error(f"创建数据库会话失败: {e}")
            raise

    raise RuntimeError("无法创建数据库会话")

@contextmanager
def batch_db_session(batch_size: int = 100):
    """
    批量操作会话管理器

    Args:
        batch_size: 批处理大小

    Yields:
        (session, commit_func) 元组
    """
    with enhanced_db_session(autocommit=False, context="batch_operation") as session:
        operation_count = 0

        def maybe_commit():
            nonlocal operation_count
            operation_count += 1

            if operation_count >= batch_size:
                session.commit()
                operation_count = 0

        yield session, maybe_commit

        # 提交剩余的操作
        if operation_count > 0:
            session.commit()

def execute_with_session_retry(
    operation: Callable[[Session], Any],
    max_retries: int = 3,
    context: str = ""
) -> Any:
    """
    带重试的数据库操作执行器

    Args:
        operation: 数据库操作函数，接收session参数
        max_retries: 最大重试次数
        context: 操作上下文

    Returns:
        操作结果
    """
    for attempt in range(max_retries + 1):
        try:
            with enhanced_db_session(context=f"{context}_attempt_{attempt}") as session:
                return operation(session)

        except Exception as e:
            if attempt < max_retries:
                wait_time = 0.5 * (2 ** attempt)
                logger.warning(f"操作失败，{wait_time:.2f}秒后重试: {e}")
                time.sleep(wait_time)
            else:
                logger.error(f"操作最终失败: {e}")
                raise

def get_session_health_info() -> Dict[str, Any]:
    """获取会话健康信息"""
    try:
        # 获取基本统计
        stats = session_tracker.get_stats()

        # 检查泄漏
        leaks = session_tracker.check_leaks()

        # 健康评估
        health_status = "healthy"
        if len(leaks) > 5:
            health_status = "critical"
        elif len(leaks) > 0 or stats['active_sessions'] > 20:
            health_status = "warning"

        return {
            "stats": stats,
            "leaks": leaks,
            "leak_count": len(leaks),
            "health_status": health_status,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"获取会话健康信息失败: {e}")
        return {"error": str(e)}

def cleanup_leaked_sessions():
    """清理泄漏的会话"""
    try:
        leaks = session_tracker.check_leaks(max_age_seconds=300)  # 5分钟

        if leaks:
            logger.info(f"清理 {len(leaks)} 个泄漏会话")

            # 强制清理跟踪记录
            with session_tracker.lock:
                for leak in leaks:
                    session_id = leak['session_id']
                    if session_id in session_tracker.active_sessions:
                        del session_tracker.active_sessions[session_id]

        return len(leaks)

    except Exception as e:
        logger.error(f"清理泄漏会话失败: {e}")
        return 0

class DatabaseSessionManager:
    """数据库会话管理器"""

    def __init__(self):
        self.cleanup_thread = None
        self.cleanup_running = False

    def start_cleanup_task(self, interval: int = 300):
        """启动会话清理任务"""
        if self.cleanup_running:
            return

        self.cleanup_running = True

        def cleanup_loop():
            while self.cleanup_running:
                try:
                    cleanup_leaked_sessions()
                    time.sleep(interval)
                except Exception as e:
                    logger.error(f"会话清理任务错误: {e}")
                    time.sleep(interval)

        self.cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
        self.cleanup_thread.start()
        logger.info(f"会话清理任务已启动，间隔: {interval}秒")

    def stop_cleanup_task(self):
        """停止会话清理任务"""
        self.cleanup_running = False
        if self.cleanup_thread:
            self.cleanup_thread.join()
        logger.info("会话清理任务已停止")

# 全局会话管理器
session_manager = DatabaseSessionManager()

def initialize_session_management():
    """初始化会话管理"""
    try:
        session_manager.start_cleanup_task(interval=300)  # 5分钟清理一次
        logger.info("数据库会话管理初始化完成")
    except Exception as e:
        logger.error(f"数据库会话管理初始化失败: {e}")

def get_session_tracker() -> SessionTracker:
    """获取会话跟踪器"""
    return session_tracker

def get_session_manager() -> DatabaseSessionManager:
    """获取会话管理器"""
    return session_manager