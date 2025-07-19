#!/usr/bin/env python3
"""
发送模拟的月度同步进度消息到WebSocket，测试前端接收
"""
import asyncio
import json
import logging
import sys
import os

sys.path.insert(0, '/root/project/TgGod/backend')

from app.websocket.manager import websocket_manager
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def send_mock_progress_messages():
    """发送模拟的月度同步进度消息"""
    
    # 等待连接建立
    await asyncio.sleep(3)
    
    connected_clients = websocket_manager.get_connected_clients()
    logger.info(f"📊 连接的客户端: {len(connected_clients)} 个")
    
    if not connected_clients:
        logger.warning("❌ 没有客户端连接")
        return False
    
    # 发送开始消息
    start_message = {
        "type": "monthly_sync_progress",
        "data": {
            "currentMonth": "2025-07",
            "progress": 0,
            "total": 3,
            "completed": 0,
            "failed": 0
        },
        "timestamp": datetime.now().isoformat()
    }
    
    # 发送进度消息序列
    for i in range(4):
        if i < 3:
            progress_message = {
                "type": "monthly_sync_progress",
                "data": {
                    "currentMonth": f"2025-{7-i:02d}",
                    "progress": i + 1,
                    "total": 3,
                    "completed": i,
                    "failed": 0
                },
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"📤 发送进度消息 {i+1}/3: {progress_message['data']['currentMonth']}")
            
            for client_id in connected_clients:
                await websocket_manager.send_message(client_id, progress_message)
            
            await asyncio.sleep(2)
        else:
            # 发送完成消息
            complete_message = {
                "type": "monthly_sync_complete",
                "data": {
                    "success": True,
                    "total_messages": 150,
                    "months_synced": 3,
                    "failed_months": [],
                    "monthly_stats": [
                        {"year": 2025, "month": 7, "total_messages": 50, "saved_messages": 50},
                        {"year": 2025, "month": 6, "total_messages": 50, "saved_messages": 50},
                        {"year": 2025, "month": 5, "total_messages": 50, "saved_messages": 50}
                    ]
                },
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"✅ 发送完成消息")
            
            for client_id in connected_clients:
                await websocket_manager.send_message(client_id, complete_message)
    
    return True

if __name__ == "__main__":
    print("🎭 发送模拟月度同步进度消息...")
    print("请在前端打开月度同步模态框来测试接收")
    
    result = asyncio.run(send_mock_progress_messages())
    if result:
        print("✅ 模拟消息发送完成")
    else:
        print("❌ 模拟消息发送失败")