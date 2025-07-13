from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        """接受WebSocket连接"""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"Client {client_id} connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, client_id: str):
        """断开WebSocket连接"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"Client {client_id} disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: dict, client_id: str):
        """发送个人消息"""
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending message to {client_id}: {e}")
                self.disconnect(client_id)
    
    async def broadcast(self, message: dict):
        """广播消息给所有连接的客户端"""
        disconnected_clients = []
        
        for client_id, connection in self.active_connections.items():
            try:
                await connection.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error broadcasting to {client_id}: {e}")
                disconnected_clients.append(client_id)
        
        # 清理断开的连接
        for client_id in disconnected_clients:
            self.disconnect(client_id)
    
    async def send_log(self, log_data: dict, client_id: str = None):
        """发送日志消息"""
        message = {
            "type": "log",
            "data": log_data,
            "timestamp": datetime.now().isoformat()
        }
        
        if client_id:
            await self.send_personal_message(message, client_id)
        else:
            await self.broadcast(message)
    
    async def send_progress(self, progress_data: dict, client_id: str = None):
        """发送进度更新"""
        message = {
            "type": "progress",
            "data": progress_data,
            "timestamp": datetime.now().isoformat()
        }
        
        if client_id:
            await self.send_personal_message(message, client_id)
        else:
            await self.broadcast(message)
    
    async def send_status(self, status_data: dict, client_id: str = None):
        """发送状态更新"""
        message = {
            "type": "status",
            "data": status_data,
            "timestamp": datetime.now().isoformat()
        }
        
        if client_id:
            await self.send_personal_message(message, client_id)
        else:
            await self.broadcast(message)
    
    async def send_notification(self, notification_data: dict, client_id: str = None):
        """发送通知"""
        message = {
            "type": "notification",
            "data": notification_data,
            "timestamp": datetime.now().isoformat()
        }
        
        if client_id:
            await self.send_personal_message(message, client_id)
        else:
            await self.broadcast(message)
    
    def get_connection_count(self) -> int:
        """获取当前连接数"""
        return len(self.active_connections)
    
    def get_connected_clients(self) -> List[str]:
        """获取已连接的客户端列表"""
        clients = list(self.active_connections.keys())
        logger.debug(f"当前连接的客户端: {clients}")
        return clients
    
    async def send_message(self, client_id: str, message_data: dict):
        """发送消息到特定客户端，支持自定义消息类型"""
        logger.info(f"尝试发送消息到客户端 {client_id}, 消息类型: {message_data.get('type', 'unknown')}")
        
        if client_id in self.active_connections:
            try:
                message_json = json.dumps(message_data)
                await self.active_connections[client_id].send_text(message_json)
                logger.info(f"消息成功发送到 {client_id}: {message_data.get('type', 'unknown')}")
            except Exception as e:
                logger.error(f"发送消息到 {client_id} 失败: {e}")
                self.disconnect(client_id)
        else:
            logger.warning(f"客户端 {client_id} 不在活跃连接列表中，当前连接: {list(self.active_connections.keys())}")
    
    async def send_realtime_message(self, message_data: dict, client_id: str = None):
        """发送实时消息（保持原有方法兼容性）"""
        message = {
            "type": "message",
            "data": message_data,
            "timestamp": datetime.now().isoformat()
        }
        
        if client_id:
            await self.send_personal_message(message, client_id)
        else:
            await self.broadcast(message)
    
    async def send_group_status(self, group_status_data: dict, client_id: str = None):
        """发送群组状态更新"""
        message = {
            "type": "group_status",
            "data": group_status_data,
            "timestamp": datetime.now().isoformat()
        }
        
        if client_id:
            await self.send_personal_message(message, client_id)
        else:
            await self.broadcast(message)
    
    async def send_message_stats(self, stats_data: dict, client_id: str = None):
        """发送消息统计更新"""
        message = {
            "type": "message_stats",
            "data": stats_data,
            "timestamp": datetime.now().isoformat()
        }
        
        if client_id:
            await self.send_personal_message(message, client_id)
        else:
            await self.broadcast(message)

# 创建全局WebSocket管理器实例
websocket_manager = WebSocketManager()