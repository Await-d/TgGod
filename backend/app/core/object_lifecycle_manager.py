"""
对象生命周期管理器

管理对象的创建、使用和销毁，防止内存泄漏和资源浪费
"""

import asyncio
import gc
import logging
import threading
import time
import weakref
from collections import defaultdict
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Type, Callable
from enum import Enum

logger = logging.getLogger(__name__)


class ObjectState(Enum):
    """对象状态枚举"""
    CREATED = "created"
    ACTIVE = "active"
    IDLE = "idle"
    CLEANUP = "cleanup"
    DESTROYED = "destroyed"


@dataclass
class ObjectInfo:
    """对象信息"""
    obj_id: int
    obj_type: str
    state: ObjectState
    created_at: float
    last_access: float
    access_count: int
    size_bytes: int
    ref_count: int


class ObjectPool:
    """对象池 - 复用对象减少创建开销"""

    def __init__(self, obj_type: Type, max_size: int = 10, max_idle_time: int = 300,
                 enable_expansion: bool = True, expansion_factor: float = 1.5,
                 max_expansion_size: int = 50, enable_waiting: bool = True,
                 max_wait_time: float = 5.0, preload_size: int = 0):
        self.obj_type = obj_type
        self.max_size = max_size
        self.max_idle_time = max_idle_time

        # 动态扩展配置
        self.enable_expansion = enable_expansion
        self.expansion_factor = expansion_factor
        self.max_expansion_size = max_expansion_size
        self.current_max_size = max_size

        # 等待队列配置
        self.enable_waiting = enable_waiting
        self.max_wait_time = max_wait_time
        self._waiting_queue = []  # 等待对象的线程队列

        # LRU策略实现
        self.available_objects: List[Any] = []
        self.object_access_times: Dict[Any, float] = {}  # 对象访问时间
        self.object_usage_count: Dict[Any, int] = {}     # 对象使用次数

        self.in_use_objects: Set[Any] = set()
        self._lock = threading.Lock()
        self._condition = threading.Condition(self._lock)  # 用于等待队列

        # 统计信息
        self.created_count = 0
        self.reused_count = 0
        self.expansion_count = 0
        self.wait_count = 0
        self.eviction_count = 0

        # 池预热
        if preload_size > 0:
            self._preload_pool(preload_size)

    def get_object(self, *args, **kwargs) -> Any:
        """获取对象实例"""
        with self._lock:
            # 尝试从池中获取可用对象
            if self.available_objects:
                obj = self.available_objects.pop()
                self.in_use_objects.add(obj)
                self.reused_count += 1

                # 如果对象有重置方法，调用它
                if hasattr(obj, 'reset'):
                    obj.reset(*args, **kwargs)

                logger.debug(f"从池中复用对象 {self.obj_type.__name__}")
                return obj

            # 池中没有可用对象，创建新的
            if len(self.in_use_objects) < self.max_size:
                try:
                    obj = self.obj_type(*args, **kwargs)
                    self.in_use_objects.add(obj)
                    self.created_count += 1
                    logger.debug(f"创建新对象 {self.obj_type.__name__}")
                    return obj
                except Exception as e:
                    logger.error(f"创建对象失败 {self.obj_type.__name__}: {e}")
                    raise

            # 池已满，实现动态扩展策略
            return self._handle_pool_full(*args, **kwargs)


    def _is_reusable(self, obj: Any) -> bool:
        """检查对象是否可以重用"""
        # 检查对象是否有cleanup方法且执行成功
        if hasattr(obj, 'cleanup'):
            try:
                if asyncio.iscoroutinefunction(obj.cleanup):
                    # 异步清理方法需要特殊处理
                    return True  # 假设可以重用，实际清理延迟执行
                else:
                    obj.cleanup()
                return True
            except Exception as e:
                logger.warning(f"对象清理失败，不能重用: {e}")
                return False
        return True

    def _cleanup_object(self, obj: Any):
        """清理对象"""
        try:
            if hasattr(obj, 'cleanup'):
                if asyncio.iscoroutinefunction(obj.cleanup):
                    # 对于异步清理，创建任务执行
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            asyncio.create_task(obj.cleanup())
                    except RuntimeError:
                        # 没有事件循环，跳过异步清理
                        pass
                else:
                    obj.cleanup()
        except Exception as e:
            logger.warning(f"对象清理出错: {e}")

    def cleanup_idle_objects(self):
        """清理空闲对象"""
        current_time = time.time()
        with self._lock:
            # 移除超时的空闲对象
            self.available_objects = [
                obj for obj in self.available_objects
                if current_time - getattr(obj, '_pool_return_time', current_time) < self.max_idle_time
            ]

    def get_stats(self) -> Dict[str, Any]:
        """获取池统计信息"""
        with self._lock:
            return {
                'obj_type': self.obj_type.__name__,
                'max_size': self.max_size,
                'available_count': len(self.available_objects),
                'in_use_count': len(self.in_use_objects),
                'created_count': self.created_count,
                'reused_count': self.reused_count,
                'reuse_ratio': self.reused_count / max(self.created_count, 1)
            }

    def _preload_pool(self, size: int):
        """池预热 - 预先创建指定数量的对象"""
        try:
            for _ in range(min(size, self.max_size)):
                try:
                    obj = self.obj_type()
                    self.available_objects.append(obj)
                    self.object_access_times[obj] = time.time()
                    self.object_usage_count[obj] = 0
                    self.created_count += 1
                except Exception as e:
                    logger.warning(f"池预热失败: {e}")
                    break
            logger.info(f"池预热完成，创建了 {len(self.available_objects)} 个对象")
        except Exception as e:
            logger.error(f"池预热出错: {e}")

    def _handle_pool_full(self, *args, **kwargs) -> Any:
        """处理池已满的情况"""
        # 首先尝试动态扩展
        if self.enable_expansion and self.current_max_size < self.max_expansion_size:
            return self._try_expand_pool(*args, **kwargs)

        # 如果启用等待队列，尝试等待
        if self.enable_waiting:
            return self._wait_for_object(*args, **kwargs)

        # 最后选择：创建临时对象或LRU淘汰
        return self._create_or_evict(*args, **kwargs)

    def _try_expand_pool(self, *args, **kwargs) -> Any:
        """尝试动态扩展池"""
        new_size = min(
            int(self.current_max_size * self.expansion_factor),
            self.max_expansion_size
        )

        if new_size > self.current_max_size:
            old_size = self.current_max_size
            self.current_max_size = new_size
            self.expansion_count += 1

            logger.info(f"池动态扩展: {old_size} -> {new_size}")

            # 创建新对象
            try:
                obj = self.obj_type(*args, **kwargs)
                self.in_use_objects.add(obj)
                self.created_count += 1
                self._update_object_stats(obj)
                return obj
            except Exception as e:
                logger.error(f"池扩展时创建对象失败: {e}")
                # 回滚扩展
                self.current_max_size = old_size
                raise

        # 扩展失败，使用其他策略
        return self._create_or_evict(*args, **kwargs)

    def _wait_for_object(self, *args, **kwargs) -> Any:
        """等待队列实现"""
        wait_start = time.time()
        self.wait_count += 1

        try:
            while time.time() - wait_start < self.max_wait_time:
                # 检查是否有对象可用
                if self.available_objects:
                    obj = self.available_objects.pop()
                    self.in_use_objects.add(obj)
                    self.reused_count += 1
                    self._update_object_stats(obj)

                    if hasattr(obj, 'reset'):
                        obj.reset(*args, **kwargs)

                    logger.debug(f"等待后获取到对象 {self.obj_type.__name__}")
                    return obj

                # 等待通知
                if not self._condition.wait(timeout=0.1):
                    continue

            # 等待超时，创建临时对象
            logger.warning(f"等待对象超时，创建临时对象 {self.obj_type.__name__}")
            return self._create_temporary_object(*args, **kwargs)

        except Exception as e:
            logger.error(f"等待对象时出错: {e}")
            return self._create_temporary_object(*args, **kwargs)

    def _create_or_evict(self, *args, **kwargs) -> Any:
        """创建临时对象或使用LRU淘汰策略"""
        # 尝试LRU淘汰
        if self.available_objects:
            evicted_obj = self._lru_evict()
            if evicted_obj:
                self.in_use_objects.add(evicted_obj)
                self.reused_count += 1
                self._update_object_stats(evicted_obj)

                if hasattr(evicted_obj, 'reset'):
                    evicted_obj.reset(*args, **kwargs)

                logger.debug(f"LRU淘汰后重用对象 {self.obj_type.__name__}")
                return evicted_obj

        # 创建临时对象
        return self._create_temporary_object(*args, **kwargs)

    def _lru_evict(self) -> Optional[Any]:
        """LRU淘汰策略 - 淘汰最近最少使用的对象"""
        if not self.available_objects:
            return None

        # 按访问时间排序，选择最旧的对象
        lru_obj = min(
            self.available_objects,
            key=lambda obj: (
                self.object_access_times.get(obj, 0),
                self.object_usage_count.get(obj, 0)
            )
        )

        self.available_objects.remove(lru_obj)
        self.eviction_count += 1
        logger.debug(f"LRU淘汰对象 {self.obj_type.__name__}")
        return lru_obj

    def _create_temporary_object(self, *args, **kwargs) -> Any:
        """创建临时对象（不放入池中）"""
        obj = self.obj_type(*args, **kwargs)
        logger.debug(f"创建临时对象 {self.obj_type.__name__}")
        return obj

    def _update_object_stats(self, obj: Any):
        """更新对象统计信息"""
        current_time = time.time()
        self.object_access_times[obj] = current_time
        self.object_usage_count[obj] = self.object_usage_count.get(obj, 0) + 1

    def return_object(self, obj: Any):
        """归还对象到池中（增强版）"""
        with self._condition:
            if obj in self.in_use_objects:
                self.in_use_objects.remove(obj)

                # 检查对象是否可以重用
                if len(self.available_objects) < self.current_max_size and self._is_reusable(obj):
                    # 使用LRU策略管理可用对象
                    self._add_to_available_with_lru(obj)
                    logger.debug(f"对象已归还到池 {self.obj_type.__name__}")

                    # 通知等待的线程
                    self._condition.notify()
                else:
                    # 对象不能重用，执行清理
                    self._cleanup_object(obj)
                    self._cleanup_object_stats(obj)
                    logger.debug(f"对象已清理 {self.obj_type.__name__}")
            else:
                # 临时对象，直接清理
                self._cleanup_object(obj)

    def _add_to_available_with_lru(self, obj: Any):
        """使用LRU策略添加对象到可用列表"""
        # 如果可用对象列表已满，先淘汰最老的对象
        if len(self.available_objects) >= self.current_max_size:
            if self.available_objects:
                lru_obj = self._lru_evict()
                if lru_obj:
                    self._cleanup_object(lru_obj)
                    self._cleanup_object_stats(lru_obj)

        # 添加新对象
        self.available_objects.append(obj)
        obj._pool_return_time = time.time()
        self._update_object_stats(obj)

    def _cleanup_object_stats(self, obj: Any):
        """清理对象统计信息"""
        self.object_access_times.pop(obj, None)
        self.object_usage_count.pop(obj, None)

    def get_stats(self) -> Dict[str, Any]:
        """获取池统计信息（增强版）"""
        with self._lock:
            return {
                'obj_type': self.obj_type.__name__,
                'max_size': self.max_size,
                'current_max_size': self.current_max_size,
                'available_count': len(self.available_objects),
                'in_use_count': len(self.in_use_objects),
                'created_count': self.created_count,
                'reused_count': self.reused_count,
                'expansion_count': self.expansion_count,
                'wait_count': self.wait_count,
                'eviction_count': self.eviction_count,
                'reuse_ratio': self.reused_count / max(self.created_count, 1),
                'expansion_enabled': self.enable_expansion,
                'waiting_enabled': self.enable_waiting,
                'lru_stats': {
                    'total_objects_tracked': len(self.object_access_times),
                    'avg_usage_count': sum(self.object_usage_count.values()) / max(len(self.object_usage_count), 1)
                }
            }

    def clear(self):
        """清空池"""
        with self._lock:
            for obj in self.available_objects:
                self._cleanup_object(obj)
            self.available_objects.clear()

            for obj in self.in_use_objects.copy():
                self._cleanup_object(obj)
            self.in_use_objects.clear()

            # 清理统计信息
            self.object_access_times.clear()
            self.object_usage_count.clear()


