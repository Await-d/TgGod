#!/usr/bin/env python3
"""
在HTTP请求上下文中测试WebSocket管理器状态
"""
import requests
import time
import json

def test_websocket_via_api():
    """通过API端点测试WebSocket管理器状态"""
    
    # 等待WebSocket连接建立
    print("等待3秒让WebSocket连接建立...")
    time.sleep(3)
    
    # 调用一个API端点来触发WebSocket调试
    try:
        # 模拟一个会访问websocket_manager的API调用
        response = requests.post(
            "http://localhost:8000/api/telegram/groups/1/sync-monthly",
            json={"months": [{"year": 2025, "month": 7}]},
            timeout=10
        )
        
        print(f"API响应: {response.status_code}")
        print(f"响应内容: {response.text}")
        
        return True
        
    except Exception as e:
        print(f"API调用失败: {e}")
        return False

if __name__ == "__main__":
    print("📞 通过API测试WebSocket管理器...")
    print("请确保WebSocket监听器正在运行")
    
    success = test_websocket_via_api()
    print(f"测试结果: {'成功' if success else '失败'}")