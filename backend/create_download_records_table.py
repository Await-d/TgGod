#!/usr/bin/env python3
"""
直接在线上数据库创建download_records表的脚本
"""
import os
import sys
import sqlite3
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_download_records_table_directly():
    """直接在线上数据库创建download_records表"""
    
    # 检查可能的数据库路径
    possible_paths = [
        "/app/data/tggod.db",  # Docker容器内路径
        "./tggod.db",          # 本地路径
        "/data/tggod.db",      # 备选路径
    ]
    
    db_path = None
    for path in possible_paths:
        if Path(path).exists():
            db_path = path
            logger.info(f"找到数据库文件: {path}")
            break
    
    if not db_path:
        logger.error("未找到数据库文件")
        return False
    
    try:
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查表是否已存在
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='download_records'
        """)
        
        if cursor.fetchone():
            logger.info("✓ download_records表已存在")
            
            # 检查表结构
            cursor.execute("PRAGMA table_info(download_records)")
            columns = cursor.fetchall()
            logger.info(f"表结构: {len(columns)} 个字段")
            for col in columns:
                logger.info(f"  - {col[1]} {col[2]}")
                
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
        cursor.execute("CREATE INDEX ix_download_records_task_id ON download_records(task_id)")
        cursor.execute("CREATE INDEX ix_download_records_completed_at ON download_records(download_completed_at)")
        
        # 提交更改
        conn.commit()
        
        # 验证表创建成功
        cursor.execute("SELECT COUNT(*) FROM download_records")
        count = cursor.fetchone()[0]
        logger.info(f"🎉 download_records表创建成功！当前记录数: {count}")
        
        # 显示所有表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()
        logger.info(f"数据库表列表 ({len(tables)}):")
        for table in tables:
            logger.info(f"  ✓ {table[0]}")
        
        conn.close()
        return True
        
    except sqlite3.Error as e:
        logger.error(f"❌ 数据库操作失败: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ 创建表过程中发生错误: {e}")
        return False

if __name__ == "__main__":
    logger.info("🔧 开始创建download_records表...")
    success = create_download_records_table_directly()
    
    if success:
        logger.info("🎉 任务完成！")
        exit(0)
    else:
        logger.error("❌ 任务失败！")
        exit(1)