"""
临时文件管理器 - 统一管理系统中的临时文件

特性：
1. 统一临时文件管理
2. 自动清理机制（基于时间、空间）
3. 文件锁机制防止冲突
4. 配额管理和监控
5. 生产级实现，确保可靠性
"""

import os
import shutil
import tempfile
import threading
import time
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from contextlib import contextmanager, asynccontextmanager
import hashlib
import weakref
import fcntl
import signal
import psutil
from concurrent.futures import ThreadPoolExecutor

from ..core.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class TempFileConfig:
    """临时文件配置"""
    base_path: Optional[str] = None
    max_size: int = 1024 * 1024 * 1024  # 1GB 默认最大大小
    max_age: int = 3600 * 24  # 24小时默认过期时间
    cleanup_interval: int = 300  # 5分钟清理间隔
    enable_compression: bool = False
    auto_cleanup: bool = True
    thread_safe: bool = True
    use_memory_mapping: bool = False


@dataclass
class TempFileInfo:
    """临时文件信息"""
    path: str
    size: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    purpose: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    locked: bool = False
    lock_process: Optional[int] = None
    ref_count: int = 0


class FileLockManager:
    """文件锁管理器"""

    def __init__(self):
        self._locks: Dict[str, threading.RLock] = {}
        self._file_locks: Dict[str, int] = {}  # 文件描述符
        self._lock = threading.RLock()

    @contextmanager
    def acquire_lock(self, file_path: str, exclusive: bool = True):
        """获取文件锁"""
        with self._lock:
            if file_path not in self._locks:
                self._locks[file_path] = threading.RLock()

        thread_lock = self._locks[file_path]

        with thread_lock:
            try:
                # 创建目录（如果不存在）
                os.makedirs(os.path.dirname(file_path), exist_ok=True)

                # 打开文件并获取文件锁
                fd = os.open(file_path, os.O_CREAT | os.O_WRONLY)

                lock_type = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
                fcntl.flock(fd, lock_type | fcntl.LOCK_NB)

                self._file_locks[file_path] = fd
                logger.debug(f"File lock acquired: {file_path}")

                yield file_path

            except (OSError, IOError) as e:
                logger.warning(f"Failed to acquire file lock for {file_path}: {e}")
                raise
            finally:
                # 释放文件锁
                if file_path in self._file_locks:
                    try:
                        os.close(self._file_locks[file_path])
                        del self._file_locks[file_path]
                        logger.debug(f"File lock released: {file_path}")
                    except OSError:
                        pass

    def is_locked(self, file_path: str) -> bool:
        """检查文件是否被锁定"""
        return file_path in self._file_locks


