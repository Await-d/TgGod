"""
迁移脚本：添加用户设置表
"""
import sqlite3
import os
import json
from typing import Tuple, Optional
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_database_path() -> str:
    """获取数据库路径"""
    # 尝试从环境变量获取数据库路径
    database_url = os.environ.get("DATABASE_URL", "sqlite:////app/data/tggod.db")
    
    # 如果是SQLite数据库，提取路径
    if database_url.startswith("sqlite:///"):
        return database_url.replace("sqlite:///", "")
    
    # 如果不是SQLite，记录警告并使用默认路径
    logger.warning(f"不支持的数据库类型: {database_url}，将使用默认SQLite数据库")
    return "/app/data/tggod.db"

def run_migration() -> Tuple[bool, str]:
    """
    运行迁移脚本，添加用户设置表
    
    Returns:
        (是否成功, 消息)
    """
    try:
        # 获取数据库路径
        db_path = get_database_path()
        logger.info(f"数据库路径: {db_path}")
        
        # 确保数据库目录存在
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查表是否已存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_settings'")
        table_exists = cursor.fetchone() is not None
        
        if table_exists:
            logger.info("用户设置表已存在，检查字段...")
            
            # 检查表结构
            cursor.execute("PRAGMA table_info(user_settings)")
            columns = {row[1] for row in cursor.fetchall()}
            required_columns = {'id', 'user_id', 'settings_data', 'created_at', 'updated_at'}
            
            missing_columns = required_columns - columns
            
            if missing_columns:
                # 添加缺失字段
                for column in missing_columns:
                    try:
                        if column == 'created_at':
                            cursor.execute(
                                "ALTER TABLE user_settings ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
                            )
                        elif column == 'updated_at':
                            cursor.execute(
                                "ALTER TABLE user_settings ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
                            )
                        elif column == 'settings_data':
                            cursor.execute(
                                "ALTER TABLE user_settings ADD COLUMN settings_data TEXT NOT NULL DEFAULT '{}'"
                            )
                    except sqlite3.OperationalError as e:
                        if 'duplicate column name' in str(e).lower():
                            logger.warning(f"列 {column} 已存在")
                        else:
                            raise
                            
                conn.commit()
                return True, f"用户设置表已修复，添加了字段: {', '.join(missing_columns)}"
            
            return True, "用户设置表结构正确"
        
        # 创建表
        logger.info("创建用户设置表...")
        cursor.execute("""
            CREATE TABLE user_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                settings_data TEXT NOT NULL DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        
        # 创建唯一索引
        logger.info("创建用户设置表索引...")
        cursor.execute("""
            CREATE UNIQUE INDEX idx_user_settings_user_id ON user_settings(user_id)
        """)
        
        # 为每个用户创建默认设置
        logger.info("为现有用户创建默认设置...")
        cursor.execute("SELECT id FROM users")
        users = cursor.fetchall()
        
        # 默认设置
        default_settings = {
            "language": "zh_CN",
            "theme": "system",
            "notificationEnabled": True,
            "autoDownload": False,
            "autoDownloadMaxSize": 10,
            "thumbnailsEnabled": True,
            "timezone": "Asia/Shanghai",
            "dateFormat": "YYYY-MM-DD HH:mm",
            "defaultDownloadPath": "downloads",
            "displayDensity": "default",
            "previewFilesInline": True,
            "defaultPageSize": 20,
            "developerMode": False
        }
        
        default_settings_json = json.dumps(default_settings)
        
        for user_id, in users:
            cursor.execute(
                "INSERT INTO user_settings (user_id, settings_data) VALUES (?, ?)",
                (user_id, default_settings_json)
            )
        
        # 提交更改并关闭连接
        conn.commit()
        conn.close()
        
        return True, f"用户设置表创建成功，并为 {len(users)} 个用户添加了默认设置"
    except Exception as e:
        logger.error(f"创建用户设置表时出错: {e}")
        return False, str(e)


if __name__ == "__main__":
    success, message = run_migration()
    if success:
        print(f"✅ 迁移成功: {message}")
    else:
        print(f"❌ 迁移失败: {message}")