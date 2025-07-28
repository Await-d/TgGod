#!/usr/bin/env python3
"""
数据库字段添加脚本：为filter_rules表添加高级过滤字段
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

def add_advanced_rule_fields():
    """为filter_rules表添加高级过滤字段"""
    db_path = get_database_path()
    if not db_path:
        logger.warning("未找到数据库文件，跳过高级规则字段添加")
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
            logger.info("filter_rules表不存在，跳过字段添加")
            return
        
        # 获取当前表结构
        cursor.execute("PRAGMA table_info(filter_rules)")
        columns = cursor.fetchall()
        existing_columns = [col[1] for col in columns]
        
        # 定义需要添加的新字段
        new_fields = [
            # 视频/音频时长过滤（秒）
            ("min_duration", "INTEGER"),
            ("max_duration", "INTEGER"),
            
            # 视频尺寸过滤（像素）
            ("min_width", "INTEGER"),
            ("max_width", "INTEGER"),
            ("min_height", "INTEGER"),
            ("max_height", "INTEGER"),
            
            # 文本长度过滤（字符数）
            ("min_text_length", "INTEGER"),
            ("max_text_length", "INTEGER"),
            
            # 高级过滤选项
            ("has_urls", "BOOLEAN"),
            ("has_mentions", "BOOLEAN"),
            ("has_hashtags", "BOOLEAN"),
            ("is_reply", "BOOLEAN"),
            ("is_edited", "BOOLEAN"),
            ("is_pinned", "BOOLEAN"),
            
            # 时间相关过滤
            ("message_age_days", "INTEGER"),
            ("exclude_weekends", "BOOLEAN DEFAULT 0"),
            ("time_range_start", "VARCHAR(5)"),  # HH:MM格式
            ("time_range_end", "VARCHAR(5)"),    # HH:MM格式
        ]
        
        # 添加消息表的媒体详细信息字段
        message_fields = [
            ("media_duration", "INTEGER"),
            ("media_width", "INTEGER"),
            ("media_height", "INTEGER"),
            ("media_title", "VARCHAR(255)"),
            ("media_performer", "VARCHAR(255)"),
        ]
        
        # 检查并添加规则表字段
        fields_added = 0
        for field_name, field_type in new_fields:
            if field_name not in existing_columns:
                try:
                    sql = f"ALTER TABLE filter_rules ADD COLUMN {field_name} {field_type}"
                    cursor.execute(sql)
                    logger.info(f"✅ 添加字段: filter_rules.{field_name}")
                    fields_added += 1
                except Exception as e:
                    logger.error(f"❌ 添加字段 {field_name} 失败: {e}")
        
        # 检查并添加消息表字段
        cursor.execute("PRAGMA table_info(telegram_messages)")
        message_columns = cursor.fetchall()
        existing_message_columns = [col[1] for col in message_columns]
        
        message_fields_added = 0
        for field_name, field_type in message_fields:
            if field_name not in existing_message_columns:
                try:
                    sql = f"ALTER TABLE telegram_messages ADD COLUMN {field_name} {field_type}"
                    cursor.execute(sql)
                    logger.info(f"✅ 添加字段: telegram_messages.{field_name}")
                    message_fields_added += 1
                except Exception as e:
                    logger.error(f"❌ 添加字段 {field_name} 失败: {e}")
        
        conn.commit()
        
        total_added = fields_added + message_fields_added
        if total_added > 0:
            logger.info(f"✅ 成功添加 {total_added} 个新字段")
        else:
            logger.info("✅ 所有高级规则字段已存在，无需添加")
        
        # 验证字段添加结果
        cursor.execute("PRAGMA table_info(filter_rules)")
        final_columns = cursor.fetchall()
        logger.info(f"filter_rules表当前字段数: {len(final_columns)}")
        
        cursor.execute("PRAGMA table_info(telegram_messages)")
        final_message_columns = cursor.fetchall()
        logger.info(f"telegram_messages表当前字段数: {len(final_message_columns)}")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"❌ 添加高级规则字段失败: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    try:
        add_advanced_rule_fields()
        logger.info("🎉 高级规则字段添加脚本执行完成")
    except Exception as e:
        logger.error(f"💥 脚本执行失败: {e}")
        sys.exit(1)