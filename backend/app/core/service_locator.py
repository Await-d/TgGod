"""
服务定位器 - 解决循环导入问题
提供统一的服务管理和依赖注入机制
"""

import asyncio
import threading
from typing import Optional, Dict, Any, Callable, TypeVar, Type, Union
from contextlib import asynccontextmanager
import weakref
import inspect
from functools import wraps
from dataclasses import dataclass, field

from ..core.logging_config import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


@dataclass
class ServiceConfig:
    """服务配置"""
    singleton: bool = True
    lazy_init: bool = True
    factory: Optional[Callable] = None
    dependencies: list = field(default_factory=list)
    lifecycle_hooks: Dict[str, Callable] = field(default_factory=dict)


class ServiceLocator:
    """
    服务定位器 - 管理服务的生命周期和依赖注入

    特性：
    1. 单例模式管理
    2. 延迟初始化
    3. 依赖注入
    4. 生命周期管理
    5. 线程安全
    6. 弱引用避免内存泄漏
    """

    _instance = None
    _lock = threading.RLock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._services: Dict[str, Any] = {}
            self._configs: Dict[str, ServiceConfig] = {}
            self._factories: Dict[str, Callable] = {}
            self._weak_refs: Dict[str, weakref.ref] = {}
            self._initialization_lock = threading.RLock()
            self._async_lock = asyncio.Lock()
            self._initialized = True
            logger.info("ServiceLocator initialized")

    def register(self,
                name: str,
                service_class: Optional[Type[T]] = None,
                instance: Optional[T] = None,
                config: Optional[ServiceConfig] = None,
                factory: Optional[Callable] = None) -> None:
        """
        注册服务

        Args:
            name: 服务名称
            service_class: 服务类型
            instance: 服务实例
            config: 服务配置
            factory: 工厂函数
        """
        with self._initialization_lock:
            if config is None:
                config = ServiceConfig()

            self._configs[name] = config

            if instance is not None:
                # 直接注册实例
                self._services[name] = instance
                if config.singleton:
                    self._weak_refs[name] = weakref.ref(instance)
                logger.info(f"Service '{name}' registered with instance")

            elif factory is not None:
                # 注册工厂函数
                self._factories[name] = factory
                logger.info(f"Service '{name}' registered with factory")

            elif service_class is not None:
                # 注册服务类
                self._factories[name] = lambda: service_class()
                logger.info(f"Service '{name}' registered with class")

            else:
                raise ValueError(f"Must provide either service_class, instance, or factory for service '{name}'")

    def get(self, name: str, default: Optional[T] = None) -> Optional[T]:
        """
        获取服务实例

        Args:
            name: 服务名称
            default: 默认值

        Returns:
            服务实例或默认值
        """
        try:
            # 检查是否已有实例
            if name in self._services:
                return self._services[name]

            # 检查弱引用
            if name in self._weak_refs:
                service = self._weak_refs[name]()
                if service is not None:
                    self._services[name] = service
                    return service
                else:
                    # 弱引用已失效，清除
                    del self._weak_refs[name]

            # 延迟初始化
            return self._create_service(name, default)

        except Exception as e:
            logger.error(f"Error getting service '{name}': {e}")
            return default

    async def get_async(self, name: str, default: Optional[T] = None) -> Optional[T]:
        """异步获取服务实例"""
        async with self._async_lock:
            return self.get(name, default)

    def _create_service(self, name: str, default: Optional[T] = None) -> Optional[T]:
        """创建服务实例"""
        with self._initialization_lock:
            # 双重检查锁定
            if name in self._services:
                return self._services[name]

            if name not in self._configs:
                logger.warning(f"Service '{name}' not registered")
                return default

            config = self._configs[name]

            try:
                # 执行初始化前钩子
                if 'before_init' in config.lifecycle_hooks:
                    config.lifecycle_hooks['before_init']()

                # 创建实例
                if name in self._factories:
                    factory = self._factories[name]

                    # 检查工厂函数是否需要依赖注入
                    if config.dependencies:
                        deps = {}
                        for dep_name in config.dependencies:
                            deps[dep_name] = self.get(dep_name)

                        # 检查工厂函数签名
                        sig = inspect.signature(factory)
                        if len(sig.parameters) > 0:
                            service = factory(**deps)
                        else:
                            service = factory()
                    else:
                        service = factory()

                    # 存储实例
                    if config.singleton:
                        self._services[name] = service
                        self._weak_refs[name] = weakref.ref(service)

                    # 执行初始化后钩子
                    if 'after_init' in config.lifecycle_hooks:
                        config.lifecycle_hooks['after_init'](service)

                    logger.info(f"Service '{name}' created successfully")
                    return service
                else:
                    logger.error(f"No factory registered for service '{name}'")
                    return default

            except Exception as e:
                logger.error(f"Error creating service '{name}': {e}")
                return default

    def has(self, name: str) -> bool:
        """检查服务是否已注册"""
        return name in self._configs

    def remove(self, name: str) -> bool:
        """移除服务"""
        with self._initialization_lock:
            removed = False

            if name in self._services:
                # 执行销毁前钩子
                config = self._configs.get(name)
                if config and 'before_destroy' in config.lifecycle_hooks:
                    try:
                        config.lifecycle_hooks['before_destroy'](self._services[name])
                    except Exception as e:
                        logger.error(f"Error in before_destroy hook for '{name}': {e}")

                del self._services[name]
                removed = True

            if name in self._weak_refs:
                del self._weak_refs[name]
                removed = True

            if name in self._configs:
                del self._configs[name]
                removed = True

            if name in self._factories:
                del self._factories[name]
                removed = True

            if removed:
                logger.info(f"Service '{name}' removed")

            return removed

    def clear(self):
        """清除所有服务"""
        with self._initialization_lock:
            # 执行所有销毁钩子
            for name, service in self._services.items():
                config = self._configs.get(name)
                if config and 'before_destroy' in config.lifecycle_hooks:
                    try:
                        config.lifecycle_hooks['before_destroy'](service)
                    except Exception as e:
                        logger.error(f"Error in before_destroy hook for '{name}': {e}")

            self._services.clear()
            self._weak_refs.clear()
            self._configs.clear()
            self._factories.clear()
            logger.info("All services cleared")

    def list_services(self) -> Dict[str, Dict[str, Any]]:
        """列出所有已注册的服务"""
        result = {}

        for name, config in self._configs.items():
            result[name] = {
                'config': {
                    'singleton': config.singleton,
                    'lazy_init': config.lazy_init,
                    'dependencies': config.dependencies
                },
                'instantiated': name in self._services,
                'has_factory': name in self._factories,
                'weak_ref_alive': name in self._weak_refs and self._weak_refs[name]() is not None
            }

        return result


