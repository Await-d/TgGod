"""
内存监控服务

提供实时内存监控、自动清理和性能告警功能
"""

import asyncio
import gc
import logging
import os
import psutil
import time
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
import weakref

from ..core.memory_manager import memory_manager, MemoryTracker
from ..websocket.manager import websocket_manager

logger = logging.getLogger(__name__)


@dataclass
class MemoryAlert:
    """内存告警信息"""
    level: str  # 'warning', 'critical'
    message: str
    memory_usage: float
    timestamp: datetime
    details: Dict[str, Any]


class MemoryCleanupRegistry:
    """内存清理注册器"""

    def __init__(self):
        self.cleanup_callbacks: List[Callable[[], None]] = []
        self.weak_references: weakref.WeakSet = weakref.WeakSet()
        self.service_caches: Dict[str, Any] = {}

    def register_cleanup_callback(self, callback: Callable[[], None], name: str = None):
        """注册清理回调"""
        self.cleanup_callbacks.append(callback)
        if name:
            logger.info(f"注册内存清理回调: {name}")

    def register_weak_reference(self, obj: Any, name: str = None):
        """注册弱引用对象"""
        self.weak_references.add(obj)
        if name:
            logger.debug(f"注册弱引用对象: {name}")

    def register_service_cache(self, service_name: str, cache_obj: Any):
        """注册服务缓存"""
        self.service_caches[service_name] = cache_obj
        logger.info(f"注册服务缓存: {service_name}")

    def execute_cleanup(self, force: bool = False) -> Dict[str, Any]:
        """执行清理操作"""
        cleanup_results = {
            'callbacks_executed': 0,
            'objects_collected': 0,
            'caches_cleared': 0,
            'memory_freed_mb': 0
        }

        # 记录清理前的内存使用
        process = psutil.Process()
        memory_before = process.memory_info().rss

        try:
            # 执行注册的清理回调
            for i, callback in enumerate(self.cleanup_callbacks):
                try:
                    callback()
                    cleanup_results['callbacks_executed'] += 1
                except Exception as e:
                    logger.error(f"清理回调 {i} 执行失败: {e}")

            # 清理服务缓存
            for service_name, cache_obj in self.service_caches.items():
                try:
                    if hasattr(cache_obj, 'clear'):
                        cache_obj.clear()
                        cleanup_results['caches_cleared'] += 1
                        logger.info(f"已清理服务缓存: {service_name}")
                except Exception as e:
                    logger.error(f"清理服务缓存失败 {service_name}: {e}")

            # 强制垃圾回收
            collected = gc.collect()
            cleanup_results['objects_collected'] = collected

            # 计算释放的内存
            memory_after = process.memory_info().rss
            memory_freed = max(0, memory_before - memory_after)
            cleanup_results['memory_freed_mb'] = memory_freed / 1024 / 1024

            logger.info(f"内存清理完成: {cleanup_results}")
            return cleanup_results

        except Exception as e:
            logger.error(f"内存清理过程出错: {e}")
            return cleanup_results


