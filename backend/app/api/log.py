from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db
from ..models.log import TaskLog, SystemLog  
from pydantic import BaseModel
from datetime import datetime
import logging

router = APIRouter()

# Pydantic模型
class LogResponse(BaseModel):
    id: int
    level: str
    message: str
    created_at: datetime
    task_id: Optional[int] = None
    details: Optional[dict] = None
    timestamp: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class SystemLogResponse(BaseModel):
    id: int
    level: str
    message: str
    module: Optional[str]
    function: Optional[str]
    details: Optional[dict]
    created_at: datetime

class BatchDeleteRequest(BaseModel):
    log_ids: List[int]

@router.get("/logs/task", response_model=List[LogResponse])
async def get_task_logs(
    task_id: Optional[int] = Query(None),
    level: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """获取任务日志"""
    query = db.query(TaskLog)
    
    if task_id:
        query = query.filter(TaskLog.task_id == task_id)
    
    if level:
        query = query.filter(TaskLog.level == level.upper())
    
    if search:
        query = query.filter(TaskLog.message.contains(search))
    
    logs = query.order_by(TaskLog.created_at.desc()).offset(skip).limit(limit).all()
    return logs

@router.get("/logs/system", response_model=List[SystemLogResponse])
async def get_system_logs(
    level: Optional[str] = Query(None),
    module: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """获取系统日志"""
    query = db.query(SystemLog)
    
    if level:
        query = query.filter(SystemLog.level == level.upper())
    
    if module:
        query = query.filter(SystemLog.module == module)
        
    if search:
        query = query.filter(SystemLog.message.contains(search))
    
    logs = query.order_by(SystemLog.created_at.desc()).offset(skip).limit(limit).all()
    return logs

@router.delete("/logs/task")
async def clear_task_logs(
    task_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """清除任务日志"""
    query = db.query(TaskLog)
    
    if task_id:
        query = query.filter(TaskLog.task_id == task_id)
    
    count = query.count()
    query.delete()
    db.commit()
    
    return {"message": f"成功清除 {count} 条任务日志"}

@router.delete("/logs/system")
async def clear_system_logs(
    module: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """清除系统日志"""
    query = db.query(SystemLog)
    
    if module:
        query = query.filter(SystemLog.module == module)
    
    count = query.count()
    query.delete()
    db.commit()
    
    return {"message": f"成功清除 {count} 条系统日志"}

# 添加系统日志记录功能
logger = logging.getLogger(__name__)

@router.post("/logs/system")
async def add_system_log(
    level: str,
    message: str,
    module: str = None,
    function: str = None,
    details: dict = None,
    db: Session = Depends(get_db)
):
    """添加系统日志"""
    try:
        log_entry = SystemLog(
            level=level.upper(),
            message=message,
            module=module,
            function=function,
            details=details
        )
        db.add(log_entry)
        db.commit()
        
        return {
            "success": True,
            "message": "系统日志添加成功",
            "log_id": log_entry.id
        }
    except Exception as e:
        logger.error(f"添加系统日志失败: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"添加系统日志失败: {str(e)}")

@router.get("/logs/recent")
async def get_recent_logs(
    limit: int = Query(100, ge=1, le=1000),
    log_type: str = Query("all"),  # all, task, system
    db: Session = Depends(get_db)
):
    """获取最近的日志"""
    recent_logs = []
    
    try:
        if log_type in ["all", "task"]:
            task_logs = db.query(TaskLog).order_by(TaskLog.created_at.desc()).limit(limit//2 if log_type == "all" else limit).all()
            for log in task_logs:
                recent_logs.append({
                    "id": log.id,
                    "type": "task",
                    "level": log.level,
                    "message": log.message,
                    "task_id": log.task_id,
                    "details": log.details,
                    "created_at": log.created_at,
                    "timestamp": log.created_at
                })
        
        if log_type in ["all", "system"]:
            system_logs = db.query(SystemLog).order_by(SystemLog.created_at.desc()).limit(limit//2 if log_type == "all" else limit).all() 
            for log in system_logs:
                recent_logs.append({
                    "id": log.id,
                    "type": "system",
                    "level": log.level,
                    "message": log.message,
                    "module": log.module,
                    "function": log.function,
                    "details": log.details,
                    "created_at": log.created_at,
                    "timestamp": log.created_at
                })
        
        # 按时间排序
        recent_logs.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return recent_logs[:limit]
        
    except Exception as e:
        logger.error(f"获取最近日志失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取最近日志失败: {str(e)}")

@router.get("/logs/stats")
async def get_log_stats(
    start_time: Optional[str] = Query(None),
    end_time: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """获取日志统计信息"""
    try:
        # 任务日志统计
        task_query = db.query(TaskLog)
        if start_time:
            task_query = task_query.filter(TaskLog.created_at >= start_time)
        if end_time:
            task_query = task_query.filter(TaskLog.created_at <= end_time)
            
        task_log_count = task_query.count()
        task_error_count = task_query.filter(TaskLog.level == "ERROR").count()
        task_warning_count = task_query.filter(TaskLog.level == "WARNING").count()
        task_info_count = task_query.filter(TaskLog.level == "INFO").count()
        task_debug_count = task_query.filter(TaskLog.level == "DEBUG").count()
        
        # 系统日志统计
        system_query = db.query(SystemLog)
        if start_time:
            system_query = system_query.filter(SystemLog.created_at >= start_time)
        if end_time:
            system_query = system_query.filter(SystemLog.created_at <= end_time)
            
        system_log_count = system_query.count()
        system_error_count = system_query.filter(SystemLog.level == "ERROR").count()
        system_warning_count = system_query.filter(SystemLog.level == "WARNING").count()
        system_info_count = system_query.filter(SystemLog.level == "INFO").count()
        system_debug_count = system_query.filter(SystemLog.level == "DEBUG").count()
        
        return {
            "task_logs": {
                "total": task_log_count,
                "errors": task_error_count,
                "warnings": task_warning_count,
                "info": task_info_count,
                "debug": task_debug_count
            },
            "system_logs": {
                "total": system_log_count,
                "errors": system_error_count,
                "warnings": system_warning_count,
                "info": system_info_count,
                "debug": system_debug_count
            },
            "total_logs": task_log_count + system_log_count,
            "total_errors": task_error_count + system_error_count,
            "total_warnings": task_warning_count + system_warning_count,
            "total_info": task_info_count + system_info_count,
            "total_debug": task_debug_count + system_debug_count
        }
        
    except Exception as e:
        logger.error(f"获取日志统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取日志统计失败: {str(e)}")

@router.delete("/logs/batch")
async def delete_logs_batch(
    request: BatchDeleteRequest,
    db: Session = Depends(get_db)
):
    """批量删除日志"""
    try:
        log_ids = request.log_ids
        # 删除任务日志
        task_deleted = db.query(TaskLog).filter(TaskLog.id.in_(log_ids)).delete(synchronize_session=False)
        # 删除系统日志  
        system_deleted = db.query(SystemLog).filter(SystemLog.id.in_(log_ids)).delete(synchronize_session=False)
        
        db.commit()
        total_deleted = task_deleted + system_deleted
        
        return {
            "success": True,
            "message": f"成功删除 {total_deleted} 条日志",
            "deleted_count": total_deleted
        }
        
    except Exception as e:
        logger.error(f"批量删除日志失败: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"批量删除日志失败: {str(e)}")

@router.post("/logs/export")
async def export_logs(
    log_type: str = "all",
    level: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    start_time: Optional[str] = Query(None),
    end_time: Optional[str] = Query(None),
    format: str = "json",
    db: Session = Depends(get_db)
):
    """导出日志"""
    import tempfile
    import json
    import csv
    import os
    from datetime import datetime
    
    try:
        logs_data = []
        
        # 获取任务日志
        if log_type in ["all", "task"]:
            task_query = db.query(TaskLog)
            if level:
                task_query = task_query.filter(TaskLog.level == level.upper())
            if search:
                task_query = task_query.filter(TaskLog.message.contains(search))
            if start_time:
                task_query = task_query.filter(TaskLog.created_at >= start_time)
            if end_time:
                task_query = task_query.filter(TaskLog.created_at <= end_time)
                
            task_logs = task_query.order_by(TaskLog.created_at.desc()).all()
            for log in task_logs:
                logs_data.append({
                    "id": log.id,
                    "type": "task",
                    "level": log.level,
                    "message": log.message,
                    "task_id": log.task_id,
                    "details": log.details,
                    "created_at": log.created_at.isoformat()
                })
        
        # 获取系统日志
        if log_type in ["all", "system"]:
            system_query = db.query(SystemLog)
            if level:
                system_query = system_query.filter(SystemLog.level == level.upper())
            if search:
                system_query = system_query.filter(SystemLog.message.contains(search))
            if start_time:
                system_query = system_query.filter(SystemLog.created_at >= start_time)
            if end_time:
                system_query = system_query.filter(SystemLog.created_at <= end_time)
                
            system_logs = system_query.order_by(SystemLog.created_at.desc()).all()
            for log in system_logs:
                logs_data.append({
                    "id": log.id,
                    "type": "system",
                    "level": log.level,
                    "message": log.message,
                    "module": log.module,
                    "function": log.function,
                    "details": log.details,
                    "created_at": log.created_at.isoformat()
                })
        
        # 按时间排序
        logs_data.sort(key=lambda x: x["created_at"], reverse=True)
        
        # 生成文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"logs_{timestamp}.{format}"
        
        # 创建临时文件
        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, filename)
        
        if format == "json":
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(logs_data, f, ensure_ascii=False, indent=2)
        elif format == "csv":
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                if logs_data:
                    fieldnames = logs_data[0].keys()
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(logs_data)
        elif format == "txt":
            with open(file_path, 'w', encoding='utf-8') as f:
                for log in logs_data:
                    f.write(f"[{log['created_at']}] {log['level']} - {log['message']}\\n")
                    if log.get('details'):
                        f.write(f"Details: {json.dumps(log['details'], ensure_ascii=False)}\\n")
                    f.write("\\n")
        
        # 返回下载信息（简化实现，实际应该通过文件服务器提供下载）
        return {
            "download_url": f"/static/temp/{filename}",
            "filename": filename,
            "size": os.path.getsize(file_path)
        }
        
    except Exception as e:
        logger.error(f"导出日志失败: {e}")
        raise HTTPException(status_code=500, detail=f"导出日志失败: {str(e)}")