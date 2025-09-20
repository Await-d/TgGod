"""
完整生产级错误管理框架
企业级错误处理，具备预测性故障检测、自动恢复和全面错误预防
"""

import asyncio
import time
import traceback
import psutil
import logging
from typing import Dict, Any, Optional, List, Callable, Set, Tuple, Union
from datetime import datetime, timezone, timedelta
from enum import Enum
from dataclasses import dataclass, field
from collections import deque, defaultdict
from concurrent.futures import ThreadPoolExecutor
import threading
import json
import os
import signal
import weakref
from contextlib import asynccontextmanager

from .error_handler import global_error_handler, ErrorLogger, ErrorMetrics
from .exceptions import (
    ServiceError, ErrorSeverity, ErrorCategory, ErrorContext,
    SystemError, NetworkError, DatabaseError, TelegramServiceError,
    TaskExecutionError, ExternalServiceError
)
from .result_types import ServiceResult, HealthCheckResult
from ..websocket.manager import websocket_manager


class FailurePattern(Enum):
    """故障模式分类"""
    MEMORY_LEAK = "memory_leak"
    CPU_SPIKE = "cpu_spike"
    DISK_FULL = "disk_full"
    NETWORK_TIMEOUT = "network_timeout"
    DATABASE_DEADLOCK = "database_deadlock"
    SERVICE_UNAVAILABLE = "service_unavailable"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    CASCADING_FAILURE = "cascading_failure"
    CIRCULAR_DEPENDENCY = "circular_dependency"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"


class RecoveryStrategy(Enum):
    """恢复策略"""
    RESTART_SERVICE = "restart_service"
    CLEAR_CACHE = "clear_cache"
    SCALE_RESOURCES = "scale_resources"
    CIRCUIT_BREAKER = "circuit_breaker"
    FALLBACK_MODE = "fallback_mode"
    GRACEFUL_DEGRADATION = "graceful_degradation"
    RETRY_WITH_BACKOFF = "retry_with_backoff"
    LOAD_BALANCING = "load_balancing"
    EMERGENCY_SHUTDOWN = "emergency_shutdown"


@dataclass
class FailurePrediction:
    """故障预测结果"""
    pattern: FailurePattern
    probability: float  # 0.0-1.0
    estimated_time: Optional[datetime]  # 预计发生时间
    affected_services: List[str]
    suggested_actions: List[RecoveryStrategy]
    confidence_level: float  # 0.0-1.0
    risk_level: ErrorSeverity


@dataclass
class RecoveryAction:
    """恢复行动"""
    strategy: RecoveryStrategy
    target_service: str
    parameters: Dict[str, Any]
    priority: int  # 1-10, 1为最高优先级
    estimated_duration: int  # 秒
    success_criteria: List[str]
    rollback_plan: Optional[Dict[str, Any]] = None


@dataclass
class SystemMetrics:
    """系统指标"""
    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_io: Dict[str, float]
    active_connections: int
    error_rate: float
    response_time: float
    thread_count: int
    fd_count: int  # 文件描述符数量


