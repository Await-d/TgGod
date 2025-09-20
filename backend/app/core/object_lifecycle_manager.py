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

    def __init__(self, obj_type: Type, max_size: int = 10, max_idle_time: int = 300):
        self.obj_type = obj_type
        self.max_size = max_size
        self.max_idle_time = max_idle_time
        self.available_objects: List[Any] = []
        self.in_use_objects: Set[Any] = set()
        self._lock = threading.Lock()
        self.created_count = 0
        self.reused_count = 0

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

            # 池已满，直接创建临时对象
            obj = self.obj_type(*args, **kwargs)
            logger.debug(f"池已满，创建临时对象 {self.obj_type.__name__}")
            return obj

    def return_object(self, obj: Any):
        """归还对象到池中"""
        with self._lock:
            if obj in self.in_use_objects:
                self.in_use_objects.remove(obj)

                # 检查对象是否可以重用
                if len(self.available_objects) < self.max_size and self._is_reusable(obj):
                    self.available_objects.append(obj)
                    logger.debug(f"对象已归还到池 {self.obj_type.__name__}")
                else:
                    # 对象不能重用，执行清理
                    self._cleanup_object(obj)
                    logger.debug(f"对象已清理 {self.obj_type.__name__}")

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

    def clear(self):
        """清空池"""
        with self._lock:
            for obj in self.available_objects:
                self._cleanup_object(obj)
            self.available_objects.clear()

            for obj in self.in_use_objects.copy():
                self._cleanup_object(obj)
            self.in_use_objects.clear()


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