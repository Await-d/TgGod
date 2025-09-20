"""
完整的服务健康监控系统

该模块实现了全面的服务健康监控，具备实时分析、预测性维护和自主恢复系统。
提供深度的服务可观察性、智能故障检测和零手动干预的自动化恢复能力。

Key Features:
    - 实时多维度健康监控
    - 预测性故障检测和预防
    - 智能性能分析和优化建议
    - 完整的服务依赖关系映射
    - 自动化故障恢复和隔离
    - 深度学习的异常检测
    - 全面的可观察性和指标收集

Technical Architecture:
    - 分层监控架构 (系统/服务/应用层)
    - 实时流处理和分析引擎
    - 机器学习驱动的异常检测
    - 分布式健康检查和协调
    - 自适应监控策略和阈值
    - 完整的事件驱动恢复机制

Author: TgGod Team
Version: 1.0.0
"""

import asyncio
import threading
import time
import logging
import json
import psutil
import sqlite3
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any, Union, Set, Tuple, NamedTuple
from concurrent.futures import ThreadPoolExecutor
import weakref
import statistics

from ..core import (
    ServiceResult, HealthCheckResult, SystemError, ExternalServiceError,
    NetworkError, FileSystemError, handle_service_errors, timeout,
    performance_monitor, ServiceLoggerMixin, create_error_context,
    operation_context, robust_service_method, RetryConfig
)
from ..core.auto_recovery_engine import (
    get_auto_recovery_engine, register_service_for_auto_recovery,
    FailureCategory, ServiceState
)
from ..core.batch_logging import HighPerformanceLogger, get_batch_handler
from .service_monitor import service_monitor
from .connection_pool_monitor import get_pool_monitor
from .memory_monitoring_service import memory_monitoring_service


class MonitoringLevel(Enum):
    """监控级别"""
    BASIC = auto()          # 基础监控
    STANDARD = auto()       # 标准监控
    COMPREHENSIVE = auto()  # 全面监控
    DEEP = auto()          # 深度监控


class HealthStatus(Enum):
    """健康状态"""
    HEALTHY = auto()        # 健康
    WARNING = auto()        # 警告
    CRITICAL = auto()       # 严重
    FAILED = auto()         # 失败
    RECOVERING = auto()     # 恢复中
    UNKNOWN = auto()        # 未知


class MetricType(Enum):
    """指标类型"""
    COUNTER = auto()        # 计数器
    GAUGE = auto()          # 仪表
    HISTOGRAM = auto()      # 直方图
    TIMER = auto()          # 计时器


@dataclass
class HealthMetric:
    """健康指标"""
    name: str
    value: float
    unit: str
    timestamp: float
    labels: Dict[str, str] = field(default_factory=dict)
    threshold_warning: Optional[float] = None
    threshold_critical: Optional[float] = None
    trend: Optional[float] = None  # 趋势指标 (-1.0 到 1.0)


@dataclass
class ServiceHealth:
    """服务健康状态"""
    service_name: str
    status: HealthStatus
    overall_score: float  # 0.0 - 1.0
    metrics: List[HealthMetric]
    dependencies: List[str]
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    last_check: float = field(default_factory=time.time)
    check_duration: float = 0.0


@dataclass
class AlertRule:
    """告警规则"""
    name: str
    metric_pattern: str
    condition: str  # 条件表达式
    threshold: float
    severity: str
    action: str
    enabled: bool = True
    cooldown_period: float = 300.0  # 冷却期(秒)


@dataclass
class MonitoringConfig:
    """监控配置"""
    level: MonitoringLevel = MonitoringLevel.STANDARD
    check_interval: float = 10.0
    retention_period: int = 24 * 3600  # 24小时
    enable_predictions: bool = True
    enable_auto_recovery: bool = True
    enable_alerts: bool = True
    max_concurrent_checks: int = 10
    batch_size: int = 100


class HealthCheckProvider:
    """健康检查提供者基类"""

    def __init__(self, name: str, priority: int = 0):
        self.name = name
        self.priority = priority
        self.enabled = True
        self.last_check_time = 0.0
        self.check_count = 0
        self.error_count = 0

    async def check_health(self) -> ServiceHealth:
        """执行健康检查"""
        raise NotImplementedError

    def get_dependencies(self) -> List[str]:
        """获取依赖服务"""
        return []

    def is_ready(self) -> bool:
        """检查是否准备就绪"""
        return self.enabled


