"""
Enterprise Service Governance Framework
企业级服务治理框架

This module provides comprehensive service governance capabilities including:
- Service discovery and registry
- Health monitoring and metrics collection
- Circuit breaker and rate limiting
- Service mesh coordination
- Performance monitoring
- Dependency management
- Service lifecycle management

Author: TgGod DevOps Team
Version: 1.0.0
"""

import asyncio
import time
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from contextlib import contextmanager
from collections import defaultdict
import weakref
import threading
from concurrent.futures import ThreadPoolExecutor
import uuid

from . import (
    ServiceResult, HealthCheckResult, ServiceError, SystemError,
    NetworkError, ConfigurationError, ErrorSeverity, ErrorContext,
    handle_service_errors, timeout, performance_monitor,
    ServiceLoggerMixin, create_error_context, operation_context
)


class ServiceStatus(Enum):
    """服务状态枚举"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    INITIALIZING = "initializing"
    SHUTTING_DOWN = "shutting_down"
    CIRCUIT_OPEN = "circuit_open"


class ServiceType(Enum):
    """服务类型枚举"""
    CORE = "core"              # 核心业务服务
    UTILITY = "utility"        # 工具服务
    EXTERNAL = "external"      # 外部依赖服务
    INFRASTRUCTURE = "infrastructure"  # 基础设施服务


class DependencyType(Enum):
    """依赖类型枚举"""
    HARD = "hard"          # 硬依赖，必须可用
    SOFT = "soft"          # 软依赖，可以降级
    OPTIONAL = "optional"   # 可选依赖


@dataclass
class ServiceDependency:
    """服务依赖定义"""
    service_name: str
    dependency_type: DependencyType
    timeout_seconds: float = 30.0
    retry_count: int = 3
    circuit_breaker_enabled: bool = True
    health_check_endpoint: Optional[str] = None


@dataclass
class ServiceMetrics:
    """服务指标数据"""
    request_count: int = 0
    error_count: int = 0
    total_response_time: float = 0.0
    min_response_time: float = float('inf')
    max_response_time: float = 0.0
    last_request_time: Optional[datetime] = None
    last_error_time: Optional[datetime] = None
    circuit_breaker_trips: int = 0
    availability_percentage: float = 100.0
    
    @property
    def average_response_time(self) -> float:
        """平均响应时间"""
        return self.total_response_time / max(self.request_count, 1)
    
    @property
    def error_rate(self) -> float:
        """错误率"""
        return (self.error_count / max(self.request_count, 1)) * 100


@dataclass
class ServiceDefinition:
    """服务定义"""
    name: str
    service_type: ServiceType
    version: str
    description: str
    health_check_url: Optional[str] = None
    dependencies: List[ServiceDependency] = field(default_factory=list)
    tags: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    max_instances: int = 1
    min_instances: int = 1
    auto_scale: bool = False


@dataclass
class ServiceInstance:
    """服务实例"""
    instance_id: str
    service_name: str
    host: str
    port: int
    status: ServiceStatus
    registration_time: datetime
    last_heartbeat: datetime
    metrics: ServiceMetrics = field(default_factory=ServiceMetrics)
    health_data: Dict[str, Any] = field(default_factory=dict)
    load_factor: float = 0.0  # 负载因子 0-1


class CircuitBreakerState(Enum):
    """熔断器状态"""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    """熔断器实现"""
    service_name: str
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    half_open_max_calls: int = 3
    
    # 状态跟踪
    state: CircuitBreakerState = CircuitBreakerState.CLOSED
    failure_count: int = 0
    last_failure_time: Optional[datetime] = None
    half_open_calls: int = 0
    
    def should_allow_request(self) -> bool:
        """是否允许请求通过"""
        now = datetime.now()
        
        if self.state == CircuitBreakerState.CLOSED:
            return True
        elif self.state == CircuitBreakerState.OPEN:
            if (self.last_failure_time and 
                (now - self.last_failure_time).total_seconds() > self.recovery_timeout):
                self.state = CircuitBreakerState.HALF_OPEN
                self.half_open_calls = 0
                return True
            return False
        elif self.state == CircuitBreakerState.HALF_OPEN:
            return self.half_open_calls < self.half_open_max_calls
        
        return False
    
    def record_success(self):
        """记录成功调用"""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.half_open_calls += 1
            if self.half_open_calls >= self.half_open_max_calls:
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
        elif self.state == CircuitBreakerState.CLOSED:
            self.failure_count = max(0, self.failure_count - 1)
    
    def record_failure(self):
        """记录失败调用"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.state == CircuitBreakerState.CLOSED:
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitBreakerState.OPEN
        elif self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.OPEN


