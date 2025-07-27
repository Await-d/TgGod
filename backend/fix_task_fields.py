#!/usr/bin/env python3
"""
永久修复download_tasks表的调度字段问题
确保所有必需的字段都存在并且应用重启后不会丢失
"""

import os
import sys
import sqlite3
from pathlib import Path
from datetime import datetime

# 设置环境变量
# 使用应用程序默认的数据库路径或环境变量中的路径
if 'DATABASE_URL' not in os.environ:
    os.environ['DATABASE_URL'] = 'sqlite:////app/data/tggod.db'

def fix_download_tasks_table():
    """修复download_tasks表的调度字段"""
    db_path = '/app/data/tggod.db'
    
    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        return False
    
    print(f"🔧 开始修复数据库表: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查当前表结构
        cursor.execute("PRAGMA table_info(download_tasks)")
        existing_columns = [col[1] for col in cursor.fetchall()]
        
        print(f"📋 当前字段数量: {len(existing_columns)}")
        
        # 需要的调度字段
        required_fields = {
            'task_type': 'VARCHAR(20) DEFAULT "once"',
            'schedule_type': 'VARCHAR(20)',
            'schedule_config': 'JSON',
            'next_run_time': 'DATETIME',
            'last_run_time': 'DATETIME', 
            'is_active': 'BOOLEAN DEFAULT 1',
            'max_runs': 'INTEGER',
            'run_count': 'INTEGER DEFAULT 0'
        }
        
        # 检查缺失的字段
        missing_fields = []
        for field_name in required_fields:
            if field_name not in existing_columns:
                missing_fields.append(field_name)
            else:
                print(f"  ✓ {field_name} (已存在)")
        
        if missing_fields:
            print(f"\n🔄 需要添加的字段: {missing_fields}")
            
            # 添加缺失的字段
            for field_name in missing_fields:
                field_def = required_fields[field_name]
                sql = f"ALTER TABLE download_tasks ADD COLUMN {field_name} {field_def}"
                
                try:
                    cursor.execute(sql)
                    print(f"  ✅ 已添加: {field_name}")
                except sqlite3.Error as e:
                    print(f"  ❌ 添加失败 {field_name}: {e}")
            
            # 提交更改
            conn.commit()
            print("💾 数据库更改已提交")
        else:
            print("\n✅ 所有调度字段都已存在")
        
        # 验证修复结果
        cursor.execute("PRAGMA table_info(download_tasks)")
        final_columns = [col[1] for col in cursor.fetchall()]
        
        print(f"\n📊 修复后字段数量: {len(final_columns)}")
        
        # 检查是否所有字段都存在
        final_missing = []
        for field_name in required_fields:
            if field_name in final_columns:
                print(f"  ✓ {field_name}")
            else:
                final_missing.append(field_name)
        
        if not final_missing:
            print("\n🎉 所有调度字段修复完成!")
            return True
        else:
            print(f"\n❌ 仍有字段缺失: {final_missing}")
            return False
            
    except Exception as e:
        print(f"❌ 修复过程中出错: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def verify_sqlalchemy_compatibility():
    """验证SQLAlchemy模型兼容性"""
    try:
        # 设置Python路径
        sys.path.insert(0, '/root/project/tg/backend')
        
        from app.database import engine
        from app.models.rule import DownloadTask
        import sqlalchemy as sa
        
        print("\n🔍 验证SQLAlchemy模型兼容性...")
        
        # 尝试查询表结构
        inspector = sa.inspect(engine)
        columns = inspector.get_columns('download_tasks')
        
        print("✅ SQLAlchemy可以正常访问表结构")
        
        # 尝试创建一个简单的查询
        from sqlalchemy.orm import sessionmaker
        Session = sessionmaker(bind=engine)
        session = Session()
        
        try:
            # 测试查询（不会返回结果，只是测试字段访问）
            result = session.query(DownloadTask).filter(
                DownloadTask.task_type == 'once'
            ).limit(1).all()
            print("✅ 调度字段查询测试成功")
        except Exception as e:
            print(f"❌ 调度字段查询测试失败: {e}")
            return False
        finally:
            session.close()
        
        return True
        
    except Exception as e:
        print(f"❌ SQLAlchemy兼容性验证失败: {e}")
        return False

def main():
    """主函数"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("=" * 60)
    print(f"🛠️  Download Tasks 表调度字段修复工具")
    print(f"⏰ 执行时间: {timestamp}")
    print("=" * 60)
    
    # 步骤1: 修复数据库表
    if not fix_download_tasks_table():
        print("\n❌ 数据库表修复失败")
        sys.exit(1)
    
    # 步骤2: 验证SQLAlchemy兼容性
    if not verify_sqlalchemy_compatibility():
        print("\n❌ SQLAlchemy兼容性验证失败")
        sys.exit(1)
    
    end_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("\n" + "=" * 60)
    print("🎉 所有修复完成！调度功能应该可以正常工作了")
    print("建议重启应用以确保所有更改生效")
    print(f"⏰ 完成时间: {end_timestamp}")
    print("=" * 60)

if __name__ == '__main__':
    main()