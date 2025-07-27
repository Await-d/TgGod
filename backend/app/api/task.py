from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db
from ..models.rule import DownloadTask
from ..models.telegram import TelegramGroup
from ..models.rule import FilterRule
from ..services.task_execution_service import task_execution_service
from ..services.mock_task_execution_service import mock_task_execution_service
from pydantic import BaseModel
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

def get_task_execution_service():
    """获取可用的任务执行服务（优先使用真实服务，否则使用Mock服务）"""
    try:
        # 检查真实服务是否可用
        if hasattr(task_execution_service, '_initialized') and task_execution_service._initialized:
            return task_execution_service
        else:
            logger.warning("使用Mock任务执行服务")
            return mock_task_execution_service
    except Exception as e:
        logger.warning(f"真实任务执行服务不可用，使用Mock服务: {e}")
        return mock_task_execution_service

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
    
    # 调度配置
    task_type: Optional[str] = "once"
    schedule_type: Optional[str] = None
    schedule_config: Optional[dict] = None
    max_runs: Optional[int] = None

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
    
    # 调度配置
    task_type: Optional[str] = None
    schedule_type: Optional[str] = None
    schedule_config: Optional[dict] = None
    max_runs: Optional[int] = None

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
    
    # 调度配置
    task_type: Optional[str] = "once"
    schedule_type: Optional[str] = None
    schedule_config: Optional[dict] = None
    next_run_time: Optional[datetime] = None
    last_run_time: Optional[datetime] = None
    is_active: Optional[bool] = True
    max_runs: Optional[int] = None
    run_count: Optional[int] = 0
    
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
    try:
        query = db.query(DownloadTask)
        
        if group_id:
            query = query.filter(DownloadTask.group_id == group_id)
        
        if status:
            query = query.filter(DownloadTask.status == status)
        
        tasks = query.order_by(DownloadTask.created_at.desc()).offset(skip).limit(limit).all()
        return tasks
    except Exception as e:
        logger.error(f"查询任务列表失败: {str(e)}")
        # 如果是数据库结构问题，返回空列表
        if "no such column" in str(e).lower() or "unknown column" in str(e).lower():
            logger.warning("检测到数据库结构问题，建议重启应用以触发自动修复")
            return []
        raise HTTPException(status_code=500, detail=f"查询任务失败: {str(e)}")

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
    try:
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
    except Exception as e:
        logger.error(f"获取任务统计失败: {str(e)}")
        # 如果是数据库结构问题，返回默认统计
        if "no such column" in str(e).lower() or "unknown column" in str(e).lower():
            logger.warning("检测到数据库结构问题，返回默认统计信息")
            return {
                "total": 0,
                "running": 0,
                "completed": 0,
                "failed": 0,
                "pending": 0
            }
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")

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
        execution_service = get_task_execution_service()
        success = await execution_service.start_task(task_id)
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
        execution_service = get_task_execution_service()
        success = await execution_service.pause_task(task_id)
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
        execution_service = get_task_execution_service()
        success = await execution_service.stop_task(task_id)
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

