"""
优化的Telegram媒体文件下载服务

专注于内存优化和资源管理的媒体下载器
"""

import os
import logging
import shutil
import tempfile
import weakref
from typing import Optional, Dict, Any, AsyncGenerator
from telethon import TelegramClient
from telethon.errors import AuthKeyUnregisteredError, FloodWaitError
from ..config import settings
from ..core.memory_manager import memory_manager, ChunkedFileReader, memory_tracking, LRUCache
import asyncio
from datetime import datetime
import json

logger = logging.getLogger(__name__)

# 使用信号量控制并发连接数
_connection_semaphore = asyncio.Semaphore(2)

# 使用内存安全的全局缓存替代普通字典
_session_cache = LRUCache(max_size=100, max_memory_mb=10)


class OptimizedTelegramMediaDownloader:
    """内存优化的Telegram媒体文件下载器"""

    def __init__(self, chat_id: Optional[int] = None, message_id: Optional[int] = None):
        """初始化媒体下载器"""
        self.client: Optional[TelegramClient] = None
        self._initialized = False
        self.chat_id = chat_id
        self.message_id = message_id

        # 使用弱引用跟踪实例，避免循环引用
        memory_manager.tracker.track_object(self, f"MediaDownloader_{chat_id}_{message_id}")

        # 创建唯一session标识
        if chat_id and message_id:
            import hashlib
            session_key = f"{chat_id}_{message_id}"
            session_hash = hashlib.md5(session_key.encode()).hexdigest()[:12]
            session_id = f"download_{session_hash}"
        else:
            import threading
            session_id = f"downloader_{os.getpid()}_{threading.get_ident()}"

        self.session_name = os.path.join("./telegram_sessions", session_id)
        self.progress_file = f"{self.session_name}.progress"

        # 内存限制的进度缓冲区
        self._progress_buffer = []
        self._max_progress_entries = 10

    def __del__(self):
        """析构函数 - 确保资源清理"""
        try:
            # 清理session文件
            session_file = f"{self.session_name}.session"
            if os.path.exists(session_file):
                os.remove(session_file)

            # 清理进度文件
            if hasattr(self, 'progress_file') and os.path.exists(self.progress_file):
                os.remove(self.progress_file)

            # 从内存跟踪器中移除
            memory_manager.tracker.untrack_object(self)
        except:
            # 析构函数中不抛出异常
            pass

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.cleanup()

    def _save_progress_optimized(self, file_path: str, current: int, total: int):
        """优化的进度保存，使用内存缓冲"""
        try:
            progress_entry = {
                "file_path": file_path,
                "current": current,
                "total": total,
                "timestamp": datetime.now().isoformat(),
                "chat_id": self.chat_id,
                "message_id": self.message_id
            }

            # 使用内存缓冲，减少频繁的文件I/O
            self._progress_buffer.append(progress_entry)

            # 保持缓冲区大小限制
            if len(self._progress_buffer) > self._max_progress_entries:
                self._progress_buffer.pop(0)

            # 每10个条目或下载完成时批量写入
            if len(self._progress_buffer) >= 10 or current == total:
                self._flush_progress_buffer()

        except Exception as e:
            logger.warning(f"保存下载进度失败: {e}")

    def _flush_progress_buffer(self):
        """刷新进度缓冲区到文件"""
        if not self._progress_buffer:
            return

        try:
            os.makedirs(os.path.dirname(self.progress_file), exist_ok=True)

            # 只保存最新的进度
            latest_progress = self._progress_buffer[-1]

            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(latest_progress, f, indent=2)

            # 清空缓冲区
            self._progress_buffer.clear()

        except Exception as e:
            logger.warning(f"刷新进度缓冲区失败: {e}")

    def _load_progress(self, file_path: str) -> Optional[Dict[str, Any]]:
        """加载下载进度"""
        try:
            if not os.path.exists(self.progress_file):
                return None

            with open(self.progress_file, 'r', encoding='utf-8') as f:
                progress_data = json.load(f)

            # 验证进度数据
            if progress_data.get("file_path") == file_path:
                return progress_data

        except Exception as e:
            logger.warning(f"加载下载进度失败: {e}")

        return None

    def _clear_progress(self):
        """清理进度文件和缓冲区"""
        try:
            # 清空内存缓冲区
            self._progress_buffer.clear()

            # 删除进度文件
            if os.path.exists(self.progress_file):
                os.remove(self.progress_file)
        except Exception as e:
            logger.warning(f"清理进度失败: {e}")

    async def initialize(self):
        """初始化Telegram客户端"""
        if self._initialized and self.client and self.client.is_connected():
            return

        with memory_tracking("MediaDownloader.initialize"):
            try:
                # 清理旧客户端
                if self.client:
                    try:
                        await self.client.disconnect()
                    except:
                        pass
                    finally:
                        self.client = None

                # 检查缓存中的session状态
                cache_key = f"session_status_{self.chat_id}_{self.message_id}"
                cached_status = _session_cache.get(cache_key)

                if cached_status and not cached_status.get('valid', False):
                    raise AuthKeyUnregisteredError("缓存显示session无效")

                # 获取配置
                api_id = settings.telegram_api_id
                api_hash = settings.telegram_api_hash

                if not api_id or not api_hash:
                    raise ValueError(f"Telegram API配置不完整")

                # 设置session目录
                session_dir = os.path.dirname(self.session_name)
                os.makedirs(session_dir, exist_ok=True)
                os.chmod(session_dir, 0o755)

                # 复制主session文件
                await self._setup_session_file()

                # 创建客户端
                self.client = TelegramClient(
                    self.session_name,
                    api_id,
                    api_hash,
                    connection_retries=3,
                    retry_delay=2,
                    timeout=30,
                    use_ipv6=False
                )

                # 使用信号量控制并发连接
                async with _connection_semaphore:
                    await asyncio.sleep(0.5)  # 避免冲突
                    await self.client.connect()

                # 验证认证状态
                is_authorized = await self.client.is_user_authorized()
                if not is_authorized:
                    raise AuthKeyUnregisteredError("Session未授权")

                # 缓存session状态
                _session_cache.set(cache_key, {'valid': True, 'timestamp': datetime.now().timestamp()})

                self._initialized = True
                logger.info("优化媒体下载器初始化成功")

            except Exception as e:
                logger.error(f"媒体下载器初始化失败: {e}")
                await self._cleanup_internal()
                raise

    async def _setup_session_file(self):
        """设置session文件"""
        main_session_path = os.path.join("./telegram_sessions", "tggod_session.session")

        if not os.path.exists(main_session_path):
            raise ValueError("主session文件不存在")

        try:
            # 使用临时文件确保原子性复制
            with tempfile.NamedTemporaryFile(delete=False, suffix='.session') as temp_file:
                with open(main_session_path, 'rb') as src:
                    # 分块复制，避免大文件内存溢出
                    shutil.copyfileobj(src, temp_file, length=8192)
                temp_path = temp_file.name

            # 原子性移动
            target_path = f"{self.session_name}.session"
            shutil.move(temp_path, target_path)
            os.chmod(target_path, 0o666)

            logger.info("Session文件设置完成")

        except Exception as e:
            logger.error(f"Session文件设置失败: {e}")
            raise

    async def download_file_chunked(
        self,
        file_id: str,
        file_path: str,
        chat_id: Optional[int] = None,
        message_id: Optional[int] = None,
        progress_callback: Optional[callable] = None,
        chunk_size: int = 64 * 1024  # 64KB chunks
    ) -> bool:
        """
        分块下载文件，优化内存使用
        """
        try:
            await self.initialize()

            if not self.client or not self.client.is_connected():
                logger.error("Telegram客户端未连接")
                return False

            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            if chat_id and message_id:
                return await self._download_by_message_chunked(
                    chat_id, message_id, file_path, progress_callback, chunk_size
                )
            else:
                logger.warning("缺少必要参数")
                return False

        except Exception as e:
            logger.error(f"分块下载失败: {e}")
            # 清理不完整文件
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except:
                    pass
            return False
        finally:
            await self.cleanup()

    async def _download_by_message_chunked(
        self,
        chat_id: int,
        message_id: int,
        file_path: str,
        progress_callback: Optional[callable] = None,
        chunk_size: int = 64 * 1024
    ) -> bool:
        """通过消息ID分块下载文件"""
        max_retries = 3

        for attempt in range(max_retries):
            try:
                # 获取消息
                chat = await self.client.get_entity(chat_id)
                messages = await self.client.get_messages(chat, ids=message_id)

                message = messages[0] if hasattr(messages, '__iter__') else messages
                if not message or not message.media:
                    logger.warning(f"消息 {message_id} 无媒体内容")
                    return False

                # 获取媒体信息
                media_info = self._get_media_description(message.media)
                logger.info(f"开始分块下载: {media_info}")

                # 检查之前的进度
                saved_progress = self._load_progress(file_path)
                resume_from = 0
                if saved_progress:
                    resume_from = saved_progress.get('current', 0)
                    logger.info(f"从 {resume_from} 字节处恢复下载")

                # 创建进度回调包装器
                def progress_wrapper(current, total):
                    try:
                        # 调整为实际进度
                        actual_current = current + resume_from
                        self._save_progress_optimized(file_path, actual_current, total)

                        if progress_callback:
                            progress_percent = (actual_current / total) * 100 if total > 0 else 0

                            # 限制进度回调频率
                            if hasattr(progress_wrapper, '_last_percent'):
                                if abs(progress_percent - progress_wrapper._last_percent) < 5:
                                    return
                            progress_wrapper._last_percent = progress_percent

                            try:
                                if asyncio.iscoroutinefunction(progress_callback):
                                    asyncio.create_task(
                                        progress_callback(actual_current, total, progress_percent)
                                    )
                                else:
                                    progress_callback(actual_current, total, progress_percent)
                            except Exception as e:
                                logger.warning(f"进度回调错误: {e}")
                    except Exception as e:
                        logger.warning(f"进度处理错误: {e}")

                # 使用临时文件避免写入冲突
                temp_file_path = f"{file_path}.tmp"

                try:
                    # 执行下载
                    await asyncio.wait_for(
                        self.client.download_media(
                            message.media,
                            temp_file_path,
                            progress_callback=progress_wrapper if progress_callback else None
                        ),
                        timeout=600  # 10分钟超时
                    )

                    # 下载完成，移动到目标位置
                    if os.path.exists(temp_file_path):
                        shutil.move(temp_file_path, file_path)
                        logger.info(f"分块下载完成: {file_path}")
                        self._clear_progress()
                        return True
                    else:
                        logger.error("临时文件不存在")
                        return False

                except asyncio.TimeoutError:
                    logger.error(f"下载超时: {file_path}")
                    if os.path.exists(temp_file_path):
                        os.remove(temp_file_path)
                    raise
                except Exception as e:
                    logger.error(f"下载过程出错: {e}")
                    if os.path.exists(temp_file_path):
                        os.remove(temp_file_path)
                    raise

            except FloodWaitError as e:
                if attempt < max_retries - 1:
                    wait_time = min(e.seconds, 300)
                    logger.warning(f"遇到限速，等待 {wait_time} 秒")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"达到最大重试次数")
                    raise
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"尝试 {attempt + 1} 失败: {e}")
                    await asyncio.sleep(2)
                else:
                    logger.error(f"下载失败: {e}")
                    raise

        return False

    def _get_media_description(self, media) -> str:
        """获取媒体描述信息"""
        try:
            if hasattr(media, 'photo'):
                return "照片"
            elif hasattr(media, 'document'):
                doc = media.document
                if hasattr(doc, 'attributes'):
                    for attr in doc.attributes:
                        attr_type = type(attr).__name__
                        if 'Video' in attr_type:
                            duration = getattr(attr, 'duration', 0)
                            return f"视频 ({duration}秒)" if duration > 0 else "视频"
                        elif 'Audio' in attr_type:
                            duration = getattr(attr, 'duration', 0)
                            title = getattr(attr, 'title', '') or getattr(attr, 'file_name', '')
                            desc = f"音频 ({duration}秒)" if duration > 0 else "音频"
                            return f"{desc} - {title}" if title else desc
                        elif 'Animated' in attr_type:
                            return "GIF动图"
                        elif 'Sticker' in attr_type:
                            return "贴纸"
                return "文档"
            else:
                return "媒体文件"
        except Exception as e:
            logger.warning(f"获取媒体描述失败: {e}")
            return "未知媒体"

    async def cleanup(self):
        """清理资源"""
        await self._cleanup_internal()

    async def _cleanup_internal(self):
        """内部清理方法"""
        try:
            # 刷新待写入的进度
            self._flush_progress_buffer()

            # 断开客户端连接
            if self.client:
                try:
                    await self.client.disconnect()
                except Exception as e:
                    if "readonly database" in str(e):
                        logger.warning("断开连接时遇到只读数据库错误（已忽略）")
                    else:
                        logger.warning(f"断开连接错误: {e}")
                finally:
                    self.client = None

            self._initialized = False
            logger.info("媒体下载器资源清理完成")

        except Exception as e:
            logger.error(f"资源清理失败: {e}")