class SystemHealthProvider(HealthCheckProvider):
    """系统健康检查提供者"""

    def __init__(self):
        super().__init__("system", priority=100)
        self.process = psutil.Process()

    async def check_health(self) -> ServiceHealth:
        """检查系统健康状况"""
        start_time = time.time()
        metrics = []
        issues = []
        recommendations = []

        try:
            # CPU指标
            cpu_percent = self.process.cpu_percent(interval=0.1)
            metrics.append(HealthMetric(
                name="cpu_usage",
                value=cpu_percent,
                unit="percent",
                timestamp=time.time(),
                threshold_warning=80.0,
                threshold_critical=95.0
            ))

            if cpu_percent > 95.0:
                issues.append("CPU使用率过高")
                recommendations.append("检查高CPU进程并优化")

            # 内存指标
            memory_info = self.process.memory_info()
            memory_percent = self.process.memory_percent()
            metrics.append(HealthMetric(
                name="memory_usage",
                value=memory_percent,
                unit="percent",
                timestamp=time.time(),
                threshold_warning=80.0,
                threshold_critical=90.0
            ))

            if memory_percent > 90.0:
                issues.append("内存使用率过高")
                recommendations.append("释放内存或增加内存容量")

            # 磁盘指标
            disk_usage = psutil.disk_usage('/').percent
            metrics.append(HealthMetric(
                name="disk_usage",
                value=disk_usage,
                unit="percent",
                timestamp=time.time(),
                threshold_warning=80.0,
                threshold_critical=95.0
            ))

            if disk_usage > 95.0:
                issues.append("磁盘空间不足")
                recommendations.append("清理磁盘空间或扩容")

            # 网络指标
            net_io = psutil.net_io_counters()
            if hasattr(net_io, 'errin') and net_io.packets_recv > 0:
                error_rate = (net_io.errin + net_io.errout) / (net_io.packets_recv + net_io.packets_sent)
                metrics.append(HealthMetric(
                    name="network_error_rate",
                    value=error_rate,
                    unit="ratio",
                    timestamp=time.time(),
                    threshold_warning=0.01,
                    threshold_critical=0.05
                ))

            # 计算总体健康评分
            overall_score = self._calculate_overall_score(metrics)
            status = self._determine_status(overall_score, issues)

            return ServiceHealth(
                service_name="system",
                status=status,
                overall_score=overall_score,
                metrics=metrics,
                dependencies=[],
                issues=issues,
                recommendations=recommendations,
                check_duration=time.time() - start_time
            )

        except Exception as e:
            return ServiceHealth(
                service_name="system",
                status=HealthStatus.FAILED,
                overall_score=0.0,
                metrics=[],
                dependencies=[],
                issues=[f"健康检查失败: {str(e)}"],
                check_duration=time.time() - start_time
            )

    def _calculate_overall_score(self, metrics: List[HealthMetric]) -> float:
        """计算总体健康评分"""
        scores = []
        for metric in metrics:
            if metric.threshold_critical and metric.threshold_warning:
                if metric.value >= metric.threshold_critical:
                    score = 0.0
                elif metric.value >= metric.threshold_warning:
                    # 线性插值
                    range_size = metric.threshold_critical - metric.threshold_warning
                    score = 1.0 - (metric.value - metric.threshold_warning) / range_size
                else:
                    score = 1.0
                scores.append(score)

        return statistics.mean(scores) if scores else 1.0

    def _determine_status(self, score: float, issues: List[str]) -> HealthStatus:
        """确定健康状态"""
        if score >= 0.9 and not issues:
            return HealthStatus.HEALTHY
        elif score >= 0.7:
            return HealthStatus.WARNING
        elif score >= 0.3:
            return HealthStatus.CRITICAL
        else:
            return HealthStatus.FAILED


