import asyncio
import logging
import shutil
import os
import time
import asyncio
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
from .task_db_manager import task_db_manager
from .file_organizer_service import FileOrganizerService
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class TaskExecutionService:
    """任务执行服务"""
    
    def __init__(self):
        self.running_tasks: Dict[int, asyncio.Task] = {}
        self.media_downloader = TelegramMediaDownloader()
        self.jellyfin_service = None  # 延迟导入
        self.file_organizer = FileOrganizerService()  # 文件组织服务
        self._initialized = False
        # 日志批量处理
        self.pending_logs = []
        self.log_batch_size = 50  # 累积50条日志再批量写入，进一步减少数据库访问
        self.last_log_flush = time.time()  # 上次刷新时间  # 上次刷新时间
    
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
                db.commit()
        
        # 在会话外记录日志事件
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
                db.commit()
        
        # 在会话外记录日志事件
        await self._log_task_event(task_id, "INFO", f"任务已停止")
        
        del self.running_tasks[task_id]
        logger.info(f"任务 {task_id} 已停止")
        return True
    
    async def _execute_task(self, task_id: int):
        """执行具体的下载任务（优化：避免长时间持有数据库会话）"""
        try:
            # 第一阶段：获取任务信息和筛选消息（短时间数据库操作）
            task_info = await self._prepare_task_execution(task_id)
            if not task_info:
                return
            
            task_data, messages = task_info
            total_messages = len(messages)
            
            await self._log_task_event(task_id, "INFO", f"开始执行任务: {task_data['task_name']}")
            await self._log_task_event(task_id, "INFO", f"找到 {total_messages} 条符合条件的消息")
            
            # 创建下载目录
            download_dir = os.path.join(task_data['download_path'])
            os.makedirs(download_dir, exist_ok=True)
            
            # 第二阶段：执行下载循环（无数据库会话持有）
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
                        success = await self._download_message_media(message, task_data, task_id)
                        if success:
                            downloaded_count += 1
                        else:
                            failed_count += 1
                    
                    # 更新进度（短时间数据库操作）
                    progress = int((i + 1) / total_messages * 100)
                    await self._update_task_progress(task_id, progress, downloaded_count)
                    
                    # 发送进度更新
                    await self._send_progress_update(task_id, progress, downloaded_count, total_messages)
                    
                    # 避免过于频繁的下载，同时让其他任务有机会访问数据库
                    await asyncio.sleep(0.2)  # 减少延迟，提高效率
                    
                except Exception as e:
                    logger.error(f"下载消息 {message.id} 失败: {e}")
                    failed_count += 1
                    await self._log_task_event(task_id, "ERROR", f"下载消息 {message.id} 失败: {str(e)}")
            
            # 第三阶段：任务完成处理（短时间数据库操作）
            await self._complete_task_execution(
                task_id, 
                f"任务完成，成功下载 {downloaded_count} 个文件，失败 {failed_count} 个"
            )
            
        except asyncio.CancelledError:
            logger.info(f"任务 {task_id} 被取消")
            raise
        except Exception as e:
            logger.error(f"执行任务 {task_id} 时发生错误: {e}")
            await self._handle_task_error_simple(task_id, str(e))
        finally:
            # 清理运行中的任务记录
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
    
    async def _prepare_task_execution(self, task_id: int):
        """准备任务执行：获取任务信息和筛选消息（修复：支持多规则架构）"""
        # 第一步：快速获取基本信息并转换为字典
        task_data = None
        all_rules_data = []
        
        # 第一步：获取基本数据，检查数据完整性
        error_message = None
        
        with optimized_db_session() as db:
            # 获取任务信息
            download_task = db.query(DownloadTask).filter(DownloadTask.id == task_id).first()
            if not download_task:
                logger.error(f"任务 {task_id} 不存在")
                return None
            
            # 获取群组信息
            group = db.query(TelegramGroup).filter(TelegramGroup.id == download_task.group_id).first()
            if not group:
                error_message = "群组不存在"
            else:
                # 获取任务关联的所有规则
                from ..models.task_rule_association import TaskRuleAssociation
                from ..models.rule import FilterRule
                
                rule_associations = db.query(TaskRuleAssociation).filter(
                    TaskRuleAssociation.task_id == task_id,
                    TaskRuleAssociation.is_active == True
                ).order_by(TaskRuleAssociation.priority.desc()).all()
                
                if not rule_associations:
                    error_message = "任务没有关联的活跃规则"
                else:
                    # 获取所有规则详细信息
                    rule_ids = [assoc.rule_id for assoc in rule_associations]
                    rules = db.query(FilterRule).filter(FilterRule.id.in_(rule_ids)).all()
                    
                    if not rules:
                        error_message = "关联的规则不存在"
        
        # 第二步：在会话外处理错误（避免数据库锁定）
        if error_message:
            await self._handle_task_error_simple(task_id, error_message)
            return None
        
        # 第三步：重新获取数据进行处理（会话已关闭，重新开启）
        with optimized_db_session() as db:
            # 重新获取任务信息
            download_task = db.query(DownloadTask).filter(DownloadTask.id == task_id).first()
            group = db.query(TelegramGroup).filter(TelegramGroup.id == download_task.group_id).first()
            
            # 重新获取规则信息
            from ..models.task_rule_association import TaskRuleAssociation
            from ..models.rule import FilterRule
            
            rule_associations = db.query(TaskRuleAssociation).filter(
                TaskRuleAssociation.task_id == task_id,
                TaskRuleAssociation.is_active == True
            ).order_by(TaskRuleAssociation.priority.desc()).all()
            
            rule_ids = [assoc.rule_id for assoc in rule_associations]
            rules = db.query(FilterRule).filter(FilterRule.id.in_(rule_ids)).all()
            
            # 将对象数据提取为字典，避免会话绑定问题
            task_data = {
                'task_id': download_task.id,
                'task_name': download_task.name,
                'download_path': download_task.download_path,
                'use_jellyfin_structure': getattr(download_task, 'use_jellyfin_structure', False),
                'include_metadata': getattr(download_task, 'include_metadata', False),
                'download_thumbnails': getattr(download_task, 'download_thumbnails', False),
                'use_series_structure': getattr(download_task, 'use_series_structure', False),
                'organize_by_date': getattr(download_task, 'organize_by_date', False),
                'max_filename_length': getattr(download_task, 'max_filename_length', 255),
                'thumbnail_size': getattr(download_task, 'thumbnail_size', '400x300'),
                'poster_size': getattr(download_task, 'poster_size', '400x600'),
                'fanart_size': getattr(download_task, 'fanart_size', '1920x1080'),
                'group_id': group.id,
                'group_telegram_id': group.telegram_id,
                'group_title': group.title,
                'group_name': group.title,  # 群组名称（保留兼容性）
                'group_username': group.username,
                'subscription_name': download_task.name  # 订阅名（任务名）- 用于Jellyfin格式
            }
            
            # 提取所有规则数据
            for rule in rules:
                rule_data = {
                    'id': rule.id,
                    'name': rule.name,
                    'keywords': rule.keywords,
                    'exclude_keywords': rule.exclude_keywords,
                    'media_types': rule.media_types,
                    'sender_filter': rule.sender_filter,
                    'min_file_size': rule.min_file_size,
                    'max_file_size': rule.max_file_size,
                    'include_forwarded': rule.include_forwarded,
                    'date_from': rule.date_from,
                    'date_to': rule.date_to,
                    'min_views': rule.min_views,
                    'max_views': rule.max_views,
                    # 添加高级过滤条件
                    'min_duration': getattr(rule, 'min_duration', None),
                    'max_duration': getattr(rule, 'max_duration', None),
                    'min_width': getattr(rule, 'min_width', None),
                    'max_width': getattr(rule, 'max_width', None),
                    'min_height': getattr(rule, 'min_height', None),
                    'max_height': getattr(rule, 'max_height', None),
                    'min_text_length': getattr(rule, 'min_text_length', None),
                    'max_text_length': getattr(rule, 'max_text_length', None),
                    'has_urls': getattr(rule, 'has_urls', None),
                    'has_mentions': getattr(rule, 'has_mentions', None),
                    'has_hashtags': getattr(rule, 'has_hashtags', None),
                    'is_reply': getattr(rule, 'is_reply', None),
                    'is_edited': getattr(rule, 'is_edited', None),
                    'is_pinned': getattr(rule, 'is_pinned', None)
                }
                all_rules_data.append(rule_data)
            
            # 检查增量查询字段
            task_data['last_processed_time'] = getattr(download_task, 'last_processed_time', None)
            task_data['force_full_scan'] = getattr(download_task, 'force_full_scan', False)
        
        # 第二步：在会话外执行耗时的数据同步（为所有规则确保数据可用性）
        for rule_data in all_rules_data:
            await self._ensure_rule_data_availability(rule_data['id'], task_id)
        
        # 第三步：执行筛选查询（支持多规则OR逻辑）
        messages = await self._filter_messages_with_multiple_rules(all_rules_data, task_data, task_id)
        
        if len(messages) == 0:
            await self._complete_task_execution(task_id, "没有找到符合任何规则条件的消息")
            return None
        
        # 第四步：更新任务总数
        with optimized_db_session() as db:
            # 重新获取任务对象（因为之前的会话已关闭）
            download_task = db.query(DownloadTask).filter(DownloadTask.id == task_id).first()
            if not download_task:
                return None
                
            download_task.total_messages = len(messages)
            download_task.downloaded_messages = 0
            download_task.progress = 0
            db.commit()
        
        return task_data, messages
    
    async def _update_task_progress(self, task_id: int, progress: int, downloaded_count: int):
        """更新任务进度（优化：减少频繁的数据库更新）"""
        # 只在进度发生显著变化时才更新数据库
        if not hasattr(self, '_last_progress_update'):
            self._last_progress_update = {}
        
        last_update = self._last_progress_update.get(task_id, {'progress': -1, 'count': -1})
        
        # 减少数据库更新频率：只有在进度变化超过10%或下载数量变化超过20时才更新
        progress_diff = abs(progress - last_update['progress'])
        count_diff = abs(downloaded_count - last_update['count'])
        
        if progress_diff >= 10 or count_diff >= 20 or progress == 0 or progress == 100:
            logger.debug(f"任务{task_id}: 触发进度更新 - 进度: {progress}%, 下载数: {downloaded_count}")
            try:
                # 使用专用数据库管理器进行进度更新
                async with task_db_manager.get_task_session(task_id, "progress") as session:
                    download_task = session.query(DownloadTask).filter(DownloadTask.id == task_id).first()
                    if download_task:
                        logger.debug(f"任务{task_id}: 找到任务记录，更新进度数据")
                        download_task.progress = progress
                        download_task.downloaded_messages = downloaded_count
                        session.commit()
                        
                        # 记录最后更新的进度
                        self._last_progress_update[task_id] = {
                            'progress': progress, 
                            'count': downloaded_count
                        }
                        logger.debug(f"任务{task_id}: 进度更新成功 - 进度: {progress}%, 下载数: {downloaded_count}")
                    else:
                        logger.warning(f"任务{task_id}: 未找到任务记录，无法更新进度")
                        
            except Exception as e:
                logger.error(f"任务{task_id}: 更新任务进度失败 - {e}", exc_info=True)  # 不抛出异常，避免中断下载
    
    async def _complete_task_execution(self, task_id: int, message: str):
        """完成任务执行"""
        # 添加文件组织统计信息到完成消息
        completion_message = message
        if hasattr(self, '_organization_stats') and self._organization_stats:
            stats = self.file_organizer.get_organization_stats()
            organized_count = self._organization_stats.get('organized_files', 0)
            duplicate_count = stats.get('duplicate_files_count', 0)
            
            if organized_count > 0 or duplicate_count > 0:
                stats_msg = f" [文件整理: 已整理{organized_count}个文件"
                if duplicate_count > 0:
                    stats_msg += f", 跳过{duplicate_count}个重复文件"
                stats_msg += "]"
                completion_message += stats_msg
                
                # 记录详细统计信息
                await self._log_task_event(task_id, "INFO", 
                    f"文件组织统计: 整理文件{organized_count}个, 重复文件{duplicate_count}个")
                
                # 清理文件组织缓存
                self.file_organizer.clear_cache()
                if hasattr(self, '_organization_stats'):
                    delattr(self, '_organization_stats')
        
        # 使用快速状态更新
        await task_db_manager.quick_status_update(task_id, "completed")
        await self._log_task_event(task_id, "INFO", completion_message)
    
    async def _handle_task_error_simple(self, task_id: int, error_message: str):
        """处理任务错误（简化版，使用快速状态更新）"""
        # 使用快速状态更新
        await task_db_manager.quick_status_update(task_id, "failed", error_message)
        await self._log_task_event(task_id, "ERROR", error_message)
    
    async def _ensure_rule_data_availability(self, rule_id: int, task_id: int):
        """确保规则数据可用性（在会话外执行）"""
        try:
            with optimized_db_session() as db:
                sync_result = await rule_sync_service.ensure_rule_data_availability(rule_id, db)
                logger.info(f"规则 {rule_id} 数据可用性检查完成: {sync_result}")
                
                if sync_result['sync_performed']:
                    await self._log_task_event(task_id, "INFO", 
                        f"执行了 {sync_result['sync_type']} 同步，同步了 {sync_result.get('message_count', 0)} 条消息")
        except Exception as e:
            logger.warning(f"规则数据同步失败，继续使用现有数据: {e}")
            await self._log_task_event(task_id, "WARNING", f"规则数据同步失败: {str(e)}")
    
    async def _filter_messages_optimized(self, rule_data: dict, task_data: dict, task_id: int) -> List[TelegramMessage]:
        """优化的消息筛选方法（使用数据字典，减少数据库锁定时间）"""
        # 第一步：快速构建查询，不立即执行
        base_query_params = {
            'group_id': task_data['group_id'],
            'last_processed_time': task_data.get('last_processed_time'),
            'force_full_scan': task_data.get('force_full_scan', False)
        }
        
