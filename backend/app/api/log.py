from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db
from ..models.log import TaskLog, SystemLog
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()

# Pydantic模型
class LogResponse(BaseModel):
    id: int
    level: str
    message: str
    created_at: datetime
    task_id: Optional[int] = None
    details: Optional[dict] = None

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
    
    logs = query.order_by(TaskLog.created_at.desc()).offset(skip).limit(limit).all()
    return logs

@router.get("/logs/system", response_model=List[SystemLogResponse])
async def get_system_logs(
    level: Optional[str] = Query(None),
    module: Optional[str] = Query(None),
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
        }
    }