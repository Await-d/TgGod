"""
下载历史管理API路由
提供下载历史记录的查询、查看和管理功能
"""

import logging
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, and_, or_, func

logger = logging.getLogger(__name__)

from ..database import get_db
from ..models.rule import DownloadTask, DownloadRecord
from ..models.telegram import TelegramGroup
from ..schemas.download_history import (
    DownloadRecordResponse, 
    DownloadHistoryListResponse,
    DownloadHistoryStatsResponse,
    DownloadRecordCreate
)

router = APIRouter(prefix="/download-history", tags=["下载历史"])

@router.get("/records", response_model=DownloadHistoryListResponse, summary="获取下载历史记录")
async def get_download_records(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    task_id: Optional[int] = Query(None, description="任务ID过滤"),
    group_id: Optional[int] = Query(None, description="群组ID过滤"),
    file_type: Optional[str] = Query(None, description="文件类型过滤"),
    status: Optional[str] = Query(None, description="下载状态过滤"),
    date_from: Optional[datetime] = Query(None, description="开始日期过滤"),
    date_to: Optional[datetime] = Query(None, description="结束日期过滤"),
    search: Optional[str] = Query(None, description="搜索关键词"),
):
    """
    获取下载历史记录列表，支持分页和多种过滤条件
    """
    try:
        # 构建基础查询
        query = db.query(DownloadRecord).options(
            joinedload(DownloadRecord.task).joinedload(DownloadTask.group)
        )
        
        # 应用过滤条件
        conditions = []
        
        if task_id:
            conditions.append(DownloadRecord.task_id == task_id)
        
        if group_id:
            conditions.append(DownloadTask.group_id == group_id)
            query = query.join(DownloadTask)
        
        if file_type:
            conditions.append(DownloadRecord.file_type == file_type)
        
        if status:
            conditions.append(DownloadRecord.download_status == status)
        
        if date_from:
            conditions.append(DownloadRecord.download_completed_at >= date_from)
        
        if date_to:
            conditions.append(DownloadRecord.download_completed_at <= date_to)
        
        if search:
            search_conditions = [
                DownloadRecord.file_name.contains(search),
                DownloadRecord.message_text.contains(search),
                DownloadRecord.sender_name.contains(search)
            ]
            conditions.append(or_(*search_conditions))
        
        # 应用所有条件
        if conditions:
            query = query.filter(and_(*conditions))
        
        # 获取总数
        total = query.count()
        
        # 应用分页和排序
        records = query.order_by(desc(DownloadRecord.download_completed_at)).offset(
            (page - 1) * page_size
        ).limit(page_size).all()
        
        # 转换为响应格式
        record_list = []
        for record in records:
            record_data = {
                "id": record.id,
                "task_id": record.task_id,
                "task_name": record.task.name if record.task else None,
                "group_name": record.task.group.title if record.task and record.task.group else None,
                "file_name": record.file_name,
                "local_file_path": record.local_file_path,
                "file_size": record.file_size,
                "file_type": record.file_type,
                "message_id": record.message_id,
                "sender_id": record.sender_id,
                "sender_name": record.sender_name,
                "message_date": record.message_date,
                "message_text": record.message_text,
                "download_status": record.download_status,
                "download_progress": record.download_progress,
                "error_message": record.error_message,
                "download_started_at": record.download_started_at,
                "download_completed_at": record.download_completed_at
            }
            record_list.append(record_data)
        
        return {
            "records": record_list,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取下载历史记录失败: {str(e)}")

@router.get("/records/{record_id}", response_model=DownloadRecordResponse, summary="获取单个下载记录详情")
async def get_download_record(
    record_id: int,
    db: Session = Depends(get_db)
):
    """
    获取指定下载记录的详细信息
    """
    try:
        record = db.query(DownloadRecord).options(
            joinedload(DownloadRecord.task).joinedload(DownloadTask.group)
        ).filter(DownloadRecord.id == record_id).first()
        
        if not record:
            raise HTTPException(status_code=404, detail="下载记录不存在")
        
        return {
            "id": record.id,
            "task_id": record.task_id,
            "task_name": record.task.name if record.task else None,
            "group_name": record.task.group.title if record.task and record.task.group else None,
            "file_name": record.file_name,
            "local_file_path": record.local_file_path,
            "file_size": record.file_size,
            "file_type": record.file_type,
            "message_id": record.message_id,
            "sender_id": record.sender_id,
            "sender_name": record.sender_name,
            "message_date": record.message_date,
            "message_text": record.message_text,
            "download_status": record.download_status,
            "download_progress": record.download_progress,
            "error_message": record.error_message,
            "download_started_at": record.download_started_at,
            "download_completed_at": record.download_completed_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取下载记录详情失败: {str(e)}")

@router.get("/stats", response_model=DownloadHistoryStatsResponse, summary="获取下载历史统计信息")
async def get_download_stats(
    db: Session = Depends(get_db),
    days: int = Query(30, ge=1, le=365, description="统计天数")
):
    """
    获取下载历史的统计信息
    """
    try:
        # 检查download_records表是否存在，如果不存在则创建
        from sqlalchemy import text, inspect
        inspector = inspect(db.bind)
        tables = inspector.get_table_names()
        
        if 'download_records' not in tables:
            # 表不存在，创建表
            create_table_sql = """
            CREATE TABLE download_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                file_name VARCHAR(500) NOT NULL,
                local_file_path VARCHAR(1000) NOT NULL,
                file_size INTEGER,
                file_type VARCHAR(50),
                message_id INTEGER NOT NULL,
                sender_id INTEGER,
                sender_name VARCHAR(255),
                message_date DATETIME,
                message_text TEXT,
                download_status VARCHAR(50) DEFAULT 'completed',
                download_progress INTEGER DEFAULT 100,
                error_message TEXT,
                download_started_at DATETIME,
                download_completed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES download_tasks(id)
            )
            """
            db.execute(text(create_table_sql))
            db.execute(text("CREATE INDEX ix_download_records_id ON download_records(id)"))
            db.execute(text("CREATE INDEX ix_download_records_task_id ON download_records(task_id)"))
            db.execute(text("CREATE INDEX ix_download_records_completed_at ON download_records(download_completed_at)"))
            db.commit()
            logger.info("✅ download_records表已创建")
        
        # 如果表为空，返回空统计
        table_check = db.execute(text("SELECT COUNT(*) FROM download_records")).scalar()
        if table_check == 0:
            return {
                "total_downloads": 0,
                "successful_downloads": 0,
                "failed_downloads": 0,
                "success_rate": 0.0,
                "total_file_size": 0,
                "file_types": {},
                "top_tasks": [],
                "period_days": days
            }
        # 计算时间范围
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # 基础查询
        base_query = db.query(DownloadRecord).filter(
            DownloadRecord.download_completed_at >= start_date
        )
        
        # 总下载数量
        total_downloads = base_query.count()
        
        # 成功下载数量
        successful_downloads = base_query.filter(
            DownloadRecord.download_status == "completed"
        ).count()
        
        # 失败下载数量
        failed_downloads = base_query.filter(
            DownloadRecord.download_status == "failed"
        ).count()
        
        # 总文件大小
        total_size_result = base_query.filter(
            DownloadRecord.file_size.isnot(None)
        ).with_entities(func.sum(DownloadRecord.file_size)).scalar()
        total_file_size = total_size_result or 0
        
        # 按文件类型统计
        file_type_stats = base_query.filter(
            DownloadRecord.file_type.isnot(None)
        ).with_entities(
            DownloadRecord.file_type,
            func.count(DownloadRecord.id).label('count')
        ).group_by(DownloadRecord.file_type).all()
        
        file_types = {
            file_type: count for file_type, count in file_type_stats
        }
        
        # 按任务统计
        task_stats = base_query.join(DownloadTask).with_entities(
            DownloadTask.name,
            func.count(DownloadRecord.id).label('count')
        ).group_by(DownloadTask.name).order_by(desc('count')).limit(10).all()
        
        top_tasks = [
            {"task_name": task_name, "download_count": count}
            for task_name, count in task_stats
        ]
        
        # 计算成功率
        success_rate = (successful_downloads / total_downloads * 100) if total_downloads > 0 else 0
        
        return {
            "total_downloads": total_downloads,
            "successful_downloads": successful_downloads,
            "failed_downloads": failed_downloads,
            "success_rate": round(success_rate, 2),
            "total_file_size": total_file_size,
            "file_types": file_types,
            "top_tasks": top_tasks,
            "period_days": days
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")

@router.delete("/records/{record_id}", summary="删除下载记录")
async def delete_download_record(
    record_id: int,
    db: Session = Depends(get_db)
):
    """
    删除指定的下载记录（仅删除数据库记录，不删除本地文件）
    """
    try:
        record = db.query(DownloadRecord).filter(DownloadRecord.id == record_id).first()
        
        if not record:
            raise HTTPException(status_code=404, detail="下载记录不存在")
        
        db.delete(record)
        db.commit()
        
        return {"message": "下载记录删除成功", "record_id": record_id}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除下载记录失败: {str(e)}")

@router.post("/records/batch-delete", summary="批量删除下载记录")
async def batch_delete_records(
    record_ids: List[int],
    db: Session = Depends(get_db)
):
    """
    批量删除多个下载记录
    """
    try:
        if not record_ids:
            raise HTTPException(status_code=400, detail="请提供要删除的记录ID列表")
        
        # 查找存在的记录
        existing_records = db.query(DownloadRecord).filter(
            DownloadRecord.id.in_(record_ids)
        ).all()
        
        if not existing_records:
            raise HTTPException(status_code=404, detail="没有找到要删除的记录")
        
        # 删除记录
        deleted_count = db.query(DownloadRecord).filter(
            DownloadRecord.id.in_(record_ids)
        ).delete(synchronize_session=False)
        
        db.commit()
        
        return {
            "message": f"成功删除 {deleted_count} 条下载记录",
            "deleted_count": deleted_count,
            "requested_count": len(record_ids)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"批量删除下载记录失败: {str(e)}")

@router.get("/tasks/{task_id}/records", response_model=DownloadHistoryListResponse, summary="获取任务的下载记录")
async def get_task_download_records(
    task_id: int,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量")
):
    """
    获取指定任务的所有下载记录
    """
    try:
        # 验证任务是否存在
        task = db.query(DownloadTask).filter(DownloadTask.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="下载任务不存在")
        
        # 查询任务的下载记录
        query = db.query(DownloadRecord).filter(DownloadRecord.task_id == task_id)
        
        # 获取总数
        total = query.count()
        
        # 应用分页和排序
        records = query.order_by(desc(DownloadRecord.download_completed_at)).offset(
            (page - 1) * page_size
        ).limit(page_size).all()
        
        # 转换为响应格式
        record_list = []
        for record in records:
            record_data = {
                "id": record.id,
                "task_id": record.task_id,
                "task_name": task.name,
                "group_name": task.group.title if task.group else None,
                "file_name": record.file_name,
                "local_file_path": record.local_file_path,
                "file_size": record.file_size,
                "file_type": record.file_type,
                "message_id": record.message_id,
                "sender_id": record.sender_id,
                "sender_name": record.sender_name,
                "message_date": record.message_date,
                "message_text": record.message_text,
                "download_status": record.download_status,
                "download_progress": record.download_progress,
                "error_message": record.error_message,
                "download_started_at": record.download_started_at,
                "download_completed_at": record.download_completed_at
            }
            record_list.append(record_data)
        
        return {
            "records": record_list,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取任务下载记录失败: {str(e)}")

@router.post("/records", response_model=DownloadRecordResponse, summary="创建下载记录")
async def create_download_record(
    record_data: DownloadRecordCreate,
    db: Session = Depends(get_db)
):
    """
    创建新的下载记录（供下载服务调用）
    """
    try:
        # 验证任务是否存在
        task = db.query(DownloadTask).filter(DownloadTask.id == record_data.task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="下载任务不存在")
        
        # 创建下载记录
        record = DownloadRecord(**record_data.dict())
        db.add(record)
        db.commit()
        db.refresh(record)
        
        return {
            "id": record.id,
            "task_id": record.task_id,
            "task_name": task.name,
            "group_name": task.group.title if task.group else None,
            "file_name": record.file_name,
            "local_file_path": record.local_file_path,
            "file_size": record.file_size,
            "file_type": record.file_type,
            "message_id": record.message_id,
            "sender_id": record.sender_id,
            "sender_name": record.sender_name,
            "message_date": record.message_date,
            "message_text": record.message_text,
            "download_status": record.download_status,
            "download_progress": record.download_progress,
            "error_message": record.error_message,
            "download_started_at": record.download_started_at,
            "download_completed_at": record.download_completed_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建下载记录失败: {str(e)}")