#!/usr/bin/env python3
"""
生产环境验证脚本
验证数据库初始化系统的完整性
"""

import os
import sys
import tempfile
import sqlite3
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def verify_production_database_system():
    """验证生产环境数据库系统"""
    print("=" * 60)
    print("TgGod 生产环境数据库系统验证")
    print("=" * 60)
    
    # 1. 验证空数据库初始化
    print("\n1. 验证空数据库初始化...")
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
        test_db_path = tmp_db.name
    
    try:
        # 设置测试数据库URL
        os.environ['DATABASE_URL'] = f'sqlite:///{test_db_path}'
        
        # 运行数据库检查
        from check_database import DatabaseChecker
        checker = DatabaseChecker()
        
        # 验证空数据库
        conn = sqlite3.connect(test_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        initial_tables = cursor.fetchall()
        conn.close()
        
        print(f"   初始表数量: {len(initial_tables)}")
        
        # 执行检查和修复
        success = checker.check_and_repair()
        
        if success:
            print("   ✓ 数据库初始化成功")
            
            # 验证表创建
            conn = sqlite3.connect(test_db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            final_tables = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            print(f"   创建的表: {sorted(final_tables)}")
            
            # 验证必需表存在
            required_tables = ['users', 'telegram_groups', 'telegram_messages', 
                             'filter_rules', 'system_logs']
            missing_tables = [t for t in required_tables if t not in final_tables]
            
            if missing_tables:
                print(f"   ✗ 缺少表: {missing_tables}")
                return False
            
            print("   ✓ 所有必需表创建成功")
            
        else:
            print("   ✗ 数据库初始化失败")
            return False
            
    finally:
        # 清理
        if os.path.exists(test_db_path):
            os.unlink(test_db_path)
        if 'DATABASE_URL' in os.environ:
            del os.environ['DATABASE_URL']
    
    # 2. 验证现有数据库检查
    print("\n2. 验证现有数据库检查...")
    
    # 使用默认数据库
    try:
        from app.config import settings
        print(f"   数据库URL: {settings.database_url}")
        
        checker = DatabaseChecker()
        success = checker.check_and_repair()
        
        if success:
            print("   ✓ 现有数据库检查通过")
        else:
            print("   ✗ 现有数据库检查失败")
            return False
            
    except Exception as e:
        print(f"   ✗ 数据库检查异常: {e}")
        return False
    
    # 3. 验证生产启动脚本
    print("\n3. 验证生产启动脚本...")
    try:
        # 导入测试
        from production_start import main
        print("   ✓ 生产启动脚本导入成功")
        
        # 验证初始化脚本
        from init_database import init_database
        print("   ✓ 数据库初始化脚本导入成功")
        
    except Exception as e:
        print(f"   ✗ 生产脚本导入失败: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✅ 生产环境数据库系统验证全部通过!")
    print("=" * 60)
    
    print("\n🎯 系统特性:")
    print("• 自动检测空数据库并完整初始化")
    print("• 检查现有数据库结构并自动修复")
    print("• 支持Alembic版本管理")
    print("• 生产环境友好的启动流程")
    print("• 完整的错误处理和日志记录")
    
    print("\n🚀 使用方法:")
    print("• 生产环境启动: python production_start.py")
    print("• 数据库检查: python check_database.py")
    print("• 手动初始化: python init_database.py")
    print("• 系统测试: python test_db_init.py")
    
    return True

if __name__ == "__main__":
    success = verify_production_database_system()
    sys.exit(0 if success else 1)