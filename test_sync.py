#!/usr/bin/env python3
"""
简单测试脚本，用于测试群组同步功能
"""

import requests
import json

def test_sync_groups():
    """测试同步群组功能"""
    
    # 首先测试连接
    print("1. 测试Telegram连接...")
    try:
        response = requests.post("http://localhost:8001/api/telegram/test-connection")
        print(f"Status code: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"连接测试: {result}")
            
            if not result.get("success"):
                print("❌ 连接失败，请检查Telegram认证状态")
                return False
        else:
            print(f"❌ API调用失败: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 连接测试失败: {e}")
        return False
    
    # 测试同步群组
    print("\n2. 测试同步群组...")
    try:
        response = requests.post("http://localhost:8001/api/telegram/sync-groups")
        result = response.json()
        print(f"同步结果: {result}")
        
        if result.get("success"):
            print(f"✅ 同步成功: {result.get('synced_count', 0)} 个群组")
        else:
            print(f"❌ 同步失败: {result.get('message', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ 同步失败: {e}")
        return False
    
    # 测试获取群组列表
    print("\n3. 测试获取群组列表...")
    try:
        response = requests.get("http://localhost:8001/api/telegram/groups")
        groups = response.json()
        print(f"群组数量: {len(groups)}")
        for group in groups[:3]:  # 显示前3个群组
            print(f"  - {group.get('title', 'Unknown')} (@{group.get('username', 'no_username')})")
            
    except Exception as e:
        print(f"❌ 获取群组列表失败: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🔧 Telegram群组同步测试")
    print("=" * 40)
    
    success = test_sync_groups()
    
    if success:
        print("\n✅ 所有测试通过！")
    else:
        print("\n❌ 测试失败，请检查后端服务和认证状态")