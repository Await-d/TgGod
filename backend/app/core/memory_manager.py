"""
内存管理模块

提供内存优化、监控和自动清理功能
"""

import gc
import logging
import os
import psutil
import threading
import time
import weakref
from collections import defaultdict
from contextlib import contextmanager
from functools import wraps
from typing import Any, Dict, List, Optional, Callable, Generator
import asyncio

logger = logging.getLogger(__name__)


class MemoryTracker:
    """内存使用跟踪器"""

    def __init__(self):
        self.tracked_objects = weakref.WeakSet()
        self.memory_snapshots = []
        self.peak_usage = 0
        self.allocation_history = defaultdict(list)

    def track_object(self, obj: Any, name: str = None):
        """跟踪对象内存使用"""
        self.tracked_objects.add(obj)
        size = self._get_object_size(obj)
        self.allocation_history[name or type(obj).__name__].append({
            'timestamp': time.time(),
            'size': size,
            'action': 'allocate'
        })

    def untrack_object(self, obj: Any, name: str = None):
        """停止跟踪对象"""
        try:
            self.tracked_objects.discard(obj)
            self.allocation_history[name or type(obj).__name__].append({
                'timestamp': time.time(),
                'size': 0,
                'action': 'deallocate'
            })
        except:
            pass

    def _get_object_size(self, obj: Any) -> int:
        """获取对象内存大小"""
        try:
            import sys
            return sys.getsizeof(obj)
        except:
            return 0

    def get_memory_usage(self) -> Dict[str, Any]:
        """获取当前内存使用情况"""
        process = psutil.Process()
        memory_info = process.memory_info()

        return {
            'rss': memory_info.rss,  # 物理内存
            'vms': memory_info.vms,  # 虚拟内存
            'percent': process.memory_percent(),
            'tracked_objects': len(self.tracked_objects),
            'peak_usage': self.peak_usage
        }

    def take_snapshot(self):
        """创建内存快照"""
        snapshot = self.get_memory_usage()
        snapshot['timestamp'] = time.time()
        self.memory_snapshots.append(snapshot)

        # 更新峰值使用
        if snapshot['rss'] > self.peak_usage:
            self.peak_usage = snapshot['rss']

        # 保留最近100个快照
        if len(self.memory_snapshots) > 100:
            self.memory_snapshots.pop(0)

    def get_memory_trend(self) -> List[Dict[str, Any]]:
        """获取内存使用趋势"""
        return self.memory_snapshots.copy()


class LRUCache:
    """内存安全的LRU缓存"""

    def __init__(self, max_size: int = 1000, max_memory_mb: int = 100):
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.cache = {}
        self.access_order = []
        self.current_memory = 0
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self._lock:
            if key in self.cache:
                # 更新访问顺序
                self.access_order.remove(key)
                self.access_order.append(key)
                return self.cache[key]['value']
            return None

    def set(self, key: str, value: Any):
        """设置缓存值"""
        with self._lock:
            # 计算值的大小
            import sys
            value_size = sys.getsizeof(value)

            # 如果单个值就超过内存限制，不缓存
            if value_size > self.max_memory_bytes:
                logger.warning(f"值太大无法缓存: {value_size / 1024 / 1024:.1f}MB")
                return

            # 清理空间
            self._make_space(value_size)

            # 更新或添加缓存
            if key in self.cache:
                old_size = self.cache[key]['size']
                self.current_memory -= old_size
                self.access_order.remove(key)

            self.cache[key] = {
                'value': value,
                'size': value_size,
                'timestamp': time.time()
            }
            self.access_order.append(key)
            self.current_memory += value_size

    def _make_space(self, needed_size: int):
        """为新值腾出空间"""
        # 检查大小限制
        while (len(self.cache) >= self.max_size or
               self.current_memory + needed_size > self.max_memory_bytes):
            if not self.access_order:
                break

            # 移除最久未使用的项
            oldest_key = self.access_order.pop(0)
            if oldest_key in self.cache:
                removed_size = self.cache[oldest_key]['size']
                del self.cache[oldest_key]
                self.current_memory -= removed_size

    def clear(self):
        """清空缓存"""
        with self._lock:
            self.cache.clear()
            self.access_order.clear()
            self.current_memory = 0

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        with self._lock:
            return {
                'size': len(self.cache),
                'max_size': self.max_size,
                'memory_usage_bytes': self.current_memory,
                'memory_usage_mb': self.current_memory / 1024 / 1024,
                'max_memory_mb': self.max_memory_bytes / 1024 / 1024,
                'hit_ratio': getattr(self, '_hit_count', 0) / max(getattr(self, '_access_count', 1), 1)
            }