class ServiceRegistry:
    """服务注册中心"""
    
    def __init__(self):
        self._services: Dict[str, ServiceDefinition] = {}
        self._instances: Dict[str, List[ServiceInstance]] = defaultdict(list)
        self._lock = threading.RLock()
        self._heartbeat_timeout = 30.0  # 心跳超时时间
    
    def register_service(self, service_def: ServiceDefinition) -> ServiceResult[None]:
        """注册服务定义"""
        with self._lock:
            self._services[service_def.name] = service_def
            if service_def.name not in self._instances:
                self._instances[service_def.name] = []
        
        return ServiceResult.success_result(None)
    
    def register_instance(self, instance: ServiceInstance) -> ServiceResult[None]:
        """注册服务实例"""
        with self._lock:
            # 检查服务是否已定义
            if instance.service_name not in self._services:
                return ServiceResult.error_result(
                    ConfigurationError(f"Service {instance.service_name} not defined")
                )
            
            # 检查实例是否已存在
            existing_instances = self._instances[instance.service_name]
            for i, existing in enumerate(existing_instances):
                if existing.instance_id == instance.instance_id:
                    existing_instances[i] = instance
                    return ServiceResult.success_result(None)
            
            # 添加新实例
            existing_instances.append(instance)
        
        return ServiceResult.success_result(None)
    
    def deregister_instance(self, service_name: str, instance_id: str) -> ServiceResult[None]:
        """注销服务实例"""
        with self._lock:
            if service_name in self._instances:
                instances = self._instances[service_name]
                self._instances[service_name] = [
                    inst for inst in instances if inst.instance_id != instance_id
                ]
        
        return ServiceResult.success_result(None)
    
    def get_healthy_instances(self, service_name: str) -> List[ServiceInstance]:
        """获取健康的服务实例"""
        with self._lock:
            if service_name not in self._instances:
                return []
            
            now = datetime.now()
            healthy_instances = []
            
            for instance in self._instances[service_name]:
                # 检查心跳超时
                if (now - instance.last_heartbeat).total_seconds() > self._heartbeat_timeout:
                    instance.status = ServiceStatus.UNHEALTHY
                
                # 只返回健康的实例
                if instance.status in [ServiceStatus.HEALTHY, ServiceStatus.DEGRADED]:
                    healthy_instances.append(instance)
            
            return healthy_instances
    
    def update_instance_health(self, service_name: str, instance_id: str, 
                             health_data: Dict[str, Any]) -> ServiceResult[None]:
        """更新实例健康状态"""
        with self._lock:
            if service_name not in self._instances:
                return ServiceResult.error_result(
                    ConfigurationError(f"Service {service_name} not found")
                )
            
            for instance in self._instances[service_name]:
                if instance.instance_id == instance_id:
                    instance.health_data = health_data
                    instance.last_heartbeat = datetime.now()
                    
                    # 根据健康数据更新状态
                    if health_data.get('status') == 'healthy':
                        instance.status = ServiceStatus.HEALTHY
                    elif health_data.get('status') == 'degraded':
                        instance.status = ServiceStatus.DEGRADED
                    else:
                        instance.status = ServiceStatus.UNHEALTHY
                    
                    return ServiceResult.success_result(None)
            
            return ServiceResult.error_result(
                ConfigurationError(f"Instance {instance_id} not found")
            )
    
    def get_service_definition(self, service_name: str) -> Optional[ServiceDefinition]:
        """获取服务定义"""
        return self._services.get(service_name)
    
    def list_services(self) -> List[str]:
        """列出所有注册的服务"""
        return list(self._services.keys())


