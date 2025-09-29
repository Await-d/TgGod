from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import time
import logging

from ..database import get_db
from ..models.telegram import TelegramGroup, TelegramMessage
from ..models.user import User
from ..utils.auth import get_current_active_user

logger = logging.getLogger(__name__)
router = APIRouter()

# 缓存设置
CACHE_TTL = 300  # 5分钟缓存
_dashboard_cache: Dict[str, Dict[str, Any]] = {}

def get_cached_data(cache_key: str, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
    """获取缓存数据"""
    if force_refresh:
        return None
    
    current_time = time.time()
    if cache_key in _dashboard_cache:
        cached_data = _dashboard_cache[cache_key]
        if current_time - cached_data["timestamp"] < CACHE_TTL:
            return cached_data["data"]
    return None

def set_cached_data(cache_key: str, data: Dict[str, Any]):
    """设置缓存数据"""
    _dashboard_cache[cache_key] = {
        "data": data,
        "timestamp": time.time()
    }

@router.get("/overview")
async def get_dashboard_overview(
    db: Session = Depends(get_db),
    force_refresh: bool = Query(False, description="强制刷新缓存"),
    current_user: User = Depends(get_current_active_user)
):
    """获取仪表盘概览数据"""
    
    cache_key = "dashboard_overview"
    cached_data = get_cached_data(cache_key, force_refresh)
    if cached_data:
        logger.info("返回缓存的仪表盘概览数据")
        return cached_data
    
    try:
        # 基础统计
        total_groups = db.query(TelegramGroup).count()
        active_groups = db.query(TelegramGroup).filter(TelegramGroup.is_active == True).count()
        total_messages = db.query(TelegramMessage).count()
        
        # 媒体统计
        media_messages = db.query(TelegramMessage).filter(
            TelegramMessage.media_type.isnot(None)
        ).count()
        
        downloaded_media = db.query(TelegramMessage).filter(
            TelegramMessage.media_downloaded == True
        ).count()
        
        # 今日数据（最近24小时）
        yesterday = datetime.now() - timedelta(days=1)
        today_messages = db.query(TelegramMessage).filter(
            TelegramMessage.created_at >= yesterday
        ).count()
        
        today_media_downloads = db.query(TelegramMessage).filter(
            and_(
                TelegramMessage.media_downloaded == True,
                TelegramMessage.updated_at >= yesterday
            )
        ).count()
        
        # 存储统计
        total_media_size = db.query(func.sum(TelegramMessage.media_size)).filter(
            TelegramMessage.media_downloaded == True
        ).scalar() or 0
        
        # 消息类型分布
        message_types = db.query(
            TelegramMessage.media_type,
            func.count(TelegramMessage.id).label('count')
        ).filter(
            TelegramMessage.media_type.isnot(None)
        ).group_by(TelegramMessage.media_type).all()
        
        media_distribution = {media_type: count for media_type, count in message_types}
        
        # 下载进度中的任务（模拟，基于有下载进度但未完成的消息）
        downloading_tasks = db.query(TelegramMessage).filter(
            and_(
                TelegramMessage.download_progress > 0,
                TelegramMessage.download_progress < 100,
                TelegramMessage.media_downloaded == False
            )
        ).count()
        
        overview_data = {
            "basic_stats": {
                "total_groups": total_groups,
                "active_groups": active_groups,
                "total_messages": total_messages,
                "media_messages": media_messages,
                "text_messages": total_messages - media_messages
            },
            "download_stats": {
                "downloaded_media": downloaded_media,
                "total_media_size": total_media_size,
                "downloading_tasks": downloading_tasks,
                "download_completion_rate": round((downloaded_media / media_messages * 100) if media_messages > 0 else 0, 2)
            },
            "today_stats": {
                "new_messages": today_messages,
                "new_downloads": today_media_downloads
            },
            "media_distribution": media_distribution,
            "last_updated": datetime.now().isoformat()
        }
        
        # 缓存数据
        set_cached_data(cache_key, overview_data)
        
        return overview_data
        
    except Exception as e:
        logger.error(f"获取仪表盘概览数据失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取仪表盘概览数据失败: {str(e)}")

@router.get("/groups-summary")
async def get_groups_summary(
    db: Session = Depends(get_db),
    limit: int = Query(10, ge=1, le=50),
    force_refresh: bool = Query(False),
    current_user: User = Depends(get_current_active_user)
):
    """获取群组汇总信息"""
    
    cache_key = f"groups_summary_{limit}"
    cached_data = get_cached_data(cache_key, force_refresh)
    if cached_data:
        return cached_data
    
    try:
        # 获取群组消息统计
        groups_stats = db.query(
            TelegramGroup.id,
            TelegramGroup.title,
            TelegramGroup.username,
            TelegramGroup.member_count,
            TelegramGroup.is_active,
            func.count(TelegramMessage.id).label('message_count'),
            func.count(func.nullif(TelegramMessage.media_type, None)).label('media_count'),
            func.count(func.nullif(TelegramMessage.media_downloaded, False)).label('downloaded_count'),
            func.max(TelegramMessage.date).label('last_message_date')
        ).outerjoin(
            TelegramMessage, TelegramGroup.id == TelegramMessage.group_id
        ).group_by(
            TelegramGroup.id
        ).order_by(
            desc('message_count')
        ).limit(limit).all()
        
        groups_data = []
        for group_stat in groups_stats:
            groups_data.append({
                "group_id": group_stat.id,
                "title": group_stat.title,
                "username": group_stat.username,
                "member_count": group_stat.member_count,
                "is_active": group_stat.is_active,
                "message_count": group_stat.message_count,
                "media_count": group_stat.media_count,
                "downloaded_count": group_stat.downloaded_count,
                "download_rate": round((group_stat.downloaded_count / group_stat.media_count * 100) if group_stat.media_count > 0 else 0, 2),
                "last_message_date": group_stat.last_message_date.isoformat() if group_stat.last_message_date else None
            })
        
        summary_data = {
            "groups": groups_data,
            "total_groups": db.query(TelegramGroup).count(),
            "last_updated": datetime.now().isoformat()
        }
        
        set_cached_data(cache_key, summary_data)
        return summary_data
        
    except Exception as e:
        logger.error(f"获取群组汇总信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取群组汇总信息失败: {str(e)}")

@router.get("/recent-activity")
async def get_recent_activity(
    db: Session = Depends(get_db),
    hours: int = Query(24, ge=1, le=168, description="最近几小时的活动"),
    limit: int = Query(20, ge=1, le=100),
    force_refresh: bool = Query(False),
    current_user: User = Depends(get_current_active_user)
):
    """获取最近活动"""
    
    cache_key = f"recent_activity_{hours}_{limit}"
    cached_data = get_cached_data(cache_key, force_refresh)
    if cached_data:
        return cached_data
    
    try:
        since_time = datetime.now() - timedelta(hours=hours)
        
        # 最近的消息
        recent_messages = db.query(
            TelegramMessage.id,
            TelegramMessage.group_id,
            TelegramMessage.message_id,
            TelegramMessage.sender_name,
            TelegramMessage.text,
            TelegramMessage.media_type,
            TelegramMessage.date,
            TelegramGroup.title.label('group_title')
        ).join(
            TelegramGroup, TelegramMessage.group_id == TelegramGroup.id
        ).filter(
            TelegramMessage.date >= since_time
        ).order_by(
            desc(TelegramMessage.date)
        ).limit(limit).all()
        
        # 最近的下载
        recent_downloads = db.query(
            TelegramMessage.id,
            TelegramMessage.group_id,
            TelegramMessage.message_id,
            TelegramMessage.media_filename,
            TelegramMessage.media_type,
            TelegramMessage.media_size,
            TelegramMessage.updated_at,
            TelegramGroup.title.label('group_title')
        ).join(
            TelegramGroup, TelegramMessage.group_id == TelegramGroup.id
        ).filter(
            and_(
                TelegramMessage.media_downloaded == True,
                TelegramMessage.updated_at >= since_time
            )
        ).order_by(
            desc(TelegramMessage.updated_at)
        ).limit(limit).all()
        
        # 格式化数据
        messages_data = []
        for msg in recent_messages:
            messages_data.append({
                "id": msg.id,
                "group_id": msg.group_id,
                "group_title": msg.group_title,
                "message_id": msg.message_id,
                "sender_name": msg.sender_name,
                "text": msg.text[:100] + "..." if msg.text and len(msg.text) > 100 else msg.text,
                "media_type": msg.media_type,
                "date": msg.date.isoformat(),
                "type": "message"
            })
        
        downloads_data = []
        for download in recent_downloads:
            downloads_data.append({
                "id": download.id,
                "group_id": download.group_id,
                "group_title": download.group_title,
                "message_id": download.message_id,
                "filename": download.media_filename,
                "media_type": download.media_type,
                "size": download.media_size,
                "date": download.updated_at.isoformat(),
                "type": "download"
            })
        
        activity_data = {
            "recent_messages": messages_data,
            "recent_downloads": downloads_data,
            "time_range_hours": hours,
            "last_updated": datetime.now().isoformat()
        }
        
        set_cached_data(cache_key, activity_data)
        return activity_data
        
    except Exception as e:
        logger.error(f"获取最近活动失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取最近活动失败: {str(e)}")

@router.get("/download-stats")
async def get_download_statistics(
    db: Session = Depends(get_db),
    days: int = Query(7, ge=1, le=365),
    force_refresh: bool = Query(False),
    current_user: User = Depends(get_current_active_user)
):
    """获取下载统计信息"""
    
    cache_key = f"download_stats_{days}"
    cached_data = get_cached_data(cache_key, force_refresh)
    if cached_data:
        return cached_data
    
    try:
        since_date = datetime.now() - timedelta(days=days)
        
        # 按日期统计下载量
        daily_downloads = db.query(
            func.date(TelegramMessage.updated_at).label('date'),
            func.count(TelegramMessage.id).label('count'),
            func.sum(TelegramMessage.media_size).label('total_size')
        ).filter(
            and_(
                TelegramMessage.media_downloaded == True,
                TelegramMessage.updated_at >= since_date
            )
        ).group_by(
            func.date(TelegramMessage.updated_at)
        ).order_by('date').all()
        
        # 按媒体类型统计
        downloads_by_type = db.query(
            TelegramMessage.media_type,
            func.count(TelegramMessage.id).label('count'),
            func.sum(TelegramMessage.media_size).label('total_size')
        ).filter(
            and_(
                TelegramMessage.media_downloaded == True,
                TelegramMessage.updated_at >= since_date
            )
        ).group_by(TelegramMessage.media_type).all()
        
        # 下载速度统计（基于有记录的下载）
        avg_download_speed = db.query(
            func.avg(TelegramMessage.download_speed)
        ).filter(
            and_(
                TelegramMessage.download_speed > 0,
                TelegramMessage.updated_at >= since_date
            )
        ).scalar() or 0
        
        # 格式化数据
        daily_data = []
        for daily in daily_downloads:
            # 处理日期格式，确保正确序列化
            if hasattr(daily.date, 'isoformat'):
                date_str = daily.date.isoformat()
            else:
                date_str = str(daily.date)
            
            daily_data.append({
                "date": date_str,
                "downloads_count": daily.count,  # 匹配前端期望的字段名
                "total_size": daily.total_size or 0,
                "completion_rate": 100.0  # 这些都是已完成的下载
            })
        
        type_data = {}
        for type_stat in downloads_by_type:
            type_data[type_stat.media_type] = {
                "count": type_stat.count,
                "total_size": type_stat.total_size or 0
            }
        
        stats_data = {
            "daily_stats": daily_data,  # 匹配前端期望的字段名
            "downloads_by_type": type_data,
            "average_download_speed": round(avg_download_speed, 2),
            "time_range_days": days,
            "last_updated": datetime.now().isoformat()
        }
        
        set_cached_data(cache_key, stats_data)
        return stats_data
        
    except Exception as e:
        logger.error(f"获取下载统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取下载统计失败: {str(e)}")

@router.get("/system-info")
async def get_system_info(
    db: Session = Depends(get_db),
    force_refresh: bool = Query(False),
    current_user: User = Depends(get_current_active_user)
):
    """获取系统信息"""
    
    cache_key = "system_info"
    cached_data = get_cached_data(cache_key, force_refresh)
    if cached_data:
        return cached_data
    
    try:
        import os
        from ..config import settings
        
        # 数据库统计
        db_stats = {
            "total_groups": db.query(TelegramGroup).count(),
            "total_messages": db.query(TelegramMessage).count(),
            "media_files": db.query(TelegramMessage).filter(TelegramMessage.media_type.isnot(None)).count()
        }
        
        # 尝试获取系统资源信息
        try:
            import psutil
            
            # 磁盘使用情况
            media_root = getattr(settings, 'media_root', './media')
            disk_usage = None
            try:
                if os.path.exists(media_root):
                    disk_info = psutil.disk_usage(media_root)
                    # 确保返回的是3个值
                    if len(disk_info) == 3:
                        total, used, free = disk_info
                        disk_usage = {
                            "total": total,
                            "used": used,
                            "free": free,
                            "usage_percent": round((used / total) * 100, 2) if total > 0 else 0
                        }
                    else:
                        logger.warning(f"psutil.disk_usage返回了{len(disk_info)}个值，期望3个")
                else:
                    logger.warning(f"媒体目录不存在: {media_root}")
            except Exception as disk_error:
                logger.error(f"获取磁盘使用情况失败: {disk_error}")
                disk_usage = None
            
            # 内存使用情况
            memory = psutil.virtual_memory()
            memory_info = {
                "total": memory.total,
                "available": memory.available,
                "used": memory.used,
                "usage_percent": memory.percent
            }
            
            # CPU使用情况
            cpu_percent = psutil.cpu_percent(interval=1)
            
        except ImportError:
            logger.error("psutil模块未安装，无法获取系统资源信息")
            # 返回空数据而不是模拟数据
            disk_usage = None
            memory_info = None
            cpu_percent = None
        
        system_data = {
            "database": db_stats,
            "disk_usage": disk_usage, 
            "memory": memory_info,
            "cpu_percent": cpu_percent,
            "cpu_usage": cpu_percent if cpu_percent is not None else 0,  # 兼容前端字段名
            "memory_usage": memory_info["usage_percent"] if memory_info else 0,  # 兼容前端字段名
            "disk_usage_percent": disk_usage["usage_percent"] if disk_usage else 0,  # 兼容前端字段名
            "total_memory": memory_info["total"] if memory_info else 0,
            "available_memory": memory_info["available"] if memory_info else 0,
            "total_disk": disk_usage["total"] if disk_usage else 0,
            "free_disk": disk_usage["free"] if disk_usage else 0,
            "media_root": getattr(settings, 'media_root', './media'),
            "psutil_available": True,  # 标记psutil已安装
            "last_updated": datetime.now().isoformat()
        }
        
        set_cached_data(cache_key, system_data)
        return system_data
        
    except Exception as e:
        logger.error(f"获取系统信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取系统信息失败: {str(e)}")

@router.get("/storage-analysis")
async def get_storage_analysis(
    db: Session = Depends(get_db),
    force_refresh: bool = Query(False),
    current_user: User = Depends(get_current_active_user)
):
    """获取存储空间详细分析"""

    cache_key = "storage_analysis"
    cached_data = get_cached_data(cache_key, force_refresh)
    if cached_data:
        return cached_data

    try:
        # 按媒体类型统计存储使用情况
        storage_by_type = db.query(
            TelegramMessage.media_type,
            func.count(TelegramMessage.id).label('file_count'),
            func.sum(TelegramMessage.media_size).label('total_size'),
            func.avg(TelegramMessage.media_size).label('avg_size'),
            func.max(TelegramMessage.media_size).label('max_size'),
            func.min(TelegramMessage.media_size).label('min_size')
        ).filter(
            and_(
                TelegramMessage.media_downloaded == True,
                TelegramMessage.media_size > 0
            )
        ).group_by(TelegramMessage.media_type).all()

        # 按群组统计存储使用情况
        storage_by_group = db.query(
            TelegramGroup.id,
            TelegramGroup.title,
            func.count(TelegramMessage.id).label('file_count'),
            func.sum(TelegramMessage.media_size).label('total_size')
        ).join(
            TelegramMessage, TelegramGroup.id == TelegramMessage.group_id
        ).filter(
            and_(
                TelegramMessage.media_downloaded == True,
                TelegramMessage.media_size > 0
            )
        ).group_by(
            TelegramGroup.id, TelegramGroup.title
        ).order_by(
            desc(func.sum(TelegramMessage.media_size))
        ).limit(10).all()

        # 计算总存储统计
        total_stats = db.query(
            func.count(TelegramMessage.id).label('total_files'),
            func.sum(TelegramMessage.media_size).label('total_size'),
            func.avg(TelegramMessage.media_size).label('avg_file_size')
        ).filter(
            and_(
                TelegramMessage.media_downloaded == True,
                TelegramMessage.media_size > 0
            )
        ).first()

        # 格式化数据
        type_analysis = []
        for type_stat in storage_by_type:
            if type_stat.media_type:
                type_analysis.append({
                    "media_type": type_stat.media_type,
                    "file_count": type_stat.file_count,
                    "total_size": type_stat.total_size or 0,
                    "avg_size": round(type_stat.avg_size or 0, 2),
                    "max_size": type_stat.max_size or 0,
                    "min_size": type_stat.min_size or 0,
                    "size_percentage": round((type_stat.total_size / total_stats.total_size * 100) if total_stats.total_size > 0 else 0, 2)
                })

        group_analysis = []
        for group_stat in storage_by_group:
            group_analysis.append({
                "group_id": group_stat.id,
                "group_title": group_stat.title,
                "file_count": group_stat.file_count,
                "total_size": group_stat.total_size or 0,
                "size_percentage": round((group_stat.total_size / total_stats.total_size * 100) if total_stats.total_size > 0 else 0, 2)
            })

        analysis_data = {
            "total_statistics": {
                "total_files": total_stats.total_files or 0,
                "total_size": total_stats.total_size or 0,
                "average_file_size": round(total_stats.avg_file_size or 0, 2)
            },
            "storage_by_type": type_analysis,
            "top_groups_by_storage": group_analysis,
            "analysis_timestamp": datetime.now().isoformat()
        }

        set_cached_data(cache_key, analysis_data)
        return analysis_data

    except Exception as e:
        logger.error(f"获取存储分析失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取存储分析失败: {str(e)}")

@router.delete("/cache")
async def clear_dashboard_cache(
    current_user: User = Depends(get_current_active_user)
):
    """清除仪表盘缓存"""
    try:
        global _dashboard_cache
        _dashboard_cache.clear()
        return {
            "success": True,
            "message": "仪表盘缓存已清除",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"清除缓存失败: {e}")
        raise HTTPException(status_code=500, detail=f"清除缓存失败: {str(e)}")