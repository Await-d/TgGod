#!/usr/bin/env python3
"""
数据库字段检查和修复工具
自动检查并添加缺少的下载进度相关字段
"""
import sqlite3
import logging
from pathlib import Path
from typing import List, Tuple

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 需要添加的字段及其定义
REQUIRED_FIELDS = [
    ("download_progress", "INTEGER DEFAULT 0"),
    ("downloaded_size", "BIGINT DEFAULT 0"),
    ("download_speed", "INTEGER DEFAULT 0"),
    ("estimated_time_remaining", "INTEGER DEFAULT 0"),
    ("download_started_at", "DATETIME"),
    ("media_group_id", "VARCHAR(255)"),  # Telegram媒体组ID
]

# 需要添加到download_tasks表的字段
DOWNLOAD_TASKS_FIELDS = [
    ("date_from", "DATETIME"),
    ("date_to", "DATETIME"),
]

def get_database_path() -> str:
    """获取数据库文件路径"""
    # 检查常见的数据库路径
    possible_paths = [
        "/app/data/tggod.db",  # 生产环境路径
        "./tg_data.db",
        "./tggod.db", 
        "./app.db",
        "./database.db",
        "../tg_data.db",
        "/app/tg_data.db",
    ]
    
    for path in possible_paths:
        if Path(path).exists():
            logger.info(f"找到数据库文件: {path}")
            return path
    
    # 如果都没找到，使用默认路径
    default_path = "./tg_data.db"
    logger.info(f"使用默认数据库路径: {default_path}")
    return default_path

def check_table_exists(cursor: sqlite3.Cursor, table_name: str) -> bool:
    """检查表是否存在"""
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name=?
    """, (table_name,))
    return cursor.fetchone() is not None

def get_table_columns(cursor: sqlite3.Cursor, table_name: str) -> List[str]:
    """获取表的所有列名"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return columns

def check_column_exists(cursor: sqlite3.Cursor, table_name: str, column_name: str) -> bool:
    """检查列是否存在"""
    columns = get_table_columns(cursor, table_name)
    return column_name in columns

def add_column_if_missing(cursor: sqlite3.Cursor, table_name: str, column_name: str, column_def: str) -> bool:
    """添加缺少的列，如果列不存在的话"""
    if not check_column_exists(cursor, table_name, column_name):
        try:
            sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}"
            logger.info(f"添加列: {sql}")
            cursor.execute(sql)
            logger.info(f"✅ 成功添加列: {table_name}.{column_name}")
            return True
        except sqlite3.Error as e:
            logger.error(f"❌ 添加列失败 {table_name}.{column_name}: {e}")
            return False
    else:
        logger.info(f"✓ 列已存在: {table_name}.{column_name}")
        return True

def fix_telegram_messages_table(db_path: str) -> bool:
    """修复telegram_messages表的缺少字段"""
    try:
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查表是否存在
        if not check_table_exists(cursor, "telegram_messages"):
            logger.error("❌ telegram_messages表不存在")
            return False
        
        logger.info("📋 检查telegram_messages表的字段...")
        
        # 显示当前字段
        existing_columns = get_table_columns(cursor, "telegram_messages")
        logger.info(f"当前字段数量: {len(existing_columns)}")
        
        # 检查并添加缺少的字段
        success_count = 0
        for column_name, column_def in REQUIRED_FIELDS:
            if add_column_if_missing(cursor, "telegram_messages", column_name, column_def):
                success_count += 1
        
        # 提交更改
        conn.commit()
        
        # 验证结果
        final_columns = get_table_columns(cursor, "telegram_messages")
        logger.info(f"修复后字段数量: {len(final_columns)}")
        
        # 关闭连接
        conn.close()
        
        if success_count == len(REQUIRED_FIELDS):
            logger.info("🎉 telegram_messages表字段修复完成！")
            return True
        else:
            logger.warning(f"⚠️ 部分字段修复失败 ({success_count}/{len(REQUIRED_FIELDS)})")
            return False
            
    except sqlite3.Error as e:
        logger.error(f"❌ 数据库操作失败: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ 修复过程中发生错误: {e}")
        return False

