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
from sqlalchemy import text

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

        # 自动应用模式：自适应调优算法
        return self.apply_auto_tuning(recommendations)

    def apply_auto_tuning(self, recommendations: List[TuningRecommendation]) -> Dict[str, Any]:
        """自适应自动调优算法"""
        try:
            # 安全阈值检查
            if not self._validate_safety_thresholds(recommendations):
                return {"error": "建议超出安全阈值，拒绝自动应用"}

            # 性能基准测试 - 调优前
            pre_tuning_benchmark = self._run_performance_baseline_test()
            if not pre_tuning_benchmark:
                return {"error": "无法建立性能基线，中止自动调优"}

            # 保存当前配置用于回滚
            rollback_config = self._create_rollback_point()

            applied_changes = []
            failed_changes = []

            # 按优先级和置信度排序
            sorted_recommendations = sorted(
                recommendations,
                key=lambda r: (self._get_priority_weight(r.priority), r.confidence),
                reverse=True
            )

            # 逐步应用调优建议
            for rec in sorted_recommendations:
                if rec.confidence < self._get_minimum_confidence_threshold():
                    logger.info(f"跳过低置信度建议: {rec.parameter} (置信度: {rec.confidence})")
                    continue

                logger.info(f"应用调优建议: {rec.parameter} {rec.current_value} -> {rec.recommended_value}")

                success = self._apply_single_recommendation(rec)
                if success:
                    applied_changes.append({
                        "parameter": rec.parameter,
                        "from": rec.current_value,
                        "to": rec.recommended_value,
                        "reason": rec.reason
                    })

                    # 增量验证 - 每次变更后检查系统稳定性
                    if not self._validate_system_stability():
                        logger.warning(f"系统稳定性检查失败，回滚 {rec.parameter} 变更")
                        self._rollback_single_change(rec)
                        failed_changes.append(rec.parameter)
                        break
                else:
                    failed_changes.append(rec.parameter)

            # 整体性能验证
            post_tuning_benchmark = self._run_performance_baseline_test()

            tuning_result = {
                "success": True,
                "applied_changes": applied_changes,
                "failed_changes": failed_changes,
                "performance_improvement": self._calculate_improvement(
                    pre_tuning_benchmark, post_tuning_benchmark
                ),
                "rollback_point": rollback_config["id"],
                "validation_scheduled": True
            }

            # 如果性能没有改善或恶化，执行完整回滚
            if tuning_result["performance_improvement"]["overall_score"] < 0:
                logger.warning("自动调优未带来性能改善，执行回滚")
                self._execute_full_rollback(rollback_config)
                tuning_result["rollback_executed"] = True
                tuning_result["success"] = False

            # 安排延迟验证
            self._schedule_delayed_validation(rollback_config)

            # 记录调优日志
            self._log_tuning_operation(tuning_result)

            return tuning_result

        except Exception as e:
            logger.error(f"自动调优失败: {e}")
            # 紧急回滚
            try:
                self._execute_emergency_rollback()
            except:
                logger.critical("紧急回滚失败，需要手动干预")
            return {"error": str(e), "emergency_rollback": True}

    def _validate_safety_thresholds(self, recommendations: List[TuningRecommendation]) -> bool:
        """验证安全阈值"""
        for rec in recommendations:
            param = rec.parameter
            new_value = rec.recommended_value

            if param == "pool_size":
                if not (self.safety_limits['min_pool_size'] <= new_value <= self.safety_limits['max_pool_size']):
                    logger.error(f"pool_size {new_value} 超出安全范围 [{self.safety_limits['min_pool_size']}, {self.safety_limits['max_pool_size']}]")
                    return False

            elif param == "max_overflow":
                if not (self.safety_limits['min_max_overflow'] <= new_value <= self.safety_limits['max_max_overflow']):
                    logger.error(f"max_overflow {new_value} 超出安全范围 [{self.safety_limits['min_max_overflow']}, {self.safety_limits['max_max_overflow']}]")
                    return False

            elif param == "pool_timeout":
                if not (self.safety_limits['min_pool_timeout'] <= new_value <= self.safety_limits['max_pool_timeout']):
                    logger.error(f"pool_timeout {new_value} 超出安全范围 [{self.safety_limits['min_pool_timeout']}, {self.safety_limits['max_pool_timeout']}]")
                    return False

        return True

    def _run_performance_baseline_test(self) -> Optional[Dict[str, Any]]:
        """运行性能基线测试"""
        try:
            # 运行轻量级基准测试
            start_time = time.time()

            # 测试数据库连接性能
            connection_test = self._test_connection_performance()

            # 获取当前系统指标
            current_metrics = self.analyze_current_performance()

            baseline = {
                "timestamp": datetime.now().isoformat(),
                "test_duration": time.time() - start_time,
                "connection_performance": connection_test,
                "system_metrics": current_metrics,
                "overall_score": current_metrics.get('performance_score', 0)
            }

            logger.debug(f"性能基线建立完成: 得分 {baseline['overall_score']}")
            return baseline

        except Exception as e:
            logger.error(f"性能基线测试失败: {e}")
            return None

    def _test_connection_performance(self) -> Dict[str, Any]:
        """测试连接性能"""
        try:
            from app.database.connection import get_engine
            engine = get_engine()

            test_results = {
                "connection_acquisition_time": [],
                "query_execution_time": [],
                "connection_release_time": []
            }

            # 执行10次测试
            for _ in range(10):
                start = time.time()

                with engine.connect() as conn:
                    acquire_time = time.time() - start
                    test_results["connection_acquisition_time"].append(acquire_time)

                    # 简单查询测试
                    query_start = time.time()
                    conn.execute(text("SELECT 1"))
                    query_time = time.time() - query_start
                    test_results["query_execution_time"].append(query_time)

                release_time = time.time() - start - acquire_time - query_time
                test_results["connection_release_time"].append(release_time)

            # 计算平均值
            return {
                "avg_connection_acquisition_ms": sum(test_results["connection_acquisition_time"]) / 10 * 1000,
                "avg_query_execution_ms": sum(test_results["query_execution_time"]) / 10 * 1000,
                "avg_connection_release_ms": sum(test_results["connection_release_time"]) / 10 * 1000,
                "total_tests": 10
            }

        except Exception as e:
            logger.error(f"连接性能测试失败: {e}")
            return {"error": str(e)}

    def _get_priority_weight(self, priority: str) -> int:
        """获取优先级权重"""
        weights = {"high": 3, "medium": 2, "low": 1}
        return weights.get(priority.lower(), 0)

    def _get_minimum_confidence_threshold(self) -> float:
        """获取最小置信度阈值"""
        thresholds = {
            TuningStrategy.CONSERVATIVE: 0.8,
            TuningStrategy.BALANCED: 0.6,
            TuningStrategy.AGGRESSIVE: 0.4
        }
        return thresholds.get(self.strategy, 0.6)

    def _create_rollback_point(self) -> Dict[str, Any]:
        """创建回滚点"""
        try:
            from app.database.connection import get_engine
            engine = get_engine()

            rollback_id = f"rollback_{int(time.time())}"

            rollback_config = {
                "id": rollback_id,
                "timestamp": datetime.now().isoformat(),
                "pool_config": {
                    "pool_size": getattr(engine.pool, 'size', lambda: 10)(),
                    "max_overflow": getattr(engine.pool, '_max_overflow', 20),
                    "pool_timeout": getattr(engine.pool, '_timeout', 30),
                    "pool_recycle": getattr(engine.pool, '_recycle', 3600)
                },
                "performance_snapshot": self._capture_performance_snapshot()
            }

            # 保存回滚点
            if not hasattr(self, '_rollback_points'):
                self._rollback_points = {}
            self._rollback_points[rollback_id] = rollback_config

            logger.info(f"回滚点已创建: {rollback_id}")
            return rollback_config

        except Exception as e:
            logger.error(f"创建回滚点失败: {e}")
            return {"id": None, "error": str(e)}

    def _validate_system_stability(self) -> bool:
        """验证系统稳定性"""
        try:
            # 等待短暂时间让系统稳定
            time.sleep(2)

            # 检查连接池状态
            status = self.monitor.get_current_status()

            # 稳定性检查指标
            checks = {
                "connection_errors": status.get('connection_errors_per_hour', 0) < 10,
                "pool_utilization": 0.1 <= status.get('pool_usage_percent', 0) / 100 <= 0.95,
                "active_connections": status.get('active_connections', 0) >= 0
            }

            all_passed = all(checks.values())

            if not all_passed:
                logger.warning(f"系统稳定性检查失败: {checks}")

            return all_passed

        except Exception as e:
            logger.error(f"系统稳定性检查异常: {e}")
            return False

    def _calculate_improvement(self, pre_benchmark: Dict, post_benchmark: Dict) -> Dict[str, Any]:
        """计算性能改善"""
        try:
            pre_score = pre_benchmark.get('overall_score', 0)
            post_score = post_benchmark.get('overall_score', 0)

            improvement = {
                "overall_score": post_score - pre_score,
                "improvement_percentage": ((post_score - pre_score) / max(pre_score, 1)) * 100,
                "pre_benchmark": pre_score,
                "post_benchmark": post_score
            }

            # 细分指标改善
            if 'connection_performance' in pre_benchmark and 'connection_performance' in post_benchmark:
                pre_conn = pre_benchmark['connection_performance']
                post_conn = post_benchmark['connection_performance']

                improvement["connection_metrics"] = {
                    "acquisition_time_change": (
                        pre_conn.get('avg_connection_acquisition_ms', 0) -
                        post_conn.get('avg_connection_acquisition_ms', 0)
                    ),
                    "query_time_change": (
                        pre_conn.get('avg_query_execution_ms', 0) -
                        post_conn.get('avg_query_execution_ms', 0)
                    )
                }

            return improvement

        except Exception as e:
            logger.error(f"计算性能改善失败: {e}")
            return {"overall_score": 0, "error": str(e)}

    def _log_tuning_operation(self, result: Dict[str, Any]):
        """记录调优操作日志"""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "operation": "auto_tuning",
                "strategy": self.strategy.value,
                "result": result,
                "system_info": {
                    "pool_status": self.monitor.get_current_status(),
                    "performance_score": self.analyze_current_performance().get('performance_score', 0)
                }
            }

            # 保存到调优日志
            if not hasattr(self, '_tuning_logs'):
                self._tuning_logs = []
            self._tuning_logs.append(log_entry)

            # 只保留最近100条记录
            if len(self._tuning_logs) > 100:
                self._tuning_logs = self._tuning_logs[-100:]

            logger.info(f"调优操作已记录: 成功={result.get('success', False)}")

        except Exception as e:
            logger.error(f"记录调优日志失败: {e}")

    def _apply_single_recommendation(self, rec: TuningRecommendation) -> bool:
        """应用单个调优建议"""
        try:
            if rec.parameter == "pool_size":
                return self._apply_pool_size_change(rec.current_value, rec.recommended_value)
            elif rec.parameter == "max_overflow":
                return self._apply_max_overflow_change(rec.current_value, rec.recommended_value)
            elif rec.parameter == "pool_timeout":
                return self._apply_pool_timeout_change(rec.current_value, rec.recommended_value)
            elif rec.parameter == "pool_recycle":
                return self._apply_pool_recycle_change(rec.current_value, rec.recommended_value)
            else:
                logger.warning(f"未知的调优参数: {rec.parameter}")
                return False
        except Exception as e:
            logger.error(f"应用调优建议失败 {rec.parameter}: {e}")
            return False

    def _rollback_single_change(self, rec: TuningRecommendation):
        """回滚单个变更"""
        try:
            # 回滚到原始值
            if rec.parameter == "pool_size":
                self._apply_pool_size_change(rec.recommended_value, rec.current_value)
            elif rec.parameter == "max_overflow":
                self._apply_max_overflow_change(rec.recommended_value, rec.current_value)
            elif rec.parameter == "pool_timeout":
                self._apply_pool_timeout_change(rec.recommended_value, rec.current_value)
            elif rec.parameter == "pool_recycle":
                self._apply_pool_recycle_change(rec.recommended_value, rec.current_value)

            logger.info(f"已回滚 {rec.parameter} 变更: {rec.recommended_value} -> {rec.current_value}")

        except Exception as e:
            logger.error(f"回滚 {rec.parameter} 变更失败: {e}")

    def _execute_full_rollback(self, rollback_config: Dict[str, Any]):
        """执行完整回滚"""
        try:
            if not rollback_config.get("pool_config"):
                logger.error("回滚配置无效")
                return False

            config = rollback_config["pool_config"]

            # 重建连接池
            from sqlalchemy import create_engine
            from app.config import get_database_url

            rollback_engine = create_engine(
                get_database_url(),
                pool_size=config["pool_size"],
                max_overflow=config["max_overflow"],
                pool_timeout=config["pool_timeout"],
                pool_recycle=config["pool_recycle"]
            )

            self._replace_engine_instance(rollback_engine)
            logger.info(f"完整回滚到配置: {rollback_config['id']}")
            return True

        except Exception as e:
            logger.error(f"完整回滚失败: {e}")
            return False

    def _execute_emergency_rollback(self):
        """执行紧急回滚"""
        try:
            # 使用最近的回滚点
            if hasattr(self, '_rollback_points') and self._rollback_points:
                latest_rollback = max(self._rollback_points.values(),
                                    key=lambda x: x.get('timestamp', ''))
                self._execute_full_rollback(latest_rollback)
            else:
                # 使用默认安全配置
                self._apply_safe_default_configuration()

        except Exception as e:
            logger.critical(f"紧急回滚失败: {e}")

    def _apply_safe_default_configuration(self):
        """应用安全的默认配置"""
        try:
            from sqlalchemy import create_engine
            from app.config import get_database_url

            safe_engine = create_engine(
                get_database_url(),
                pool_size=5,  # 安全的默认值
                max_overflow=10,
                pool_timeout=30,
                pool_recycle=3600
            )

            self._replace_engine_instance(safe_engine)
            logger.info("已应用安全默认配置")

        except Exception as e:
            logger.critical(f"应用安全默认配置失败: {e}")

    def _schedule_delayed_validation(self, rollback_config: Dict[str, Any]):
        """安排延迟验证"""
        def delayed_validation():
            try:
                time.sleep(600)  # 10分钟后验证

                # 运行延迟性能验证
                validation_result = self._run_delayed_performance_validation()

                # 如果性能恶化超过阈值，自动回滚
                if validation_result.get('performance_degradation', 0) > 15:  # 15%性能下降阈值
                    logger.warning("延迟验证发现性能恶化，执行自动回滚")
                    self._execute_full_rollback(rollback_config)

                logger.info(f"延迟验证完成: {validation_result}")

            except Exception as e:
                logger.error(f"延迟验证失败: {e}")

        validation_thread = threading.Thread(target=delayed_validation, daemon=True)
        validation_thread.start()

    def _run_delayed_performance_validation(self) -> Dict[str, Any]:
        """运行延迟性能验证"""
        try:
            # 获取当前性能指标
            current_metrics = self.analyze_current_performance()

            # 与历史平均值比较
            if len(self.performance_history) > 0:
                historical_avg = sum(
                    h.get('current_performance', {}).get('performance_score', 0)
                    for h in self.performance_history[-5:]  # 最近5次
                ) / min(len(self.performance_history), 5)

                current_score = current_metrics.get('performance_score', 0)
                degradation = ((historical_avg - current_score) / max(historical_avg, 1)) * 100

                return {
                    "current_score": current_score,
                    "historical_average": historical_avg,
                    "performance_degradation": degradation,
                    "validation_time": datetime.now().isoformat()
                }

            return {"current_score": current_metrics.get('performance_score', 0)}

        except Exception as e:
            logger.error(f"延迟性能验证失败: {e}")
            return {"error": str(e)}

    def get_tuning_report(self) -> Dict[str, Any]:
        """获取调优报告"""
        try:
            report = {
                "summary": {
                    "total_tuning_operations": len(getattr(self, '_tuning_logs', [])),
                    "successful_operations": len([
                        log for log in getattr(self, '_tuning_logs', [])
                        if log.get('result', {}).get('success', False)
                    ]),
                    "current_strategy": self.strategy.value,
                    "auto_tuning_enabled": self.tuning_enabled
                },
                "recent_operations": getattr(self, '_tuning_logs', [])[-10:],  # 最近10次操作
                "performance_trend": self._calculate_performance_trend(),
                "rollback_points": len(getattr(self, '_rollback_points', {})),
                "safety_limits": self.safety_limits,
                "current_configuration": self._capture_current_config().to_dict(),
                "report_generated": datetime.now().isoformat()
            }

            return report

        except Exception as e:
            logger.error(f"生成调优报告失败: {e}")
            return {"error": str(e)}

    def _calculate_performance_trend(self) -> Dict[str, Any]:
        """计算性能趋势"""
        try:
            if len(self.performance_history) < 3:
                return {"insufficient_data": True}

            # 取最近的性能记录
            recent_scores = [
                h.get('current_performance', {}).get('performance_score', 0)
                for h in self.performance_history[-10:]
            ]

            if len(recent_scores) < 2:
                return {"insufficient_data": True}

            # 计算趋势
            first_half = recent_scores[:len(recent_scores)//2]
            second_half = recent_scores[len(recent_scores)//2:]

            first_avg = sum(first_half) / len(first_half)
            second_avg = sum(second_half) / len(second_half)

            trend_percentage = ((second_avg - first_avg) / max(first_avg, 1)) * 100

            return {
                "trend_percentage": trend_percentage,
                "trend_direction": "improving" if trend_percentage > 5 else "declining" if trend_percentage < -5 else "stable",
                "first_period_avg": first_avg,
                "second_period_avg": second_avg,
                "data_points": len(recent_scores)
            }

        except Exception as e:
            logger.error(f"计算性能趋势失败: {e}")
            return {"error": str(e)}

    def _legacy_apply_recommendations(self, recommendations: List[TuningRecommendation]) -> Dict[str, Any]:
        """遗留的应用建议方法（保留兼容性）"""
        try:
            # 保存当前配置用于回滚
            current_config = self._capture_current_config()
            self.configuration_history.append(current_config)

            applied_changes = []

            for rec in recommendations:
                if rec.confidence < 0.5:  # 置信度太低，跳过
                    continue

                if rec.parameter == "pool_size":
                    success = self._apply_pool_size_change(rec.current_value, rec.recommended_value)
                    if success:
                        applied_changes.append(f"pool_size: {rec.current_value} -> {rec.recommended_value}")
                        logger.info(f"已应用 pool_size 调整: {rec.current_value} -> {rec.recommended_value}")
                    else:
                        logger.warning(f"pool_size 调整失败: {rec.current_value} -> {rec.recommended_value}")

                elif rec.parameter == "max_overflow":
                    success = self._apply_max_overflow_change(rec.current_value, rec.recommended_value)
                    if success:
                        applied_changes.append(f"max_overflow: {rec.current_value} -> {rec.recommended_value}")
                        logger.info(f"已应用 max_overflow 调整: {rec.current_value} -> {rec.recommended_value}")
                    else:
                        logger.warning(f"max_overflow 调整失败: {rec.current_value} -> {rec.recommended_value}")

                elif rec.parameter == "pool_timeout":
                    success = self._apply_pool_timeout_change(rec.current_value, rec.recommended_value)
                    if success:
                        applied_changes.append(f"pool_timeout: {rec.current_value} -> {rec.recommended_value}")
                        logger.info(f"已应用 pool_timeout 调整: {rec.current_value} -> {rec.recommended_value}")
                    else:
                        logger.warning(f"pool_timeout 调整失败: {rec.current_value} -> {rec.recommended_value}")

                elif rec.parameter == "pool_recycle":
                    success = self._apply_pool_recycle_change(rec.current_value, rec.recommended_value)
                    if success:
                        applied_changes.append(f"pool_recycle: {rec.current_value} -> {rec.recommended_value}")
                        logger.info(f"已应用 pool_recycle 调整: {rec.current_value} -> {rec.recommended_value}")
                    else:
                        logger.warning(f"pool_recycle 调整失败: {rec.current_value} -> {rec.recommended_value}")

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

    def _apply_pool_size_change(self, current_value: int, new_value: int) -> bool:
        """应用连接池大小调整"""
        try:
            # 备份当前配置以便回滚
            self._backup_current_config()

            # 获取数据库引擎实例
            from app.database.connection import get_engine
            engine = get_engine()

            # 记录变更前性能指标
            pre_change_metrics = self._capture_performance_snapshot()

            # 动态调整连接池大小
            if hasattr(engine.pool, 'size'):
                old_size = engine.pool.size()
                # SQLAlchemy连接池动态调整
                engine.pool.dispose()  # 清理现有连接

                # 重新配置引擎
                from sqlalchemy import create_engine
                from app.config import get_database_url

                new_engine = create_engine(
                    get_database_url(),
                    pool_size=new_value,
                    max_overflow=engine.pool._max_overflow,
                    pool_timeout=engine.pool._timeout,
                    pool_recycle=engine.pool._recycle
                )

                # 替换全局引擎实例
                self._replace_engine_instance(new_engine)

                # 验证调整效果
                time.sleep(2)  # 等待连接池稳定
                post_change_metrics = self._capture_performance_snapshot()

                if self._validate_change_effectiveness(pre_change_metrics, post_change_metrics):
                    logger.info(f"Pool size successfully changed from {current_value} to {new_value}")
                    return True
                else:
                    # 性能验证失败，回滚
                    self._rollback_configuration()
                    logger.warning(f"Pool size change validation failed, rolled back")
                    return False

            return False

        except Exception as e:
            logger.error(f"Failed to apply pool size change: {e}")
            # 尝试回滚
            try:
                self._rollback_configuration()
            except:
                pass
            return False

    def _apply_max_overflow_change(self, current_value: int, new_value: int) -> bool:
        """应用最大溢出连接数调整"""
        try:
            self._backup_current_config()

            from app.database.connection import get_engine
            engine = get_engine()

            pre_change_metrics = self._capture_performance_snapshot()

            # 动态调整最大溢出连接数
            if hasattr(engine.pool, '_max_overflow'):
                engine.pool._max_overflow = new_value

                time.sleep(2)
                post_change_metrics = self._capture_performance_snapshot()

                if self._validate_change_effectiveness(pre_change_metrics, post_change_metrics):
                    logger.info(f"Max overflow successfully changed from {current_value} to {new_value}")
                    return True
                else:
                    self._rollback_configuration()
                    return False

            return False

        except Exception as e:
            logger.error(f"Failed to apply max overflow change: {e}")
            try:
                self._rollback_configuration()
            except:
                pass
            return False

    def _apply_pool_timeout_change(self, current_value: float, new_value: float) -> bool:
        """应用连接池超时调整"""
        try:
            self._backup_current_config()

            from app.database.connection import get_engine
            engine = get_engine()

            pre_change_metrics = self._capture_performance_snapshot()

            # 动态调整连接池超时
            if hasattr(engine.pool, '_timeout'):
                engine.pool._timeout = new_value

                time.sleep(2)
                post_change_metrics = self._capture_performance_snapshot()

                if self._validate_change_effectiveness(pre_change_metrics, post_change_metrics):
                    logger.info(f"Pool timeout successfully changed from {current_value} to {new_value}")
                    return True
                else:
                    self._rollback_configuration()
                    return False

            return False

        except Exception as e:
            logger.error(f"Failed to apply pool timeout change: {e}")
            try:
                self._rollback_configuration()
            except:
                pass
            return False

    def _apply_pool_recycle_change(self, current_value: int, new_value: int) -> bool:
        """应用连接回收时间调整"""
        try:
            self._backup_current_config()

            from app.database.connection import get_engine
            engine = get_engine()

            pre_change_metrics = self._capture_performance_snapshot()

            # 动态调整连接回收时间
            if hasattr(engine.pool, '_recycle'):
                engine.pool._recycle = new_value

                time.sleep(2)
                post_change_metrics = self._capture_performance_snapshot()

                if self._validate_change_effectiveness(pre_change_metrics, post_change_metrics):
                    logger.info(f"Pool recycle successfully changed from {current_value} to {new_value}")
                    return True
                else:
                    self._rollback_configuration()
                    return False

            return False

        except Exception as e:
            logger.error(f"Failed to apply pool recycle change: {e}")
            try:
                self._rollback_configuration()
            except:
                pass
            return False

    def _backup_current_config(self):
        """备份当前配置"""
        try:
            from app.database.connection import get_engine
            engine = get_engine()

            self._config_backup = {
                'pool_size': getattr(engine.pool, 'size', lambda: 10)(),
                'max_overflow': getattr(engine.pool, '_max_overflow', 20),
                'pool_timeout': getattr(engine.pool, '_timeout', 30),
                'pool_recycle': getattr(engine.pool, '_recycle', 3600),
                'timestamp': time.time()
            }
            logger.debug("Configuration backed up successfully")

        except Exception as e:
            logger.error(f"Failed to backup configuration: {e}")

    def _rollback_configuration(self):
        """回滚配置"""
        try:
            if not hasattr(self, '_config_backup') or not self._config_backup:
                logger.warning("No configuration backup available for rollback")
                return False

            backup = self._config_backup

            # 重建连接池
            from sqlalchemy import create_engine
            from app.config import get_database_url

            rollback_engine = create_engine(
                get_database_url(),
                pool_size=backup['pool_size'],
                max_overflow=backup['max_overflow'],
                pool_timeout=backup['pool_timeout'],
                pool_recycle=backup['pool_recycle']
            )

            self._replace_engine_instance(rollback_engine)
            logger.info("Configuration successfully rolled back")
            return True

        except Exception as e:
            logger.error(f"Failed to rollback configuration: {e}")
            return False

    def _replace_engine_instance(self, new_engine):
        """替换全局引擎实例"""
        try:
            from app.database import connection
            # 关闭旧引擎的连接
            if hasattr(connection, '_engine') and connection._engine:
                connection._engine.dispose()

            # 替换引擎实例
            connection._engine = new_engine
            logger.debug("Engine instance replaced successfully")

        except Exception as e:
            logger.error(f"Failed to replace engine instance: {e}")

    def _capture_performance_snapshot(self) -> dict:
        """捕获性能快照"""
        try:
            status = self.monitor.get_current_status()

            return {
                'timestamp': time.time(),
                'active_connections': status.get('active_connections', 0),
                'total_connections': status.get('total_connections', 0),
                'pool_usage': status.get('pool_usage_percent', 0),
                'avg_query_time': status.get('avg_query_time_ms', 0),
                'slow_queries': status.get('slow_queries_per_hour', 0),
                'connection_errors': status.get('connection_errors_per_hour', 0)
            }

        except Exception as e:
            logger.error(f"Failed to capture performance snapshot: {e}")
            return {}

    def _validate_change_effectiveness(self, pre_metrics: dict, post_metrics: dict) -> bool:
        """验证配置变更的有效性"""
        try:
            if not pre_metrics or not post_metrics:
                return False

            # 计算性能指标变化
            metrics_changes = {}
            for key in ['avg_query_time', 'slow_queries', 'connection_errors']:
                if key in pre_metrics and key in post_metrics:
                    pre_val = pre_metrics[key]
                    post_val = post_metrics[key]
                    if pre_val > 0:
                        change_percent = ((post_val - pre_val) / pre_val) * 100
                        metrics_changes[key] = change_percent

            # 验证条件
            validation_passed = True

            # 查询时间不应显著增加（超过20%）
            if 'avg_query_time' in metrics_changes:
                if metrics_changes['avg_query_time'] > 20:
                    validation_passed = False
                    logger.warning(f"Query time increased by {metrics_changes['avg_query_time']:.1f}%")

            # 慢查询数量不应显著增加（超过50%）
            if 'slow_queries' in metrics_changes:
                if metrics_changes['slow_queries'] > 50:
                    validation_passed = False
                    logger.warning(f"Slow queries increased by {metrics_changes['slow_queries']:.1f}%")

            # 连接错误不应增加（超过10%）
            if 'connection_errors' in metrics_changes:
                if metrics_changes['connection_errors'] > 10:
                    validation_passed = False
                    logger.warning(f"Connection errors increased by {metrics_changes['connection_errors']:.1f}%")

            if validation_passed:
                logger.info("Configuration change validation passed")
            else:
                logger.warning("Configuration change validation failed")

            return validation_passed

        except Exception as e:
            logger.error(f"Failed to validate change effectiveness: {e}")
            return False

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