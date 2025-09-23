"""
SQLite迁移管理器
专门处理SQLite不支持的DDL操作，如DROP COLUMN
使用表重建策略实现完整的迁移功能
"""
import os
import sqlite3
import logging
import asyncio
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import shutil
import tempfile
import json
from datetime import datetime
from contextlib import contextmanager
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

class SQLiteMigrationManager:
    """SQLite数据库迁移管理器"""
    
    def __init__(self, database_url: str, backup_dir: str = None):
        self.database_url = database_url
        self.database_path = database_url.replace('sqlite:///', '')
        self.backup_dir = Path(backup_dir) if backup_dir else Path(self.database_path).parent / 'backups'
        self.backup_dir.mkdir(exist_ok=True)
        
        # 创建SQLAlchemy引擎
        self.engine = create_engine(database_url, echo=False)
        
        # 迁移状态跟踪
        self.migration_log = []
        self.current_backup = None
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接上下文管理器"""
        connection = self.engine.connect()
        try:
            yield connection
        finally:
            connection.close()
    
    def create_backup(self, suffix: str = None) -> str:
        """创建数据库备份"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        suffix_str = f"_{suffix}" if suffix else ""
        backup_filename = f"tggod_backup_{timestamp}{suffix_str}.db"
        backup_path = self.backup_dir / backup_filename
        
        try:
            # 复制数据库文件
            shutil.copy2(self.database_path, backup_path)
            self.current_backup = str(backup_path)
            
            logger.info(f"📦 数据库备份创建成功: {backup_path}")
            
            # 验证备份完整性
            if self._verify_backup_integrity(backup_path):
                return str(backup_path)
            else:
                raise Exception("备份完整性验证失败")
                
        except Exception as e:
            logger.error(f"❌ 创建数据库备份失败: {e}")
            raise
    
    def _verify_backup_integrity(self, backup_path: Path) -> bool:
        """验证备份文件完整性"""
        try:
            with sqlite3.connect(str(backup_path)) as conn:
                # 执行PRAGMA完整性检查
                result = conn.execute("PRAGMA integrity_check").fetchone()
                is_valid = result and result[0] == "ok"
                
                if is_valid:
                    logger.info("✅ 备份文件完整性验证通过")
                else:
                    logger.error(f"❌ 备份文件完整性验证失败: {result}")
                
                return is_valid
                
        except Exception as e:
            logger.error(f"❌ 备份完整性验证异常: {e}")
            return False
    
    def restore_from_backup(self, backup_path: str = None) -> bool:
        """从备份恢复数据库"""
        try:
            backup_to_restore = backup_path or self.current_backup
            
            if not backup_to_restore or not os.path.exists(backup_to_restore):
                raise Exception("备份文件不存在或未指定")
            
            logger.info(f"🔄 开始从备份恢复数据库: {backup_to_restore}")
            
            # 关闭当前连接
            self.engine.dispose()
            
            # 恢复数据库文件
            shutil.copy2(backup_to_restore, self.database_path)
            
            # 重新创建引擎
            self.engine = create_engine(self.database_url, echo=False)
            
            logger.info("✅ 数据库恢复成功")
            return True
            
        except Exception as e:
            logger.error(f"❌ 数据库恢复失败: {e}")
            return False
    
    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """获取表结构信息"""
        try:
            with self.get_connection() as conn:
                # 获取表的创建SQL
                create_sql_result = conn.execute(text(
                    "SELECT sql FROM sqlite_master WHERE type='table' AND name=:table_name"
                ), {"table_name": table_name}).fetchone()
                
                if not create_sql_result:
                    raise Exception(f"表 {table_name} 不存在")
                
                # 获取列信息
                columns_result = conn.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
                
                # 获取索引信息
                indexes_result = conn.execute(text(
                    "SELECT name, sql FROM sqlite_master WHERE type='index' AND tbl_name=:table_name"
                ), {"table_name": table_name}).fetchall()
                
                # 获取触发器信息
                triggers_result = conn.execute(text(
                    "SELECT name, sql FROM sqlite_master WHERE type='trigger' AND tbl_name=:table_name"
                ), {"table_name": table_name}).fetchall()
                
                return {
                    "create_sql": create_sql_result[0],
                    "columns": [
                        {
                            "cid": row[0],
                            "name": row[1],
                            "type": row[2],
                            "notnull": bool(row[3]),
                            "default_value": row[4],
                            "pk": bool(row[5])
                        }
                        for row in columns_result
                    ],
                    "indexes": [
                        {"name": row[0], "sql": row[1]}
                        for row in indexes_result
                        if row[1]  # 排除自动索引
                    ],
                    "triggers": [
                        {"name": row[0], "sql": row[1]}
                        for row in triggers_result
                    ]
                }
                
        except Exception as e:
            logger.error(f"❌ 获取表结构失败: {e}")
            raise
    
    def rebuild_table_drop_columns(self, table_name: str, columns_to_drop: List[str],
                                   progress_callback=None) -> bool:
        """通过重建表的方式删除列"""
        try:
            logger.info(f"🔧 开始重建表 {table_name}，删除列: {', '.join(columns_to_drop)}")
            
            # 步骤1: 创建备份
            backup_path = self.create_backup(f"drop_columns_{table_name}")
            
            # 步骤2: 获取原表结构
            schema = self.get_table_schema(table_name)
            original_columns = schema["columns"]
            
            # 步骤3: 计算新表的列
            new_columns = [col for col in original_columns if col["name"] not in columns_to_drop]
            
            if len(new_columns) == len(original_columns):
                logger.warning("没有找到需要删除的列")
                return True
            
            # 步骤4: 生成新表的CREATE语句
            new_create_sql = self._generate_new_create_sql(
                table_name, new_columns, schema["create_sql"]
            )
            
            # 步骤5: 执行表重建
            with self.get_connection() as conn:
                # 开始事务
                trans = conn.begin()
                
                try:
                    # 报告进度
                    if progress_callback:
                        try:
                            progress_callback("创建临时表")
                        except Exception as e:
                            logger.warning(f"进度回调失败: {e}")
                    
                    # 创建临时表
                    temp_table_name = f"{table_name}_temp_{int(datetime.now().timestamp())}"
                    temp_create_sql = new_create_sql.replace(table_name, temp_table_name)
                    conn.execute(text(temp_create_sql))
                    
                    # 报告进度
                    if progress_callback:
                        try:
                            progress_callback("复制数据")
                        except Exception as e:
                            logger.warning(f"进度回调失败: {e}")
                    
                    # 复制数据
                    column_names = [col["name"] for col in new_columns]
                    columns_str = ", ".join(column_names)
                    
                    copy_sql = f"""
                        INSERT INTO {temp_table_name} ({columns_str})
                        SELECT {columns_str} FROM {table_name}
                    """
                    
                    conn.execute(text(copy_sql))
                    
                    # 报告进度
                    if progress_callback:
                        try:
                            progress_callback("重建索引")
                        except Exception as e:
                            logger.warning(f"进度回调失败: {e}")
                    
                    # 删除原表
                    conn.execute(text(f"DROP TABLE {table_name}"))
                    
                    # 重命名临时表
                    conn.execute(text(f"ALTER TABLE {temp_table_name} RENAME TO {table_name}"))
                    
                    # 重建索引
                    for index in schema["indexes"]:
                        if index["sql"]:
                            conn.execute(text(index["sql"]))
                    
                    # 重建触发器
                    for trigger in schema["triggers"]:
                        if trigger["sql"]:
                            conn.execute(text(trigger["sql"]))
                    
                    # 提交事务
                    trans.commit()
                    
                    logger.info(f"✅ 表 {table_name} 重建成功，删除了 {len(columns_to_drop)} 个列")
                    
                    # 记录迁移日志
                    self.migration_log.append({
                        "timestamp": datetime.now().isoformat(),
                        "operation": "drop_columns",
                        "table": table_name,
                        "dropped_columns": columns_to_drop,
                        "backup": backup_path,
                        "success": True
                    })
                    
                    return True
                    
                except Exception as e:
                    # 回滚事务
                    trans.rollback()
                    logger.error(f"❌ 表重建失败，正在回滚: {e}")
                    
                    # 从备份恢复
                    self.restore_from_backup(backup_path)
                    
                    # 记录失败日志
                    self.migration_log.append({
                        "timestamp": datetime.now().isoformat(),
                        "operation": "drop_columns",
                        "table": table_name,
                        "dropped_columns": columns_to_drop,
                        "backup": backup_path,
                        "success": False,
                        "error": str(e)
                    })
                    
                    raise
                    
        except Exception as e:
            logger.error(f"❌ 删除列操作失败: {e}")
            return False
    
    def _generate_new_create_sql(self, table_name: str, columns: List[Dict], 
                               original_sql: str) -> str:
        """生成新表的CREATE SQL语句"""
        # 构建列定义
        column_defs = []
        primary_keys = []
        
        for col in columns:
            col_def = f"{col['name']} {col['type']}"
            
            if col["notnull"]:
                col_def += " NOT NULL"
            
            if col["default_value"] is not None:
                col_def += f" DEFAULT {col['default_value']}"
            
            if col["pk"]:
                primary_keys.append(col["name"])
            
            column_defs.append(col_def)
        
        # 添加主键约束
        if primary_keys:
            if len(primary_keys) == 1 and not any("AUTOINCREMENT" in original_sql.upper() for _ in [1]):
                # 单主键，可能需要AUTOINCREMENT
                if "AUTOINCREMENT" in original_sql.upper():
                    column_defs[0] += " PRIMARY KEY AUTOINCREMENT"
                else:
                    column_defs[0] += " PRIMARY KEY"
            else:
                # 复合主键
                column_defs.append(f"PRIMARY KEY ({', '.join(primary_keys)})")
        
        # 构建完整的CREATE语句
        columns_str = ",\n    ".join(column_defs)
        create_sql = f"CREATE TABLE {table_name} (\n    {columns_str}\n)"
        
        return create_sql
    
    def add_columns(self, table_name: str, columns: List[Dict[str, Any]]) -> bool:
        """添加列（SQLite原生支持）"""
        try:
            logger.info(f"🔧 为表 {table_name} 添加列: {[col['name'] for col in columns]}")
            
            # 创建备份
            backup_path = self.create_backup(f"add_columns_{table_name}")
            
            with self.get_connection() as conn:
                for col in columns:
                    col_def = f"{col['name']} {col['type']}"
                    
                    if col.get('not_null', False):
                        col_def += " NOT NULL"
                    
                    if col.get('default') is not None:
                        col_def += f" DEFAULT {col['default']}"
                    
                    add_sql = f"ALTER TABLE {table_name} ADD COLUMN {col_def}"
                    conn.execute(text(add_sql))
                
                conn.commit()
            
            logger.info(f"✅ 成功为表 {table_name} 添加了 {len(columns)} 个列")
            
            # 记录迁移日志
            self.migration_log.append({
                "timestamp": datetime.now().isoformat(),
                "operation": "add_columns",
                "table": table_name,
                "added_columns": [col['name'] for col in columns],
                "backup": backup_path,
                "success": True
            })
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 添加列失败: {e}")
            return False
    
    def rename_column(self, table_name: str, old_name: str, new_name: str) -> bool:
        """重命名列（通过表重建）"""
        try:
            logger.info(f"🔧 重命名表 {table_name} 的列: {old_name} -> {new_name}")
            
            # 创建备份
            backup_path = self.create_backup(f"rename_column_{table_name}")
            
            # 获取表结构
            schema = self.get_table_schema(table_name)
            
            # 修改列名
            new_columns = []
            for col in schema["columns"]:
                if col["name"] == old_name:
                    col = col.copy()
                    col["name"] = new_name
                new_columns.append(col)
            
            # 生成新的CREATE语句
            new_create_sql = self._generate_new_create_sql(
                table_name, new_columns, schema["create_sql"]
            )
            
            with self.get_connection() as conn:
                trans = conn.begin()
                
                try:
                    # 创建临时表
                    temp_table_name = f"{table_name}_temp_{int(datetime.now().timestamp())}"
                    temp_create_sql = new_create_sql.replace(table_name, temp_table_name)
                    conn.execute(text(temp_create_sql))
                    
                    # 复制数据（映射旧列名到新列名）
                    old_columns = [col["name"] for col in schema["columns"]]
                    new_column_names = [col["name"] for col in new_columns]
                    
                    old_columns_str = ", ".join(old_columns)
                    new_columns_str = ", ".join(new_column_names)
                    
                    copy_sql = f"""
                        INSERT INTO {temp_table_name} ({new_columns_str})
                        SELECT {old_columns_str} FROM {table_name}
                    """
                    
                    conn.execute(text(copy_sql))
                    
                    # 删除原表并重命名
                    conn.execute(text(f"DROP TABLE {table_name}"))
                    conn.execute(text(f"ALTER TABLE {temp_table_name} RENAME TO {table_name}"))
                    
                    # 重建索引和触发器（需要更新列名）
                    for index in schema["indexes"]:
                        if index["sql"]:
                            # 替换索引中的旧列名
                            updated_sql = index["sql"].replace(old_name, new_name)
                            conn.execute(text(updated_sql))
                    
                    for trigger in schema["triggers"]:
                        if trigger["sql"]:
                            # 替换触发器中的旧列名
                            updated_sql = trigger["sql"].replace(old_name, new_name)
                            conn.execute(text(updated_sql))
                    
                    trans.commit()
                    
                    logger.info(f"✅ 成功重命名列: {old_name} -> {new_name}")
                    
                    # 记录迁移日志
                    self.migration_log.append({
                        "timestamp": datetime.now().isoformat(),
                        "operation": "rename_column",
                        "table": table_name,
                        "old_name": old_name,
                        "new_name": new_name,
                        "backup": backup_path,
                        "success": True
                    })
                    
                    return True
                    
                except Exception as e:
                    trans.rollback()
                    self.restore_from_backup(backup_path)
                    raise
                    
        except Exception as e:
            logger.error(f"❌ 重命名列失败: {e}")
            return False
    
    def get_migration_history(self) -> List[Dict[str, Any]]:
        """获取迁移历史"""
        return self.migration_log.copy()
    
    def cleanup_old_backups(self, keep_count: int = 10):
        """清理旧备份文件"""
        try:
            backup_files = list(self.backup_dir.glob("tggod_backup_*.db"))
            backup_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            
            if len(backup_files) > keep_count:
                for backup_file in backup_files[keep_count:]:
                    backup_file.unlink()
                    logger.info(f"🗑️ 删除旧备份: {backup_file}")
                    
        except Exception as e:
            logger.warning(f"⚠️ 清理备份文件失败: {e}")


