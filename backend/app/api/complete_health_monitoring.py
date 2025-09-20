"""
完整健康监控API

提供全面的服务健康监控、自动恢复和预测性维护API接口。
包括实时健康状态、历史趋势、告警管理和恢复统计等功能。

Author: TgGod Team
Version: 1.0.0
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from ..services.complete_health_monitoring import (
    get_health_monitor, start_complete_health_monitoring,
    stop_complete_health_monitoring, get_system_health_summary
)
from ..core.auto_recovery_engine import get_auto_recovery_engine

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/complete-health/status")
async def get_complete_health_status():
    """获取完整的健康状态"""
    try:
        monitor = get_health_monitor()
        result = await monitor.get_current_health()

        if not result.success:
            raise HTTPException(status_code=500, detail=result.error.message)

        return {
            "success": True,
            "data": result.data,
            "message": f"系统整体健康评分: {result.data['overall_health_score']:.2f}"
        }
    except Exception as e:
        logger.error(f"获取完整健康状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取完整健康状态失败: {str(e)}")


@router.get("/complete-health/detailed")
async def get_detailed_health_status(
    service_name: Optional[str] = Query(None, description="特定服务名称")
):
    """获取详细的健康状态信息"""
    try:
        monitor = get_health_monitor()
        result = await monitor.get_detailed_health(service_name)

        if not result.success:
            raise HTTPException(status_code=500, detail=result.error.message)

        return {
            "success": True,
            "data": result.data,
            "message": f"获取{'服务 ' + service_name if service_name else '所有服务'}详细健康信息成功"
        }
    except Exception as e:
        logger.error(f"获取详细健康状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取详细健康状态失败: {str(e)}")


@router.get("/complete-health/history")
async def get_health_history(
    hours: int = Query(1, description="历史时间范围(小时)", ge=1, le=72)
):
    """获取健康状态历史"""
    try:
        monitor = get_health_monitor()
        result = await monitor.get_health_history(hours)

        if not result.success:
            raise HTTPException(status_code=500, detail=result.error.message)

        return {
            "success": True,
            "data": {
                "history": result.data,
                "period_hours": hours,
                "total_records": len(result.data)
            },
            "message": f"获取最近 {hours} 小时的健康历史成功"
        }
    except Exception as e:
        logger.error(f"获取健康历史失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取健康历史失败: {str(e)}")


@router.get("/complete-health/alerts")
async def get_active_alerts():
    """获取活跃告警"""
    try:
        monitor = get_health_monitor()
        result = await monitor.get_active_alerts()

        if not result.success:
            raise HTTPException(status_code=500, detail=result.error.message)

        return {
            "success": True,
            "data": {
                "alerts": result.data,
                "alert_count": len(result.data),
                "timestamp": datetime.now().isoformat()
            },
            "message": f"当前有 {len(result.data)} 个活跃告警"
        }
    except Exception as e:
        logger.error(f"获取活跃告警失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取活跃告警失败: {str(e)}")


@router.get("/complete-health/recommendations")
async def get_health_recommendations():
    """获取系统优化建议"""
    try:
        monitor = get_health_monitor()
        result = await monitor.get_recommendations()

        if not result.success:
            raise HTTPException(status_code=500, detail=result.error.message)

        return {
            "success": True,
            "data": {
                "recommendations": result.data,
                "recommendation_count": len(result.data),
                "generated_at": datetime.now().isoformat()
            },
            "message": f"生成了 {len(result.data)} 条优化建议"
        }
    except Exception as e:
        logger.error(f"获取优化建议失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取优化建议失败: {str(e)}")


@router.post("/complete-health/monitoring/start")
async def start_monitoring():
    """启动完整健康监控"""
    try:
        monitor = get_health_monitor()

        if monitor.running:
            return {
                "success": True,
                "data": {"already_running": True},
                "message": "完整健康监控已在运行"
            }

        await monitor.start()

        return {
            "success": True,
            "data": {
                "started": True,
                "monitoring_interval": monitor.config.check_interval,
                "auto_recovery_enabled": monitor.config.enable_auto_recovery
            },
            "message": "完整健康监控已启动"
        }
    except Exception as e:
        logger.error(f"启动完整健康监控失败: {e}")
        raise HTTPException(status_code=500, detail=f"启动完整健康监控失败: {str(e)}")


@router.post("/complete-health/monitoring/stop")
async def stop_monitoring():
    """停止完整健康监控"""
    try:
        monitor = get_health_monitor()

        if not monitor.running:
            return {
                "success": True,
                "data": {"already_stopped": True},
                "message": "完整健康监控未在运行"
            }

        await monitor.stop()

        return {
            "success": True,
            "data": {"stopped": True},
            "message": "完整健康监控已停止"
        }
    except Exception as e:
        logger.error(f"停止完整健康监控失败: {e}")
        raise HTTPException(status_code=500, detail=f"停止完整健康监控失败: {str(e)}")


@router.get("/complete-health/monitoring/config")
async def get_monitoring_config():
    """获取监控配置"""
    try:
        monitor = get_health_monitor()

        config_info = {
            "level": monitor.config.level.name,
            "check_interval": monitor.config.check_interval,
            "retention_period": monitor.config.retention_period,
            "enable_predictions": monitor.config.enable_predictions,
            "enable_auto_recovery": monitor.config.enable_auto_recovery,
            "enable_alerts": monitor.config.enable_alerts,
            "max_concurrent_checks": monitor.config.max_concurrent_checks,
            "batch_size": monitor.config.batch_size,
            "providers_count": len(monitor.providers),
            "alert_rules_count": len(monitor.alert_rules),
            "running": monitor.running
        }

        return {
            "success": True,
            "data": config_info,
            "message": "获取监控配置成功"
        }
    except Exception as e:
        logger.error(f"获取监控配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取监控配置失败: {str(e)}")


# ========== 自动恢复引擎API ==========

@router.get("/auto-recovery/status")
async def get_auto_recovery_status():
    """获取自动恢复引擎状态"""
    try:
        engine = get_auto_recovery_engine()
        stats = engine.get_recovery_stats()

        return {
            "success": True,
            "data": stats,
            "message": f"自动恢复引擎状态: {'运行中' if stats['running'] else '已停止'}"
        }
    except Exception as e:
        logger.error(f"获取自动恢复状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取自动恢复状态失败: {str(e)}")


@router.get("/auto-recovery/service-health")
async def get_service_health_summary():
    """获取服务健康摘要"""
    try:
        engine = get_auto_recovery_engine()
        summary = engine.get_service_health_summary()

        return {
            "success": True,
            "data": summary,
            "message": f"获取 {len(summary)} 个服务的健康摘要"
        }
    except Exception as e:
        logger.error(f"获取服务健康摘要失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取服务健康摘要失败: {str(e)}")


@router.post("/auto-recovery/register-service")
async def register_service_for_monitoring(
    service_name: str = Query(..., description="服务名称"),
    check_interval: float = Query(5.0, description="检查间隔(秒)", ge=1.0, le=300.0)
):
    """注册服务到自动恢复监控"""
    try:
        engine = get_auto_recovery_engine()
        engine.register_service(service_name, check_interval)

        return {
            "success": True,
            "data": {
                "service_name": service_name,
                "check_interval": check_interval,
                "registered": True
            },
            "message": f"服务 {service_name} 已注册到自动恢复监控"
        }
    except Exception as e:
        logger.error(f"注册服务失败: {e}")
        raise HTTPException(status_code=500, detail=f"注册服务失败: {str(e)}")


@router.post("/auto-recovery/start")
async def start_auto_recovery():
    """启动自动恢复引擎"""
    try:
        engine = get_auto_recovery_engine()

        if engine.running:
            return {
                "success": True,
                "data": {"already_running": True},
                "message": "自动恢复引擎已在运行"
            }

        await engine.start()

        return {
            "success": True,
            "data": {
                "started": True,
                "monitoring_interval": engine.monitoring_interval
            },
            "message": "自动恢复引擎已启动"
        }
    except Exception as e:
        logger.error(f"启动自动恢复引擎失败: {e}")
        raise HTTPException(status_code=500, detail=f"启动自动恢复引擎失败: {str(e)}")


@router.post("/auto-recovery/stop")
async def stop_auto_recovery():
    """停止自动恢复引擎"""
    try:
        engine = get_auto_recovery_engine()

        if not engine.running:
            return {
                "success": True,
                "data": {"already_stopped": True},
                "message": "自动恢复引擎未在运行"
            }

        await engine.stop()

        return {
            "success": True,
            "data": {"stopped": True},
            "message": "自动恢复引擎已停止"
        }
    except Exception as e:
        logger.error(f"停止自动恢复引擎失败: {e}")
        raise HTTPException(status_code=500, detail=f"停止自动恢复引擎失败: {str(e)}")


# ========== 综合健康分析API ==========

@router.get("/health-analysis/system-overview")
async def get_system_health_overview():
    """获取系统健康概览"""
    try:
        # 获取完整健康监控数据
        monitor = get_health_monitor()
        health_result = await monitor.get_current_health()

        # 获取自动恢复统计
        engine = get_auto_recovery_engine()
        recovery_stats = engine.get_recovery_stats()
        service_health = engine.get_service_health_summary()

        # 组合数据
        overview = {
            "health_monitoring": health_result.data if health_result.success else {},
            "auto_recovery": recovery_stats,
            "service_summary": service_health,
            "system_status": {
                "monitoring_active": monitor.running,
                "recovery_active": engine.running,
                "total_services": len(monitor.providers),
                "monitored_services": len(service_health),
                "last_update": datetime.now().isoformat()
            }
        }

        # 计算综合健康评分
        if health_result.success:
            overall_score = health_result.data.get('overall_health_score', 0.0)
            overall_status = health_result.data.get('overall_status', 'UNKNOWN')
        else:
            overall_score = 0.0
            overall_status = 'FAILED'

        return {
            "success": True,
            "data": overview,
            "metadata": {
                "overall_health_score": overall_score,
                "overall_status": overall_status,
                "recovery_success_rate": recovery_stats.get('success_rate', 0.0),
                "active_recoveries": recovery_stats.get('active_recoveries', 0)
            },
            "message": f"系统健康概览 - 整体评分: {overall_score:.2f}, 状态: {overall_status}"
        }
    except Exception as e:
        logger.error(f"获取系统健康概览失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取系统健康概览失败: {str(e)}")


@router.get("/health-analysis/performance-metrics")
async def get_performance_metrics():
    """获取性能指标分析"""
    try:
        monitor = get_health_monitor()

        # 获取监控性能指标
        monitoring_stats = {
            "check_count": monitor.check_count,
            "error_count": monitor.error_count,
            "total_check_time": monitor.total_check_time,
            "avg_check_time": monitor.total_check_time / max(1, monitor.check_count),
            "error_rate": monitor.error_count / max(1, monitor.check_count),
            "providers_count": len(monitor.providers)
        }

        # 获取恢复性能指标
        engine = get_auto_recovery_engine()
        recovery_stats = engine.get_recovery_stats()

        # 获取最近的健康历史
        history_result = await monitor.get_health_history(hours=1)
        recent_history = history_result.data if history_result.success else []

        return {
            "success": True,
            "data": {
                "monitoring_performance": monitoring_stats,
                "recovery_performance": recovery_stats,
                "recent_activity": {
                    "history_records": len(recent_history),
                    "latest_checks": recent_history[:10] if recent_history else []
                }
            },
            "message": "性能指标分析获取成功"
        }
    except Exception as e:
        logger.error(f"获取性能指标失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取性能指标失败: {str(e)}")


@router.post("/health-analysis/force-check")
async def force_health_check():
    """强制执行一次完整的健康检查"""
    try:
        monitor = get_health_monitor()

        # 如果监控未运行，执行一次性检查
        if not monitor.running:
            # 临时启动监控进行检查
            await monitor._perform_health_checks()
        else:
            # 监控运行中，获取当前状态
            pass

        # 获取检查结果
        result = await monitor.get_current_health()

        return {
            "success": True,
            "data": {
                "check_completed": True,
                "health_status": result.data if result.success else {},
                "timestamp": datetime.now().isoformat()
            },
            "message": "强制健康检查已完成"
        }
    except Exception as e:
        logger.error(f"强制健康检查失败: {e}")
        raise HTTPException(status_code=500, detail=f"强制健康检查失败: {str(e)}")