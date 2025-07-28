from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
from ..database import get_db
from ..models.rule import FilterRule, DownloadTask
from ..models.telegram import TelegramGroup, TelegramMessage
# from ..services.rule_sync_service import rule_sync_service  # 暂时注释
from pydantic import BaseModel
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Pydantic模型
class RuleCreate(BaseModel):
    name: str
    # 移除 group_id - 群组关联由任务管理
    keywords: Optional[List[str]] = None
    exclude_keywords: Optional[List[str]] = None
    sender_filter: Optional[List[str]] = None
    media_types: Optional[List[str]] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    min_views: Optional[int] = None
    max_views: Optional[int] = None
    min_file_size: Optional[int] = None  # 最小文件大小（字节）
    max_file_size: Optional[int] = None  # 最大文件大小（字节）
    
    # 视频/音频时长过滤（秒）
    min_duration: Optional[int] = None
    max_duration: Optional[int] = None
    
    # 视频尺寸过滤（像素）
    min_width: Optional[int] = None
    max_width: Optional[int] = None
    min_height: Optional[int] = None
    max_height: Optional[int] = None
    
    # 文本长度过滤（字符数）
    min_text_length: Optional[int] = None
    max_text_length: Optional[int] = None
    
    # 高级过滤选项
    has_urls: Optional[bool] = None
    has_mentions: Optional[bool] = None
    has_hashtags: Optional[bool] = None
    is_reply: Optional[bool] = None
    is_edited: Optional[bool] = None
    is_pinned: Optional[bool] = None
    
    # 时间相关过滤
    message_age_days: Optional[int] = None
    exclude_weekends: bool = False
    time_range_start: Optional[str] = None  # HH:MM格式
    time_range_end: Optional[str] = None    # HH:MM格式
    
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
    min_file_size: Optional[int] = None  # 最小文件大小（字节）
    max_file_size: Optional[int] = None  # 最大文件大小（字节）
    
    # 视频/音频时长过滤（秒）
    min_duration: Optional[int] = None
    max_duration: Optional[int] = None
    
    # 视频尺寸过滤（像素）
    min_width: Optional[int] = None
    max_width: Optional[int] = None
    min_height: Optional[int] = None
    max_height: Optional[int] = None
    
    # 文本长度过滤（字符数）
    min_text_length: Optional[int] = None
    max_text_length: Optional[int] = None
    
    # 高级过滤选项
    has_urls: Optional[bool] = None
    has_mentions: Optional[bool] = None
    has_hashtags: Optional[bool] = None
    is_reply: Optional[bool] = None
    is_edited: Optional[bool] = None
    is_pinned: Optional[bool] = None
    
    # 时间相关过滤
    message_age_days: Optional[int] = None
    exclude_weekends: Optional[bool] = None
    time_range_start: Optional[str] = None  # HH:MM格式
    time_range_end: Optional[str] = None    # HH:MM格式
    
    include_forwarded: Optional[bool] = None
    is_active: Optional[bool] = None

class RuleResponse(BaseModel):
    id: int
    name: str
    # 移除 group_id - 群组关联由任务管理
    keywords: Optional[List[str]]
    exclude_keywords: Optional[List[str]]
    sender_filter: Optional[List[str]]
    media_types: Optional[List[str]]
    date_from: Optional[datetime]
    date_to: Optional[datetime]
    min_views: Optional[int]
    max_views: Optional[int]
    min_file_size: Optional[int]  # 最小文件大小（字节）
    max_file_size: Optional[int]  # 最大文件大小（字节）
    
    # 视频/音频时长过滤（秒）
    min_duration: Optional[int]
    max_duration: Optional[int]
    
    # 视频尺寸过滤（像素）
    min_width: Optional[int]
    max_width: Optional[int]
    min_height: Optional[int]
    max_height: Optional[int]
    
    # 文本长度过滤（字符数）
    min_text_length: Optional[int]
    max_text_length: Optional[int]
    
    # 高级过滤选项
    has_urls: Optional[bool]
    has_mentions: Optional[bool]
    has_hashtags: Optional[bool]
    is_reply: Optional[bool]
    is_edited: Optional[bool]
    is_pinned: Optional[bool]
    
    # 时间相关过滤
    message_age_days: Optional[int]
    exclude_weekends: bool
    time_range_start: Optional[str]  # HH:MM格式
    time_range_end: Optional[str]    # HH:MM格式
    
    include_forwarded: bool
    is_active: bool
    # 同步跟踪字段（暂时注释）
    # last_sync_time: Optional[datetime]  # 最后同步时间
    # last_sync_message_count: int  # 最后同步的消息数量
    # sync_status: str  # 同步状态
    # needs_full_resync: bool  # 是否需要完全重新同步
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class RuleTestResponse(BaseModel):
    rule_id: int
    rule_name: str
    # 移除群组相关字段 - 规则测试现在需要通过任务进行
    message: str = "规则测试功能已移至任务管理，请创建任务后测试规则效果"

class RuleValidationResponse(BaseModel):
    rule_id: int
    is_valid: bool
    validation_errors: List[str]
    validation_warnings: List[str]
    recommended_actions: List[str]

@router.get("/rules", response_model=List[RuleResponse])
async def get_rules(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """获取规则列表 - 群组过滤通过任务获取"""
    try:
        query = db.query(FilterRule)
        rules = query.offset(skip).limit(limit).all()
        return rules
    except Exception as e:
        logger.error(f"获取规则列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取规则列表失败: {str(e)}")

@router.post("/rules", response_model=RuleResponse)
async def create_rule(
    rule: RuleCreate,
    db: Session = Depends(get_db)
):
    """创建规则 - 不再直接关联群组"""
    # 检查规则名称是否已存在
    existing_rule = db.query(FilterRule).filter(FilterRule.name == rule.name).first()
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
    
    # 检查是否有影响查询结果的字段被修改
    sync_affecting_fields = {
        'keywords', 'exclude_keywords', 'sender_filter', 'media_types',
        'date_from', 'date_to', 'min_views', 'max_views', 
        'min_file_size', 'max_file_size', 'include_forwarded'
    }
    
    update_data = rule_update.dict(exclude_unset=True)
    needs_resync = any(field in sync_affecting_fields for field in update_data.keys())
    
    # 更新字段
    for field, value in update_data.items():
        setattr(rule, field, value)
    
    # 如果规则条件被修改，标记需要重新同步（暂时注释）
    if needs_resync:
        # rule.needs_full_resync = True
        # rule.sync_status = 'pending'
        logger.info(f"规则 {rule_id} 条件已修改，标记为需要重新同步")
    
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

@router.post("/rules/{rule_id}/test", response_model=RuleTestResponse)
async def test_rule(
    rule_id: int,
    db: Session = Depends(get_db)
):
    """规则测试功能已移至任务管理"""
    # 获取规则
    rule = db.query(FilterRule).filter(FilterRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    
    return RuleTestResponse(
        rule_id=rule_id,
        rule_name=rule.name,
        message="规则测试功能已移至任务管理。请创建使用此规则的任务，然后通过任务测试规则效果。"
    )

# 移除了与群组相关的辅助函数，规则测试现在通过任务进行

@router.post("/rules/{rule_id}/validate", response_model=RuleValidationResponse)
async def validate_rule(
    rule_id: int,
    db: Session = Depends(get_db)
):
    """验证规则的完整性和有效性 - 简化版本，不依赖群组"""
    try:
        # 获取规则
        rule = db.query(FilterRule).filter(FilterRule.id == rule_id).first()
        if not rule:
            raise HTTPException(status_code=404, detail="规则不存在")
        
        validation_errors = []
        validation_warnings = []
        recommended_actions = []
        
        # 检查规则是否激活
        if not rule.is_active:
            validation_warnings.append("规则当前未激活")
            recommended_actions.append("启用规则以使其生效")
        
        # 检查过滤条件
        filter_count = 0
        
        if rule.keywords:
            filter_count += 1
            if len(rule.keywords) > 20:
                validation_warnings.append("关键词数量过多，可能影响性能")
                recommended_actions.append("考虑减少关键词数量或使用更精确的关键词")
        
        if rule.exclude_keywords:
            filter_count += 1
        
        if rule.media_types:
            filter_count += 1
            valid_media_types = ['photo', 'video', 'audio', 'voice', 'document', 'sticker', 'video_note']
            invalid_types = [mt for mt in rule.media_types if mt not in valid_media_types]
            if invalid_types:
                validation_errors.append(f"无效的媒体类型: {', '.join(invalid_types)}")
                recommended_actions.append(f"请使用有效的媒体类型: {', '.join(valid_media_types)}")
        
        if rule.sender_filter:
            filter_count += 1
        
        if rule.date_from and rule.date_to:
            filter_count += 1
            if rule.date_from > rule.date_to:
                validation_errors.append("开始日期不能晚于结束日期")
                recommended_actions.append("请调整日期范围")
        
        if rule.min_views is not None and rule.max_views is not None:
            filter_count += 1
            if rule.min_views > rule.max_views:
                validation_errors.append("最小浏览量不能大于最大浏览量")
                recommended_actions.append("请调整浏览量范围")
        
        if rule.min_file_size is not None and rule.max_file_size is not None:
            filter_count += 1
            if rule.min_file_size > rule.max_file_size:
                validation_errors.append("最小文件大小不能大于最大文件大小")
                recommended_actions.append("请调整文件大小范围")
        
        # 检查是否有足够的过滤条件
        if filter_count == 0:
            validation_warnings.append("规则没有设置任何过滤条件，将匹配所有媒体消息")
            recommended_actions.append("建议添加关键词、媒体类型或其他过滤条件")
        
        # 检查规则是否被任务使用
        task_count = db.query(DownloadTask).filter(DownloadTask.rule_id == rule_id).count()
        if task_count == 0:
            validation_warnings.append("规则未被任何任务使用")
            recommended_actions.append("创建使用此规则的下载任务")
        else:
            validation_warnings.append(f"规则正在被 {task_count} 个任务使用")
        
        is_valid = len(validation_errors) == 0
        
        return RuleValidationResponse(
            rule_id=rule_id,
            is_valid=is_valid,
            validation_errors=validation_errors,
            validation_warnings=validation_warnings,
            recommended_actions=recommended_actions
        )
        
    except Exception as e:
        logger.error(f"验证规则 {rule_id} 失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"规则验证失败: {str(e)}")

@router.get("/rules/stats")
async def get_rules_stats(
    db: Session = Depends(get_db)
):
    """获取规则统计信息"""
    try:
        total_rules = db.query(FilterRule).count()
        active_rules = db.query(FilterRule).filter(FilterRule.is_active == True).count()
        inactive_rules = total_rules - active_rules
        
        # 统计规则使用情况（通过任务）
        rules_with_tasks = db.query(FilterRule.id).join(DownloadTask).distinct().count()
        unused_rules = total_rules - rules_with_tasks
        
        return {
            "total_rules": total_rules,
            "active_rules": active_rules,
            "inactive_rules": inactive_rules,
            "rules_with_tasks": rules_with_tasks,
            "unused_rules": unused_rules
        }
        
    except Exception as e:
        logger.error(f"获取规则统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取规则统计失败: {str(e)}")


@router.post("/rules/{rule_id}/ensure-data")
async def ensure_rule_data_availability(
    rule_id: int,
    db: Session = Depends(get_db)
):
    """
    确保规则有足够的数据可供查询
    自动检测并执行必要的消息同步
    """
    try:
        result = await rule_sync_service.ensure_rule_data_availability(rule_id, db)
        return {
            "success": True,
            "message": "数据可用性检查完成",
            "data": result
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"确保规则数据可用性失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"操作失败: {str(e)}")


# 暂时注释同步状态相关endpoint
# @router.get("/rules/{rule_id}/sync-status")
# async def get_rule_sync_status(
#     rule_id: int,
#     db: Session = Depends(get_db)
# ):
#     """
#     获取规则的同步状态信息
#     """
#     try:
#         status = await rule_sync_service.get_sync_status(rule_id, db)
#         return {
#             "success": True,
#             "data": status
#         }
#     except ValueError as e:
#         raise HTTPException(status_code=404, detail=str(e))
#     except Exception as e:
#         logger.error(f"获取同步状态失败: {str(e)}")
#         raise HTTPException(status_code=500, detail=f"获取同步状态失败: {str(e)}")


@router.post("/rules/{rule_id}/mark-for-resync")
async def mark_rule_for_resync(
    rule_id: int,
    db: Session = Depends(get_db)
):
    """
    标记规则需要重新同步（在规则修改后调用）
    """
    try:
        await rule_sync_service.mark_rule_for_resync(rule_id, db)
        return {
            "success": True,
            "message": f"规则 {rule_id} 已标记为需要重新同步"
        }
    except Exception as e:
        logger.error(f"标记重新同步失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"操作失败: {str(e)}")