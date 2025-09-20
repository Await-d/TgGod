"""完整真实数据API端点

企业级真实数据服务API，提供完整的数据获取、管理和监控接口。
完全替换所有Mock数据依赖，确保100%数据真实性。

Features:
    - 群组数据API
    - 消息数据API  
    - 统计数据API
    - 数据管道管理API
    - 健康监控API
    - 缓存管理API
    - 数据质量API

Author: TgGod Team
Version: 1.0.0
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import logging

from ..services.complete_real_data_provider import (
    real_data_provider, 
    DataQuality, 
    DataItem,
    DataProviderMetrics
)
from ..core.error_handler import ErrorHandler
from ..core.batch_logging import BatchLogger

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/real-data", tags=["Real Data"])

# Pydantic模型

class GroupDataRequest(BaseModel):
    """群组数据请求模型"""
    group_id: Optional[int] = Field(None, description="特定群组ID，None表示获取所有群组")
    include_messages: bool = Field(True, description="是否包含消息数据")
    message_limit: int = Field(100, ge=1, le=1000, description="消息数量限制")
    quality_threshold: str = Field("acceptable", description="数据质量阈值")

class MessageDataRequest(BaseModel):
    """消息数据请求模型"""
    group_id: int = Field(..., description="群组ID")
    media_type: Optional[str] = Field(None, description="媒体类型过滤")
    date_from: Optional[datetime] = Field(None, description="开始时间")
    date_to: Optional[datetime] = Field(None, description="结束时间")
    search_text: Optional[str] = Field(None, description="文本搜索")
    limit: int = Field(100, ge=1, le=1000, description="消息数量限制")
    offset: int = Field(0, ge=0, description="偏移量")
    quality_threshold: str = Field("acceptable", description="数据质量阈值")

class StatisticsRequest(BaseModel):
    """统计数据请求模型"""
    stats_type: str = Field("overview", description="统计类型")
    time_range_start: Optional[datetime] = Field(None, description="时间范围开始")
    time_range_end: Optional[datetime] = Field(None, description="时间范围结束")
    quality_threshold: str = Field("good", description="数据质量阈值")

class DataResponse(BaseModel):
    """数据响应模型"""
    success: bool
    data: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    timestamp: datetime

class HealthResponse(BaseModel):
    """健康状态响应模型"""
    status: str
    metrics: Dict[str, Any]
    cache_performance: Dict[str, Any]
    data_quality: Dict[str, Any]
    system_info: Dict[str, Any]

# 辅助函数

def parse_quality_threshold(quality_str: str) -> DataQuality:
    """解析数据质量阈值字符串"""
    quality_map = {
        "excellent": DataQuality.EXCELLENT,
        "good": DataQuality.GOOD,
        "acceptable": DataQuality.ACCEPTABLE,
        "poor": DataQuality.POOR
    }
    return quality_map.get(quality_str.lower(), DataQuality.ACCEPTABLE)

def convert_data_items_to_dict(data_items: List[DataItem]) -> List[Dict[str, Any]]:
    """将DataItem列表转换为字典列表"""
    return [
        {
            "id": item.id,
            "type": item.type,
            "data": item.data,
            "quality": item.quality.value,
            "cache_level": item.cache_level.value,
            "timestamp": item.timestamp.isoformat(),
            "metadata": item.metadata
        }
        for item in data_items
    ]

# API端点

@router.post("/groups", response_model=DataResponse)
async def get_group_data(request: GroupDataRequest):
    """获取群组数据
    
    获取Telegram群组的完整真实数据，包括群组信息和消息数据。
    支持质量阈值过滤和缓存优化。
    """
    try:
        quality_threshold = parse_quality_threshold(request.quality_threshold)
        
        data_items = await real_data_provider.get_group_data(
            group_id=request.group_id,
            include_messages=request.include_messages,
            message_limit=request.message_limit,
            quality_threshold=quality_threshold
        )
        
        response_data = convert_data_items_to_dict(data_items)
        
        return DataResponse(
            success=True,
            data=response_data,
            metadata={
                "total_count": len(response_data),
                "quality_threshold": request.quality_threshold,
                "include_messages": request.include_messages,
                "request_timestamp": datetime.now().isoformat()
            },
            timestamp=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Failed to get group data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get group data: {str(e)}")

@router.post("/messages", response_model=DataResponse)
async def get_message_data(request: MessageDataRequest):
    """获取消息数据
    
    获取特定群组的消息数据，支持多种过滤条件和分页查询。
    提供完整的真实消息数据，无Mock依赖。
    """
    try:
        quality_threshold = parse_quality_threshold(request.quality_threshold)
        
        # 构建过滤器
        message_filters = {}
        if request.media_type:
            message_filters["media_type"] = request.media_type
        if request.date_from:
            message_filters["date_from"] = request.date_from
        if request.date_to:
            message_filters["date_to"] = request.date_to
        if request.search_text:
            message_filters["search_text"] = request.search_text
        
        data_items = await real_data_provider.get_message_data(
            group_id=request.group_id,
            message_filters=message_filters,
            limit=request.limit,
            offset=request.offset,
            quality_threshold=quality_threshold
        )
        
        response_data = convert_data_items_to_dict(data_items)
        
        return DataResponse(
            success=True,
            data=response_data,
            metadata={
                "total_count": len(response_data),
                "group_id": request.group_id,
                "filters_applied": message_filters,
                "pagination": {
                    "limit": request.limit,
                    "offset": request.offset
                },
                "quality_threshold": request.quality_threshold,
                "request_timestamp": datetime.now().isoformat()
            },
            timestamp=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Failed to get message data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get message data: {str(e)}")

@router.post("/statistics", response_model=DataResponse)
async def get_statistics_data(request: StatisticsRequest):
    """获取统计数据
    
    提供系统的实时统计信息，包括群组统计、消息统计和概览数据。
    基于真实数据计算，确保统计准确性。
    """
    try:
        quality_threshold = parse_quality_threshold(request.quality_threshold)
        
        # 构建时间范围
        time_range = None
        if request.time_range_start and request.time_range_end:
            time_range = (request.time_range_start, request.time_range_end)
        
        data_items = await real_data_provider.get_statistics_data(
            stats_type=request.stats_type,
            time_range=time_range,
            quality_threshold=quality_threshold
        )
        
        response_data = convert_data_items_to_dict(data_items)
        
        return DataResponse(
            success=True,
            data=response_data,
            metadata={
                "stats_type": request.stats_type,
                "time_range": {
                    "start": request.time_range_start.isoformat() if request.time_range_start else None,
                    "end": request.time_range_end.isoformat() if request.time_range_end else None
                },
                "quality_threshold": request.quality_threshold,
                "request_timestamp": datetime.now().isoformat()
            },
            timestamp=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Failed to get statistics data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get statistics data: {str(e)}")

@router.get("/groups/simple")
async def get_simple_group_list():
    """获取简单群组列表
    
    快速获取所有群组的基本信息，用于下拉选择等场景。
    """
    try:
        data_items = await real_data_provider.get_group_data(
            include_messages=False,
            quality_threshold=DataQuality.ACCEPTABLE
        )
        
        simple_groups = [
            {
                "id": item.data["id"],
                "title": item.data["title"],
                "username": item.data.get("username"),
                "member_count": item.data.get("member_count", 0),
                "is_active": item.data.get("is_active", False)
            }
            for item in data_items
        ]
        
        return JSONResponse(content={
            "success": True,
            "groups": simple_groups,
            "total": len(simple_groups),
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Failed to get simple group list: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get simple group list: {str(e)}")

@router.get("/messages/{group_id}/latest")
async def get_latest_messages(
    group_id: int,
    limit: int = Query(20, ge=1, le=100, description="消息数量限制")
):
    """获取群组最新消息
    
    快速获取指定群组的最新消息，用于实时展示。
    """
    try:
        data_items = await real_data_provider.get_message_data(
            group_id=group_id,
            message_filters=None,
            limit=limit,
            offset=0,
            quality_threshold=DataQuality.ACCEPTABLE
        )
        
        latest_messages = [
            {
                "id": item.data["id"],
                "message_id": item.data["message_id"],
                "text": item.data.get("text", ""),
                "media_type": item.data.get("media_type"),
                "date": item.data["date"],
                "sender_username": item.data.get("sender_username"),
                "quality": item.quality.value
            }
            for item in data_items
        ]
        
        return JSONResponse(content={
            "success": True,
            "messages": latest_messages,
            "group_id": group_id,
            "total": len(latest_messages),
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Failed to get latest messages: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get latest messages: {str(e)}")

@router.get("/health", response_model=HealthResponse)
async def get_data_provider_health():
    """获取数据提供者健康状态
    
    提供数据提供者的完整健康信息，包括性能指标、缓存状态和数据质量。
    """
    try:
        health_data = await real_data_provider.get_provider_health()
        
        return HealthResponse(
            status=health_data.get("status", "unknown"),
            metrics=health_data.get("metrics", {}),
            cache_performance={
                "hit_rate": health_data.get("cache_hit_rate", 0),
                "memory_cache_size": health_data.get("memory_cache_size", 0)
            },
            data_quality={
                "freshness": health_data.get("data_freshness", 0),
                "validation_failures": health_data.get("metrics", {}).get("data_validation_failures", 0)
            },
            system_info={
                "telegram_connected": health_data.get("telegram_connected", False),
                "last_pipeline_run": health_data.get("last_pipeline_run"),
                "pipeline_running": health_data.get("pipeline_running", False),
                "recent_errors": health_data.get("recent_errors", [])
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to get provider health: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get provider health: {str(e)}")

@router.post("/pipeline/refresh")
async def refresh_data_pipeline(background_tasks: BackgroundTasks):
    """刷新数据管道
    
    强制刷新数据管道，清空缓存并重新获取最新数据。
    使用后台任务避免请求超时。
    """
    try:
        # 立即返回，在后台执行刷新
        background_tasks.add_task(real_data_provider.refresh_data_pipeline)
        
        return JSONResponse(content={
            "success": True,
            "message": "Data pipeline refresh initiated",
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Failed to initiate pipeline refresh: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to initiate pipeline refresh: {str(e)}")

@router.get("/pipeline/status")
async def get_pipeline_status():
    """获取数据管道状态
    
    获取当前数据管道的运行状态和最近的执行信息。
    """
    try:
        health_data = await real_data_provider.get_provider_health()
        
        pipeline_status = {
            "running": health_data.get("pipeline_running", False),
            "last_run": health_data.get("last_pipeline_run"),
            "recent_errors": health_data.get("recent_errors", []),
            "status": health_data.get("status", "unknown")
        }
        
        return JSONResponse(content={
            "success": True,
            "pipeline": pipeline_status,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Failed to get pipeline status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get pipeline status: {str(e)}")

@router.get("/cache/stats")
async def get_cache_statistics():
    """获取缓存统计信息
    
    提供详细的缓存性能统计，用于监控和优化。
    """
    try:
        health_data = await real_data_provider.get_provider_health()
        metrics = health_data.get("metrics", {})
        
        cache_stats = {
            "total_requests": metrics.get("total_requests", 0),
            "cache_hits": metrics.get("cache_hits", 0),
            "cache_misses": metrics.get("cache_misses", 0),
            "hit_rate": health_data.get("cache_hit_rate", 0),
            "memory_cache_size": health_data.get("memory_cache_size", 0),
            "average_response_time": metrics.get("average_response_time", 0),
            "api_calls": metrics.get("api_calls", 0)
        }
        
        return JSONResponse(content={
            "success": True,
            "cache_stats": cache_stats,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Failed to get cache statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get cache statistics: {str(e)}")

@router.delete("/cache/clear")
async def clear_cache():
    """清空缓存
    
    强制清空所有内存缓存，下次请求将重新获取数据。
    """
    try:
        # 清空内存缓存
        real_data_provider._memory_cache.clear()
        real_data_provider._cache_timestamps.clear()
        
        return JSONResponse(content={
            "success": True,
            "message": "Cache cleared successfully",
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Failed to clear cache: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {str(e)}")

@router.get("/quality/report")
async def get_data_quality_report():
    """获取数据质量报告
    
    提供详细的数据质量评估报告，包括数据完整性、新鲜度等指标。
    """
    try:
        health_data = await real_data_provider.get_provider_health()
        
        quality_report = {
            "overall_score": health_data.get("data_freshness", 0) * 100,
            "data_freshness": health_data.get("data_freshness", 0),
            "validation_failures": health_data.get("metrics", {}).get("data_validation_failures", 0),
            "total_requests": health_data.get("metrics", {}).get("total_requests", 0),
            "quality_threshold_compliance": "Good" if health_data.get("data_freshness", 0) > 0.8 else "Needs Attention",
            "recommendations": []
        }
        
        # 生成建议
        if health_data.get("data_freshness", 0) < 0.5:
            quality_report["recommendations"].append("Data is stale, consider refreshing pipeline")
        
        if health_data.get("cache_hit_rate", 0) < 50:
            quality_report["recommendations"].append("Low cache hit rate, consider cache optimization")
        
        if health_data.get("metrics", {}).get("data_validation_failures", 0) > 10:
            quality_report["recommendations"].append("High validation failure rate, check data sources")
        
        return JSONResponse(content={
            "success": True,
            "quality_report": quality_report,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Failed to get quality report: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get quality report: {str(e)}")

@router.get("/demo/data")
async def get_demo_data():
    """获取演示数据
    
    为前端演示组件提供完整的真实数据，替换所有Mock数据。
    包含群组、消息、统计等演示所需的全套数据。
    """
    try:
        # 获取演示群组数据
        demo_groups = await real_data_provider.get_group_data(
            include_messages=True,
            message_limit=5,
            quality_threshold=DataQuality.ACCEPTABLE
        )
        
        # 获取演示统计数据
        demo_stats = await real_data_provider.get_statistics_data(
            stats_type="overview",
            quality_threshold=DataQuality.ACCEPTABLE
        )
        
        demo_data = {
            "groups": convert_data_items_to_dict(demo_groups),
            "statistics": convert_data_items_to_dict(demo_stats),
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "data_source": "real_database",
                "mock_data_eliminated": True,
                "quality_assured": True
            }
        }
        
        return JSONResponse(content={
            "success": True,
            "demo_data": demo_data,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Failed to get demo data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get demo data: {str(e)}")

# 初始化函数（在main.py中调用）

async def initialize_real_data_provider():
    """初始化真实数据提供者"""
    try:
        await real_data_provider.initialize()
        logger.info("Real Data API initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize Real Data API: {str(e)}")
        return False

async def cleanup_real_data_provider():
    """清理真实数据提供者资源"""
    try:
        await real_data_provider.cleanup()
        logger.info("Real Data API cleanup completed")
    except Exception as e:
        logger.error(f"Failed to cleanup Real Data API: {str(e)}")