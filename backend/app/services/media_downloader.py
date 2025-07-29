import os
import logging
import shutil
from typing import Optional, Dict, Any
from telethon import TelegramClient
from telethon.errors import AuthKeyUnregisteredError, FloodWaitError
from ..config import settings
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)

# 全局信号量控制并发连接数，避免数据库锁定
_connection_semaphore = asyncio.Semaphore(2)

class TelegramMediaDownloader:
    """Telegram媒体文件下载器"""
    
    def __init__(self, chat_id: Optional[int] = None, message_id: Optional[int] = None):
        self.client: Optional[TelegramClient] = None
        self._initialized = False
        self._shared_client = None  # 共享的客户端实例
        self.chat_id = chat_id
        self.message_id = message_id
        
        # 使用消息ID创建持久化session，这样可以保持下载进度
        if chat_id and message_id:
            # 基于聊天ID和消息ID创建唯一但持久的session名称
            import hashlib
            session_key = f"{chat_id}_{message_id}"
            session_hash = hashlib.md5(session_key.encode()).hexdigest()[:12]
            session_id = f"download_{session_hash}"
        else:
            # 如果没有提供消息信息，使用进程ID作为备用方案
            import threading
            session_id = f"downloader_{os.getpid()}_{threading.get_ident()}"
        
        self.session_name = os.path.join("./telegram_sessions", session_id)
        
        # 下载进度文件路径
        self.progress_file = f"{self.session_name}.progress"
    
    def _save_progress(self, file_path: str, current: int, total: int):
        """保存下载进度到文件"""
        try:
            import json
            progress_data = {
                "file_path": file_path,
                "current": current,
                "total": total,
                "timestamp": str(datetime.now()),
                "chat_id": self.chat_id,
                "message_id": self.message_id
            }
            
            os.makedirs(os.path.dirname(self.progress_file), exist_ok=True)
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, indent=2)
                
        except Exception as e:
            logger.warning(f"保存下载进度失败: {e}")
    
    def _load_progress(self, file_path: str) -> Optional[Dict[str, Any]]:
        """从文件加载下载进度"""
        try:
            if not os.path.exists(self.progress_file):
                return None
                
            import json
            with open(self.progress_file, 'r', encoding='utf-8') as f:
                progress_data = json.load(f)
            
            # 验证进度数据是否匹配当前下载任务
            if progress_data.get("file_path") == file_path:
                return progress_data
                
        except Exception as e:
            logger.warning(f"加载下载进度失败: {e}")
        
        return None
    
    def _clear_progress(self):
        """清理进度文件"""
        try:
            if os.path.exists(self.progress_file):
                os.remove(self.progress_file)
        except Exception as e:
            logger.warning(f"清理进度文件失败: {e}")
    
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
            
            # 确保session目录存在并有正确权限
            session_dir = os.path.dirname(self.session_name)
            os.makedirs(session_dir, exist_ok=True)
            # 设置目录权限，确保可读写
            os.chmod(session_dir, 0o755)
            
            # 使用独立session文件避免数据库锁定问题
            main_session_path = os.path.join("./telegram_sessions", "tggod_session")
            
            # 检查主session是否存在
            if not os.path.exists(f"{main_session_path}.session"):
                raise ValueError("主session文件不存在，请确保主服务已完成认证")
            
            # 检查并修复主session文件权限
            try:
                main_session_file = f"{main_session_path}.session"
                current_stat = os.stat(main_session_file)
                if oct(current_stat.st_mode)[-3:] != '666':
                    logger.info("修复主session文件权限")
                    os.chmod(main_session_file, 0o666)
            except Exception as perm_error:
                logger.warning(f"无法修复主session文件权限: {perm_error}")
            
            logger.info(f"复制主session到独立文件: {self.session_name}")
            
            # 使用临时文件安全地复制session文件
            import tempfile
            
            try:
                # 复制session文件到独立路径，避免并发访问
                if os.path.exists(f"{main_session_path}.session"):
                    # 使用临时文件确保原子性复制
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.session') as temp_file:
                        with open(f"{main_session_path}.session", 'rb') as src:
                            shutil.copyfileobj(src, temp_file)
                        temp_path = temp_file.name
                    
                    # 原子性移动到目标位置
                    shutil.move(temp_path, f"{self.session_name}.session")
                    
                    # 设置文件权限为可读写，解决只读数据库问题
                    os.chmod(f"{self.session_name}.session", 0o666)
                    logger.info("Session文件复制完成，权限已设置为可读写")
                
                # 使用独立的session文件
                self.client = TelegramClient(
                    self.session_name,
                    api_id,
                    api_hash,
                    connection_retries=3,
                    retry_delay=2,
                    timeout=30,
                    use_ipv6=False
                )
                
            except Exception as e:
                logger.error(f"Session文件复制失败: {e}")
                # 回退到内存session
                logger.info("回退到内存session模式")
                self.client = TelegramClient(
                    f":memory:",
                    api_id,
                    api_hash,
                    connection_retries=3,
                    retry_delay=2,
                    timeout=30,
                    use_ipv6=False
                )
            
            # 使用信号量控制并发连接，避免数据库锁定
            async with _connection_semaphore:
                # 连接前稍作延迟，避免与主服务冲突
                await asyncio.sleep(0.5)
                
                # 连接客户端
                logger.info("正在连接媒体下载器客户端...")
                await self.client.connect()
            
            # 检查认证状态
            is_authorized = await self.client.is_user_authorized()
            if not is_authorized:
                raise AuthKeyUnregisteredError("主session未授权，请重新认证Telegram服务")
            
            self._initialized = True
            logger.info("Telegram媒体下载器初始化成功")
            
        except AuthKeyUnregisteredError as e:
            logger.error(f"媒体下载器认证失败: {str(e)}")
            logger.error("请确保主Telegram服务已完成认证")
            await self._cleanup()
            raise
        except Exception as e:
            logger.error(f"Telegram媒体下载器初始化失败: {str(e)}")
            await self._cleanup()
            raise
    
    async def _cleanup(self, force_remove_session: bool = False):
        """清理资源和临时文件"""
        try:
            # 断开客户端连接
            if self.client:
                try:
                    await self.client.disconnect()
                except Exception as e:
                    # 处理SQLite只读错误，避免影响清理过程
                    if "attempt to write a readonly database" in str(e):
                        logger.warning(f"断开下载器连接时遇到只读数据库错误（已忽略）: {e}")
                    else:
                        logger.warning(f"断开下载器连接时出错: {e}")
                finally:
                    self.client = None
            
            # 根据参数决定是否清理session文件
            if force_remove_session and hasattr(self, 'session_name') and self.session_name:
                session_file = f"{self.session_name}.session"
                if os.path.exists(session_file):
                    try:
                        os.remove(session_file)
                        logger.info(f"已清理session文件: {session_file}")
                    except Exception as e:
                        logger.warning(f"清理session文件失败: {e}")
            
            self._initialized = False
            
        except Exception as e:
            logger.error(f"资源清理失败: {e}")
    
    def __del__(self):
        """析构函数，确保资源被清理"""
        if hasattr(self, 'session_name') and self.session_name:
            session_file = f"{self.session_name}.session"
            if os.path.exists(session_file):
                try:
                    os.remove(session_file)
                except:
                    pass  # 忽略析构函数中的错误
    
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
                    # 检查是否有之前的下载进度
                    saved_progress = self._load_progress(file_path)
                    if saved_progress:
                        current_progress = saved_progress.get('current', 0)
                        total_size = saved_progress.get('total', 0)
                        if total_size > 0:
                            logger.info(f"发现之前的下载进度: {current_progress}/{total_size} ({current_progress/total_size*100:.1f}%)")
                    
                    # 增强的进度处理包装器 - 包含进度保存功能
                    def progress_wrapper(current, total):
                        try:
                            if total > 0:
                                # 保存下载进度到文件
                                self._save_progress(file_path, current, total)
                                
                                # 使用简化的进度报告，避免异步回调问题
                                progress_percent = (current / total) * 100
                                # 每5%报告一次进度，提供更细粒度的进度信息
                                if int(progress_percent) % 5 == 0 or current == total:
                                    logger.info(f"下载进度: {current}/{total} ({progress_percent:.1f}%)")
                                
                                # 尝试调用回调，但不要让回调错误中断下载
                                try:
                                    if asyncio.iscoroutinefunction(progress_callback):
                                        # 对于异步回调，使用 call_soon_threadsafe 来避免死锁
                                        loop = asyncio.get_event_loop()
                                        if loop.is_running():
                                            # 在这里我们不等待异步回调完成，避免死锁
                                            asyncio.create_task(progress_callback(current, total, progress_percent))
                                    else:
                                        # 直接调用同步回调
                                        progress_callback(current, total, progress_percent)
                                except Exception as callback_error:
                                    # 进度回调错误不应该中断下载
                                    logger.warning(f"进度回调警告: {callback_error}")
                        except Exception as e:
                            # 包装器本身的错误也不应该中断下载
                            logger.warning(f"进度包装器警告: {e}")
                    
                    try:
                        logger.info(f"开始下载文件: {file_path}")
                        # 添加下载超时，防止卡住（10分钟超时）
                        await asyncio.wait_for(
                            self.client.download_media(message.media, file_path, progress_callback=progress_wrapper),
                            timeout=600
                        )
                        
                        logger.info(f"通过消息下载文件成功: {file_path}")
                        # 下载成功后清理进度文件
                        self._clear_progress()
                        return True
                    except asyncio.TimeoutError:
                        logger.error(f"下载超时 (10分钟): {file_path}")
                        raise
                    except Exception as e:
                        logger.error(f"下载失败: {e}")
                        raise
                else:
                    logger.info(f"开始下载文件 (无进度回调): {file_path}")
                    # 添加下载超时，即使没有进度回调
                    await asyncio.wait_for(
                        self.client.download_media(message.media, file_path),
                        timeout=600
                    )
                    
                    logger.info(f"通过消息下载文件成功: {file_path}")
                    # 下载成功后清理进度文件
                    self._clear_progress()
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
                error_msg = str(e)
                # 特殊处理SQLite只读数据库错误
                if "attempt to write a readonly database" in error_msg:
                    if attempt < max_retries - 1:
                        logger.warning(f"下载尝试 {attempt + 1} 遇到只读数据库错误，尝试重新初始化连接后重试...")
                        # 强制重新初始化客户端
                        await self._cleanup(force_remove_session=True)
                        self._initialized = False
                        await asyncio.sleep(2)  # 等待更长时间确保清理完成
                        await self.initialize()
                    else:
                        logger.error(f"通过消息ID下载失败（只读数据库错误）: {e}")
                        raise
                else:
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

