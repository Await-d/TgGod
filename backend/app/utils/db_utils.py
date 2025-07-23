"""
数据库工具模块 - 提供数据库自动检测和修复功能
"""
from sqlalchemy.orm import Session
from sqlalchemy import inspect, text
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

def check_and_fix_database_on_startup(db: Session) -> Dict[str, Any]:
    """
    检查并修复数据库表结构
    
    该函数在应用启动时运行，检查数据库表结构是否符合预期，
    如果不存在则自动创建或修复。
    
    Args:
        db: 数据库会话
    
    Returns:
        包含状态和详细信息的字典
    """
    results = {
        "status": "success",
        "details": {}
    }
    
    # 检查用户设置表是否存在
    try:
        inspector = inspect(db.bind)
        
        # 检查user_settings表
        if 'user_settings' not in inspector.get_table_names():
            logger.info("用户设置表不存在，创建...")
            
            # 创建表
            db.execute(text("""
                CREATE TABLE IF NOT EXISTS user_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    settings_data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """))
            
            # 创建索引
            db.execute(text("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_user_settings_user_id 
                ON user_settings(user_id)
            """))
            
            # 提交更改
            db.commit()
            
            results["details"]["user_settings"] = {
                "status": "fixed",
                "message": "用户设置表已创建"
            }
        else:
            # 表已存在，检查字段
            columns = {c['name'] for c in inspector.get_columns('user_settings')}
            required_columns = {'id', 'user_id', 'settings_data', 'created_at', 'updated_at'}
            
            missing_columns = required_columns - columns
            
            if missing_columns:
                # 添加缺失字段
                for column in missing_columns:
                    if column == 'created_at':
                        db.execute(text(
                            "ALTER TABLE user_settings ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
                        ))
                    elif column == 'updated_at':
                        db.execute(text(
                            "ALTER TABLE user_settings ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
                        ))
                    elif column == 'settings_data':
                        db.execute(text(
                            "ALTER TABLE user_settings ADD COLUMN settings_data TEXT NOT NULL DEFAULT '{}'"
                        ))
                
                db.commit()
                
                results["details"]["user_settings"] = {
                    "status": "fixed",
                    "message": f"用户设置表已修复，添加了字段: {', '.join(missing_columns)}"
                }
            else:
                results["details"]["user_settings"] = {
                    "status": "ok",
                    "message": "用户设置表结构正确"
                }
    except Exception as e:
        logger.error(f"检查用户设置表时出错: {e}")
        results["status"] = "partial"
        results["details"]["user_settings"] = {
            "status": "error",
            "message": f"检查用户设置表失败: {str(e)}"
        }
    
    # 在这里可以添加更多表的检查和修复
    
    return results