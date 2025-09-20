"""连接池监控服务

该模块提供数据库连接池的实时监控、健康检查和性能分析功能。

主要功能:
- 连接池状态监控
- 连接泄漏检测
- 性能指标收集
- 自动调优建议
- 健康检查和报警

Author: TgGod Team
Version: 1.0.0
"""

import time
import logging
import threading
import psutil
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.pool import Pool
from sqlalchemy.engine import Engine
from dataclasses import dataclass
from collections import deque, defaultdict

from ..database import engine, SessionLocal

logger = logging.getLogger(__name__)

@dataclass
class ConnectionMetrics:
    """连接池指标数据类"""
    timestamp: datetime
    pool_size: int
    checked_out: int
    overflow: int
    checked_in: int
    total_connections: int
    avg_checkout_time: float
    peak_connections: int
    connection_errors: int
    query_count: int

@dataclass
class ConnectionLeakInfo:
    """连接泄漏信息"""
    connection_id: str
    checkout_time: datetime
    stack_trace: str
    duration: timedelta

class ConnectionPoolMonitor:
    """连接池监控器"""

    def __init__(self, engine: Engine, max_history: int = 1000):
        self.engine = engine
        self.pool = engine.pool
        self.max_history = max_history

        # 指标历史记录
        self.metrics_history: deque = deque(maxlen=max_history)

        # 连接追踪
        self.active_connections: Dict[str, Dict] = {}
        self.connection_checkout_times: Dict[str, datetime] = {}

        # 统计数据
        self.total_queries = 0
        self.query_times: deque = deque(maxlen=1000)
        self.connection_errors = 0
        self.peak_connections = 0

        # 监控线程控制
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()

        # 健康阈值
        self.health_thresholds = {
            'max_checkout_time': 30.0,  # 最大连接获取时间(秒)
            'max_connection_age': 300.0,  # 最大连接持有时间(秒)
            'error_rate_threshold': 0.05,  # 错误率阈值
            'pool_utilization_warning': 0.8,  # 连接池使用率警告阈值
            'pool_utilization_critical': 0.95  # 连接池使用率严重阈值
        }

    def start_monitoring(self, interval: float = 10.0):
        """开始监控连接池"""
        if self.monitoring:
            return

        self.monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval,),
            daemon=True
        )
        self.monitor_thread.start()
        logger.info(f"连接池监控已启动，间隔: {interval}秒")

    def stop_monitoring(self):
        """停止监控"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join()
        logger.info("连接池监控已停止")

    def _monitor_loop(self, interval: float):
        """监控循环"""
        while self.monitoring:
            try:
                self._collect_metrics()
                self._check_connection_leaks()
                time.sleep(interval)
            except Exception as e:
                logger.error(f"连接池监控错误: {e}")
                time.sleep(interval)

    def _collect_metrics(self):
        """收集连接池指标"""
        try:
            with self.lock:
                pool = self.pool

                # 获取连接池状态
                pool_size = pool.size()
                checked_out = pool.checkedout()
                overflow = pool.overflow()
                checked_in = pool.checkedin()
                total_connections = checked_out + checked_in

                # 计算平均连接获取时间
                avg_checkout_time = (
                    sum(self.query_times) / len(self.query_times)
                    if self.query_times else 0.0
                )

                # 更新峰值连接数
                self.peak_connections = max(self.peak_connections, total_connections)

                # 创建指标记录
                metrics = ConnectionMetrics(
                    timestamp=datetime.now(),
                    pool_size=pool_size,
                    checked_out=checked_out,
                    overflow=overflow,
                    checked_in=checked_in,
                    total_connections=total_connections,
                    avg_checkout_time=avg_checkout_time,
                    peak_connections=self.peak_connections,
                    connection_errors=self.connection_errors,
                    query_count=self.total_queries
                )

                self.metrics_history.append(metrics)

        except Exception as e:
            logger.error(f"收集连接池指标失败: {e}")

    def _check_connection_leaks(self):
        """检查连接泄漏"""
        try:
            current_time = datetime.now()
            max_age = timedelta(seconds=self.health_thresholds['max_connection_age'])

            leaks = []
            for conn_id, checkout_time in list(self.connection_checkout_times.items()):
                age = current_time - checkout_time
                if age > max_age:
                    leak_info = ConnectionLeakInfo(
                        connection_id=conn_id,
                        checkout_time=checkout_time,
                        stack_trace="",  # 在实际实现中可以记录堆栈跟踪
                        duration=age
                    )
                    leaks.append(leak_info)

            if leaks:
                logger.warning(f"检测到 {len(leaks)} 个可能的连接泄漏")
                for leak in leaks:
                    logger.warning(f"连接 {leak.connection_id} 已持有 {leak.duration}")

        except Exception as e:
            logger.error(f"连接泄漏检查失败: {e}")

    def get_current_status(self) -> Dict[str, Any]:
        """获取当前连接池状态"""
        try:
            with self.lock:
                pool = self.pool

                # 基本状态
                status = {
                    'pool_size': pool.size(),
                    'checked_out': pool.checkedout(),
                    'overflow': pool.overflow(),
                    'checked_in': pool.checkedin(),
                    'total_connections': pool.checkedout() + pool.checkedin(),
                    'peak_connections': self.peak_connections,
                    'total_queries': self.total_queries,
                    'connection_errors': self.connection_errors,
                    'active_connections_count': len(self.active_connections),
                    'monitoring_active': self.monitoring
                }

                # 计算使用率
                max_connections = pool.size() + pool.overflow()
                if max_connections > 0:
                    status['utilization'] = status['checked_out'] / max_connections
                else:
                    status['utilization'] = 0.0

                # 健康状态
                status['health_status'] = self._assess_health(status)

                return status

        except Exception as e:
            logger.error(f"获取连接池状态失败: {e}")
            return {'error': str(e)}

    def _assess_health(self, status: Dict[str, Any]) -> str:
        """评估连接池健康状态"""
        try:
            utilization = status.get('utilization', 0.0)
            error_rate = (
                status.get('connection_errors', 0) / max(status.get('total_queries', 1), 1)
            )

            # 严重状态
            if utilization >= self.health_thresholds['pool_utilization_critical']:
                return 'critical'
            if error_rate >= self.health_thresholds['error_rate_threshold']:
                return 'critical'

            # 警告状态
            if utilization >= self.health_thresholds['pool_utilization_warning']:
                return 'warning'

            # 检查是否有长时间持有的连接
            if len(self.active_connections) > status.get('checked_out', 0):
                return 'warning'

            return 'healthy'

        except Exception as e:
            logger.error(f"健康状态评估失败: {e}")
            return 'unknown'

    def get_metrics_history(self, minutes: int = 60) -> List[Dict[str, Any]]:
        """获取指标历史记录"""
        try:
            cutoff_time = datetime.now() - timedelta(minutes=minutes)

            filtered_metrics = [
                {
                    'timestamp': m.timestamp.isoformat(),
                    'pool_size': m.pool_size,
                    'checked_out': m.checked_out,
                    'overflow': m.overflow,
                    'checked_in': m.checked_in,
                    'total_connections': m.total_connections,
                    'avg_checkout_time': m.avg_checkout_time,
                    'peak_connections': m.peak_connections,
                    'connection_errors': m.connection_errors,
                    'query_count': m.query_count
                }
                for m in self.metrics_history
                if m.timestamp >= cutoff_time
            ]

            return filtered_metrics

        except Exception as e:
            logger.error(f"获取指标历史失败: {e}")
            return []

    def get_optimization_suggestions(self) -> List[str]:
        """获取优化建议"""
        suggestions = []

        try:
            status = self.get_current_status()

            # 连接池大小建议
            utilization = status.get('utilization', 0.0)
            if utilization >= 0.9:
                suggestions.append("连接池使用率过高，建议增加 pool_size 或 max_overflow")
            elif utilization <= 0.3:
                suggestions.append("连接池使用率较低，可以考虑减少 pool_size 以节省资源")

            # 错误率建议
            error_rate = (
                status.get('connection_errors', 0) / max(status.get('total_queries', 1), 1)
            )
            if error_rate > 0.05:
                suggestions.append("连接错误率较高，检查数据库连接配置和网络状态")

            # 连接回收建议
            if self.metrics_history:
                recent_metrics = list(self.metrics_history)[-10:]
                avg_overflow = sum(m.overflow for m in recent_metrics) / len(recent_metrics)
                if avg_overflow > 5:
                    suggestions.append("溢出连接数较高，建议增加基础连接池大小")

            # 性能建议
            if status.get('peak_connections', 0) > status.get('pool_size', 0) * 2:
                suggestions.append("峰值连接数过高，考虑增加连接池大小或优化查询")

            return suggestions

        except Exception as e:
            logger.error(f"生成优化建议失败: {e}")
            return ["无法生成优化建议，请检查监控服务状态"]

    def record_query_time(self, query_time: float):
        """记录查询时间"""
        with self.lock:
            self.query_times.append(query_time)
            self.total_queries += 1

    def record_connection_error(self):
        """记录连接错误"""
        with self.lock:
            self.connection_errors += 1

    def test_connection_pool(self) -> Dict[str, Any]:
        """测试连接池性能"""
        test_results = {
            'start_time': datetime.now().isoformat(),
            'test_duration': 0.0,
            'successful_connections': 0,
            'failed_connections': 0,
            'avg_connection_time': 0.0,
            'max_connection_time': 0.0,
            'min_connection_time': float('inf'),
            'concurrent_connections': 0
        }

        try:
            start_time = time.time()
            connection_times = []

            # 测试10次连接获取
            for i in range(10):
                conn_start = time.time()
                try:
                    with SessionLocal() as session:
                        # 执行简单查询
                        session.execute(text("SELECT 1"))
                        conn_time = time.time() - conn_start
                        connection_times.append(conn_time)
                        test_results['successful_connections'] += 1
                except Exception as e:
                    test_results['failed_connections'] += 1
                    logger.error(f"连接测试失败: {e}")

            # 计算统计信息
            if connection_times:
                test_results['avg_connection_time'] = sum(connection_times) / len(connection_times)
                test_results['max_connection_time'] = max(connection_times)
                test_results['min_connection_time'] = min(connection_times)

            test_results['test_duration'] = time.time() - start_time
            test_results['end_time'] = datetime.now().isoformat()

        except Exception as e:
            logger.error(f"连接池测试失败: {e}")
            test_results['error'] = str(e)

        return test_results

# 全局监控器实例
pool_monitor = ConnectionPoolMonitor(engine)

def get_pool_monitor() -> ConnectionPoolMonitor:
    """获取连接池监控器实例"""
    return pool_monitor

def initialize_pool_monitoring():
    """初始化连接池监控"""
    try:
        pool_monitor.start_monitoring(interval=15.0)  # 15秒间隔监控
        logger.info("连接池监控初始化完成")
    except Exception as e:
        logger.error(f"连接池监控初始化失败: {e}")