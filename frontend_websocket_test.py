#!/usr/bin/env python3
"""
模拟前端WebSocket连接并监听消息
"""
import asyncio
import websockets
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def frontend_websocket_test():
    """模拟前端WebSocket连接"""
    client_id = "frontend_test_client"
    uri = f"ws://localhost:8000/ws/{client_id}"
    
    logger.info(f"🔌 前端模拟连接: {uri}")
    
    try:
        async with websockets.connect(uri) as websocket:
            logger.info("✅ 前端WebSocket连接成功")
            
            # 发送订阅消息（模拟前端订阅）
            subscribe_message = {
                "type": "subscribe_monthly_sync",
                "timestamp": "2025-07-13T06:00:00Z"
            }
            
            await websocket.send(json.dumps(subscribe_message))
            logger.info("📫 已发送订阅消息")
            
            # 监听60秒
            logger.info("👂 开始监听WebSocket消息（60秒）...")
            logger.info("请在另一个终端运行: python mock_sync_progress.py")
            
            try:
                while True:
                    message = await asyncio.wait_for(websocket.recv(), timeout=60.0)
                    parsed = json.loads(message)
                    
                    if parsed.get("type") == "monthly_sync_progress":
                        data = parsed["data"]
                        logger.info(f"📊 进度更新: {data['currentMonth']} - {data['progress']}/{data['total']}")
                    elif parsed.get("type") == "monthly_sync_complete":
                        data = parsed["data"]
                        if data.get("success"):
                            logger.info(f"✅ 同步完成: 总计 {data.get('total_messages', 0)} 条消息")
                        else:
                            logger.error(f"❌ 同步失败: {data.get('error', '未知错误')}")
                        break
                    else:
                        logger.info(f"📨 其他消息: {parsed}")
                        
            except asyncio.TimeoutError:
                logger.info("⏰ 60秒监听超时")
            
    except Exception as e:
        logger.error(f"❌ 前端WebSocket连接失败: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🖥️  启动前端WebSocket测试...")
    success = asyncio.run(frontend_websocket_test())
    if success:
        print("✅ 前端WebSocket测试完成")
    else:
        print("❌ 前端WebSocket测试失败")