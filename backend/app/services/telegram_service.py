from telethon import TelegramClient, errors
from telethon.tl.types import Channel, Chat, User, Message, MessageMediaPhoto, MessageMediaDocument
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.messages import GetHistoryRequest
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import asyncio
import logging
from datetime import datetime, timezone
import os
import aiofiles
from ..config import settings
from ..models.telegram import TelegramGroup, TelegramMessage
from ..database import get_db

logger = logging.getLogger(__name__)

class TelegramService:
    def __init__(self):
        self.client: Optional[TelegramClient] = None
        self.session_name = "tggod_session"
        
    async def initialize(self):
        """初始化Telegram客户端"""
        if self.client is None:
            self.client = TelegramClient(
                self.session_name,
                settings.telegram_api_id,
                settings.telegram_api_hash
            )
            await self.client.start()
            logger.info("Telegram客户端初始化成功")
        
    async def disconnect(self):
        """断开Telegram客户端"""
        if self.client:
            await self.client.disconnect()
            self.client = None
            logger.info("Telegram客户端已断开")
    
    async def get_group_info(self, group_username: str) -> Optional[Dict[str, Any]]:
        """获取群组信息"""
        try:
            await self.initialize()
            
            # 获取群组实体
            entity = await self.client.get_entity(group_username)
            
            if isinstance(entity, (Channel, Chat)):
                # 获取完整信息
                if isinstance(entity, Channel):
                    full_info = await self.client(GetFullChannelRequest(entity))
                    member_count = full_info.full_chat.participants_count
                    description = full_info.full_chat.about
                else:
                    member_count = entity.participants_count if hasattr(entity, 'participants_count') else 0
                    description = None
                
                return {
                    "telegram_id": entity.id,
                    "title": entity.title,
                    "username": entity.username,
                    "description": description,
                    "member_count": member_count,
                    "is_active": True
                }
            else:
                logger.error(f"实体 {group_username} 不是群组或频道")
                return None
                
        except Exception as e:
            logger.error(f"获取群组信息失败: {e}")
            return None
    
    async def add_group_to_db(self, group_username: str, db: Session) -> Optional[TelegramGroup]:
        """添加群组到数据库"""
        try:
            # 检查群组是否已存在
            existing_group = db.query(TelegramGroup).filter(
                TelegramGroup.username == group_username
            ).first()
            
            if existing_group:
                logger.info(f"群组 {group_username} 已存在")
                return existing_group
            
            # 获取群组信息
            group_info = await self.get_group_info(group_username)
            if not group_info:
                return None
            
            # 创建群组记录
            group = TelegramGroup(**group_info)
            db.add(group)
            db.commit()
            db.refresh(group)
            
            logger.info(f"群组 {group_username} 添加成功")
            return group
            
        except Exception as e:
            logger.error(f"添加群组到数据库失败: {e}")
            db.rollback()
            return None
    
    async def get_messages(self, group_username: str, limit: int = 100, offset_id: int = 0) -> List[Dict[str, Any]]:
        """获取群组消息"""
        try:
            await self.initialize()
            
            entity = await self.client.get_entity(group_username)
            messages = []
            
            async for message in self.client.iter_messages(entity, limit=limit, offset_id=offset_id):
                message_data = await self._process_message(message)
                if message_data:
                    messages.append(message_data)
            
            return messages
            
        except Exception as e:
            logger.error(f"获取消息失败: {e}")
            return []
    
    async def _process_message(self, message: Message) -> Optional[Dict[str, Any]]:
        """处理单条消息"""
        try:
            # 基本信息
            message_data = {
                "message_id": message.id,
                "text": message.text,
                "date": message.date,
                "view_count": message.views or 0,
                "is_forwarded": message.forward is not None,
                "forwarded_from": None,
                "reply_to_message_id": message.reply_to_msg_id,
                "edit_date": message.edit_date,
                "is_pinned": message.pinned or False,
                "reactions": None,
                "mentions": [],
                "hashtags": [],
                "urls": []
            }
            
            # 发送者信息
            if message.sender:
                if isinstance(message.sender, User):
                    message_data.update({
                        "sender_id": message.sender.id,
                        "sender_username": message.sender.username,
                        "sender_name": f"{message.sender.first_name or ''} {message.sender.last_name or ''}".strip()
                    })
                elif isinstance(message.sender, Channel):
                    message_data.update({
                        "sender_id": message.sender.id,
                        "sender_username": message.sender.username,
                        "sender_name": message.sender.title
                    })
            
            # 转发信息
            if message.forward:
                if message.forward.from_name:
                    message_data["forwarded_from"] = message.forward.from_name
                elif message.forward.chat:
                    message_data["forwarded_from"] = message.forward.chat.title
            
            # 处理消息文本中的特殊元素
            if message.text:
                message_data["mentions"] = self._extract_mentions(message.text)
                message_data["hashtags"] = self._extract_hashtags(message.text)
                message_data["urls"] = self._extract_urls(message.text)
            
            # 处理消息反应
            if hasattr(message, 'reactions') and message.reactions:
                message_data["reactions"] = self._process_reactions(message.reactions)
            
            # 媒体信息
            if message.media:
                media_info = await self._process_media(message)
                message_data.update(media_info)
            
            return message_data
            
        except Exception as e:
            logger.error(f"处理消息失败: {e}")
            return None
    
    def _extract_mentions(self, text: str) -> List[str]:
        """提取消息中的@mentions"""
        import re
        mentions = re.findall(r'@(\w+)', text)
        return mentions
    
    def _extract_hashtags(self, text: str) -> List[str]:
        """提取消息中的#hashtags"""
        import re
        hashtags = re.findall(r'#(\w+)', text)
        return hashtags
    
    def _extract_urls(self, text: str) -> List[str]:
        """提取消息中的URLs"""
        import re
        urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', text)
        return urls
    
    def _process_reactions(self, reactions) -> Dict[str, Any]:
        """处理消息反应"""
        try:
            reaction_data = {}
            if hasattr(reactions, 'results'):
                for reaction in reactions.results:
                    if hasattr(reaction, 'reaction') and hasattr(reaction, 'count'):
                        reaction_data[str(reaction.reaction)] = reaction.count
            return reaction_data
        except Exception as e:
            logger.error(f"处理消息反应失败: {e}")
            return {}
    
    async def _process_media(self, message: Message) -> Dict[str, Any]:
        """处理媒体文件"""
        media_info = {
            "media_type": None,
            "media_path": None,
            "media_size": None,
            "media_filename": None
        }
        
        try:
            if isinstance(message.media, MessageMediaPhoto):
                media_info["media_type"] = "photo"
                media_info["media_size"] = getattr(message.media.photo, 'size', 0)
                
            elif isinstance(message.media, MessageMediaDocument):
                doc = message.media.document
                media_info["media_size"] = doc.size
                
                # 判断媒体类型
                if doc.mime_type:
                    if doc.mime_type.startswith('image/'):
                        media_info["media_type"] = "photo"
                    elif doc.mime_type.startswith('video/'):
                        media_info["media_type"] = "video"
                    elif doc.mime_type.startswith('audio/'):
                        media_info["media_type"] = "audio"
                    else:
                        media_info["media_type"] = "document"
                
                # 获取文件名
                for attribute in doc.attributes:
                    if hasattr(attribute, 'file_name'):
                        media_info["media_filename"] = attribute.file_name
                        break
                
            return media_info
            
        except Exception as e:
            logger.error(f"处理媒体失败: {e}")
            return media_info
    
    async def download_media(self, message: Message, download_path: str) -> Optional[str]:
        """下载媒体文件"""
        try:
            await self.initialize()
            
            if not message.media:
                return None
            
            # 确保下载目录存在
            os.makedirs(download_path, exist_ok=True)
            
            # 生成文件名
            filename = f"media_{message.id}"
            if isinstance(message.media, MessageMediaDocument):
                doc = message.media.document
                for attribute in doc.attributes:
                    if hasattr(attribute, 'file_name'):
                        filename = attribute.file_name
                        break
                else:
                    # 根据mime_type添加扩展名
                    if doc.mime_type:
                        ext = doc.mime_type.split('/')[-1]
                        filename = f"{filename}.{ext}"
            
            file_path = os.path.join(download_path, filename)
            
            # 下载文件
            await self.client.download_media(message.media, file_path)
            
            logger.info(f"媒体文件下载成功: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"下载媒体文件失败: {e}")
            return None
    
    async def save_messages_to_db(self, group_id: int, messages: List[Dict[str, Any]], db: Session):
        """保存消息到数据库"""
        try:
            for message_data in messages:
                # 检查消息是否已存在
                existing_message = db.query(TelegramMessage).filter(
                    TelegramMessage.group_id == group_id,
                    TelegramMessage.message_id == message_data["message_id"]
                ).first()
                
                if existing_message:
                    continue
                
                # 创建消息记录
                message = TelegramMessage(
                    group_id=group_id,
                    **message_data
                )
                db.add(message)
            
            db.commit()
            logger.info(f"成功保存 {len(messages)} 条消息到数据库")
            
        except Exception as e:
            logger.error(f"保存消息到数据库失败: {e}")
            db.rollback()
    
    async def send_message(self, group_username: str, text: str, reply_to_message_id: Optional[int] = None) -> Optional[int]:
        """发送消息到群组"""
        try:
            await self.initialize()
            
            # 获取群组实体
            entity = await self.client.get_entity(group_username)
            
            # 发送消息
            message = await self.client.send_message(
                entity,
                text,
                reply_to=reply_to_message_id
            )
            
            logger.info(f"消息发送成功，消息ID: {message.id}")
            return message.id
            
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            return None
    
    async def delete_message(self, group_username: str, message_id: int) -> bool:
        """删除群组消息"""
        try:
            await self.initialize()
            
            # 获取群组实体
            entity = await self.client.get_entity(group_username)
            
            # 删除消息
            await self.client.delete_messages(entity, message_id)
            
            logger.info(f"消息删除成功，消息ID: {message_id}")
            return True
            
        except Exception as e:
            logger.error(f"删除消息失败: {e}")
            return False
    
    async def edit_message(self, group_username: str, message_id: int, new_text: str) -> bool:
        """编辑群组消息"""
        try:
            await self.initialize()
            
            # 获取群组实体
            entity = await self.client.get_entity(group_username)
            
            # 编辑消息
            await self.client.edit_message(entity, message_id, new_text)
            
            logger.info(f"消息编辑成功，消息ID: {message_id}")
            return True
            
        except Exception as e:
            logger.error(f"编辑消息失败: {e}")
            return False
    
    async def pin_message(self, group_username: str, message_id: int) -> bool:
        """置顶消息"""
        try:
            await self.initialize()
            
            # 获取群组实体
            entity = await self.client.get_entity(group_username)
            
            # 置顶消息
            await self.client.pin_message(entity, message_id)
            
            logger.info(f"消息置顶成功，消息ID: {message_id}")
            return True
            
        except Exception as e:
            logger.error(f"置顶消息失败: {e}")
            return False
    
    async def unpin_message(self, group_username: str, message_id: int) -> bool:
        """取消置顶消息"""
        try:
            await self.initialize()
            
            # 获取群组实体
            entity = await self.client.get_entity(group_username)
            
            # 取消置顶消息
            await self.client.unpin_message(entity, message_id)
            
            logger.info(f"消息取消置顶成功，消息ID: {message_id}")
            return True
            
        except Exception as e:
            logger.error(f"取消置顶消息失败: {e}")
            return False

# 创建全局服务实例
telegram_service = TelegramService()