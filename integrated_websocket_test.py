#!/usr/bin/env python3
"""
在同一个事件循环中测试WebSocket连接和消息发送
"""
import asyncio
import websockets
import json
import logging
import sys

sys.path.insert(0, '/root/project/TgGod/backend')

from app.websocket.manager import websocket_manager
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def integrated_websocket_test():
    """集成测试：连接WebSocket并发送消息"""
    client_id = "integrated_test_client"
    uri = f"ws://localhost:8000/ws/{client_id}"
    
    logger.info(f"🔗 连接WebSocket: {uri}")
    
    # 创建WebSocket连接任务
    async def websocket_client():
        try:
            async with websockets.connect(uri) as websocket:
                logger.info("✅ WebSocket连接建立")
                
                # 监听消息
                while True:
                    message = await websocket.recv()
                    parsed = json.loads(message)
                    
                    if parsed.get("type") == "monthly_sync_progress":
                        data = parsed["data"]
                        logger.info(f"📊 收到进度: {data['currentMonth']} - {data['progress']}/{data['total']}")
                    elif parsed.get("type") == "monthly_sync_complete":
                        data = parsed["data"]
                        logger.info(f"✅ 收到完成: 成功={data.get('success')}")
                        break
                    else:
                        logger.info(f"📨 收到消息: {parsed.get('type')}")
                        
        except Exception as e:
            logger.error(f"WebSocket客户端错误: {e}")
    
    # 创建消息发送任务
    async def message_sender():
        # 等待连接建立
        await asyncio.sleep(2)
        
        # 直接检查websocket_manager的状态
        logger.info("🔍 检查WebSocket管理器状态...")
        clients = websocket_manager.get_connected_clients()
        logger.info(f"管理器显示的客户端: {clients}")
        
        # 检查活跃连接
        active_connections = websocket_manager.active_connections
        logger.info(f"活跃连接数: {len(active_connections)}")
        logger.info(f"连接键值: {list(active_connections.keys())}")
        
        if not clients:
            logger.warning("⚠️  管理器中没有客户端，尝试直接发送...")
            
            # 尝试直接使用连接字典
            for conn_id, connection in active_connections.items():
                logger.info(f"🎯 尝试发送给连接: {conn_id}")
                try:
                    test_message = {
                        "type": "monthly_sync_progress",
                        "data": {
                            "currentMonth": "2025-07",
                            "progress": 1,
                            "total": 1,
                            "completed": 0,
                            "failed": 0
                        },
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    await connection.send_text(json.dumps(test_message))
                    logger.info(f"✅ 消息发送成功给: {conn_id}")
                    
                    await asyncio.sleep(1)
                    
                    complete_message = {
                        "type": "monthly_sync_complete",
                        "data": {
                            "success": True,
                            "total_messages": 42
                        },
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    await connection.send_text(json.dumps(complete_message))
                    logger.info(f"✅ 完成消息发送成功给: {conn_id}")
                    
                except Exception as e:
                    logger.error(f"❌ 发送失败给 {conn_id}: {e}")
        else:
            logger.info(f"📤 通过管理器发送消息给 {len(clients)} 个客户端")
            # 正常发送逻辑...
    
    # 并行运行两个任务
    try:
        await asyncio.gather(
            websocket_client(),
            message_sender(),
            return_exceptions=True
        )
    except Exception as e:
        logger.error(f"测试失败: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🔬 启动集成WebSocket测试...")
    success = asyncio.run(integrated_websocket_test())
    if success:
        print("✅ 集成测试完成")
    else:
        print("❌ 集成测试失败")