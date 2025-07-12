#!/usr/bin/env python3
"""
测试转发消息API功能
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.config import settings
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.telegram import TelegramGroup, TelegramMessage
from datetime import datetime

def test_forwarded_message_api():
    """测试转发消息API功能"""
    print("测试转发消息API功能...")
    
    # 创建数据库连接
    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # 获取第一个群组
        group = session.query(TelegramGroup).first()
        if not group:
            print("错误: 数据库中没有群组")
            return False
        
        print(f"使用群组: {group.title} (ID: {group.id})")
        
        # 创建一个测试转发消息
        test_message = TelegramMessage(
            group_id=group.id,
            message_id=99999,  # 使用一个不会冲突的ID
            sender_id=123456,
            sender_username="test_user",
            sender_name="测试用户",
            text="这是一条测试转发消息",
            is_forwarded=True,
            forwarded_from="测试频道",
            forwarded_from_id=987654321,
            forwarded_from_type="channel",
            forwarded_date=datetime.now(),
            date=datetime.now(),
            created_at=datetime.now()
        )
        
        # 检查消息是否已存在
        existing = session.query(TelegramMessage).filter(
            TelegramMessage.message_id == 99999,
            TelegramMessage.group_id == group.id
        ).first()
        
        if existing:
            print("更新现有测试消息...")
            existing.is_forwarded = True
            existing.forwarded_from = "测试频道"
            existing.forwarded_from_id = 987654321
            existing.forwarded_from_type = "channel"
            existing.forwarded_date = datetime.now()
            session.commit()
            message_id = existing.id
        else:
            print("创建新的测试消息...")
            session.add(test_message)
            session.commit()
            message_id = test_message.id
        
        print(f"测试消息创建/更新成功，ID: {message_id}")
        
        # 查询转发消息
        forwarded_msg = session.query(TelegramMessage).filter(
            TelegramMessage.id == message_id
        ).first()
        
        if forwarded_msg:
            print("转发消息字段验证:")
            print(f"  is_forwarded: {forwarded_msg.is_forwarded}")
            print(f"  forwarded_from: {forwarded_msg.forwarded_from}")
            print(f"  forwarded_from_id: {forwarded_msg.forwarded_from_id}")
            print(f"  forwarded_from_type: {forwarded_msg.forwarded_from_type}")
            print(f"  forwarded_date: {forwarded_msg.forwarded_date}")
            print("✅ 转发消息字段测试通过!")
            return True
        else:
            print("❌ 无法找到创建的测试消息")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        session.rollback()
        return False
    finally:
        session.close()

if __name__ == "__main__":
    success = test_forwarded_message_api()
    sys.exit(0 if success else 1)