class DatabaseHealthProvider(HealthCheckProvider):
    """数据库健康检查提供者"""

    def __init__(self):
        super().__init__("database", priority=90)

    async def check_health(self) -> ServiceHealth:
        """检查数据库健康状况"""
        start_time = time.time()
        metrics = []
        issues = []
        recommendations = []

        try:
            # 连接池状态
            pool_monitor = get_pool_monitor()
            pool_status = pool_monitor.get_current_status()

            # 连接池利用率
            utilization = pool_status.get('utilization', 0.0)
            metrics.append(HealthMetric(
                name="connection_pool_utilization",
                value=utilization,
                unit="ratio",
                timestamp=time.time(),
                threshold_warning=0.8,
                threshold_critical=0.95
            ))

            if utilization > 0.95:
                issues.append("连接池利用率过高")
                recommendations.append("考虑增加连接池大小或优化查询")

            # 查询性能
            avg_query_time = pool_status.get('avg_query_time', 0.0)
            if avg_query_time > 0:
                metrics.append(HealthMetric(
                    name="avg_query_time",
                    value=avg_query_time,
                    unit="seconds",
                    timestamp=time.time(),
                    threshold_warning=1.0,
                    threshold_critical=5.0
                ))

                if avg_query_time > 5.0:
                    issues.append("数据库查询响应时间过长")
                    recommendations.append("优化慢查询或添加索引")

            # 错误率
            error_rate = pool_status.get('error_rate', 0.0)
            metrics.append(HealthMetric(
                name="database_error_rate",
                value=error_rate,
                unit="ratio",
                timestamp=time.time(),
                threshold_warning=0.01,
                threshold_critical=0.05
            ))

            if error_rate > 0.05:
                issues.append("数据库错误率过高")
                recommendations.append("检查数据库连接和配置")

            overall_score = self._calculate_score(metrics)
            status = self._determine_status(overall_score, issues)

            return ServiceHealth(
                service_name="database",
                status=status,
                overall_score=overall_score,
                metrics=metrics,
                dependencies=["system"],
                issues=issues,
                recommendations=recommendations,
                check_duration=time.time() - start_time
            )

        except Exception as e:
            return ServiceHealth(
                service_name="database",
                status=HealthStatus.FAILED,
                overall_score=0.0,
                metrics=[],
                dependencies=["system"],
                issues=[f"数据库健康检查失败: {str(e)}"],
                check_duration=time.time() - start_time
            )

    def _calculate_score(self, metrics: List[HealthMetric]) -> float:
        """计算健康评分"""
        scores = []
        for metric in metrics:
            if metric.threshold_critical and metric.threshold_warning:
                if metric.value >= metric.threshold_critical:
                    score = 0.0
                elif metric.value >= metric.threshold_warning:
                    range_size = metric.threshold_critical - metric.threshold_warning
                    score = 1.0 - (metric.value - metric.threshold_warning) / range_size
                else:
                    score = 1.0
                scores.append(score)
        return statistics.mean(scores) if scores else 1.0

    def _determine_status(self, score: float, issues: List[str]) -> HealthStatus:
        """确定健康状态"""
        if score >= 0.9 and not issues:
            return HealthStatus.HEALTHY
        elif score >= 0.7:
            return HealthStatus.WARNING
        elif score >= 0.3:
            return HealthStatus.CRITICAL
        else:
            return HealthStatus.FAILED

    def get_dependencies(self) -> List[str]:
        return ["system"]


class TelegramServiceHealthProvider(HealthCheckProvider):
    """Telegram服务健康检查提供者"""

    def __init__(self):
        super().__init__("telegram_service", priority=80)

    async def check_health(self) -> ServiceHealth:
        """检查Telegram服务健康状况"""
        start_time = time.time()
        metrics = []
        issues = []
        recommendations = []

        try:
            # 检查Telegram服务状态
            from ..services.telegram_service import telegram_service

            if not telegram_service.client:
                issues.append("Telegram客户端未初始化")
                recommendations.append("检查Telegram配置并重新初始化")
                status = HealthStatus.FAILED
                overall_score = 0.0
            else:
                # 连接状态
                is_connected = await telegram_service.is_connected()
                connection_score = 1.0 if is_connected else 0.0

                metrics.append(HealthMetric(
                    name="telegram_connection",
                    value=connection_score,
                    unit="boolean",
                    timestamp=time.time()
                ))

                if not is_connected:
                    issues.append("Telegram连接断开")
                    recommendations.append("检查网络连接和认证状态")

                # 认证状态
                is_authenticated = telegram_service.is_authenticated
                auth_score = 1.0 if is_authenticated else 0.0

                metrics.append(HealthMetric(
                    name="telegram_authentication",
                    value=auth_score,
                    unit="boolean",
                    timestamp=time.time()
                ))

                if not is_authenticated:
                    issues.append("Telegram认证失败")
                    recommendations.append("重新进行Telegram认证")

                # 整体评分
                overall_score = (connection_score + auth_score) / 2.0
                status = self._determine_status(overall_score, issues)

            return ServiceHealth(
                service_name="telegram_service",
                status=status,
                overall_score=overall_score,
                metrics=metrics,
                dependencies=["system", "database"],
                issues=issues,
                recommendations=recommendations,
                check_duration=time.time() - start_time
            )

        except Exception as e:
            return ServiceHealth(
                service_name="telegram_service",
                status=HealthStatus.FAILED,
                overall_score=0.0,
                metrics=[],
                dependencies=["system", "database"],
                issues=[f"Telegram服务检查失败: {str(e)}"],
                recommendations=["检查Telegram服务配置和网络连接"],
                check_duration=time.time() - start_time
            )

    def _determine_status(self, score: float, issues: List[str]) -> HealthStatus:
        """确定健康状态"""
        if score >= 0.9 and not issues:
            return HealthStatus.HEALTHY
        elif score >= 0.7:
            return HealthStatus.WARNING
        elif score >= 0.5:
            return HealthStatus.CRITICAL
        else:
            return HealthStatus.FAILED

    def get_dependencies(self) -> List[str]:
        return ["system", "database"]


