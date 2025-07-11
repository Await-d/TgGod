import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Set
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import TelegramGroup, TelegramMessage
from ..services.telegram_service import telegram_service
from ..websocket.manager import websocket_manager

logger = logging.getLogger(__name__)

class MessageSyncTask:
    def __init__(self):
        self.active_groups: Set[int] = set()
        self.sync_intervals: Dict[int, int] = {}  # group_id -> interval in seconds
        self.is_running = False
        self.sync_task = None

    def add_group(self, group_id: int, interval: int = 30):
        """添加需要同步的群组"""
        self.active_groups.add(group_id)
        self.sync_intervals[group_id] = interval
        logger.info(f"Added group {group_id} for sync with interval {interval}s")

    def remove_group(self, group_id: int):
        """移除群组同步"""
        self.active_groups.discard(group_id)
        if group_id in self.sync_intervals:
            del self.sync_intervals[group_id]
        logger.info(f"Removed group {group_id} from sync")

    async def sync_group_messages(self, group_id: int, db: Session):
        """同步单个群组的消息"""
        try:
            # 获取群组信息
            group = db.query(TelegramGroup).filter(TelegramGroup.id == group_id).first()
            if not group or not group.is_active:
                logger.warning(f"Group {group_id} not found or inactive")
                return 0

            # 确定群组标识符
            group_identifier = group.username or group.telegram_id
            if not group_identifier:
                logger.error(f"Group {group_id} has no identifier")
                return 0

            # 获取最新消息
            messages = await telegram_service.get_messages(group_identifier, limit=50)
            
            # 保存到数据库
            saved_count = await telegram_service.save_messages_to_db(group_id, messages, db)
            
            # 如果有新消息，通过WebSocket推送
            if saved_count > 0:
                try:
                    # 推送新消息通知
                    for message_data in messages[-saved_count:]:  # 只推送新消息
                        await websocket_manager.send_message({
                            "chat_id": group_id,
                            "message_id": message_data.get("message_id"),
                            "text": message_data.get("text"),
                            "sender_name": message_data.get("sender_name"),
                            "sender_username": message_data.get("sender_username"),
                            "date": message_data.get("date"),
                            "is_own_message": message_data.get("is_own_message", False),
                            "media_type": message_data.get("media_type"),
                            "reply_to_message_id": message_data.get("reply_to_message_id")
                        })
                    
                    # 推送统计更新
                    await websocket_manager.send_message_stats({
                        "group_id": group_id,
                        "new_messages": saved_count,
                        "sync_time": datetime.now().isoformat(),
                        "auto_sync": True
                    })
                    
                except Exception as ws_error:
                    logger.error(f"WebSocket推送失败: {ws_error}")
            
            if saved_count > 0:
                logger.info(f"Synced {saved_count} new messages for group {group_id}")
            
            return saved_count
            
        except Exception as e:
            logger.error(f"Error syncing group {group_id}: {e}")
            return 0

    async def run_sync_cycle(self):
        """运行同步循环"""
        while self.is_running:
            if not self.active_groups:
                await asyncio.sleep(10)  # 如果没有活跃群组，等待10秒
                continue

            # 获取数据库会话
            db = next(get_db())
            try:
                # 同步所有活跃群组
                sync_tasks = []
                for group_id in self.active_groups.copy():  # 使用copy避免并发修改
                    task = self.sync_group_messages(group_id, db)
                    sync_tasks.append(task)
                
                # 并发执行同步任务
                if sync_tasks:
                    results = await asyncio.gather(*sync_tasks, return_exceptions=True)
                    total_synced = sum(r for r in results if isinstance(r, int))
                    
                    if total_synced > 0:
                        logger.info(f"Sync cycle completed: {total_synced} messages synced across {len(sync_tasks)} groups")
                
            except Exception as e:
                logger.error(f"Error in sync cycle: {e}")
            finally:
                db.close()

            # 等待30秒后进行下一轮同步
            await asyncio.sleep(30)

    def start(self):
        """启动同步任务"""
        if not self.is_running:
            self.is_running = True
            self.sync_task = asyncio.create_task(self.run_sync_cycle())
            logger.info("Message sync task started")

    def stop(self):
        """停止同步任务"""
        self.is_running = False
        if self.sync_task:
            self.sync_task.cancel()
            self.sync_task = None
        logger.info("Message sync task stopped")

    def get_active_groups(self) -> Set[int]:
        """获取活跃群组列表"""
        return self.active_groups.copy()

    def get_sync_status(self) -> Dict:
        """获取同步状态"""
        return {
            "is_running": self.is_running,
            "active_groups": list(self.active_groups),
            "total_groups": len(self.active_groups)
        }

# 创建全局同步任务实例
message_sync_task = MessageSyncTask()