class TempFileManager:
    """
    临时文件管理器

    提供统一的临时文件管理，包括创建、清理、锁定等功能。
    """

    _instance = None
    _lock = threading.RLock()

    def __new__(cls, config: Optional[TempFileConfig] = None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config: Optional[TempFileConfig] = None):
        if hasattr(self, '_initialized'):
            return

        self.config = config or TempFileConfig()
        self._files: Dict[str, TempFileInfo] = {}
        self._lock = threading.RLock()
        self._cleanup_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()
        self._file_lock_manager = FileLockManager()
        self._weak_refs: weakref.WeakSet = weakref.WeakSet()
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="TempFileManager")

        # 设置基础路径
        if self.config.base_path:
            self.base_path = Path(self.config.base_path)
        else:
            self.base_path = Path(tempfile.gettempdir()) / "tggod_temp"

        # 确保基础目录存在
        self.base_path.mkdir(parents=True, exist_ok=True)

        # 启动清理线程
        if self.config.auto_cleanup:
            self._start_cleanup_thread()

        # 注册进程退出处理
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        self._initialized = True
        logger.info(f"TempFileManager initialized with base path: {self.base_path}")

    def _signal_handler(self, signum, frame):
        """处理进程退出信号"""
        logger.info(f"Received signal {signum}, cleaning up temp files...")
        self.cleanup_all()

    def _start_cleanup_thread(self):
        """启动清理线程"""
        if self._cleanup_thread is None or not self._cleanup_thread.is_alive():
            self._cleanup_thread = threading.Thread(
                target=self._cleanup_worker,
                name="TempFileCleanup",
                daemon=True
            )
            self._cleanup_thread.start()
            logger.info("Cleanup thread started")

    def _cleanup_worker(self):
        """清理工作线程"""
        while not self._shutdown_event.is_set():
            try:
                self._periodic_cleanup()

                # 等待下次清理
                self._shutdown_event.wait(self.config.cleanup_interval)

            except Exception as e:
                logger.error(f"Error in cleanup worker: {e}")
                time.sleep(60)  # 出错后等待1分钟再试

    def _periodic_cleanup(self):
        """定期清理过期文件"""
        current_time = datetime.now()
        files_to_remove = []
        total_size = 0

        with self._lock:
            for path, file_info in self._files.items():
                # 检查文件是否过期
                if (current_time - file_info.created_at).total_seconds() > self.config.max_age:
                    if not file_info.locked and file_info.ref_count == 0:
                        files_to_remove.append(path)
                        continue

                # 统计总大小
                if os.path.exists(path):
                    try:
                        file_info.size = os.path.getsize(path)
                        total_size += file_info.size
                    except OSError:
                        files_to_remove.append(path)

        # 删除过期文件
        for path in files_to_remove:
            self._remove_file_safe(path, "expired")

        # 检查总大小限制
        if total_size > self.config.max_size:
            self._cleanup_by_size(total_size - self.config.max_size)

        # 记录统计信息
        if files_to_remove:
            logger.info(f"Cleanup completed: {len(files_to_remove)} files removed, "
                       f"total size: {self._format_size(total_size)}")

    def _cleanup_by_size(self, bytes_to_free: int):
        """按大小清理文件（LRU策略）"""
        files_by_access = []

        with self._lock:
            for path, file_info in self._files.items():
                if not file_info.locked and file_info.ref_count == 0:
                    files_by_access.append((file_info.last_accessed, path, file_info.size))

        # 按最后访问时间排序
        files_by_access.sort()

        freed_bytes = 0
        for _, path, size in files_by_access:
            if freed_bytes >= bytes_to_free:
                break

            if self._remove_file_safe(path, "size_limit"):
                freed_bytes += size

        logger.info(f"Size-based cleanup: freed {self._format_size(freed_bytes)} bytes")

    def _remove_file_safe(self, path: str, reason: str = "cleanup") -> bool:
        """安全删除文件"""
        try:
            with self._lock:
                if path in self._files:
                    file_info = self._files[path]

                    # 检查是否被锁定或有引用
                    if file_info.locked or file_info.ref_count > 0:
                        return False

                    # 删除文件
                    if os.path.exists(path):
                        if os.path.isdir(path):
                            shutil.rmtree(path)
                        else:
                            os.remove(path)

                    # 从管理器中移除
                    del self._files[path]

                    logger.debug(f"File removed ({reason}): {path}")
                    return True

        except Exception as e:
            logger.error(f"Error removing file {path}: {e}")
            return False

        return False

    def create_temp_file(self,
                        suffix: str = "",
                        prefix: str = "tggod_",
                        purpose: str = "",
                        metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        创建临时文件

        Args:
            suffix: 文件后缀
            prefix: 文件前缀
            purpose: 文件用途描述
            metadata: 附加元数据

        Returns:
            临时文件路径
        """
        try:
            # 生成唯一文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = hashlib.md5(f"{timestamp}_{threading.current_thread().ident}".encode()).hexdigest()[:8]

            filename = f"{prefix}{timestamp}_{unique_id}{suffix}"
            temp_path = str(self.base_path / filename)

            # 创建文件信息
            file_info = TempFileInfo(
                path=temp_path,
                purpose=purpose,
                metadata=metadata or {}
            )

            with self._lock:
                self._files[temp_path] = file_info

            # 创建空文件
            Path(temp_path).touch()

            logger.debug(f"Temp file created: {temp_path} (purpose: {purpose})")
            return temp_path

        except Exception as e:
            logger.error(f"Error creating temp file: {e}")
            raise

    def create_temp_dir(self,
                       prefix: str = "tggod_dir_",
                       purpose: str = "",
                       metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        创建临时目录

        Args:
            prefix: 目录前缀
            purpose: 目录用途描述
            metadata: 附加元数据

        Returns:
            临时目录路径
        """
        try:
            # 生成唯一目录名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = hashlib.md5(f"{timestamp}_{threading.current_thread().ident}".encode()).hexdigest()[:8]

            dirname = f"{prefix}{timestamp}_{unique_id}"
            temp_path = str(self.base_path / dirname)

            # 创建目录信息
            file_info = TempFileInfo(
                path=temp_path,
                purpose=purpose,
                metadata=metadata or {}
            )

            with self._lock:
                self._files[temp_path] = file_info

            # 创建目录
            os.makedirs(temp_path, exist_ok=True)

            logger.debug(f"Temp directory created: {temp_path} (purpose: {purpose})")
            return temp_path

        except Exception as e:
            logger.error(f"Error creating temp directory: {e}")
            raise

    @contextmanager
    def temp_file(self, *args, **kwargs):
        """临时文件上下文管理器"""
        temp_path = None
        try:
            temp_path = self.create_temp_file(*args, **kwargs)
            yield temp_path
        finally:
            if temp_path:
                self.remove_file(temp_path)

    @contextmanager
    def temp_dir(self, *args, **kwargs):
        """临时目录上下文管理器"""
        temp_path = None
        try:
            temp_path = self.create_temp_dir(*args, **kwargs)
            yield temp_path
        finally:
            if temp_path:
                self.remove_file(temp_path)

    @contextmanager
    def lock_file(self, file_path: str, exclusive: bool = True):
        """文件锁上下文管理器"""
        with self._file_lock_manager.acquire_lock(file_path, exclusive):
            # 标记文件为锁定状态
            with self._lock:
                if file_path in self._files:
                    self._files[file_path].locked = True
                    self._files[file_path].lock_process = os.getpid()

            try:
                yield file_path
            finally:
                # 解除锁定状态
                with self._lock:
                    if file_path in self._files:
                        self._files[file_path].locked = False
                        self._files[file_path].lock_process = None

    def add_reference(self, file_path: str) -> None:
        """增加文件引用计数"""
        with self._lock:
            if file_path in self._files:
                self._files[file_path].ref_count += 1
                self._files[file_path].last_accessed = datetime.now()

    def remove_reference(self, file_path: str) -> None:
        """减少文件引用计数"""
        with self._lock:
            if file_path in self._files:
                self._files[file_path].ref_count = max(0, self._files[file_path].ref_count - 1)

    def remove_file(self, file_path: str) -> bool:
        """手动移除文件"""
        return self._remove_file_safe(file_path, "manual")

    def get_file_info(self, file_path: str) -> Optional[TempFileInfo]:
        """获取文件信息"""
        with self._lock:
            return self._files.get(file_path)

    def list_files(self, purpose: Optional[str] = None) -> List[TempFileInfo]:
        """列出所有临时文件"""
        with self._lock:
            files = list(self._files.values())

            if purpose:
                files = [f for f in files if f.purpose == purpose]

            return files

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            total_files = len(self._files)
            total_size = 0
            locked_files = 0

            for file_info in self._files.values():
                if os.path.exists(file_info.path):
                    try:
                        file_info.size = os.path.getsize(file_info.path)
                        total_size += file_info.size
                    except OSError:
                        pass

                if file_info.locked:
                    locked_files += 1

            # 系统磁盘信息
            disk_usage = shutil.disk_usage(self.base_path)

            return {
                "total_files": total_files,
                "total_size": total_size,
                "total_size_formatted": self._format_size(total_size),
                "locked_files": locked_files,
                "base_path": str(self.base_path),
                "disk_free": disk_usage.free,
                "disk_free_formatted": self._format_size(disk_usage.free),
                "disk_total": disk_usage.total,
                "disk_total_formatted": self._format_size(disk_usage.total),
                "config": {
                    "max_size": self.config.max_size,
                    "max_size_formatted": self._format_size(self.config.max_size),
                    "max_age_hours": self.config.max_age / 3600,
                    "cleanup_interval_minutes": self.config.cleanup_interval / 60,
                    "auto_cleanup": self.config.auto_cleanup
                }
            }

    def cleanup_all(self, force: bool = False) -> int:
        """清理所有临时文件"""
        removed_count = 0

        with self._lock:
            files_to_remove = []

            for path, file_info in self._files.items():
                if force or (not file_info.locked and file_info.ref_count == 0):
                    files_to_remove.append(path)

        for path in files_to_remove:
            if self._remove_file_safe(path, "cleanup_all"):
                removed_count += 1

        logger.info(f"Cleanup all: {removed_count} files removed")
        return removed_count

    def shutdown(self):
        """关闭管理器"""
        logger.info("Shutting down TempFileManager...")

        # 停止清理线程
        self._shutdown_event.set()
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=5)

        # 关闭线程池
        self._executor.shutdown(wait=True)

        # 清理所有文件
        self.cleanup_all(force=True)

        logger.info("TempFileManager shutdown completed")

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """格式化文件大小"""
        if size_bytes == 0:
            return "0 B"

        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        size = float(size_bytes)

        while size >= 1024.0 and i < len(size_names) - 1:
            size /= 1024.0
            i += 1

        return f"{size:.1f} {size_names[i]}"


