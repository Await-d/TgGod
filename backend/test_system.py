#!/usr/bin/env python3
"""
TgGod 系统功能测试脚本
测试配置、连接、API功能等
"""

import asyncio
import requests
import json
import time
from datetime import datetime

# 配置
API_BASE_URL = "http://localhost:8001"
TELEGRAM_API_ID = 27902826
TELEGRAM_API_HASH = "76e23a2f92b8a3a75963d851fbcb4384"

def test_api_health():
    """测试API健康状态"""
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        if response.status_code == 200:
            print("✅ API服务健康检查通过")
            return True
        else:
            print(f"❌ API服务健康检查失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API服务连接失败: {e}")
        return False

def test_telegram_auth_status():
    """测试Telegram认证状态"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/telegram/auth/status")
        if response.status_code == 200:
            data = response.json()
            if data.get("is_authorized"):
                print("✅ Telegram用户已认证")
                user_info = data.get("user_info", {})
                print(f"   用户: {user_info.get('name', 'N/A')}")
                print(f"   用户名: @{user_info.get('username', 'N/A')}")
                return True
            else:
                print("⚠️  Telegram用户未认证")
                print(f"   状态: {data.get('message', 'N/A')}")
                return False
        else:
            print(f"❌ 认证状态检查失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 认证状态检查错误: {e}")
        return False

def test_groups_api():
    """测试群组相关API"""
    try:
        # 获取群组列表
        response = requests.get(f"{API_BASE_URL}/api/telegram/groups")
        if response.status_code == 200:
            groups = response.json()
            print(f"✅ 群组列表获取成功: {len(groups)} 个群组")
            if groups:
                for group in groups[:3]:  # 显示前3个群组
                    print(f"   - {group.get('title', 'N/A')} (@{group.get('username', 'N/A')})")
            return len(groups) > 0
        else:
            print(f"❌ 群组列表获取失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 群组API测试错误: {e}")
        return False

def test_sync_groups():
    """测试同步群组功能"""
    try:
        response = requests.post(f"{API_BASE_URL}/api/telegram/sync-groups")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 群组同步测试完成")
            print(f"   成功: {data.get('success', False)}")
            print(f"   消息: {data.get('message', 'N/A')}")
            return data.get('success', False)
        else:
            print(f"❌ 群组同步失败: {response.status_code}")
            try:
                error = response.json()
                print(f"   错误: {error.get('detail', 'N/A')}")
            except:
                pass
            return False
    except Exception as e:
        print(f"❌ 群组同步错误: {e}")
        return False

def test_monthly_sync_api():
    """测试按月同步API"""
    try:
        # 测试批量按月同步
        months = [
            {"year": 2025, "month": 7},
            {"year": 2025, "month": 6},
            {"year": 2025, "month": 5}
        ]
        
        payload = {"months": months}
        response = requests.post(
            f"{API_BASE_URL}/api/telegram/sync-all-groups-monthly",
            json=payload
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ 按月同步API测试完成")
            print(f"   总群组: {data.get('total_groups', 0)}")
            print(f"   成功同步: {data.get('synced_groups', 0)}")
            print(f"   总消息: {data.get('total_messages', 0)}")
            return True
        else:
            print(f"❌ 按月同步API失败: {response.status_code}")
            try:
                error = response.json()
                print(f"   错误: {error.get('detail', 'N/A')}")
            except:
                pass
            return False
    except Exception as e:
        print(f"❌ 按月同步API错误: {e}")
        return False

def test_telegram_config():
    """测试Telegram配置"""
    try:
        import os
        os.environ['TELEGRAM_API_ID'] = str(TELEGRAM_API_ID)
        os.environ['TELEGRAM_API_HASH'] = TELEGRAM_API_HASH
        
        from app.config import Settings
        settings = Settings()
        
        print("✅ Telegram配置测试")
        print(f"   API ID: {settings.telegram_api_id}")
        print(f"   API Hash: {settings.telegram_api_hash[:10]}...")
        print(f"   数据库: {settings.database_url}")
        
        return settings.telegram_api_id != 0 and settings.telegram_api_hash != ""
    except Exception as e:
        print(f"❌ Telegram配置测试失败: {e}")
        return False

async def test_telegram_client():
    """测试Telegram客户端连接"""
    try:
        import os
        os.environ['TELEGRAM_API_ID'] = str(TELEGRAM_API_ID)
        os.environ['TELEGRAM_API_HASH'] = TELEGRAM_API_HASH
        
        from app.services.telegram_service import TelegramService
        
        service = TelegramService()
        await service.initialize()
        
        print("✅ Telegram客户端连接成功")
        
        # 检查认证状态
        if await service.client.is_user_authorized():
            print("✅ 用户已认证")
            me = await service.client.get_me()
            print(f"   用户: {me.first_name} {me.last_name or ''}")
            print(f"   用户名: @{me.username or '无'}")
            print(f"   手机: {me.phone or '未设置'}")
            auth_status = True
        else:
            print("⚠️  用户未认证")
            auth_status = False
        
        await service.disconnect()
        return auth_status
    except Exception as e:
        print(f"❌ Telegram客户端测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("=" * 60)
    print("TgGod 系统功能测试")
    print("=" * 60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"API地址: {API_BASE_URL}")
    print(f"API ID: {TELEGRAM_API_ID}")
    print(f"API Hash: {TELEGRAM_API_HASH[:10]}...")
    print("=" * 60)
    
    results = {}
    
    # 1. 测试API健康状态
    print("\n1. 测试API健康状态...")
    results['api_health'] = test_api_health()
    
    # 2. 测试Telegram配置
    print("\n2. 测试Telegram配置...")
    results['telegram_config'] = test_telegram_config()
    
    # 3. 测试Telegram客户端
    print("\n3. 测试Telegram客户端...")
    results['telegram_client'] = asyncio.run(test_telegram_client())
    
    # 4. 测试认证状态
    print("\n4. 测试认证状态...")
    results['auth_status'] = test_telegram_auth_status()
    
    # 5. 测试群组API
    print("\n5. 测试群组API...")
    results['groups_api'] = test_groups_api()
    
    # 6. 测试同步群组
    print("\n6. 测试同步群组...")
    results['sync_groups'] = test_sync_groups()
    
    # 7. 测试按月同步API
    print("\n7. 测试按月同步API...")
    results['monthly_sync'] = test_monthly_sync_api()
    
    # 测试结果汇总
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name.ljust(20)}: {status}")
        if result:
            passed += 1
    
    print(f"\n总体结果: {passed}/{total} 项测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！系统运行正常")
    elif passed >= total * 0.7:
        print("⚠️  大部分测试通过，但有一些问题需要注意")
    else:
        print("❌ 多项测试失败，需要检查系统配置")
    
    print("\n" + "=" * 60)
    print("使用说明:")
    print("1. 如果用户未认证，请先通过Web界面进行Telegram登录")
    print("2. 认证后可以使用群组同步和按月同步功能")
    print("3. 访问 http://localhost:8001/docs 查看完整API文档")
    print("=" * 60)

if __name__ == "__main__":
    main()