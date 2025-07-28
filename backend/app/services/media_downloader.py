import os
import logging
import shutil
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
        self._shared_client = None  # 共享的客户端实例
        # 使用独立的session路径，添加进程ID避免并发冲突
        import time
        session_id = f"downloader_{int(time.time() * 1000) % 100000}"
        self.session_name = os.path.join("./telegram_sessions", session_id)
    
    async def initialize(self):
        """初始化Telegram客户端"""
        if self._initialized and self.client and self.client.is_connected():
            return
        
        try:
            # 如果已有客户端实例，先断开
            if self.client:
                try:
                    await self.client.disconnect()
                except:
                    pass
                self.client = None
            
            # 获取Telegram配置 - 使用缓存避免重复数据库访问
            api_id = settings.telegram_api_id
            api_hash = settings.telegram_api_hash
            
            logger.info(f"媒体下载器 - API ID: {api_id}, API Hash: {'*' * len(str(api_hash)) if api_hash else 'None'}")
            
            if not api_id or not api_hash:
                raise ValueError(f"Telegram API配置不完整: API ID={api_id}, API Hash={'已设置' if api_hash else '未设置'}")
            
            # 确保session目录存在
            os.makedirs(os.path.dirname(self.session_name), exist_ok=True)
            
            # 为媒体下载器创建独立的session，避免与主服务的session文件冲突
            import time
            import threading
            downloader_session_name = os.path.join(
                "./telegram_sessions", 
                f"downloader_{threading.get_ident()}_{int(time.time() * 1000) % 100000}"
            )
            
            # 尝试复制主session文件到下载器session（如果主session存在）
            main_session_path = os.path.join("./telegram_sessions", "tggod_session.session")
            downloader_session_path = f"{downloader_session_name}.session"
            
            if os.path.exists(main_session_path) and not os.path.exists(downloader_session_path):
                try:
                    import shutil
                    shutil.copy2(main_session_path, downloader_session_path)
                    logger.info(f"已复制主session到下载器session: {downloader_session_path}")
                except Exception as copy_error:
                    logger.warning(f"复制session文件失败，将使用独立session: {copy_error}")
            
            # 创建客户端，使用独立的session文件
            self.client = TelegramClient(
                downloader_session_name,
                api_id,
                api_hash,
                # 使用更保守的连接配置
                connection_retries=2,
                retry_delay=2,
                timeout=30,
                use_ipv6=False
            )
            
            # 连接客户端
            logger.info("正在连接媒体下载器客户端...")
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
        message_id: Optional[int] = None,
        progress_callback: Optional[callable] = None
    ) -> bool:
        """
        下载媒体文件
        
        Args:
            file_id: Telegram文件ID
            file_path: 本地保存路径
            chat_id: 聊天ID（可选，用于获取更多文件信息）
            message_id: 消息ID（可选，用于获取更多文件信息）
            progress_callback: 进度回调函数
        
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
                return await self._download_by_message(chat_id, message_id, file_path, progress_callback)
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
        finally:
            # 下载完成后断开连接释放资源
            await self.cleanup()
    
    async def _download_by_message(self, chat_id: int, message_id: int, file_path: str, progress_callback: Optional[callable] = None) -> bool:
        """通过消息ID下载文件"""
        max_retries = 3
        logger.info(f"媒体下载器 - 接收到参数: chat_id={chat_id}, message_id={message_id}, file_path={file_path}")
        for attempt in range(max_retries):
            try:
                # 获取聊天实体
                logger.info(f"媒体下载器 - 尝试获取实体: chat_id={chat_id}")
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
                
                if progress_callback:
                    # 创建进度处理包装器
                    def progress_wrapper(current, total):
                        try:
                            if total > 0:
                                # 检查回调函数是否是异步的
                                import asyncio
                                if asyncio.iscoroutinefunction(progress_callback):
                                    # 对于异步回调，我们需要在当前事件循环中运行它
                                    loop = asyncio.get_event_loop()
                                    if loop.is_running():
                                        # 如果循环已经在运行，创建一个task
                                        loop.create_task(progress_callback(current, total))
                                    else:
                                        # 如果循环没有运行，直接运行
                                        loop.run_until_complete(progress_callback(current, total))
                                else:
                                    # 同步回调直接调用
                                    progress_callback(current, total)
                        except Exception as e:
                            logger.error(f"进度回调执行失败: {e}")
                            # 如果是取消下载的异常，停止下载
                            if str(e) == "下载已取消":
                                logger.info("检测到下载取消信号，停止下载过程")
                                raise e  # 向上传递异常以中断下载过程
                    
                    try:
                        await self.client.download_media(message.media, file_path, progress_callback=progress_wrapper)
                        
                        logger.info(f"通过消息下载文件成功: {file_path}")
                        return True
                    except Exception as e:
                        # 特殊处理下载取消异常
                        if str(e) == "下载已取消":
                            logger.info("下载已被用户取消")
                            # 重新抛出异常以便上层处理
                            raise
                        # 其他异常正常记录
                        logger.error(f"下载失败: {e}")
                        raise
                else:
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
            # 实际的Telegram API调用获取文件信息
            from telethon.tl.types import Document, Photo
            
            # 通过消息ID获取消息
            message = await self.client.get_messages(entity=None, ids=int(file_id))
            if not message or not message.media:
                return None
                
            media = message.media
            if isinstance(media, Document):
                return {
                    "file_id": file_id,
                    "file_size": media.size,
                    "mime_type": media.mime_type or "application/octet-stream"
                }
            elif isinstance(media, Photo):
                # 对于照片，获取最大尺寸的信息
                largest_size = max(media.sizes, key=lambda x: getattr(x, 'size', 0))
                return {
                    "file_id": file_id,
                    "file_size": getattr(largest_size, 'size', 0),
                    "mime_type": "image/jpeg"
                }
            else:
                # 其他媒体类型的基本信息
                return {
                    "file_id": file_id,
                    "file_size": getattr(media, 'size', 0),
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
    
    async def cleanup(self):
        """清理资源，下载完成后调用"""
        try:
            if self.client and self.client.is_connected():
                await self.client.disconnect()
                logger.info("媒体下载器连接已断开")
        except Exception as e:
            logger.warning(f"断开下载器连接时出错: {e}")
        finally:
            self._initialized = False
    
    async def close(self):
        """关闭客户端连接"""
        await self.cleanup()
        logger.info("Telegram媒体下载器已关闭")

async def get_media_downloader() -> TelegramMediaDownloader:
    """获取媒体下载器实例 - 每次创建独立实例避免session冲突"""
    logger.info("创建独立的媒体下载器实例")
    downloader = TelegramMediaDownloader()
    
    try:
        await downloader.initialize()
        logger.info("媒体下载器实例创建成功")
        return downloader
    except Exception as e:
        logger.error(f"媒体下载器初始化失败: {e}")
        # 确保清理资源
        try:
            await downloader.cleanup()
        except:
            pass
        raise