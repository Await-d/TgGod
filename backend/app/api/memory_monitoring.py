"""
内存监控API端点

提供内存使用监控、性能分析和告警管理的REST API
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import asyncio

from ..services.memory_monitoring_service import memory_monitoring_service
from ..core.memory_manager import memory_manager
from ..core.object_lifecycle_manager import lifecycle_manager

router = APIRouter(prefix="/api/memory", tags=["memory"])


@router.get("/status")
async def get_memory_status():
    """获取当前内存状态"""
    try:
        stats = memory_monitoring_service.get_memory_statistics()

        return {
            "status": "success",
            "data": {
                "memory_stats": stats,
                "manager_stats": memory_manager.get_stats(),
                "lifecycle_stats": lifecycle_manager.get_lifecycle_stats(),
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取内存状态失败: {str(e)}")


@router.get("/history")
async def get_memory_history(
    hours: int = 24,
    limit: int = 100
):
    """获取内存使用历史"""
    try:
        stats = memory_monitoring_service.get_memory_statistics()
        history = stats.get('memory_trend', [])

        # 根据时间范围过滤
        if hours > 0:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            history = [
                item for item in history
                if datetime.fromisoformat(item['timestamp']) >= cutoff_time
            ]

        # 限制返回数量
        if limit > 0:
            history = history[-limit:]

        return {
            "status": "success",
            "data": {
                "history": history,
                "total_records": len(history),
                "time_range_hours": hours
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取内存历史失败: {str(e)}")


@router.get("/alerts")
async def get_memory_alerts(limit: int = 50):
    """获取内存告警历史"""
    try:
        stats = memory_monitoring_service.get_memory_statistics()
        alerts = stats.get('recent_alerts', [])

        if limit > 0:
            alerts = alerts[-limit:]

        return {
            "status": "success",
            "data": {
                "alerts": alerts,
                "total_alerts": len(alerts)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取内存告警失败: {str(e)}")


@router.post("/cleanup")
async def force_memory_cleanup():
    """强制执行内存清理"""
    try:
        cleanup_results = memory_monitoring_service.force_cleanup()

        return {
            "status": "success",
            "data": {
                "cleanup_results": cleanup_results,
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"内存清理失败: {str(e)}")


@router.get("/analysis")
async def get_memory_analysis():
    """获取内存使用分析"""
    try:
        # 获取各种统计信息
        manager_stats = memory_manager.get_stats()
        lifecycle_stats = lifecycle_manager.get_lifecycle_stats()
        monitoring_stats = memory_monitoring_service.get_memory_statistics()
        service_usage = memory_monitoring_service.get_service_memory_usage()

        # 计算分析数据
        analysis = {
            "memory_efficiency": {
                "cache_hit_ratio": manager_stats.get('cache', {}).get('hit_ratio', 0),
                "object_reuse_ratio": _calculate_object_reuse_ratio(lifecycle_stats),
                "memory_growth_rate": _calculate_memory_growth_rate(monitoring_stats),
                "cleanup_effectiveness": _calculate_cleanup_effectiveness(monitoring_stats)
            },
            "resource_usage": {
                "tracked_objects": lifecycle_stats.get('tracked_objects_count', 0),
                "object_pools": lifecycle_stats.get('object_pools_count', 0),
                "cache_usage_mb": manager_stats.get('cache', {}).get('memory_usage_mb', 0),
                "peak_memory_mb": monitoring_stats.get('peak_memory_mb', 0)
            },
            "service_breakdown": service_usage,
            "recommendations": _generate_recommendations(manager_stats, lifecycle_stats, monitoring_stats)
        }

        return {
            "status": "success",
            "data": analysis
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"内存分析失败: {str(e)}")


@router.post("/optimize")
async def optimize_memory():
    """执行内存优化"""
    try:
        optimization_results = {}

        # 1. 清理缓存
        cache_stats_before = memory_manager.global_cache.get_stats()
        memory_manager.global_cache.clear()
        cache_stats_after = memory_manager.global_cache.get_stats()

        optimization_results['cache_cleanup'] = {
            'items_cleared': cache_stats_before['size'],
            'memory_freed_mb': cache_stats_before['memory_usage_mb']
        }

        # 2. 强制对象清理
        lifecycle_manager.force_cleanup()

        # 3. 执行垃圾回收
        import gc
        collected = gc.collect()
        optimization_results['garbage_collection'] = {
            'objects_collected': collected
        }

        # 4. 清理服务缓存
        cleanup_results = memory_monitoring_service.force_cleanup()
        optimization_results['service_cleanup'] = cleanup_results

        return {
            "status": "success",
            "data": {
                "optimization_results": optimization_results,
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"内存优化失败: {str(e)}")


@router.get("/config")
async def get_memory_config():
    """获取内存监控配置"""
    try:
        config = {
            "monitoring": {
                "check_interval": memory_monitoring_service.check_interval,
                "warning_threshold": memory_monitoring_service.warning_threshold,
                "critical_threshold": memory_monitoring_service.critical_threshold,
                "auto_cleanup_threshold": memory_monitoring_service.auto_cleanup_threshold
            },
            "cache": {
                "max_size": memory_manager.global_cache.max_size,
                "max_memory_mb": memory_manager.global_cache.max_memory_bytes / 1024 / 1024
            },
            "lifecycle": {
                "max_idle_time": lifecycle_manager.max_idle_time,
                "cleanup_interval": lifecycle_manager.cleanup_interval
            }
        }

        return {
            "status": "success",
            "data": config
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取配置失败: {str(e)}")


@router.put("/config")
async def update_memory_config(config: Dict[str, Any]):
    """更新内存监控配置"""
    try:
        updated_fields = []

        # 更新监控配置
        if "monitoring" in config:
            monitoring_config = config["monitoring"]
            if "warning_threshold" in monitoring_config:
                memory_monitoring_service.warning_threshold = monitoring_config["warning_threshold"]
                updated_fields.append("warning_threshold")
            if "critical_threshold" in monitoring_config:
                memory_monitoring_service.critical_threshold = monitoring_config["critical_threshold"]
                updated_fields.append("critical_threshold")
            if "auto_cleanup_threshold" in monitoring_config:
                memory_monitoring_service.auto_cleanup_threshold = monitoring_config["auto_cleanup_threshold"]
                updated_fields.append("auto_cleanup_threshold")

        # 更新生命周期配置
        if "lifecycle" in config:
            lifecycle_config = config["lifecycle"]
            if "max_idle_time" in lifecycle_config:
                lifecycle_manager.max_idle_time = lifecycle_config["max_idle_time"]
                updated_fields.append("max_idle_time")
            if "cleanup_interval" in lifecycle_config:
                lifecycle_manager.cleanup_interval = lifecycle_config["cleanup_interval"]
                updated_fields.append("cleanup_interval")

        return {
            "status": "success",
            "data": {
                "updated_fields": updated_fields,
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新配置失败: {str(e)}")


@router.get("/services")
async def get_service_memory_usage():
    """获取各服务的内存使用情况"""
    try:
        service_usage = memory_monitoring_service.get_service_memory_usage()

        return {
            "status": "success",
            "data": {
                "services": service_usage,
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取服务内存使用失败: {str(e)}")


@router.post("/services/{service_name}/cleanup")
async def cleanup_service_memory(service_name: str):
    """清理特定服务的内存"""
    try:
        service_usage = memory_monitoring_service.get_service_memory_usage()

        if service_name not in service_usage:
            raise HTTPException(status_code=404, detail=f"服务 {service_name} 未找到")

        # 获取服务缓存对象
        cache_obj = memory_monitoring_service.cleanup_registry.service_caches.get(service_name)
        if cache_obj and hasattr(cache_obj, 'clear'):
            cache_obj.clear()

        return {
            "status": "success",
            "data": {
                "service_name": service_name,
                "cleanup_completed": True,
                "timestamp": datetime.now().isoformat()
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清理服务内存失败: {str(e)}")


def _calculate_object_reuse_ratio(lifecycle_stats: Dict[str, Any]) -> float:
    """计算对象复用率"""
    try:
        pool_stats = lifecycle_stats.get('pool_stats', {})
        if not pool_stats:
            return 0.0

        total_reused = sum(stats.get('reused_count', 0) for stats in pool_stats.values())
        total_created = sum(stats.get('created_count', 0) for stats in pool_stats.values())

        if total_created == 0:
            return 0.0

        return total_reused / total_created
    except:
        return 0.0


def _calculate_memory_growth_rate(monitoring_stats: Dict[str, Any]) -> float:
    """计算内存增长率"""
    try:
        trend = monitoring_stats.get('memory_trend', [])
        if len(trend) < 2:
            return 0.0

        # 计算最近的内存增长率
        recent_data = trend[-10:]  # 最近10个数据点
        if len(recent_data) < 2:
            return 0.0

        start_memory = recent_data[0]['process_memory_mb']
        end_memory = recent_data[-1]['process_memory_mb']

        return (end_memory - start_memory) / start_memory * 100
    except:
        return 0.0


def _calculate_cleanup_effectiveness(monitoring_stats: Dict[str, Any]) -> float:
    """计算清理效果"""
    try:
        total_cleanups = monitoring_stats.get('total_cleanups', 0)
        if total_cleanups == 0:
            return 0.0

        # 简单的效果评估 - 基于清理次数和内存峰值
        peak_memory = monitoring_stats.get('peak_memory_mb', 0)
        current_memory = monitoring_stats.get('current_memory_mb', 0)

        if peak_memory == 0:
            return 0.0

        # 计算内存回收效果
        effectiveness = (peak_memory - current_memory) / peak_memory * 100
        return max(0.0, min(100.0, effectiveness))
    except:
        return 0.0


def _generate_recommendations(
    manager_stats: Dict[str, Any],
    lifecycle_stats: Dict[str, Any],
    monitoring_stats: Dict[str, Any]
) -> List[str]:
    """生成优化建议"""
    recommendations = []

    try:
        # 基于缓存命中率的建议
        cache_stats = manager_stats.get('cache', {})
        hit_ratio = cache_stats.get('hit_ratio', 0)
        if hit_ratio < 0.5:
            recommendations.append("缓存命中率较低，考虑调整缓存策略或增加缓存大小")

        # 基于内存使用的建议
        current_memory = monitoring_stats.get('current_memory_mb', 0)
        peak_memory = monitoring_stats.get('peak_memory_mb', 0)
        if current_memory > 0 and peak_memory > 0:
            usage_ratio = current_memory / peak_memory
            if usage_ratio > 0.8:
                recommendations.append("当前内存使用接近峰值，建议执行内存清理")

        # 基于对象数量的建议
        tracked_objects = lifecycle_stats.get('tracked_objects_count', 0)
        if tracked_objects > 1000:
            recommendations.append("跟踪的对象数量较多，考虑优化对象生命周期管理")

        # 基于清理频率的建议
        total_cleanups = monitoring_stats.get('total_cleanups', 0)
        uptime_hours = monitoring_stats.get('uptime_hours', 0)
        if uptime_hours > 0 and total_cleanups / uptime_hours < 0.1:
            recommendations.append("自动清理频率较低，考虑降低清理阈值")

        # 基于对象复用率的建议
        reuse_ratio = _calculate_object_reuse_ratio(lifecycle_stats)
        if reuse_ratio < 0.3:
            recommendations.append("对象复用率较低，考虑增加对象池的使用")

        if not recommendations:
            recommendations.append("内存使用情况良好，无需特别优化")

    except Exception as e:
        recommendations.append(f"生成建议时出错: {str(e)}")

    return recommendations