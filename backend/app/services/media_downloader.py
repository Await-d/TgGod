import os
import logging
from typing import Optional, Dict, Any
from telethon import TelegramClient
from ..config import settings

logger = logging.getLogger(__name__)

class TelegramMediaDownloader:
    """Telegram媒体文件下载器"""
    
    def __init__(self):
        self.client: Optional[TelegramClient] = None
        self._initialized = False
    
    async def initialize(self):
        """初始化Telegram客户端"""
        if self._initialized:
            return
        
        try:
            # 获取Telegram配置
            api_id = settings.telegram_api_id
            api_hash = settings.telegram_api_hash
            
            if not api_id or not api_hash:
                raise ValueError("Telegram API配置不完整")
            
            # 创建客户端
            self.client = TelegramClient(
                'media_downloader_session',
                api_id,
                api_hash
            )
            
            await self.client.start()
            self._initialized = True
            logger.info("Telegram媒体下载器初始化成功")
            
        except Exception as e:
            logger.error(f"Telegram媒体下载器初始化失败: {str(e)}")
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
        if not self._initialized:
            await self.initialize()
        
        if not self.client:
            logger.error("Telegram客户端未初始化")
            return False
        
        try:
            # 确保目标目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            if chat_id and message_id:
                # 通过聊天和消息ID获取文件
                try:
                    chat = await self.client.get_entity(chat_id)
                    messages = await self.client.get_messages(chat, ids=message_id)
                    message = messages[0] if messages and len(messages) > 0 else None
                    
                    if message and message.media:
                        await self.client.download_media(message.media, file_path)
                        logger.info(f"通过消息下载文件成功: {file_path}")
                        return True
                    else:
                        logger.warning(f"消息 {message_id} 不存在或无媒体内容")
                        return False
                        
                except Exception as e:
                    logger.error(f"通过消息ID下载失败: {e}")
                    return False
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
        if self.client:
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
        await _downloader.initialize()
    return _downloader