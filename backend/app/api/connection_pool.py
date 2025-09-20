"""连接池监控API

提供数据库连接池的监控、状态查询和性能分析接口。

主要功能:
- 连接池状态查询
- 实时监控指标
- 性能测试
- 优化建议
- 健康检查

Author: TgGod Team
Version: 1.0.0
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..services.connection_pool_monitor import get_pool_monitor
from ..services.connection_pool_tuner import get_pool_tuner
from ..utils.db_performance_benchmark import get_benchmark_instance
from ..database import get_db, SessionLocal
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/connection-pool/status")
async def get_connection_pool_status():
    """获取连接池当前状态"""
    try:
        monitor = get_pool_monitor()
        status = monitor.get_current_status()

        return {
            "success": True,
            "data": status,
            "message": f"连接池状态: {status.get('health_status', 'unknown')}"
        }
    except Exception as e:
        logger.error(f"获取连接池状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取连接池状态失败: {str(e)}")

@router.get("/connection-pool/metrics")
async def get_connection_pool_metrics(
    minutes: int = Query(60, description="获取最近N分钟的指标", ge=1, le=1440)
):
    """获取连接池历史指标"""
    try:
        monitor = get_pool_monitor()
        metrics = monitor.get_metrics_history(minutes=minutes)

        return {
            "success": True,
            "data": {
                "metrics": metrics,
                "period_minutes": minutes,
                "total_records": len(metrics)
            },
            "message": f"成功获取最近 {minutes} 分钟的连接池指标"
        }
    except Exception as e:
        logger.error(f"获取连接池指标失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取连接池指标失败: {str(e)}")

@router.get("/connection-pool/health")
async def check_connection_pool_health():
    """连接池健康检查"""
    try:
        monitor = get_pool_monitor()
        status = monitor.get_current_status()

        health_status = status.get('health_status', 'unknown')
        utilization = status.get('utilization', 0.0)

        # 生成健康报告
        health_report = {
            "status": health_status,
            "utilization": utilization,
            "utilization_percentage": f"{utilization * 100:.1f}%",
            "active_connections": status.get('checked_out', 0),
            "total_capacity": status.get('pool_size', 0) + status.get('overflow', 0),
            "peak_connections": status.get('peak_connections', 0),
            "total_queries": status.get('total_queries', 0),
            "connection_errors": status.get('connection_errors', 0),
            "monitoring_active": status.get('monitoring_active', False),
            "timestamp": datetime.now().isoformat()
        }

        # 错误率计算
        if health_report['total_queries'] > 0:
            error_rate = health_report['connection_errors'] / health_report['total_queries']
            health_report['error_rate'] = f"{error_rate * 100:.2f}%"
        else:
            health_report['error_rate'] = "0.00%"

        return {
            "success": True,
            "data": health_report,
            "message": f"连接池健康状态: {health_status}"
        }
    except Exception as e:
        logger.error(f"连接池健康检查失败: {e}")
        raise HTTPException(status_code=500, detail=f"连接池健康检查失败: {str(e)}")

@router.get("/connection-pool/suggestions")
async def get_optimization_suggestions():
    """获取连接池优化建议"""
    try:
        monitor = get_pool_monitor()
        suggestions = monitor.get_optimization_suggestions()

        return {
            "success": True,
            "data": {
                "suggestions": suggestions,
                "suggestion_count": len(suggestions),
                "generated_at": datetime.now().isoformat()
            },
            "message": f"生成了 {len(suggestions)} 条优化建议"
        }
    except Exception as e:
        logger.error(f"获取优化建议失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取优化建议失败: {str(e)}")

@router.post("/connection-pool/test")
async def test_connection_pool():
    """测试连接池性能"""
    try:
        monitor = get_pool_monitor()
        test_results = monitor.test_connection_pool()

        # 添加性能评级
        avg_time = test_results.get('avg_connection_time', 0)
        if avg_time < 0.1:
            performance_rating = "优秀"
        elif avg_time < 0.5:
            performance_rating = "良好"
        elif avg_time < 1.0:
            performance_rating = "一般"
        else:
            performance_rating = "较差"

        test_results['performance_rating'] = performance_rating

        return {
            "success": True,
            "data": test_results,
            "message": f"连接池测试完成，性能评级: {performance_rating}"
        }
    except Exception as e:
        logger.error(f"连接池测试失败: {e}")
        raise HTTPException(status_code=500, detail=f"连接池测试失败: {str(e)}")

@router.post("/connection-pool/monitor/start")
async def start_monitoring():
    """启动连接池监控"""
    try:
        monitor = get_pool_monitor()

        if monitor.monitoring:
            return {
                "success": True,
                "data": {"already_running": True},
                "message": "连接池监控已在运行"
            }

        monitor.start_monitoring(interval=15.0)

        return {
            "success": True,
            "data": {"started": True, "interval": 15.0},
            "message": "连接池监控已启动"
        }
    except Exception as e:
        logger.error(f"启动连接池监控失败: {e}")
        raise HTTPException(status_code=500, detail=f"启动连接池监控失败: {str(e)}")

@router.post("/connection-pool/monitor/stop")
async def stop_monitoring():
    """停止连接池监控"""
    try:
        monitor = get_pool_monitor()

        if not monitor.monitoring:
            return {
                "success": True,
                "data": {"already_stopped": True},
                "message": "连接池监控未在运行"
            }

        monitor.stop_monitoring()

        return {
            "success": True,
            "data": {"stopped": True},
            "message": "连接池监控已停止"
        }
    except Exception as e:
        logger.error(f"停止连接池监控失败: {e}")
        raise HTTPException(status_code=500, detail=f"停止连接池监控失败: {str(e)}")

@router.get("/connection-pool/detailed-status")
async def get_detailed_connection_pool_status():
    """获取详细的连接池状态信息"""
    try:
        monitor = get_pool_monitor()

        # 获取基础状态
        status = monitor.get_current_status()

        # 获取最近的指标
        recent_metrics = monitor.get_metrics_history(minutes=10)

        # 计算趋势信息
        trend_data = {}
        if len(recent_metrics) >= 2:
            first_metric = recent_metrics[0]
            last_metric = recent_metrics[-1]

            trend_data = {
                "utilization_trend": last_metric['checked_out'] - first_metric['checked_out'],
                "query_trend": last_metric['query_count'] - first_metric['query_count'],
                "error_trend": last_metric['connection_errors'] - first_metric['connection_errors']
            }

        # 组合详细状态
        detailed_status = {
            "current_status": status,
            "recent_metrics_count": len(recent_metrics),
            "trend_data": trend_data,
            "monitoring_info": {
                "active": monitor.monitoring,
                "max_history": monitor.max_history,
                "current_history_size": len(monitor.metrics_history)
            },
            "health_thresholds": monitor.health_thresholds,
            "timestamp": datetime.now().isoformat()
        }

        return {
            "success": True,
            "data": detailed_status,
            "message": "获取详细连接池状态成功"
        }
    except Exception as e:
        logger.error(f"获取详细连接池状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取详细连接池状态失败: {str(e)}")

@router.get("/connection-pool/config")
async def get_connection_pool_config():
    """获取当前连接池配置"""
    try:
        from ..database import engine, pool_size, max_overflow

        pool = engine.pool

        config_info = {
            "pool_size": pool_size,
            "max_overflow": max_overflow,
            "total_capacity": pool_size + max_overflow,
            "pool_timeout": getattr(pool, '_timeout', 'N/A'),
            "pool_recycle": getattr(pool, '_recycle', 'N/A'),
            "pool_pre_ping": getattr(pool, '_pre_ping', 'N/A'),
            "pool_reset_on_return": getattr(pool, '_reset_on_return', 'N/A'),
            "database_url_type": "sqlite" if "sqlite" in str(engine.url) else str(engine.url).split(':')[0],
            "engine_info": {
                "name": engine.name,
                "driver": engine.driver,
                "echo": engine.echo
            }
        }

        return {
            "success": True,
            "data": config_info,
            "message": "获取连接池配置成功"
        }
    except Exception as e:
        logger.error(f"获取连接池配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取连接池配置失败: {str(e)}")

@router.post("/connection-pool/reset-stats")
async def reset_connection_pool_stats():
    """重置连接池统计信息"""
    try:
        monitor = get_pool_monitor()

        # 重置统计信息
        with monitor.lock:
            monitor.total_queries = 0
            monitor.connection_errors = 0
            monitor.peak_connections = 0
            monitor.metrics_history.clear()
            monitor.query_times.clear()
            monitor.active_connections.clear()
            monitor.connection_checkout_times.clear()

        return {
            "success": True,
            "data": {
                "reset_time": datetime.now().isoformat(),
                "cleared_metrics": True
            },
            "message": "连接池统计信息已重置"
        }
    except Exception as e:
        logger.error(f"重置连接池统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"重置连接池统计失败: {str(e)}")

# ========== 连接池调优相关API ==========

@router.get("/connection-pool/tuning/analysis")
async def get_performance_analysis():
    """获取性能分析报告"""
    try:
        tuner = get_pool_tuner()
        analysis = tuner.analyze_current_performance()

        return {
            "success": True,
            "data": analysis,
            "message": f"性能分析完成，得分: {analysis.get('performance_score', 0):.1f}"
        }
    except Exception as e:
        logger.error(f"性能分析失败: {e}")
        raise HTTPException(status_code=500, detail=f"性能分析失败: {str(e)}")

@router.get("/connection-pool/tuning/recommendations")
async def get_tuning_recommendations():
    """获取调优建议"""
    try:
        tuner = get_pool_tuner()
        recommendations = tuner.generate_tuning_recommendations()

        return {
            "success": True,
            "data": {
                "recommendations": [
                    {
                        "parameter": r.parameter,
                        "current_value": r.current_value,
                        "recommended_value": r.recommended_value,
                        "reason": r.reason,
                        "priority": r.priority,
                        "expected_improvement": r.expected_improvement,
                        "confidence": r.confidence
                    }
                    for r in recommendations
                ],
                "total_recommendations": len(recommendations),
                "generated_at": datetime.now().isoformat()
            },
            "message": f"生成了 {len(recommendations)} 条调优建议"
        }
    except Exception as e:
        logger.error(f"获取调优建议失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取调优建议失败: {str(e)}")

@router.post("/connection-pool/tuning/apply")
async def apply_tuning_recommendations(auto_apply: bool = Query(False, description="是否自动应用建议")):
    """应用调优建议"""
    try:
        tuner = get_pool_tuner()
        recommendations = tuner.generate_tuning_recommendations()

        if not recommendations:
            return {
                "success": True,
                "data": {"message": "当前配置已优化，无需调整"},
                "message": "无调优建议可应用"
            }

        result = tuner.apply_recommendations(recommendations, auto_apply=auto_apply)

        return {
            "success": True,
            "data": result,
            "message": "调优建议处理完成"
        }
    except Exception as e:
        logger.error(f"应用调优建议失败: {e}")
        raise HTTPException(status_code=500, detail=f"应用调优建议失败: {str(e)}")

@router.get("/connection-pool/tuning/history")
async def get_tuning_history():
    """获取调优历史"""
    try:
        tuner = get_pool_tuner()
        history = tuner.get_tuning_history()

        return {
            "success": True,
            "data": history,
            "message": f"获取调优历史成功，包含 {len(history.get('configuration_history', []))} 条配置记录"
        }
    except Exception as e:
        logger.error(f"获取调优历史失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取调优历史失败: {str(e)}")

@router.post("/connection-pool/tuning/strategy")
async def set_tuning_strategy(strategy: str = Query(..., description="调优策略: conservative, balanced, aggressive")):
    """设置调优策略"""
    try:
        tuner = get_pool_tuner()
        tuner.set_strategy(strategy)

        return {
            "success": True,
            "data": {"strategy": strategy},
            "message": f"调优策略已设置为: {strategy}"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"设置调优策略失败: {e}")
        raise HTTPException(status_code=500, detail=f"设置调优策略失败: {str(e)}")

@router.post("/connection-pool/tuning/auto-start")
async def start_auto_tuning(interval: int = Query(600, description="自动调优间隔(秒)", ge=300, le=3600)):
    """启动自动调优"""
    try:
        tuner = get_pool_tuner()
        tuner.start_auto_tuning(interval=interval)

        return {
            "success": True,
            "data": {
                "auto_tuning_enabled": True,
                "interval": interval
            },
            "message": f"自动调优已启动，间隔: {interval}秒"
        }
    except Exception as e:
        logger.error(f"启动自动调优失败: {e}")
        raise HTTPException(status_code=500, detail=f"启动自动调优失败: {str(e)}")

@router.post("/connection-pool/tuning/auto-stop")
async def stop_auto_tuning():
    """停止自动调优"""
    try:
        tuner = get_pool_tuner()
        tuner.stop_auto_tuning()

        return {
            "success": True,
            "data": {"auto_tuning_enabled": False},
            "message": "自动调优已停止"
        }
    except Exception as e:
        logger.error(f"停止自动调优失败: {e}")
        raise HTTPException(status_code=500, detail=f"停止自动调优失败: {str(e)}")

# ========== 性能基准测试相关API ==========

@router.post("/connection-pool/benchmark/quick")
async def run_quick_benchmark():
    """运行快速基准测试"""
    try:
        from ..utils.db_performance_benchmark import run_quick_benchmark
        result = run_quick_benchmark()

        return {
            "success": True,
            "data": result,
            "message": f"快速基准测试完成，性能评级: {result.get('performance_rating', '未知')}"
        }
    except Exception as e:
        logger.error(f"快速基准测试失败: {e}")
        raise HTTPException(status_code=500, detail=f"快速基准测试失败: {str(e)}")

@router.post("/connection-pool/benchmark/comprehensive")
async def run_comprehensive_benchmark():
    """运行综合基准测试"""
    try:
        benchmark = get_benchmark_instance()
        result = benchmark.run_comprehensive_benchmark()

        return {
            "success": True,
            "data": result,
            "message": "综合基准测试完成"
        }
    except Exception as e:
        logger.error(f"综合基准测试失败: {e}")
        raise HTTPException(status_code=500, detail=f"综合基准测试失败: {str(e)}")

@router.post("/connection-pool/benchmark/stress")
async def run_stress_test(
    concurrent_connections: int = Query(10, description="并发连接数", ge=1, le=50),
    operations_per_connection: int = Query(20, description="每连接操作数", ge=1, le=100),
    connection_hold_time: float = Query(0.1, description="连接持有时间(秒)", ge=0.01, le=5.0)
):
    """运行压力测试"""
    try:
        benchmark = get_benchmark_instance()
        result = benchmark.run_connection_pool_stress_test(
            concurrent_connections=concurrent_connections,
            operations_per_connection=operations_per_connection,
            connection_hold_time=connection_hold_time
        )

        return {
            "success": True,
            "data": {
                "test_name": result.test_name,
                "duration": result.duration,
                "total_operations": result.total_operations,
                "operations_per_second": result.operations_per_second,
                "avg_response_time": result.avg_response_time,
                "success_rate": result.success_rate,
                "error_count": result.error_count,
                "concurrent_level": result.concurrent_level
            },
            "message": f"压力测试完成，{result.operations_per_second:.2f} ops/sec"
        }
    except Exception as e:
        logger.error(f"压力测试失败: {e}")
        raise HTTPException(status_code=500, detail=f"压力测试失败: {str(e)}")

@router.get("/connection-pool/benchmark/results")
async def get_benchmark_results():
    """获取基准测试结果"""
    try:
        benchmark = get_benchmark_instance()
        results = benchmark.get_test_results()

        return {
            "success": True,
            "data": {
                "results": results,
                "total_tests": len(results)
            },
            "message": f"获取 {len(results)} 条测试结果"
        }
    except Exception as e:
        logger.error(f"获取基准测试结果失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取基准测试结果失败: {str(e)}")

@router.post("/connection-pool/benchmark/clear")
async def clear_benchmark_results():
    """清空基准测试结果"""
    try:
        benchmark = get_benchmark_instance()
        benchmark.clear_results()

        return {
            "success": True,
            "data": {"cleared": True},
            "message": "基准测试结果已清空"
        }
    except Exception as e:
        logger.error(f"清空基准测试结果失败: {e}")
        raise HTTPException(status_code=500, detail=f"清空基准测试结果失败: {str(e)}")

# ========== 会话管理相关API ==========

@router.get("/connection-pool/sessions/health")
async def get_session_health():
    """获取会话健康信息"""
    try:
        from ..utils.enhanced_db_session import get_session_health_info
        health_info = get_session_health_info()

        return {
            "success": True,
            "data": health_info,
            "message": f"会话健康状态: {health_info.get('health_status', 'unknown')}"
        }
    except Exception as e:
        logger.error(f"获取会话健康信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取会话健康信息失败: {str(e)}")

@router.post("/connection-pool/sessions/cleanup")
async def cleanup_sessions():
    """清理泄漏的会话"""
    try:
        from ..utils.enhanced_db_session import cleanup_leaked_sessions
        cleaned_count = cleanup_leaked_sessions()

        return {
            "success": True,
            "data": {
                "cleaned_sessions": cleaned_count,
                "cleanup_time": datetime.now().isoformat()
            },
            "message": f"已清理 {cleaned_count} 个泄漏会话"
        }
    except Exception as e:
        logger.error(f"清理会话失败: {e}")
        raise HTTPException(status_code=500, detail=f"清理会话失败: {str(e)}")