# 会话状态检查 - 使用缓存减少检查频率
async def check_session_status_cached() -> bool:
    """缓存的session状态检查"""
    cache_key = "main_session_status"
    cached_result = _session_cache.get(cache_key)

    # 如果缓存未过期（5分钟），直接返回
    if cached_result:
        cache_time = cached_result.get('timestamp', 0)
        if time.time() - cache_time < 300:  # 5分钟缓存
            return cached_result.get('valid', False)

    # 执行实际检查
    try:
        main_session_path = os.path.join("./telegram_sessions", "tggod_session.session")

        if not os.path.exists(main_session_path):
            result = False
        else:
            api_id = settings.telegram_api_id
            api_hash = settings.telegram_api_hash

            if not api_id or not api_hash:
                result = False
            else:
                temp_client = TelegramClient(
                    os.path.join("./telegram_sessions", "tggod_session"),
                    api_id,
                    api_hash,
                    connection_retries=1,
                    retry_delay=1,
                    timeout=10
                )

                try:
                    await temp_client.connect()
                    result = await temp_client.is_user_authorized()
                finally:
                    await temp_client.disconnect()

        # 缓存结果
        _session_cache.set(cache_key, {
            'valid': result,
            'timestamp': time.time()
        })

        return result

    except Exception as e:
        logger.warning(f"Session状态检查失败: {e}")
        # 缓存失败结果
        _session_cache.set(cache_key, {
            'valid': False,
            'timestamp': time.time()
        })
        return False


async def get_optimized_media_downloader(
    chat_id: Optional[int] = None,
    message_id: Optional[int] = None
) -> OptimizedTelegramMediaDownloader:
    """
    获取优化的媒体下载器实例
    """
    logger.info(f"创建优化媒体下载器: {chat_id}_{message_id}")

    downloader = OptimizedTelegramMediaDownloader(chat_id=chat_id, message_id=message_id)

    try:
        await downloader.initialize()
        return downloader
    except Exception as e:
        logger.error(f"媒体下载器初始化失败: {e}")
        await downloader.cleanup()
        raise


# 注册清理回调到全局内存管理器
def _cleanup_global_cache():
    """清理全局缓存"""
    _session_cache.clear()
    logger.info("媒体下载器全局缓存已清理")

memory_manager.add_cleanup_callback(_cleanup_global_cache)