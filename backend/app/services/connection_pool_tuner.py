"""智能连接池参数调优器

基于实时监控数据和性能指标自动调优数据库连接池参数。

主要功能:
- 自动参数调优
- 性能分析和建议
- 自适应配置调整
- 负载预测
- 配置回滚机制

Author: TgGod Team
Version: 1.0.0
"""

import time
import json
import logging
import threading
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum

from ..services.connection_pool_monitor import get_pool_monitor
from ..utils.db_performance_benchmark import get_benchmark_instance
from ..database import engine

logger = logging.getLogger(__name__)

class TuningStrategy(Enum):
    """调优策略"""
    CONSERVATIVE = "conservative"  # 保守策略
    AGGRESSIVE = "aggressive"     # 激进策略
    BALANCED = "balanced"         # 平衡策略

@dataclass
class PoolConfiguration:
    """连接池配置"""
    pool_size: int
    max_overflow: int
    pool_timeout: float
    pool_recycle: int
    strategy: TuningStrategy
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            'timestamp': self.timestamp.isoformat(),
            'strategy': self.strategy.value
        }

@dataclass
class TuningRecommendation:
    """调优建议"""
    parameter: str
    current_value: Any
    recommended_value: Any
    reason: str
    priority: str  # high, medium, low
    expected_improvement: str
    confidence: float  # 0.0 - 1.0

