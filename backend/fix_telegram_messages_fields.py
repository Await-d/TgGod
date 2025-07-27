#!/usr/bin/env python3
"""
修复 telegram_messages 表缺失的字段
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

def fix_telegram_messages_fields():
    """修复 telegram_messages 表的缺失字段"""
    try:
        from app.database import engine
        import sqlalchemy as sa
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print("=" * 50)
        print("🔧 Telegram Messages 表字段修复工具")
        print(f"⏰ 执行时间: {timestamp}")
        print("=" * 50)
        print("📋 检查 telegram_messages 表字段...")
        
        # 检查现有字段
        inspector = sa.inspect(engine)
        existing_columns = [col['name'] for col in inspector.get_columns('telegram_messages')]
        
        print("当前 telegram_messages 表字段:")
        for col in existing_columns:
            print(f"  - {col}")
        
        # 需要的下载字段
        download_fields = [
            'download_progress',
            'downloaded_size', 
            'download_speed',
            'estimated_time_remaining',
            'download_started_at',
            'is_downloading'
        ]
        
        missing_fields = [field for field in download_fields if field not in existing_columns]
        
        if missing_fields:
            print(f"\n缺失的下载字段: {missing_fields}")
            print("正在添加缺失字段...")
            
            with engine.connect() as conn:
                for field in missing_fields:
                    try:
                        if field == 'download_progress':
                            conn.execute(sa.text('ALTER TABLE telegram_messages ADD COLUMN download_progress INTEGER DEFAULT 0'))
                        elif field == 'downloaded_size':
                            conn.execute(sa.text('ALTER TABLE telegram_messages ADD COLUMN downloaded_size INTEGER DEFAULT 0'))
                        elif field == 'download_speed':
                            conn.execute(sa.text('ALTER TABLE telegram_messages ADD COLUMN download_speed REAL DEFAULT 0.0'))
                        elif field == 'estimated_time_remaining':
                            conn.execute(sa.text('ALTER TABLE telegram_messages ADD COLUMN estimated_time_remaining INTEGER DEFAULT 0'))
                        elif field == 'download_started_at':
                            conn.execute(sa.text('ALTER TABLE telegram_messages ADD COLUMN download_started_at DATETIME'))
                        elif field == 'is_downloading':
                            conn.execute(sa.text('ALTER TABLE telegram_messages ADD COLUMN is_downloading BOOLEAN DEFAULT 0'))
                        
                        print(f"  ✓ 已添加字段: {field}")
                    except Exception as e:
                        print(f"  ✗ 添加字段 {field} 失败: {e}")
                
                conn.commit()
            
            print("✅ telegram_messages 表字段修复完成!")
        else:
            print("\n✅ 所有下载字段已存在，无需修复")
        
        end_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print("\n" + "=" * 50)
        print("🎉 Telegram Messages 字段检查完成!")
        print(f"⏰ 完成时间: {end_timestamp}")
        print("=" * 50)
            
    except Exception as e:
        print(f"❌ 修复 telegram_messages 表字段失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    fix_telegram_messages_fields()