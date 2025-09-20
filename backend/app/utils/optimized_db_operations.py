"""优化的高频数据库操作

重构常见的高频数据库操作，使用连接池监控和增强的会话管理来提升性能。

主要优化:
- 使用批量操作减少连接使用
- 应用增强的会话管理
- 实现查询缓存
- 优化事务管理
- 减少连接持有时间

Author: TgGod Team
Version: 1.0.0
"""

import time
import logging
from typing import List, Dict, Any, Optional, Callable, Union
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text, and_, or_
from functools import wraps

from ..utils.enhanced_db_session import enhanced_db_session, batch_db_session, execute_with_session_retry
from ..services.connection_pool_monitor import get_pool_monitor
from ..models.rule import DownloadTask, TelegramGroup, TelegramMessage, FilterRule

logger = logging.getLogger(__name__)

def monitor_db_operation(operation_name: str):
    """数据库操作监控装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            monitor = get_pool_monitor()

            try:
                result = func(*args, **kwargs)

                # 记录成功的操作时间
                operation_time = time.time() - start_time
                monitor.record_query_time(operation_time)

                if operation_time > 1.0:  # 记录慢操作
                    logger.warning(f"慢数据库操作 {operation_name}: {operation_time:.2f}秒")

                return result

            except Exception as e:
                # 记录错误
                monitor.record_connection_error()
                logger.error(f"数据库操作失败 {operation_name}: {e}")
                raise

        return wrapper
    return decorator

class OptimizedDbOperations:
    """优化的数据库操作类"""

    @staticmethod
    @monitor_db_operation("batch_create_tasks")
    def batch_create_tasks(tasks_data: List[Dict[str, Any]]) -> List[int]:
        """批量创建下载任务

        Args:
            tasks_data: 任务数据列表

        Returns:
            创建的任务ID列表
        """
        if not tasks_data:
            return []

        def create_tasks_operation(session: Session) -> List[int]:
            task_ids = []

            for task_data in tasks_data:
                task = DownloadTask(
                    name=task_data.get('name'),
                    group_id=task_data.get('group_id'),
                    status='pending',
                    created_at=datetime.now(),
                    **{k: v for k, v in task_data.items() if k not in ['name', 'group_id']}
                )
                session.add(task)
                session.flush()  # 获取ID但不提交
                task_ids.append(task.id)

            return task_ids

        return execute_with_session_retry(
            create_tasks_operation,
            max_retries=3,
            context="batch_create_tasks"
        )

    @staticmethod
    @monitor_db_operation("batch_update_task_status")
    def batch_update_task_status(task_updates: List[Dict[str, Any]]) -> int:
        """批量更新任务状态

        Args:
            task_updates: 任务更新数据列表，每个包含task_id和新状态

        Returns:
            更新的任务数量
        """
        if not task_updates:
            return 0

        def update_tasks_operation(session: Session) -> int:
            updated_count = 0

            # 按状态分组以优化查询
            status_groups = {}
            for update in task_updates:
                status = update.get('status')
                if status not in status_groups:
                    status_groups[status] = []
                status_groups[status].append(update)

            # 批量更新每个状态组
            for status, updates in status_groups.items():
                task_ids = [update['task_id'] for update in updates]

                result = session.query(DownloadTask).filter(
                    DownloadTask.id.in_(task_ids)
                ).update(
                    {
                        'status': status,
                        'updated_at': datetime.now()
                    },
                    synchronize_session=False
                )

                updated_count += result

            return updated_count

        return execute_with_session_retry(
            update_tasks_operation,
            max_retries=3,
            context="batch_update_task_status"
        )

    @staticmethod
    @monitor_db_operation("get_pending_tasks_optimized")
    def get_pending_tasks_optimized(limit: int = 100, group_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """优化的获取待处理任务列表

        Args:
            limit: 限制返回数量
            group_id: 可选的群组ID过滤

        Returns:
            任务数据列表
        """
        def get_tasks_operation(session: Session) -> List[Dict[str, Any]]:
            query = session.query(DownloadTask).filter(
                DownloadTask.status == 'pending'
            )

            if group_id:
                query = query.filter(DownloadTask.group_id == group_id)

            # 优化查询：只获取需要的字段
            tasks = query.with_entities(
                DownloadTask.id,
                DownloadTask.name,
                DownloadTask.group_id,
                DownloadTask.status,
                DownloadTask.created_at,
                DownloadTask.priority
            ).order_by(DownloadTask.priority.desc(), DownloadTask.created_at).limit(limit).all()

            return [
                {
                    'id': task.id,
                    'name': task.name,
                    'group_id': task.group_id,
                    'status': task.status,
                    'created_at': task.created_at.isoformat() if task.created_at else None,
                    'priority': task.priority
                }
                for task in tasks
            ]

        return execute_with_session_retry(
            get_tasks_operation,
            max_retries=2,
            context="get_pending_tasks"
        )

    @staticmethod
    @monitor_db_operation("bulk_insert_messages")
    def bulk_insert_messages(messages_data: List[Dict[str, Any]]) -> int:
        """批量插入消息记录

        Args:
            messages_data: 消息数据列表

        Returns:
            插入的消息数量
        """
        if not messages_data:
            return 0

        def insert_messages_operation(session: Session) -> int:
            # 使用批量插入优化
            messages = []
            for msg_data in messages_data:
                message = TelegramMessage(
                    group_id=msg_data.get('group_id'),
                    message_id=msg_data.get('message_id'),
                    content=msg_data.get('content'),
                    media_type=msg_data.get('media_type'),
                    file_path=msg_data.get('file_path'),
                    created_at=datetime.now(),
                    **{k: v for k, v in msg_data.items()
                       if k not in ['group_id', 'message_id', 'content', 'media_type', 'file_path']}
                )
                messages.append(message)

            # 批量添加
            session.add_all(messages)
            session.flush()

            return len(messages)

        return execute_with_session_retry(
            insert_messages_operation,
            max_retries=3,
            context="bulk_insert_messages"
        )

    @staticmethod
    @monitor_db_operation("get_group_stats_optimized")
    def get_group_stats_optimized(group_ids: List[int]) -> Dict[int, Dict[str, Any]]:
        """优化的群组统计查询

        Args:
            group_ids: 群组ID列表

        Returns:
            群组统计数据字典
        """
        if not group_ids:
            return {}

        def get_stats_operation(session: Session) -> Dict[int, Dict[str, Any]]:
            stats = {}

            # 一次性查询所有群组的消息统计
            message_stats = session.query(
                TelegramMessage.group_id,
                session.query().from_statement(text("""
                    SELECT
                        group_id,
                        COUNT(*) as total_messages,
                        COUNT(CASE WHEN media_type IS NOT NULL THEN 1 END) as media_messages,
                        MIN(created_at) as first_message_date,
                        MAX(created_at) as last_message_date
                    FROM telegram_messages
                    WHERE group_id IN :group_ids
                    GROUP BY group_id
                """)).params(group_ids=tuple(group_ids))
            ).all()

            # 一次性查询所有群组的任务统计
            task_stats = session.query(
                DownloadTask.group_id,
                session.query().from_statement(text("""
                    SELECT
                        group_id,
                        COUNT(*) as total_tasks,
                        COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_tasks,
                        COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_tasks,
                        COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_tasks
                    FROM download_tasks
                    WHERE group_id IN :group_ids
                    GROUP BY group_id
                """)).params(group_ids=tuple(group_ids))
            ).all()

            # 组装统计数据
            for group_id in group_ids:
                stats[group_id] = {
                    'total_messages': 0,
                    'media_messages': 0,
                    'total_tasks': 0,
                    'completed_tasks': 0,
                    'pending_tasks': 0,
                    'failed_tasks': 0,
                    'first_message_date': None,
                    'last_message_date': None
                }

            # 填充消息统计
            for stat in message_stats:
                if hasattr(stat, 'group_id'):
                    stats[stat.group_id].update({
                        'total_messages': stat.total_messages,
                        'media_messages': stat.media_messages,
                        'first_message_date': stat.first_message_date.isoformat() if stat.first_message_date else None,
                        'last_message_date': stat.last_message_date.isoformat() if stat.last_message_date else None
                    })

            # 填充任务统计
            for stat in task_stats:
                if hasattr(stat, 'group_id'):
                    stats[stat.group_id].update({
                        'total_tasks': stat.total_tasks,
                        'completed_tasks': stat.completed_tasks,
                        'pending_tasks': stat.pending_tasks,
                        'failed_tasks': stat.failed_tasks
                    })

            return stats

        return execute_with_session_retry(
            get_stats_operation,
            max_retries=2,
            context="get_group_stats"
        )

    @staticmethod
    @monitor_db_operation("cleanup_old_records")
    def cleanup_old_records(days_to_keep: int = 30) -> Dict[str, int]:
        """清理旧记录

        Args:
            days_to_keep: 保留天数

        Returns:
            清理统计信息
        """
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)

        def cleanup_operation(session: Session) -> Dict[str, int]:
            cleanup_stats = {
                'deleted_messages': 0,
                'deleted_tasks': 0,
                'deleted_logs': 0
            }

            # 清理旧消息记录
            deleted_messages = session.query(TelegramMessage).filter(
                TelegramMessage.created_at < cutoff_date,
                TelegramMessage.is_downloaded == True  # 只删除已下载的
            ).delete(synchronize_session=False)
            cleanup_stats['deleted_messages'] = deleted_messages

            # 清理已完成的旧任务
            deleted_tasks = session.query(DownloadTask).filter(
                DownloadTask.created_at < cutoff_date,
                DownloadTask.status.in_(['completed', 'failed'])
            ).delete(synchronize_session=False)
            cleanup_stats['deleted_tasks'] = deleted_tasks

            return cleanup_stats

        return execute_with_session_retry(
            cleanup_operation,
            max_retries=3,
            context="cleanup_old_records"
        )

    @staticmethod
    @monitor_db_operation("optimized_search_messages")
    def optimized_search_messages(
        search_params: Dict[str, Any],
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """优化的消息搜索

        Args:
            search_params: 搜索参数
            limit: 限制返回数量
            offset: 偏移量

        Returns:
            搜索结果和总数
        """
        def search_operation(session: Session) -> Dict[str, Any]:
            # 构建基础查询
            query = session.query(TelegramMessage)

            # 应用搜索条件
            if search_params.get('group_id'):
                query = query.filter(TelegramMessage.group_id == search_params['group_id'])

            if search_params.get('media_type'):
                query = query.filter(TelegramMessage.media_type == search_params['media_type'])

            if search_params.get('content_search'):
                query = query.filter(
                    TelegramMessage.content.contains(search_params['content_search'])
                )

            if search_params.get('date_from'):
                query = query.filter(TelegramMessage.created_at >= search_params['date_from'])

            if search_params.get('date_to'):
                query = query.filter(TelegramMessage.created_at <= search_params['date_to'])

            # 获取总数（优化：使用count查询）
            total_count = query.count()

            # 获取分页结果
            messages = query.order_by(TelegramMessage.created_at.desc()).offset(offset).limit(limit).all()

            return {
                'messages': [
                    {
                        'id': msg.id,
                        'group_id': msg.group_id,
                        'message_id': msg.message_id,
                        'content': msg.content[:100] + '...' if msg.content and len(msg.content) > 100 else msg.content,
                        'media_type': msg.media_type,
                        'file_path': msg.file_path,
                        'created_at': msg.created_at.isoformat() if msg.created_at else None,
                        'is_downloaded': msg.is_downloaded
                    }
                    for msg in messages
                ],
                'total_count': total_count,
                'has_more': total_count > offset + limit
            }

        return execute_with_session_retry(
            search_operation,
            max_retries=2,
            context="optimized_search_messages"
        )

# 高频操作的缓存装饰器
class QueryCache:
    """简单的查询缓存"""

    def __init__(self, ttl_seconds: int = 300):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl_seconds = ttl_seconds

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if key in self.cache:
            cached_data = self.cache[key]
            if time.time() - cached_data['timestamp'] < self.ttl_seconds:
                return cached_data['data']
            else:
                del self.cache[key]
        return None

    def set(self, key: str, data: Any):
        """设置缓存值"""
        self.cache[key] = {
            'data': data,
            'timestamp': time.time()
        }

    def clear(self):
        """清空缓存"""
        self.cache.clear()

# 全局查询缓存实例
query_cache = QueryCache(ttl_seconds=300)  # 5分钟缓存

def with_cache(cache_key_func: Callable[..., str], ttl: int = 300):
    """查询缓存装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = cache_key_func(*args, **kwargs)

            # 尝试从缓存获取
            cached_result = query_cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            query_cache.set(cache_key, result)

            return result
        return wrapper
    return decorator

# 使用示例：带缓存的群组信息查询
@with_cache(lambda group_id: f"group_info_{group_id}", ttl=600)
@monitor_db_operation("get_group_info_cached")
def get_group_info_cached(group_id: int) -> Optional[Dict[str, Any]]:
    """获取群组信息（带缓存）"""
    def get_group_operation(session: Session) -> Optional[Dict[str, Any]]:
        group = session.query(TelegramGroup).filter(
            TelegramGroup.id == group_id
        ).first()

        if not group:
            return None

        return {
            'id': group.id,
            'title': group.title,
            'username': group.username,
            'member_count': group.member_count,
            'is_active': group.is_active,
            'created_at': group.created_at.isoformat() if group.created_at else None
        }

    return execute_with_session_retry(
        get_group_operation,
        max_retries=2,
        context="get_group_info"
    )

# 工具函数
def clear_query_cache():
    """清空查询缓存"""
    query_cache.clear()
    logger.info("查询缓存已清空")

def get_cache_stats() -> Dict[str, Any]:
    """获取缓存统计"""
    return {
        'cache_size': len(query_cache.cache),
        'cache_keys': list(query_cache.cache.keys())
    }