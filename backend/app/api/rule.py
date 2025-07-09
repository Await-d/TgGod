from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db
from ..models.rule import FilterRule, DownloadTask
from ..models.telegram import TelegramGroup
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()

# Pydantic模型
class RuleCreate(BaseModel):
    name: str
    group_id: int
    keywords: Optional[List[str]] = None
    exclude_keywords: Optional[List[str]] = None
    sender_filter: Optional[List[str]] = None
    media_types: Optional[List[str]] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    min_views: Optional[int] = None
    max_views: Optional[int] = None
    include_forwarded: bool = True

class RuleUpdate(BaseModel):
    name: Optional[str] = None
    keywords: Optional[List[str]] = None
    exclude_keywords: Optional[List[str]] = None
    sender_filter: Optional[List[str]] = None
    media_types: Optional[List[str]] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    min_views: Optional[int] = None
    max_views: Optional[int] = None
    include_forwarded: Optional[bool] = None
    is_active: Optional[bool] = None

class RuleResponse(BaseModel):
    id: int
    name: str
    group_id: int
    keywords: Optional[List[str]]
    exclude_keywords: Optional[List[str]]
    sender_filter: Optional[List[str]]
    media_types: Optional[List[str]]
    date_from: Optional[datetime]
    date_to: Optional[datetime]
    min_views: Optional[int]
    max_views: Optional[int]
    include_forwarded: bool
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

@router.get("/rules", response_model=List[RuleResponse])
async def get_rules(
    group_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """获取规则列表"""
    query = db.query(FilterRule)
    
    if group_id:
        query = query.filter(FilterRule.group_id == group_id)
    
    rules = query.offset(skip).limit(limit).all()
    return rules

@router.post("/rules", response_model=RuleResponse)
async def create_rule(
    rule: RuleCreate,
    db: Session = Depends(get_db)
):
    """创建规则"""
    # 检查群组是否存在
    group = db.query(TelegramGroup).filter(TelegramGroup.id == rule.group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="群组不存在")
    
    # 检查规则名称是否已存在
    existing_rule = db.query(FilterRule).filter(
        FilterRule.name == rule.name,
        FilterRule.group_id == rule.group_id
    ).first()
    if existing_rule:
        raise HTTPException(status_code=400, detail="规则名称已存在")
    
    # 创建规则
    new_rule = FilterRule(**rule.dict())
    db.add(new_rule)
    db.commit()
    db.refresh(new_rule)
    
    return new_rule

@router.get("/rules/{rule_id}", response_model=RuleResponse)
async def get_rule(
    rule_id: int,
    db: Session = Depends(get_db)
):
    """获取单个规则"""
    rule = db.query(FilterRule).filter(FilterRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    return rule

@router.put("/rules/{rule_id}", response_model=RuleResponse)
async def update_rule(
    rule_id: int,
    rule_update: RuleUpdate,
    db: Session = Depends(get_db)
):
    """更新规则"""
    rule = db.query(FilterRule).filter(FilterRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    
    # 更新字段
    for field, value in rule_update.dict(exclude_unset=True).items():
        setattr(rule, field, value)
    
    db.commit()
    db.refresh(rule)
    return rule

@router.delete("/rules/{rule_id}")
async def delete_rule(
    rule_id: int,
    db: Session = Depends(get_db)
):
    """删除规则"""
    rule = db.query(FilterRule).filter(FilterRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    
    # 检查是否有关联的任务
    task_count = db.query(DownloadTask).filter(DownloadTask.rule_id == rule_id).count()
    if task_count > 0:
        raise HTTPException(status_code=400, detail="规则关联的任务存在，无法删除")
    
    db.delete(rule)
    db.commit()
    return {"message": "规则删除成功"}

@router.post("/rules/{rule_id}/test")
async def test_rule(
    rule_id: int,
    db: Session = Depends(get_db)
):
    """测试规则"""
    rule = db.query(FilterRule).filter(FilterRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    
    # TODO: 实现规则测试逻辑
    # 这里应该根据规则条件筛选消息，返回匹配的消息数量
    
    return {
        "rule_id": rule_id,
        "matched_messages": 0,
        "message": "规则测试功能待实现"
    }