#!/usr/bin/env python3
"""
手动添加Jellyfin兼容字段到download_tasks表
用于修复线上数据库结构问题
"""

import sqlite3
import logging
import sys
import os
from pathlib import Path

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_database_path():
    """获取数据库路径"""
    # 尝试多个可能的路径
    possible_paths = [
        "/app/tggod.db",
        "/app/data/tggod.db", 
        "tggod.db",
        "./tggod.db"
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    # 如果都不存在，返回默认路径
    return "/app/tggod.db"

def check_column_exists(cursor, table_name, column_name):
    """检查表中是否存在某列"""
    try:
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
        return column_name in columns
    except Exception as e:
        logger.error(f"检查列 {column_name} 是否存在时出错: {e}")
        return False

def add_jellyfin_fields():
    """添加Jellyfin兼容字段到download_tasks表"""
    db_path = get_database_path()
    logger.info(f"使用数据库路径: {db_path}")
    
    # Jellyfin字段定义
    jellyfin_fields = [
        ("use_jellyfin_structure", "BOOLEAN DEFAULT 0"),
        ("include_metadata", "BOOLEAN DEFAULT 1"),
        ("download_thumbnails", "BOOLEAN DEFAULT 1"),
        ("use_series_structure", "BOOLEAN DEFAULT 0"),
        ("organize_by_date", "BOOLEAN DEFAULT 1"),
        ("max_filename_length", "INTEGER DEFAULT 150"),
        ("thumbnail_size", "VARCHAR(20) DEFAULT '400x300'"),
        ("poster_size", "VARCHAR(20) DEFAULT '600x900'"),
        ("fanart_size", "VARCHAR(20) DEFAULT '1920x1080'")
    ]
    
    try:
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        logger.info("开始检查和添加Jellyfin字段...")
        
        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='download_tasks'")
        if not cursor.fetchone():
            logger.error("download_tasks表不存在，请先创建基础表结构")
            return False
        
        added_fields = []
        existing_fields = []
        
        # 逐个检查并添加字段
        for field_name, field_type in jellyfin_fields:
            if check_column_exists(cursor, "download_tasks", field_name):
                existing_fields.append(field_name)
                logger.info(f"✓ 字段已存在: {field_name}")
            else:
                try:
                    # 添加字段
                    sql = f"ALTER TABLE download_tasks ADD COLUMN {field_name} {field_type}"
                    cursor.execute(sql)
                    added_fields.append(field_name)
                    logger.info(f"✅ 成功添加字段: {field_name}")
                except Exception as e:
                    logger.error(f"❌ 添加字段 {field_name} 失败: {e}")
                    return False
        
        # 提交更改
        conn.commit()
        
        # 总结
        logger.info("="*50)
        logger.info("Jellyfin字段修复完成！")
        logger.info(f"已存在字段: {len(existing_fields)} 个")
        logger.info(f"新添加字段: {len(added_fields)} 个")
        
        if existing_fields:
            logger.info(f"已存在的字段: {', '.join(existing_fields)}")
        if added_fields:
            logger.info(f"新添加的字段: {', '.join(added_fields)}")
        
        logger.info("="*50)
        
        return True
        
    except Exception as e:
        logger.error(f"数据库操作失败: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def verify_fields():
    """验证Jellyfin字段是否正确添加"""
    db_path = get_database_path()
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 获取表结构
        cursor.execute("PRAGMA table_info(download_tasks)")
        columns = cursor.fetchall()
        
        logger.info("download_tasks表当前结构:")
        for col in columns:
            logger.info(f"  {col[1]} ({col[2]})" + (f" DEFAULT {col[4]}" if col[4] else ""))
        
        return True
        
    except Exception as e:
        logger.error(f"验证字段失败: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    logger.info("开始修复Jellyfin字段...")
    
    # 添加字段
    success = add_jellyfin_fields()
    
    if success:
        logger.info("字段添加成功，开始验证...")
        verify_fields()
        logger.info("修复完成！现在可以重启应用。")
        sys.exit(0)
    else:
        logger.error("修复失败，请检查错误信息")
        sys.exit(1)