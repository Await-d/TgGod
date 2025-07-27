#!/usr/bin/env python3
"""
数据库锁定问题诊断和修复工具
针对任务执行过程中的数据库锁定问题进行分析和优化
"""

import sqlite3
import time
import logging
import os
import sys
import asyncio
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent))

from app.utils.db_optimization import optimize_sqlite_database, get_database_stats
from app.database import SessionLocal
from app.models.rule import DownloadTask
from app.models.telegram import TelegramMessage, TelegramGroup
from app.models.log import TaskLog, SystemLog

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseLockAnalyzer:
    """数据库锁定分析器"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        
    def analyze_database_status(self):
        """分析数据库状态"""
        logger.info("=== 数据库状态分析 ===")
        
        try:
            # 检查数据库文件
            if not os.path.exists(self.db_path):
                logger.error(f"数据库文件不存在: {self.db_path}")
                return False
                
            logger.info(f"数据库文件路径: {self.db_path}")
            logger.info(f"数据库文件大小: {os.path.getsize(self.db_path) / 1024 / 1024:.2f} MB")
            
            # 检查数据库配置
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            cursor = conn.cursor()
            
            # 获取当前配置
            configs = [
                'journal_mode', 'synchronous', 'cache_size', 
                'busy_timeout', 'temp_store', 'mmap_size'
            ]
            
            current_config = {}
            for config in configs:
                cursor.execute(f"PRAGMA {config};")
                result = cursor.fetchone()
                current_config[config] = result[0] if result else 'N/A'
            
            logger.info("当前数据库配置:")
            for key, value in current_config.items():
                logger.info(f"  {key}: {value}")
            
            # 检查锁状态
            cursor.execute("BEGIN IMMEDIATE;")
            cursor.execute("ROLLBACK;")
            logger.info("✓ 数据库可正常访问，无锁定状态")
            
            # 检查表统计
            tables = ['telegram_messages', 'download_tasks', 'filter_rules', 'task_logs', 'system_logs']
            for table in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table};")
                    count = cursor.fetchone()[0]
                    logger.info(f"  {table}: {count} 条记录")
                except Exception as e:
                    logger.warning(f"  {table}: 无法统计 ({e})")
            
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"数据库状态分析失败: {e}")
            return False
    
    def analyze_concurrent_usage(self):
        """分析并发使用情况"""
        logger.info("=== 并发使用分析 ===")
        
        try:
            # 模拟多个并发连接
            connections = []
            for i in range(5):
                try:
                    conn = sqlite3.connect(self.db_path, timeout=5.0)
                    connections.append(conn)
                    logger.info(f"连接 {i+1}: 成功")
                except Exception as e:
                    logger.warning(f"连接 {i+1}: 失败 - {e}")
            
            # 测试并发读取
            start_time = time.time()
            for i, conn in enumerate(connections):
                try:
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM telegram_messages;")
                    result = cursor.fetchone()
                    logger.info(f"并发读取 {i+1}: 成功 ({result[0]} 条记录)")
                except Exception as e:
                    logger.warning(f"并发读取 {i+1}: 失败 - {e}")
            
            end_time = time.time()
            logger.info(f"并发测试完成，耗时: {end_time - start_time:.2f} 秒")
            
            # 关闭连接
            for conn in connections:
                try:
                    conn.close()
                except:
                    pass
            
            return True
            
        except Exception as e:
            logger.error(f"并发使用分析失败: {e}")
            return False
    
    def check_long_running_transactions(self):
        """检查长时间运行的事务"""
        logger.info("=== 长时间运行事务检查 ===")
        
        try:
            conn = sqlite3.connect(self.db_path, timeout=5.0)
            cursor = conn.cursor()
            
            # 检查WAL文件大小（如果存在）
            wal_file = self.db_path + '-wal'
            if os.path.exists(wal_file):
                wal_size = os.path.getsize(wal_file)
                logger.info(f"WAL文件大小: {wal_size / 1024:.2f} KB")
                if wal_size > 1024 * 1024:  # 超过1MB
                    logger.warning("WAL文件过大，可能存在长时间运行的事务")
            else:
                logger.info("无WAL文件（可能未启用WAL模式）")
            
            # 检查SHM文件
            shm_file = self.db_path + '-shm'
            if os.path.exists(shm_file):
                logger.info(f"SHM文件存在，大小: {os.path.getsize(shm_file)} bytes")
            
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"长时间运行事务检查失败: {e}")
            return False

class DatabaseLockFixer:
    """数据库锁定修复器"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def apply_optimal_configuration(self):
        """应用最优数据库配置"""
        logger.info("=== 应用最优数据库配置 ===")
        
        try:
            success = optimize_sqlite_database(self.db_path)
            if success:
                logger.info("✓ 数据库配置优化完成")
                
                # 验证配置
                stats = get_database_stats()
                logger.info("优化后的配置:")
                for key, value in stats.items():
                    logger.info(f"  {key}: {value}")
                
                return True
            else:
                logger.error("✗ 数据库配置优化失败")
                return False
                
        except Exception as e:
            logger.error(f"应用最优配置失败: {e}")
            return False
    
    def cleanup_stale_connections(self):
        """清理过期连接"""
        logger.info("=== 清理过期连接 ===")
        
        try:
            # 强制检查点操作（将WAL合并到主数据库）
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            cursor = conn.cursor()
            
            # 执行检查点
            cursor.execute("PRAGMA wal_checkpoint(FULL);")
            result = cursor.fetchone()
            logger.info(f"WAL检查点结果: {result}")
            
            # 清理临时文件
            cursor.execute("VACUUM;")
            logger.info("✓ 数据库清理完成")
            
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"清理过期连接失败: {e}")
            return False
    
    def optimize_task_execution_queries(self):
        """优化任务执行查询"""
        logger.info("=== 优化任务执行查询 ===")
        
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            cursor = conn.cursor()
            
            # 创建索引以优化常用查询
            indexes = [
                ("idx_telegram_messages_group_date", "telegram_messages", "group_id, date"),
                ("idx_telegram_messages_download_status", "telegram_messages", "is_downloaded"),
                ("idx_download_tasks_status", "download_tasks", "status"),
                ("idx_task_logs_task_id", "task_logs", "task_id"),
                ("idx_task_logs_created_at", "task_logs", "created_at"),
            ]
            
            for index_name, table_name, columns in indexes:
                try:
                    cursor.execute(f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} ({columns});")
                    logger.info(f"✓ 创建索引: {index_name}")
                except Exception as e:
                    logger.warning(f"索引创建失败 {index_name}: {e}")
            
            # 更新表统计信息
            cursor.execute("ANALYZE;")
            logger.info("✓ 更新表统计信息完成")
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"优化任务执行查询失败: {e}")
            return False

