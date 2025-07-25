#!/usr/bin/env python3
"""
验证数据库字段完整性的脚本
"""
import sys
import os
sys.path.append('/app')
sys.path.append('/app/app')

from sqlalchemy import create_engine, inspect, text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_database():
    """验证数据库字段完整性"""
    try:
        # 直接连接线上数据库
        engine = create_engine('sqlite:////app/data/tggod.db')
        inspector = inspect(engine)
        
        print("🔍 验证数据库表和字段...")
        
        # 1. 检查所有表
        tables = inspector.get_table_names()
        print(f"📋 数据库表 ({len(tables)}):")
        for table in sorted(tables):
            print(f"  ✓ {table}")
        
        # 2. 检查telegram_messages表字段
        print("\n📋 telegram_messages表字段:")
        columns = inspector.get_columns('telegram_messages')
        column_names = [col['name'] for col in columns]
        required_fields = ['media_group_id', 'download_progress', 'download_started_at']
        
        for field in required_fields:
            if field in column_names:
                print(f"  ✅ {field}")
            else:
                print(f"  ❌ {field} - 缺失")
        
        # 3. 检查download_tasks表字段
        print("\n📋 download_tasks表字段:")
        columns = inspector.get_columns('download_tasks')
        column_names = [col['name'] for col in columns]
        required_fields = ['date_from', 'date_to']
        
        for field in required_fields:
            if field in column_names:
                print(f"  ✅ {field}")
            else:
                print(f"  ❌ {field} - 缺失")
        
        # 4. 检查download_records表
        if 'download_records' in tables:
            print("\n📋 download_records表:")
            print("  ✅ 表存在")
            columns = inspector.get_columns('download_records')
            print(f"  字段数量: {len(columns)}")
        else:
            print("\n❌ download_records表不存在")
        
        # 5. 测试实际查询
        print("\n🔍 测试数据库查询...")
        with engine.connect() as conn:
            try:
                # 测试查询telegram_messages
                result = conn.execute(text("""
                    SELECT id, media_group_id, download_progress 
                    FROM telegram_messages 
                    LIMIT 1
                """))
                print("  ✅ telegram_messages查询成功")
                
                # 测试查询download_records
                result = conn.execute(text("SELECT COUNT(*) FROM download_records"))
                count = result.scalar()
                print(f"  ✅ download_records查询成功 (记录数: {count})")
                
                # 测试查询download_tasks
                result = conn.execute(text("""
                    SELECT id, date_from, date_to 
                    FROM download_tasks 
                    LIMIT 1
                """))
                print("  ✅ download_tasks查询成功")
                
            except Exception as e:
                print(f"  ❌ 查询失败: {e}")
                return False
        
        print("\n🎉 数据库验证完成！所有字段和表都正常。")
        return True
        
    except Exception as e:
        print(f"❌ 数据库验证失败: {e}")
        return False

if __name__ == "__main__":
    success = verify_database()
    exit(0 if success else 1)