# 第二步：使用专用数据库管理器执行查询
        logger.info(f"任务{task_id}: 开始批量查询操作，群组ID: {base_query_params['group_id']}")
        async with task_db_manager.get_task_session(task_id, "batch_query") as db:
            try:
                # 基础查询 - 预加载group关联以避免后续会话绑定问题
                logger.debug(f"任务{task_id}: 构建基础查询条件")
                from sqlalchemy.orm import joinedload
                query = db.query(TelegramMessage).options(joinedload(TelegramMessage.group)).filter(TelegramMessage.group_id == base_query_params['group_id'])
                
                # 增量查询优化
                if base_query_params['last_processed_time']:
                    query = query.filter(TelegramMessage.date > base_query_params['last_processed_time'])
                    await self._log_task_event(task_id, "INFO", f"增量筛选: 只查询 {base_query_params['last_processed_time']} 之后的消息")
                    logger.info(f"增量筛选: 只查询 {base_query_params['last_processed_time']} 之后的消息")
                elif not base_query_params['force_full_scan']:
                    await self._log_task_event(task_id, "INFO", "使用完整数据集进行筛选")
                    logger.info("使用规则的完整数据集进行筛选")
                
                # 应用规则筛选
                query = self._apply_rule_filters_from_dict(query, rule_data)
                
                # 分批查询以减少锁定时间
                batch_size = 1000  # 每批1000条记录
                all_results = []
                offset = 0
                
                while True:
                    # 执行分批查询
                    batch_query = query.order_by(TelegramMessage.date.desc()).offset(offset).limit(batch_size)
                    batch_results = batch_query.all()
                    
                    if not batch_results:
                        break
                    
                    # 立即将批次结果从会话中分离
                    for message in batch_results:
                        db.expunge(message)
                        
                    all_results.extend(batch_results)
                    offset += batch_size
                    
                    # 如果批次小于限制，说明已经是最后一批
                    if len(batch_results) < batch_size:
                        break
                        
                    # 每批之间短暂释放锁
                    await asyncio.sleep(0.01)
                
                logger.info(f"任务 {task_id} 筛选完成，共找到 {len(all_results)} 条消息")
                logger.debug(f"任务{task_id}: 所有消息对象已在批次处理中从会话分离")
                
                # 第三步：使用单独的会话更新任务时间
                if all_results and base_query_params['last_processed_time'] is not None:
                    await self._update_task_processed_time(task_data['task_id'], all_results)
                
                return all_results
                
            except Exception as e:
                logger.error(f"任务{task_id}: 消息筛选查询失败: {e}", exc_info=True)
                await self._log_task_event(task_id, "ERROR", f"消息筛选失败: {str(e)}")
                raise
    
    async def _filter_messages_with_multiple_rules(self, all_rules_data: List[dict], task_data: dict, task_id: int) -> List[TelegramMessage]:
        """支持多规则的消息筛选方法（使用OR逻辑组合多个规则）"""
        # 第一步：快速构建查询，不立即执行
        base_query_params = {
            'group_id': task_data['group_id'],
            'last_processed_time': task_data.get('last_processed_time'),
            'force_full_scan': task_data.get('force_full_scan', False)
        }
        
        logger.info(f"任务{task_id}: 开始多规则批量查询操作，群组ID: {base_query_params['group_id']}, 规则数量: {len(all_rules_data)}")
        
        # 第二步：使用专用数据库管理器执行查询
        async with task_db_manager.get_task_session(task_id, "batch_query") as db:
            try:
                # 基础查询 - 预加载group关联以避免后续会话绑定问题
                logger.debug(f"任务{task_id}: 构建基础查询条件")
                from sqlalchemy.orm import joinedload
                from sqlalchemy import or_
                
                query = db.query(TelegramMessage).options(joinedload(TelegramMessage.group)).filter(
                    TelegramMessage.group_id == base_query_params['group_id']
                )
                
                # 增量查询优化
                if base_query_params['last_processed_time']:
                    query = query.filter(TelegramMessage.date > base_query_params['last_processed_time'])
                    await self._log_task_event(task_id, "INFO", f"增量筛选: 只查询 {base_query_params['last_processed_time']} 之后的消息")
                    logger.info(f"增量筛选: 只查询 {base_query_params['last_processed_time']} 之后的消息")
                elif not base_query_params['force_full_scan']:
                    await self._log_task_event(task_id, "INFO", "使用完整数据集进行多规则筛选")
                    logger.info("使用规则的完整数据集进行多规则筛选")
                
                # 应用多规则筛选（OR逻辑）
                rule_conditions = []
                for rule_data in all_rules_data:
                    logger.debug(f"任务{task_id}: 处理规则 {rule_data['id']} - {rule_data['name']}")
                    
                    # 为每个规则创建一个子查询条件
                    rule_query = db.query(TelegramMessage.id).filter(TelegramMessage.group_id == base_query_params['group_id'])
                    
                    # 增量查询条件也应用到每个规则
                    if base_query_params['last_processed_time']:
                        rule_query = rule_query.filter(TelegramMessage.date > base_query_params['last_processed_time'])
                    
                    # 应用规则筛选条件
                    rule_query = self._apply_rule_filters_from_dict(rule_query, rule_data)
                    
                    # 添加到OR条件中
                    rule_conditions.append(TelegramMessage.id.in_(rule_query))
                
                # 如果有规则条件，应用OR逻辑
                if rule_conditions:
                    query = query.filter(or_(*rule_conditions))
                    logger.info(f"任务{task_id}: 应用了 {len(rule_conditions)} 个规则的OR组合条件")
                
                # 分批查询以减少锁定时间
                batch_size = 1000  # 每批1000条记录
                all_results = []
                offset = 0
                
                while True:
                    # 执行分批查询
                    batch_query = query.order_by(TelegramMessage.date.desc()).offset(offset).limit(batch_size)
                    batch_results = batch_query.all()
                    
                    if not batch_results:
                        break
                    
                    # 立即将批次结果从会话中分离
                    for message in batch_results:
                        db.expunge(message)
                        
                    all_results.extend(batch_results)
                    offset += batch_size
                    
                    # 如果批次小于限制，说明已经是最后一批
                    if len(batch_results) < batch_size:
                        break
                        
                    # 每批之间短暂释放锁
                    await asyncio.sleep(0.01)
                
                logger.info(f"任务 {task_id} 多规则筛选完成，共找到 {len(all_results)} 条消息")
                logger.debug(f"任务{task_id}: 所有消息对象已在批次处理中从会话分离")
                
                # 第三步：使用单独的会话更新任务时间
                if all_results and base_query_params['last_processed_time'] is not None:
                    await self._update_task_processed_time(task_data['task_id'], all_results)
                
                return all_results
                
            except Exception as e:
                logger.error(f"任务{task_id}: 多规则消息筛选查询失败: {e}", exc_info=True)
                await self._log_task_event(task_id, "ERROR", f"多规则消息筛选失败: {str(e)}")
                raise
    
    async def _update_task_processed_time(self, task_id: int, messages: List[TelegramMessage]):
        """单独的会话更新任务处理时间"""
        try:
            latest_message_time = max(msg.date for msg in messages if msg.date)
            with optimized_db_session(max_retries=10) as update_db:
                task_update = update_db.query(DownloadTask).filter(DownloadTask.id == task_id).first()
                if task_update:
                    task_update.last_processed_time = latest_message_time
                    update_db.commit()
                    logger.debug(f"更新任务 {task_id} 处理时间: {latest_message_time}")
        except Exception as e:
            logger.warning(f"更新任务处理时间失败: {e}")  # 不抛出异常，因为这不是关键操作
    
    def _apply_rule_filters(self, query, rule: FilterRule):
        """应用规则筛选条件"""
        # 关键词筛选
        if rule.keywords:
            keyword_conditions = []
            for keyword in rule.keywords:
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
        
        # 排除关键词
        if rule.exclude_keywords:
            for exclude_keyword in rule.exclude_keywords:
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
        
        # 其他筛选条件
        if rule.media_types:
            query = query.filter(TelegramMessage.media_type.in_(rule.media_types))
        
        if rule.sender_filter:
            query = query.filter(TelegramMessage.sender_username.in_(rule.sender_filter))
        
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
        
        return query

    def _apply_rule_filters_from_dict(self, query, rule_data: dict):
        """应用规则筛选条件（使用字典数据，避免SQLAlchemy会话绑定问题）"""
        from sqlalchemy import and_, or_
        from ..models.telegram import TelegramMessage
        
        # 关键词筛选
        keywords = rule_data.get('keywords')
        if keywords:
            keyword_conditions = []
            for keyword in keywords:
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
        
        # 排除关键词
        exclude_keywords = rule_data.get('exclude_keywords')
        if exclude_keywords:
            for exclude_keyword in exclude_keywords:
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
        
        # 其他筛选条件
        media_types = rule_data.get('media_types')
        if media_types:
            query = query.filter(TelegramMessage.media_type.in_(media_types))
        
        sender_filter = rule_data.get('sender_filter')
        if sender_filter:
            query = query.filter(TelegramMessage.sender_username.in_(sender_filter))
        
        # 文件大小过滤
        min_file_size = rule_data.get('min_file_size')
        if min_file_size is not None:
            query = query.filter(TelegramMessage.media_size >= min_file_size)
        
        max_file_size = rule_data.get('max_file_size')
        if max_file_size is not None:
            query = query.filter(TelegramMessage.media_size <= max_file_size)
        
        include_forwarded = rule_data.get('include_forwarded', True)
        if not include_forwarded:
            query = query.filter(TelegramMessage.is_forwarded == False)
        
        # 只选择有媒体的消息
        query = query.filter(TelegramMessage.media_type != 'text')
        query = query.filter(TelegramMessage.media_type.isnot(None))
        
        return query
    
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
    
    async def _download_message_media(self, message: TelegramMessage, task_data: dict, task_id: int) -> bool:
        """下载单个消息的媒体文件"""
        try:
            # 检查是否使用 Jellyfin 格式
            if task_data.get('use_jellyfin_structure') and self.jellyfin_service:
                # 使用 Jellyfin 服务下载
                jellyfin_config = {
                    'use_jellyfin_structure': task_data.get('use_jellyfin_structure'),
                    'include_metadata': task_data.get('include_metadata'),
                    'download_thumbnails': task_data.get('download_thumbnails'),
                    'use_series_structure': task_data.get('use_series_structure'),
                    'organize_by_date': task_data.get('organize_by_date'),
                    'max_filename_length': task_data.get('max_filename_length'),
                    'thumbnail_size': self._parse_size_string(task_data.get('thumbnail_size')),
                    'poster_size': self._parse_size_string(task_data.get('poster_size')),
                    'fanart_size': self._parse_size_string(task_data.get('fanart_size'))
                }
                
                # 需要重新获取group和task对象用于Jellyfin服务
                # 使用短时间数据库会话
                async with task_db_manager.get_task_session(task_id, "jellyfin_download") as session:
                    from ..models.rule import DownloadTask
                    from ..models.telegram import TelegramGroup
                    
                    download_task = session.query(DownloadTask).filter(DownloadTask.id == task_data['task_id']).first()
                    group = session.query(TelegramGroup).filter(TelegramGroup.id == task_data['group_id']).first()
                    
                    if not download_task or not group:
                        logger.error(f"任务{task_id}: 无法获取下载任务或群组信息")
                        return False
                    
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
            elif task_data.get('use_jellyfin_structure') and not self.jellyfin_service:
                # Jellyfin服务未可用，回退到传统下载
                logger.warning("Jellyfin服务不可用，使用传统下载方式")
                await self._log_task_event(task_id, "WARNING", "Jellyfin服务不可用，使用传统下载方式")
            
            # 使用传统下载方式
            download_dir = task_data['download_path']
            # 确保下载目录存在
            os.makedirs(download_dir, exist_ok=True)
            
            file_extension = self._get_file_extension(message.media_type)
            filename = f"{message.message_id}_{message.id}{file_extension}"
            file_path = os.path.join(download_dir, filename)
            
            # 检查文件是否已存在
            if os.path.exists(file_path):
                logger.info(f"文件已存在，跳过下载: {file_path}")
                # 即使文件已存在，也检查是否需要整理
                organize_success = await self._organize_downloaded_file(file_path, message, task_data, task_id)
                
                # 创建下载记录（使用整理后的文件路径）
                final_file_path = file_path
                if organize_success and hasattr(self, '_last_organized_path'):
                    final_file_path = self._last_organized_path
                
                await self._create_download_record(message, task_data, final_file_path, task_id)
                return True
            
            # 检查媒体下载器是否可用
            if not self.media_downloader:
                logger.error(f"媒体下载器不可用，无法下载文件: {filename}")
                return False
            
            # 定义进度回调函数（兼容不同的进度回调签名）
            async def progress_callback(current: int, total: int, progress_percent: float = None):
                # 如果没有提供进度百分比，自己计算
                if progress_percent is None and total > 0:
                    progress_percent = (current / total) * 100
                elif progress_percent is None:
                    progress_percent = 0
                    
                await self._log_download_progress(task_id, message.id, current, total, progress_percent)
            
            # 实时从数据库获取最新的群组ID，避免使用缓存的过期数据
            from ..models.telegram import TelegramGroup as TGGroup  # 使用别名避免作用域问题
            with optimized_db_session() as db:
                current_group = db.query(TGGroup).filter(TGGroup.id == task_data['group_id']).first()
                if not current_group:
                    logger.error(f"任务{task_id}: 无法找到群组ID {task_data['group_id']}")
                    return False, None
                current_group_telegram_id = current_group.telegram_id
            
            # 调试日志：确认传递的ID
            logger.info(f"任务{task_id}: 准备下载文件 - group_telegram_id: {current_group_telegram_id}, message_id: {message.message_id}")
            
            # 群组ID已修复，移除验证逻辑
            
            # 使用媒体下载器下载文件
            success = await self.media_downloader.download_file(
                file_id=message.media_file_id or "",
                file_path=file_path,
                chat_id=current_group_telegram_id,
                message_id=message.message_id,
                progress_callback=progress_callback
            )
            
            if success:
                logger.info(f"成功下载文件: {filename}")
                
                # 文件下载成功后进行整理
                organize_success = await self._organize_downloaded_file(file_path, message, task_data, task_id)
                
                # 创建下载记录（使用整理后的文件路径）
                final_file_path = file_path  # 如果整理失败，使用原始路径
                if organize_success and hasattr(self, '_last_organized_path'):
                    final_file_path = self._last_organized_path
                
                await self._create_download_record(message, task_data, final_file_path, task_id)
                return True
            else:
                logger.warning(f"下载文件失败: {filename}")
                return False
            
        except Exception as e:
            logger.error(f"下载消息 {message.id} 的媒体文件失败: {e}")
            await self._log_task_event(task_id, "ERROR", f"下载文件失败: {str(e)}")
            return False

    async def _organize_downloaded_file(self, 
                                       file_path: str, 
                                       message: 'TelegramMessage', 
                                       task_data: dict, 
                                       task_id: int) -> bool:
        """
        整理已下载的文件
        
        Args:
            file_path: 下载的文件路径
            message: 消息对象
            task_data: 任务数据
            task_id: 任务ID
        
        Returns:
            整理是否成功
        """
        try:
            logger.info(f"任务{task_id}: 开始整理文件 {file_path}")
            
            # 调试日志：输出Jellyfin相关配置
            logger.info(f"任务{task_id}: Jellyfin配置检查 - use_jellyfin_structure: {task_data.get('use_jellyfin_structure', False)}")
            logger.info(f"任务{task_id}: Jellyfin配置检查 - use_series_structure: {task_data.get('use_series_structure', False)}")
            logger.info(f"任务{task_id}: Jellyfin配置检查 - organize_by_date: {task_data.get('organize_by_date', False)}")
            logger.info(f"任务{task_id}: Jellyfin配置检查 - group_name: {task_data.get('group_name', 'None')}")
            
            # 添加群组名称到task_data，用于文件组织
            if 'group_name' not in task_data:
                # 从task_data中获取群组信息，避免访问已脱离会话的关联对象
                try:
                    # 使用短暂的数据库会话获取群组信息
                    async with task_db_manager.get_task_session(task_id, "get_group_info") as db:
                        from ..models.telegram import TelegramGroup
                        group = db.query(TelegramGroup).filter(TelegramGroup.id == task_data.get('group_id')).first()
                        if group:
                            task_data['group_name'] = group.title
                        else:
                            task_data['group_name'] = 'Unknown_Group'
                except Exception as e:
                    logger.warning(f"任务{task_id}: 获取群组信息失败，使用默认名称: {e}")
                    task_data['group_name'] = 'Unknown_Group'
            
            # 使用文件组织服务整理文件
            success, organized_path, error_msg = self.file_organizer.organize_downloaded_file(
                source_path=file_path,
                message=message,
                task_data=task_data
            )
            
            if success:
                # 记录整理后的路径，供后续创建下载记录使用
                self._last_organized_path = organized_path
                
                if organized_path != file_path:
                    logger.info(f"任务{task_id}: 文件已整理到 {organized_path}")
                    await self._log_task_event(task_id, "INFO", f"文件已整理: {os.path.basename(organized_path)}")
                else:
                    logger.info(f"任务{task_id}: 文件已在正确位置 {organized_path}")
                
                # 记录组织统计信息
                if hasattr(self, '_organization_stats'):
                    self._organization_stats['organized_files'] = self._organization_stats.get('organized_files', 0) + 1
                else:
                    self._organization_stats = {'organized_files': 1}
                
                return True
            else:
                logger.error(f"任务{task_id}: 文件整理失败 - {error_msg}")
                await self._log_task_event(task_id, "ERROR", f"文件整理失败: {error_msg}")
                return False
                
        except Exception as e:
            error_msg = f"整理文件时发生异常: {str(e)}"
            logger.error(f"任务{task_id}: {error_msg}")
            await self._log_task_event(task_id, "ERROR", error_msg)
            return False

    async def _create_download_record(self, 
                                     message: 'TelegramMessage', 
                                     task_data: dict, 
                                     file_path: str, 
                                     task_id: int) -> bool:
        """
        为下载的文件创建下载记录
        
        Args:
            message: 消息对象
            task_data: 任务数据
            file_path: 文件路径
            task_id: 任务ID
        
        Returns:
            创建是否成功
        """
        try:
            from ..models.rule import DownloadRecord
            from datetime import datetime, timezone
            
            # 使用短时间数据库会话创建记录
            async with task_db_manager.get_task_session(task_id, "create_record") as db:
                # 检查记录是否已存在（避免重复创建）
                existing_record = db.query(DownloadRecord).filter(
                    DownloadRecord.task_id == task_data['task_id'],
                    DownloadRecord.message_id == message.message_id
                ).first()
                
                if existing_record:
                    # 更新现有记录的路径
                    existing_record.local_file_path = file_path
                    logger.debug(f"任务{task_id}: 更新现有下载记录 {existing_record.id}")
                else:
                    # 创建新的下载记录
                    file_stat = os.stat(file_path) if os.path.exists(file_path) else None
                    
                    record = DownloadRecord(
                        task_id=task_data['task_id'],
                        file_name=os.path.basename(file_path),
                        local_file_path=file_path,
                        file_size=file_stat.st_size if file_stat else None,
                        file_type=message.media_type,
                        message_id=message.message_id,
                        sender_id=getattr(message, 'sender_id', None),
                        sender_name=getattr(message, 'sender_name', None),
                        message_date=getattr(message, 'date', None),
                        message_text=getattr(message, 'text', None),
                        download_status="completed",
                        download_progress=100,
                        download_started_at=datetime.now(timezone.utc),
                        download_completed_at=datetime.now(timezone.utc)
                    )
                    
                    db.add(record)
                    logger.debug(f"任务{task_id}: 创建新下载记录 {message.message_id}")
                
                db.commit()
                return True
                
        except Exception as e:
            logger.error(f"任务{task_id}: 创建下载记录失败 - {str(e)}")
            await self._log_task_event(task_id, "WARNING", f"创建下载记录失败: {str(e)}")
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
            with optimized_db_session(max_retries=10) as db:
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
    
    async def _log_download_progress(self, task_id: int, message_id: int, current: int, total: int, progress_percent: float = None):
        """记录下载进度（优化：减少数据库写入频率）"""
        if total > 0:
            # 使用提供的进度百分比，或者自己计算
            if progress_percent is not None:
                progress = int(progress_percent)
            else:
                progress = int(current / total * 100)
            
            # 只在特定进度节点记录日志，避免频繁数据库写入导致锁定
            # 记录：0%, 25%, 50%, 75%, 100% 和每10%的整数进度
            if progress == 0 or progress == 100 or progress % 25 == 0 or progress % 10 == 0:
                await self._log_task_event(
                    task_id, 
                    "DEBUG", 
                    f"消息 {message_id} 下载进度: {progress}%",
                    {"message_id": message_id, "current": current, "total": total, "progress_percent": progress_percent}
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