from telethon import TelegramClient, errors
from telethon.errors import FloodWaitError, AuthKeyUnregisteredError
from telethon.tl.types import Channel, Chat, User, Message, MessageMediaPhoto, MessageMediaDocument
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.messages import GetHistoryRequest
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import asyncio
import logging
from datetime import datetime, timezone, timedelta
import os
import aiofiles
from ..config import settings
from ..models.telegram import TelegramGroup, TelegramMessage
from ..database import get_db

logger = logging.getLogger(__name__)

class TelegramService:
    def __init__(self):
        self.client: Optional[TelegramClient] = None
        self.session_name = os.path.join("./telegram_sessions", "tggod_session")
        
    async def initialize(self):
        """初始化Telegram客户端"""
        if self.client is None:
            # 强制清除配置缓存，确保获取最新配置
            settings.clear_cache()
            
            # 确保API配置不为空
            api_id = settings.telegram_api_id
            api_hash = settings.telegram_api_hash
            
            logger.info(f"API ID: {api_id}, API Hash: {'*' * len(str(api_hash)) if api_hash else 'None'}")
            
            if not api_id or not api_hash:
                raise ValueError(f"API配置不完整: API ID={api_id}, API Hash={'已设置' if api_hash else '未设置'}")
            
            self.client = TelegramClient(
                self.session_name,
                api_id,
                api_hash
            )
            # 使用非交互式连接，避免在服务器环境中要求用户输入
            await self.client.connect()
            logger.info("Telegram客户端初始化成功")
        
    async def disconnect(self):
        """断开Telegram客户端"""
        if self.client:
            await self.client.disconnect()
            self.client = None
            logger.info("Telegram客户端已断开")
    
    async def _handle_flood_wait(self, func, *args, **kwargs):
        """处理Flood Wait错误的重试机制"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                return await func(*args, **kwargs)
            except FloodWaitError as e:
                if attempt < max_retries - 1:
                    wait_time = min(e.seconds, 300)  # 最多等待5分钟
                    logger.warning(f"遇到Flood Wait，等待{wait_time}秒后重试 (尝试 {attempt + 1}/{max_retries})")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"达到最大重试次数，Flood Wait错误: {e}")
                    raise
            except Exception as e:
                logger.error(f"执行函数时出错: {e}")
                raise
    
    async def get_group_info(self, group_identifier) -> Optional[Dict[str, Any]]:
        """获取群组信息 - 支持用户名、ID或实体对象"""
        try:
            await self.initialize()
            
            # 如果传入的已经是实体对象，直接使用
            if hasattr(group_identifier, 'id'):
                entity = group_identifier
            else:
                # 尝试获取群组实体
                try:
                    entity = await self.client.get_entity(group_identifier)
                except Exception as e:
                    logger.warning(f"无法通过标识符 {group_identifier} 获取实体: {e}")
                    return None
            
            if isinstance(entity, (Channel, Chat)):
                # 获取完整信息，加入错误处理
                member_count = 0
                description = None
                
                try:
                    if isinstance(entity, Channel):
                        # 对于频道，尝试获取完整信息
                        try:
                            full_info = await self._handle_flood_wait(
                                self.client, GetFullChannelRequest(entity)
                            )
                            member_count = full_info.full_chat.participants_count or 0
                            description = full_info.full_chat.about
                        except Exception as e:
                            logger.warning(f"无法获取频道 {entity.title} 的完整信息: {e}")
                            member_count = getattr(entity, 'participants_count', 0)
                    else:
                        # 对于普通群组
                        member_count = getattr(entity, 'participants_count', 0)
                        
                except Exception as e:
                    logger.warning(f"获取群组 {entity.title} 详细信息时出错: {e}")
                
                return {
                    "telegram_id": entity.id,
                    "title": entity.title or "未知群组",
                    "username": getattr(entity, 'username', None),
                    "description": description,
                    "member_count": member_count,
                    "is_active": True
                }
            else:
                logger.warning(f"实体 {group_identifier} 不是群组或频道，类型: {type(entity)}")
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
    
    async def get_messages(self, group_identifier, limit: int = 100, offset_id: int = 0) -> List[Dict[str, Any]]:
        """获取群组消息 - 支持用户名、ID或实体对象"""
        try:
            await self.initialize()
            
            # 验证输入参数
            if not group_identifier:
                logger.error("群组标识符不能为空")
                return []
            
            # 获取群组实体
            try:
                if hasattr(group_identifier, 'id'):
                    # 如果传入的已经是实体对象，直接使用
                    entity = group_identifier
                    logger.info(f"使用实体对象: {getattr(entity, 'title', 'Unknown')}")
                else:
                    # 尝试通过用户名或ID获取实体
                    logger.info(f"尝试获取实体: {group_identifier}")
                    entity = await self.client.get_entity(group_identifier)
                    logger.info(f"成功获取实体: {getattr(entity, 'title', 'Unknown')}")
                    
            except Exception as e:
                logger.error(f"无法获取群组实体 {group_identifier}: {e}")
                return []
            
            messages = []
            message_count = 0
            
            try:
                async for message in self.client.iter_messages(entity, limit=limit, offset_id=offset_id):
                    message_data = await self._process_message(message)
                    if message_data:
                        messages.append(message_data)
                        message_count += 1
                
                logger.info(f"成功获取 {message_count} 条消息")
                
            except Exception as e:
                logger.error(f"获取消息时出错: {e}")
            
            return messages
            
        except Exception as e:
            logger.error(f"获取消息失败: {e}")
            return []
    
    async def _process_message(self, message: Message) -> Optional[Dict[str, Any]]:
        """处理单条消息"""
        try:
            # 获取当前用户信息
            current_user = await self.client.get_me()
            
            # 基本信息
            message_data = {
                "message_id": message.id,
                "text": message.text,
                "date": message.date,
                "view_count": message.views or 0,
                "is_forwarded": message.forward is not None,
                "forwarded_from": None,
                "forwarded_from_id": None,
                "forwarded_from_type": None,
                "forwarded_date": None,
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
                    # 检查是否是当前用户发送的消息
                    is_current_user = message.sender.id == current_user.id
                    
                    message_data.update({
                        "sender_id": message.sender.id,
                        "sender_username": message.sender.username,
                        "sender_name": f"{message.sender.first_name or ''} {message.sender.last_name or ''}".strip(),
                        "is_own_message": is_current_user  # 直接标记是否为当前用户发送
                    })
                elif isinstance(message.sender, Channel):
                    message_data.update({
                        "sender_id": message.sender.id,
                        "sender_username": message.sender.username,
                        "sender_name": message.sender.title,
                        "is_own_message": False  # 频道消息不是个人发送的
                    })
            
            # 转发信息
            if message.forward:
                # 设置转发日期
                message_data["forwarded_date"] = message.forward.date
                
                # 处理转发来源 - 简化逻辑，避免过度查询导致权限错误
                if message.forward.from_name:
                    # 从用户名转发（隐私设置导致无法获取用户对象）
                    message_data["forwarded_from"] = message.forward.from_name
                    message_data["forwarded_from_type"] = "user"
                elif message.forward.from_id:
                    # 从用户ID转发 - 简化处理，避免权限问题
                    message_data["forwarded_from_id"] = message.forward.from_id
                    message_data["forwarded_from_type"] = "user"
                    
                    # 尝试获取用户信息，但不强制要求成功
                    try:
                        user = await self.client.get_entity(message.forward.from_id)
                        if isinstance(user, User):
                            full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
                            message_data["forwarded_from"] = full_name or user.username or f"用户{user.id}"
                    except Exception as e:
                        logger.debug(f"无法获取转发用户详细信息，使用ID: {e}")
                        message_data["forwarded_from"] = f"用户{message.forward.from_id}"
                        
                elif message.forward.chat:
                    # 从群组/频道转发
                    chat = message.forward.chat
                    message_data["forwarded_from"] = chat.title
                    message_data["forwarded_from_id"] = chat.id
                    
                    if isinstance(chat, Channel):
                        if chat.broadcast:
                            message_data["forwarded_from_type"] = "channel"
                        else:
                            message_data["forwarded_from_type"] = "group"
                    elif isinstance(chat, Chat):
                        message_data["forwarded_from_type"] = "group"
            
            # 处理消息文本中的特殊元素
            if message.text:
                message_data["mentions"] = self._extract_mentions(message.text)
                message_data["hashtags"] = self._extract_hashtags(message.text)
                message_data["urls"] = self._extract_urls(message.text)
            
            # 处理消息反应
            if hasattr(message, 'reactions') and message.reactions:
                message_data["reactions"] = self._process_reactions(message.reactions)
            
            # 媒体信息 - 默认不下载，只收集元数据
            if message.media:
                media_info = await self._process_media(message, download=False)
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
    
    async def _process_media(self, message: Message, download: bool = True) -> Dict[str, Any]:
        """处理媒体文件
        
        Args:
            message: Telegram消息对象
            download: 是否下载媒体文件（转发消息设为False）
        """
        media_info = {
            "media_type": None,
            "media_path": None,
            "media_size": None,
            "media_filename": None,
            "media_file_id": None,
            "media_file_unique_id": None,
            "media_downloaded": False
        }
        
        try:
            if isinstance(message.media, MessageMediaPhoto):
                media_info["media_type"] = "photo"
                media_info["media_size"] = getattr(message.media.photo, 'size', 0)
                media_info["media_filename"] = f"photo_{message.id}.jpg"
                
                # 设置文件ID信息（用于后续下载）
                if hasattr(message.media.photo, 'id'):
                    media_info["media_file_id"] = str(message.media.photo.id)
                if hasattr(message.media.photo, 'file_reference'):
                    media_info["media_file_unique_id"] = str(message.media.photo.file_reference)
                
                # 只有在download=True时才下载文件
                if download:
                    try:
                        from ..config import settings
                        media_dir = os.path.join(settings.media_root, "photos")
                        os.makedirs(media_dir, exist_ok=True)
                        
                        file_path = os.path.join(media_dir, media_info["media_filename"])
                        await self.client.download_media(message.media, file_path)
                        
                        # 保存相对路径
                        media_info["media_path"] = f"media/photos/{media_info['media_filename']}"
                        media_info["media_downloaded"] = True
                        logger.info(f"图片下载成功: {file_path}")
                        
                    except Exception as e:
                        logger.error(f"图片下载失败: {e}")
                        # 即使下载失败，也保留媒体信息
                else:
                    logger.debug(f"跳过转发图片下载: {media_info['media_filename']}")
                
            elif isinstance(message.media, MessageMediaDocument):
                doc = message.media.document
                media_info["media_size"] = doc.size
                
                # 设置文件ID信息
                if hasattr(doc, 'id'):
                    media_info["media_file_id"] = str(doc.id)
                if hasattr(doc, 'file_reference'):
                    media_info["media_file_unique_id"] = str(doc.file_reference)
                
                # 判断媒体类型
                if doc.mime_type:
                    if doc.mime_type.startswith('image/'):
                        media_info["media_type"] = "photo"
                    elif doc.mime_type.startswith('video/'):
                        media_info["media_type"] = "video"
                    elif doc.mime_type.startswith('audio/'):
                        # 检查是否是语音消息
                        is_voice = False
                        for attribute in doc.attributes:
                            if hasattr(attribute, 'voice') and attribute.voice:
                                is_voice = True
                                break
                        media_info["media_type"] = "voice" if is_voice else "audio"
                    else:
                        media_info["media_type"] = "document"
                else:
                    media_info["media_type"] = "document"
                
                # 获取文件名
                original_filename = None
                for attribute in doc.attributes:
                    if hasattr(attribute, 'file_name'):
                        original_filename = attribute.file_name
                        break
                
                if not original_filename:
                    # 根据mime_type生成文件名
                    if doc.mime_type:
                        ext = doc.mime_type.split('/')[-1]
                        if ext in ['jpeg', 'jpg', 'png', 'gif', 'webp']:
                            original_filename = f"image_{message.id}.{ext}"
                        elif ext in ['mp4', 'avi', 'mov', 'webm']:
                            original_filename = f"video_{message.id}.{ext}"
                        elif ext in ['mp3', 'wav', 'ogg', 'aac']:
                            original_filename = f"audio_{message.id}.{ext}"
                        else:
                            original_filename = f"document_{message.id}.{ext}"
                    else:
                        original_filename = f"document_{message.id}"
                
                media_info["media_filename"] = original_filename
                
                # 只有在download=True时才下载文件
                if download:
                    try:
                        from ..config import settings
                        media_type = media_info["media_type"]
                        media_dir = os.path.join(settings.media_root, f"{media_type}s")
                        os.makedirs(media_dir, exist_ok=True)
                        
                        file_path = os.path.join(media_dir, original_filename)
                        await self.client.download_media(message.media, file_path)
                        
                        # 保存相对路径
                        media_info["media_path"] = f"media/{media_type}s/{original_filename}"
                        media_info["media_downloaded"] = True
                        logger.info(f"{media_type}文件下载成功: {file_path}")
                        
                    except Exception as e:
                        logger.error(f"文件下载失败: {e}")
                        # 即使下载失败，也保留媒体信息
                else:
                    logger.debug(f"跳过转发{media_info['media_type']}文件下载: {original_filename}")
                
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
    
    async def save_messages_to_db(self, group_id: int, messages: List[Dict[str, Any]], db: Session) -> int:
        """保存消息到数据库，返回保存的消息数量"""
        try:
            saved_count = 0
            
            for message_data in messages:
                # 检查消息是否已存在
                existing_message = db.query(TelegramMessage).filter(
                    TelegramMessage.group_id == group_id,
                    TelegramMessage.message_id == message_data["message_id"]
                ).first()
                
                if existing_message:
                    continue
                
                # 清理数据，确保没有 Telethon 对象
                cleaned_data = self._clean_message_data(message_data)
                
                # 创建消息记录
                message = TelegramMessage(
                    group_id=group_id,
                    **cleaned_data
                )
                db.add(message)
                saved_count += 1
            
            db.commit()
            logger.info(f"成功保存 {saved_count} 条消息到数据库")
            return saved_count
            
        except Exception as e:
            logger.error(f"保存消息到数据库失败: {e}")
            db.rollback()
            return 0
    
    def _clean_message_data(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """清理消息数据，移除或转换不兼容的对象"""
        cleaned_data = {}
        
        # 定义允许的字段和其类型转换规则
        allowed_fields = {
            'message_id', 'sender_id', 'sender_username', 'sender_name', 'text',
            'media_type', 'media_path', 'media_size', 'media_filename', 
            'media_file_id', 'media_file_unique_id', 'media_downloaded',
            'media_download_url', 'media_download_error', 'media_thumbnail_path',
            'view_count', 'is_forwarded', 'forwarded_from', 'forwarded_from_id',
            'forwarded_from_type', 'forwarded_date', 'is_own_message',
            'reply_to_message_id', 'edit_date', 'is_pinned', 'reactions',
            'mentions', 'hashtags', 'urls', 'date'
        }
        
        for key, value in message_data.items():
            if key not in allowed_fields:
                logger.warning(f"跳过未知字段: {key}")
                continue
                
            # 跳过 None 值
            if value is None:
                cleaned_data[key] = None
                continue
                
            # 检查并跳过 Telethon 对象
            if hasattr(value, '__class__'):
                type_str = str(type(value))
                if 'telethon' in type_str.lower() or 'peer' in type_str.lower():
                    logger.warning(f"跳过 Telethon 对象字段 {key}: {type(value)}")
                    continue
            
            # 转换特殊类型
            if key in ['reactions', 'mentions', 'hashtags', 'urls']:
                if isinstance(value, (list, dict)):
                    import json
                    try:
                        cleaned_data[key] = json.dumps(value, ensure_ascii=False)
                    except (TypeError, ValueError) as e:
                        logger.warning(f"JSON序列化失败 {key}: {e}")
                        cleaned_data[key] = str(value)
                else:
                    cleaned_data[key] = str(value) if value is not None else None
            elif key in ['forwarded_date', 'edit_date', 'date']:
                # 确保日期字段是正确的格式
                if hasattr(value, 'isoformat'):
                    cleaned_data[key] = value
                elif isinstance(value, str):
                    cleaned_data[key] = value
                else:
                    logger.warning(f"日期字段 {key} 格式异常: {type(value)}")
                    cleaned_data[key] = None
            else:
                # 其他字段直接赋值，但确保不是对象
                if isinstance(value, (str, int, float, bool)) or value is None:
                    cleaned_data[key] = value
                else:
                    logger.warning(f"字段 {key} 类型异常: {type(value)}, 转换为字符串")
                    cleaned_data[key] = str(value)
        
        return cleaned_data
    
    async def sync_messages_by_month(self, group_identifier, months: List[Dict[str, Any]]) -> Dict[str, Any]:
        """按月同步群组消息
        
        Args:
            group_identifier: 群组标识符（用户名、ID或实体对象）
            months: 月份列表，每个月份包含 year 和 month 字段
            
        Returns:
            同步结果统计
        """
        try:
            await self.initialize()
            
            # 验证输入参数
            if not group_identifier:
                logger.error("群组标识符不能为空")
                return {"success": False, "error": "群组标识符不能为空"}
            
            if not months:
                logger.error("月份列表不能为空")
                return {"success": False, "error": "月份列表不能为空"}
            
            # 获取群组实体
            try:
                if hasattr(group_identifier, 'id'):
                    entity = group_identifier
                    logger.info(f"使用实体对象: {getattr(entity, 'title', 'Unknown')}")
                else:
                    logger.info(f"尝试获取实体: {group_identifier}")
                    entity = await self.client.get_entity(group_identifier)
            except Exception as e:
                logger.error(f"获取群组实体失败: {e}")
                return {"success": False, "error": f"获取群组实体失败: {e}"}
            
            # 同步结果统计
            sync_result = {
                "success": True,
                "total_messages": 0,
                "months_synced": 0,
                "failed_months": [],
                "monthly_stats": []
            }
            
            # 按月同步消息
            for month_info in months:
                try:
                    year = month_info.get("year")
                    month = month_info.get("month")
                    
                    if not year or not month:
                        logger.error(f"月份信息不完整: {month_info}")
                        sync_result["failed_months"].append({
                            "month": month_info,
                            "error": "月份信息不完整"
                        })
                        continue
                    
                    logger.info(f"开始同步 {year}-{month:02d} 的消息...")
                    
                    # 计算时间范围
                    start_date = datetime(year, month, 1, tzinfo=timezone.utc)
                    if month == 12:
                        end_date = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
                    else:
                        end_date = datetime(year, month + 1, 1, tzinfo=timezone.utc)
                    
                    # 获取该月的消息
                    month_messages = await self._get_messages_by_time_range(
                        entity, start_date, end_date
                    )
                    
                    # 保存消息到数据库
                    from ..database import SessionLocal
                    db = SessionLocal()
                    try:
                        # 获取群组ID
                        group_record = db.query(TelegramGroup).filter_by(
                            telegram_id=entity.id
                        ).first()
                        
                        if not group_record:
                            logger.error(f"未找到群组记录: {entity.id}")
                            sync_result["failed_months"].append({
                                "month": month_info,
                                "error": "未找到群组记录"
                            })
                            continue
                        
                        saved_count = await self.save_messages_to_db(
                            group_record.id, month_messages, db
                        )
                        
                        # 统计结果
                        month_stat = {
                            "year": year,
                            "month": month,
                            "total_messages": len(month_messages),
                            "saved_messages": saved_count,
                            "start_date": start_date.isoformat(),
                            "end_date": end_date.isoformat()
                        }
                        
                        sync_result["monthly_stats"].append(month_stat)
                        sync_result["total_messages"] += saved_count
                        sync_result["months_synced"] += 1
                        
                        logger.info(f"✓ {year}-{month:02d} 同步完成: {saved_count}/{len(month_messages)} 条消息")
                        
                    finally:
                        db.close()
                        
                except Exception as e:
                    logger.error(f"同步 {year}-{month:02d} 失败: {e}")
                    sync_result["failed_months"].append({
                        "month": month_info,
                        "error": str(e)
                    })
                    
                # 添加延迟以避免API限制
                await asyncio.sleep(2)
            
            logger.info(f"按月同步完成: 总计 {sync_result['total_messages']} 条消息")
            return sync_result
            
        except Exception as e:
            logger.error(f"按月同步失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def _get_messages_by_time_range(self, entity, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """根据时间范围获取消息"""
        try:
            messages = []
            offset_id = 0
            batch_size = 100
            max_messages = 10000  # 单月最大消息数限制
            
            while len(messages) < max_messages:
                try:
                    # 获取消息历史
                    history = await self.client(GetHistoryRequest(
                        peer=entity,
                        limit=batch_size,
                        offset_id=offset_id,
                        offset_date=None,
                        add_offset=0,
                        max_id=0,
                        min_id=0,
                        hash=0
                    ))
                    
                    if not history.messages:
                        break
                    
                    batch_messages = []
                    for msg in history.messages:
                        # 检查消息时间是否在范围内
                        if msg.date < start_date:
                            # 已经超出时间范围，停止获取
                            return messages
                        
                        if msg.date >= end_date:
                            # 还没到时间范围，继续获取
                            offset_id = msg.id
                            continue
                        
                        # 在时间范围内，处理消息
                        message_data = await self._process_message(msg)
                        if message_data:
                            batch_messages.append(message_data)
                    
                    messages.extend(batch_messages)
                    
                    # 如果这批消息少于请求的数量，说明已经到达历史消息的末尾
                    if len(history.messages) < batch_size:
                        break
                    
                    # 更新offset_id为最后一条消息的ID
                    offset_id = history.messages[-1].id
                    
                    # 添加短暂延迟以避免API限制
                    await asyncio.sleep(0.5)
                    
                except FloodWaitError as e:
                    logger.warning(f"遇到频率限制，等待 {e.seconds} 秒...")
                    await asyncio.sleep(e.seconds)
                except Exception as e:
                    logger.error(f"获取消息批次失败: {e}")
                    break
            
            logger.info(f"获取到 {len(messages)} 条消息 ({start_date.strftime('%Y-%m')})")
            return messages
            
        except Exception as e:
            logger.error(f"根据时间范围获取消息失败: {e}")
            return []
    
    async def get_default_sync_months(self, count: int = 3) -> List[Dict[str, Any]]:
        """获取默认的同步月份（最近N个月）"""
        try:
            months = []
            current_date = datetime.now()
            
            for i in range(count):
                # 计算目标月份
                target_date = current_date - timedelta(days=30 * i)
                months.append({
                    "year": target_date.year,
                    "month": target_date.month
                })
            
            return months
            
        except Exception as e:
            logger.error(f"获取默认同步月份失败: {e}")
            return []
    
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