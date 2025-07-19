#!/usr/bin/env python3
"""
直接测试WebSocket消息发送，绕过月度同步逻辑
"""
import asyncio
import json
import logging
import sys
import os

# 添加backend路径以便导入模块
sys.path.insert(0, '/root/project/TgGod/backend')

from app.websocket.manager import websocket_manager
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_direct_websocket_send():
    """直接通过WebSocket管理器发送测试消息"""
    
    # 等待一下让其他连接建立
    await asyncio.sleep(2)
    
    # 获取连接的客户端
    connected_clients = websocket_manager.get_connected_clients()
    logger.info(f"当前连接的客户端数量: {len(connected_clients)}")
    logger.info(f"客户端列表: {connected_clients}")
    
    if not connected_clients:
        logger.warning("没有客户端连接，无法发送消息")
        return False
    
    # 发送测试进度消息
    progress_message = {
        "type": "monthly_sync_progress",
        "data": {
            "currentMonth": "2025-07",
            "progress": 1,
            "total": 3,
            "completed": 0,
            "failed": 0
        },
        "timestamp": datetime.now().isoformat()
    }
    
    logger.info(f"🔄 发送测试进度消息: {progress_message}")
    
    for client_id in connected_clients:
        try:
            await websocket_manager.send_message(client_id, progress_message)
            logger.info(f"✅ 消息已发送给客户端: {client_id}")
        except Exception as e:
            logger.error(f"❌ 发送给客户端 {client_id} 失败: {e}")
    
    # 等待一会儿
    await asyncio.sleep(2)
    
    # 发送完成消息
    complete_message = {
        "type": "monthly_sync_complete",
        "data": {
            "success": True,
            "total_messages": 100,
            "months_synced": 1,
            "failed_months": [],
            "monthly_stats": []
        },
        "timestamp": datetime.now().isoformat()
    }
    
    logger.info(f"✅ 发送测试完成消息: {complete_message}")
    
    for client_id in connected_clients:
        try:
            await websocket_manager.send_message(client_id, complete_message)
            logger.info(f"✅ 完成消息已发送给客户端: {client_id}")
        except Exception as e:
            logger.error(f"❌ 发送给客户端 {client_id} 失败: {e}")
    
    return True

if __name__ == "__main__":
    print("📡 直接测试WebSocket消息发送...")
    print("请在另一个终端运行 websocket_monitor.py 来接收消息")
    print("等待3秒后开始发送...")
    
    result = asyncio.run(test_direct_websocket_send())
    if result:
        print("✅ WebSocket消息发送测试完成")
    else:
        print("❌ WebSocket消息发送测试失败")