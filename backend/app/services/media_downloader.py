import os
import logging
from typing import Optional, Dict, Any
from telethon import TelegramClient
from telethon.errors import AuthKeyUnregisteredError, FloodWaitError
from ..config import settings
import asyncio

logger = logging.getLogger(__name__)

class TelegramMediaDownloader:
    """Telegram媒体文件下载器"""
    
    def __init__(self):
        self.client: Optional[TelegramClient] = None
        self._initialized = False
        # 使用与主服务相同的session路径
        self.session_name = os.path.join("./telegram_sessions", "tggod_session")
    
    async def initialize(self):
        """初始化Telegram客户端"""
        if self._initialized and self.client and self.client.is_connected():
            return
        
        try:
            # 强制清除配置缓存，确保获取最新配置
            settings.clear_cache()
            
            # 获取Telegram配置
            api_id = settings.telegram_api_id
            api_hash = settings.telegram_api_hash
            
            logger.info(f"媒体下载器 - API ID: {api_id}, API Hash: {'*' * len(str(api_hash)) if api_hash else 'None'}")
            
            if not api_id or not api_hash:
                raise ValueError(f"Telegram API配置不完整: API ID={api_id}, API Hash={'已设置' if api_hash else '未设置'}")
            
            # 确保session目录存在
            os.makedirs(os.path.dirname(self.session_name), exist_ok=True)
            
            # 创建客户端
            self.client = TelegramClient(
                self.session_name,
                api_id,
                api_hash
            )
            
            # 连接客户端
            await self.client.connect()
            
            # 检查认证状态
            if not await self.client.is_user_authorized():
                logger.error("媒体下载器 - Telegram客户端未授权，请先在主服务中完成认证")
                raise AuthKeyUnregisteredError("Telegram客户端未授权")
            
            self._initialized = True
            logger.info("Telegram媒体下载器初始化成功")
            
        except AuthKeyUnregisteredError as e:
            logger.error(f"媒体下载器认证失败: {str(e)}")
            logger.error("请确保主Telegram服务已完成认证")
            if self.client:
                await self.client.disconnect()
                self.client = None
            raise
        except Exception as e:
            logger.error(f"Telegram媒体下载器初始化失败: {str(e)}")
            if self.client:
                await self.client.disconnect()
                self.client = None
            raise
    
    async def download_file(
        self, 
        file_id: str, 
        file_path: str,
        chat_id: Optional[int] = None,
        message_id: Optional[int] = None
    ) -> bool:
        """
        下载媒体文件
        
        Args:
            file_id: Telegram文件ID
            file_path: 本地保存路径
            chat_id: 聊天ID（可选，用于获取更多文件信息）
            message_id: 消息ID（可选，用于获取更多文件信息）
        
        Returns:
            下载是否成功
        """
        try:
            # 重新初始化确保连接正常
            await self.initialize()
            
            if not self.client or not self.client.is_connected():
                logger.error("Telegram客户端未连接")
                return False
            
            # 确保目标目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            if chat_id and message_id:
                # 通过聊天和消息ID获取文件
                return await self._download_by_message(chat_id, message_id, file_path)
            else:
                logger.warning(f"缺少chat_id或message_id，无法下载文件: {file_id}")
                return False
                
        except Exception as e:
            logger.error(f"下载文件失败 {file_id}: {str(e)}")
            # 清理可能创建的不完整文件
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except:
                    pass
            return False
    
    async def _download_by_message(self, chat_id: int, message_id: int, file_path: str) -> bool:
        """通过消息ID下载文件"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # 获取聊天实体
                chat = await self.client.get_entity(chat_id)
                
                # 获取消息
                messages = await self.client.get_messages(chat, ids=message_id)
                
                # 处理返回的消息，可能是单个消息或消息列表
                if messages:
                    if hasattr(messages, '__iter__') and not isinstance(messages, str):
                        # 是列表类型
                        message = messages[0] if len(messages) > 0 else None
                    else:
                        # 是单个消息对象
                        message = messages
                else:
                    message = None
                
                if not message:
                    logger.warning(f"消息 {message_id} 不存在")
                    return False
                
                if not message.media:
                    logger.warning(f"消息 {message_id} 无媒体内容")
                    return False
                
                # 下载媒体文件
                await self.client.download_media(message.media, file_path)
                logger.info(f"通过消息下载文件成功: {file_path}")
                return True
                
            except FloodWaitError as e:
                if attempt < max_retries - 1:
                    wait_time = min(e.seconds, 300)  # 最多等待5分钟
                    logger.warning(f"媒体下载遇到Flood Wait，等待{wait_time}秒后重试 (尝试 {attempt + 1}/{max_retries})")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"媒体下载达到最大重试次数，Flood Wait错误: {e}")
                    raise
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"下载尝试 {attempt + 1} 失败: {e}, 重试中...")
                    await asyncio.sleep(1)
                else:
                    logger.error(f"通过消息ID下载失败: {e}")
                    raise
        
        return False
    
    async def get_file_info(self, file_id: str) -> Optional[Dict[str, Any]]:
        """
        获取文件信息
        
        Args:
            file_id: Telegram文件ID
        
        Returns:
            文件信息字典或None
        """
        if not self._initialized:
            await self.initialize()
        
        if not self.client:
            return None
        
        try:
            # 这里应该实现获取文件信息的逻辑
            # 由于Telegram API的复杂性，这里返回模拟数据
            return {
                "file_id": file_id,
                "file_size": 1024,  # 默认大小
                "mime_type": "application/octet-stream"
            }
        except Exception as e:
            logger.error(f"获取文件信息失败 {file_id}: {str(e)}")
            return None
    
    async def generate_thumbnail(
        self, 
        media_path: str, 
        thumbnail_path: str,
        media_type: str
    ) -> bool:
        """
        生成媒体文件缩略图
        
        Args:
            media_path: 原媒体文件路径
            thumbnail_path: 缩略图保存路径
            media_type: 媒体类型
        
        Returns:
            生成是否成功
        """
        try:
            if media_type == "photo":
                # 图片缩略图
                from PIL import Image
                
                with Image.open(media_path) as img:
                    # 生成缩略图 (200x200)
                    img.thumbnail((200, 200), Image.Resampling.LANCZOS)
                    
                    # 确保目标目录存在
                    os.makedirs(os.path.dirname(thumbnail_path), exist_ok=True)
                    
                    # 保存缩略图
                    img.save(thumbnail_path, format='JPEG', quality=85)
                    
                logger.info(f"图片缩略图生成成功: {thumbnail_path}")
                return True
                
            elif media_type == "video":
                # 视频缩略图（需要ffmpeg或其他工具）
                # 这里创建一个占位符
                with open(thumbnail_path, 'wb') as f:
                    f.write(b'video thumbnail placeholder')
                
                logger.info(f"视频缩略图占位符创建: {thumbnail_path}")
                return True
            
            else:
                # 其他类型不生成缩略图
                return False
                
        except Exception as e:
            logger.error(f"生成缩略图失败: {str(e)}")
            return False
    
    async def close(self):
        """关闭客户端连接"""
        if self.client and self.client.is_connected():
            await self.client.disconnect()
        self._initialized = False
        logger.info("Telegram媒体下载器已关闭")

# 全局下载器实例
_downloader: Optional[TelegramMediaDownloader] = None

async def get_media_downloader() -> TelegramMediaDownloader:
    """获取媒体下载器实例"""
    global _downloader
    if _downloader is None:
        _downloader = TelegramMediaDownloader()
    
    # 每次都尝试初始化，确保连接正常
    try:
        await _downloader.initialize()
    except Exception as e:
        logger.error(f"媒体下载器初始化失败: {e}")
        # 重置实例
        _downloader = None
        raise
    
    return _downloader