#!/usr/bin/env python3
"""
Telegram群组消息获取测试脚本
用于验证API凭据和群组消息获取功能
"""

import asyncio
from telethon import TelegramClient
import sys
import os

async def test_telegram_groups():
    """测试Telegram群组消息获取功能"""
    
    # 使用提供的API凭据
    api_id = 27902826
    api_hash = '76e23a2f92b8a3a75963d851fbcb4384'
    
    # 使用session文件
    client = TelegramClient('tggod_session', api_id, api_hash)
    
    try:
        print("正在连接到Telegram...")
        await client.connect()
        
        # 检查是否已授权
        if await client.is_user_authorized():
            print("✓ 已授权，正在验证连接...")
            
            # 获取用户信息
            me = await client.get_me()
            print(f"✓ 当前用户: {me.first_name} (@{me.username})")
            
            # 获取对话列表
            dialogs = await client.get_dialogs()
            groups = [d for d in dialogs if d.is_group or d.is_channel]
            
            print(f"✓ 共有 {len(groups)} 个群组/频道")
            
            if groups:
                print("\n群组列表:")
                for i, group in enumerate(groups[:10]):
                    print(f"  {i+1}. {group.name} - ID: {group.entity.id}")
                
                # 测试获取第一个群组的消息
                test_group = groups[0]
                print(f"\n正在获取群组 \"{test_group.name}\" 的消息...")
                
                messages = []
                message_count = 0
                async for message in client.iter_messages(test_group.entity, limit=5):
                    message_count += 1
                    # 处理发送者信息
                    sender_name = 'Unknown'
                    if message.sender:
                        if hasattr(message.sender, 'first_name'):
                            sender_name = message.sender.first_name
                        elif hasattr(message.sender, 'title'):
                            sender_name = message.sender.title
                        elif hasattr(message.sender, 'username'):
                            sender_name = message.sender.username
                    
                    if message.text:
                        messages.append({
                            'id': message.id,
                            'text': message.text[:100] + '...' if len(message.text) > 100 else message.text,
                            'sender': sender_name,
                            'date': message.date.strftime("%Y-%m-%d %H:%M:%S")
                        })
                
                print(f"✓ 成功获取 {message_count} 条消息，其中 {len(messages)} 条包含文本")
                
                if messages:
                    print("\n最新消息:")
                    for msg in messages[:3]:
                        print(f"  - [{msg['id']}] {msg['sender']} ({msg['date']}): {msg['text']}")
                
                print("\n✅ 群组消息获取功能测试成功!")
                
                # 测试获取群组信息
                print(f"\n群组详细信息:")
                print(f"  - 名称: {test_group.name}")
                print(f"  - ID: {test_group.entity.id}")
                print(f"  - 类型: {'频道' if test_group.is_channel else '群组'}")
                if hasattr(test_group.entity, 'participants_count'):
                    print(f"  - 成员数: {test_group.entity.participants_count}")
                    
            else:
                print("未找到任何群组或频道")
                
        else:
            print("❌ 未授权 - 需要先运行认证脚本进行手机号码验证")
            print("请在有交互式终端的环境中运行:")
            print("python telegram_auth.py")
            
        await client.disconnect()
        
    except Exception as e:
        print(f"✗ 测试过程出错: {e}")
        import traceback
        traceback.print_exc()
        await client.disconnect()
        sys.exit(1)

if __name__ == "__main__":
    print("Telegram群组消息获取测试")
    print("=" * 50)
    
    # 运行测试
    asyncio.run(test_telegram_groups())