class ObjectLifecycleManager:
    """对象生命周期管理器"""

    def __init__(self):
        self.tracked_objects: Dict[int, ObjectInfo] = {}
        self.object_pools: Dict[Type, ObjectPool] = {}
        self.weak_refs: weakref.WeakSet = weakref.WeakSet()
        self.cleanup_callbacks: Dict[Type, List[Callable]] = defaultdict(list)
        self._lock = threading.Lock()
        self.monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None

        # 配置
        self.max_idle_time = 300  # 5分钟空闲时间
        self.cleanup_interval = 60  # 1分钟清理间隔

    def register_object_pool(self, obj_type: Type, max_size: int = 10, max_idle_time: int = 300):
        """注册对象池"""
        self.object_pools[obj_type] = ObjectPool(obj_type, max_size, max_idle_time)
        logger.info(f"注册对象池: {obj_type.__name__}, 最大大小: {max_size}")

    def get_pooled_object(self, obj_type: Type, *args, **kwargs) -> Any:
        """从池中获取对象"""
        if obj_type not in self.object_pools:
            # 没有注册池，直接创建对象
            return obj_type(*args, **kwargs)

        obj = self.object_pools[obj_type].get_object(*args, **kwargs)
        self.track_object(obj)
        return obj

    def return_pooled_object(self, obj: Any):
        """归还对象到池"""
        obj_type = type(obj)
        if obj_type in self.object_pools:
            self.object_pools[obj_type].return_object(obj)
        self.untrack_object(obj)

    def track_object(self, obj: Any, obj_type: str = None):
        """跟踪对象"""
        obj_id = id(obj)
        current_time = time.time()

        # 添加弱引用
        self.weak_refs.add(obj)

        # 记录对象信息
        obj_info = ObjectInfo(
            obj_id=obj_id,
            obj_type=obj_type or type(obj).__name__,
            state=ObjectState.CREATED,
            created_at=current_time,
            last_access=current_time,
            access_count=1,
            size_bytes=self._estimate_object_size(obj),
            ref_count=self._get_ref_count(obj)
        )

        with self._lock:
            self.tracked_objects[obj_id] = obj_info

        logger.debug(f"开始跟踪对象: {obj_info.obj_type}#{obj_id}")

    def untrack_object(self, obj: Any):
        """停止跟踪对象"""
        obj_id = id(obj)
        with self._lock:
            if obj_id in self.tracked_objects:
                obj_info = self.tracked_objects[obj_id]
                obj_info.state = ObjectState.DESTROYED
                del self.tracked_objects[obj_id]
                logger.debug(f"停止跟踪对象: {obj_info.obj_type}#{obj_id}")

        # 从弱引用集合中移除
        try:
            self.weak_refs.discard(obj)
        except:
            pass

    def access_object(self, obj: Any):
        """记录对象访问"""
        obj_id = id(obj)
        with self._lock:
            if obj_id in self.tracked_objects:
                obj_info = self.tracked_objects[obj_id]
                obj_info.last_access = time.time()
                obj_info.access_count += 1
                obj_info.state = ObjectState.ACTIVE

    def register_cleanup_callback(self, obj_type: Type, callback: Callable):
        """注册清理回调"""
        self.cleanup_callbacks[obj_type].append(callback)
        logger.info(f"注册清理回调: {obj_type.__name__}")

    def start_monitoring(self):
        """开始监控对象生命周期"""
        if self.monitoring:
            return

        self.monitoring = True
        self._monitor_task = asyncio.create_task(self._monitoring_loop())
        logger.info("对象生命周期监控已启动")

    def stop_monitoring(self):
        """停止监控"""
        if not self.monitoring:
            return

        self.monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
        logger.info("对象生命周期监控已停止")

    async def _monitoring_loop(self):
        """监控循环"""
        while self.monitoring:
            try:
                await self._cleanup_idle_objects()
                await self._cleanup_object_pools()
                await self._update_object_states()
                await asyncio.sleep(self.cleanup_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"对象生命周期监控错误: {e}")
                await asyncio.sleep(self.cleanup_interval)

    async def _cleanup_idle_objects(self):
        """清理空闲对象"""
        current_time = time.time()
        idle_objects = []

        with self._lock:
            for obj_id, obj_info in list(self.tracked_objects.items()):
                if (current_time - obj_info.last_access > self.max_idle_time and
                    obj_info.state != ObjectState.CLEANUP):
                    obj_info.state = ObjectState.IDLE
                    idle_objects.append(obj_id)

        # 执行清理回调
        for obj_id in idle_objects:
            await self._execute_cleanup_callbacks(obj_id)

    async def _cleanup_object_pools(self):
        """清理对象池"""
        for pool in self.object_pools.values():
            pool.cleanup_idle_objects()

    async def _update_object_states(self):
        """更新对象状态"""
        with self._lock:
            for obj_info in self.tracked_objects.values():
                obj_info.ref_count = self._get_ref_count_by_id(obj_info.obj_id)

    async def _execute_cleanup_callbacks(self, obj_id: int):
        """执行清理回调"""
        with self._lock:
            if obj_id not in self.tracked_objects:
                return

            obj_info = self.tracked_objects[obj_id]
            obj_info.state = ObjectState.CLEANUP

        # 查找对应的清理回调
        for obj_type, callbacks in self.cleanup_callbacks.items():
            if obj_info.obj_type == obj_type.__name__:
                for callback in callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(obj_id, obj_info)
                        else:
                            callback(obj_id, obj_info)
                    except Exception as e:
                        logger.error(f"清理回调执行失败: {e}")

    def _estimate_object_size(self, obj: Any) -> int:
        """估算对象大小"""
        try:
            import sys
            return sys.getsizeof(obj)
        except:
            return 0

    def _get_ref_count(self, obj: Any) -> int:
        """获取对象引用计数"""
        try:
            import sys
            return sys.getrefcount(obj)
        except:
            return 0

    def _get_ref_count_by_id(self, obj_id: int) -> int:
        """通过ID获取引用计数"""
        try:
            import gc
            for obj in gc.get_objects():
                if id(obj) == obj_id:
                    return self._get_ref_count(obj)
            return 0
        except:
            return 0

    def get_lifecycle_stats(self) -> Dict[str, Any]:
        """获取生命周期统计"""
        with self._lock:
            stats = {
                'tracked_objects_count': len(self.tracked_objects),
                'weak_refs_count': len(self.weak_refs),
                'object_pools_count': len(self.object_pools),
                'states_distribution': defaultdict(int),
                'types_distribution': defaultdict(int),
                'pool_stats': {}
            }

            # 统计状态分布
            for obj_info in self.tracked_objects.values():
                stats['states_distribution'][obj_info.state.value] += 1
                stats['types_distribution'][obj_info.obj_type] += 1

            # 统计池信息
            for obj_type, pool in self.object_pools.items():
                stats['pool_stats'][obj_type.__name__] = pool.get_stats()

            return stats

    def force_cleanup(self):
        """强制清理所有对象"""
        logger.info("开始强制对象清理")

        # 清理所有对象池
        for pool in self.object_pools.values():
            pool.clear()

        # 清理跟踪的对象
        with self._lock:
            for obj_info in self.tracked_objects.values():
                obj_info.state = ObjectState.DESTROYED
            self.tracked_objects.clear()

        # 清理弱引用
        self.weak_refs.clear()

        # 强制垃圾回收
        collected = gc.collect()
        logger.info(f"强制清理完成，回收了 {collected} 个对象")