class SQLiteMigrationProgressReporter:
    """SQLite迁移进度报告器"""
    
    def __init__(self, websocket_manager=None):
        self.websocket_manager = websocket_manager
        self.current_operation = ""
        self.progress = 0
    
    async def report_progress(self, operation: str, progress: int = 0, details: str = ""):
        """报告迁移进度"""
        self.current_operation = operation
        self.progress = progress
        
        progress_data = {
            "type": "migration_progress",
            "operation": operation,
            "progress": progress,
            "details": details
        }
        
        logger.info(f"📊 迁移进度: {operation} - {details}")
        
        if self.websocket_manager:
            await self.websocket_manager.broadcast(progress_data)
    
    async def report_error(self, error: str, details: str = ""):
        """报告迁移错误"""
        error_data = {
            "type": "migration_error",
            "error": error,
            "details": details,
            "operation": self.current_operation
        }
        
        logger.error(f"❌ 迁移错误: {error} - {details}")
        
        if self.websocket_manager:
            await self.websocket_manager.broadcast(error_data)
    
    async def report_success(self, message: str):
        """报告迁移成功"""
        success_data = {
            "type": "migration_success",
            "message": message,
            "operation": self.current_operation
        }
        
        logger.info(f"✅ 迁移成功: {message}")
        
        if self.websocket_manager:
            await self.websocket_manager.broadcast(success_data)