#!/usr/bin/env python3
"""
修复规则同步字段问题的脚本
"""

import sqlite3
import logging
import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_rule_sync_fields():
    """修复规则同步字段问题"""
    
    # 数据库路径
    db_path = '/app/data/tggod.db'
    
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
        
        # 获取当前表结构详细信息
        cursor.execute("PRAGMA table_info(filter_rules)")
        columns_info = cursor.fetchall()
        columns = {row[1]: row for row in columns_info}
        
        logger.info("当前filter_rules表结构:")
        for col_name, col_info in columns.items():
            logger.info(f"  {col_name}: {col_info}")
        
        # 需要添加的字段详细定义
        new_fields = [
            {
                'name': 'last_sync_time',
                'type': 'DATETIME',
                'nullable': True,
                'default': None
            },
            {
                'name': 'last_sync_message_count',
                'type': 'INTEGER',
                'nullable': False,
                'default': '0'
            },
            {
                'name': 'sync_status',
                'type': 'VARCHAR(20)',
                'nullable': False,
                'default': "'pending'"
            },
            {
                'name': 'needs_full_resync',
                'type': 'BOOLEAN',
                'nullable': False,
                'default': '1'
            }
        ]
        
        # 检查并添加字段
        added_fields = []
        for field_def in new_fields:
            field_name = field_def['name']
            
            if field_name not in columns:
                # 构建ALTER TABLE语句
                alter_sql = f"ALTER TABLE filter_rules ADD COLUMN {field_name} {field_def['type']}"
                if not field_def['nullable']:
                    alter_sql += " NOT NULL"
                if field_def['default'] is not None:
                    alter_sql += f" DEFAULT {field_def['default']}"
                
                try:
                    logger.info(f"执行SQL: {alter_sql}")
                    cursor.execute(alter_sql)
                    added_fields.append(field_name)
                    logger.info(f"✓ 成功添加字段: {field_name}")
                except sqlite3.Error as e:
                    logger.error(f"添加字段 {field_name} 失败: {e}")
            else:
                logger.info(f"✓ 字段已存在: {field_name}")
        
        # 提交更改
        conn.commit()
        
        # 验证字段是否正确
        cursor.execute("PRAGMA table_info(filter_rules)")
        new_columns_info = cursor.fetchall()
        new_columns = {row[1]: row for row in new_columns_info}
        
        logger.info("更新后filter_rules表结构:")
        for col_name, col_info in new_columns.items():
            if col_name in [f['name'] for f in new_fields]:
                logger.info(f"  ★ {col_name}: {col_info}")
            else:
                logger.info(f"    {col_name}: {col_info}")
        
        # 测试查询这些字段
        try:
            cursor.execute("SELECT last_sync_time, last_sync_message_count, sync_status, needs_full_resync FROM filter_rules LIMIT 1")
            result = cursor.fetchone()
            logger.info(f"字段查询测试成功: {result}")
        except sqlite3.Error as e:
            logger.error(f"字段查询测试失败: {e}")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"修复失败: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    logger.info("开始修复规则同步字段问题...")
    success = fix_rule_sync_fields()
    if success:
        logger.info("✅ 修复完成")
    else:
        logger.error("❌ 修复失败")