# 全局实例
temp_file_manager = TempFileManager()


# 便捷函数
def create_temp_file(*args, **kwargs) -> str:
    """创建临时文件的便捷函数"""
    return temp_file_manager.create_temp_file(*args, **kwargs)


def create_temp_dir(*args, **kwargs) -> str:
    """创建临时目录的便捷函数"""
    return temp_file_manager.create_temp_dir(*args, **kwargs)


@contextmanager
def temp_file(*args, **kwargs):
    """临时文件上下文管理器便捷函数"""
    with temp_file_manager.temp_file(*args, **kwargs) as temp_path:
        yield temp_path


@contextmanager
def temp_dir(*args, **kwargs):
    """临时目录上下文管理器便捷函数"""
    with temp_file_manager.temp_dir(*args, **kwargs) as temp_path:
        yield temp_path


@contextmanager
def lock_file(file_path: str, exclusive: bool = True):
    """文件锁上下文管理器便捷函数"""
    with temp_file_manager.lock_file(file_path, exclusive) as locked_path:
        yield locked_path


# 导出主要接口
__all__ = [
    'TempFileManager',
    'TempFileConfig',
    'TempFileInfo',
    'FileLockManager',
    'temp_file_manager',
    'create_temp_file',
    'create_temp_dir',
    'temp_file',
    'temp_dir',
    'lock_file'
]