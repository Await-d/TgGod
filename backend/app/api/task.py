from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db
from ..models.rule import DownloadTask
from ..models.telegram import TelegramGroup
from ..models.rule import FilterRule
from ..services.task_execution_service import task_execution_service
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()

# Pydantic模型
class TaskCreate(BaseModel):
    name: str
    group_id: int
    rule_id: int
    download_path: str
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    
    # Jellyfin 配置
    use_jellyfin_structure: bool = False
    include_metadata: bool = True
    download_thumbnails: bool = True
    use_series_structure: bool = False
    organize_by_date: bool = True
    max_filename_length: int = 150
    thumbnail_size: str = "400x300"
    poster_size: str = "600x900"
    fanart_size: str = "1920x1080"

class TaskUpdate(BaseModel):
    name: Optional[str] = None
    download_path: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    
    # Jellyfin 配置
    use_jellyfin_structure: Optional[bool] = None
    include_metadata: Optional[bool] = None
    download_thumbnails: Optional[bool] = None
    use_series_structure: Optional[bool] = None
    organize_by_date: Optional[bool] = None
    max_filename_length: Optional[int] = None
    thumbnail_size: Optional[str] = None
    poster_size: Optional[str] = None
    fanart_size: Optional[str] = None

class TaskResponse(BaseModel):
    id: int
    name: str
    group_id: int
    rule_id: int
    status: str
    progress: int
    total_messages: int
    downloaded_messages: int
    download_path: str
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    
    # Jellyfin 配置
    use_jellyfin_structure: bool = False
    include_metadata: bool = True
    download_thumbnails: bool = True
    use_series_structure: bool = False
    organize_by_date: bool = True
    max_filename_length: int = 150
    thumbnail_size: str = "400x300"
    poster_size: str = "600x900"
    fanart_size: str = "1920x1080"
    
    created_at: datetime
    updated_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]
    
    class Config:
        from_attributes = True

@router.get("/tasks", response_model=List[TaskResponse])
async def get_tasks(
    group_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """获取下载任务列表"""
    query = db.query(DownloadTask)
    
    if group_id:
        query = query.filter(DownloadTask.group_id == group_id)
    
    if status:
        query = query.filter(DownloadTask.status == status)
    
    tasks = query.order_by(DownloadTask.created_at.desc()).offset(skip).limit(limit).all()
    return tasks

@router.post("/tasks", response_model=TaskResponse)
async def create_task(
    task: TaskCreate,
    db: Session = Depends(get_db)
):
    """创建下载任务"""
    # 检查群组是否存在
    group = db.query(TelegramGroup).filter(TelegramGroup.id == task.group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="群组不存在")
    
    # 检查规则是否存在
    rule = db.query(FilterRule).filter(FilterRule.id == task.rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    
    # 检查任务名称是否已存在
    existing_task = db.query(DownloadTask).filter(
        DownloadTask.name == task.name,
        DownloadTask.group_id == task.group_id
    ).first()
    if existing_task:
        raise HTTPException(status_code=400, detail="任务名称已存在")
    
    # 创建任务
    new_task = DownloadTask(**task.dict())
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    
    return new_task

@router.get("/tasks/stats")
async def get_task_stats(
    db: Session = Depends(get_db)
):
    """获取任务统计信息"""
    total_tasks = db.query(DownloadTask).count()
    running_tasks = db.query(DownloadTask).filter(DownloadTask.status == "running").count()
    completed_tasks = db.query(DownloadTask).filter(DownloadTask.status == "completed").count()
    failed_tasks = db.query(DownloadTask).filter(DownloadTask.status == "failed").count()
    
    return {
        "total": total_tasks,
        "running": running_tasks,
        "completed": completed_tasks,
        "failed": failed_tasks,
        "pending": total_tasks - running_tasks - completed_tasks - failed_tasks
    }

@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    db: Session = Depends(get_db)
):
    """获取单个任务"""
    task = db.query(DownloadTask).filter(DownloadTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task

@router.post("/tasks/{task_id}/start")
async def start_task(
    task_id: int,
    db: Session = Depends(get_db)
):
    """启动任务"""
    task = db.query(DownloadTask).filter(DownloadTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    if task.status == "running":
        raise HTTPException(status_code=400, detail="任务已在运行中")
    
    # 更新任务状态
    task.status = "running"
    task.progress = 0
    task.error_message = None
    db.commit()
    
    # 启动实际的下载任务
    try:
        success = await task_execution_service.start_task(task_id)
        if not success:
            task.status = "failed"
            task.error_message = "启动任务执行服务失败"
            db.commit()
            raise HTTPException(status_code=500, detail="启动任务执行服务失败")
    except Exception as e:
        task.status = "failed"
        task.error_message = f"启动任务失败: {str(e)}"
        db.commit()
        raise HTTPException(status_code=500, detail=f"启动任务失败: {str(e)}")
    
    return {"message": "任务启动成功"}

@router.post("/tasks/{task_id}/pause")
async def pause_task(
    task_id: int,
    db: Session = Depends(get_db)
):
    """暂停任务"""
    task = db.query(DownloadTask).filter(DownloadTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    if task.status != "running":
        raise HTTPException(status_code=400, detail="任务未运行，无法暂停")
    
    # 暂停实际的下载任务
    try:
        success = await task_execution_service.pause_task(task_id)
        if not success:
            raise HTTPException(status_code=400, detail="暂停任务失败，任务可能未在运行")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"暂停任务失败: {str(e)}")
    
    return {"message": "任务暂停成功"}

@router.post("/tasks/{task_id}/stop")
async def stop_task(
    task_id: int,
    db: Session = Depends(get_db)
):
    """停止任务"""
    task = db.query(DownloadTask).filter(DownloadTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    if task.status in ["completed", "failed"]:
        raise HTTPException(status_code=400, detail="任务已完成或失败，无法停止")
    
    # 停止实际的下载任务
    try:
        success = await task_execution_service.stop_task(task_id)
        if not success:
            raise HTTPException(status_code=400, detail="停止任务失败，任务可能未在运行")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"停止任务失败: {str(e)}")
    
    return {"message": "任务停止成功"}

@router.put("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_update: TaskUpdate,
    db: Session = Depends(get_db)
):
    """更新任务"""
    task = db.query(DownloadTask).filter(DownloadTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    if task.status == "running":
        raise HTTPException(status_code=400, detail="任务正在运行，无法更新")
    
    # 更新任务字段
    update_data = task_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)
    
    task.updated_at = datetime.now()
    db.commit()
    db.refresh(task)
    
    return task

@router.delete("/tasks/{task_id}")
async def delete_task(
    task_id: int,
    db: Session = Depends(get_db)
):
    """删除任务"""
    task = db.query(DownloadTask).filter(DownloadTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    if task.status == "running":
        raise HTTPException(status_code=400, detail="任务正在运行，无法删除")
    
    db.delete(task)
    db.commit()
    return {"message": "任务删除成功"}