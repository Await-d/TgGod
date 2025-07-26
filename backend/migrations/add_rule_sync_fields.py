#!/usr/bin/env python3
"""
添加规则同步跟踪字段迁移脚本
"""

import sqlite3
import logging
import os

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_rule_sync_fields():
    """添加规则同步跟踪字段"""
    
    # 确定数据库路径
    db_path = '/app/data/tggod.db'
    if not os.path.exists(db_path):
        # 尝试其他可能的路径
        db_path = os.path.join(os.path.dirname(__file__), '..', 'tggod.db')
        if not os.path.exists(db_path):
            db_path = os.path.join(os.path.dirname(__file__), '..', '..', 'tggod.db')
    
    logger.info(f"数据库路径: {db_path}")
    
    if not os.path.exists(db_path):
        logger.error(f"数据库文件不存在: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='filter_rules'")
        if not cursor.fetchone():
            logger.error("filter_rules表不存在")
            return False
        
        # 获取当前表结构
        cursor.execute("PRAGMA table_info(filter_rules)")
        columns = [row[1] for row in cursor.fetchall()]
        logger.info(f"当前filter_rules表字段: {columns}")
        
        # 需要添加的字段
        new_fields = [
            ("last_sync_time", "DATETIME"),
            ("last_sync_message_count", "INTEGER DEFAULT 0"),
            ("sync_status", "VARCHAR(20) DEFAULT 'pending'"),
            ("needs_full_resync", "BOOLEAN DEFAULT 1")
        ]
        
        added_fields = []
        for field_name, field_type in new_fields:
            if field_name not in columns:
                try:
                    logger.info(f"添加字段: {field_name} ({field_type})")
                    cursor.execute(f"ALTER TABLE filter_rules ADD COLUMN {field_name} {field_type}")
                    added_fields.append(field_name)
                except sqlite3.Error as e:
                    logger.error(f"添加字段 {field_name} 失败: {e}")
            else:
                logger.info(f"✓ 字段已存在: {field_name}")
        
        # 提交更改
        conn.commit()
        
        if added_fields:
            logger.info(f"成功添加字段: {added_fields}")
        else:
            logger.info("所有字段都已存在，无需添加")
        
        # 验证字段是否添加成功
        cursor.execute("PRAGMA table_info(filter_rules)")
        new_columns = [row[1] for row in cursor.fetchall()]
        logger.info(f"更新后filter_rules表字段: {new_columns}")
        
        return True
        
    except Exception as e:
        logger.error(f"迁移失败: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    logger.info("开始添加规则同步跟踪字段...")
    success = add_rule_sync_fields()
    if success:
        logger.info("✅ 迁移完成")
    else:
        logger.error("❌ 迁移失败")