class ChunkedFileReader:
    """分块文件读取器，避免大文件内存溢出"""

    def __init__(self, file_path: str, chunk_size: int = 8192):
        self.file_path = file_path
        self.chunk_size = chunk_size
        self.file_handle = None

    def __enter__(self):
        self.file_handle = open(self.file_path, 'rb')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.file_handle:
            self.file_handle.close()

    def read_chunks(self) -> Generator[bytes, None, None]:
        """逐块读取文件"""
        if not self.file_handle:
            raise ValueError("文件未打开，请使用 with 语句")

        while True:
            chunk = self.file_handle.read(self.chunk_size)
            if not chunk:
                break
            yield chunk

    def process_with_callback(self, callback: Callable[[bytes], Any]):
        """使用回调函数处理每个块"""
        for chunk in self.read_chunks():
            try:
                callback(chunk)
            except Exception as e:
                logger.error(f"处理文件块时出错: {e}")
                break


class MemoryLimitedBuffer:
    """内存限制的缓冲区"""

    def __init__(self, max_memory_mb: int = 50):
        self.max_memory = max_memory_mb * 1024 * 1024
        self.buffer = []
        self.current_memory = 0
        self._lock = threading.Lock()

    def add(self, data: Any) -> bool:
        """添加数据到缓冲区"""
        with self._lock:
            import sys
            data_size = sys.getsizeof(data)

            if data_size > self.max_memory:
                logger.warning(f"数据太大无法缓冲: {data_size / 1024 / 1024:.1f}MB")
                return False

            # 如果空间不足，清理一部分数据
            while self.current_memory + data_size > self.max_memory and self.buffer:
                removed = self.buffer.pop(0)
                self.current_memory -= sys.getsizeof(removed)

            self.buffer.append(data)
            self.current_memory += data_size
            return True

    def get_all(self) -> List[Any]:
        """获取所有缓冲数据"""
        with self._lock:
            return self.buffer.copy()

    def clear(self):
        """清空缓冲区"""
        with self._lock:
            self.buffer.clear()
            self.current_memory = 0

    def get_usage_mb(self) -> float:
        """获取当前内存使用（MB）"""
        return self.current_memory / 1024 / 1024


class MemoryMonitor:
    """内存监控器"""

    def __init__(self, check_interval: int = 30, warning_threshold: float = 80.0, critical_threshold: float = 95.0):
        self.check_interval = check_interval
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self.callbacks = {
            'warning': [],
            'critical': [],
            'normal': []
        }
        self.monitoring = False
        self._monitor_task = None

    def add_callback(self, level: str, callback: Callable[[Dict[str, Any]], None]):
        """添加内存使用回调"""
        if level in self.callbacks:
            self.callbacks[level].append(callback)

    def start_monitoring(self):
        """开始内存监控"""
        if self.monitoring:
            return

        self.monitoring = True
        self._monitor_task = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_task.start()
        logger.info("内存监控已启动")

    def stop_monitoring(self):
        """停止内存监控"""
        self.monitoring = False
        if self._monitor_task:
            self._monitor_task.join(timeout=5)
        logger.info("内存监控已停止")

    def _monitor_loop(self):
        """监控循环"""
        last_state = 'normal'

        while self.monitoring:
            try:
                memory_usage = self._get_memory_usage()
                current_state = self._get_state(memory_usage['percent'])

                # 状态变化时触发回调
                if current_state != last_state or current_state != 'normal':
                    for callback in self.callbacks[current_state]:
                        try:
                            callback(memory_usage)
                        except Exception as e:
                            logger.error(f"内存监控回调错误: {e}")

                last_state = current_state
                time.sleep(self.check_interval)

            except Exception as e:
                logger.error(f"内存监控错误: {e}")
                time.sleep(self.check_interval)

    def _get_memory_usage(self) -> Dict[str, Any]:
        """获取内存使用情况"""
        process = psutil.Process()
        memory_info = process.memory_info()
        system_memory = psutil.virtual_memory()

        return {
            'process_rss_mb': memory_info.rss / 1024 / 1024,
            'process_vms_mb': memory_info.vms / 1024 / 1024,
            'percent': process.memory_percent(),
            'system_total_mb': system_memory.total / 1024 / 1024,
            'system_available_mb': system_memory.available / 1024 / 1024,
            'system_percent': system_memory.percent,
            'timestamp': time.time()
        }

    def _get_state(self, percent: float) -> str:
        """根据内存使用百分比确定状态"""
        if percent >= self.critical_threshold:
            return 'critical'
        elif percent >= self.warning_threshold:
            return 'warning'
        else:
            return 'normal'