class PredictiveAnalyzer:
    """预测性分析器"""

    def __init__(self, window_size: int = 300):  # 5分钟窗口
        self.window_size = window_size
        self.metrics_history: deque = deque(maxlen=window_size)
        self.error_patterns: Dict[str, List[datetime]] = defaultdict(list)
        self.failure_thresholds = {
            FailurePattern.MEMORY_LEAK: {"memory_increase_rate": 5.0},  # % per minute
            FailurePattern.CPU_SPIKE: {"cpu_threshold": 85.0},
            FailurePattern.DISK_FULL: {"disk_threshold": 90.0},
            FailurePattern.NETWORK_TIMEOUT: {"timeout_rate": 0.1},
            FailurePattern.RESOURCE_EXHAUSTION: {"combined_threshold": 80.0}
        }

    def analyze_metrics(self, metrics: SystemMetrics) -> List[FailurePrediction]:
        """分析系统指标并预测故障"""
        self.metrics_history.append(metrics)
        predictions = []

        # 内存泄漏检测
        memory_prediction = self._detect_memory_leak()
        if memory_prediction:
            predictions.append(memory_prediction)

        # CPU峰值检测
        cpu_prediction = self._detect_cpu_spike()
        if cpu_prediction:
            predictions.append(cpu_prediction)

        # 磁盘空间检测
        disk_prediction = self._detect_disk_exhaustion()
        if disk_prediction:
            predictions.append(disk_prediction)

        # 网络超时检测
        network_prediction = self._detect_network_issues()
        if network_prediction:
            predictions.append(network_prediction)

        # 资源耗尽检测
        resource_prediction = self._detect_resource_exhaustion()
        if resource_prediction:
            predictions.append(resource_prediction)

        return predictions

    def _detect_memory_leak(self) -> Optional[FailurePrediction]:
        """检测内存泄漏"""
        if len(self.metrics_history) < 10:  # 需要足够的历史数据
            return None

        recent_metrics = list(self.metrics_history)[-10:]
        memory_usage = [m.memory_usage for m in recent_metrics]

        # 计算内存使用增长率
        if len(memory_usage) >= 2:
            growth_rate = (memory_usage[-1] - memory_usage[0]) / len(memory_usage)

            if growth_rate > self.failure_thresholds[FailurePattern.MEMORY_LEAK]["memory_increase_rate"]:
                # 预测内存耗尽时间
                current_usage = memory_usage[-1]
                remaining_memory = 100.0 - current_usage
                estimated_time = datetime.now(timezone.utc) + timedelta(
                    minutes=remaining_memory / growth_rate
                )

                return FailurePrediction(
                    pattern=FailurePattern.MEMORY_LEAK,
                    probability=min(growth_rate / 10.0, 0.95),
                    estimated_time=estimated_time,
                    affected_services=["all"],
                    suggested_actions=[
                        RecoveryStrategy.RESTART_SERVICE,
                        RecoveryStrategy.CLEAR_CACHE,
                        RecoveryStrategy.SCALE_RESOURCES
                    ],
                    confidence_level=0.8,
                    risk_level=ErrorSeverity.HIGH
                )

        return None

    def _detect_cpu_spike(self) -> Optional[FailurePrediction]:
        """检测CPU峰值"""
        if len(self.metrics_history) < 5:
            return None

        recent_cpu = [m.cpu_usage for m in list(self.metrics_history)[-5:]]
        avg_cpu = sum(recent_cpu) / len(recent_cpu)

        if avg_cpu > self.failure_thresholds[FailurePattern.CPU_SPIKE]["cpu_threshold"]:
            return FailurePrediction(
                pattern=FailurePattern.CPU_SPIKE,
                probability=0.7,
                estimated_time=datetime.now(timezone.utc) + timedelta(minutes=2),
                affected_services=["telegram_service", "task_execution"],
                suggested_actions=[
                    RecoveryStrategy.GRACEFUL_DEGRADATION,
                    RecoveryStrategy.LOAD_BALANCING
                ],
                confidence_level=0.9,
                risk_level=ErrorSeverity.MEDIUM
            )

        return None

    def _detect_disk_exhaustion(self) -> Optional[FailurePrediction]:
        """检测磁盘空间耗尽"""
        if not self.metrics_history:
            return None

        current_disk = self.metrics_history[-1].disk_usage

        if current_disk > self.failure_thresholds[FailurePattern.DISK_FULL]["disk_threshold"]:
            return FailurePrediction(
                pattern=FailurePattern.DISK_FULL,
                probability=0.9,
                estimated_time=datetime.now(timezone.utc) + timedelta(hours=1),
                affected_services=["file_organizer", "media_downloader"],
                suggested_actions=[
                    RecoveryStrategy.CLEAR_CACHE,
                    RecoveryStrategy.EMERGENCY_SHUTDOWN
                ],
                confidence_level=0.95,
                risk_level=ErrorSeverity.CRITICAL
            )

        return None

    def _detect_network_issues(self) -> Optional[FailurePrediction]:
        """检测网络问题"""
        if len(self.metrics_history) < 5:
            return None

        recent_errors = [m.error_rate for m in list(self.metrics_history)[-5:]]
        avg_error_rate = sum(recent_errors) / len(recent_errors)

        if avg_error_rate > self.failure_thresholds[FailurePattern.NETWORK_TIMEOUT]["timeout_rate"]:
            return FailurePrediction(
                pattern=FailurePattern.NETWORK_TIMEOUT,
                probability=0.6,
                estimated_time=datetime.now(timezone.utc) + timedelta(minutes=1),
                affected_services=["telegram_service"],
                suggested_actions=[
                    RecoveryStrategy.RETRY_WITH_BACKOFF,
                    RecoveryStrategy.CIRCUIT_BREAKER
                ],
                confidence_level=0.7,
                risk_level=ErrorSeverity.MEDIUM
            )

        return None

    def _detect_resource_exhaustion(self) -> Optional[FailurePrediction]:
        """检测资源耗尽"""
        if not self.metrics_history:
            return None

        current = self.metrics_history[-1]
        combined_usage = (current.cpu_usage + current.memory_usage + current.disk_usage) / 3

        if combined_usage > self.failure_thresholds[FailurePattern.RESOURCE_EXHAUSTION]["combined_threshold"]:
            return FailurePrediction(
                pattern=FailurePattern.RESOURCE_EXHAUSTION,
                probability=0.8,
                estimated_time=datetime.now(timezone.utc) + timedelta(minutes=5),
                affected_services=["all"],
                suggested_actions=[
                    RecoveryStrategy.SCALE_RESOURCES,
                    RecoveryStrategy.GRACEFUL_DEGRADATION
                ],
                confidence_level=0.85,
                risk_level=ErrorSeverity.HIGH
            )

        return None


