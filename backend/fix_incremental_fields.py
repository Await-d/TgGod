#!/usr/bin/env python3
"""
修复增量查询优化相关字段
为download_tasks表添加last_processed_time和force_full_scan字段
"""

import os
import sys
import sqlite3
from pathlib import Path
from datetime import datetime

# 设置环境变量和路径
if 'DATABASE_URL' not in os.environ:
    os.environ['DATABASE_URL'] = 'sqlite:////app/data/tggod.db'

backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

def fix_incremental_fields():
    """修复增量查询相关字段"""
    try:
        from app.database import engine
        import sqlalchemy as sa
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print("=" * 50)
        print("🔧 增量查询优化字段修复工具")
        print(f"⏰ 执行时间: {timestamp}")
        print("=" * 50)
        print("📋 检查 download_tasks 表增量字段...")
        
        # 检查现有字段
        inspector = sa.inspect(engine)
        existing_columns = [col['name'] for col in inspector.get_columns('download_tasks')]
        
        print("当前 download_tasks 表字段:")
        for col in existing_columns:
            print(f"  - {col}")
        
        # 需要的增量查询字段
        incremental_fields = [
            'last_processed_time',
            'force_full_scan'
        ]
        
        missing_fields = [field for field in incremental_fields if field not in existing_columns]
        
        if missing_fields:
            print(f"\n缺失的增量字段: {missing_fields}")
            print("正在添加缺失字段...")
            
            with engine.connect() as conn:
                for field in missing_fields:
                    try:
                        if field == 'last_processed_time':
                            conn.execute(sa.text('ALTER TABLE download_tasks ADD COLUMN last_processed_time DATETIME'))
                        elif field == 'force_full_scan':
                            conn.execute(sa.text('ALTER TABLE download_tasks ADD COLUMN force_full_scan BOOLEAN DEFAULT 0'))
                        
                        print(f"  ✓ 已添加字段: {field}")
                    except Exception as e:
                        print(f"  ✗ 添加字段 {field} 失败: {e}")
                
                conn.commit()
            
            print("✅ 增量查询字段修复完成!")
        else:
            print("\n✅ 所有增量字段已存在，无需修复")
        
        # 验证字段类型和默认值
        print("\n🔍 验证字段配置:")
        final_columns = inspector.get_columns('download_tasks')
        
        for col in final_columns:
            if col['name'] in incremental_fields:
                print(f"  - {col['name']}: {col['type']} (可空: {col['nullable']}, 默认值: {col.get('default', '无')})")
        
        end_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print("\n" + "=" * 50)
        print("🎉 增量查询字段检查完成!")
        print(f"⏰ 完成时间: {end_timestamp}")
        print("=" * 50)
            
    except Exception as e:
        print(f"❌ 修复增量字段失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    fix_incremental_fields()