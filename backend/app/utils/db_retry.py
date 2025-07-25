"""
数据库重试工具
用于处理SQLite数据库锁定等并发问题
"""
import time
import logging
from functools import wraps
from typing import Any, Callable
from sqlalchemy.exc import OperationalError

logger = logging.getLogger(__name__)

def db_retry(max_retries: int = 3, delay: float = 0.1, backoff: float = 2.0):
    """
    数据库操作重试装饰器
    
    Args:
        max_retries: 最大重试次数
        delay: 初始延迟时间（秒）
        backoff: 延迟递增倍数
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except OperationalError as e:
                    last_exception = e
                    error_msg = str(e).lower()
                    
                    # 只对特定的数据库错误进行重试
                    if any(error in error_msg for error in ['database is locked', 'timeout', 'busy']):
                        if attempt < max_retries:
                            logger.warning(f"数据库操作失败，{current_delay:.2f}秒后重试 (尝试 {attempt + 1}/{max_retries}): {e}")
                            time.sleep(current_delay)
                            current_delay *= backoff
                            continue
                    
                    # 不是可重试的错误或已达到最大重试次数
                    raise
                except Exception as e:
                    # 非数据库错误，直接抛出
                    raise
            
            # 如果所有重试都失败了
            raise last_exception
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            import asyncio
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except OperationalError as e:
                    last_exception = e
                    error_msg = str(e).lower()
                    
                    # 只对特定的数据库错误进行重试
                    if any(error in error_msg for error in ['database is locked', 'timeout', 'busy']):
                        if attempt < max_retries:
                            logger.warning(f"数据库操作失败，{current_delay:.2f}秒后重试 (尝试 {attempt + 1}/{max_retries}): {e}")
                            await asyncio.sleep(current_delay)
                            current_delay *= backoff
                            continue
                    
                    # 不是可重试的错误或已达到最大重试次数
                    raise
                except Exception as e:
                    # 非数据库错误，直接抛出
                    raise
            
            # 如果所有重试都失败了
            raise last_exception
        
        # 根据函数类型返回相应的包装器
        if hasattr(func, '__code__') and 'await' in func.__code__.co_names:
            return async_wrapper
        else:
            return sync_wrapper
            
    return decorator

def safe_db_operation(operation_func: Callable, *args, **kwargs) -> Any:
    """
    安全执行数据库操作的辅助函数
    """
    @db_retry(max_retries=3, delay=0.1, backoff=2.0)
    def _operation():
        return operation_func(*args, **kwargs)
    
    return _operation()

async def safe_async_db_operation(operation_func: Callable, *args, **kwargs) -> Any:
    """
    安全执行异步数据库操作的辅助函数
    """
    @db_retry(max_retries=3, delay=0.1, backoff=2.0)
    async def _operation():
        return await operation_func(*args, **kwargs)
    
    return await _operation()