# 全局对象生命周期管理器
lifecycle_manager = ObjectLifecycleManager()


@contextmanager
def managed_object(obj_type: Type, *args, **kwargs):
    """托管对象上下文管理器"""
    obj = lifecycle_manager.get_pooled_object(obj_type, *args, **kwargs)
    try:
        yield obj
    finally:
        lifecycle_manager.return_pooled_object(obj)


@asynccontextmanager
async def async_managed_object(obj_type: Type, *args, **kwargs):
    """异步托管对象上下文管理器"""
    obj = lifecycle_manager.get_pooled_object(obj_type, *args, **kwargs)
    try:
        yield obj
    finally:
        lifecycle_manager.return_pooled_object(obj)
        # 如果对象有异步清理方法，确保执行
        if hasattr(obj, 'cleanup') and asyncio.iscoroutinefunction(obj.cleanup):
            try:
                await obj.cleanup()
            except Exception as e:
                logger.warning(f"异步清理失败: {e}")


def track_object_lifecycle(obj_type: str = None):
    """对象生命周期跟踪装饰器"""
    def decorator(cls):
        original_init = cls.__init__

        def __init__(self, *args, **kwargs):
            original_init(self, *args, **kwargs)
            lifecycle_manager.track_object(self, obj_type or cls.__name__)

        def __del__(self):
            lifecycle_manager.untrack_object(self)

        cls.__init__ = __init__
        cls.__del__ = __del__
        return cls

    return decorator