#!/usr/bin/env python3
"""
WebSocket connection test script
"""
import asyncio
import websockets
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_websocket():
    """Test WebSocket connection to the backend"""
    client_id = "test_client_python"
    uri = f"ws://localhost:8000/ws/{client_id}"
    
    logger.info(f"Attempting to connect to: {uri}")
    
    try:
        async with websockets.connect(uri) as websocket:
            logger.info("✅ WebSocket connection established")
            
            # Send a test message
            test_message = {
                "type": "ping",
                "timestamp": "2025-07-13T05:12:00Z"
            }
            
            await websocket.send(json.dumps(test_message))
            logger.info(f"📤 Sent message: {test_message}")
            
            # Wait for response
            response = await websocket.recv()
            logger.info(f"📥 Received response: {response}")
            
            # Parse response
            try:
                parsed_response = json.loads(response)
                if parsed_response.get("type") == "pong":
                    logger.info("✅ Ping-pong test successful")
                else:
                    logger.info(f"📋 Received: {parsed_response}")
            except json.JSONDecodeError:
                logger.info(f"📋 Raw response: {response}")
                
    except Exception as e:
        logger.error(f"❌ WebSocket connection failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = asyncio.run(test_websocket())
    if success:
        print("✅ WebSocket test passed")
    else:
        print("❌ WebSocket test failed")