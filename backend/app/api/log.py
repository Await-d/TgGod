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
    db: Session = Depends(get_db)
):
    """获取日志统计信息"""
    # 任务日志统计
    task_log_count = db.query(TaskLog).count()
    task_error_count = db.query(TaskLog).filter(TaskLog.level == "ERROR").count()
    
    # 系统日志统计
    system_log_count = db.query(SystemLog).count()
    system_error_count = db.query(SystemLog).filter(SystemLog.level == "ERROR").count()
    
    return {
        "task_logs": {
            "total": task_log_count,
            "errors": task_error_count
        },
        "system_logs": {
            "total": system_log_count,
            "errors": system_error_count
        },
        "total_logs": task_log_count + system_log_count,
        "total_errors": task_error_count + system_error_count
    }