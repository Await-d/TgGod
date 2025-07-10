#!/usr/bin/env python3
"""
Telegram认证脚本
用于初次登录和验证Telegram账户
"""

import asyncio
from telethon import TelegramClient
import sys
import os

async def authenticate_telegram():
    """执行Telegram认证流程"""
    
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
                for i, group in enumerate(groups[:5]):
                    print(f"  {i+1}. {group.name} - ID: {group.entity.id}")
                
                # 测试获取第一个群组的消息
                test_group = groups[0]
                print(f"\n测试获取群组 \"{test_group.name}\" 的消息:")
                
                messages = []
                async for message in client.iter_messages(test_group.entity, limit=3):
                    if message.text:
                        # 处理发送者信息
                        sender_name = 'Unknown'
                        if message.sender:
                            if hasattr(message.sender, 'first_name'):
                                sender_name = message.sender.first_name
                            elif hasattr(message.sender, 'title'):
                                sender_name = message.sender.title
                            elif hasattr(message.sender, 'username'):
                                sender_name = message.sender.username
                        
                        messages.append({
                            'id': message.id,
                            'text': message.text[:80] + '...' if len(message.text) > 80 else message.text,
                            'sender': sender_name,
                            'date': message.date
                        })
                
                print(f"✓ 成功获取 {len(messages)} 条消息")
                for msg in messages:
                    print(f"  - [{msg['id']}] {msg['sender']}: {msg['text']}")
                    
                print("\n✅ 群组消息获取功能正常!")
                
        else:
            print("需要进行手机号码验证...")
            
            # 输入手机号码
            phone = input("请输入手机号码 (格式: +1234567890): ")
            
            # 发送验证码
            await client.send_code_request(phone)
            print("验证码已发送到您的手机")
            
            # 输入验证码
            code = input("请输入验证码: ")
            
            try:
                # 验证登录
                await client.sign_in(phone, code)
                print("✓ 登录成功!")
                
                # 获取用户信息
                me = await client.get_me()
                print(f"✓ 当前用户: {me.first_name} (@{me.username})")
                
                print("认证完成，可以开始使用Telegram服务")
                
            except Exception as auth_error:
                print(f"✗ 认证失败: {auth_error}")
                
                # 检查是否需要两步验证
                if "Two-step verification" in str(auth_error):
                    password = input("请输入两步验证密码: ")
                    await client.sign_in(password=password)
                    print("✓ 两步验证成功!")
                else:
                    raise auth_error
        
        await client.disconnect()
        
    except Exception as e:
        print(f"✗ 认证过程出错: {e}")
        await client.disconnect()
        sys.exit(1)

if __name__ == "__main__":
    print("Telegram认证脚本")
    print("=" * 50)
    
    # 运行认证
    asyncio.run(authenticate_telegram())