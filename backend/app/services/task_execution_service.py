import asyncio
import logging
import shutil
import os
import time
from typing import Optional, List, Dict
from sqlalchemy import or_, and_
from sqlalchemy.orm import Session
from ..models.rule import DownloadTask, FilterRule
from ..models.telegram import TelegramMessage, TelegramGroup
from ..models.log import TaskLog
from .media_downloader import TelegramMediaDownloader
from .rule_sync_service import rule_sync_service
from ..utils.db_optimization import optimized_db_session
from ..websocket.manager import websocket_manager
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class TaskExecutionService:
    """任务执行服务"""
    
    def __init__(self):
        self.running_tasks: Dict[int, asyncio.Task] = {}
        self.media_downloader = TelegramMediaDownloader()
        self.jellyfin_service = None  # 延迟导入
        self._initialized = False
        # 日志批量处理
        self.pending_logs = []
        self.log_batch_size = 20  # 累积20条日志再批量写入，减少数据库访问
        self.last_log_flush = time.time()  # 上次刷新时间
    
    async def initialize(self):
        """初始化服务"""
        if self._initialized:
            return
        
        try:
            # 尝试初始化媒体下载器
            await self.media_downloader.initialize()
            logger.info("媒体下载器初始化成功")
            
        except Exception as e:
            logger.error(f"媒体下载器初始化失败: {e}")
            logger.warning("媒体下载功能将不可用，但服务将继续以有限模式运行")
            # 将媒体下载器设为None，表示不可用
            self.media_downloader = None
            
        try:
            # 延迟导入 JellyfinMediaService 避免循环导入
            from .jellyfin_media_service import JellyfinMediaService
            self.jellyfin_service = JellyfinMediaService()
            logger.info("Jellyfin媒体服务初始化成功")
        except ImportError as e:
            logger.warning(f"Jellyfin媒体服务导入失败，将禁用Jellyfin功能: {e}")
            self.jellyfin_service = None
        except Exception as e:
            logger.error(f"Jellyfin媒体服务初始化失败: {e}")
            self.jellyfin_service = None
        
        # 即使某些服务初始化失败，也标记为已初始化，允许基本功能运行
        self._initialized = True
        logger.info("任务执行服务初始化完成（可能以有限模式运行）")
        raise
    
    async def start_task(self, task_id: int) -> bool:
        """启动任务执行"""
        if task_id in self.running_tasks:
            logger.warning(f"任务 {task_id} 已在运行中")
            return False
        
        # 确保服务已初始化
        await self.initialize()
        
        # 创建异步任务
        task = asyncio.create_task(self._execute_task(task_id))
        self.running_tasks[task_id] = task
        
        logger.info(f"任务 {task_id} 已启动")
        return True
    
    async def pause_task(self, task_id: int) -> bool:
        """暂停任务执行"""
        if task_id not in self.running_tasks:
            return False
        
        # 取消异步任务
        task = self.running_tasks[task_id]
        task.cancel()
        
        # 更新数据库状态
        with optimized_db_session() as db:
            download_task = db.query(DownloadTask).filter(DownloadTask.id == task_id).first()
            if download_task:
                download_task.status = "paused"
                
                await self._log_task_event(task_id, "INFO", f"任务已暂停")
        
        del self.running_tasks[task_id]
        logger.info(f"任务 {task_id} 已暂停")
        return True
    
    async def stop_task(self, task_id: int) -> bool:
        """停止任务执行"""
        if task_id not in self.running_tasks:
            return False
        
        # 取消异步任务
        task = self.running_tasks[task_id]
        task.cancel()
        
        # 更新数据库状态
        with optimized_db_session() as db:
            download_task = db.query(DownloadTask).filter(DownloadTask.id == task_id).first()
            if download_task:
                download_task.status = "failed"
                download_task.error_message = "任务被手动停止"
                
                await self._log_task_event(task_id, "INFO", f"任务已停止")
        
        del self.running_tasks[task_id]
        logger.info(f"任务 {task_id} 已停止")
        return True
    
    async def _execute_task(self, task_id: int):
        """执行具体的下载任务"""
        with optimized_db_session() as db:
            try:
                # 获取任务信息
                download_task = db.query(DownloadTask).filter(DownloadTask.id == task_id).first()
                if not download_task:
                    logger.error(f"任务 {task_id} 不存在")
                    return
                
                # 获取规则和群组信息
                rule = db.query(FilterRule).filter(FilterRule.id == download_task.rule_id).first()
                group = db.query(TelegramGroup).filter(TelegramGroup.id == download_task.group_id).first()
                
                if not rule or not group:
                    await self._handle_task_error(task_id, "规则或群组不存在", db)
                    return
                
                await self._log_task_event(task_id, "INFO", f"开始执行任务: {download_task.name}")
                
                # 应用规则筛选消息，并考虑任务的日期范围
                messages = await self._filter_messages(rule, group, download_task, db)
                total_messages = len(messages)
                
                if total_messages == 0:
                    await self._handle_task_completion(task_id, "没有找到符合条件的消息", db)
                    return
                
                # 更新任务总数
                download_task.total_messages = total_messages
                download_task.downloaded_messages = 0
                download_task.progress = 0
                
                await self._log_task_event(task_id, "INFO", f"找到 {total_messages} 条符合条件的消息")
                
                # 创建下载目录
                download_dir = os.path.join(download_task.download_path)
                os.makedirs(download_dir, exist_ok=True)
                
                # 执行下载
                downloaded_count = 0
                failed_count = 0
                
                for i, message in enumerate(messages):
                    try:
                        # 检查任务是否被取消
                        if task_id not in self.running_tasks:
                            logger.info(f"任务 {task_id} 已被取消")
                            return
                        
                        # 下载媒体文件
                        if message.media_type and message.media_type != 'text':
                            success = await self._download_message_media(message, download_task, group, task_id)
                            if success:
                                downloaded_count += 1
                            else:
                                failed_count += 1
                        
                        # 更新进度
                        progress = int((i + 1) / total_messages * 100)
                        download_task.progress = progress
                        download_task.downloaded_messages = downloaded_count
                        
                        # 发送进度更新
                        await self._send_progress_update(task_id, progress, downloaded_count, total_messages)
                        
                        # 避免过于频繁的下载
                        await asyncio.sleep(0.5)
                        
                    except Exception as e:
                        logger.error(f"下载消息 {message.id} 失败: {e}")
                        failed_count += 1
                        await self._log_task_event(task_id, "ERROR", f"下载消息 {message.id} 失败: {str(e)}")
                
                # 任务完成
                await self._handle_task_completion(
                    task_id, 
                    f"任务完成，成功下载 {downloaded_count} 个文件，失败 {failed_count} 个", 
                    db
                )
            
            except asyncio.CancelledError:
                logger.info(f"任务 {task_id} 被取消")
                raise
            except Exception as e:
                logger.error(f"执行任务 {task_id} 时发生错误: {e}")
                await self._handle_task_error(task_id, str(e), db)
            finally:
                # 清理运行中的任务记录
                if task_id in self.running_tasks:
                    del self.running_tasks[task_id]
    
    async def _filter_messages(self, rule: FilterRule, group: TelegramGroup, task: DownloadTask, db: Session) -> List[TelegramMessage]:
        """根据规则筛选消息，同时考虑任务的日期范围"""
        
        # 确保规则有足够的数据可供查询
        try:
            sync_result = await rule_sync_service.ensure_rule_data_availability(rule.id, db)
            logger.info(f"规则 {rule.id} 数据可用性检查完成: {sync_result}")
            
            if sync_result['sync_performed']:
                await self._log_task_event(task.id, "INFO", 
                    f"执行了 {sync_result['sync_type']} 同步，同步了 {sync_result.get('message_count', 0)} 条消息")
        except Exception as e:
            logger.warning(f"规则数据同步失败，继续使用现有数据: {e}")
            await self._log_task_event(task.id, "WARNING", f"规则数据同步失败: {str(e)}")
        
        # 基础查询 - 预加载群组关系以避免后续查询时的N+1问题
        from sqlalchemy.orm import joinedload
        query = db.query(TelegramMessage).options(joinedload(TelegramMessage.group)).filter(TelegramMessage.group_id == group.id)
        
        # 优化: 增量查询 - 如果任务有上次处理时间，只查询新消息
        if hasattr(task, 'last_processed_time') and task.last_processed_time:
            query = query.filter(TelegramMessage.date > task.last_processed_time)
            await self._log_task_event(task.id, "INFO", f"增量筛选: 只查询 {task.last_processed_time} 之后的消息")
            logger.info(f"增量筛选: 只查询 {task.last_processed_time} 之后的消息")
        elif not getattr(task, 'force_full_scan', False):
            # 如果不是强制全量扫描，记录使用完整数据集
            await self._log_task_event(task.id, "INFO", "使用完整数据集进行筛选")
            logger.info("使用规则的完整数据集进行筛选")
        
        # 应用规则筛选
        if rule.keywords:
            keyword_conditions = []
            for keyword in rule.keywords:
                # 处理text字段可能为空的情况，同时搜索消息文本、发送者名称和媒体文件名
                text_condition = and_(
                    TelegramMessage.text.isnot(None),
                    TelegramMessage.text.contains(keyword)
                )
                sender_condition = and_(
                    TelegramMessage.sender_name.isnot(None),
                    TelegramMessage.sender_name.contains(keyword)
                )
                filename_condition = and_(
                    TelegramMessage.media_filename.isnot(None),
                    TelegramMessage.media_filename.contains(keyword)
                )
                keyword_conditions.append(or_(text_condition, sender_condition, filename_condition))
            if keyword_conditions:
                query = query.filter(or_(*keyword_conditions))
        
        if rule.exclude_keywords:
            for exclude_keyword in rule.exclude_keywords:
                # 处理text字段可能为空的情况，排除包含关键词的消息文本、发送者名称和媒体文件名
                text_exclude = and_(
                    TelegramMessage.text.isnot(None),
                    TelegramMessage.text.contains(exclude_keyword)
                )
                sender_exclude = and_(
                    TelegramMessage.sender_name.isnot(None),
                    TelegramMessage.sender_name.contains(exclude_keyword)
                )
                filename_exclude = and_(
                    TelegramMessage.media_filename.isnot(None),
                    TelegramMessage.media_filename.contains(exclude_keyword)
                )
                query = query.filter(~or_(text_exclude, sender_exclude, filename_exclude))
        
        if rule.media_types:
            query = query.filter(TelegramMessage.media_type.in_(rule.media_types))
        
        if rule.sender_filter:
            query = query.filter(TelegramMessage.sender_username.in_(rule.sender_filter))
        
        # 优先使用任务的日期范围，如果没有则使用规则的日期范围
        date_from = task.date_from if task.date_from else rule.date_from
        date_to = task.date_to if task.date_to else rule.date_to
        
        if date_from:
            query = query.filter(TelegramMessage.date >= date_from)
        
        if date_to:
            query = query.filter(TelegramMessage.date <= date_to)
        
        if rule.min_views is not None:
            query = query.filter(TelegramMessage.views >= rule.min_views)
        
        if rule.max_views is not None:
            query = query.filter(TelegramMessage.views <= rule.max_views)
        
        # 文件大小过滤
        if rule.min_file_size is not None:
            query = query.filter(TelegramMessage.media_size >= rule.min_file_size)
        
        if rule.max_file_size is not None:
            query = query.filter(TelegramMessage.media_size <= rule.max_file_size)
        
        if not rule.include_forwarded:
            query = query.filter(TelegramMessage.is_forwarded == False)
        
        # 只选择有媒体的消息
        query = query.filter(TelegramMessage.media_type != 'text')
        query = query.filter(TelegramMessage.media_type.isnot(None))
        
        results = query.order_by(TelegramMessage.date.desc()).all()
        
        # 优化: 更新任务的最后处理时间，用于下次增量查询
        if results:
            latest_processed = max(msg.date for msg in results)
            try:
                # 更新任务的最后处理时间
                if hasattr(task, 'last_processed_time'):
                    task.last_processed_time = latest_processed
                    db.commit()
                    await self._log_task_event(task.id, "INFO", f"已更新任务最后处理时间: {latest_processed}")
                    logger.info(f"任务 {task.id} 最后处理时间已更新: {latest_processed}")
            except Exception as e:
                logger.warning(f"更新任务最后处理时间失败: {e}")
        
        return results
    
    async def _download_message_media(self, message: TelegramMessage, download_task: DownloadTask, group: TelegramGroup, task_id: int) -> bool:
        """下载单个消息的媒体文件"""
        try:
            # 检查是否使用 Jellyfin 格式
            if download_task.use_jellyfin_structure and self.jellyfin_service:
                # 使用 Jellyfin 服务下载
                jellyfin_config = {
                    'use_jellyfin_structure': download_task.use_jellyfin_structure,
                    'include_metadata': download_task.include_metadata,
                    'download_thumbnails': download_task.download_thumbnails,
                    'use_series_structure': download_task.use_series_structure,
                    'organize_by_date': download_task.organize_by_date,
                    'max_filename_length': download_task.max_filename_length,
                    'thumbnail_size': self._parse_size_string(download_task.thumbnail_size),
                    'poster_size': self._parse_size_string(download_task.poster_size),
                    'fanart_size': self._parse_size_string(download_task.fanart_size)
                }
                
                success, error_msg, file_paths = await self.jellyfin_service.download_media_with_jellyfin_structure(
                    message=message,
                    group=group,
                    task=download_task,
                    jellyfin_config=jellyfin_config
                )
                
                if success:
                    logger.info(f"Jellyfin格式下载成功: {file_paths.get('main_media', 'unknown')}")
                    await self._log_task_event(task_id, "INFO", f"Jellyfin格式下载成功，文件数: {len(file_paths)}")
                    return True
                else:
                    logger.error(f"Jellyfin格式下载失败: {error_msg}")
                    await self._log_task_event(task_id, "ERROR", f"Jellyfin格式下载失败: {error_msg}")
                    return False
            elif download_task.use_jellyfin_structure and not self.jellyfin_service:
                # Jellyfin服务未可用，回退到传统下载
                logger.warning("Jellyfin服务不可用，使用传统下载方式")
                await self._log_task_event(task_id, "WARNING", "Jellyfin服务不可用，使用传统下载方式")
            else:
                # 使用传统下载方式
                download_dir = download_task.download_path
                # 确保下载目录存在
                os.makedirs(download_dir, exist_ok=True)
                
                file_extension = self._get_file_extension(message.media_type)
                filename = f"{message.message_id}_{message.id}{file_extension}"
                file_path = os.path.join(download_dir, filename)
                
                # 检查文件是否已存在
                if os.path.exists(file_path):
                    logger.info(f"文件已存在，跳过下载: {file_path}")
                    return True
                
                # 检查媒体下载器是否可用
                if not self.media_downloader:
                    logger.error(f"媒体下载器不可用，无法下载文件: {filename}")
                    return False
                
                # 定义进度回调函数
                async def progress_callback(current: int, total: int):
                    await self._log_download_progress(task_id, message.id, current, total)
                
                # 使用媒体下载器下载文件
                success = await self.media_downloader.download_file(
                    file_id=message.media_file_id or "",
                    file_path=file_path,
                    chat_id=message.group.telegram_id,
                    message_id=message.message_id,
                    progress_callback=progress_callback
                )
                
                if success:
                    logger.info(f"成功下载文件: {filename}")
                    return True
                else:
                    logger.warning(f"下载文件失败: {filename}")
                    return False
            
        except Exception as e:
            logger.error(f"下载消息 {message.id} 的媒体文件失败: {e}")
            await self._log_task_event(task_id, "ERROR", f"下载文件失败: {str(e)}")
            return False
    
    def _get_file_extension(self, media_type: str) -> str:
        """根据媒体类型获取文件扩展名"""
        extensions = {
            'photo': '.jpg',
            'video': '.mp4',
            'document': '.doc',
            'audio': '.mp3',
            'voice': '.ogg',
            'video_note': '.mp4',
            'sticker': '.webp'
        }
        return extensions.get(media_type, '.bin')
    
    def _parse_size_string(self, size_str: str) -> tuple:
        """解析尺寸字符串 '400x300' -> (400, 300)"""
        try:
            if not size_str or 'x' not in size_str:
                return (400, 300)  # 默认尺寸
            
            parts = size_str.split('x')
            if len(parts) != 2:
                return (400, 300)
            
            width = int(parts[0])
            height = int(parts[1])
            return (width, height)
        except (ValueError, AttributeError):
            return (400, 300)  # 默认尺寸
    
    
    async def _handle_task_completion(self, task_id: int, message: str, db: Session):
        """处理任务完成"""
        download_task = db.query(DownloadTask).filter(DownloadTask.id == task_id).first()
        if download_task:
            download_task.status = "completed"
            download_task.progress = 100
            download_task.completed_at = datetime.now(timezone.utc)
            
            # 如果是循环任务，不要重置进度和消息计数，因为调度器会处理
            # 只有一次性任务才真正"完成"
            if getattr(download_task, 'task_type', 'once') == 'once':
                # 一次性任务完成后彻底结束
                pass
            else:
                # 循环任务完成后等待下次调度
                logger.info(f"循环任务 {task_id} 本次执行完成，等待下次调度")
            
            db.commit()
        
        await self._log_task_event(task_id, "INFO", message)
        await self._send_task_status_update(task_id, "completed", message)
    
    async def _handle_task_error(self, task_id: int, error_message: str, db: Session):
        """处理任务错误"""
        download_task = db.query(DownloadTask).filter(DownloadTask.id == task_id).first()
        if download_task:
            download_task.status = "failed"
            download_task.error_message = error_message
            db.commit()
        
        await self._log_task_event(task_id, "ERROR", error_message)
        await self._send_task_status_update(task_id, "failed", error_message)
    
    async def _log_task_event(self, task_id: int, level: str, message: str, details: Optional[Dict] = None):
        """记录任务事件日志"""
        # 先尝试通过WebSocket发送日志 - 无论数据库操作是否成功都确保UI更新
        timestamp = datetime.now(timezone.utc)
        try:
            await websocket_manager.broadcast({
                "type": "task_log",
                "task_id": task_id,
                "level": level,
                "message": message,
                "timestamp": timestamp.isoformat()
            })
        except Exception as e:
            logger.error(f"WebSocket广播日志失败: {e}")
        
        # 只添加重要日志到批处理队列，跳过DEBUG级别的进度日志
        if level in ["ERROR", "WARNING", "INFO"]:
            # 添加到待处理队列
            log_entry = {
                "task_id": task_id,
                "level": level,
                "message": message,
                "details": details,
                "created_at": timestamp
            }
            self.pending_logs.append(log_entry)
            
            # 当积累足够日志或遇到错误/警告级别或超时时立即刷新
            current_time = time.time()
            should_flush = (
                level in ["ERROR", "WARNING"] or  # 重要日志立即刷新
                len(self.pending_logs) >= self.log_batch_size or  # 批量大小达到
                (self.pending_logs and current_time - self.last_log_flush > 5.0)  # 超过5秒未刷新
            )
            
            if should_flush:
                await self._flush_pending_logs()
                
    async def _flush_pending_logs(self):
        """批量处理待写入的日志"""
        if not self.pending_logs:
            return
            
        logs_to_write = self.pending_logs.copy()
        self.pending_logs = []
        self.last_log_flush = time.time()  # 更新刷新时间
        
        try:
            with optimized_db_session(max_retries=5) as db:
                for log in logs_to_write:
                    # 只保存重要日志到数据库
                    if log["level"] in ["ERROR", "WARNING", "INFO"]:
                        db_log = TaskLog(
                            task_id=log["task_id"],
                            level=log["level"],
                            message=log["message"],
                            details=log["details"],
                            created_at=log["created_at"]
                        )
                        db.add(db_log)
        except Exception as e:
            logger.error(f"批量写入日志失败: {e}")
            # 失败时将未写入的重要日志重新加入队列
            for log in logs_to_write:
                if log["level"] in ["ERROR", "WARNING", "INFO"]:
                    self.pending_logs.append(log)
    
    async def _log_download_progress(self, task_id: int, message_id: int, current: int, total: int):
        """记录下载进度（优化：减少数据库写入频率）"""
        if total > 0:
            progress = int(current / total * 100)
            
            # 只在特定进度节点记录日志，避免频繁数据库写入导致锁定
            # 记录：0%, 25%, 50%, 75%, 100% 和每10%的整数进度
            if progress == 0 or progress == 100 or progress % 25 == 0 or progress % 10 == 0:
                await self._log_task_event(
                    task_id, 
                    "DEBUG", 
                    f"消息 {message_id} 下载进度: {progress}%",
                    {"message_id": message_id, "current": current, "total": total}
                )
    
    async def _send_progress_update(self, task_id: int, progress: int, downloaded: int, total: int):
        """发送进度更新"""
        await websocket_manager.broadcast({
            "type": "task_progress",
            "task_id": task_id,
            "progress": progress,
            "downloaded": downloaded,
            "total": total,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    async def _send_task_status_update(self, task_id: int, status: str, message: str):
        """发送任务状态更新"""
        await websocket_manager.broadcast({
            "type": "task_status",
            "task_id": task_id,
            "status": status,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    def get_running_tasks(self) -> List[int]:
        """获取正在运行的任务列表"""
        return list(self.running_tasks.keys())
    
    def is_task_running(self, task_id: int) -> bool:
        """检查任务是否正在运行"""
        return task_id in self.running_tasks

# 创建全局任务执行服务实例
task_execution_service = TaskExecutionService()