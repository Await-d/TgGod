"""
数据库工具模块 - 提供数据库检查和自动修复功能
"""
import logging
from sqlalchemy import inspect
from sqlalchemy.orm import Session

# 配置日志
logger = logging.getLogger(__name__)

class DatabaseChecker:
    """数据库检查器，用于检查数据库表结构并自动修复"""
    
    def __init__(self, db: Session):
        self.db = db
        self.inspector = inspect(db.bind)
    
    def check_table_exists(self, table_name: str) -> bool:
        """检查表是否存在"""
        return table_name in self.inspector.get_table_names()
    
    def run_migration_if_needed(self, table_name: str, migration_function) -> bool:
        """如果表不存在，运行迁移函数"""
        if not self.check_table_exists(table_name):
            logger.warning(f"表 {table_name} 不存在，准备运行迁移...")
            
            try:
                # 关闭当前会话，因为迁移函数可能会创建新的连接
                self.db.close()
                
                # 运行迁移函数
                migration_function()
                logger.info(f"表 {table_name} 迁移完成")
                return True
            except Exception as e:
                logger.error(f"表 {table_name} 迁移失败: {e}")
                return False
        else:
            logger.debug(f"表 {table_name} 已存在，无需迁移")
            return False
    
    def check_and_fix_database(self) -> dict:
        """检查并修复数据库"""
        results = {
            "status": "success",
            "message": "数据库检查完成",
            "details": {}
        }
        
        # 检查user_settings表
        try:
            if not self.check_table_exists("user_settings"):
                logger.info("准备创建user_settings表...")
                from ...migrations.add_user_settings_table import run_migration
                success, message = run_migration()
                
                results["details"]["user_settings"] = {
                    "status": "fixed" if success else "error",
                    "message": message
                }
            else:
                results["details"]["user_settings"] = {
                    "status": "ok",
                    "message": "user_settings表已存在"
                }
        except Exception as e:
            logger.error(f"检查user_settings表时出错: {e}")
            results["details"]["user_settings"] = {
                "status": "error",
                "message": str(e)
            }
        
        # 如果有任何表修复失败，更新整体状态
        for table, detail in results["details"].items():
            if detail["status"] == "error":
                results["status"] = "error"
                results["message"] = "数据库检查完成，但存在错误"
                break
        
        return results

def check_and_fix_database_on_startup(db: Session) -> dict:
    """启动时检查并修复数据库"""
    checker = DatabaseChecker(db)
    return checker.check_and_fix_database()