import asyncio
import logging
import shutil
import os
from typing import Optional, List, Dict
from sqlalchemy import or_
from sqlalchemy.orm import Session
from ..models.rule import DownloadTask, FilterRule
from ..models.telegram import TelegramMessage, TelegramGroup
from ..models.log import TaskLog
from .media_downloader import TelegramMediaDownloader
from ..database import SessionLocal
from ..websocket.manager import websocket_manager
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class TaskExecutionService:
    """任务执行服务"""
    
    def __init__(self):
        self.running_tasks: Dict[int, asyncio.Task] = {}
        self.media_downloader = TelegramMediaDownloader()
        self._initialized = False
    
    async def initialize(self):
        """初始化服务"""
        if self._initialized:
            return
        
        try:
            await self.media_downloader.initialize()
            self._initialized = True
            logger.info("任务执行服务初始化成功")
        except Exception as e:
            logger.error(f"任务执行服务初始化失败: {e}")
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
        db = SessionLocal()
        try:
            download_task = db.query(DownloadTask).filter(DownloadTask.id == task_id).first()
            if download_task:
                download_task.status = "paused"
                db.commit()
                
                await self._log_task_event(task_id, "INFO", f"任务已暂停")
        finally:
            db.close()
        
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
        db = SessionLocal()
        try:
            download_task = db.query(DownloadTask).filter(DownloadTask.id == task_id).first()
            if download_task:
                download_task.status = "failed"
                download_task.error_message = "任务被手动停止"
                db.commit()
                
                await self._log_task_event(task_id, "INFO", f"任务已停止")
        finally:
            db.close()
        
        del self.running_tasks[task_id]
        logger.info(f"任务 {task_id} 已停止")
        return True
    
    async def _execute_task(self, task_id: int):
        """执行具体的下载任务"""
        db = SessionLocal()
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
            
            # 应用规则筛选消息
            messages = await self._filter_messages(rule, group, db)
            total_messages = len(messages)
            
            if total_messages == 0:
                await self._handle_task_completion(task_id, "没有找到符合条件的消息", db)
                return
            
            # 更新任务总数
            download_task.total_messages = total_messages
            download_task.downloaded_messages = 0
            download_task.progress = 0
            db.commit()
            
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
                        success = await self._download_message_media(message, download_dir, task_id)
                        if success:
                            downloaded_count += 1
                        else:
                            failed_count += 1
                    
                    # 更新进度
                    progress = int((i + 1) / total_messages * 100)
                    download_task.progress = progress
                    download_task.downloaded_messages = downloaded_count
                    db.commit()
                    
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
            db.close()
            # 清理运行中的任务记录
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
    
    async def _filter_messages(self, rule: FilterRule, group: TelegramGroup, db: Session) -> List[TelegramMessage]:
        """根据规则筛选消息"""
        query = db.query(TelegramMessage).filter(TelegramMessage.group_id == group.id)
        
        # 应用规则筛选
        if rule.keywords:
            keyword_conditions = []
            for keyword in rule.keywords:
                keyword_conditions.append(TelegramMessage.text.contains(keyword))
            if keyword_conditions:
                query = query.filter(or_(*keyword_conditions))
        
        if rule.exclude_keywords:
            for exclude_keyword in rule.exclude_keywords:
                query = query.filter(~TelegramMessage.text.contains(exclude_keyword))
        
        if rule.media_types:
            query = query.filter(TelegramMessage.media_type.in_(rule.media_types))
        
        if rule.sender_filter:
            query = query.filter(TelegramMessage.sender_username.in_(rule.sender_filter))
        
        if rule.date_from:
            query = query.filter(TelegramMessage.date >= rule.date_from)
        
        if rule.date_to:
            query = query.filter(TelegramMessage.date <= rule.date_to)
        
        if rule.min_views is not None:
            query = query.filter(TelegramMessage.views >= rule.min_views)
        
        if rule.max_views is not None:
            query = query.filter(TelegramMessage.views <= rule.max_views)
        
        # 文件大小过滤
        if rule.min_file_size is not None:
            query = query.filter(TelegramMessage.file_size >= rule.min_file_size)
        
        if rule.max_file_size is not None:
            query = query.filter(TelegramMessage.file_size <= rule.max_file_size)
        
        if not rule.include_forwarded:
            query = query.filter(TelegramMessage.is_forwarded == False)
        
        # 只选择有媒体的消息
        query = query.filter(TelegramMessage.media_type != 'text')
        query = query.filter(TelegramMessage.media_type.isnot(None))
        
        return query.order_by(TelegramMessage.date.desc()).all()
    
    async def _download_message_media(self, message: TelegramMessage, download_dir: str, task_id: int) -> bool:
        """下载单个消息的媒体文件"""
        try:
            # 构建文件名
            file_extension = self._get_file_extension(message.media_type)
            filename = f"{message.message_id}_{message.id}{file_extension}"
            file_path = os.path.join(download_dir, filename)
            
            # 检查文件是否已存在
            if os.path.exists(file_path):
                logger.info(f"文件已存在，跳过下载: {filename}")
                return True
            
            # 定义进度回调函数
            async def progress_callback(current: int, total: int):
                await self._log_download_progress(task_id, message.id, current, total)
            
            # 使用媒体下载器下载文件
            success = await self.media_downloader.download_file(
                file_id=message.file_id or "",
                file_path=file_path,
                chat_id=message.group_id,
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
    
    
    async def _handle_task_completion(self, task_id: int, message: str, db: Session):
        """处理任务完成"""
        download_task = db.query(DownloadTask).filter(DownloadTask.id == task_id).first()
        if download_task:
            download_task.status = "completed"
            download_task.progress = 100
            download_task.completed_at = datetime.now(timezone.utc)
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
        db = SessionLocal()
        try:
            log_entry = TaskLog(
                task_id=task_id,
                level=level,
                message=message,
                details=details
            )
            db.add(log_entry)
            db.commit()
            
            # 通过WebSocket发送日志
            await websocket_manager.broadcast({
                "type": "task_log",
                "task_id": task_id,
                "level": level,
                "message": message,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        except Exception as e:
            logger.error(f"记录任务日志失败: {e}")
        finally:
            db.close()
    
    async def _log_download_progress(self, task_id: int, message_id: int, current: int, total: int):
        """记录下载进度"""
        if total > 0:
            progress = int(current / total * 100)
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