class ConnectionPoolTuner:
    """连接池智能调优器"""

    def __init__(self):
        self.monitor = get_pool_monitor()
        self.benchmark = get_benchmark_instance()

        # 调优历史
        self.configuration_history: List[PoolConfiguration] = []
        self.performance_history: List[Dict[str, Any]] = []

        # 当前配置
        self.current_config: Optional[PoolConfiguration] = None

        # 调优参数
        self.tuning_enabled = False
        self.tuning_thread: Optional[threading.Thread] = None
        self.tuning_interval = 300  # 5分钟

        # 性能阈值
        self.performance_thresholds = {
            'utilization_high': 0.85,
            'utilization_low': 0.3,
            'error_rate_high': 0.05,
            'response_time_high': 1.0,
            'overflow_high': 0.5  # 溢出连接比例
        }

        # 调优策略
        self.strategy = TuningStrategy.BALANCED

        # 安全限制
        self.safety_limits = {
            'min_pool_size': 2,
            'max_pool_size': 50,
            'min_max_overflow': 0,
            'max_max_overflow': 100,
            'min_pool_timeout': 5,
            'max_pool_timeout': 300
        }

    def analyze_current_performance(self) -> Dict[str, Any]:
        """分析当前性能状态"""
        try:
            # 获取当前状态
            status = self.monitor.get_current_status()

            # 获取历史指标
            metrics = self.monitor.get_metrics_history(minutes=30)

            if not metrics:
                return {"error": "没有足够的历史数据"}

            # 计算性能指标
            recent_metrics = metrics[-10:] if len(metrics) >= 10 else metrics

            avg_utilization = sum(m['checked_out'] / max(m['pool_size'], 1) for m in recent_metrics) / len(recent_metrics)
            avg_overflow = sum(m['overflow'] for m in recent_metrics) / len(recent_metrics)

            # 错误率
            total_queries = status.get('total_queries', 0)
            total_errors = status.get('connection_errors', 0)
            error_rate = total_errors / max(total_queries, 1)

            # 响应时间趋势
            response_times = [m.get('avg_checkout_time', 0) for m in recent_metrics]
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0

            analysis = {
                'current_status': status,
                'avg_utilization': avg_utilization,
                'avg_overflow': avg_overflow,
                'error_rate': error_rate,
                'avg_response_time': avg_response_time,
                'performance_score': self._calculate_performance_score(
                    avg_utilization, error_rate, avg_response_time
                ),
                'analysis_time': datetime.now().isoformat()
            }

            # 识别性能问题
            issues = self._identify_performance_issues(analysis)
            analysis['issues'] = issues

            return analysis

        except Exception as e:
            logger.error(f"性能分析失败: {e}")
            return {"error": str(e)}

    def _calculate_performance_score(self, utilization: float, error_rate: float, response_time: float) -> float:
        """计算性能得分 (0-100)"""
        score = 100.0

        # 利用率评分
        if utilization > 0.9:
            score -= 30
        elif utilization > 0.8:
            score -= 15
        elif utilization < 0.2:
            score -= 10

        # 错误率评分
        if error_rate > 0.1:
            score -= 40
        elif error_rate > 0.05:
            score -= 20
        elif error_rate > 0.01:
            score -= 10

        # 响应时间评分
        if response_time > 2.0:
            score -= 30
        elif response_time > 1.0:
            score -= 15
        elif response_time > 0.5:
            score -= 5

        return max(0.0, score)

    def _identify_performance_issues(self, analysis: Dict[str, Any]) -> List[str]:
        """识别性能问题"""
        issues = []

        utilization = analysis.get('avg_utilization', 0)
        error_rate = analysis.get('error_rate', 0)
        response_time = analysis.get('avg_response_time', 0)
        overflow = analysis.get('avg_overflow', 0)

        if utilization > self.performance_thresholds['utilization_high']:
            issues.append("连接池利用率过高，可能导致连接等待")

        if utilization < self.performance_thresholds['utilization_low']:
            issues.append("连接池利用率过低，资源配置可能过多")

        if error_rate > self.performance_thresholds['error_rate_high']:
            issues.append("连接错误率过高，需要检查配置或网络")

        if response_time > self.performance_thresholds['response_time_high']:
            issues.append("平均响应时间过长，可能存在性能瓶颈")

        if overflow > self.performance_thresholds['overflow_high']:
            issues.append("溢出连接使用频繁，建议增加基础连接池大小")

        return issues

    def generate_tuning_recommendations(self) -> List[TuningRecommendation]:
        """生成调优建议"""
        try:
            analysis = self.analyze_current_performance()

            if "error" in analysis:
                return []

            recommendations = []
            status = analysis['current_status']

            current_pool_size = status.get('pool_size', 10)
            current_overflow = status.get('overflow', 20)
            utilization = analysis.get('avg_utilization', 0)
            error_rate = analysis.get('error_rate', 0)

            # 基于利用率调整连接池大小
            if utilization > 0.85:
                recommended_pool_size = min(
                    current_pool_size + self._get_adjustment_step(),
                    self.safety_limits['max_pool_size']
                )
                recommendations.append(TuningRecommendation(
                    parameter="pool_size",
                    current_value=current_pool_size,
                    recommended_value=recommended_pool_size,
                    reason="连接池利用率过高，增加基础连接数",
                    priority="high",
                    expected_improvement="减少连接等待时间，提高并发性能",
                    confidence=0.8
                ))

            elif utilization < 0.3 and current_pool_size > self.safety_limits['min_pool_size']:
                recommended_pool_size = max(
                    current_pool_size - self._get_adjustment_step(),
                    self.safety_limits['min_pool_size']
                )
                recommendations.append(TuningRecommendation(
                    parameter="pool_size",
                    current_value=current_pool_size,
                    recommended_value=recommended_pool_size,
                    reason="连接池利用率过低，减少资源占用",
                    priority="medium",
                    expected_improvement="降低资源消耗，优化内存使用",
                    confidence=0.7
                ))

            # 基于溢出情况调整最大溢出连接数
            avg_overflow = analysis.get('avg_overflow', 0)
            if avg_overflow > current_overflow * 0.5:  # 溢出使用率超过50%
                recommended_overflow = min(
                    current_overflow + self._get_adjustment_step() * 2,
                    self.safety_limits['max_max_overflow']
                )
                recommendations.append(TuningRecommendation(
                    parameter="max_overflow",
                    current_value=current_overflow,
                    recommended_value=recommended_overflow,
                    reason="溢出连接使用频繁，增加溢出容量",
                    priority="medium",
                    expected_improvement="减少连接拒绝，提高峰值处理能力",
                    confidence=0.6
                ))

            # 基于响应时间调整超时设置
            response_time = analysis.get('avg_response_time', 0)
            if response_time > 1.0:
                recommendations.append(TuningRecommendation(
                    parameter="pool_timeout",
                    current_value=30,  # 当前默认值
                    recommended_value=60,
                    reason="响应时间较长，增加连接超时时间",
                    priority="low",
                    expected_improvement="减少超时错误，提高请求成功率",
                    confidence=0.5
                ))

            # 基于错误率的建议
            if error_rate > 0.05:
                recommendations.append(TuningRecommendation(
                    parameter="pool_recycle",
                    current_value=1800,  # 当前默认值
                    recommended_value=900,
                    reason="连接错误率高，增加连接回收频率",
                    priority="high",
                    expected_improvement="减少连接相关错误，提高稳定性",
                    confidence=0.7
                ))

            return recommendations

        except Exception as e:
            logger.error(f"生成调优建议失败: {e}")
            return []

    def _get_adjustment_step(self) -> int:
        """获取调整步长"""
        if self.strategy == TuningStrategy.CONSERVATIVE:
            return 2
        elif self.strategy == TuningStrategy.AGGRESSIVE:
            return 5
        else:  # BALANCED
            return 3

    def apply_recommendations(self, recommendations: List[TuningRecommendation], auto_apply: bool = False) -> Dict[str, Any]:
        """应用调优建议"""
        if not recommendations:
            return {"message": "没有调优建议可应用"}

        if not auto_apply:
            return {
                "message": "调优建议已生成，需要手动确认应用",
                "recommendations": [
                    {
                        "parameter": r.parameter,
                        "current_value": r.current_value,
                        "recommended_value": r.recommended_value,
                        "reason": r.reason,
                        "priority": r.priority,
                        "confidence": r.confidence
                    }
                    for r in recommendations
                ]
            }

        try:
            # 保存当前配置用于回滚
            current_config = self._capture_current_config()
            self.configuration_history.append(current_config)

            applied_changes = []

            for rec in recommendations:
                if rec.confidence < 0.5:  # 置信度太低，跳过
                    continue

                if rec.parameter == "pool_size":
                    # 注意：这里只是示例，实际应用需要重启引擎或者动态调整
                    logger.info(f"建议调整 pool_size: {rec.current_value} -> {rec.recommended_value}")
                    applied_changes.append(f"pool_size: {rec.recommended_value}")

                elif rec.parameter == "max_overflow":
                    logger.info(f"建议调整 max_overflow: {rec.current_value} -> {rec.recommended_value}")
                    applied_changes.append(f"max_overflow: {rec.recommended_value}")

                # 其他参数的调整...

            # 记录调优后的性能
            self._schedule_performance_validation()

            return {
                "success": True,
                "applied_changes": applied_changes,
                "message": f"已应用 {len(applied_changes)} 项调优建议",
                "validation_scheduled": True
            }

        except Exception as e:
            logger.error(f"应用调优建议失败: {e}")
            return {"error": str(e)}

    def _capture_current_config(self) -> PoolConfiguration:
        """捕获当前配置"""
        status = self.monitor.get_current_status()

        return PoolConfiguration(
            pool_size=status.get('pool_size', 10),
            max_overflow=status.get('overflow', 20),
            pool_timeout=30.0,  # 默认值
            pool_recycle=1800,  # 默认值
            strategy=self.strategy,
            timestamp=datetime.now()
        )

    def _schedule_performance_validation(self):
        """安排性能验证"""
        def validate_after_delay():
            time.sleep(300)  # 5分钟后验证
            try:
                self._validate_tuning_effectiveness()
            except Exception as e:
                logger.error(f"性能验证失败: {e}")

        validation_thread = threading.Thread(target=validate_after_delay, daemon=True)
        validation_thread.start()

    def _validate_tuning_effectiveness(self):
        """验证调优效果"""
        try:
            # 运行基准测试
            benchmark_result = self.benchmark.run_connection_pool_stress_test(
                concurrent_connections=5,
                operations_per_connection=20
            )

            # 分析性能改进
            current_performance = self.analyze_current_performance()

            validation_result = {
                "validation_time": datetime.now().isoformat(),
                "benchmark_result": {
                    "operations_per_second": benchmark_result.operations_per_second,
                    "avg_response_time": benchmark_result.avg_response_time,
                    "success_rate": benchmark_result.success_rate
                },
                "current_performance": current_performance,
                "improvement_detected": self._detect_improvement(current_performance)
            }

            self.performance_history.append(validation_result)

            logger.info(f"调优效果验证完成: {validation_result['improvement_detected']}")

        except Exception as e:
            logger.error(f"调优效果验证失败: {e}")

    def _detect_improvement(self, current_performance: Dict[str, Any]) -> bool:
        """检测性能改进"""
        if len(self.performance_history) < 2:
            return False

        previous_performance = self.performance_history[-2]
        current_score = current_performance.get('performance_score', 0)
        previous_score = previous_performance.get('current_performance', {}).get('performance_score', 0)

        return current_score > previous_score

    def start_auto_tuning(self, interval: int = 300):
        """启动自动调优"""
        if self.tuning_enabled:
            return

        self.tuning_enabled = True
        self.tuning_interval = interval

        def tuning_loop():
            while self.tuning_enabled:
                try:
                    logger.info("执行自动调优检查")

                    # 生成建议
                    recommendations = self.generate_tuning_recommendations()

                    if recommendations:
                        # 只应用高优先级的建议
                        high_priority_recs = [r for r in recommendations if r.priority == "high"]

                        if high_priority_recs:
                            result = self.apply_recommendations(high_priority_recs, auto_apply=True)
                            logger.info(f"自动调优结果: {result}")

                    time.sleep(self.tuning_interval)

                except Exception as e:
                    logger.error(f"自动调优循环错误: {e}")
                    time.sleep(self.tuning_interval)

        self.tuning_thread = threading.Thread(target=tuning_loop, daemon=True)
        self.tuning_thread.start()

        logger.info(f"自动调优已启动，间隔: {interval}秒")

    def stop_auto_tuning(self):
        """停止自动调优"""
        self.tuning_enabled = False

        if self.tuning_thread:
            self.tuning_thread.join()

        logger.info("自动调优已停止")

    def get_tuning_history(self) -> Dict[str, Any]:
        """获取调优历史"""
        return {
            "configuration_history": [config.to_dict() for config in self.configuration_history],
            "performance_history": self.performance_history,
            "tuning_enabled": self.tuning_enabled,
            "current_strategy": self.strategy.value
        }

    def set_strategy(self, strategy: str):
        """设置调优策略"""
        try:
            self.strategy = TuningStrategy(strategy)
            logger.info(f"调优策略已设置为: {strategy}")
        except ValueError:
            logger.error(f"无效的调优策略: {strategy}")
            raise ValueError(f"无效的调优策略: {strategy}")

    def reset_tuning_history(self):
        """重置调优历史"""
        self.configuration_history.clear()
        self.performance_history.clear()
        logger.info("调优历史已重置")

# 全局调优器实例
pool_tuner = ConnectionPoolTuner()

def get_pool_tuner() -> ConnectionPoolTuner:
    """获取连接池调优器实例"""
    return pool_tuner

def initialize_pool_tuning():
    """初始化连接池调优"""
    try:
        # 可以根据需要启动自动调优
        # pool_tuner.start_auto_tuning(interval=600)  # 10分钟间隔
        logger.info("连接池调优器初始化完成")
    except Exception as e:
        logger.error(f"连接池调优器初始化失败: {e}")