class MemoryMonitoringService:
    """内存监控服务"""

    def __init__(self, check_interval: int = 30):
        self.check_interval = check_interval
        self.monitoring = False
        self.cleanup_registry = MemoryCleanupRegistry()
        self.alerts_history: List[MemoryAlert] = []
        self.memory_history: List[Dict[str, Any]] = []
        self._monitor_task: Optional[asyncio.Task] = None

        # 阈值配置
        self.warning_threshold = 75.0  # 75% 内存使用率警告
        self.critical_threshold = 90.0  # 90% 内存使用率危急
        self.auto_cleanup_threshold = 85.0  # 85% 自动清理

        # 统计信息
        self.stats = {
            'total_cleanups': 0,
            'total_alerts': 0,
            'peak_memory_mb': 0,
            'start_time': None
        }

    async def start(self):
        """启动内存监控"""
        if self.monitoring:
            logger.warning("内存监控已在运行")
            return

        self.monitoring = True
        self.stats['start_time'] = datetime.now()
        self._monitor_task = asyncio.create_task(self._monitoring_loop())

        # 启动全局内存管理器
        memory_manager.start()

        logger.info(f"内存监控服务已启动，检查间隔: {self.check_interval}秒")

    async def stop(self):
        """停止内存监控"""
        if not self.monitoring:
            return

        self.monitoring = False

        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        # 停止全局内存管理器
        memory_manager.stop()

        logger.info("内存监控服务已停止")

    async def _monitoring_loop(self):
        """监控循环"""
        last_cleanup_time = 0

        while self.monitoring:
            try:
                # 获取内存使用情况
                memory_info = self._get_detailed_memory_info()
                self.memory_history.append(memory_info)

                # 保留最近1000个记录
                if len(self.memory_history) > 1000:
                    self.memory_history.pop(0)

                # 更新峰值内存
                current_memory_mb = memory_info['process_memory_mb']
                if current_memory_mb > self.stats['peak_memory_mb']:
                    self.stats['peak_memory_mb'] = current_memory_mb

                # 检查是否需要告警
                await self._check_memory_alerts(memory_info)

                # 检查是否需要自动清理
                memory_percent = memory_info['system_memory_percent']
                current_time = time.time()

                if (memory_percent > self.auto_cleanup_threshold and
                    current_time - last_cleanup_time > 300):  # 5分钟内不重复清理

                    logger.warning(f"内存使用率达到 {memory_percent:.1f}%，触发自动清理")
                    await self._auto_cleanup()
                    last_cleanup_time = current_time

                # 发送内存信息到WebSocket客户端
                await self._broadcast_memory_info(memory_info)

                await asyncio.sleep(self.check_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"内存监控循环出错: {e}")
                await asyncio.sleep(self.check_interval)

    def _get_detailed_memory_info(self) -> Dict[str, Any]:
        """获取详细的内存信息"""
        process = psutil.Process()
        process_memory = process.memory_info()
        system_memory = psutil.virtual_memory()

        # 获取Python内存信息
        import sys
        python_objects = len(gc.get_objects())

        return {
            'timestamp': datetime.now().isoformat(),
            'process_memory_mb': process_memory.rss / 1024 / 1024,
            'process_memory_percent': process.memory_percent(),
            'system_memory_percent': system_memory.percent,
            'system_available_mb': system_memory.available / 1024 / 1024,
            'system_total_mb': system_memory.total / 1024 / 1024,
            'python_objects_count': python_objects,
            'tracked_objects': len(memory_manager.tracker.tracked_objects),
            'cache_usage': memory_manager.global_cache.get_stats()
        }

    async def _check_memory_alerts(self, memory_info: Dict[str, Any]):
        """检查内存告警"""
        memory_percent = memory_info['system_memory_percent']
        process_percent = memory_info['process_memory_percent']

        alert_level = None
        alert_message = None

        if memory_percent >= self.critical_threshold or process_percent >= self.critical_threshold:
            alert_level = 'critical'
            alert_message = f"内存使用危急: 系统 {memory_percent:.1f}%, 进程 {process_percent:.1f}%"
        elif memory_percent >= self.warning_threshold or process_percent >= self.warning_threshold:
            alert_level = 'warning'
            alert_message = f"内存使用警告: 系统 {memory_percent:.1f}%, 进程 {process_percent:.1f}%"

        if alert_level:
            alert = MemoryAlert(
                level=alert_level,
                message=alert_message,
                memory_usage=memory_percent,
                timestamp=datetime.now(),
                details=memory_info
            )

            self.alerts_history.append(alert)
            self.stats['total_alerts'] += 1

            # 保留最近100个告警
            if len(self.alerts_history) > 100:
                self.alerts_history.pop(0)

            logger.log(
                logging.CRITICAL if alert_level == 'critical' else logging.WARNING,
                alert_message
            )

            # 发送告警到WebSocket客户端
            await self._broadcast_alert(alert)

    async def _auto_cleanup(self):
        """自动内存清理"""
        try:
            logger.info("开始自动内存清理")

            # 执行清理
            cleanup_results = self.cleanup_registry.execute_cleanup()
            self.stats['total_cleanups'] += 1

            # 记录清理结果
            logger.info(f"自动清理完成: {cleanup_results}")

            # 发送清理结果到WebSocket客户端
            await websocket_manager.broadcast({
                'type': 'memory_cleanup',
                'data': {
                    'timestamp': datetime.now().isoformat(),
                    'results': cleanup_results
                }
            })

        except Exception as e:
            logger.error(f"自动内存清理失败: {e}")

    async def _broadcast_memory_info(self, memory_info: Dict[str, Any]):
        """广播内存信息"""
        try:
            await websocket_manager.broadcast({
                'type': 'memory_status',
                'data': memory_info
            })
        except Exception as e:
            logger.debug(f"广播内存信息失败: {e}")

    async def _broadcast_alert(self, alert: MemoryAlert):
        """广播内存告警"""
        try:
            await websocket_manager.broadcast({
                'type': 'memory_alert',
                'data': {
                    'level': alert.level,
                    'message': alert.message,
                    'memory_usage': alert.memory_usage,
                    'timestamp': alert.timestamp.isoformat(),
                    'details': alert.details
                }
            })
        except Exception as e:
            logger.debug(f"广播内存告警失败: {e}")

    def get_memory_statistics(self) -> Dict[str, Any]:
        """获取内存统计信息"""
        if not self.memory_history:
            return {}

        # 计算统计信息
        memory_values = [item['process_memory_mb'] for item in self.memory_history]

        return {
            'current_memory_mb': memory_values[-1] if memory_values else 0,
            'peak_memory_mb': self.stats['peak_memory_mb'],
            'average_memory_mb': sum(memory_values) / len(memory_values),
            'total_cleanups': self.stats['total_cleanups'],
            'total_alerts': self.stats['total_alerts'],
            'uptime_hours': (
                (datetime.now() - self.stats['start_time']).total_seconds() / 3600
                if self.stats['start_time'] else 0
            ),
            'recent_alerts': [
                {
                    'level': alert.level,
                    'message': alert.message,
                    'timestamp': alert.timestamp.isoformat()
                }
                for alert in self.alerts_history[-10:]  # 最近10个告警
            ],
            'memory_trend': self.memory_history[-50:] if self.memory_history else []  # 最近50个数据点
        }

    def force_cleanup(self) -> Dict[str, Any]:
        """强制执行内存清理"""
        logger.info("执行强制内存清理")
        cleanup_results = self.cleanup_registry.execute_cleanup(force=True)
        self.stats['total_cleanups'] += 1
        return cleanup_results

    def register_service_for_cleanup(self, service_name: str, cleanup_callback: Callable[[], None]):
        """为服务注册清理回调"""
        self.cleanup_registry.register_cleanup_callback(cleanup_callback, service_name)

    def register_service_cache(self, service_name: str, cache_obj: Any):
        """注册服务缓存对象"""
        self.cleanup_registry.register_service_cache(service_name, cache_obj)

    def get_service_memory_usage(self) -> Dict[str, Any]:
        """获取各服务的内存使用情况"""
        service_usage = {}

        # 获取缓存使用情况
        for service_name, cache_obj in self.cleanup_registry.service_caches.items():
            try:
                if hasattr(cache_obj, 'get_stats'):
                    stats = cache_obj.get_stats()
                    service_usage[service_name] = {
                        'type': 'cache',
                        'stats': stats
                    }
                elif hasattr(cache_obj, '__len__'):
                    service_usage[service_name] = {
                        'type': 'collection',
                        'size': len(cache_obj)
                    }
            except Exception as e:
                logger.debug(f"获取服务 {service_name} 内存使用失败: {e}")

        return service_usage


# 全局内存监控服务实例
memory_monitoring_service = MemoryMonitoringService()


def register_memory_cleanup(service_name: str, cleanup_callback: Callable[[], None]):
    """注册内存清理回调的便捷函数"""
    memory_monitoring_service.register_service_for_cleanup(service_name, cleanup_callback)


def register_service_cache(service_name: str, cache_obj: Any):
    """注册服务缓存的便捷函数"""
    memory_monitoring_service.register_service_cache(service_name, cache_obj)