#!/usr/bin/env python3
"""
数据库健康检查和自动修复脚本
用于监控和修复数据库锁定问题
"""

import os
import sys
import sqlite3
import time
import logging
import asyncio
from pathlib import Path
from typing import Dict, List, Optional

# 添加项目路径
sys.path.append(str(Path(__file__).parent))

from app.utils.db_optimization import optimize_sqlite_database, get_database_stats

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseHealthMonitor:
    """数据库健康监控器"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.health_metrics = {}
        
    def check_database_health(self) -> Dict:
        """检查数据库健康状态"""
        health_report = {
            "status": "healthy",
            "issues": [],
            "recommendations": [],
            "metrics": {}
        }
        
        try:
            # 检查数据库文件
            if not os.path.exists(self.db_path):
                health_report["status"] = "critical"
                health_report["issues"].append("数据库文件不存在")
                return health_report
            
            # 检查文件大小
            file_size = os.path.getsize(self.db_path)
            health_report["metrics"]["file_size_mb"] = round(file_size / 1024 / 1024, 2)
            
            # 检查WAL文件大小
            wal_file = self.db_path + '-wal'
            if os.path.exists(wal_file):
                wal_size = os.path.getsize(wal_file)
                health_report["metrics"]["wal_size_kb"] = round(wal_size / 1024, 2)
                
                # WAL文件过大是性能问题的指标
                if wal_size > 10 * 1024 * 1024:  # 超过10MB
                    health_report["status"] = "warning"
                    health_report["issues"].append("WAL文件过大，可能有长期运行的事务")
                    health_report["recommendations"].append("执行WAL检查点操作")
            
            # 连接数据库进行健康检查
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            cursor = conn.cursor()
            
            # 检查数据库配置
            configs_to_check = {
                'journal_mode': 'WAL',
                'synchronous': 'NORMAL',
                'busy_timeout': '120000'
            }
            
            for config, expected in configs_to_check.items():
                cursor.execute(f"PRAGMA {config};")
                result = cursor.fetchone()
                actual = str(result[0]) if result else 'N/A'
                health_report["metrics"][config] = actual
                
                if actual != expected:
                    health_report["status"] = "warning"
                    health_report["issues"].append(f"{config} 配置不是最优值: {actual} (期望: {expected})")
                    health_report["recommendations"].append(f"设置 {config} 为 {expected}")
            
            # 检查表完整性
            cursor.execute("PRAGMA integrity_check;")
            integrity_result = cursor.fetchone()
            if integrity_result[0] != "ok":
                health_report["status"] = "critical"
                health_report["issues"].append(f"数据库完整性检查失败: {integrity_result[0]}")
                health_report["recommendations"].append("运行数据库修复操作")
            
            # 检查表锁状态（尝试快速写入测试）
            try:
                cursor.execute("BEGIN IMMEDIATE;")
                cursor.execute("ROLLBACK;")
                health_report["metrics"]["write_access"] = "available"
            except sqlite3.OperationalError as e:
                if "locked" in str(e).lower():
                    health_report["status"] = "critical"
                    health_report["issues"].append("数据库被锁定，无法写入")
                    health_report["recommendations"].append("检查并终止长期运行的事务")
                    health_report["metrics"]["write_access"] = "locked"
            
            # 统计表记录数
            tables = ['telegram_messages', 'download_tasks', 'filter_rules', 'task_logs']
            for table in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table};")
                    count = cursor.fetchone()[0]
                    health_report["metrics"][f"{table}_count"] = count
                except sqlite3.Error:
                    health_report["metrics"][f"{table}_count"] = "error"
            
            conn.close()
            
            # 如果有任何问题但不是严重问题，设置为警告状态
            if health_report["issues"] and health_report["status"] == "healthy":
                health_report["status"] = "warning"
                
            return health_report
            
        except Exception as e:
            health_report["status"] = "critical"
            health_report["issues"].append(f"健康检查失败: {str(e)}")
            return health_report
    
    def auto_fix_issues(self, health_report: Dict) -> bool:
        """自动修复发现的问题"""
        if health_report["status"] == "healthy":
            logger.info("数据库健康状态良好，无需修复")
            return True
        
        fixed_issues = []
        
        try:
            # 应用最优配置
            if "配置不是最优值" in str(health_report["issues"]):
                logger.info("应用数据库最优配置...")
                if optimize_sqlite_database(self.db_path):
                    fixed_issues.append("已应用最优数据库配置")
                    
            # 执行WAL检查点
            if "WAL文件过大" in str(health_report["issues"]):
                logger.info("执行WAL检查点操作...")
                conn = sqlite3.connect(self.db_path, timeout=30.0)
                cursor = conn.cursor()
                cursor.execute("PRAGMA wal_checkpoint(FULL);")
                result = cursor.fetchone()
                conn.close()
                fixed_issues.append(f"WAL检查点完成: {result}")
            
            # 清理数据库
            if len(fixed_issues) > 0:
                logger.info("执行数据库清理...")
                conn = sqlite3.connect(self.db_path, timeout=30.0)
                cursor = conn.cursor()
                cursor.execute("VACUUM;")
                conn.close()
                fixed_issues.append("数据库清理完成")
            
            if fixed_issues:
                logger.info(f"修复完成: {', '.join(fixed_issues)}")
                return True
            else:
                logger.warning("没有可以自动修复的问题")
                return False
                
        except Exception as e:
            logger.error(f"自动修复失败: {e}")
            return False

def main():
    """主函数"""
    # 获取数据库路径
    database_url = os.environ.get("DATABASE_URL", "sqlite:////app/data/tggod.db")
    db_path = database_url.replace("sqlite:///", "")
    
    logger.info("=" * 60)
    logger.info("数据库健康检查和自动修复")
    logger.info("=" * 60)
    
    # 创建健康监控器
    monitor = DatabaseHealthMonitor(db_path)
    
    # 执行健康检查
    logger.info("正在执行数据库健康检查...")
    health_report = monitor.check_database_health()
    
    # 显示检查结果
    logger.info(f"数据库状态: {health_report['status'].upper()}")
    
    if health_report["metrics"]:
        logger.info("数据库指标:")
        for key, value in health_report["metrics"].items():
            logger.info(f"  {key}: {value}")
    
    if health_report["issues"]:
        logger.warning("发现问题:")
        for issue in health_report["issues"]:
            logger.warning(f"  - {issue}")
    
    if health_report["recommendations"]:
        logger.info("建议操作:")
        for rec in health_report["recommendations"]:
            logger.info(f"  - {rec}")
    
    # 自动修复
    if health_report["status"] in ["warning", "critical"]:
        logger.info("\n开始自动修复...")
        success = monitor.auto_fix_issues(health_report)
        
        if success:
            # 重新检查
            logger.info("重新检查数据库状态...")
            new_report = monitor.check_database_health()
            logger.info(f"修复后状态: {new_report['status'].upper()}")
        else:
            logger.error("自动修复失败，请手动检查")
    
    logger.info("=" * 60)
    logger.info("健康检查完成")
    logger.info("=" * 60)

if __name__ == "__main__":
    main()