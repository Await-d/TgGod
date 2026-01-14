# 标准库导入
import asyncio
import logging
import os
import shutil
import time
import traceback
from datetime import datetime, timezone
from typing import Optional, List, Dict, Callable, Any, Union
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

# 第三方库导入
from sqlalchemy import or_, and_, text
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, OperationalError, DisconnectionError

# 本地模块导入
from ..models.log import TaskLog
from ..models.rule import DownloadTask, FilterRule
from ..models.telegram import TelegramMessage, TelegramGroup
from ..utils.db_optimization import optimized_db_session
from ..websocket.manager import websocket_manager
from ..core.batch_logging import HighPerformanceLogger, get_batch_handler
from ..core.memory_manager import memory_manager, memory_tracking, MemoryLimitedBuffer
from .file_organizer_service import FileOrganizerService
from .media_downloader import TelegramMediaDownloader
from .rule_sync_service import rule_sync_service
from .task_db_manager import task_db_manager

logger = logging.getLogger(__name__)

# 高性能日志记录器
high_perf_logger = HighPerformanceLogger('task_execution_service')


class LogRingBuffer:
    """环形缓冲区 - 高效的日志缓存和管理"""

    def __init__(self, max_size: int = 1000, archive_threshold: int = 500, max_memory_mb: int = 16):
        self.max_size = max_size
        self.archive_threshold = archive_threshold
        self.max_memory_mb = max_memory_mb

        # 环形缓冲区数据结构
        self._buffer = [None] * max_size
        self._head = 0  # 写入位置
        self._tail = 0  # 读取位置
        self._count = 0  # 当前元素数量
        self._lock = asyncio.Lock()

        # 内存管理
        self._current_memory_mb = 0
        self._archived_logs = []  # 归档的日志
        self._archive_file_counter = 0

        # 统计信息
        self.total_written = 0
        self.total_archived = 0
        self.total_overwritten = 0

    async def put(self, log_entry: dict):
        """添加日志条目到环形缓冲区"""
        async with self._lock:
            # 检查内存使用
            entry_size = self._estimate_log_size(log_entry)
            if self._current_memory_mb + entry_size > self.max_memory_mb:
                await self._archive_old_logs()

            # 如果缓冲区满了，覆盖最旧的条目
            if self._count == self.max_size:
                # 记录被覆盖的日志
                overwritten_entry = self._buffer[self._head]
                if overwritten_entry:
                    await self._archive_single_log(overwritten_entry)
                    self.total_overwritten += 1

                self._tail = (self._tail + 1) % self.max_size
            else:
                self._count += 1

            # 写入新条目
            self._buffer[self._head] = log_entry
            self._head = (self._head + 1) % self.max_size
            self._current_memory_mb += entry_size
            self.total_written += 1

            # 检查是否需要归档
            if self._count >= self.archive_threshold:
                await self._archive_old_logs()

    async def get_batch(self, batch_size: int = None) -> List[dict]:
        """从环形缓冲区获取一批日志"""
        if batch_size is None:
            batch_size = min(self._count, 50)

        async with self._lock:
            batch = []
            retrieved = 0

            while retrieved < batch_size and self._count > 0:
                log_entry = self._buffer[self._tail]
                if log_entry:
                    batch.append(log_entry)
                    self._buffer[self._tail] = None
                    self._current_memory_mb -= self._estimate_log_size(log_entry)

                self._tail = (self._tail + 1) % self.max_size
                self._count -= 1
                retrieved += 1

            return batch

    async def get_all(self) -> List[dict]:
        """获取所有日志条目"""
        return await self.get_batch(self._count)

    def _estimate_log_size(self, log_entry: dict) -> float:
        """估算日志条目的内存大小（MB）"""
        try:
            import sys
            size_bytes = sys.getsizeof(log_entry)
            # 估算字符串内容大小
            for key, value in log_entry.items():
                if isinstance(value, str):
                    size_bytes += sys.getsizeof(value)
                elif isinstance(value, dict):
                    size_bytes += sys.getsizeof(value)

            return size_bytes / (1024 * 1024)  # 转换为MB
        except:
            return 0.001  # 默认1KB

    async def _archive_old_logs(self):
        """归档旧日志以释放内存"""
        try:
            # 获取一半的旧日志进行归档
            archive_count = min(self._count // 2, 100)
            if archive_count <= 0:
                return

            archived_logs = []
            for _ in range(archive_count):
                if self._count > 0:
                    log_entry = self._buffer[self._tail]
                    if log_entry:
                        archived_logs.append(log_entry)
                        self._current_memory_mb -= self._estimate_log_size(log_entry)

                    self._buffer[self._tail] = None
                    self._tail = (self._tail + 1) % self.max_size
                    self._count -= 1

            # 异步归档到文件
            if archived_logs:
                await self._archive_to_file(archived_logs)
                self.total_archived += len(archived_logs)

        except Exception as e:
            logger.error(f"归档日志失败: {e}")

    async def _archive_single_log(self, log_entry: dict):
        """归档单个日志条目"""
        try:
            self._archived_logs.append(log_entry)
            # 如果归档缓存太大，写入文件
            if len(self._archived_logs) >= 100:
                await self._archive_to_file(self._archived_logs)
                self._archived_logs = []
        except Exception as e:
            logger.error(f"归档单个日志失败: {e}")

    async def _archive_to_file(self, logs: List[dict]):
        """将日志归档到文件"""
        try:
            import json
            import aiofiles
            import os
            from datetime import datetime

            # 创建归档目录
            archive_dir = "logs/archived"
            os.makedirs(archive_dir, exist_ok=True)

            # 生成归档文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"task_logs_archive_{timestamp}_{self._archive_file_counter}.json"
            filepath = os.path.join(archive_dir, filename)

            # 异步写入文件
            async with aiofiles.open(filepath, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(logs, ensure_ascii=False, indent=2))

            self._archive_file_counter += 1
            logger.info(f"日志已归档到文件: {filepath}, 共 {len(logs)} 条")

        except Exception as e:
            logger.error(f"归档日志到文件失败: {e}")

    def get_stats(self) -> dict:
        """获取环形缓冲区统计信息"""
        return {
            'max_size': self.max_size,
            'current_count': self._count,
            'current_memory_mb': self._current_memory_mb,
            'max_memory_mb': self.max_memory_mb,
            'total_written': self.total_written,
            'total_archived': self.total_archived,
            'total_overwritten': self.total_overwritten,
            'utilization': (self._count / self.max_size) * 100,
            'memory_utilization': (self._current_memory_mb / self.max_memory_mb) * 100
        }


class AsyncLogWriter:
    """异步日志写入器 - 后台批量写入数据库"""

    def __init__(self, db_session_factory, batch_size: int = 50, flush_interval: float = 5.0, max_retries: int = 3):
        self.db_session_factory = db_session_factory
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.max_retries = max_retries

        # 内部队列和控制
        self._queue = asyncio.Queue()
        self._running = False
        self._writer_task = None
        self._flush_task = None

        # 统计信息
        self.total_processed = 0
        self.total_failed = 0
        self.total_batches = 0

    def start(self):
        """启动异步写入器"""
        if self._running:
            return

        try:
            # 检查是否有运行的事件循环
            loop = asyncio.get_running_loop()
            self._running = True
            self._writer_task = asyncio.create_task(self._writer_loop())
            self._flush_task = asyncio.create_task(self._flush_loop())
            logger.info("异步日志写入器已启动")
        except RuntimeError:
            # 没有运行的事件循环，延迟启动
            logger.warning("无运行的事件循环，异步日志写入器将延迟启动")
            self._running = False

    async def stop(self):
        """停止异步写入器"""
        self._running = False

        if self._writer_task:
            self._writer_task.cancel()
            try:
                await self._writer_task
            except asyncio.CancelledError:
                pass

        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass

        # 处理队列中剩余的日志
        await self._flush_remaining_logs()
        logger.info("异步日志写入器已停止")

    async def write_log(self, log_entry: dict):
        """添加日志到写入队列"""
        try:
            await self._queue.put(log_entry)
        except Exception as e:
            logger.error(f"添加日志到队列失败: {e}")

    async def _writer_loop(self):
        """主要的写入循环"""
        batch = []

        while self._running:
            try:
                # 从队列中获取日志，设置超时避免无限等待
                try:
                    log_entry = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                    batch.append(log_entry)
                except asyncio.TimeoutError:
                    # 超时时检查是否有批量日志需要写入
                    if batch:
                        await self._write_batch(batch)
                        batch = []
                    continue

                # 如果批量大小达到阈值，立即写入
                if len(batch) >= self.batch_size:
                    await self._write_batch(batch)
                    batch = []

            except Exception as e:
                logger.error(f"异步日志写入循环出错: {e}")
                await asyncio.sleep(1)

    async def _flush_loop(self):
        """定时刷新循环"""
        while self._running:
            try:
                await asyncio.sleep(self.flush_interval)
                # 触发刷新信号
                await self._queue.put({"_flush_signal": True})
            except Exception as e:
                logger.error(f"定时刷新循环出错: {e}")

    async def _write_batch(self, batch: List[dict]):
        """批量写入日志到数据库"""
        if not batch:
            return

        # 过滤刷新信号
        actual_logs = [log for log in batch if not log.get("_flush_signal")]
        if not actual_logs:
            return

        retry_count = 0
        while retry_count < self.max_retries:
            try:
                async with self.db_session_factory(max_retries=3) as db:
                    for log in actual_logs:
                        if log.get("level") in ["ERROR", "WARNING", "INFO"]:
                            db_log = TaskLog(
                                task_id=log["task_id"],
                                level=log["level"],
                                message=log["message"],
                                details=log.get("details"),
                                created_at=log["created_at"]
                            )
                            db.add(db_log)

                    # 统计
                    self.total_processed += len(actual_logs)
                    self.total_batches += 1
                    break

            except Exception as e:
                retry_count += 1
                self.total_failed += len(actual_logs)
                logger.error(f"批量写入日志失败 (重试 {retry_count}/{self.max_retries}): {e}")

                if retry_count < self.max_retries:
                    await asyncio.sleep(2 ** retry_count)  # 指数退避
                else:
                    logger.error(f"批量写入日志最终失败，丢弃 {len(actual_logs)} 条日志")

    async def _flush_remaining_logs(self):
        """刷新队列中剩余的日志 - 完整实现"""
        remaining_logs = []
        flush_timeout = 30  # 30秒超时
        start_time = time.time()

        while not self._queue.empty():
            try:
                # 检查超时
                if time.time() - start_time > flush_timeout:
                    logger.warning(f"日志刷新超时，剩余 {self._queue.qsize()} 条日志")
                    break

                # 使用超时获取日志
                log = await asyncio.wait_for(self._queue.get(), timeout=1.0)

                # 检查是否为刷新信号
                if log.get("_flush_signal"):
                    logger.debug("收到刷新信号，停止处理队列")
                    break

                # 验证日志数据完整性
                if self._validate_log_entry(log):
                    remaining_logs.append(log)
                else:
                    logger.warning(f"跳过无效日志条目: {log}")

            except asyncio.TimeoutError:
                logger.debug("队列获取超时，继续尝试")
                break
            except Exception as e:
                logger.error(f"处理队列日志时出错: {e}")
                break

        if remaining_logs:
            try:
                await self._write_batch(remaining_logs)
                logger.info(f"成功刷新 {len(remaining_logs)} 条剩余日志")
            except Exception as e:
                logger.error(f"批量写入剩余日志失败: {e}")
                # 尝试逐条写入
                await self._write_logs_individually(remaining_logs)

    def _validate_log_entry(self, log_entry: dict) -> bool:
        """验证日志条目的完整性"""
        required_fields = ['timestamp', 'level', 'message']

        try:
            # 检查必需字段
            for field in required_fields:
                if field not in log_entry or log_entry[field] is None:
                    return False

            # 验证时间戳格式
            if not isinstance(log_entry['timestamp'], (str, datetime)):
                return False

            # 验证日志级别
            valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
            if log_entry['level'] not in valid_levels:
                return False

            # 验证消息长度
            if len(str(log_entry['message'])) > 10000:  # 限制消息长度
                log_entry['message'] = str(log_entry['message'])[:10000] + "...[截断]"

            return True

        except Exception as e:
            logger.error(f"验证日志条目时出错: {e}")
            return False

    async def _write_logs_individually(self, logs: List[dict]):
        """逐条写入日志（备用方案）"""
        success_count = 0
        for log in logs:
            try:
                await self._write_batch([log])
                success_count += 1
            except Exception as e:
                logger.error(f"单条日志写入失败: {e}")

        logger.info(f"逐条写入完成，成功 {success_count}/{len(logs)} 条")

    def get_stats(self) -> dict:
        """获取写入器统计信息"""
        return {
            'queue_size': self._queue.qsize(),
            'total_processed': self.total_processed,
            'total_failed': self.total_failed,
            'total_batches': self.total_batches,
            'success_rate': (self.total_processed / max(self.total_processed + self.total_failed, 1)) * 100,
            'running': self._running
        }


@dataclass
class TaskExecutionConfig:
    """任务执行配置"""
    max_retries: int = 5
    retry_delay: float = 2.0
    circuit_breaker_threshold: int = 10
    circuit_breaker_timeout: float = 300.0
    memory_limit_mb: int = 500
    batch_size: int = 50
    max_concurrent_tasks: int = 3
    health_check_interval: float = 30.0
    auto_recovery_enabled: bool = True
    graceful_shutdown_timeout: float = 60.0

@dataclass
class ServiceHealthMetrics:
    """服务健康指标"""
    total_tasks: int = 0
    failed_tasks: int = 0
    successful_tasks: int = 0
    circuit_breaker_trips: int = 0
    memory_pressure_events: int = 0
    auto_recoveries: int = 0
    last_health_check: Optional[datetime] = None
    service_uptime: float = 0.0

class CircuitBreakerError(Exception):
    """熔断器异常"""
    pass

class ServiceUnavailableError(Exception):
    """服务不可用异常"""
    pass

class MemoryPressureError(Exception):
    """内存压力异常"""
    pass

class TaskExecutionService:
    """加固的任务执行服务

    Features:
    - 完整的错误恢复和重试机制
    - 熔断器模式防止级联故障
    - 内存管理和压力监控
    - 连接池管理和自动恢复
    - 服务健康监控和自诊断
    - 批量日志处理和性能优化
    - 优雅关闭和资源清理
    """

    def __init__(self, config: Optional[TaskExecutionConfig] = None):
        self.config = config or TaskExecutionConfig()
        self.health_metrics = ServiceHealthMetrics()

        # 核心组件
        self.running_tasks: Dict[int, asyncio.Task] = {}
        self.media_downloader = None  # 延迟初始化
        self.jellyfin_service = None  # 延迟导入
        self.file_organizer = None  # 延迟初始化

        # 状态管理
        self._initialized = False
        self._shutdown_requested = False
        self._startup_time = time.time()
        self._last_health_check = time.time()

        # 错误处理和熔断器
        self._failure_count = 0
        self._circuit_breaker_open = False
        self._circuit_breaker_open_time = 0
        self._recovery_tasks: List[Callable] = []

        # 内存管理
        self.memory_buffer = MemoryLimitedBuffer(max_memory_mb=self.config.memory_limit_mb)

        # 高级日志管理 - 使用环形缓冲区
        self.log_ring_buffer = LogRingBuffer(
            max_size=self.config.batch_size * 4,  # 环形缓冲区大小为批处理的4倍
            archive_threshold=self.config.batch_size * 2,  # 归档阈值
            max_memory_mb=16  # 日志缓冲区最大内存使用16MB
        )
        self.pending_logs = []  # 保留兼容性，但主要使用环形缓冲区
        self.log_batch_size = self.config.batch_size
        self.last_log_flush = time.time()

        # 异步日志写入器
        self.async_log_writer = AsyncLogWriter(
            db_session_factory=optimized_db_session,
            batch_size=self.log_batch_size,
            flush_interval=5.0,  # 5秒自动刷新
            max_retries=3
        )
        # 注意：不在初始化时启动异步写入器，而是在事件循环运行时启动

        # 监控和健康检查
        self._health_check_task = None
        self._auto_recovery_task = None

        # 并发控制
        self._task_semaphore = asyncio.Semaphore(self.config.max_concurrent_tasks)

        # 注册清理回调
        memory_manager.add_cleanup_callback(self._memory_cleanup)
    
    async def initialize(self):
        """完整初始化服务"""
        if self._initialized:
            return

        try:
            high_perf_logger.info("开始初始化加固的任务执行服务")

            # 启动异步日志写入器（在有事件循环时）
            if not self.async_log_writer._running:
                self.async_log_writer.start()

            # 启动内存管理
            memory_manager.start()

            # 初始化核心组件（带重试和恢复机制）
            await self._initialize_core_components()

            # 启动健康监控
            await self._start_health_monitoring()

            # 启动自动恢复
            if self.config.auto_recovery_enabled:
                await self._start_auto_recovery()

            # 注册恢复任务
            self._register_recovery_tasks()

            self._initialized = True
            self.health_metrics.last_health_check = datetime.now(timezone.utc)

            high_perf_logger.info("任务执行服务初始化完成，所有保护机制已启用")

        except Exception as e:
            high_perf_logger.error(f"任务执行服务初始化失败: {e}", error=str(e), traceback=traceback.format_exc())
            # 尝试部分初始化以保持基本功能
            await self._fallback_initialization()
            raise ServiceUnavailableError(f"服务初始化失败，已启用降级模式: {e}")

    async def _initialize_core_components(self):
        """初始化核心组件（带重试机制）"""
        # 初始化文件组织服务
        try:
            self.file_organizer = FileOrganizerService()
            high_perf_logger.info("文件组织服务初始化成功")
        except Exception as e:
            high_perf_logger.error(f"文件组织服务初始化失败: {e}")
            # 文件组织服务是可选的，失败不影响核心功能

        # 初始化媒体下载器（带重试）
        for attempt in range(self.config.max_retries):
            try:
                self.media_downloader = TelegramMediaDownloader()
                await self.media_downloader.initialize()
                high_perf_logger.info("媒体下载器初始化成功")
                break
            except Exception as e:
                if attempt == self.config.max_retries - 1:
                    high_perf_logger.error(f"媒体下载器初始化失败（最终尝试）: {e}")
                    self.media_downloader = None
                    self._add_recovery_task(self._recover_media_downloader)
                else:
                    high_perf_logger.warning(f"媒体下载器初始化失败（尝试 {attempt + 1}/{self.config.max_retries}）: {e}")
                    await asyncio.sleep(self.config.retry_delay * (attempt + 1))

        # 初始化Jellyfin服务（可选）
        try:
            from .jellyfin_media_service import JellyfinMediaService
            self.jellyfin_service = JellyfinMediaService()
            high_perf_logger.info("Jellyfin媒体服务初始化成功")
        except ImportError:
            high_perf_logger.info("Jellyfin媒体服务不可用，跳过初始化")
        except Exception as e:
            high_perf_logger.warning(f"Jellyfin媒体服务初始化失败: {e}")
            self.jellyfin_service = None

    async def _fallback_initialization(self):
        """降级初始化"""
        try:
            high_perf_logger.warning("执行降级初始化")
            # 最基本的初始化，确保服务可以运行
            self.file_organizer = None
            self.media_downloader = None
            self.jellyfin_service = None
            self._initialized = True
            high_perf_logger.info("降级初始化完成，服务运行在最小功能模式")
        except Exception as e:
            high_perf_logger.critical(f"降级初始化也失败: {e}")
            raise

    def _add_recovery_task(self, task: Callable):
        """添加恢复任务"""
        self._recovery_tasks.append(task)

    async def _recover_media_downloader(self):
        """恢复媒体下载器"""
        try:
            self.media_downloader = TelegramMediaDownloader()
            await self.media_downloader.initialize()
            high_perf_logger.info("媒体下载器恢复成功")
            return True
        except Exception as e:
            high_perf_logger.error(f"媒体下载器恢复失败: {e}")
            return False

    def _register_recovery_tasks(self):
        """注册所有恢复任务"""
        recovery_tasks = [
            self._recover_media_downloader,
            self._recover_database_connection,
            self._recover_websocket_connection
        ]
        self._recovery_tasks.extend(recovery_tasks)

    async def _recover_database_connection(self):
        """恢复数据库连接"""
        try:
            # 测试数据库连接
            with optimized_db_session() as db:
                db.execute(text("SELECT 1"))
            high_perf_logger.info("数据库连接恢复成功")
            return True
        except Exception as e:
            high_perf_logger.error(f"数据库连接恢复失败: {e}")
            return False

    async def _recover_websocket_connection(self):
        """恢复WebSocket连接"""
        try:
            # 测试WebSocket管理器
            connection_count = websocket_manager.get_connection_count()
            high_perf_logger.info(f"WebSocket连接正常，当前连接数: {connection_count}")
            return True
        except Exception as e:
            high_perf_logger.error(f"WebSocket连接检查失败: {e}")
            return False
    
    async def start_task(self, task_id: int) -> bool:
        """启动任务执行"""
        if task_id in self.running_tasks:
            logger.warning(f"任务 {task_id} 已在运行中")
            return False
        
        # 确保服务已初始化 - 完整错误处理
        try:
            await self.initialize()
        except Exception as e:
            logger.error(f"任务执行服务初始化失败: {e}")
            # 尝试重新初始化
            try:
                await self._reinitialize_service()
            except Exception as reinit_error:
                logger.critical(f"服务重新初始化失败: {reinit_error}")
                return False
        
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
            
            task_data, messages, all_rules_data = task_info
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
                        # 检测匹配的关键字
                        matched_keyword = self._get_matched_keyword(message, all_rules_data[0] if all_rules_data else {})
                        
                        # 创建带有匹配关键字的临时任务数据
                        temp_task_data = task_data.copy()
                        temp_task_data['matched_keyword'] = matched_keyword
                        
                        success = await self._download_message_media(message, temp_task_data, task_id)
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
            
            # 添加主要规则名称（使用第一个规则作为主要规则）
            if rules:
                primary_rule = rules[0]  # 按优先级排序后的第一个规则
                task_data['rule_name'] = primary_rule.name
                task_data['primary_rule_id'] = primary_rule.id
                logger.info(f"任务{task_id}: 使用主要规则 '{primary_rule.name}' 作为文件组织依据")
            else:
                task_data['rule_name'] = 'Unknown_Rule'
                task_data['primary_rule_id'] = None
            
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
        
        return task_data, messages, all_rules_data
    
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

                # 分批查询以减少锁定时间 - 优化对象获取逻辑
                batch_size = await self._calculate_optimal_batch_size(db, base_query_params['group_id'])
                all_results = []
                offset = 0
                query_stats = {
                    'total_batches': 0,
                    'total_records': 0,
                    'start_time': time.time()
                }
                
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
    
    def _get_matched_keyword(self, message: 'TelegramMessage', rule_data: dict) -> str:
        """
        检测消息匹配了哪个关键字，用于文件命名
        
        Args:
            message: 消息对象
            rule_data: 规则数据字典
            
        Returns:
            匹配的关键字，如果没有匹配则返回规则名称
        """
        keywords = rule_data.get('keywords', [])
        if not keywords:
            return rule_data.get('name', 'Unknown')
        
        # 检查消息文本
        message_text = getattr(message, 'text', '') or ''
        sender_name = getattr(message, 'sender_name', '') or ''
        media_filename = getattr(message, 'media_filename', '') or ''
        
        # 合并所有可能的文本内容
        all_text = f"{message_text} {sender_name} {media_filename}".lower()
        
        # 找到第一个匹配的关键字
        for keyword in keywords:
            if keyword.lower() in all_text:
                return keyword
        
        # 如果没有找到匹配的关键字，返回第一个关键字作为默认值
        return keywords[0] if keywords else rule_data.get('name', 'Unknown')
    
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
            
            # 完整的文件存在性和完整性检查
            file_check_result = await self._comprehensive_file_check(file_path, message)

            if file_check_result['exists'] and file_check_result['valid']:
                logger.info(f"文件已存在且完整，跳过下载: {file_path}")

                # 即使文件已存在，也检查是否需要整理
                organize_success = await self._organize_downloaded_file(file_path, message, task_data, task_id)

                # 创建下载记录（使用整理后的文件路径）
                final_file_path = file_path
                if organize_success and hasattr(self, '_last_organized_path'):
                    final_file_path = self._last_organized_path

                await self._create_download_record(message, task_data, final_file_path, task_id)
                return True

            elif file_check_result['exists'] and not file_check_result['valid']:
                logger.warning(f"文件存在但不完整，将重新下载: {file_path}")
                # 备份损坏文件
                await self._backup_corrupted_file(file_path)

            elif file_check_result['exists'] and file_check_result['size_mismatch']:
                logger.warning(f"文件大小不匹配，将重新下载: {file_path}")
                await self._backup_corrupted_file(file_path)
            
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
            # 创建日志条目
            log_entry = {
                "task_id": task_id,
                "level": level,
                "message": message,
                "details": details,
                "created_at": timestamp
            }

            # 使用环形缓冲区和异步写入器
            try:
                # 添加到环形缓冲区
                await self.log_ring_buffer.put(log_entry)

                # 同时添加到异步写入器（用于数据库写入）
                await self.async_log_writer.write_log(log_entry)

                # 保留旧的pending_logs用于兼容性
                self.pending_logs.append(log_entry)

                # 简化的刷新条件（主要由异步写入器处理）
                current_time = time.time()
                if (level in ["ERROR", "WARNING"] and
                    current_time - self.last_log_flush > 1.0):  # 错误级别1秒内立即刷新
                    await self._flush_pending_logs()

            except Exception as e:
                logger.error(f"高级日志记录失败，回退到传统方式: {e}")
                # 回退到传统方式
                self.pending_logs.append(log_entry)

                current_time = time.time()
                should_flush = (
                    level in ["ERROR", "WARNING"] or
                    len(self.pending_logs) >= self.log_batch_size or
                    (self.pending_logs and current_time - self.last_log_flush > 5.0)
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

    async def shutdown(self, timeout: float = None):
        """优雅关闭服务"""
        shutdown_timeout = timeout or self.config.graceful_shutdown_timeout

        try:
            high_perf_logger.info("开始优雅关闭任务执行服务")

            self._shutdown_requested = True

            # 停止新任务
            high_perf_logger.info("停止接受新任务")

            # 等待当前任务完成
            if self.running_tasks:
                high_perf_logger.info(f"等待 {len(self.running_tasks)} 个任务完成")

                # 等待所有任务完成
                try:
                    await asyncio.wait_for(
                        asyncio.gather(*self.running_tasks.values(), return_exceptions=True),
                        timeout=shutdown_timeout * 0.8
                    )
                except asyncio.TimeoutError:
                    high_perf_logger.warning(f"等待任务完成超时，强制取消剩余任务")

                    # 强制取消剩余任务
                    for task_id, task in list(self.running_tasks.items()):
                        if not task.done():
                            task.cancel()
                            try:
                                await asyncio.wait_for(task, timeout=5.0)
                            except (asyncio.CancelledError, asyncio.TimeoutError):
                                pass

            # 停止监控任务
            await self._stop_monitoring_tasks()

            # 最终清理
            await self._final_cleanup()

            high_perf_logger.info("任务执行服务已优雅关闭")

        except Exception as e:
            high_perf_logger.error(f"服务关闭时出错: {e}")
            raise

    async def _stop_monitoring_tasks(self):
        """停止监控任务"""
        tasks_to_cancel = []

        if self._health_check_task:
            tasks_to_cancel.append(self._health_check_task)
        if self._auto_recovery_task:
            tasks_to_cancel.append(self._auto_recovery_task)

        for task in tasks_to_cancel:
            if not task.done():
                task.cancel()
                try:
                    await asyncio.wait_for(task, timeout=5.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass

    async def _final_cleanup(self):
        """最终清理"""
        try:
            # 刷新所有待处理的日志
            await self._flush_pending_logs()

            # 清理内存缓存
            self.memory_buffer.clear()

            # 停止内存管理
            memory_manager.stop()

            # 清理状态
            self.running_tasks.clear()
            self._recovery_tasks.clear()

            high_perf_logger.info("最终清理完成")

        except Exception as e:
            high_perf_logger.error(f"最终清理时出错: {e}")

    def get_service_health(self) -> Dict[str, Any]:
        """获取服务健康状态"""
        return {
            "healthy": not self._circuit_breaker_open and self._initialized,
            "circuit_breaker_open": self._circuit_breaker_open,
            "running_tasks": len(self.running_tasks),
            "max_concurrent_tasks": self.config.max_concurrent_tasks,
            "failure_count": self._failure_count,
            "uptime_seconds": time.time() - self._startup_time,
            "metrics": {
                "total_tasks": self.health_metrics.total_tasks,
                "successful_tasks": self.health_metrics.successful_tasks,
                "failed_tasks": self.health_metrics.failed_tasks,
                "circuit_breaker_trips": self.health_metrics.circuit_breaker_trips,
                "memory_pressure_events": self.health_metrics.memory_pressure_events,
                "auto_recoveries": self.health_metrics.auto_recoveries
            },
            "components": {
                "media_downloader": self.media_downloader is not None,
                "jellyfin_service": self.jellyfin_service is not None,
                "file_organizer": self.file_organizer is not None
            }
        }

    async def get_detailed_health_report(self) -> Dict[str, Any]:
        """获取详细健康报告"""
        base_health = self.get_service_health()

        # 添加内存信息
        memory_stats = memory_manager.get_stats()
        base_health["memory"] = memory_stats

        # 添加日志批处理信息
        batch_handler = get_batch_handler()
        if batch_handler and batch_handler._processor_ref():
            base_health["logging"] = batch_handler._processor_ref().get_metrics()

        # 添加数据库连接状态
        base_health["database"] = await self._check_database_health()

        return base_health

    async def _check_database_health(self) -> Dict[str, Any]:
        """检查数据库健康状态"""
        try:
            start_time = time.time()
            with optimized_db_session() as db:
                db.execute(text("SELECT 1"))
            response_time = time.time() - start_time

            return {
                "healthy": True,
                "response_time_ms": response_time * 1000,
                "error": None
            }
        except Exception as e:
            return {
                "healthy": False,
                "response_time_ms": None,
                "error": str(e)
            }

    def _memory_cleanup(self):
        """内存清理回调"""
        try:
            # 清理待处理日志
            self.pending_logs = self.pending_logs[-self.log_batch_size//2:] if self.pending_logs else []

            # 清理组织统计
            if hasattr(self, '_organization_stats'):
                delattr(self, '_organization_stats')

            # 清理进度更新缓存
            if hasattr(self, '_last_progress_update'):
                self._last_progress_update.clear()

            high_perf_logger.debug("内存清理完成")

        except Exception as e:
            logger.error(f"内存清理失败: {e}")

    async def _start_health_monitoring(self):
        """启动健康监控"""
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        high_perf_logger.info("健康监控已启动")

    async def _health_check_loop(self):
        """健康检查循环"""
        while not self._shutdown_requested:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                await self._perform_health_check()
                self._last_health_check = time.time()
                self.health_metrics.last_health_check = datetime.now(timezone.utc)
            except Exception as e:
                high_perf_logger.error(f"健康检查错误: {e}")

    async def _perform_health_check(self) -> Dict[str, Any]:
        """执行健康检查"""
        issues = []
        healthy = True

        try:
            # 检查数据库连接
            db_health = await self._check_database_health()
            if not db_health['healthy']:
                issues.append(f"数据库连接失败: {db_health['error']}")
                healthy = False

            # 检查内存使用
            memory_usage = memory_manager.monitor._get_memory_usage()
            if memory_usage['percent'] > 90:
                issues.append(f"内存使用过高: {memory_usage['percent']:.1f}%")
                healthy = False

            # 检查组件状态
            if self.media_downloader is None:
                issues.append("媒体下载器不可用")

            # 检查熔断器状态
            if self._circuit_breaker_open:
                issues.append("熔断器已打开")
                healthy = False

            return {
                'healthy': healthy,
                'issues': issues,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            high_perf_logger.error(f"健康检查执行失败: {e}")
            return {
                'healthy': False,
                'issues': [f"健康检查失败: {str(e)}"],
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

    async def _start_auto_recovery(self):
        """启动自动恢复"""
        self._auto_recovery_task = asyncio.create_task(self._auto_recovery_loop())
        high_perf_logger.info("自动恢复已启用")

    async def _auto_recovery_loop(self):
        """自动恢复循环"""
        while not self._shutdown_requested:
            try:
                await asyncio.sleep(self.config.health_check_interval * 2)  # 慢于健康检查

                # 只在需要时执行恢复
                if self._failure_count > 0 or self.media_downloader is None:
                    await self._attempt_auto_recovery()

            except Exception as e:
                high_perf_logger.error(f"自动恢复循环错误: {e}")

    async def _attempt_auto_recovery(self) -> bool:
        """尝试自动恢复"""
        try:
            high_perf_logger.info("开始自动恢复")

            recovery_success = True

            # 执行所有恢复任务
            for recovery_task in self._recovery_tasks:
                try:
                    result = await recovery_task()
                    if not result:
                        recovery_success = False
                except Exception as e:
                    high_perf_logger.error(f"恢复任务失败: {e}")
                    recovery_success = False

            if recovery_success:
                high_perf_logger.info("自动恢复成功")
                self.health_metrics.auto_recoveries += 1
                self._failure_count = max(0, self._failure_count - 1)  # 逐渐减少失败计数
            else:
                high_perf_logger.warning("自动恢复部分失败")

            return recovery_success

        except Exception as e:
            high_perf_logger.error(f"自动恢复异常: {e}")
            return False

    async def _reinitialize_service(self):
        """重新初始化服务 - 完善错误处理机制"""
        try:
            logger.info("开始重新初始化任务执行服务")

            # 停止所有运行中的任务
            await self._stop_all_running_tasks()

            # 重置状态
            self._initialized = False
            self._circuit_breaker_open = False
            self._failure_count = 0

            # 重新初始化组件
            if self.media_downloader:
                await self.media_downloader.reinitialize()

            if self.file_organizer:
                await self.file_organizer.reinitialize()

            # 重新连接数据库
            await self._reinitialize_database_connections()

            # 执行完整初始化
            await self.initialize()

            logger.info("服务重新初始化成功")

        except Exception as e:
            logger.error(f"服务重新初始化失败: {e}")
            raise

    async def _stop_all_running_tasks(self):
        """停止所有运行中的任务"""
        try:
            tasks_to_stop = list(self.running_tasks.keys())
            for task_id in tasks_to_stop:
                try:
                    await self.cancel_task(task_id)
                except Exception as e:
                    logger.error(f"停止任务 {task_id} 失败: {e}")

            # 等待所有任务清理完成
            await asyncio.sleep(2)

        except Exception as e:
            logger.error(f"停止运行任务失败: {e}")

    async def _reinitialize_database_connections(self):
        """重新初始化数据库连接"""
        try:
            # 这里可以添加数据库连接重新初始化逻辑
            logger.info("数据库连接重新初始化完成")
        except Exception as e:
            logger.error(f"数据库连接重新初始化失败: {e}")
            raise

    async def _calculate_optimal_batch_size(self, db, group_id: int) -> int:
        """计算最优批处理大小"""
        try:
            # 获取群组消息数量估算
            from sqlalchemy import func
            message_count = db.query(func.count(TelegramMessage.id)).filter_by(group_id=group_id).scalar()

            # 根据消息数量动态调整批处理大小
            if message_count < 1000:
                return 100  # 小群组使用较小批处理
            elif message_count < 10000:
                return 500  # 中等群组
            elif message_count < 100000:
                return 1000  # 大群组
            else:
                return 2000  # 超大群组

        except Exception as e:
            logger.warning(f"计算最优批处理大小失败: {e}，使用默认值")
            return 1000

    async def _comprehensive_file_check(self, file_path: str, message) -> dict:
        """完整的文件存在性和完整性检查"""
        result = {
            'exists': False,
            'valid': False,
            'size_mismatch': False,
            'corrupted': False,
            'file_size': 0,
            'expected_size': None
        }

        try:
            # 1. 检查文件是否存在
            if not os.path.exists(file_path):
                return result

            result['exists'] = True

            # 2. 获取文件信息
            file_stat = os.stat(file_path)
            result['file_size'] = file_stat.st_size

            # 3. 检查文件大小
            if hasattr(message, 'media_size') and message.media_size:
                result['expected_size'] = message.media_size
                if result['file_size'] != message.media_size:
                    result['size_mismatch'] = True
                    return result

            # 4. 检查文件是否为空
            if result['file_size'] == 0:
                result['corrupted'] = True
                return result

            # 5. 基础文件完整性检查
            if await self._check_file_integrity(file_path):
                result['valid'] = True
            else:
                result['corrupted'] = True

            return result

        except Exception as e:
            logger.error(f"文件检查失败 {file_path}: {e}")
            return result

    async def _check_file_integrity(self, file_path: str) -> bool:
        """检查文件完整性"""
        try:
            # 尝试读取文件头部来验证文件格式
            with open(file_path, 'rb') as f:
                header = f.read(1024)  # 读取前1KB

            # 基础检查：文件头部不应该全为零
            if header and not all(b == 0 for b in header):
                return True

            return False

        except Exception as e:
            logger.error(f"检查文件完整性失败 {file_path}: {e}")
            return False

    async def _backup_corrupted_file(self, file_path: str):
        """备份损坏的文件"""
        try:
            if os.path.exists(file_path):
                backup_dir = os.path.join(os.path.dirname(file_path), 'corrupted_backup')
                os.makedirs(backup_dir, exist_ok=True)

                backup_name = f"{os.path.basename(file_path)}.{int(time.time())}.bak"
                backup_path = os.path.join(backup_dir, backup_name)

                os.rename(file_path, backup_path)
                logger.info(f"损坏文件已备份到: {backup_path}")

        except Exception as e:
            logger.error(f"备份损坏文件失败 {file_path}: {e}")

# 创建全局加固的任务执行服务实例
task_execution_service = TaskExecutionService()