# 全局session状态管理
_session_status_cache = {}
_last_session_check = 0

async def check_main_session_status():
    """检查主session的认证状态，并缓存结果"""
    global _session_status_cache, _last_session_check
    
    import time
    current_time = time.time()
    
    # 缓存5分钟
    if current_time - _last_session_check < 300 and 'main_session_valid' in _session_status_cache:
        return _session_status_cache['main_session_valid']
    
    try:
        main_session_path = os.path.join("./telegram_sessions", "tggod_session.session")
        
        if not os.path.exists(main_session_path):
            _session_status_cache['main_session_valid'] = False
            _last_session_check = current_time
            return False
        
        # 使用主session创建临时客户端检查认证状态
        api_id = settings.telegram_api_id
        api_hash = settings.telegram_api_hash
        
        if not api_id or not api_hash:
            _session_status_cache['main_session_valid'] = False
            _last_session_check = current_time
            return False
        
        temp_client = TelegramClient(
            os.path.join("./telegram_sessions", "tggod_session"),
            api_id,
            api_hash,
            connection_retries=1,
            retry_delay=1,
            timeout=10
        )
        
        await temp_client.connect()
        is_authorized = await temp_client.is_user_authorized()
        await temp_client.disconnect()
        
        _session_status_cache['main_session_valid'] = is_authorized
        _last_session_check = current_time
        
        logger.info(f"主session认证状态: {'有效' if is_authorized else '无效'}")
        return is_authorized
        
    except Exception as e:
        logger.warning(f"检查主session状态失败: {e}")
        _session_status_cache['main_session_valid'] = False
        _last_session_check = current_time
        return False

async def invalidate_session_cache():
    """清除session状态缓存，强制重新检查"""
    global _session_status_cache, _last_session_check
    _session_status_cache.clear()
    _last_session_check = 0
    logger.info("已清除session状态缓存")

async def get_media_downloader(chat_id: Optional[int] = None, message_id: Optional[int] = None) -> TelegramMediaDownloader:
    """
    获取媒体下载器实例 - 使用消息ID创建持久化session
    
    Args:
        chat_id: 聊天ID，用于创建持久化session
        message_id: 消息ID，用于创建持久化session
        
    Returns:
        TelegramMediaDownloader实例
    """
    if chat_id and message_id:
        logger.info(f"创建基于消息ID的持久化媒体下载器实例: {chat_id}_{message_id}")
    else:
        logger.info("创建临时媒体下载器实例")
    
    downloader = TelegramMediaDownloader(chat_id=chat_id, message_id=message_id)
    
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