# 全局服务定位器实例
service_locator = ServiceLocator()


def service_injection(*service_names):
    """
    服务注入装饰器

    Usage:
        @service_injection('task_execution_service', 'media_downloader')
        def my_function(data, task_execution_service=None, media_downloader=None):
            # 服务会自动注入
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 注入服务
            for service_name in service_names:
                if service_name not in kwargs:
                    kwargs[service_name] = service_locator.get(service_name)

            return func(*args, **kwargs)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 异步注入服务
            for service_name in service_names:
                if service_name not in kwargs:
                    kwargs[service_name] = await service_locator.get_async(service_name)

            return await func(*args, **kwargs)

        # 根据函数是否为协程返回相应的包装器
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return wrapper

    return decorator


@asynccontextmanager
async def service_scope(*service_names):
    """
    服务作用域上下文管理器

    Usage:
        async with service_scope('task_execution_service') as services:
            task_service = services['task_execution_service']
            # 使用服务
    """
    services = {}

    try:
        for service_name in service_names:
            services[service_name] = await service_locator.get_async(service_name)

        yield services

    finally:
        # 清理逻辑（如果需要）
        pass


class ServiceProxy:
    """
    服务代理 - 延迟获取服务实例
    避免在模块加载时立即获取服务
    """

    def __init__(self, service_name: str):
        self._service_name = service_name
        self._service_instance = None
        self._lock = threading.RLock()

    def __getattr__(self, name):
        return getattr(self._get_service(), name)

    def __call__(self, *args, **kwargs):
        return self._get_service()(*args, **kwargs)

    def _get_service(self):
        if self._service_instance is None:
            with self._lock:
                if self._service_instance is None:
                    self._service_instance = service_locator.get(self._service_name)
                    if self._service_instance is None:
                        raise ValueError(f"Service '{self._service_name}' not found")

        return self._service_instance


def create_service_proxy(service_name: str) -> ServiceProxy:
    """创建服务代理"""
    return ServiceProxy(service_name)


# 导出主要接口
__all__ = [
    'ServiceLocator',
    'ServiceConfig',
    'service_locator',
    'service_injection',
    'service_scope',
    'ServiceProxy',
    'create_service_proxy'
]