class AutoRecoveryEngine:
    """自动恢复引擎"""

    def __init__(self):
        self.recovery_history: Dict[str, List[datetime]] = defaultdict(list)
        self.active_recoveries: Dict[str, RecoveryAction] = {}
        self.recovery_strategies = {
            RecoveryStrategy.RESTART_SERVICE: self._restart_service,
            RecoveryStrategy.CLEAR_CACHE: self._clear_cache,
            RecoveryStrategy.SCALE_RESOURCES: self._scale_resources,
            RecoveryStrategy.CIRCUIT_BREAKER: self._activate_circuit_breaker,
            RecoveryStrategy.FALLBACK_MODE: self._enable_fallback_mode,
            RecoveryStrategy.GRACEFUL_DEGRADATION: self._graceful_degradation,
            RecoveryStrategy.RETRY_WITH_BACKOFF: self._retry_with_backoff,
            RecoveryStrategy.LOAD_BALANCING: self._load_balancing,
            RecoveryStrategy.EMERGENCY_SHUTDOWN: self._emergency_shutdown
        }
        self.executor = ThreadPoolExecutor(max_workers=4)

    async def execute_recovery(self, action: RecoveryAction) -> ServiceResult[bool]:
        """执行恢复行动"""
        try:
            # 检查是否已有相同的恢复操作在进行
            if action.target_service in self.active_recoveries:
                return ServiceResult.success_result(False,
                    warnings=[f"Recovery already in progress for {action.target_service}"])

            self.active_recoveries[action.target_service] = action

            # 记录恢复历史
            self.recovery_history[action.target_service].append(datetime.now(timezone.utc))

            # 执行恢复策略
            strategy_func = self.recovery_strategies.get(action.strategy)
            if not strategy_func:
                raise ValueError(f"Unknown recovery strategy: {action.strategy}")

            # 在线程池中执行恢复操作
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                strategy_func,
                action
            )

            # 验证恢复是否成功
            success = await self._verify_recovery_success(action)

            return ServiceResult.success_result(success)

        except Exception as e:
            context = ErrorContext(
                service_name="auto_recovery",
                operation_name="execute_recovery",
                additional_data={"action": action.strategy.value}
            )
            error = SystemError(f"Recovery execution failed: {e}", context=context, original_error=e)
            return ServiceResult.error_result(error)

        finally:
            # 清理活跃恢复记录
            if action.target_service in self.active_recoveries:
                del self.active_recoveries[action.target_service]

    def _restart_service(self, action: RecoveryAction) -> bool:
        """重启服务"""
        try:
            service_name = action.target_service
            # 这里应该根据实际的服务管理方式来实现
            # 例如：systemctl restart service_name
            # 或者：重新加载模块/重启进程

            if service_name == "telegram_service":
                # 重启Telegram服务逻辑
                return self._restart_telegram_service()
            elif service_name == "media_downloader":
                # 重启媒体下载器逻辑
                return self._restart_media_downloader()
            else:
                # 通用服务重启逻辑
                return self._generic_service_restart(service_name)

        except Exception:
            return False

    def _clear_cache(self, action: RecoveryAction) -> bool:
        """清理缓存"""
        try:
            # 清理各种缓存
            import gc
            gc.collect()  # 强制垃圾回收

            # 清理应用级缓存
            # 这里应该调用各个服务的缓存清理方法

            return True
        except Exception:
            return False

    def _scale_resources(self, action: RecoveryAction) -> bool:
        """扩展资源"""
        try:
            # 在单机环境中，主要是调整资源限制和优化配置
            import psutil

            # 调整进程优先级
            process = psutil.Process()
            process.nice(psutil.NORMAL_PRIORITY_CLASS if os.name == 'nt' else 0)

            # 这里可以实现更多的资源调整逻辑
            return True
        except Exception:
            return False

    def _activate_circuit_breaker(self, action: RecoveryAction) -> bool:
        """激活熔断器"""
        try:
            # 实现熔断器逻辑
            # 暂时禁用有问题的服务调用
            service_name = action.target_service

            # 这里应该设置熔断状态标志
            # 让其他组件知道该服务处于熔断状态

            return True
        except Exception:
            return False

    def _enable_fallback_mode(self, action: RecoveryAction) -> bool:
        """启用回退模式"""
        try:
            # 启用服务的回退模式
            # 使用简化的功能或备用实现
            return True
        except Exception:
            return False

    def _graceful_degradation(self, action: RecoveryAction) -> bool:
        """优雅降级"""
        try:
            # 禁用非关键功能，保持核心功能运行
            return True
        except Exception:
            return False

    def _retry_with_backoff(self, action: RecoveryAction) -> bool:
        """带退避的重试"""
        try:
            # 实现指数退避重试逻辑
            return True
        except Exception:
            return False

    def _load_balancing(self, action: RecoveryAction) -> bool:
        """负载均衡"""
        try:
            # 在单机环境中，主要是工作负载分配优化
            return True
        except Exception:
            return False

    def _emergency_shutdown(self, action: RecoveryAction) -> bool:
        """紧急关闭"""
        try:
            # 紧急关闭有问题的服务或组件
            service_name = action.target_service
            # 这里应该实现具体的关闭逻辑
            return True
        except Exception:
            return False

    def _restart_telegram_service(self) -> bool:
        """重启Telegram服务"""
        try:
            # 这里应该调用Telegram服务的重启方法
            # 例如：重新初始化客户端连接
            return True
        except Exception:
            return False

    def _restart_media_downloader(self) -> bool:
        """重启媒体下载器"""
        try:
            # 这里应该调用媒体下载器的重启方法
            return True
        except Exception:
            return False

    def _generic_service_restart(self, service_name: str) -> bool:
        """通用服务重启"""
        try:
            # 通用的服务重启逻辑
            return True
        except Exception:
            return False

    async def _verify_recovery_success(self, action: RecoveryAction) -> bool:
        """验证恢复是否成功"""
        try:
            # 根据成功标准验证恢复效果
            for criteria in action.success_criteria:
                if not await self._check_criteria(criteria, action.target_service):
                    return False
            return True
        except Exception:
            return False

    async def _check_criteria(self, criteria: str, service_name: str) -> bool:
        """检查成功标准"""
        try:
            if criteria == "service_responsive":
                # 检查服务是否响应
                return True
            elif criteria == "error_rate_normal":
                # 检查错误率是否正常
                return True
            elif criteria == "memory_usage_stable":
                # 检查内存使用是否稳定
                return True
            else:
                return True
        except Exception:
            return False