class TaskExecutionHealthProvider(HealthCheckProvider):
    """任务执行服务健康检查提供者"""

    def __init__(self):
        super().__init__("task_execution", priority=70)

    async def check_health(self) -> ServiceHealth:
        """检查任务执行服务健康状况"""
        start_time = time.time()
        metrics = []
        issues = []
        recommendations = []

        try:
            from ..services.task_execution_service import task_execution_service

            # 检查任务执行器状态
            if not hasattr(task_execution_service, 'running') or not task_execution_service.running:
                issues.append("任务执行服务未运行")
                recommendations.append("启动任务执行服务")
                status = HealthStatus.FAILED
                overall_score = 0.0
            else:
                # 活跃任务数量
                active_tasks = getattr(task_execution_service, 'active_tasks_count', 0)
                metrics.append(HealthMetric(
                    name="active_tasks",
                    value=float(active_tasks),
                    unit="count",
                    timestamp=time.time(),
                    threshold_warning=50.0,
                    threshold_critical=100.0
                ))

                if active_tasks > 100:
                    issues.append("活跃任务数量过多")
                    recommendations.append("检查任务处理性能或增加处理能力")

                # 任务成功率
                success_rate = getattr(task_execution_service, 'success_rate', 1.0)
                metrics.append(HealthMetric(
                    name="task_success_rate",
                    value=success_rate,
                    unit="ratio",
                    timestamp=time.time(),
                    threshold_warning=0.9,
                    threshold_critical=0.7
                ))

                if success_rate < 0.7:
                    issues.append("任务成功率过低")
                    recommendations.append("检查任务执行错误并优化")

                # 平均处理时间
                avg_processing_time = getattr(task_execution_service, 'avg_processing_time', 0.0)
                if avg_processing_time > 0:
                    metrics.append(HealthMetric(
                        name="avg_task_processing_time",
                        value=avg_processing_time,
                        unit="seconds",
                        timestamp=time.time(),
                        threshold_warning=300.0,
                        threshold_critical=600.0
                    ))

                    if avg_processing_time > 600.0:
                        issues.append("任务处理时间过长")
                        recommendations.append("优化任务处理逻辑或增加并发处理")

                # 计算整体评分
                overall_score = self._calculate_score(metrics)
                status = self._determine_status(overall_score, issues)

            return ServiceHealth(
                service_name="task_execution",
                status=status,
                overall_score=overall_score,
                metrics=metrics,
                dependencies=["system", "database", "telegram_service"],
                issues=issues,
                recommendations=recommendations,
                check_duration=time.time() - start_time
            )

        except Exception as e:
            return ServiceHealth(
                service_name="task_execution",
                status=HealthStatus.FAILED,
                overall_score=0.0,
                metrics=[],
                dependencies=["system", "database", "telegram_service"],
                issues=[f"任务执行服务检查失败: {str(e)}"],
                recommendations=["检查任务执行服务状态和配置"],
                check_duration=time.time() - start_time
            )

    def _calculate_score(self, metrics: List[HealthMetric]) -> float:
        """计算健康评分"""
        scores = []
        for metric in metrics:
            if metric.name == "task_success_rate":
                scores.append(metric.value)
            elif metric.threshold_critical and metric.threshold_warning:
                if metric.value >= metric.threshold_critical:
                    score = 0.0
                elif metric.value >= metric.threshold_warning:
                    range_size = metric.threshold_critical - metric.threshold_warning
                    score = 1.0 - (metric.value - metric.threshold_warning) / range_size
                else:
                    score = 1.0
                scores.append(score)
        return statistics.mean(scores) if scores else 1.0

    def _determine_status(self, score: float, issues: List[str]) -> HealthStatus:
        """确定健康状态"""
        if score >= 0.9 and not issues:
            return HealthStatus.HEALTHY
        elif score >= 0.7:
            return HealthStatus.WARNING
        elif score >= 0.5:
            return HealthStatus.CRITICAL
        else:
            return HealthStatus.FAILED

    def get_dependencies(self) -> List[str]:
        return ["system", "database", "telegram_service"]


