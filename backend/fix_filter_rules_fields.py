#!/usr/bin/env python3
"""
修复 filter_rules 表缺失的同步字段
"""

import os
import sys
import sqlite3
from pathlib import Path

# 设置环境变量和路径
# 使用应用程序默认的数据库路径或环境变量中的路径
if 'DATABASE_URL' not in os.environ:
    os.environ['DATABASE_URL'] = 'sqlite:////app/data/tggod.db'

backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

def fix_filter_rules_fields():
    """修复 filter_rules 表的同步字段"""
    try:
        from app.database import engine
        import sqlalchemy as sa
        
        print("🔧 检查 filter_rules 表字段...")
        
        # 检查现有字段
        inspector = sa.inspect(engine)
        existing_columns = [col['name'] for col in inspector.get_columns('filter_rules')]
        
        print("当前 filter_rules 表字段:")
        for col in existing_columns:
            print(f"  - {col}")
        
        # 需要的同步字段
        sync_fields = [
            'last_sync_time',
            'last_sync_message_count', 
            'sync_status',
            'needs_full_resync'
        ]
        
        missing_fields = [field for field in sync_fields if field not in existing_columns]
        
        if missing_fields:
            print(f"\n缺失的同步字段: {missing_fields}")
            print("正在添加缺失字段...")
            
            with engine.connect() as conn:
                for field in missing_fields:
                    try:
                        if field == 'last_sync_time':
                            conn.execute(sa.text('ALTER TABLE filter_rules ADD COLUMN last_sync_time DATETIME'))
                        elif field == 'last_sync_message_count':
                            conn.execute(sa.text('ALTER TABLE filter_rules ADD COLUMN last_sync_message_count INTEGER DEFAULT 0'))
                        elif field == 'sync_status':
                            conn.execute(sa.text('ALTER TABLE filter_rules ADD COLUMN sync_status VARCHAR(20) DEFAULT "pending"'))
                        elif field == 'needs_full_resync':
                            conn.execute(sa.text('ALTER TABLE filter_rules ADD COLUMN needs_full_resync BOOLEAN DEFAULT 0'))
                        
                        print(f"  ✓ 已添加字段: {field}")
                    except Exception as e:
                        print(f"  ✗ 添加字段 {field} 失败: {e}")
                
                conn.commit()
            
            print("✅ filter_rules 表字段修复完成!")
        else:
            print("\n✅ 所有同步字段已存在，无需修复")
            
    except Exception as e:
        print(f"❌ 修复 filter_rules 表字段失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    fix_filter_rules_fields()