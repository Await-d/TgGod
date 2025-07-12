#!/usr/bin/env python3
"""
生产环境数据库修复脚本
解决media_file_id字段缺失导致的API 500错误问题
"""

import sqlite3
import sys
import os
from pathlib import Path

def fix_production_database():
    """修复生产环境数据库"""
    print("=== TgGod 生产环境数据库修复工具 ===")
    
    # 检查数据库文件
    db_files = [
        "/app/data/tggod.db",
        "/root/project/TgGod/backend/tggod.db"
    ]
    
    for db_path in db_files:
        if not os.path.exists(db_path):
            print(f"⚠️  数据库文件不存在: {db_path}")
            continue
            
        print(f"\n🔍 检查数据库: {db_path}")
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 检查表结构
            cursor.execute("PRAGMA table_info(telegram_messages)")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            # 检查必需字段
            required_fields = [
                'media_file_id',
                'media_file_unique_id', 
                'media_downloaded',
                'media_download_url',
                'media_download_error',
                'media_thumbnail_path'
            ]
            
            missing_fields = [field for field in required_fields if field not in column_names]
            
            if missing_fields:
                print(f"❌ 缺少字段: {missing_fields}")
                print("🔧 开始修复...")
                
                # 添加缺失字段
                field_definitions = {
                    'media_file_id': 'VARCHAR(255)',
                    'media_file_unique_id': 'VARCHAR(255)',
                    'media_downloaded': 'BOOLEAN',
                    'media_download_url': 'VARCHAR(500)',
                    'media_download_error': 'TEXT',
                    'media_thumbnail_path': 'VARCHAR(500)'
                }
                
                for field in missing_fields:
                    if field in field_definitions:
                        sql = f"ALTER TABLE telegram_messages ADD COLUMN {field} {field_definitions[field]}"
                        cursor.execute(sql)
                        print(f"  ✅ 添加字段: {field}")
                
                conn.commit()
                print("✅ 数据库修复完成!")
            else:
                print("✅ 所有必需字段都存在")
                
                # 检查数据量
                cursor.execute("SELECT COUNT(*) FROM telegram_groups")
                groups_count = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM telegram_messages")
                messages_count = cursor.fetchone()[0]
                
                print(f"📊 数据统计: {groups_count} 个群组, {messages_count} 条消息")
                
                if groups_count == 0:
                    print("⚠️  数据库为空，建议运行示例数据创建")
            
            conn.close()
            
        except Exception as e:
            print(f"❌ 数据库检查失败: {e}")
    
    print("\n=== 修复完成 ===")
    print("建议操作:")
    print("1. 重启应用服务")
    print("2. 测试API: GET /api/telegram/groups/1/messages?is_pinned=true")
    print("3. 如果仍有问题，检查应用日志")

if __name__ == "__main__":
    fix_production_database()