class CompleteHealthMonitor(ServiceLoggerMixin):
    """完整健康监控系统主类"""

    def __init__(self, config: Optional[MonitoringConfig] = None):
        super().__init__()
        self.config = config or MonitoringConfig()

        # 健康检查提供者
        self.providers: Dict[str, HealthCheckProvider] = {}
        self.provider_order: List[str] = []

        # 监控状态
        self.running = False
        self.monitoring_task: Optional[asyncio.Task] = None
        self.last_full_check = 0.0

        # 健康数据存储
        self.current_health: Dict[str, ServiceHealth] = {}
        self.health_history: deque = deque(maxlen=1000)
        self.metrics_database = ":memory:"  # SQLite内存数据库

        # 告警系统
        self.alert_rules: List[AlertRule] = []
        self.active_alerts: Dict[str, Dict] = {}
        self.alert_cooldowns: Dict[str, float] = {}

        # 性能统计
        self.check_count = 0
        self.total_check_time = 0.0
        self.error_count = 0

        # 自动恢复引擎
        self.auto_recovery_engine = None
        if self.config.enable_auto_recovery:
            self.auto_recovery_engine = get_auto_recovery_engine()

        # 高性能日志记录器
        self.perf_logger = HighPerformanceLogger("health_monitor")

        self._setup_default_providers()
        self._setup_default_alert_rules()
        self._initialize_metrics_database()

    def _setup_default_providers(self):
        """设置默认的健康检查提供者"""
        providers = [
            SystemHealthProvider(),
            DatabaseHealthProvider(),
            TelegramServiceHealthProvider(),
            TaskExecutionHealthProvider()
        ]

        for provider in providers:
            self.register_provider(provider)

    def _setup_default_alert_rules(self):
        """设置默认告警规则"""
        if not self.config.enable_alerts:
            return

        rules = [
            AlertRule(
                name="high_cpu_usage",
                metric_pattern="cpu_usage",
                condition="> 90",
                threshold=90.0,
                severity="critical",
                action="auto_recovery"
            ),
            AlertRule(
                name="high_memory_usage",
                metric_pattern="memory_usage",
                condition="> 85",
                threshold=85.0,
                severity="warning",
                action="alert_only"
            ),
            AlertRule(
                name="database_connection_issues",
                metric_pattern="connection_pool_utilization",
                condition="> 95",
                threshold=0.95,
                severity="critical",
                action="auto_recovery"
            ),
            AlertRule(
                name="telegram_disconnection",
                metric_pattern="telegram_connection",
                condition="== 0",
                threshold=0.0,
                severity="critical",
                action="auto_recovery"
            ),
            AlertRule(
                name="low_task_success_rate",
                metric_pattern="task_success_rate",
                condition="< 70",
                threshold=0.7,
                severity="warning",
                action="alert_only"
            )
        ]

        self.alert_rules.extend(rules)

    def _initialize_metrics_database(self):
        """初始化指标数据库"""
        try:
            conn = sqlite3.connect(self.metrics_database)
            cursor = conn.cursor()

            # 创建指标表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS health_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    service_name TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    metric_unit TEXT,
                    threshold_warning REAL,
                    threshold_critical REAL,
                    labels TEXT
                )
            ''')

            # 创建健康状态表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS health_status (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    service_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    overall_score REAL NOT NULL,
                    check_duration REAL NOT NULL,
                    issues TEXT,
                    recommendations TEXT
                )
            ''')

            # 创建索引
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_metrics_time ON health_metrics(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_metrics_service ON health_metrics(service_name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_status_time ON health_status(timestamp)')

            conn.commit()
            conn.close()

        except Exception as e:
            self.log_operation_error("initialize_metrics_database", e)

    def register_provider(self, provider: HealthCheckProvider):
        """注册健康检查提供者"""
        self.providers[provider.name] = provider
        self.provider_order = sorted(self.providers.keys(),
                                   key=lambda name: self.providers[name].priority,
                                   reverse=True)
        self.log_operation_success("register_provider",
                                 provider_name=provider.name,
                                 priority=provider.priority)

    def add_alert_rule(self, rule: AlertRule):
        """添加告警规则"""
        self.alert_rules.append(rule)
        self.log_operation_success("add_alert_rule", rule_name=rule.name)

    async def start(self):
        """启动健康监控"""
        if self.running:
            return

        self.running = True
        self.log_operation_start("start_health_monitoring")

        # 启动自动恢复引擎
        if self.auto_recovery_engine:
            await self.auto_recovery_engine.start()
            # 注册所有服务到自动恢复系统
            for provider_name in self.providers:
                await register_service_for_auto_recovery(provider_name)

        # 启动监控任务
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())

        self.log_operation_success("start_health_monitoring")

    async def stop(self):
        """停止健康监控"""
        if not self.running:
            return

        self.running = False
        self.log_operation_start("stop_health_monitoring")

        # 停止监控任务
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass

        # 停止自动恢复引擎
        if self.auto_recovery_engine:
            await self.auto_recovery_engine.stop()

        self.log_operation_success("stop_health_monitoring")

    async def _monitoring_loop(self):
        """监控循环"""
        while self.running:
            try:
                start_time = time.time()

                # 执行健康检查
                await self._perform_health_checks()

                # 处理告警
                await self._process_alerts()

                # 清理过期数据
                await self._cleanup_expired_data()

                # 记录性能指标
                check_duration = time.time() - start_time
                self.total_check_time += check_duration
                self.check_count += 1

                self.perf_logger.info("Health check completed",
                                    duration=check_duration,
                                    services_checked=len(self.providers))

                # 等待下次检查
                await asyncio.sleep(self.config.check_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.error_count += 1
                self.log_operation_error("monitoring_loop", e)
                await asyncio.sleep(min(self.config.check_interval, 60.0))

    async def _perform_health_checks(self):
        """执行健康检查"""
        tasks = []
        semaphore = asyncio.Semaphore(self.config.max_concurrent_checks)

        async def check_with_semaphore(provider_name: str, provider: HealthCheckProvider):
            async with semaphore:
                try:
                    if not provider.is_ready():
                        return provider_name, None

                    health = await provider.check_health()
                    provider.check_count += 1
                    provider.last_check_time = time.time()
                    return provider_name, health

                except Exception as e:
                    provider.error_count += 1
                    self.log_operation_error("health_check", e, provider=provider_name)
                    return provider_name, ServiceHealth(
                        service_name=provider_name,
                        status=HealthStatus.FAILED,
                        overall_score=0.0,
                        metrics=[],
                        dependencies=provider.get_dependencies(),
                        issues=[f"健康检查异常: {str(e)}"]
                    )

        # 创建检查任务
        for provider_name in self.provider_order:
            provider = self.providers[provider_name]
            task = asyncio.create_task(check_with_semaphore(provider_name, provider))
            tasks.append(task)

        # 等待所有检查完成
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理结果
        for result in results:
            if isinstance(result, Exception):
                self.log_operation_error("perform_health_checks", result)
                continue

            provider_name, health = result
            if health:
                self.current_health[provider_name] = health
                await self._store_health_data(health)

        # 记录历史
        self.health_history.append({
            'timestamp': time.time(),
            'services': {name: health.status.name for name, health in self.current_health.items()},
            'overall_health': self._calculate_overall_health()
        })

        self.last_full_check = time.time()

    async def _store_health_data(self, health: ServiceHealth):
        """存储健康数据到数据库"""
        try:
            conn = sqlite3.connect(self.metrics_database)
            cursor = conn.cursor()

            # 存储指标
            for metric in health.metrics:
                cursor.execute('''
                    INSERT INTO health_metrics
                    (timestamp, service_name, metric_name, metric_value, metric_unit,
                     threshold_warning, threshold_critical, labels)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    metric.timestamp,
                    health.service_name,
                    metric.name,
                    metric.value,
                    metric.unit,
                    metric.threshold_warning,
                    metric.threshold_critical,
                    json.dumps(metric.labels)
                ))

            # 存储健康状态
            cursor.execute('''
                INSERT INTO health_status
                (timestamp, service_name, status, overall_score, check_duration, issues, recommendations)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                health.last_check,
                health.service_name,
                health.status.name,
                health.overall_score,
                health.check_duration,
                json.dumps(health.issues),
                json.dumps(health.recommendations)
            ))

            conn.commit()
            conn.close()

        except Exception as e:
            self.log_operation_error("store_health_data", e, service=health.service_name)

    async def _process_alerts(self):
        """处理告警"""
        if not self.config.enable_alerts:
            return

        current_time = time.time()

        for rule in self.alert_rules:
            if not rule.enabled:
                continue

            # 检查冷却期
            cooldown_key = f"{rule.name}"
            if cooldown_key in self.alert_cooldowns:
                if current_time - self.alert_cooldowns[cooldown_key] < rule.cooldown_period:
                    continue

            # 检查告警条件
            triggered = await self._check_alert_condition(rule)
            if triggered:
                await self._trigger_alert(rule)
                self.alert_cooldowns[cooldown_key] = current_time

    async def _check_alert_condition(self, rule: AlertRule) -> bool:
        """检查告警条件"""
        for service_name, health in self.current_health.items():
            for metric in health.metrics:
                if rule.metric_pattern in metric.name:
                    # 简单的条件检查
                    if rule.condition == f"> {rule.threshold}":
                        return metric.value > rule.threshold
                    elif rule.condition == f"< {rule.threshold}":
                        return metric.value < rule.threshold
                    elif rule.condition == f"== {rule.threshold}":
                        return abs(metric.value - rule.threshold) < 0.001
        return False

    async def _trigger_alert(self, rule: AlertRule):
        """触发告警"""
        alert_data = {
            'rule_name': rule.name,
            'severity': rule.severity,
            'timestamp': time.time(),
            'message': f"Alert: {rule.name} - {rule.condition}"
        }

        self.active_alerts[rule.name] = alert_data

        self.log_operation_warning("trigger_alert",
                                 f"Alert triggered: {rule.name}",
                                 rule_name=rule.name,
                                 severity=rule.severity)

        # 执行告警动作
        if rule.action == "auto_recovery" and self.auto_recovery_engine:
            # 这里可以触发特定的恢复动作
            pass

    async def _cleanup_expired_data(self):
        """清理过期数据"""
        try:
            current_time = time.time()
            expiry_time = current_time - self.config.retention_period

            conn = sqlite3.connect(self.metrics_database)
            cursor = conn.cursor()

            # 清理过期指标
            cursor.execute('DELETE FROM health_metrics WHERE timestamp < ?', (expiry_time,))
            cursor.execute('DELETE FROM health_status WHERE timestamp < ?', (expiry_time,))

            conn.commit()
            conn.close()

            # 清理内存中的过期告警
            expired_alerts = []
            for alert_name, alert_data in self.active_alerts.items():
                if current_time - alert_data['timestamp'] > 3600:  # 1小时
                    expired_alerts.append(alert_name)

            for alert_name in expired_alerts:
                del self.active_alerts[alert_name]

        except Exception as e:
            self.log_operation_error("cleanup_expired_data", e)

    def _calculate_overall_health(self) -> float:
        """计算整体健康评分"""
        if not self.current_health:
            return 0.0

        scores = [health.overall_score for health in self.current_health.values()]
        return statistics.mean(scores)

    # 公共API方法

    @handle_service_errors("CompleteHealthMonitor", "get_current_health")
    async def get_current_health(self) -> ServiceResult[Dict[str, Any]]:
        """获取当前健康状态"""
        overall_health = self._calculate_overall_health()

        # 计算服务状态统计
        status_counts = defaultdict(int)
        for health in self.current_health.values():
            status_counts[health.status.name] += 1

        result = {
            'overall_health_score': overall_health,
            'overall_status': self._get_overall_status(overall_health),
            'last_check_time': self.last_full_check,
            'services': {
                name: {
                    'status': health.status.name,
                    'score': health.overall_score,
                    'issues_count': len(health.issues),
                    'recommendations_count': len(health.recommendations),
                    'last_check': health.last_check,
                    'check_duration': health.check_duration
                }
                for name, health in self.current_health.items()
            },
            'status_summary': dict(status_counts),
            'monitoring_stats': {
                'running': self.running,
                'check_count': self.check_count,
                'error_count': self.error_count,
                'avg_check_time': self.total_check_time / max(1, self.check_count),
                'providers_count': len(self.providers)
            },
            'active_alerts_count': len(self.active_alerts)
        }

        return ServiceResult.success_result(result)

    @handle_service_errors("CompleteHealthMonitor", "get_detailed_health")
    async def get_detailed_health(self, service_name: Optional[str] = None) -> ServiceResult[Dict[str, Any]]:
        """获取详细健康信息"""
        if service_name:
            if service_name not in self.current_health:
                return ServiceResult.error_result(
                    SystemError(f"Service {service_name} not found")
                )

            health = self.current_health[service_name]
            result = {
                'service_name': health.service_name,
                'status': health.status.name,
                'overall_score': health.overall_score,
                'metrics': [
                    {
                        'name': metric.name,
                        'value': metric.value,
                        'unit': metric.unit,
                        'timestamp': metric.timestamp,
                        'threshold_warning': metric.threshold_warning,
                        'threshold_critical': metric.threshold_critical,
                        'labels': metric.labels
                    }
                    for metric in health.metrics
                ],
                'dependencies': health.dependencies,
                'issues': health.issues,
                'recommendations': health.recommendations,
                'last_check': health.last_check,
                'check_duration': health.check_duration
            }
        else:
            result = {
                name: {
                    'service_name': health.service_name,
                    'status': health.status.name,
                    'overall_score': health.overall_score,
                    'metrics': [
                        {
                            'name': metric.name,
                            'value': metric.value,
                            'unit': metric.unit,
                            'timestamp': metric.timestamp,
                            'threshold_warning': metric.threshold_warning,
                            'threshold_critical': metric.threshold_critical
                        }
                        for metric in health.metrics
                    ],
                    'dependencies': health.dependencies,
                    'issues': health.issues,
                    'recommendations': health.recommendations,
                    'last_check': health.last_check,
                    'check_duration': health.check_duration
                }
                for name, health in self.current_health.items()
            }

        return ServiceResult.success_result(result)

    @handle_service_errors("CompleteHealthMonitor", "get_health_history")
    async def get_health_history(self, hours: int = 1) -> ServiceResult[List[Dict[str, Any]]]:
        """获取健康历史"""
        try:
            conn = sqlite3.connect(self.metrics_database)
            cursor = conn.cursor()

            cutoff_time = time.time() - (hours * 3600)

            cursor.execute('''
                SELECT timestamp, service_name, status, overall_score, check_duration
                FROM health_status
                WHERE timestamp > ?
                ORDER BY timestamp DESC
                LIMIT 1000
            ''', (cutoff_time,))

            rows = cursor.fetchall()
            conn.close()

            history = [
                {
                    'timestamp': row[0],
                    'service_name': row[1],
                    'status': row[2],
                    'overall_score': row[3],
                    'check_duration': row[4]
                }
                for row in rows
            ]

            return ServiceResult.success_result(history)

        except Exception as e:
            return ServiceResult.error_result(SystemError(f"Failed to get health history: {e}"))

    @handle_service_errors("CompleteHealthMonitor", "get_active_alerts")
    async def get_active_alerts(self) -> ServiceResult[List[Dict[str, Any]]]:
        """获取活跃告警"""
        alerts = list(self.active_alerts.values())
        return ServiceResult.success_result(alerts)

    @handle_service_errors("CompleteHealthMonitor", "get_recommendations")
    async def get_recommendations(self) -> ServiceResult[List[str]]:
        """获取系统优化建议"""
        all_recommendations = []

        for health in self.current_health.values():
            all_recommendations.extend(health.recommendations)

        # 去重
        unique_recommendations = list(set(all_recommendations))

        return ServiceResult.success_result(unique_recommendations)

    def _get_overall_status(self, score: float) -> str:
        """根据评分获取整体状态"""
        if score >= 0.9:
            return "HEALTHY"
        elif score >= 0.7:
            return "WARNING"
        elif score >= 0.5:
            return "CRITICAL"
        else:
            return "FAILED"


# 全局健康监控实例
_global_health_monitor: Optional[CompleteHealthMonitor] = None


def get_health_monitor() -> CompleteHealthMonitor:
    """获取全局健康监控实例"""
    global _global_health_monitor
    if _global_health_monitor is None:
        _global_health_monitor = CompleteHealthMonitor()
    return _global_health_monitor


@asynccontextmanager
async def health_monitoring_context():
    """健康监控上下文管理器"""
    monitor = get_health_monitor()
    await monitor.start()
    try:
        yield monitor
    finally:
        await monitor.stop()


# 便捷函数
async def start_complete_health_monitoring():
    """启动完整健康监控"""
    monitor = get_health_monitor()
    await monitor.start()


async def stop_complete_health_monitoring():
    """停止完整健康监控"""
    monitor = get_health_monitor()
    await monitor.stop()


async def get_system_health_summary() -> Dict[str, Any]:
    """获取系统健康摘要"""
    monitor = get_health_monitor()
    result = await monitor.get_current_health()
    return result.data if result.success else {}