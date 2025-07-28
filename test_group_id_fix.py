#!/usr/bin/env python3
"""
测试群组ID修复的脚本
"""
import sys
import os
sys.path.append('/root/project/tg')

import sqlite3
from datetime import datetime

def test_database_fix():
    """测试数据库修复是否生效"""
    print("=== 测试数据库群组ID修复 ===")
    
    # 尝试多个可能的数据库路径
    possible_paths = [
        "/app/data/tggod.db",
        "/root/project/tg/data/tggod.db", 
        "/root/project/tg/tggod.db",
        "./data/tggod.db",
        "./tggod.db"
    ]
    
    db_path = None
    for path in possible_paths:
        if os.path.exists(path):
            db_path = path
            break
    
    if not db_path:
        print(f"⚠️  数据库文件不存在于任何预期位置:")
        for path in possible_paths:
            print(f"   - {path}")  
        print("这可能意味着应用未运行或数据库未初始化")
        return None  # 返回None表示跳过测试
    
    print(f"找到数据库文件: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 检查所有群组的telegram_id
        cursor.execute("SELECT COUNT(*) as total FROM telegram_groups")
        total_groups = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as positive_count FROM telegram_groups WHERE telegram_id > 0")
        positive_count = cursor.fetchone()['positive_count']
        
        cursor.execute("SELECT COUNT(*) as negative_count FROM telegram_groups WHERE telegram_id < 0")
        negative_count = cursor.fetchone()['negative_count']
        
        print(f"总群组数: {total_groups}")
        print(f"正数ID（有问题）: {positive_count}")
        print(f"负数ID（正常）: {negative_count}")
        
        if positive_count == 0 and negative_count > 0:
            print("✅ 数据库群组ID修复成功！所有群组都使用负数ID")
            
            # 检查特定的测试群组
            cursor.execute("SELECT id, telegram_id, title FROM telegram_groups WHERE id = 45")
            test_group = cursor.fetchone()
            if test_group:
                print(f"测试群组 (ID=45): telegram_id={test_group['telegram_id']}, title={test_group['title']}")
            
            conn.close()
            return True
        else:
            print(f"❌ 数据库仍有问题: {positive_count} 个群组使用正数ID")
            conn.close()
            return False
            
    except Exception as e:
        print(f"❌ 数据库检查失败: {e}")
        return False

def test_import_fix():
    """测试导入修复是否生效"""
    print("\n=== 测试导入修复 ===")
    
    try:
        # 测试导入
        from backend.app.models.telegram import TelegramGroup
        print("✅ TelegramGroup 导入成功")
        
        # 测试别名导入
        from backend.app.models.telegram import TelegramGroup as TGGroup
        print("✅ TelegramGroup 别名导入成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 导入测试失败: {e}")
        return False

def test_task_execution_service():
    """测试任务执行服务是否能正常工作"""
    print("\n=== 测试任务执行服务 ===")
    
    try:
        from backend.app.services.task_execution_service import TaskExecutionService
        print("✅ TaskExecutionService 导入成功")
        
        # 创建实例（不初始化，只是检查能否创建）
        service = TaskExecutionService()
        print("✅ TaskExecutionService 实例创建成功")
        
        return True
        
    except Exception as e:
        print(f"❌ TaskExecutionService 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("开始测试群组ID修复...")
    
    # 运行所有测试
    db_test = test_database_fix()
    import_test = test_import_fix()
    service_test = test_task_execution_service()
    
    print("\n=== 测试结果汇总 ===")
    if db_test is None:
        print("数据库修复: ⚠️  跳过（数据库不存在）")
    else:
        print(f"数据库修复: {'✅ 通过' if db_test else '❌ 失败'}")
    print(f"导入修复: {'✅ 通过' if import_test else '❌ 失败'}")
    print(f"服务测试: {'✅ 通过' if service_test else '❌ 失败'}")
    
    # 检查关键测试是否通过（导入和服务测试必须通过）
    critical_tests = [import_test, service_test]
    if db_test is not None:
        critical_tests.append(db_test)
    
    if all(critical_tests):
        print("\n🎉 关键测试通过！TelegramGroup导入错误已修复")
        if db_test is None:
            print("   注意：数据库测试跳过，需要在应用运行时验证")
        sys.exit(0)
    else:
        print("\n❌ 仍有问题需要解决")
        sys.exit(1)