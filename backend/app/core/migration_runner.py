"""
数据库迁移运行器
支持SQLite的完整DDL操作，包括DROP COLUMN
"""
import os
import sys
import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
from datetime import datetime
import importlib.util
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.engine import Engine

from .sqlite_migration_manager import SQLiteMigrationManager, SQLiteMigrationProgressReporter

logger = logging.getLogger(__name__)

class MigrationRunner:
    """数据库迁移运行器"""
    
    def __init__(self, database_url: str, migrations_dir: str, websocket_manager=None):
        self.database_url = database_url
        self.migrations_dir = Path(migrations_dir)
        self.engine = create_engine(database_url, echo=False)
        self.sqlite_manager = SQLiteMigrationManager(database_url)
        self.progress_reporter = SQLiteMigrationProgressReporter(websocket_manager)
        self.applied_migrations = set()
        self._init_migration_table()
    
    def _init_migration_table(self):
        """初始化迁移跟踪表"""
        try:
            with self.engine.connect() as conn:
                # 创建迁移历史表
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS migration_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        filename VARCHAR(255) UNIQUE NOT NULL,
                        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        success BOOLEAN DEFAULT TRUE,
                        error_message TEXT,
                        rollback_info TEXT
                    )
                """))
                conn.commit()
                
                # 加载已应用的迁移
                result = conn.execute(text(
                    "SELECT filename FROM migration_history WHERE success = TRUE"
                ))
                self.applied_migrations = {row[0] for row in result}
                
        except Exception as e:
            logger.error(f"❌ 初始化迁移跟踪表失败: {e}")
            raise
    
    def get_pending_migrations(self) -> List[Path]:
        """获取待应用的迁移文件"""
        try:
            migration_files = []
            
            for file_path in self.migrations_dir.glob("*.py"):
                if file_path.name == "__init__.py":
                    continue
                
                if file_path.name not in self.applied_migrations:
                    migration_files.append(file_path)
            
            # 按文件名排序确保执行顺序
            migration_files.sort(key=lambda f: f.name)
            
            logger.info(f"🔍 发现 {len(migration_files)} 个待应用的迁移")
            
            return migration_files
            
        except Exception as e:
            logger.error(f"❌ 获取迁移文件失败: {e}")
            return []
    
    def load_migration_module(self, migration_file: Path):
        """动态加载迁移模块"""
        try:
            spec = importlib.util.spec_from_file_location(
                migration_file.stem,
                migration_file
            )
            
            if spec is None or spec.loader is None:
                raise Exception(f"无法加载迁移文件: {migration_file}")
            
            module = importlib.util.module_from_spec(spec)
            
            # 设置模块的全局变量
            module.engine = self.engine
            module.migration_manager = self.sqlite_manager
            
            spec.loader.exec_module(module)
            
            return module
            
        except Exception as e:
            logger.error(f"❌ 加载迁移模块失败 {migration_file}: {e}")
            raise
    
    async def run_migration(self, migration_file: Path) -> bool:
        """运行单个迁移"""
        try:
            await self.progress_reporter.report_progress(
                f"应用迁移: {migration_file.name}",
                0,
                "加载迁移文件..."
            )
            
            # 加载迁移模块
            module = self.load_migration_module(migration_file)
            
            # 检查必需的函数
            if not hasattr(module, 'upgrade'):
                raise Exception(f"迁移文件 {migration_file.name} 缺少 upgrade 函数")
            
            await self.progress_reporter.report_progress(
                f"应用迁移: {migration_file.name}",
                25,
                "执行迁移..."
            )
            
            # 创建备份
            backup_path = self.sqlite_manager.create_backup(f"migration_{migration_file.stem}")
            
            await self.progress_reporter.report_progress(
                f"应用迁移: {migration_file.name}",
                50,
                "备份完成，正在应用更改..."
            )
            
            try:
                # 执行迁移
                module.upgrade()
                
                await self.progress_reporter.report_progress(
                    f"应用迁移: {migration_file.name}",
                    75,
                    "记录迁移历史..."
                )
                
                # 记录成功的迁移
                with self.engine.connect() as conn:
                    conn.execute(text("""
                        INSERT INTO migration_history 
                        (filename, applied_at, success, rollback_info)
                        VALUES (:filename, :applied_at, :success, :rollback_info)
                    """), {
                        "filename": migration_file.name,
                        "applied_at": datetime.now(),
                        "success": True,
                        "rollback_info": backup_path
                    })
                    conn.commit()
                
                self.applied_migrations.add(migration_file.name)
                
                await self.progress_reporter.report_progress(
                    f"应用迁移: {migration_file.name}",
                    100,
                    "迁移完成"
                )
                
                logger.info(f"✅ 迁移 {migration_file.name} 应用成功")
                return True
                
            except Exception as e:
                # 迁移失败，从备份恢复
                logger.error(f"❌ 迁移 {migration_file.name} 失败: {e}")
                
                await self.progress_reporter.report_error(
                    f"迁移失败: {migration_file.name}",
                    f"正在从备份恢复: {str(e)}"
                )
                
                # 恢复数据库
                if self.sqlite_manager.restore_from_backup(backup_path):
                    logger.info("✅ 数据库已从备份恢复")
                else:
                    logger.error("❌ 数据库恢复失败")
                
                # 记录失败的迁移
                with self.engine.connect() as conn:
                    conn.execute(text("""
                        INSERT INTO migration_history 
                        (filename, applied_at, success, error_message, rollback_info)
                        VALUES (:filename, :applied_at, :success, :error_message, :rollback_info)
                    """), {
                        "filename": migration_file.name,
                        "applied_at": datetime.now(),
                        "success": False,
                        "error_message": str(e),
                        "rollback_info": backup_path
                    })
                    conn.commit()
                
                raise
                
        except Exception as e:
            logger.error(f"❌ 运行迁移失败 {migration_file.name}: {e}")
            return False
    
    async def rollback_migration(self, migration_file: Path) -> bool:
        """回滚单个迁移"""
        try:
            await self.progress_reporter.report_progress(
                f"回滚迁移: {migration_file.name}",
                0,
                "加载迁移文件..."
            )
            
            # 加载迁移模块
            module = self.load_migration_module(migration_file)
            
            # 检查回滚函数
            if not hasattr(module, 'downgrade'):
                raise Exception(f"迁移文件 {migration_file.name} 缺少 downgrade 函数")
            
            await self.progress_reporter.report_progress(
                f"回滚迁移: {migration_file.name}",
                25,
                "创建回滚备份..."
            )
            
            # 创建回滚前的备份
            backup_path = self.sqlite_manager.create_backup(f"rollback_{migration_file.stem}")
            
            await self.progress_reporter.report_progress(
                f"回滚迁移: {migration_file.name}",
                50,
                "执行回滚操作..."
            )
            
            try:
                # 执行回滚
                module.downgrade()
                
                await self.progress_reporter.report_progress(
                    f"回滚迁移: {migration_file.name}",
                    75,
                    "更新迁移历史..."
                )
                
                # 从应用历史中移除
                with self.engine.connect() as conn:
                    conn.execute(text(
                        "DELETE FROM migration_history WHERE filename = :filename"
                    ), {"filename": migration_file.name})
                    conn.commit()
                
                self.applied_migrations.discard(migration_file.name)
                
                await self.progress_reporter.report_progress(
                    f"回滚迁移: {migration_file.name}",
                    100,
                    "回滚完成"
                )
                
                logger.info(f"✅ 迁移 {migration_file.name} 回滚成功")
                return True
                
            except Exception as e:
                # 回滚失败，恢复到回滚前状态
                logger.error(f"❌ 迁移 {migration_file.name} 回滚失败: {e}")
                
                await self.progress_reporter.report_error(
                    f"回滚失败: {migration_file.name}",
                    f"恢复到回滚前状态: {str(e)}"
                )
                
                self.sqlite_manager.restore_from_backup(backup_path)
                raise
                
        except Exception as e:
            logger.error(f"❌ 回滚迁移失败 {migration_file.name}: {e}")
            return False
    
    async def run_all_migrations(self) -> Dict[str, Any]:
        """运行所有待应用的迁移"""
        try:
            pending_migrations = self.get_pending_migrations()
            
            if not pending_migrations:
                logger.info("✅ 没有需要应用的迁移")
                return {
                    "success": True,
                    "applied_count": 0,
                    "failed_count": 0,
                    "applied_migrations": [],
                    "failed_migrations": []
                }
            
            results = {
                "success": True,
                "applied_count": 0,
                "failed_count": 0,
                "applied_migrations": [],
                "failed_migrations": []
            }
            
            logger.info(f"🚀 开始应用 {len(pending_migrations)} 个迁移...")
            
            for i, migration_file in enumerate(pending_migrations, 1):
                try:
                    logger.info(f"📋 正在应用迁移 {i}/{len(pending_migrations)}: {migration_file.name}")
                    
                    success = await self.run_migration(migration_file)
                    
                    if success:
                        results["applied_count"] += 1
                        results["applied_migrations"].append(migration_file.name)
                    else:
                        results["failed_count"] += 1
                        results["failed_migrations"].append(migration_file.name)
                        results["success"] = False
                        
                        # 是否继续应用后续迁移？这里选择停止
                        logger.error(f"💥 迁移失败，停止后续迁移: {migration_file.name}")
                        break
                        
                except Exception as e:
                    results["failed_count"] += 1
                    results["failed_migrations"].append(migration_file.name)
                    results["success"] = False
                    
                    logger.error(f"💥 迁移异常，停止后续迁移: {migration_file.name}: {e}")
                    break
            
            # 生成最终报告
            await self._generate_migration_report(results)
            
            return results
            
        except Exception as e:
            logger.error(f"❌ 运行迁移过程异常: {e}")
            return {
                "success": False,
                "error": str(e),
                "applied_count": 0,
                "failed_count": 0,
                "applied_migrations": [],
                "failed_migrations": []
            }
    
    async def _generate_migration_report(self, results: Dict[str, Any]):
        """生成迁移报告"""
        logger.info("=" * 50)
        logger.info("📋 数据库迁移完整报告")
        logger.info("=" * 50)
        logger.info(f"✅ 成功应用: {results['applied_count']} 个")
        logger.info(f"❌ 应用失败: {results['failed_count']} 个")
        logger.info("-" * 50)
        
        if results["applied_migrations"]:
            logger.info("成功应用的迁移:")
            for migration in results["applied_migrations"]:
                logger.info(f"  ✅ {migration}")
        
        if results["failed_migrations"]:
            logger.info("失败的迁移:")
            for migration in results["failed_migrations"]:
                logger.info(f"  ❌ {migration}")
        
        logger.info("=" * 50)
        
        # 发送WebSocket通知
        await self.progress_reporter.report_success(
            f"迁移完成: 成功 {results['applied_count']} 个, 失败 {results['failed_count']} 个"
        )
    
    def get_migration_history(self) -> List[Dict[str, Any]]:
        """获取迁移历史"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT filename, applied_at, success, error_message
                    FROM migration_history
                    ORDER BY applied_at DESC
                """))
                
                return [
                    {
                        "filename": row[0],
                        "applied_at": row[1],
                        "success": row[2],
                        "error_message": row[3]
                    }
                    for row in result
                ]
                
        except Exception as e:
            logger.error(f"❌ 获取迁移历史失败: {e}")
            return []


# 便捷函数
async def run_migrations(database_url: str, migrations_dir: str, websocket_manager=None):
    """运行所有待应用的迁移"""
    runner = MigrationRunner(database_url, migrations_dir, websocket_manager)
    return await runner.run_all_migrations()