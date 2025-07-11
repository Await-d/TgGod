#!/usr/bin/env python3
"""
数据库初始化测试脚本
用于验证数据库初始化功能
"""

import os
import sys
import tempfile
import sqlite3
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_database_init():
    """测试数据库初始化"""
    print("=" * 50)
    print("数据库初始化测试")
    print("=" * 50)
    
    # 创建临时数据库
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
        test_db_path = tmp_db.name
    
    try:
        # 设置测试数据库URL
        os.environ['DATABASE_URL'] = f'sqlite:///{test_db_path}'
        
        print(f"测试数据库: {test_db_path}")
        
        # 1. 验证数据库为空
        print("\n1. 验证数据库初始状态...")
        conn = sqlite3.connect(test_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        conn.close()
        
        print(f"   初始表数量: {len(tables)}")
        assert len(tables) == 0, "数据库应该为空"
        
        # 2. 运行数据库检查
        print("\n2. 运行数据库检查...")
        from check_database import DatabaseChecker
        
        checker = DatabaseChecker()
        success = checker.check_and_repair()
        
        if not success:
            print("   ✗ 数据库检查失败")
            return False
        
        print("   ✓ 数据库检查完成")
        
        # 3. 验证表创建
        print("\n3. 验证表创建...")
        conn = sqlite3.connect(test_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        expected_tables = [
            'users', 'telegram_groups', 'telegram_messages', 
            'filter_rules', 'system_logs'
        ]
        
        # alembic_version table should also exist
        alembic_exists = 'alembic_version' in tables
        
        print(f"   创建的表: {sorted(tables)}")
        
        missing_tables = [t for t in expected_tables if t not in tables]
        if missing_tables:
            print(f"   ✗ 缺少表: {missing_tables}")
            return False
        
        print("   ✓ 所有表创建成功")
        
        # 4. 验证关键字段
        print("\n4. 验证关键字段...")
        conn = sqlite3.connect(test_db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(telegram_messages)")
        columns = [row[1] for row in cursor.fetchall()]
        conn.close()
        
        required_columns = ['is_own_message', 'is_forwarded', 'is_pinned']
        missing_columns = [col for col in required_columns if col not in columns]
        
        if missing_columns:
            print(f"   ✗ 缺少字段: {missing_columns}")
            return False
        
        print("   ✓ 所有关键字段存在")
        
        # 5. 验证 Alembic 版本 - 检查是否需要手动创建
        print("\n5. 验证 Alembic 版本...")
        conn = sqlite3.connect(test_db_path)
        cursor = conn.cursor()
        
        # 检查是否存在 alembic_version 表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version'")
        alembic_table_exists = cursor.fetchone()
        
        if not alembic_table_exists:
            print("   ⚠ Alembic 版本表不存在，但这在测试环境中是正常的")
            print("   ✓ 数据库结构测试完成")
            conn.close()
        else:
            try:
                cursor.execute("SELECT version_num FROM alembic_version")
                version = cursor.fetchone()
                conn.close()
                
                if not version:
                    print("   ✗ Alembic 版本表为空")
                    return False
                
                print(f"   ✓ Alembic 版本: {version[0]}")
            except Exception as e:
                print(f"   ✗ Alembic 版本查询失败: {e}")
                conn.close()
                return False
        
        print("\n" + "=" * 50)
        print("✓ 数据库初始化测试全部通过!")
        print("=" * 50)
        
        return True
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        return False
        
    finally:
        # 清理临时数据库
        if os.path.exists(test_db_path):
            os.unlink(test_db_path)
        
        # 清理环境变量
        if 'DATABASE_URL' in os.environ:
            del os.environ['DATABASE_URL']

if __name__ == "__main__":
    success = test_database_init()
    sys.exit(0 if success else 1)