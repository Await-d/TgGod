from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db
from ..models.telegram import TelegramGroup, TelegramMessage
from ..services.telegram_service import telegram_service
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()

# Pydantic模型
class GroupCreate(BaseModel):
    username: str

class GroupResponse(BaseModel):
    id: int
    telegram_id: int
    title: str
    username: Optional[str]
    description: Optional[str]
    member_count: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

class MessageResponse(BaseModel):
    id: int
    group_id: int
    message_id: int
    sender_id: Optional[int]
    sender_username: Optional[str]
    sender_name: Optional[str]
    text: Optional[str]
    media_type: Optional[str]
    media_path: Optional[str]
    media_size: Optional[int]
    view_count: int
    is_forwarded: bool
    forwarded_from: Optional[str]
    date: datetime
    created_at: datetime

@router.get("/groups", response_model=List[GroupResponse])
async def get_groups(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """获取群组列表"""
    groups = db.query(TelegramGroup).offset(skip).limit(limit).all()
    return groups

@router.post("/groups", response_model=GroupResponse)
async def add_group(
    group: GroupCreate,
    db: Session = Depends(get_db)
):
    """添加群组"""
    try:
        # 检查群组是否已存在
        existing_group = db.query(TelegramGroup).filter(
            TelegramGroup.username == group.username
        ).first()
        
        if existing_group:
            raise HTTPException(status_code=400, detail="群组已存在")
        
        # 添加群组到数据库
        new_group = await telegram_service.add_group_to_db(group.username, db)
        if not new_group:
            raise HTTPException(status_code=400, detail="无法获取群组信息")
        
        return new_group
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/groups/{group_id}", response_model=GroupResponse)
async def get_group(
    group_id: int,
    db: Session = Depends(get_db)
):
    """获取单个群组信息"""
    group = db.query(TelegramGroup).filter(TelegramGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="群组不存在")
    return group

@router.put("/groups/{group_id}", response_model=GroupResponse)
async def update_group(
    group_id: int,
    is_active: bool,
    db: Session = Depends(get_db)
):
    """更新群组状态"""
    group = db.query(TelegramGroup).filter(TelegramGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="群组不存在")
    
    group.is_active = is_active
    db.commit()
    db.refresh(group)
    return group

@router.delete("/groups/{group_id}")
async def delete_group(
    group_id: int,
    db: Session = Depends(get_db)
):
    """删除群组"""
    group = db.query(TelegramGroup).filter(TelegramGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="群组不存在")
    
    db.delete(group)
    db.commit()
    return {"message": "群组删除成功"}

@router.get("/groups/{group_id}/messages", response_model=List[MessageResponse])
async def get_group_messages(
    group_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """获取群组消息"""
    # 检查群组是否存在
    group = db.query(TelegramGroup).filter(TelegramGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="群组不存在")
    
    # 获取消息
    messages = db.query(TelegramMessage).filter(
        TelegramMessage.group_id == group_id
    ).order_by(TelegramMessage.date.desc()).offset(skip).limit(limit).all()
    
    return messages

@router.post("/groups/{group_id}/sync")
async def sync_group_messages(
    group_id: int,
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """同步群组消息"""
    # 检查群组是否存在
    group = db.query(TelegramGroup).filter(TelegramGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="群组不存在")
    
    try:
        # 获取消息
        messages = await telegram_service.get_messages(group.username, limit=limit)
        
        # 保存到数据库
        await telegram_service.save_messages_to_db(group_id, messages, db)
        
        return {"message": f"成功同步 {len(messages)} 条消息"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/groups/{group_id}/stats")
async def get_group_stats(
    group_id: int,
    db: Session = Depends(get_db)
):
    """获取群组统计信息"""
    # 检查群组是否存在
    group = db.query(TelegramGroup).filter(TelegramGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="群组不存在")
    
    # 统计消息数量
    total_messages = db.query(TelegramMessage).filter(
        TelegramMessage.group_id == group_id
    ).count()
    
    # 统计媒体消息数量
    media_messages = db.query(TelegramMessage).filter(
        TelegramMessage.group_id == group_id,
        TelegramMessage.media_type.isnot(None)
    ).count()
    
    return {
        "total_messages": total_messages,
        "media_messages": media_messages,
        "text_messages": total_messages - media_messages,
        "member_count": group.member_count
    }