"""数据库性能基准测试

用于测试和评估数据库连接池性能的工具。

主要功能:
- 连接池并发性能测试
- 查询性能基准测试
- 负载测试
- 连接泄漏压力测试
- 性能回归测试

Author: TgGod Team
Version: 1.0.0
"""

import time
import asyncio
import threading
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import List, Dict, Any, Callable, Optional
from datetime import datetime, timedelta
import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..utils.enhanced_db_session import enhanced_db_session, execute_with_session_retry
from ..services.connection_pool_monitor import get_pool_monitor

logger = logging.getLogger(__name__)

@dataclass
class BenchmarkResult:
    """基准测试结果"""
    test_name: str
    duration: float
    total_operations: int
    operations_per_second: float
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    p95_response_time: float
    p99_response_time: float
    success_rate: float
    error_count: int
    concurrent_level: int
    start_time: datetime
    end_time: datetime
    additional_metrics: Dict[str, Any]

class DatabaseBenchmark:
    """数据库性能基准测试器"""

    def __init__(self):
        self.monitor = get_pool_monitor()
        self.results: List[BenchmarkResult] = []

    def run_connection_pool_stress_test(
        self,
        concurrent_connections: int = 20,
        operations_per_connection: int = 50,
        connection_hold_time: float = 0.1
    ) -> BenchmarkResult:
        """连接池压力测试"""
        test_name = f"connection_pool_stress_{concurrent_connections}x{operations_per_connection}"
        logger.info(f"开始连接池压力测试: {test_name}")

        start_time = datetime.now()
        response_times = []
        error_count = 0
        completed_operations = 0

        def connection_worker():
            nonlocal error_count, completed_operations
            worker_times = []

            for _ in range(operations_per_connection):
                op_start = time.time()
                try:
                    with enhanced_db_session(context="stress_test") as session:
                        # 模拟数据库操作
                        session.execute(text("SELECT 1"))
                        time.sleep(connection_hold_time)  # 模拟处理时间

                    op_time = time.time() - op_start
                    worker_times.append(op_time)
                    completed_operations += 1

                except Exception as e:
                    error_count += 1
                    logger.error(f"压力测试操作失败: {e}")

            return worker_times

        # 使用线程池执行并发测试
        with ThreadPoolExecutor(max_workers=concurrent_connections) as executor:
            futures = [executor.submit(connection_worker) for _ in range(concurrent_connections)]

            for future in as_completed(futures):
                try:
                    times = future.result()
                    response_times.extend(times)
                except Exception as e:
                    logger.error(f"压力测试线程失败: {e}")
                    error_count += 1

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # 计算统计指标
        total_operations = len(response_times) + error_count
        success_rate = len(response_times) / total_operations if total_operations > 0 else 0.0

        if response_times:
            avg_time = statistics.mean(response_times)
            min_time = min(response_times)
            max_time = max(response_times)
            p95_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 20 else max_time
            p99_time = statistics.quantiles(response_times, n=100)[98] if len(response_times) >= 100 else max_time
        else:
            avg_time = min_time = max_time = p95_time = p99_time = 0.0

        result = BenchmarkResult(
            test_name=test_name,
            duration=duration,
            total_operations=total_operations,
            operations_per_second=total_operations / duration if duration > 0 else 0.0,
            avg_response_time=avg_time,
            min_response_time=min_time,
            max_response_time=max_time,
            p95_response_time=p95_time,
            p99_response_time=p99_time,
            success_rate=success_rate,
            error_count=error_count,
            concurrent_level=concurrent_connections,
            start_time=start_time,
            end_time=end_time,
            additional_metrics={
                "operations_per_connection": operations_per_connection,
                "connection_hold_time": connection_hold_time,
                "completed_operations": completed_operations
            }
        )

        self.results.append(result)
        logger.info(f"压力测试完成: {result.operations_per_second:.2f} ops/sec")
        return result

    def run_query_performance_test(
        self,
        query_types: Dict[str, str],
        iterations: int = 100,
        concurrent_level: int = 5
    ) -> Dict[str, BenchmarkResult]:
        """查询性能测试"""
        results = {}

        for query_name, query_sql in query_types.items():
            logger.info(f"开始查询性能测试: {query_name}")

            start_time = datetime.now()
            response_times = []
            error_count = 0

            def query_worker():
                nonlocal error_count
                worker_times = []

                for _ in range(iterations // concurrent_level):
                    op_start = time.time()
                    try:
                        with enhanced_db_session(context=f"query_test_{query_name}") as session:
                            session.execute(text(query_sql))

                        op_time = time.time() - op_start
                        worker_times.append(op_time)

                    except Exception as e:
                        error_count += 1
                        logger.error(f"查询测试失败 [{query_name}]: {e}")

                return worker_times

            # 并发执行查询
            with ThreadPoolExecutor(max_workers=concurrent_level) as executor:
                futures = [executor.submit(query_worker) for _ in range(concurrent_level)]

                for future in as_completed(futures):
                    try:
                        times = future.result()
                        response_times.extend(times)
                    except Exception as e:
                        logger.error(f"查询测试线程失败: {e}")
                        error_count += 1

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            # 计算统计指标
            total_operations = len(response_times) + error_count
            success_rate = len(response_times) / total_operations if total_operations > 0 else 0.0

            if response_times:
                avg_time = statistics.mean(response_times)
                min_time = min(response_times)
                max_time = max(response_times)
                p95_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 20 else max_time
                p99_time = statistics.quantiles(response_times, n=100)[98] if len(response_times) >= 100 else max_time
            else:
                avg_time = min_time = max_time = p95_time = p99_time = 0.0

            result = BenchmarkResult(
                test_name=f"query_performance_{query_name}",
                duration=duration,
                total_operations=total_operations,
                operations_per_second=total_operations / duration if duration > 0 else 0.0,
                avg_response_time=avg_time,
                min_response_time=min_time,
                max_response_time=max_time,
                p95_response_time=p95_time,
                p99_response_time=p99_time,
                success_rate=success_rate,
                error_count=error_count,
                concurrent_level=concurrent_level,
                start_time=start_time,
                end_time=end_time,
                additional_metrics={
                    "query_sql": query_sql,
                    "iterations": iterations
                }
            )

            results[query_name] = result
            self.results.append(result)

        return results

    def run_connection_leak_test(
        self,
        leak_count: int = 10,
        leak_duration: int = 30
    ) -> BenchmarkResult:
        """连接泄漏测试"""
        test_name = f"connection_leak_test_{leak_count}x{leak_duration}s"
        logger.info(f"开始连接泄漏测试: {test_name}")

        start_time = datetime.now()
        leaked_sessions = []
        error_count = 0

        try:
            # 创建故意泄漏的连接
            for i in range(leak_count):
                try:
                    session = SessionLocal()
                    session.execute(text("SELECT 1"))
                    leaked_sessions.append(session)
                    logger.debug(f"创建泄漏连接 {i+1}/{leak_count}")
                except Exception as e:
                    error_count += 1
                    logger.error(f"创建泄漏连接失败: {e}")

            # 等待指定时间
            time.sleep(leak_duration)

            # 检查连接池状态
            pool_status = self.monitor.get_current_status()

        finally:
            # 清理泄漏的连接
            for session in leaked_sessions:
                try:
                    session.close()
                except Exception as e:
                    logger.error(f"清理泄漏连接失败: {e}")

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        result = BenchmarkResult(
            test_name=test_name,
            duration=duration,
            total_operations=leak_count,
            operations_per_second=leak_count / duration if duration > 0 else 0.0,
            avg_response_time=0.0,
            min_response_time=0.0,
            max_response_time=0.0,
            p95_response_time=0.0,
            p99_response_time=0.0,
            success_rate=(leak_count - error_count) / leak_count if leak_count > 0 else 0.0,
            error_count=error_count,
            concurrent_level=1,
            start_time=start_time,
            end_time=end_time,
            additional_metrics={
                "leaked_connections": leak_count - error_count,
                "leak_duration": leak_duration,
                "final_pool_status": pool_status
            }
        )

        self.results.append(result)
        logger.info(f"连接泄漏测试完成")
        return result

    def run_comprehensive_benchmark(self) -> Dict[str, Any]:
        """运行综合性能基准测试"""
        logger.info("开始综合性能基准测试")

        # 记录初始状态
        initial_pool_status = self.monitor.get_current_status()

        benchmark_results = {
            "start_time": datetime.now().isoformat(),
            "initial_pool_status": initial_pool_status,
            "tests": {}
        }

        try:
            # 1. 连接池压力测试
            logger.info("1/4 - 连接池压力测试")
            stress_result = self.run_connection_pool_stress_test(
                concurrent_connections=10,
                operations_per_connection=20,
                connection_hold_time=0.05
            )
            benchmark_results["tests"]["stress_test"] = stress_result

            # 2. 查询性能测试
            logger.info("2/4 - 查询性能测试")
            query_tests = {
                "simple_select": "SELECT 1",
                "pragma_check": "PRAGMA foreign_keys",
                "table_info": "SELECT name FROM sqlite_master WHERE type='table' LIMIT 5"
            }
            query_results = self.run_query_performance_test(
                query_types=query_tests,
                iterations=50,
                concurrent_level=3
            )
            benchmark_results["tests"]["query_performance"] = query_results

            # 3. 连接池容量测试
            logger.info("3/4 - 连接池容量测试")
            capacity_result = self.run_connection_pool_stress_test(
                concurrent_connections=initial_pool_status.get('pool_size', 10) + 5,
                operations_per_connection=10,
                connection_hold_time=0.1
            )
            benchmark_results["tests"]["capacity_test"] = capacity_result

            # 4. 连接泄漏检测测试
            logger.info("4/4 - 连接泄漏检测测试")
            leak_result = self.run_connection_leak_test(
                leak_count=5,
                leak_duration=10
            )
            benchmark_results["tests"]["leak_detection"] = leak_result

            # 记录最终状态
            final_pool_status = self.monitor.get_current_status()
            benchmark_results["final_pool_status"] = final_pool_status

            # 生成性能报告
            benchmark_results["performance_summary"] = self._generate_performance_summary()

        except Exception as e:
            logger.error(f"综合基准测试失败: {e}")
            benchmark_results["error"] = str(e)

        benchmark_results["end_time"] = datetime.now().isoformat()
        logger.info("综合性能基准测试完成")

        return benchmark_results

    def _generate_performance_summary(self) -> Dict[str, Any]:
        """生成性能总结"""
        if not self.results:
            return {"message": "没有测试结果"}

        # 计算整体统计
        total_operations = sum(r.total_operations for r in self.results)
        total_duration = sum(r.duration for r in self.results)
        avg_ops_per_sec = statistics.mean([r.operations_per_second for r in self.results])
        avg_response_time = statistics.mean([r.avg_response_time for r in self.results])
        overall_success_rate = statistics.mean([r.success_rate for r in self.results])

        # 找出最快和最慢的测试
        fastest_test = max(self.results, key=lambda r: r.operations_per_second)
        slowest_test = min(self.results, key=lambda r: r.operations_per_second)

        return {
            "total_tests": len(self.results),
            "total_operations": total_operations,
            "total_duration": total_duration,
            "avg_operations_per_second": avg_ops_per_sec,
            "avg_response_time": avg_response_time,
            "overall_success_rate": overall_success_rate,
            "fastest_test": {
                "name": fastest_test.test_name,
                "ops_per_sec": fastest_test.operations_per_second
            },
            "slowest_test": {
                "name": slowest_test.test_name,
                "ops_per_sec": slowest_test.operations_per_second
            },
            "performance_rating": self._calculate_performance_rating(avg_ops_per_sec, avg_response_time, overall_success_rate)
        }

    def _calculate_performance_rating(self, ops_per_sec: float, avg_response_time: float, success_rate: float) -> str:
        """计算性能评级"""
        # 基于操作/秒、响应时间和成功率的综合评级
        score = 0

        # 操作/秒评分
        if ops_per_sec >= 1000:
            score += 40
        elif ops_per_sec >= 500:
            score += 30
        elif ops_per_sec >= 100:
            score += 20
        else:
            score += 10

        # 响应时间评分
        if avg_response_time <= 0.01:
            score += 30
        elif avg_response_time <= 0.05:
            score += 25
        elif avg_response_time <= 0.1:
            score += 20
        elif avg_response_time <= 0.5:
            score += 15
        else:
            score += 5

        # 成功率评分
        if success_rate >= 0.99:
            score += 30
        elif success_rate >= 0.95:
            score += 25
        elif success_rate >= 0.9:
            score += 20
        else:
            score += 10

        # 评级映射
        if score >= 90:
            return "优秀"
        elif score >= 75:
            return "良好"
        elif score >= 60:
            return "一般"
        elif score >= 45:
            return "较差"
        else:
            return "很差"

    def get_test_results(self) -> List[Dict[str, Any]]:
        """获取所有测试结果"""
        return [
            {
                "test_name": r.test_name,
                "duration": r.duration,
                "total_operations": r.total_operations,
                "operations_per_second": r.operations_per_second,
                "avg_response_time": r.avg_response_time,
                "min_response_time": r.min_response_time,
                "max_response_time": r.max_response_time,
                "p95_response_time": r.p95_response_time,
                "p99_response_time": r.p99_response_time,
                "success_rate": r.success_rate,
                "error_count": r.error_count,
                "concurrent_level": r.concurrent_level,
                "start_time": r.start_time.isoformat(),
                "end_time": r.end_time.isoformat(),
                "additional_metrics": r.additional_metrics
            }
            for r in self.results
        ]

    def clear_results(self):
        """清空测试结果"""
        self.results.clear()

# 全局基准测试实例
benchmark_instance = DatabaseBenchmark()

def run_quick_benchmark() -> Dict[str, Any]:
    """运行快速基准测试"""
    logger.info("开始快速基准测试")

    benchmark = DatabaseBenchmark()

    # 简单的连接池测试
    result = benchmark.run_connection_pool_stress_test(
        concurrent_connections=5,
        operations_per_connection=10,
        connection_hold_time=0.01
    )

    return {
        "test_name": result.test_name,
        "operations_per_second": result.operations_per_second,
        "avg_response_time": result.avg_response_time,
        "success_rate": result.success_rate,
        "performance_rating": benchmark._calculate_performance_rating(
            result.operations_per_second,
            result.avg_response_time,
            result.success_rate
        )
    }

def get_benchmark_instance() -> DatabaseBenchmark:
    """获取基准测试实例"""
    return benchmark_instance