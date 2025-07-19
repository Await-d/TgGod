#!/usr/bin/env python3
"""
通过FastAPI应用上下文检查WebSocket状态
"""
import requests
import time

def check_websocket_status():
    """通过API检查WebSocket状态"""
    
    print("🔍 检查WebSocket管理器状态...")
    
    # 调用健康检查确保API工作
    try:
        health_response = requests.get("http://localhost:8000/health", timeout=5)
        print(f"健康检查: {health_response.status_code}")
    except Exception as e:
        print(f"API不可用: {e}")
        return False
    
    # 触发一个会访问websocket_manager的操作
    try:
        # 这个API调用会在同步任务中访问websocket_manager
        sync_response = requests.post(
            "http://localhost:8000/api/telegram/groups/1/sync-monthly",
            json={"months": [{"year": 2025, "month": 7}]},
            timeout=10
        )
        
        print(f"同步API调用: {sync_response.status_code}")
        print(f"响应: {sync_response.text}")
        
        return True
        
    except Exception as e:
        print(f"同步API调用失败: {e}")
        return False

if __name__ == "__main__":
    print("📡 通过API检查WebSocket状态...")
    success = check_websocket_status()
    print(f"结果: {'成功' if success else '失败'}")