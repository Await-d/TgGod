#!/usr/bin/env python3
"""
线上环境诊断和修复工具
用于检查和修复线上数据库字段问题
"""

import os
import sys
import sqlite3
from pathlib import Path

def check_database_fields():
    """检查数据库字段是否完整"""
    db_path = '/app/data/tggod.db'
    
    if not os.path.exists(db_path):
        print(f"❌ 线上数据库文件不存在: {db_path}")
        return False
    
    print(f"🔍 检查线上数据库: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查download_tasks表
        print("\n📋 检查download_tasks表字段:")
        cursor.execute("PRAGMA table_info(download_tasks)")
        dt_columns = [col[1] for col in cursor.fetchall()]
        
        required_dt_fields = [
            'task_type', 'schedule_type', 'schedule_config', 
            'next_run_time', 'last_run_time', 'is_active', 
            'max_runs', 'run_count'
        ]
        
        missing_dt = []
        for field in required_dt_fields:
            if field in dt_columns:
                print(f"  ✓ {field}")
            else:
                print(f"  ❌ {field} (缺失)")
                missing_dt.append(field)
        
        # 检查filter_rules表
        print("\n📋 检查filter_rules表字段:")
        cursor.execute("PRAGMA table_info(filter_rules)")
        fr_columns = [col[1] for col in cursor.fetchall()]
        
        required_fr_fields = [
            'last_sync_time', 'last_sync_message_count', 
            'sync_status', 'needs_full_resync'
        ]
        
        missing_fr = []
        for field in required_fr_fields:
            if field in fr_columns:
                print(f"  ✓ {field}")
            else:
                print(f"  ❌ {field} (缺失)")
                missing_fr.append(field)
        
        conn.close()
        
        if missing_dt or missing_fr:
            print(f"\n⚠️ 发现缺失字段:")
            if missing_dt:
                print(f"  download_tasks: {missing_dt}")
            if missing_fr:
                print(f"  filter_rules: {missing_fr}")
            return False
        else:
            print(f"\n✅ 所有字段都存在")
            return True
            
    except Exception as e:
        print(f"❌ 检查数据库时出错: {e}")
        return False

def run_field_fix():
    """运行字段修复脚本"""
    print("\n🛠️ 运行数据库字段修复...")
    
    try:
        # 运行修复脚本
        import subprocess
        result = subprocess.run([
            sys.executable, 
            '/root/project/tg/backend/fix_task_fields.py'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ 字段修复脚本执行成功")
            print(result.stdout)
            return True
        else:
            print("❌ 字段修复脚本执行失败")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ 运行修复脚本时出错: {e}")
        return False

def test_sqlalchemy_access():
    """测试SQLAlchemy访问"""
    print("\n🔍 测试SQLAlchemy数据库访问...")
    
    try:
        sys.path.insert(0, '/root/project/tg/backend')
        
        from app.database import engine
        from app.models.rule import DownloadTask, FilterRule
        from sqlalchemy.orm import sessionmaker
        
        Session = sessionmaker(bind=engine)
        session = Session()
        
        try:
            # 测试download_tasks表的调度字段
            print("  测试download_tasks调度字段访问...")
            result = session.query(DownloadTask).filter(
                DownloadTask.task_type == 'once'
            ).limit(1).all()
            print("  ✓ download_tasks调度字段访问正常")
            
            # 测试filter_rules表的同步字段
            print("  测试filter_rules同步字段访问...")
            result = session.query(FilterRule).filter(
                FilterRule.sync_status == 'pending'
            ).limit(1).all()
            print("  ✓ filter_rules同步字段访问正常")
            
            return True
            
        except Exception as e:
            print(f"  ❌ SQLAlchemy字段访问失败: {e}")
            return False
        finally:
            session.close()
            
    except Exception as e:
        print(f"❌ SQLAlchemy测试失败: {e}")
        return False

def generate_restart_command():
    """生成重启命令"""
    print("\n🔄 建议的线上重启命令:")
    print("sudo systemctl restart tggod")
    print("# 或者")
    print("docker-compose restart")
    print("# 或者")
    print("pm2 restart tggod")

def main():
    """主函数"""
    print("=" * 60)
    print("🔧 TgGod 线上环境诊断和修复工具")
    print("=" * 60)
    
    # 步骤1: 检查数据库字段
    print("\n📍 步骤1: 检查数据库字段完整性")
    fields_ok = check_database_fields()
    
    if not fields_ok:
        print("\n📍 步骤2: 运行字段修复")
        if not run_field_fix():
            print("\n❌ 字段修复失败，请手动检查")
            sys.exit(1)
        
        # 重新检查
        print("\n📍 步骤3: 重新检查字段")
        if not check_database_fields():
            print("\n❌ 修复后仍有问题，请检查日志")
            sys.exit(1)
    
    # 步骤4: 测试SQLAlchemy访问
    print("\n📍 步骤4: 测试SQLAlchemy访问")
    if not test_sqlalchemy_access():
        print("\n⚠️ SQLAlchemy访问有问题，需要重启应用")
        generate_restart_command()
        
        print("\n💡 请在重启应用后重新运行此诊断脚本验证")
    else:
        print("\n✅ 所有检查通过，线上环境应该正常工作")
    
    print("\n" + "=" * 60)
    print("🎉 诊断完成")
    print("=" * 60)

if __name__ == '__main__':
    main()