#!/usr/bin/env python3
"""
添加 is_downloading 字段迁移脚本
"""

import sqlite3
import logging
import os
from typing import Tuple

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migration() -> Tuple[bool, str]:
    """添加 is_downloading 字段到 telegram_messages 表"""
    
    # 确定数据库路径
    db_path = '/app/data/tggod.db'
    if not os.path.exists(db_path):
        # 尝试其他可能的路径
        db_path = os.path.join(os.path.dirname(__file__), '..', 'tggod.db')
        if not os.path.exists(db_path):
            db_path = os.path.join(os.path.dirname(__file__), '..', '..', 'tggod.db')
    
    logger.info(f"数据库路径: {db_path}")
    
    if not os.path.exists(db_path):
        error_msg = f"数据库文件不存在: {db_path}"
        logger.error(error_msg)
        return False, error_msg
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='telegram_messages'")
        if not cursor.fetchone():
            error_msg = "telegram_messages 表不存在"
            logger.error(error_msg)
            return False, error_msg
        
        # 获取当前表结构
        cursor.execute("PRAGMA table_info(telegram_messages)")
        columns = [row[1] for row in cursor.fetchall()]
        logger.info(f"当前 telegram_messages 表字段: {columns}")
        
        # 需要添加的字段
        field_name = "is_downloading"
        field_type = "BOOLEAN DEFAULT 0"
        
        if field_name not in columns:
            try:
                logger.info(f"添加字段: {field_name} ({field_type})")
                cursor.execute(f"ALTER TABLE telegram_messages ADD COLUMN {field_name} {field_type}")
                
                # 重置任何可能正在下载中的状态
                cursor.execute(
                    "UPDATE telegram_messages SET is_downloading = 0 "
                    "WHERE download_progress > 0 AND download_progress < 100 AND media_downloaded = 0"
                )
                
                # 提交更改
                conn.commit()
                
                success_msg = f"成功添加字段: {field_name}"
                logger.info(success_msg)
            except sqlite3.Error as e:
                error_msg = f"添加字段 {field_name} 失败: {e}"
                logger.error(error_msg)
                return False, error_msg
        else:
            success_msg = f"✓ 字段已存在: {field_name}"
            logger.info(success_msg)
        
        # 验证字段是否添加成功
        cursor.execute("PRAGMA table_info(telegram_messages)")
        new_columns = [row[1] for row in cursor.fetchall()]
        logger.info(f"更新后 telegram_messages 表字段: {new_columns}")
        
        return True, success_msg
        
    except Exception as e:
        error_msg = f"迁移失败: {e}"
        logger.error(error_msg)
        return False, error_msg
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    logger.info("开始添加 is_downloading 字段...")
    success, message = run_migration()
    if success:
        logger.info(f"✅ 迁移完成: {message}")
    else:
        logger.error(f"❌ 迁移失败: {message}")