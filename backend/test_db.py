#!/usr/bin/env python3
"""测试数据库连接和消息查询"""

import sys
import os
sys.path.append('.')

def test_basic_import():
    """测试基础模块导入"""
    try:
        print("1. 测试SQLAlchemy导入...")
        from sqlalchemy import create_engine
        print("✅ SQLAlchemy导入成功")
        
        print("2. 测试模型导入...")
        from app.models.telegram import TelegramMessage, TelegramGroup
        print("✅ 模型导入成功")
        
        print("3. 测试数据库配置导入...")
        from app.config import settings
        print(f"✅ 数据库URL: {settings.database_url}")
        
        return True
    except Exception as e:
        print(f"❌ 模块导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database_connection():
    """测试数据库连接"""
    try:
        from sqlalchemy import create_engine
        from app.config import settings
        
        print("4. 测试数据库连接...")
        engine = create_engine(settings.database_url)
        
        with engine.connect() as conn:
            result = conn.execute("SELECT 1")
            print("✅ 数据库连接成功")
            
        print("5. 测试数据库会话...")
        from app.database import SessionLocal
        db = SessionLocal()
        try:
            # 测试基础查询
            from app.models.telegram import TelegramGroup
            groups_count = db.query(TelegramGroup).count()
            print(f"✅ 群组数量: {groups_count}")
            
            if groups_count > 0:
                # 测试群组69是否存在
                group_69 = db.query(TelegramGroup).filter(TelegramGroup.id == 69).first()
                if group_69:
                    print(f"✅ 群组69存在: {group_69.title}")
                    
                    # 测试消息查询
                    from app.models.telegram import TelegramMessage
                    msg_count = db.query(TelegramMessage).filter(TelegramMessage.group_id == 69).count()
                    print(f"✅ 群组69消息数量: {msg_count}")
                    
                    # 测试分页查询（模拟API调用）
                    messages = db.query(TelegramMessage).filter(
                        TelegramMessage.group_id == 69
                    ).order_by(TelegramMessage.date.desc()).limit(10).all()
                    print(f"✅ 获取最新10条消息成功，实际获取: {len(messages)}")
                    
                else:
                    print("⚠️ 群组69不存在")
            
        finally:
            db.close()
            
        return True
        
    except Exception as e:
        print(f"❌ 数据库连接或查询失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=== 数据库连接测试 ===")
    
    # 基础导入测试
    if not test_basic_import():
        sys.exit(1)
    
    # 数据库连接测试
    if not test_database_connection():
        sys.exit(1)
    
    print("\n✅ 所有测试通过！数据库连接正常。")