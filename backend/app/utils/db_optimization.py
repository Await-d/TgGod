"""
数据库优化工具
专门处理SQLite的并发优化和锁冲突问题
"""
import os
import time
import logging
import sqlite3
from contextlib import contextmanager
from typing import Any, Callable, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError
from ..database import SessionLocal

logger = logging.getLogger(__name__)

def optimize_sqlite_database(db_path: str) -> bool:
    """
    优化SQLite数据库配置，启用WAL模式和其他性能优化
    
    Args:
        db_path: 数据库文件路径
        
    Returns:
        优化是否成功
    """
    try:
        # 直接连接SQLite数据库进行优化配置
        conn = sqlite3.connect(db_path, timeout=30.0)
        cursor = conn.cursor()
        
        # 启用WAL模式以提高并发性能
        cursor.execute("PRAGMA journal_mode=WAL;")
        
        # 设置同步模式为NORMAL（平衡性能和安全性）
        cursor.execute("PRAGMA synchronous=NORMAL;")
        
        # 设置缓存大小 (默认页面大小4KB * 10000 = 40MB)
        cursor.execute("PRAGMA cache_size=10000;")
        
        # 启用外键约束
        cursor.execute("PRAGMA foreign_keys=ON;")
        
        # 设置锁超时 - 更积极的超时设置
        cursor.execute("PRAGMA busy_timeout=120000;")  # 120秒，进一步增加等待时间
        
        # 启用内存映射I/O (提高读性能)
        cursor.execute("PRAGMA mmap_size=536870912;")  # 512MB，提高到512MB
        
        # 设置temp存储为内存
        cursor.execute("PRAGMA temp_store=MEMORY;")
        
        # 验证配置是否生效
        results = []
        for pragma in ['journal_mode', 'synchronous', 'cache_size', 'foreign_keys', 'busy_timeout']:
            cursor.execute(f"PRAGMA {pragma};")
            result = cursor.fetchone()
            results.append((pragma, result[0] if result else 'N/A'))
            
        logger.info("SQLite数据库优化配置:")
        for pragma, value in results:
            logger.info(f"  {pragma}: {value}")
        
        conn.commit()
        conn.close()
        
        logger.info(f"SQLite数据库优化完成: {db_path}")
        return True
        
    except Exception as e:
        logger.error(f"SQLite数据库优化失败: {str(e)}")
        return False

@contextmanager
def optimized_db_session(autocommit: bool = True, max_retries: int = 5):
    """
    优化的数据库会话管理器，带有自动重试和快速释放
    
    Args:
        autocommit: 是否自动提交
        max_retries: 最大重试次数，默认增加到5次
        
    Yields:
        数据库会话
    """
    session = None
    retry_count = 0
    
    while retry_count <= max_retries:
        try:
            session = SessionLocal()
            
            if autocommit:
                # 使用autocommit模式减少锁持有时间
                from sqlalchemy import text
                session.execute(text("BEGIN IMMEDIATE;"))
            
            yield session
            
            if autocommit and session.in_transaction():
                session.commit()
            
            break  # 成功执行，跳出重试循环
            
        except OperationalError as e:
            error_msg = str(e).lower()
            
            if any(keyword in error_msg for keyword in ['database is locked', 'timeout', 'busy']):
                retry_count += 1
                
                if session:
                    try:
                        session.rollback()
                        session.close()
                    except:
                        pass
                    session = None
                
                if retry_count <= max_retries:
                    # 更合理的重试等待时间，考虑数据库busy_timeout
                    if retry_count <= 2:
                        wait_time = 0.5 * retry_count  # 前两次快速重试
                    else:
                        wait_time = min(1.0 * (2 ** (retry_count - 2)), 10.0)  # 后续指数退避，最大10秒
                    
                    logger.warning(f"数据库锁定，{wait_time:.2f}秒后重试 (尝试 {retry_count}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"数据库操作达到最大重试次数: {e}")
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

def batch_database_operation(operations: list, batch_size: int = 50) -> list:
    """
    批量数据库操作，减少锁竞争
    
    Args:
        operations: 操作列表，每个操作是一个可调用对象
        batch_size: 批处理大小
        
    Returns:
        操作结果列表
    """
    results = []
    
    for i in range(0, len(operations), batch_size):
        batch = operations[i:i + batch_size]
        
        with optimized_db_session() as session:
            batch_results = []
            
            for operation in batch:
                try:
                    if callable(operation):
                        result = operation(session)
                        batch_results.append(result)
                    else:
                        logger.warning(f"跳过非可调用操作: {operation}")
                        batch_results.append(None)
                        
                except Exception as e:
                    logger.error(f"批处理操作失败: {str(e)}")
                    batch_results.append(None)
            
            results.extend(batch_results)
            
            # 小延迟让其他连接有机会访问数据库
            time.sleep(0.01)
    
    return results

def get_database_stats() -> dict:
    """
    获取数据库统计信息
    
    Returns:
        数据库统计字典
    """
    try:
        with optimized_db_session(autocommit=False) as session:
            stats = {}
            
            from sqlalchemy import text
            
            # 获取SQLite版本
            result = session.execute(text("SELECT sqlite_version();")).fetchone()
            stats['sqlite_version'] = result[0] if result else 'Unknown'
            
            # 获取数据库配置
            for pragma in ['journal_mode', 'synchronous', 'cache_size', 'foreign_keys', 'busy_timeout']:
                result = session.execute(text(f"PRAGMA {pragma};")).fetchone()
                stats[pragma] = result[0] if result else 'N/A'
            
            # 获取数据库大小信息
            result = session.execute(text("PRAGMA page_size;")).fetchone()
            page_size = result[0] if result else 0
            
            result = session.execute(text("PRAGMA page_count;")).fetchone()
            page_count = result[0] if result else 0
            
            stats['database_size_bytes'] = page_size * page_count
            stats['database_size_mb'] = round((page_size * page_count) / (1024 * 1024), 2)
            
            return stats
            
    except Exception as e:
        logger.error(f"获取数据库统计信息失败: {str(e)}")
        return {'error': str(e)}

def initialize_database_optimization():
    """
    初始化数据库优化设置
    """
    # 获取数据库文件路径
    database_url = os.environ.get("DATABASE_URL", "sqlite:////app/data/tggod.db")
    
    if "sqlite" in database_url:
        # 提取文件路径
        db_path = database_url.replace("sqlite:///", "")
        
        if os.path.exists(db_path):
            logger.info("开始数据库优化初始化...")
            success = optimize_sqlite_database(db_path)
            
            if success:
                stats = get_database_stats()
                logger.info("数据库优化初始化完成")
                logger.info(f"数据库统计: {stats}")
            else:
                logger.warning("数据库优化初始化失败")
        else:
            logger.warning(f"数据库文件不存在: {db_path}")
    else:
        logger.info("非SQLite数据库，跳过优化配置")