async def main():
    """主函数"""
    # 获取数据库路径
    database_url = os.environ.get("DATABASE_URL", "sqlite:////app/data/tggod.db")
    db_path = database_url.replace("sqlite:///", "")
    
    logger.info("=" * 60)
    logger.info("数据库锁定问题诊断和修复工具")
    logger.info("=" * 60)
    
    # 初始化分析器和修复器
    analyzer = DatabaseLockAnalyzer(db_path)
    fixer = DatabaseLockFixer(db_path)
    
    # 1. 分析数据库状态
    if not analyzer.analyze_database_status():
        logger.error("数据库状态异常，停止诊断")
        return False
    
    # 2. 分析并发使用情况
    analyzer.analyze_concurrent_usage()
    
    # 3. 检查长时间运行的事务
    analyzer.check_long_running_transactions()
    
    # 4. 应用最优配置
    if not fixer.apply_optimal_configuration():
        logger.error("配置优化失败")
        return False
    
    # 5. 清理过期连接
    if not fixer.cleanup_stale_connections():
        logger.warning("连接清理失败，但可以继续")
    
    # 6. 优化查询
    if not fixer.optimize_task_execution_queries():
        logger.warning("查询优化失败，但可以继续")
    
    logger.info("=" * 60)
    logger.info("诊断和修复完成")
    logger.info("=" * 60)
    
    # 最终验证
    final_stats = get_database_stats()
    logger.info("最终数据库状态:")
    for key, value in final_stats.items():
        logger.info(f"  {key}: {value}")
    
    return True

if __name__ == "__main__":
    asyncio.run(main())