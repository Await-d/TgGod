#!/usr/bin/env python3
"""
数据库字段移除脚本：移除filter_rules表中的group_id字段
在应用启动时自动运行
"""
import os
import sys
import sqlite3
import logging
from pathlib import Path

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_database_path():
    """获取数据库路径"""
    possible_paths = [
        "/app/data/tggod.db",
        "./data/tggod.db",
        "../data/tggod.db",
        "data/tggod.db"
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    return None

def check_and_remove_group_id_field():
    """检查并移除filter_rules表中的group_id字段"""
    db_path = get_database_path()
    if not db_path:
        logger.warning("未找到数据库文件，跳过group_id字段移除")
        return
    
    logger.info(f"检查数据库: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 检查filter_rules表是否存在
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='filter_rules'
        """)
        if not cursor.fetchone():
            logger.info("filter_rules表不存在，跳过字段移除")
            return
        
        # 检查group_id字段是否存在
        cursor.execute("PRAGMA table_info(filter_rules)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if 'group_id' not in column_names:
            logger.info("✅ group_id字段已不存在，无需移除")
            return
        
        logger.info("🔧 发现group_id字段，开始移除...")
        
        # 开始事务
        cursor.execute("BEGIN TRANSACTION")
        
        # 创建新表（不包含group_id）
        cursor.execute("""
            CREATE TABLE filter_rules_new (
                id INTEGER PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                keywords JSON,
                exclude_keywords JSON,
                sender_filter JSON,
                media_types JSON,
                date_from DATETIME,
                date_to DATETIME,
                min_views INTEGER,
                max_views INTEGER,
                min_file_size INTEGER,
                max_file_size INTEGER,
                include_forwarded BOOLEAN DEFAULT 1,
                is_active BOOLEAN DEFAULT 1,
                last_sync_time DATETIME,
                last_sync_message_count INTEGER DEFAULT 0,
                sync_status VARCHAR(20) DEFAULT 'pending',
                needs_full_resync BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME
            )
        """)
        
        # 复制数据（排除group_id）
        non_group_id_columns = [col for col in column_names if col != 'group_id']
        columns_str = ', '.join(non_group_id_columns)
        
        cursor.execute(f"""
            INSERT INTO filter_rules_new ({columns_str})
            SELECT {columns_str} FROM filter_rules
        """)
        
        # 获取复制的记录数
        cursor.execute("SELECT COUNT(*) FROM filter_rules_new")
        record_count = cursor.fetchone()[0]
        
        # 删除旧表
        cursor.execute("DROP TABLE filter_rules")
        
        # 重命名新表
        cursor.execute("ALTER TABLE filter_rules_new RENAME TO filter_rules")
        
        # 提交事务
        conn.commit()
        
        logger.info(f"✅ 成功移除group_id字段，保留 {record_count} 条记录")
        
        # 验证结果
        cursor.execute("PRAGMA table_info(filter_rules)")
        new_columns = cursor.fetchall()
        logger.info(f"当前表结构: {len(new_columns)} 个字段")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"❌ 移除group_id字段失败: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    try:
        check_and_remove_group_id_field()
        logger.info("🎉 group_id字段移除脚本执行完成")
    except Exception as e:
        logger.error(f"💥 脚本执行失败: {e}")
        sys.exit(1)