def fix_download_tasks_table(db_path: str) -> bool:
    """修复download_tasks表的缺少字段"""
    try:
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查表是否存在
        if not check_table_exists(cursor, "download_tasks"):
            logger.error("❌ download_tasks表不存在")
            return False
        
        logger.info("📋 检查download_tasks表的字段...")
        
        # 检查并添加缺少的字段
        success_count = 0
        for column_name, column_def in DOWNLOAD_TASKS_FIELDS:
            if add_column_if_missing(cursor, "download_tasks", column_name, column_def):
                success_count += 1
        
        # 提交更改
        conn.commit()
        conn.close()
        
        if success_count == len(DOWNLOAD_TASKS_FIELDS):
            logger.info("🎉 download_tasks表字段修复完成！")
            return True
        else:
            logger.warning(f"⚠️ 部分字段修复失败 ({success_count}/{len(DOWNLOAD_TASKS_FIELDS)})")
            return False
            
    except sqlite3.Error as e:
        logger.error(f"❌ 数据库操作失败: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ 修复过程中发生错误: {e}")
        return False

def create_download_records_table(db_path: str) -> bool:
    """创建download_records表"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查表是否已存在
        if check_table_exists(cursor, "download_records"):
            logger.info("✓ download_records表已存在")
            conn.close()
            return True
        
        logger.info("📋 创建download_records表...")
        
        # 创建表的SQL
        create_table_sql = """
        CREATE TABLE download_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            file_name VARCHAR(500) NOT NULL,
            local_file_path VARCHAR(1000) NOT NULL,
            file_size INTEGER,
            file_type VARCHAR(50),
            message_id INTEGER NOT NULL,
            sender_id INTEGER,
            sender_name VARCHAR(255),
            message_date DATETIME,
            message_text TEXT,
            download_status VARCHAR(50) DEFAULT 'completed',
            download_progress INTEGER DEFAULT 100,
            error_message TEXT,
            download_started_at DATETIME,
            download_completed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (task_id) REFERENCES download_tasks(id)
        )
        """
        
        cursor.execute(create_table_sql)
        
        # 创建索引
        cursor.execute("CREATE INDEX ix_download_records_id ON download_records(id)")
        
        conn.commit()
        conn.close()
        
        logger.info("🎉 download_records表创建完成！")
        return True
        
    except sqlite3.Error as e:
        logger.error(f"❌ 创建download_records表失败: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ 创建表过程中发生错误: {e}")
        return False

def test_database_access(db_path: str) -> bool:
    """测试数据库访问是否正常"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 测试telegram_messages表
        cursor.execute("""
            SELECT id, download_progress, downloaded_size, download_speed, media_group_id
            FROM telegram_messages 
            LIMIT 1
        """)
        
        # 测试download_records表
        cursor.execute("""
            SELECT COUNT(*) FROM download_records
        """)
        
        # 测试download_tasks表
        cursor.execute("""
            SELECT id, date_from, date_to FROM download_tasks LIMIT 1
        """)
        
        conn.close()
        
        logger.info("✅ 数据库访问测试成功")
        return True
        
    except sqlite3.Error as e:
        logger.error(f"❌ 数据库访问测试失败: {e}")
        return False

def main():
    """主函数"""
    logger.info("🔧 开始完整数据库检查和修复...")
    
    # 获取数据库路径
    db_path = get_database_path()
    
    # 检查数据库文件是否存在
    if not Path(db_path).exists():
        logger.error(f"❌ 数据库文件不存在: {db_path}")
        return False
    
    success_count = 0
    total_tasks = 3
    
    # 1. 修复telegram_messages表字段
    logger.info("1️⃣ 修复telegram_messages表...")
    if fix_telegram_messages_table(db_path):
        success_count += 1
    else:
        logger.error("❌ telegram_messages表修复失败")
    
    # 2. 修复download_tasks表字段
    logger.info("2️⃣ 修复download_tasks表...")
    if fix_download_tasks_table(db_path):
        success_count += 1
    else:
        logger.error("❌ download_tasks表修复失败")
    
    # 3. 创建download_records表
    logger.info("3️⃣ 创建download_records表...")
    if create_download_records_table(db_path):
        success_count += 1
    else:
        logger.error("❌ download_records表创建失败")
    
    # 测试数据库访问
    logger.info("4️⃣ 测试数据库访问...")
    if not test_database_access(db_path):
        logger.error("❌ 数据库访问测试失败")
        return False
    
    if success_count == total_tasks:
        logger.info("🎉 所有数据库修复任务完成！")
        return True
    else:
        logger.warning(f"⚠️ 部分任务失败 ({success_count}/{total_tasks})")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)