class MemoryManager:
    """内存管理器主类"""

    def __init__(self):
        self.tracker = MemoryTracker()
        self.monitor = MemoryMonitor()
        self.global_cache = LRUCache(max_size=1000, max_memory_mb=100)
        self._cleanup_callbacks = []

        # 设置内存监控回调
        self.monitor.add_callback('warning', self._on_memory_warning)
        self.monitor.add_callback('critical', self._on_memory_critical)

    def start(self):
        """启动内存管理"""
        self.monitor.start_monitoring()
        logger.info("内存管理器已启动")

    def stop(self):
        """停止内存管理"""
        self.monitor.stop_monitoring()
        logger.info("内存管理器已停止")

    def add_cleanup_callback(self, callback: Callable[[], None]):
        """添加清理回调"""
        self._cleanup_callbacks.append(callback)

    def force_cleanup(self):
        """强制清理内存"""
        logger.info("开始强制内存清理")

        # 清理全局缓存
        self.global_cache.clear()

        # 执行注册的清理回调
        for callback in self._cleanup_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"清理回调错误: {e}")

        # 强制垃圾回收
        collected = gc.collect()
        logger.info(f"强制清理完成，回收了 {collected} 个对象")

    def _on_memory_warning(self, memory_info: Dict[str, Any]):
        """内存警告处理"""
        logger.warning(f"内存使用过高: {memory_info['percent']:.1f}%")

        # 部分清理
        cache_stats = self.global_cache.get_stats()
        if cache_stats['size'] > 100:
            # 清理一半缓存
            for _ in range(cache_stats['size'] // 2):
                if self.global_cache.access_order:
                    oldest_key = self.global_cache.access_order[0]
                    self.global_cache.cache.pop(oldest_key, None)
                    if oldest_key in self.global_cache.access_order:
                        self.global_cache.access_order.remove(oldest_key)

    def _on_memory_critical(self, memory_info: Dict[str, Any]):
        """内存危急处理"""
        logger.critical(f"内存使用危急: {memory_info['percent']:.1f}%")
        self.force_cleanup()

    def get_stats(self) -> Dict[str, Any]:
        """获取内存管理统计"""
        return {
            'tracker': self.tracker.get_memory_usage(),
            'cache': self.global_cache.get_stats(),
            'monitor': self.monitor._get_memory_usage()
        }


# 全局内存管理器实例
memory_manager = MemoryManager()


def memory_limit(max_memory_mb: int):
    """内存限制装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_memory = psutil.Process().memory_info().rss
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                end_memory = psutil.Process().memory_info().rss
                used_memory_mb = (end_memory - start_memory) / 1024 / 1024
                if used_memory_mb > max_memory_mb:
                    logger.warning(f"函数 {func.__name__} 使用了 {used_memory_mb:.1f}MB，超过限制 {max_memory_mb}MB")
        return wrapper
    return decorator


@contextmanager
def memory_tracking(name: str):
    """内存跟踪上下文管理器"""
    start_memory = psutil.Process().memory_info().rss
    start_time = time.time()

    try:
        yield
    finally:
        end_memory = psutil.Process().memory_info().rss
        end_time = time.time()

        used_memory_mb = (end_memory - start_memory) / 1024 / 1024
        duration = end_time - start_time

        logger.info(f"内存跟踪 [{name}]: 使用 {used_memory_mb:.1f}MB，耗时 {duration:.2f}秒")


async def async_memory_tracking(name: str):
    """异步内存跟踪上下文管理器"""
    start_memory = psutil.Process().memory_info().rss
    start_time = time.time()

    try:
        yield
    finally:
        end_memory = psutil.Process().memory_info().rss
        end_time = time.time()

        used_memory_mb = (end_memory - start_memory) / 1024 / 1024
        duration = end_time - start_time

        logger.info(f"异步内存跟踪 [{name}]: 使用 {used_memory_mb:.1f}MB，耗时 {duration:.2f}秒")