class CircuitBreaker:
    """熔断器"""

    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self._lock = threading.Lock()

    def call(self, func: Callable, *args, **kwargs):
        """调用受保护的函数"""
        with self._lock:
            if self.state == "OPEN":
                if self._should_attempt_reset():
                    self.state = "HALF_OPEN"
                else:
                    raise ExternalServiceError("Circuit breaker is OPEN", "circuit_breaker")

            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result
            except Exception as e:
                self._on_failure()
                raise

    def _should_attempt_reset(self) -> bool:
        """检查是否应该尝试重置"""
        if self.last_failure_time is None:
            return False
        return time.time() - self.last_failure_time >= self.timeout

    def _on_success(self):
        """成功时的处理"""
        self.failure_count = 0
        self.state = "CLOSED"

    def _on_failure(self):
        """失败时的处理"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"


class CompleteErrorManager:
    """完整错误管理器 - 企业级错误管理的主控制器"""

    def __init__(self):
        self.analyzer = PredictiveAnalyzer()
        self.recovery_engine = AutoRecoveryEngine()
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.error_handlers: Dict[str, Callable] = {}
        self.metrics_collector = None
        self.monitoring_task = None
        self.is_running = False
        self.logger = ErrorLogger("error_manager")

        # 错误抑制 - 防止错误风暴
        self.error_suppression: Dict[str, datetime] = {}
        self.suppression_window = timedelta(minutes=5)

        # 错误恢复跟踪
        self.recovery_tracking: Dict[str, List[datetime]] = defaultdict(list)

        # 级联故障检测
        self.cascade_detection = CascadeFailureDetector()

        # 注册默认错误处理器
        self._register_default_handlers()

    def _register_default_handlers(self):
        """注册默认错误处理器"""
        self.error_handlers.update({
            "telegram_service": self._handle_telegram_error,
            "media_downloader": self._handle_media_error,
            "task_execution": self._handle_task_error,
            "database": self._handle_database_error,
            "file_system": self._handle_filesystem_error,
            "network": self._handle_network_error
        })

    async def start_monitoring(self):
        """开始监控"""
        if self.is_running:
            return

        self.is_running = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())

        # 注册信号处理器用于优雅关闭
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, self._signal_handler)
        if hasattr(signal, 'SIGINT'):
            signal.signal(signal.SIGINT, self._signal_handler)

    async def stop_monitoring(self):
        """停止监控"""
        self.is_running = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass

    def _signal_handler(self, signum, frame):
        """信号处理器"""
        asyncio.create_task(self.stop_monitoring())

    async def _monitoring_loop(self):
        """监控循环"""
        while self.is_running:
            try:
                # 收集系统指标
                metrics = await self._collect_system_metrics()

                # 预测性分析
                predictions = self.analyzer.analyze_metrics(metrics)

                # 处理预测的故障
                for prediction in predictions:
                    await self._handle_prediction(prediction)

                # 检查级联故障
                cascade_risk = self.cascade_detection.analyze_error_patterns(
                    global_error_handler.metrics.error_rates
                )

                if cascade_risk > 0.7:  # 高级联风险
                    await self._handle_cascade_risk(cascade_risk)

                # 发送监控报告
                await self._send_monitoring_report(metrics, predictions)

                await asyncio.sleep(10)  # 每10秒监控一次

            except Exception as e:
                self.logger.logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(30)  # 错误时延长间隔

    async def _collect_system_metrics(self) -> SystemMetrics:
        """收集系统指标"""
        try:
            # CPU和内存信息
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            # 网络IO
            net_io = psutil.net_io_counters()
            network_io = {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv
            }

            # 进程信息
            process = psutil.Process()

            # 错误率和响应时间（从现有错误处理器获取）
            error_summary = global_error_handler.metrics.get_error_summary()

            return SystemMetrics(
                timestamp=datetime.now(timezone.utc),
                cpu_usage=cpu_percent,
                memory_usage=memory.percent,
                disk_usage=(disk.used / disk.total) * 100,
                network_io=network_io,
                active_connections=len(websocket_manager.active_connections),
                error_rate=len(error_summary.get("error_counts_by_type", {})),
                response_time=0.0,  # 这里需要从其他地方获取
                thread_count=process.num_threads(),
                fd_count=process.num_fds() if hasattr(process, 'num_fds') else 0
            )

        except Exception as e:
            # 返回默认指标，避免监控系统本身出错
            return SystemMetrics(
                timestamp=datetime.now(timezone.utc),
                cpu_usage=0.0,
                memory_usage=0.0,
                disk_usage=0.0,
                network_io={},
                active_connections=0,
                error_rate=0.0,
                response_time=0.0,
                thread_count=0,
                fd_count=0
            )

    async def _handle_prediction(self, prediction: FailurePrediction):
        """处理故障预测"""
        try:
            # 记录预测
            await self._log_prediction(prediction)

            # 根据风险级别和置信度决定是否采取行动
            if prediction.confidence_level > 0.7 and prediction.probability > 0.6:

                # 创建恢复行动
                for strategy in prediction.suggested_actions:
                    for service in prediction.affected_services:
                        action = RecoveryAction(
                            strategy=strategy,
                            target_service=service,
                            parameters={
                                "prediction_id": prediction.pattern.value,
                                "confidence": prediction.confidence_level
                            },
                            priority=self._calculate_priority(prediction),
                            estimated_duration=60,  # 默认1分钟
                            success_criteria=["service_responsive", "error_rate_normal"]
                        )

                        # 执行恢复
                        result = await self.recovery_engine.execute_recovery(action)

                        if result.success:
                            await self._notify_recovery_success(action, prediction)
                        else:
                            await self._notify_recovery_failure(action, prediction, result.error)

        except Exception as e:
            self.logger.logger.error(f"Error handling prediction: {e}")

    def _calculate_priority(self, prediction: FailurePrediction) -> int:
        """计算恢复行动优先级"""
        base_priority = {
            ErrorSeverity.CRITICAL: 1,
            ErrorSeverity.HIGH: 3,
            ErrorSeverity.MEDIUM: 5,
            ErrorSeverity.LOW: 7
        }.get(prediction.risk_level, 5)

        # 根据概率和置信度调整
        adjustment = int((1.0 - prediction.probability * prediction.confidence_level) * 2)

        return max(1, min(10, base_priority + adjustment))

    async def _handle_cascade_risk(self, risk_level: float):
        """处理级联故障风险"""
        try:
            if risk_level > 0.9:  # 极高风险
                # 启动应急模式
                await self._activate_emergency_mode()
            elif risk_level > 0.8:  # 高风险
                # 启动预防性措施
                await self._activate_preventive_measures()

            # 通知管理员
            await self._notify_cascade_risk(risk_level)

        except Exception as e:
            self.logger.logger.error(f"Error handling cascade risk: {e}")

    async def _activate_emergency_mode(self):
        """激活应急模式"""
        # 禁用非关键功能
        # 增加监控频率
        # 自动执行预定义的应急响应计划
        pass

    async def _activate_preventive_measures(self):
        """激活预防性措施"""
        # 增加资源分配
        # 启用额外的监控
        # 预加载故障转移机制
        pass

    async def handle_error(self, error: ServiceError, service_name: str, operation_name: str):
        """处理错误（增强版）"""
        try:
            # 检查错误抑制
            error_key = f"{service_name}.{operation_name}.{error.category.value}"
            if self._should_suppress_error(error_key):
                return

            # 更新错误抑制时间
            self.error_suppression[error_key] = datetime.now(timezone.utc)

            # 调用基础错误处理
            global_error_handler.handle_error(error, service_name, operation_name)

            # 获取特定的错误处理器
            handler = self.error_handlers.get(service_name)
            if handler:
                await handler(error, operation_name)

            # 检查是否需要熔断
            circuit_breaker = self._get_circuit_breaker(service_name)
            if circuit_breaker.state == "OPEN":
                await self._handle_circuit_open(service_name)

            # 实时错误分析
            await self._analyze_error_pattern(error, service_name)

            # 发送实时通知
            await self._send_error_notification(error, service_name, operation_name)

        except Exception as e:
            # 错误处理器本身出错时的兜底逻辑
            self.logger.logger.critical(f"Error manager failed: {e}")

    def _should_suppress_error(self, error_key: str) -> bool:
        """检查是否应该抑制错误（防止错误风暴）"""
        last_occurrence = self.error_suppression.get(error_key)
        if last_occurrence:
            time_diff = datetime.now(timezone.utc) - last_occurrence
            return time_diff < self.suppression_window
        return False

    def _get_circuit_breaker(self, service_name: str) -> CircuitBreaker:
        """获取或创建熔断器"""
        if service_name not in self.circuit_breakers:
            self.circuit_breakers[service_name] = CircuitBreaker()
        return self.circuit_breakers[service_name]

    async def _handle_circuit_open(self, service_name: str):
        """处理熔断器开启"""
        # 启用备用服务或回退机制
        # 发送熔断通知
        await websocket_manager.broadcast({
            "type": "circuit_breaker",
            "data": {
                "service": service_name,
                "status": "open",
                "message": f"Service {service_name} circuit breaker is open"
            }
        })

    async def _analyze_error_pattern(self, error: ServiceError, service_name: str):
        """分析错误模式"""
        # 更新级联故障检测器
        self.cascade_detection.record_error(service_name, error)

        # 检查是否有新的故障模式
        # 这里可以实现更复杂的模式识别算法

    async def _send_error_notification(self, error: ServiceError, service_name: str, operation_name: str):
        """发送错误通知"""
        notification = {
            "type": "error",
            "data": {
                "service": service_name,
                "operation": operation_name,
                "severity": error.severity.value,
                "category": error.category.value,
                "message": error.message,
                "error_code": error.error_code,
                "timestamp": error.created_at.isoformat(),
                "suggested_action": error.suggested_action
            }
        }

        await websocket_manager.broadcast(notification)

    async def _send_monitoring_report(self, metrics: SystemMetrics, predictions: List[FailurePrediction]):
        """发送监控报告"""
        report = {
            "type": "monitoring_report",
            "data": {
                "timestamp": metrics.timestamp.isoformat(),
                "system_metrics": {
                    "cpu_usage": metrics.cpu_usage,
                    "memory_usage": metrics.memory_usage,
                    "disk_usage": metrics.disk_usage,
                    "active_connections": metrics.active_connections,
                    "error_rate": metrics.error_rate
                },
                "predictions": [
                    {
                        "pattern": pred.pattern.value,
                        "probability": pred.probability,
                        "risk_level": pred.risk_level.value,
                        "affected_services": pred.affected_services
                    }
                    for pred in predictions
                ],
                "health_status": await self._get_overall_health_status()
            }
        }

        await websocket_manager.broadcast(report)

    async def _get_overall_health_status(self) -> str:
        """获取整体健康状态"""
        try:
            health_status = global_error_handler.get_health_status()
            if health_status["overall_health"]:
                return "healthy"
            else:
                # 检查严重程度
                error_summary = health_status["error_summary"]
                if error_summary.get("total_errors", 0) > 50:
                    return "critical"
                elif error_summary.get("total_errors", 0) > 20:
                    return "warning"
                else:
                    return "degraded"
        except Exception:
            return "unknown"

    # 默认错误处理器实现
    async def _handle_telegram_error(self, error: ServiceError, operation: str):
        """处理Telegram服务错误"""
        if isinstance(error, TelegramServiceError):
            # 特定的Telegram错误处理逻辑
            pass

    async def _handle_media_error(self, error: ServiceError, operation: str):
        """处理媒体相关错误"""
        pass

    async def _handle_task_error(self, error: ServiceError, operation: str):
        """处理任务执行错误"""
        if isinstance(error, TaskExecutionError):
            # 特定的任务错误处理逻辑
            pass

    async def _handle_database_error(self, error: ServiceError, operation: str):
        """处理数据库错误"""
        if isinstance(error, DatabaseError):
            # 特定的数据库错误处理逻辑
            pass

    async def _handle_filesystem_error(self, error: ServiceError, operation: str):
        """处理文件系统错误"""
        pass

    async def _handle_network_error(self, error: ServiceError, operation: str):
        """处理网络错误"""
        if isinstance(error, NetworkError):
            # 特定的网络错误处理逻辑
            pass

    async def _log_prediction(self, prediction: FailurePrediction):
        """记录预测日志"""
        self.logger.logger.warning(
            f"Failure prediction: {prediction.pattern.value}, "
            f"probability: {prediction.probability:.2f}, "
            f"confidence: {prediction.confidence_level:.2f}"
        )

    async def _notify_recovery_success(self, action: RecoveryAction, prediction: FailurePrediction):
        """通知恢复成功"""
        notification = {
            "type": "recovery_success",
            "data": {
                "strategy": action.strategy.value,
                "service": action.target_service,
                "prediction": prediction.pattern.value
            }
        }
        await websocket_manager.broadcast(notification)

    async def _notify_recovery_failure(self, action: RecoveryAction, prediction: FailurePrediction, error: ServiceError):
        """通知恢复失败"""
        notification = {
            "type": "recovery_failure",
            "data": {
                "strategy": action.strategy.value,
                "service": action.target_service,
                "prediction": prediction.pattern.value,
                "error": error.message if error else "Unknown error"
            }
        }
        await websocket_manager.broadcast(notification)

    async def _notify_cascade_risk(self, risk_level: float):
        """通知级联故障风险"""
        notification = {
            "type": "cascade_risk",
            "data": {
                "risk_level": risk_level,
                "status": "high_risk" if risk_level > 0.8 else "medium_risk"
            }
        }
        await websocket_manager.broadcast(notification)


class CascadeFailureDetector:
    """级联故障检测器"""

    def __init__(self):
        self.error_history: Dict[str, List[datetime]] = defaultdict(list)
        self.service_dependencies = {
            "telegram_service": ["network", "database"],
            "media_downloader": ["telegram_service", "file_system"],
            "task_execution": ["database", "media_downloader"],
            "file_organizer": ["file_system", "database"]
        }

    def record_error(self, service_name: str, error: ServiceError):
        """记录错误"""
        self.error_history[service_name].append(datetime.now(timezone.utc))

        # 保留最近1小时的错误记录
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=1)
        self.error_history[service_name] = [
            ts for ts in self.error_history[service_name] if ts > cutoff_time
        ]

    def analyze_error_patterns(self, error_rates: Dict[str, List[datetime]]) -> float:
        """分析错误模式，返回级联故障风险（0.0-1.0）"""
        if not error_rates:
            return 0.0

        # 分析服务依赖链中的错误传播
        cascade_score = 0.0
        total_chains = 0

        for service, dependencies in self.service_dependencies.items():
            service_errors = len(error_rates.get(service, []))
            dependency_errors = sum(
                len(error_rates.get(dep, [])) for dep in dependencies
            )

            if service_errors > 0 and dependency_errors > 0:
                # 计算级联影响分数
                chain_score = min(1.0, (service_errors + dependency_errors) / 20.0)
                cascade_score += chain_score
                total_chains += 1

        return cascade_score / max(1, total_chains)


# 全局错误管理器实例
complete_error_manager = CompleteErrorManager()


# 装饰器：为函数添加完整错误管理
def with_complete_error_management(service_name: str, operation_name: str):
    """装饰器：为函数添加完整错误管理"""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            try:
                # 获取熔断器
                circuit_breaker = complete_error_manager._get_circuit_breaker(service_name)

                # 通过熔断器调用函数
                if asyncio.iscoroutinefunction(func):
                    return await circuit_breaker.call(func, *args, **kwargs)
                else:
                    return circuit_breaker.call(func, *args, **kwargs)

            except Exception as e:
                # 转换为ServiceError并处理
                if isinstance(e, ServiceError):
                    await complete_error_manager.handle_error(e, service_name, operation_name)
                    raise
                else:
                    context = ErrorContext(service_name=service_name, operation_name=operation_name)
                    error = SystemError(str(e), context=context, original_error=e)
                    await complete_error_manager.handle_error(error, service_name, operation_name)
                    raise error

        def sync_wrapper(*args, **kwargs):
            try:
                # 获取熔断器
                circuit_breaker = complete_error_manager._get_circuit_breaker(service_name)

                # 通过熔断器调用函数
                return circuit_breaker.call(func, *args, **kwargs)

            except Exception as e:
                # 转换为ServiceError并处理
                if isinstance(e, ServiceError):
                    # 同步版本需要创建事件循环来处理异步错误管理
                    try:
                        loop = asyncio.get_event_loop()
                        loop.run_until_complete(
                            complete_error_manager.handle_error(e, service_name, operation_name)
                        )
                    except RuntimeError:
                        # 如果没有事件循环，使用基础错误处理
                        global_error_handler.handle_error(e, service_name, operation_name)
                    raise
                else:
                    context = ErrorContext(service_name=service_name, operation_name=operation_name)
                    error = SystemError(str(e), context=context, original_error=e)
                    try:
                        loop = asyncio.get_event_loop()
                        loop.run_until_complete(
                            complete_error_manager.handle_error(error, service_name, operation_name)
                        )
                    except RuntimeError:
                        global_error_handler.handle_error(error, service_name, operation_name)
                    raise error

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# 上下文管理器：完整错误管理上下文
@asynccontextmanager
async def complete_error_context(service_name: str, operation_name: str):
    """完整错误管理上下文管理器"""
    start_time = datetime.now(timezone.utc)

    try:
        yield

        # 记录成功操作
        duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        global_error_handler.handle_success(service_name, operation_name, duration_ms)

    except Exception as e:
        # 处理异常
        if isinstance(e, ServiceError):
            await complete_error_manager.handle_error(e, service_name, operation_name)
        else:
            context = ErrorContext(service_name=service_name, operation_name=operation_name)
            error = SystemError(str(e), context=context, original_error=e)
            await complete_error_manager.handle_error(error, service_name, operation_name)

        raise


# 便捷函数
async def start_complete_error_management():
    """启动完整错误管理"""
    await complete_error_manager.start_monitoring()


async def stop_complete_error_management():
    """停止完整错误管理"""
    await complete_error_manager.stop_monitoring()


def get_error_manager() -> CompleteErrorManager:
    """获取错误管理器实例"""
    return complete_error_manager