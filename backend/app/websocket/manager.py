"""TgGod WebSocket管理器模块

该模块提供实时WebSocket连接管理和消息推送功能，包括:

- WebSocket连接的创建和管理
- 客户端连接状态跟踪
- 实时消息广播和单播
- 多种消息类型支持
- 连接断开检测和清理
- 错误处理和日志记录

Message Types:
    - log: 日志消息
    - progress: 进度更新
    - status: 状态更新
    - notification: 系统通知
    - message: 实时消息
    - group_status: 群组状态
    - message_stats: 消息统计

Features:
    - 并发连接支持
    - 自动断开检测和清理
    - 消息格式标准化
    - 类型安全的消息传输
    - 实时状态监控
    - 广播和单播支持

Author: TgGod Team
Version: 1.0.0
"""

from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class WebSocketManager:
    """实时WebSocket连接管理器

    管理所有客户端的WebSocket连接，提供消息广播、单播和
    连接状态管理功能。支持实时推送系统状态、任务进度、
    日志信息和通知消息。

    Attributes:
        active_connections (Dict[str, WebSocket]): 活跃连接字典，键为客户端ID

    Methods:
        connect(): 建立新的WebSocket连接
        disconnect(): 断开指定客户端连接
        send_personal_message(): 发送个人消息
        broadcast(): 广播消息给所有客户端
        send_log(): 发送日志消息
        send_progress(): 发送进度更新
        send_status(): 发送状态更新
        send_notification(): 发送通知消息

    Features:
        - 自动连接故障检测和清理
        - JSON消息序列化和反序列化
        - 并发安全的消息发送
        - 详细的错误日志和调试信息
        - 客户端状态实时监控

    Note:
        该类设计为单例模式，全局共享连接管理器实例
    """
    def __init__(self):
        """初始化WebSocket管理器

        创建空的活跃连接字典。
        """
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        """建立新的WebSocket连接

        接受客户端的WebSocket连接请求并将其添加到活跃连接列表。

        Args:
            websocket (WebSocket): FastAPI WebSocket实例
            client_id (str): 客户端唯一标识符

        Process:
            1. 接受WebSocket连接请求
            2. 将连接添加到活跃连接字典
            3. 记录连接信息和统计数据

        Note:
            - client_id必须唯一，重复的ID会覆盖之前的连接
            - 连接成功后客户端可以接收实时消息
        """
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"Client {client_id} connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, client_id: str):
        """断开指定客户端的WebSocket连接

        从活跃连接列表中移除指定的客户端连接。

        Args:
            client_id (str): 要断开的客户端ID

        Process:
            1. 检查客户端是否在活跃连接列表中
            2. 从字典中移除连接
            3. 记录断开信息和统计数据

        Note:
            - 此方法不会主动关闭WebSocket连接
            - 通常在发送消息失败时自动调用
            - 客户端主动断开时也会调用
        """
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"Client {client_id} disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: dict, client_id: str):
        """发送消息给指定客户端

        向特定的客户端发送JSON格式的消息。

        Args:
            message (dict): 要发送的消息字典
            client_id (str): 目标客户端ID

        Process:
            1. 检查客户端是否在活跃连接列表中
            2. 将消息序列化为JSON字符串
            3. 通过WebSocket发送消息
            4. 处理发送失败的情况

        Error Handling:
            - 发送失败时自动断开连接
            - 记录错误日志供调试

        Note:
            - 如果客户端不存在，静默忽略
            - 支持任意复杂的JSON数据结构
        """
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending message to {client_id}: {e}")
                self.disconnect(client_id)
    
    async def broadcast(self, message: dict):
        """广播消息给所有连接的客户端

        同时向所有活跃的WebSocket连接发送相同的消息。

        Args:
            message (dict): 要广播的消息字典

        Process:
            1. 遍历所有活跃连接
            2. 尝试向每个客户端发送消息
            3. 收集发送失败的客户端
            4. 清理断开的连接

        Error Handling:
            - 单个客户端发送失败不影响其他客户端
            - 自动清理断开的连接
            - 记录所有错误信息

        Use Cases:
            - 系统状态更新
            - 公告和通知
            - 实时数据同步

        Note:
            - 高并发情况下可能较慢
            - 大消息可能影响性能
        """
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
        """发送日志消息到客户端

        将系统日志信息实时推送给客户端，用于实时监控和调试。

        Args:
            log_data (dict): 日志数据，包含级别、消息、模块等信息
            client_id (str, optional): 目标客户端ID，为None时广播

        Message Format:
            {
                "type": "log",
                "data": log_data,
                "timestamp": "2023-01-01T00:00:00"
            }

        Use Cases:
            - 实时日志监控
            - 错误信息推送
            - 系统调试信息
            - 操作日志记录

        Note:
            - 自动添加时间戳
            - 支持广播和单播模式
        """
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
        """发送任务进度更新消息

        实时推送任务执行进度，用于显示下载、同步等操作的进度。

        Args:
            progress_data (dict): 进度数据，包含百分比、当前项、总数等
            client_id (str, optional): 目标客户端ID，为None时广播

        Expected Data Format:
            {
                "task_id": "unique_task_id",
                "percentage": 75,
                "current": 75,
                "total": 100,
                "message": "正在处理...",
                "speed": "1.2 MB/s"
            }

        Message Format:
            {
                "type": "progress",
                "data": progress_data,
                "timestamp": "2023-01-01T00:00:00"
            }

        Use Cases:
            - 文件下载进度
            - 消息同步进度
            - 数据导入进度
            - 任务执行状态

        Note:
            - 频繁更新可能影响性能
            - 建议限制更新频率
        """
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
        """发送系统或任务状态更新

        推送系统组件、服务或任务的状态变更信息。

        Args:
            status_data (dict): 状态数据，包含状态值、组件名称等
            client_id (str, optional): 目标客户端ID，为None时广播

        Expected Data Format:
            {
                "component": "telegram_service",
                "status": "connected",
                "message": "连接正常",
                "details": {...}
            }

        Message Format:
            {
                "type": "status",
                "data": status_data,
                "timestamp": "2023-01-01T00:00:00"
            }

        Status Types:
            - connected/disconnected: 连接状态
            - running/stopped/paused: 运行状态
            - healthy/error/warning: 健康状态
            - active/inactive: 激活状态

        Use Cases:
            - Telegram连接状态
            - 数据库连接状态
            - 任务调度器状态
            - 服务健康检查

        Note:
            - 状态变更时及时推送
            - 客户端可根据状态调整UI
        """
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
        """发送系统通知消息

        发送用户通知、警告或提示信息给客户端。

        Args:
            notification_data (dict): 通知数据，包含标题、内容、类型等
            client_id (str, optional): 目标客户端ID，为None时广播

        Expected Data Format:
            {
                "title": "通知标题",
                "message": "通知内容",
                "type": "info|success|warning|error",
                "duration": 3000,
                "action": {
                    "label": "查看详情",
                    "url": "/tasks/123"
                }
            }

        Message Format:
            {
                "type": "notification",
                "data": notification_data,
                "timestamp": "2023-01-01T00:00:00"
            }

        Notification Types:
            - info: 一般信息
            - success: 成功消息
            - warning: 警告信息
            - error: 错误信息

        Use Cases:
            - 任务完成通知
            - 错误警告
            - 系统维护通知
            - 新消息提醒

        Note:
            - 客户端应显示为弹窗或通知栏
            - 支持操作按钮和链接
        """
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
        """获取当前WebSocket连接数量

        返回当前活跃的WebSocket连接数量。

        Returns:
            int: 活跃连接的数量

        Use Cases:
            - 系统监控和统计
            - 负载评估
            - 连接状态检查
            - 性能分析

        Note:
            - 实时返回当前状态
            - 不包括断开的连接
        """
        return len(self.active_connections)
    
    def get_connected_clients(self) -> List[str]:
        """获取当前所有活跃客户端的ID列表

        返回所有当前连接的客户端ID列表。

        Returns:
            List[str]: 客户端ID列表

        Use Cases:
            - 连接状态检查
            - 系统调试和监控
            - 客户端管理
            - 连接分析

        Note:
            - 返回的是客户端ID列表，不是WebSocket实例
            - 可用于检查特定客户端是否在线
        """
        clients = list(self.active_connections.keys())
        logger.debug(f"当前连接的客户端: {clients}")
        return clients
    
    async def send_message(self, client_id: str, message_data: dict):
        """发送自定义消息到指定客户端

        支持发送任意类型的自定义消息，不限制消息格式。

        Args:
            client_id (str): 目标客户端ID
            message_data (dict): 完整的消息数据，包含type字段

        Expected Format:
            {
                "type": "custom_message_type",
                "data": {...},
                "other_fields": "..."
            }

        Process:
            1. 检查客户端连接状态
            2. 将消息序列化为JSON
            3. 发送消息并记录结果
            4. 处理发送失败情况

        Features:
            - 支持任意消息类型
            - 详细的日志记录
            - 自动连接清理
            - 错误处理

        Note:
            - 与其他send_*方法不同，不会自动添加timestamp
            - 需要客户端在活跃连接列表中
        """
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
        """发送实时消息（兼容性方法）

        发送实时数据更新消息，主要用于群组消息和数据同步。

        Args:
            message_data (dict): 实时消息数据
            client_id (str, optional): 目标客户端ID，为None时广播

        Message Format:
            {
                "type": "message",
                "data": message_data,
                "timestamp": "2023-01-01T00:00:00"
            }

        Use Cases:
            - 新消息通知
            - 数据更新通知
            - 实时事件推送

        Note:
            - 为了兼容性保留的方法
            - 新代码建议使用send_personal_message或broadcast
        """
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
        """发送Telegram群组状态更新

        推送群组相关的状态变更信息，如连接状态、同步状态等。

        Args:
            group_status_data (dict): 群组状态数据
            client_id (str, optional): 目标客户端ID，为None时广播

        Expected Data Format:
            {
                "group_id": 123,
                "group_name": "Example Group",
                "status": "syncing|idle|error",
                "message_count": 1500,
                "last_sync": "2023-01-01T00:00:00",
                "sync_progress": 75
            }

        Message Format:
            {
                "type": "group_status",
                "data": group_status_data,
                "timestamp": "2023-01-01T00:00:00"
            }

        Use Cases:
            - 群组同步状态更新
            - 群组连接状态变更
            - 群组消息计数更新
            - 群组配置变更

        Note:
            - 主要用于Telegram群组相关状态
            - 客户端可根据状态更新UI显示
        """
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
        """发送消息统计数据更新

        推送消息相关的统计信息，如消息数量、类型分布等。

        Args:
            stats_data (dict): 消息统计数据
            client_id (str, optional): 目标客户端ID，为None时广播

        Expected Data Format:
            {
                "total_messages": 10000,
                "today_messages": 150,
                "media_messages": 3500,
                "text_messages": 6500,
                "message_types": {
                    "photo": 2000,
                    "video": 1000,
                    "document": 500
                },
                "active_groups": 5
            }

        Message Format:
            {
                "type": "message_stats",
                "data": stats_data,
                "timestamp": "2023-01-01T00:00:00"
            }

        Use Cases:
            - 仪表盘数据更新
            - 统计图表刷新
            - 实时数据监控
            - 数据分析显示

        Note:
            - 主要用于数据统计和分析功能
            - 适合实时仪表盘更新
        """
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
"""全局WebSocket管理器实例

单例模式的WebSocket管理器，在整个应用程序中共享使用。

Usage:
    from app.websocket.manager import websocket_manager

    # 建立连接
    await websocket_manager.connect(websocket, client_id)

    # 发送消息
    await websocket_manager.send_notification({
        "title": "任务完成",
        "message": "所有消息已同步完成",
        "type": "success"
    })

    # 断开连接
    websocket_manager.disconnect(client_id)

Note:
    该实例会在应用程序启动时初始化，并在整个生命周期中保持存在。
"""