@router.post("/tasks/{task_id}/restart")
async def restart_task(
    task_id: int,
    db: Session = Depends(get_db)
):
    """重启任务 - 停止当前任务并重新开始"""
    task = db.query(DownloadTask).filter(DownloadTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 如果任务正在运行，先停止它
    if task.status == "running":
        try:
            execution_service = get_task_execution_service()
            await execution_service.stop_task(task_id)
            logger.info(f"任务 {task_id} 已停止，准备重启")
        except Exception as e:
            logger.error(f"停止任务 {task_id} 失败: {e}")
    
    # 重置任务状态
    task.status = "pending"
    task.progress = 0
    task.downloaded_messages = 0
    task.error_message = None
    task.updated_at = datetime.now()
    db.commit()
    
    # 启动任务
    try:
        execution_service = get_task_execution_service()
        success = await execution_service.start_task(task_id)
        if not success:
            task.status = "failed"
            task.error_message = "重启任务失败"
            db.commit()
            raise HTTPException(status_code=500, detail="重启任务失败")
        
        task.status = "running"
        db.commit()
        logger.info(f"任务 {task_id} 重启成功")
        
    except Exception as e:
        task.status = "failed"
        task.error_message = f"重启任务失败: {str(e)}"
        db.commit()
        logger.error(f"重启任务 {task_id} 失败: {e}")
        raise HTTPException(status_code=500, detail=f"重启任务失败: {str(e)}")
    
    return {"message": "任务重启成功"}

@router.post("/tasks/{task_id}/retry")
async def retry_task(
    task_id: int,
    db: Session = Depends(get_db)
):
    """重试失败的任务"""
    task = db.query(DownloadTask).filter(DownloadTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 只有失败的任务才能重试
    if task.status not in ["failed", "completed", "stopped"]:
        raise HTTPException(status_code=400, detail="只有失败、完成或停止的任务才能重试")
    
    # 重置任务状态但保留进度信息
    original_downloaded = task.downloaded_messages or 0
    task.status = "pending"
    task.error_message = None
    task.updated_at = datetime.now()
    db.commit()
    
    # 启动任务
    try:
        execution_service = get_task_execution_service()
        success = await execution_service.start_task(task_id)
        if not success:
            task.status = "failed"
            task.error_message = "重试任务失败"
            db.commit()
            raise HTTPException(status_code=500, detail="重试任务失败")
        
        task.status = "running"
        db.commit()
        logger.info(f"任务 {task_id} 重试成功，从 {original_downloaded} 个文件开始继续")
        
    except Exception as e:
        task.status = "failed"
        task.error_message = f"重试任务失败: {str(e)}"
        db.commit()
        logger.error(f"重试任务 {task_id} 失败: {e}")
        raise HTTPException(status_code=500, detail=f"重试任务失败: {str(e)}")
    
    return {"message": f"任务重试成功，从第 {original_downloaded + 1} 个文件开始继续"}

@router.post("/tasks/{task_id}/resume")
async def resume_task(
    task_id: int,
    db: Session = Depends(get_db)
):
    """恢复暂停的任务"""
    task = db.query(DownloadTask).filter(DownloadTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 只有暂停的任务才能恢复
    if task.status != "paused":
        raise HTTPException(status_code=400, detail="只有暂停的任务才能恢复")
    
    # 恢复任务
    try:
        execution_service = get_task_execution_service()
        success = await execution_service.start_task(task_id)
        if not success:
            task.error_message = "恢复任务失败"
            db.commit()
            raise HTTPException(status_code=500, detail="恢复任务失败")
        
        task.status = "running"
        task.updated_at = datetime.now()
        db.commit()
        logger.info(f"任务 {task_id} 恢复成功")
        
    except Exception as e:
        task.error_message = f"恢复任务失败: {str(e)}"
        db.commit()
        logger.error(f"恢复任务 {task_id} 失败: {e}")
        raise HTTPException(status_code=500, detail=f"恢复任务失败: {str(e)}")
    
    return {"message": "任务恢复成功"}

@router.post("/tasks/{task_id}/reset")
async def reset_task(
    task_id: int,
    db: Session = Depends(get_db)
):
    """重置任务 - 清空进度，重置到初始状态"""
    task = db.query(DownloadTask).filter(DownloadTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 如果任务正在运行，不允许重置
    if task.status == "running":
        raise HTTPException(status_code=400, detail="任务正在运行，请先停止任务")
    
    # 重置任务状态
    task.status = "pending"
    task.progress = 0
    task.downloaded_messages = 0
    task.total_messages = None
    task.error_message = None
    task.completed_at = None
    task.updated_at = datetime.now()
    db.commit()
    
    logger.info(f"任务 {task_id} 已重置")
    return {"message": "任务重置成功"}

@router.delete("/tasks/{task_id}")
async def delete_task(
    task_id: int,
    force: bool = Query(False, description="强制删除，忽略任务状态"),
    db: Session = Depends(get_db)
):
    """删除任务"""
    task = db.query(DownloadTask).filter(DownloadTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    if task.status == "running" and not force:
        raise HTTPException(status_code=400, detail="任务正在运行，无法删除。使用force=true参数强制删除")
    
    # 如果是强制删除，先尝试停止任务
    if task.status == "running" and force:
        try:
            service = get_task_execution_service()
            await service.stop_task(task_id)
            logger.info(f"强制删除时已停止运行中的任务 {task_id}")
        except Exception as e:
            logger.warning(f"强制删除时停止任务失败，继续删除: {e}")
    
    db.delete(task)
    db.commit()
    
    if force:
        return {"message": "任务强制删除成功"}
    else:
        return {"message": "任务删除成功"}

@router.post("/tasks/batch")
async def batch_task_operation(
    operation: str,
    task_ids: List[int],
    force: bool = Query(False, description="强制操作，忽略任务状态"),
    db: Session = Depends(get_db)
):
    """批量任务操作"""
    if not task_ids:
        raise HTTPException(status_code=400, detail="任务ID列表不能为空")
    
    valid_operations = ["start", "stop", "pause", "restart", "retry", "reset", "delete"]
    if operation not in valid_operations:
        raise HTTPException(status_code=400, detail=f"无效操作，支持的操作: {', '.join(valid_operations)}")
    
    results = []
    successful = 0
    failed = 0
    
    for task_id in task_ids:
        try:
            task = db.query(DownloadTask).filter(DownloadTask.id == task_id).first()
            if not task:
                results.append({"task_id": task_id, "status": "failed", "message": "任务不存在"})
                failed += 1
                continue
            
            # 根据操作类型执行相应操作
            if operation == "start":
                if task.status == "running":
                    results.append({"task_id": task_id, "status": "skipped", "message": "任务已在运行"})
                else:
                    task.status = "running"
                    execution_service = get_task_execution_service()
                    success = await execution_service.start_task(task_id)
                    if success:
                        results.append({"task_id": task_id, "status": "success", "message": "任务启动成功"})
                        successful += 1
                    else:
                        task.status = "failed"
                        results.append({"task_id": task_id, "status": "failed", "message": "任务启动失败"})
                        failed += 1
                        
            elif operation == "stop":
                if task.status != "running":
                    results.append({"task_id": task_id, "status": "skipped", "message": "任务未运行"})
                else:
                    execution_service = get_task_execution_service()
                    success = await execution_service.stop_task(task_id)
                    if success:
                        results.append({"task_id": task_id, "status": "success", "message": "任务停止成功"})
                        successful += 1
                    else:
                        results.append({"task_id": task_id, "status": "failed", "message": "任务停止失败"})
                        failed += 1
                        
            elif operation == "pause":
                if task.status != "running":
                    results.append({"task_id": task_id, "status": "skipped", "message": "任务未运行"})
                else:
                    execution_service = get_task_execution_service()
                    success = await execution_service.pause_task(task_id)
                    if success:
                        results.append({"task_id": task_id, "status": "success", "message": "任务暂停成功"})
                        successful += 1
                    else:
                        results.append({"task_id": task_id, "status": "failed", "message": "任务暂停失败"})
                        failed += 1
                        
            elif operation == "restart":
                if task.status == "running":
                    execution_service = get_task_execution_service()
                    await execution_service.stop_task(task_id)
                task.status = "pending"
                task.progress = 0
                task.downloaded_messages = 0
                task.error_message = None
                execution_service = get_task_execution_service()
                success = await execution_service.start_task(task_id)
                if success:
                    task.status = "running"
                    results.append({"task_id": task_id, "status": "success", "message": "任务重启成功"})
                    successful += 1
                else:
                    task.status = "failed"
                    results.append({"task_id": task_id, "status": "failed", "message": "任务重启失败"})
                    failed += 1
                    
            elif operation == "retry":
                if task.status not in ["failed", "completed", "stopped"]:
                    results.append({"task_id": task_id, "status": "skipped", "message": "任务状态不支持重试"})
                else:
                    task.status = "pending"
                    task.error_message = None
                    execution_service = get_task_execution_service()
                    success = await execution_service.start_task(task_id)
                    if success:
                        task.status = "running"
                        results.append({"task_id": task_id, "status": "success", "message": "任务重试成功"})
                        successful += 1
                    else:
                        task.status = "failed"
                        results.append({"task_id": task_id, "status": "failed", "message": "任务重试失败"})
                        failed += 1
                        
            elif operation == "reset":
                if task.status == "running":
                    results.append({"task_id": task_id, "status": "skipped", "message": "任务正在运行，无法重置"})
                else:
                    task.status = "pending"
                    task.progress = 0
                    task.downloaded_messages = 0
                    task.total_messages = None
                    task.error_message = None
                    task.completed_at = None
                    results.append({"task_id": task_id, "status": "success", "message": "任务重置成功"})
                    successful += 1
                    
            elif operation == "delete":
                if task.status == "running" and not force:
                    results.append({"task_id": task_id, "status": "skipped", 
                                  "message": "任务正在运行，无法删除。使用force=true强制删除"})
                else:
                    # 如果是强制删除运行中的任务，先尝试停止
                    if task.status == "running" and force:
                        try:
                            service = get_task_execution_service()
                            await service.stop_task(task_id)
                            logger.info(f"批量强制删除时已停止运行中的任务 {task_id}")
                        except Exception as e:
                            logger.warning(f"批量强制删除时停止任务失败，继续删除: {e}")
                    
                    db.delete(task)
                    message = "任务强制删除成功" if (task.status == "running" and force) else "任务删除成功"
                    results.append({"task_id": task_id, "status": "success", "message": message})
                    successful += 1
            
            db.commit()
            
        except Exception as e:
            logger.error(f"批量操作任务 {task_id} 失败: {e}")
            results.append({"task_id": task_id, "status": "failed", "message": f"操作失败: {str(e)}"})
            failed += 1
    
    return {
        "operation": operation,
        "total": len(task_ids),
        "successful": successful,
        "failed": failed,
        "results": results
    }

@router.post("/tasks/reset-orphaned")
async def reset_orphaned_tasks(db: Session = Depends(get_db)):
    """重置孤儿任务状态（处于running/paused状态但实际进程已停止的任务）"""
    try:
        # 查找所有可能的孤儿任务
        orphaned_tasks = db.query(DownloadTask).filter(
            DownloadTask.status.in_(["running", "paused"])
        ).all()
        
        reset_count = 0
        task_details = []
        
        for task in orphaned_tasks:
            original_status = task.status
            task.status = "failed"
            task.error_message = f"手动重置：原状态为{original_status}，疑似孤儿进程"
            reset_count += 1
            
            task_details.append({
                "task_id": task.id,
                "task_name": task.name,
                "original_status": original_status,
                "new_status": "failed"
            })
            
            logger.info(f"手动重置孤儿任务 {task.id}({task.name}) 状态: {original_status} -> failed")
        
        if reset_count > 0:
            db.commit()
            logger.info(f"手动重置了 {reset_count} 个孤儿任务状态")
        
        return {
            "message": f"成功重置 {reset_count} 个孤儿任务状态",
            "reset_count": reset_count,
            "tasks": task_details
        }
        
    except Exception as e:
        logger.error(f"重置孤儿任务状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"重置失败: {str(e)}")

@router.post("/tasks/create-and-start", response_model=TaskResponse)
async def create_and_start_task(
    task: TaskCreate,
    start_immediately: bool = True,
    db: Session = Depends(get_db)
):
    """创建任务并立即开始执行"""
    # 检查群组是否存在
    group = db.query(TelegramGroup).filter(TelegramGroup.id == task.group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="群组不存在")
    
    # 检查规则是否存在（如果指定了规则ID）
    if task.rule_id:
        rule = db.query(FilterRule).filter(FilterRule.id == task.rule_id).first()
        if not rule:
            raise HTTPException(status_code=404, detail="规则不存在")
    
    # 创建任务
    new_task = DownloadTask(**task.dict())
    new_task.status = "pending"
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    
    if start_immediately:
        # 立即启动任务
        try:
            new_task.status = "running"
            db.commit()
            
            success = await task_execution_service.start_task(new_task.id)
            if not success:
                new_task.status = "failed"
                new_task.error_message = "任务启动失败"
                db.commit()
                raise HTTPException(status_code=500, detail="任务创建成功但启动失败")
            
            logger.info(f"任务 {new_task.id} 创建并启动成功")
            
        except Exception as e:
            new_task.status = "failed"
            new_task.error_message = f"启动任务失败: {str(e)}"
            db.commit()
            logger.error(f"任务 {new_task.id} 启动失败: {e}")
            raise HTTPException(status_code=500, detail=f"任务创建成功但启动失败: {str(e)}")
    
    return new_task

@router.get("/tasks/{task_id}/status")
async def get_task_status(
    task_id: int,
    include_logs: bool = False,
    db: Session = Depends(get_db)
):
    """获取任务详细状态信息"""
    task = db.query(DownloadTask).filter(DownloadTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 获取关联的规则和群组信息
    rule = db.query(FilterRule).filter(FilterRule.id == task.rule_id).first() if task.rule_id else None
    group = db.query(TelegramGroup).filter(TelegramGroup.id == task.group_id).first()
    
    # 计算执行时间
    execution_time = None
    if task.created_at:
        if task.completed_at:
            execution_time = (task.completed_at - task.created_at).total_seconds()
        elif task.status == "running":
            execution_time = (datetime.now() - task.created_at).total_seconds()
    
    # 计算下载速度
    download_speed = None
    if task.downloaded_messages and execution_time and execution_time > 0:
        download_speed = task.downloaded_messages / execution_time  # 文件/秒
    
    # 估算剩余时间
    estimated_remaining = None
    if (task.total_messages and task.downloaded_messages and 
        task.total_messages > task.downloaded_messages and download_speed and download_speed > 0):
        remaining_files = task.total_messages - task.downloaded_messages
        estimated_remaining = remaining_files / download_speed  # 秒
    
    status_info = {
        "task_id": task.id,
        "name": task.name,
        "status": task.status,
        "progress": task.progress,
        "total_messages": task.total_messages,
        "downloaded_messages": task.downloaded_messages,
        "error_message": task.error_message,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
        "completed_at": task.completed_at,
        "execution_time_seconds": execution_time,
        "download_speed_files_per_second": download_speed,
        "estimated_remaining_seconds": estimated_remaining,
        "rule_info": {
            "id": rule.id,
            "name": rule.name,
            "is_active": rule.is_active
        } if rule else None,
        "group_info": {
            "id": group.id,
            "title": group.title,
            "username": group.username
        } if group else None,
        "jellyfin_config": {
            "use_jellyfin_structure": task.use_jellyfin_structure,
            "include_metadata": task.include_metadata,
            "download_thumbnails": task.download_thumbnails,
            "use_series_structure": task.use_series_structure
        }
    }
    
    # 如果请求包含日志，添加最近的任务日志
    if include_logs:
        try:
            from ..models.log import TaskLog
            recent_logs = db.query(TaskLog).filter(
                TaskLog.task_id == task_id
            ).order_by(TaskLog.created_at.desc()).limit(10).all()
            
            status_info["recent_logs"] = [
                {
                    "level": log.level,
                    "message": log.message,
                    "created_at": log.created_at
                } for log in recent_logs
            ]
        except Exception as e:
            logger.warning(f"获取任务日志失败: {e}")
            status_info["recent_logs"] = []
    
    return status_info

@router.get("/tasks/running")
async def get_running_tasks(
    db: Session = Depends(get_db)
):
    """获取所有正在运行的任务"""
    try:
        running_tasks = db.query(DownloadTask).filter(DownloadTask.status == "running").all()
        
        # 获取任务执行服务中的实际运行状态
        execution_service = get_task_execution_service()
        actual_running_task_ids = execution_service.get_running_tasks()
        
        task_info = []
        for task in running_tasks:
            is_actually_running = task.id in actual_running_task_ids
            
            # 如果数据库显示运行但服务中没有，可能是异常状态
            if not is_actually_running:
                logger.warning(f"任务 {task.id} 在数据库中显示运行但服务中不存在")
            
            task_info.append({
                "id": task.id,
                "name": task.name,
                "progress": task.progress,
                "total_messages": task.total_messages,
                "downloaded_messages": task.downloaded_messages,
                "created_at": task.created_at,
                "updated_at": task.updated_at,
                "is_actually_running": is_actually_running
            })
        
        return {
            "total_running": len(running_tasks),
            "actual_running": len(actual_running_task_ids),
            "tasks": task_info
        }
        
    except Exception as e:
        logger.error(f"获取运行中任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取运行中任务失败: {str(e)}")