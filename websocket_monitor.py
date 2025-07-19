#!/usr/bin/env python3
"""
检查WebSocket连接状态和发送测试消息
"""
import asyncio
import websockets
import json
import logging
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_websocket_with_monitoring():
    """测试WebSocket连接并监听消息"""
    client_id = "test_monitor_client"
    uri = f"ws://localhost:8000/ws/{client_id}"
    
    logger.info(f"连接到WebSocket: {uri}")
    
    try:
        async with websockets.connect(uri) as websocket:
            logger.info("✅ WebSocket连接建立成功")
            
            # 发送ping测试连接
            ping_message = {"type": "ping", "timestamp": "2025-07-13T05:30:00Z"}
            await websocket.send(json.dumps(ping_message))
            logger.info(f"📤 发送ping: {ping_message}")
            
            # 等待响应
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                logger.info(f"📥 收到响应: {response}")
            except asyncio.TimeoutError:
                logger.warning("⏰ ping响应超时")
            
            # 监听消息30秒
            logger.info("🔍 开始监听WebSocket消息...")
            logger.info("现在可以在前端触发月度同步，我将监听所有消息")
            
            try:
                while True:
                    message = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                    parsed = json.loads(message)
                    logger.info(f"📨 收到消息: {parsed}")
                    
                    if parsed.get("type") == "monthly_sync_progress":
                        logger.info(f"🎯 检测到月度同步进度消息: {parsed}")
                    elif parsed.get("type") == "monthly_sync_complete":
                        logger.info(f"✅ 检测到月度同步完成消息: {parsed}")
                        
            except asyncio.TimeoutError:
                logger.info("⏰ 30秒内未收到消息，监听结束")
            
    except Exception as e:
        logger.error(f"❌ WebSocket连接失败: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("启动WebSocket监听器...")
    print("请在前端点击月度同步按钮，我将监听所有WebSocket消息")
    asyncio.run(test_websocket_with_monitoring())