"""
批处理日志性能监控API

提供批处理日志系统的性能指标监控和配置管理功能。

Features:
    - 实时性能指标查询
    - 日志配置动态调整
    - 系统资源使用监控
    - 批处理效率分析
    - 内存压力监控

Author: TgGod Team
Version: 1.0.0
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional
from pydantic import BaseModel
import json

router = APIRouter()


class BatchLoggingConfig(BaseModel):
    """批处理日志配置模型"""
    batch_size: int = 100
    flush_interval: float = 5.0
    max_buffer_size: int = 10000
    max_memory_mb: int = 50
    enable_metrics: bool = True
    enable_debug: bool = False


@router.get("/batch-logging/metrics")
async def get_batch_logging_metrics() -> Dict[str, Any]:
    """获取批处理日志性能指标

    Returns:
        Dict包含以下指标:
        - total_entries: 总处理条目数
        - total_batches: 总批次数
        - total_bytes_written: 总写入字节数
        - average_batch_size: 平均批次大小
        - throughput_per_sec: 吞吐量(条目/秒)
        - io_efficiency_mb_per_sec: I/O效率(MB/s)
        - buffer_overflows: 缓冲区溢出次数
        - memory_pressure_events: 内存压力事件数
        - emergency_flushes: 紧急刷新次数
        - failed_writes: 写入失败次数
        - peak_buffer_size: 峰值缓冲区大小
        - peak_memory_mb: 峰值内存使用(MB)
        - uptime_seconds: 运行时间(秒)
    """
    try:
        from ..core.batch_logging import get_batch_metrics

        metrics = get_batch_metrics("default")
        if metrics is None:
            return {
                "status": "unavailable",
                "message": "批处理日志系统未启用或未初始化",
                "metrics": {}
            }

        return {
            "status": "active",
            "message": "批处理日志性能指标",
            "metrics": metrics,
            "performance_analysis": _analyze_performance(metrics)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取批处理日志指标失败: {str(e)}")


@router.get("/batch-logging/config")
async def get_batch_logging_config() -> Dict[str, Any]:
    """获取当前批处理日志配置"""
    try:
        from ..config import settings

        config = {
            "enable_batch_logging": settings.enable_batch_logging,
            "log_batch_size": settings.log_batch_size,
            "log_flush_interval": settings.log_flush_interval,
            "log_max_buffer_size": settings.log_max_buffer_size,
            "log_max_memory_mb": settings.log_max_memory_mb,
            "log_level": settings.log_level,
            "log_file": settings.log_file
        }

        return {
            "status": "success",
            "config": config,
            "recommendations": _get_config_recommendations(config)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取配置失败: {str(e)}")


@router.post("/batch-logging/config")
async def update_batch_logging_config(config: BatchLoggingConfig) -> Dict[str, Any]:
    """动态更新批处理日志配置

    Args:
        config: 新的配置参数

    Returns:
        更新结果和生效状态
    """
    try:
        from ..core.batch_logging import configure_batch_logging

        # 验证配置参数
        if config.batch_size < 1 or config.batch_size > 10000:
            raise HTTPException(status_code=400, detail="batch_size必须在1-10000之间")

        if config.flush_interval < 0.1 or config.flush_interval > 300:
            raise HTTPException(status_code=400, detail="flush_interval必须在0.1-300秒之间")

        if config.max_buffer_size < config.batch_size:
            raise HTTPException(status_code=400, detail="max_buffer_size不能小于batch_size")

        # 应用新配置
        configure_batch_logging(
            batch_size=config.batch_size,
            flush_interval=config.flush_interval,
            max_buffer_size=config.max_buffer_size,
            max_memory_mb=config.max_memory_mb,
            enable_metrics=config.enable_metrics,
            enable_debug=config.enable_debug
        )

        return {
            "status": "success",
            "message": "批处理日志配置已更新",
            "applied_config": config.dict(),
            "note": "配置更新将在下次日志处理时生效"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新配置失败: {str(e)}")


@router.get("/batch-logging/status")
async def get_batch_logging_status() -> Dict[str, Any]:
    """获取批处理日志系统状态"""
    try:
        from ..core.batch_logging import BatchLogHandler

        # 检查批处理处理器状态
        handler = BatchLogHandler.get_instance("default")
        if handler is None:
            return {
                "status": "inactive",
                "message": "批处理日志系统未初始化",
                "processor_status": "not_found"
            }

        processor = handler._processor_ref()
        if processor is None:
            return {
                "status": "inactive",
                "message": "批处理日志处理器未运行",
                "processor_status": "stopped"
            }

        # 获取系统资源使用情况
        memory_info = processor.memory_monitor.get_current_memory_mb()
        buffer_size = processor.buffer.get_active_size()
        buffer_bytes = processor.buffer.get_buffer_size_bytes()

        return {
            "status": "active",
            "message": "批处理日志系统正常运行",
            "processor_status": "running",
            "system_info": {
                "current_memory_mb": round(memory_info, 2),
                "buffer_entries": buffer_size,
                "buffer_size_bytes": buffer_bytes,
                "memory_pressure": processor.memory_monitor.is_memory_pressure(),
                "emergency_memory": processor.memory_monitor.is_emergency_memory()
            },
            "config": {
                "batch_size": processor.config.batch_size,
                "flush_interval": processor.config.flush_interval,
                "max_buffer_size": processor.config.max_buffer_size,
                "max_memory_mb": processor.config.max_memory_mb
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")


@router.post("/batch-logging/flush")
async def force_flush_logs() -> Dict[str, Any]:
    """强制刷新日志缓冲区"""
    try:
        from ..core.batch_logging import BatchLogHandler

        handler = BatchLogHandler.get_instance("default")
        if handler is None:
            raise HTTPException(status_code=404, detail="批处理日志系统未初始化")

        processor = handler._processor_ref()
        if processor is None:
            raise HTTPException(status_code=404, detail="批处理日志处理器未运行")

        # 获取刷新前的状态
        before_buffer_size = processor.buffer.get_active_size()

        # 请求紧急刷新
        processor.request_emergency_flush()

        # 等待一小段时间让刷新完成
        import asyncio
        await asyncio.sleep(0.1)

        # 获取刷新后的状态
        after_buffer_size = processor.buffer.get_active_size()

        return {
            "status": "success",
            "message": "日志缓冲区刷新完成",
            "buffer_before": before_buffer_size,
            "buffer_after": after_buffer_size,
            "flushed_entries": max(0, before_buffer_size - after_buffer_size)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刷新失败: {str(e)}")


@router.get("/batch-logging/health")
async def check_batch_logging_health() -> Dict[str, Any]:
    """批处理日志系统健康检查"""
    try:
        from ..core.batch_logging import BatchLogHandler
        import time

        handler = BatchLogHandler.get_instance("default")
        if handler is None:
            return {
                "status": "unhealthy",
                "message": "批处理日志系统未初始化",
                "issues": ["系统未启动"]
            }

        processor = handler._processor_ref()
        if processor is None:
            return {
                "status": "unhealthy",
                "message": "批处理日志处理器已停止",
                "issues": ["处理器未运行"]
            }

        # 检查各项健康指标
        issues = []
        warnings = []

        # 检查内存使用
        if processor.memory_monitor.is_emergency_memory():
            issues.append("内存使用过高，触发紧急状态")
        elif processor.memory_monitor.is_memory_pressure():
            warnings.append("内存使用较高，接近阈值")

        # 检查缓冲区状态
        buffer_size = processor.buffer.get_active_size()
        max_buffer = processor.config.max_buffer_size
        buffer_usage = buffer_size / max_buffer

        if buffer_usage > 0.9:
            issues.append(f"缓冲区使用率过高: {buffer_usage:.1%}")
        elif buffer_usage > 0.7:
            warnings.append(f"缓冲区使用率较高: {buffer_usage:.1%}")

        # 检查失败率
        metrics = processor.get_metrics()
        if metrics["total_batches"] > 0:
            failure_rate = metrics["failed_writes"] / metrics["total_batches"]
            if failure_rate > 0.1:
                issues.append(f"写入失败率过高: {failure_rate:.1%}")
            elif failure_rate > 0.05:
                warnings.append(f"写入失败率较高: {failure_rate:.1%}")

        # 检查运行时间异常
        uptime = metrics["uptime_seconds"]
        if uptime < 60:  # 运行不到1分钟可能说明频繁重启
            warnings.append(f"系统运行时间较短: {uptime:.1f}秒")

        # 确定总体状态
        if issues:
            status = "unhealthy"
            message = f"发现 {len(issues)} 个严重问题"
        elif warnings:
            status = "warning"
            message = f"发现 {len(warnings)} 个警告"
        else:
            status = "healthy"
            message = "批处理日志系统运行正常"

        return {
            "status": status,
            "message": message,
            "issues": issues,
            "warnings": warnings,
            "timestamp": time.time(),
            "uptime_seconds": uptime
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"健康检查失败: {str(e)}",
            "issues": ["健康检查执行异常"]
        }


def _analyze_performance(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """分析性能指标并提供建议"""
    analysis = {
        "efficiency_rating": "unknown",
        "bottlenecks": [],
        "recommendations": []
    }

    try:
        # 分析吞吐量
        throughput = metrics.get("throughput_per_sec", 0)
        if throughput > 1000:
            analysis["efficiency_rating"] = "excellent"
        elif throughput > 500:
            analysis["efficiency_rating"] = "good"
        elif throughput > 100:
            analysis["efficiency_rating"] = "moderate"
        else:
            analysis["efficiency_rating"] = "poor"
            analysis["bottlenecks"].append("低吞吐量")
            analysis["recommendations"].append("考虑增加批次大小或减少刷新间隔")

        # 分析I/O效率
        io_efficiency = metrics.get("io_efficiency_mb_per_sec", 0)
        if io_efficiency < 1:
            analysis["bottlenecks"].append("I/O效率低")
            analysis["recommendations"].append("检查磁盘性能或增加写入工作线程数")

        # 分析内存使用
        overflow_rate = 0
        total_batches = metrics.get("total_batches", 1)
        if total_batches > 0:
            overflow_rate = metrics.get("buffer_overflows", 0) / total_batches
            if overflow_rate > 0.05:
                analysis["bottlenecks"].append("频繁缓冲区溢出")
                analysis["recommendations"].append("增加缓冲区大小或减少刷新间隔")

        # 分析失败率
        failure_rate = 0
        if total_batches > 0:
            failure_rate = metrics.get("failed_writes", 0) / total_batches
            if failure_rate > 0.01:
                analysis["bottlenecks"].append("写入失败率高")
                analysis["recommendations"].append("检查磁盘空间和文件权限")

        # 分析平均批次大小效率
        avg_batch_size = metrics.get("average_batch_size", 0)
        if avg_batch_size < 50:
            analysis["recommendations"].append("考虑增加批次大小以提高I/O效率")

    except Exception:
        pass  # 静默处理分析错误

    return analysis


def _get_config_recommendations(config: Dict[str, Any]) -> Dict[str, str]:
    """根据当前配置提供优化建议"""
    recommendations = {}

    try:
        batch_size = config.get("log_batch_size", 100)
        flush_interval = config.get("log_flush_interval", 5.0)
        max_buffer_size = config.get("log_max_buffer_size", 10000)

        # 批次大小建议
        if batch_size < 50:
            recommendations["batch_size"] = "建议增加到50-200以提高I/O效率"
        elif batch_size > 500:
            recommendations["batch_size"] = "批次过大可能增加内存压力，建议减少到200-500"

        # 刷新间隔建议
        if flush_interval < 2.0:
            recommendations["flush_interval"] = "刷新间隔过短可能影响性能，建议设置为2-10秒"
        elif flush_interval > 30.0:
            recommendations["flush_interval"] = "刷新间隔过长可能影响日志实时性，建议设置为5-30秒"

        # 缓冲区大小建议
        ratio = max_buffer_size / batch_size
        if ratio < 10:
            recommendations["buffer_size"] = "缓冲区相对批次大小过小，建议增加到批次大小的10-50倍"
        elif ratio > 100:
            recommendations["buffer_size"] = "缓冲区过大可能占用过多内存，建议控制在批次大小的50倍以内"

    except Exception:
        pass

    return recommendations