class LoadBalancer:
    """负载均衡器"""
    
    def __init__(self, strategy: str = "round_robin"):
        self.strategy = strategy
        self._round_robin_counters: Dict[str, int] = defaultdict(int)
        self._lock = threading.Lock()
    
    def select_instance(self, instances: List[ServiceInstance]) -> Optional[ServiceInstance]:
        """选择服务实例"""
        if not instances:
            return None
        
        if len(instances) == 1:
            return instances[0]
        
        with self._lock:
            if self.strategy == "round_robin":
                return self._round_robin_select(instances)
            elif self.strategy == "least_loaded":
                return self._least_loaded_select(instances)
            elif self.strategy == "random":
                import random
                return random.choice(instances)
            else:
                return instances[0]
    
    def _round_robin_select(self, instances: List[ServiceInstance]) -> ServiceInstance:
        """轮询选择"""
        service_name = instances[0].service_name
        counter = self._round_robin_counters[service_name]
        selected = instances[counter % len(instances)]
        self._round_robin_counters[service_name] = counter + 1
        return selected
    
    def _least_loaded_select(self, instances: List[ServiceInstance]) -> ServiceInstance:
        """最小负载选择"""
        return min(instances, key=lambda x: x.load_factor)


class ServiceGovernance(ServiceLoggerMixin):
    """企业级服务治理框架"""
    
    def __init__(self):
        super().__init__()
        self.registry = ServiceRegistry()
        self.load_balancer = LoadBalancer()
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.metrics_collectors: Dict[str, ServiceMetrics] = defaultdict(ServiceMetrics)
        
        # 监控配置
        self.health_check_interval = 30.0
        self.metrics_collection_interval = 10.0
        self.cleanup_interval = 300.0  # 5分钟
        
        # 运行状态
        self._monitoring_tasks: Set[asyncio.Task] = set()
        self._shutdown_event = asyncio.Event()
        self._executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="ServiceGov")
        
        # 配置缓存
        self._config_cache: Dict[str, Any] = {}
        self._cache_lock = threading.RLock()
    
    @handle_service_errors("ServiceGovernance", "start")
    async def start(self) -> ServiceResult[None]:
        """启动服务治理框架"""
        self.log_operation_start("start", "Starting service governance framework")
        
        # 启动监控任务
        tasks = [
            self._health_monitoring_loop(),
            self._metrics_collection_loop(),
            self._cleanup_loop()
        ]
        
        for task_coro in tasks:
            task = asyncio.create_task(task_coro)
            self._monitoring_tasks.add(task)
            # 任务完成时自动清理
            task.add_done_callback(self._monitoring_tasks.discard)
        
        self.log_operation_success("start", "Service governance started")
        return ServiceResult.success_result(None)
    
    @handle_service_errors("ServiceGovernance", "stop")
    async def stop(self) -> ServiceResult[None]:
        """停止服务治理框架"""
        self.log_operation_start("stop", "Stopping service governance framework")
        
        # 设置停止信号
        self._shutdown_event.set()
        
        # 等待所有监控任务完成
        if self._monitoring_tasks:
            await asyncio.gather(*self._monitoring_tasks, return_exceptions=True)
        
        # 关闭线程池
        self._executor.shutdown(wait=True)
        
        self.log_operation_success("stop", "Service governance stopped")
        return ServiceResult.success_result(None)
    
    @handle_service_errors("ServiceGovernance", "register_service")
    def register_service(self, service_def: ServiceDefinition) -> ServiceResult[None]:
        """注册服务"""
        # 创建熔断器
        if service_def.name not in self.circuit_breakers:
            self.circuit_breakers[service_def.name] = CircuitBreaker(service_def.name)
        
        # 注册到服务注册中心
        result = self.registry.register_service(service_def)
        if not result.success:
            return result
        
        # 初始化指标收集器
        if service_def.name not in self.metrics_collectors:
            self.metrics_collectors[service_def.name] = ServiceMetrics()
        
        self.log_operation_success("register_service", f"Service {service_def.name} registered")
        return ServiceResult.success_result(None)
    
    @handle_service_errors("ServiceGovernance", "call_service")
    async def call_service(self, service_name: str, operation: Callable, 
                          *args, **kwargs) -> ServiceResult[Any]:
        """调用服务（带治理功能）"""
        start_time = time.time()
        
        # 检查熔断器
        circuit_breaker = self.circuit_breakers.get(service_name)
        if circuit_breaker and not circuit_breaker.should_allow_request():
            error = NetworkError(f"Circuit breaker open for service {service_name}")
            self._record_service_call(service_name, start_time, error)
            return ServiceResult.error_result(error)
        
        # 获取健康实例
        instances = self.registry.get_healthy_instances(service_name)
        if not instances:
            error = NetworkError(f"No healthy instances available for service {service_name}")
            self._record_service_call(service_name, start_time, error)
            return ServiceResult.error_result(error)
        
        # 负载均衡选择实例
        selected_instance = self.load_balancer.select_instance(instances)
        if not selected_instance:
            error = NetworkError(f"Load balancer failed to select instance for service {service_name}")
            self._record_service_call(service_name, start_time, error)
            return ServiceResult.error_result(error)
        
        try:
            # 执行服务调用
            if asyncio.iscoroutinefunction(operation):
                result = await operation(*args, **kwargs)
            else:
                # 在线程池中执行同步操作
                result = await asyncio.get_event_loop().run_in_executor(
                    self._executor, operation, *args, **kwargs
                )
            
            # 记录成功调用
            self._record_service_call(service_name, start_time, None)
            if circuit_breaker:
                circuit_breaker.record_success()
            
            return ServiceResult.success_result(result)
            
        except Exception as e:
            # 记录失败调用
            service_error = SystemError(f"Service call failed: {e}", original_error=e)
            self._record_service_call(service_name, start_time, service_error)
            if circuit_breaker:
                circuit_breaker.record_failure()
            
            return ServiceResult.error_result(service_error)
    
    def _record_service_call(self, service_name: str, start_time: float, error: Optional[ServiceError]):
        """记录服务调用指标"""
        metrics = self.metrics_collectors[service_name]
        metrics.request_count += 1
        metrics.last_request_time = datetime.now()
        
        response_time = (time.time() - start_time) * 1000  # 转换为毫秒
        metrics.total_response_time += response_time
        metrics.min_response_time = min(metrics.min_response_time, response_time)
        metrics.max_response_time = max(metrics.max_response_time, response_time)
        
        if error:
            metrics.error_count += 1
            metrics.last_error_time = datetime.now()
        
        # 更新可用性百分比
        metrics.availability_percentage = ((metrics.request_count - metrics.error_count) / 
                                         max(metrics.request_count, 1)) * 100
    
    @handle_service_errors("ServiceGovernance", "get_service_health")
    async def get_service_health(self, service_name: str) -> ServiceResult[HealthCheckResult]:
        """获取服务健康状态"""
        instances = self.registry.get_healthy_instances(service_name)
        metrics = self.metrics_collectors[service_name]
        circuit_breaker = self.circuit_breakers.get(service_name)
        
        # 计算整体健康状态
        if not instances:
            status = ServiceStatus.UNHEALTHY
            message = "No healthy instances available"
        elif circuit_breaker and circuit_breaker.state == CircuitBreakerState.OPEN:
            status = ServiceStatus.CIRCUIT_OPEN
            message = "Circuit breaker is open"
        elif metrics.error_rate > 50:
            status = ServiceStatus.UNHEALTHY
            message = f"High error rate: {metrics.error_rate:.1f}%"
        elif metrics.error_rate > 10:
            status = ServiceStatus.DEGRADED
            message = f"Elevated error rate: {metrics.error_rate:.1f}%"
        else:
            status = ServiceStatus.HEALTHY
            message = "Service is healthy"
        
        health_result = HealthCheckResult(
            service_name=service_name,
            is_healthy=(status == ServiceStatus.HEALTHY),
            status_message=message,
            details={
                "status": status.value,
                "instance_count": len(instances),
                "metrics": {
                    "request_count": metrics.request_count,
                    "error_count": metrics.error_count,
                    "error_rate": metrics.error_rate,
                    "average_response_time": metrics.average_response_time,
                    "availability_percentage": metrics.availability_percentage
                },
                "circuit_breaker": {
                    "state": circuit_breaker.state.value if circuit_breaker else "disabled",
                    "failure_count": circuit_breaker.failure_count if circuit_breaker else 0
                }
            }
        )
        
        return ServiceResult.success_result(health_result)
    
    @handle_service_errors("ServiceGovernance", "get_all_services_health")
    async def get_all_services_health(self) -> ServiceResult[Dict[str, HealthCheckResult]]:
        """获取所有服务的健康状态"""
        services_health = {}
        
        for service_name in self.registry.list_services():
            health_result = await self.get_service_health(service_name)
            if health_result.success:
                services_health[service_name] = health_result.data
            else:
                # 创建错误健康结果
                services_health[service_name] = HealthCheckResult(
                    service_name=service_name,
                    is_healthy=False,
                    status_message=f"Health check failed: {health_result.error.message}",
                    details={"error": health_result.error.to_dict()}
                )
        
        return ServiceResult.success_result(services_health)
    
    async def _health_monitoring_loop(self):
        """健康监控循环"""
        while not self._shutdown_event.is_set():
            try:
                # 执行健康检查
                await self._perform_health_checks()
                
                # 等待下次检查
                await asyncio.wait_for(
                    self._shutdown_event.wait(), 
                    timeout=self.health_check_interval
                )
            except asyncio.TimeoutError:
                continue  # 正常的超时，继续下一轮检查
            except Exception as e:
                self.log_operation_error("health_monitoring_loop", e)
                await asyncio.sleep(10)  # 错误时短暂等待
    
    async def _perform_health_checks(self):
        """执行健康检查"""
        services = self.registry.list_services()
        
        # 并发执行所有服务的健康检查
        health_check_tasks = [
            self._check_service_health(service_name) 
            for service_name in services
        ]
        
        if health_check_tasks:
            await asyncio.gather(*health_check_tasks, return_exceptions=True)
    
    async def _check_service_health(self, service_name: str):
        """检查单个服务的健康状态"""
        try:
            instances = self.registry.get_healthy_instances(service_name)
            
            # 检查每个实例的健康状态
            for instance in instances:
                # 这里可以添加更复杂的健康检查逻辑
                # 比如HTTP健康检查、依赖检查等
                if instance.health_data.get('last_check_failed', False):
                    instance.status = ServiceStatus.DEGRADED
                
        except Exception as e:
            self.log_operation_error("check_service_health", e)
    
    async def _metrics_collection_loop(self):
        """指标收集循环"""
        while not self._shutdown_event.is_set():
            try:
                # 收集指标
                await self._collect_metrics()
                
                # 等待下次收集
                await asyncio.wait_for(
                    self._shutdown_event.wait(), 
                    timeout=self.metrics_collection_interval
                )
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.log_operation_error("metrics_collection_loop", e)
                await asyncio.sleep(10)
    
    async def _collect_metrics(self):
        """收集服务指标"""
        # 这里可以添加更复杂的指标收集逻辑
        # 比如从监控系统获取CPU、内存、网络等指标
        pass
    
    async def _cleanup_loop(self):
        """清理循环"""
        while not self._shutdown_event.is_set():
            try:
                # 执行清理操作
                await self._cleanup_expired_data()
                
                # 等待下次清理
                await asyncio.wait_for(
                    self._shutdown_event.wait(), 
                    timeout=self.cleanup_interval
                )
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.log_operation_error("cleanup_loop", e)
                await asyncio.sleep(60)
    
    async def _cleanup_expired_data(self):
        """清理过期数据"""
        # 清理过期的服务实例
        # 重置指标计数器
        # 清理缓存等
        pass


# 全局服务治理实例
service_governance = ServiceGovernance()


@contextmanager
def service_context(service_name: str):
    """服务上下文管理器"""
    # 记录服务调用开始
    start_time = time.time()
    
    try:
        yield
        # 记录成功
        service_governance._record_service_call(service_name, start_time, None)
    except Exception as e:
        # 记录失败
        error = SystemError(f"Service operation failed: {e}", original_error=e)
        service_governance._record_service_call(service_name, start_time, error)
        raise


def governed_service(service_name: str):
    """服务治理装饰器"""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            return await service_governance.call_service(service_name, func, *args, **kwargs)
        
        def sync_wrapper(*args, **kwargs):
            with service_context(service_name):
                return func(*args, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator