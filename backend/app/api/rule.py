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
    group_id: int
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
    min_file_size: Optional[int]  # 最小文件大小（字节）
    max_file_size: Optional[int]  # 最大文件大小（字节）
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
    group_id: int
    group_name: str
    total_messages: int
    matched_messages: int
    sample_matches: List[dict]
    filter_summary: dict

class RuleValidationResponse(BaseModel):
    rule_id: int
    is_valid: bool
    validation_errors: List[str]
    validation_warnings: List[str]
    recommended_actions: List[str]

@router.get("/rules", response_model=List[RuleResponse])
async def get_rules(
    group_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """获取规则列表"""
    try:
        query = db.query(FilterRule)
        
        if group_id:
            query = query.filter(FilterRule.group_id == group_id)
        
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
    limit: int = Query(5, ge=1, le=20, description="返回的样本消息数量"),
    db: Session = Depends(get_db)
):
    """测试规则 - 应用规则条件筛选消息并返回匹配结果"""
    try:
        # 获取规则
        rule = db.query(FilterRule).filter(FilterRule.id == rule_id).first()
        if not rule:
            raise HTTPException(status_code=404, detail="规则不存在")
        
        # 获取群组信息
        group = db.query(TelegramGroup).filter(TelegramGroup.id == rule.group_id).first()
        if not group:
            raise HTTPException(status_code=404, detail="关联的群组不存在")
        
        # 获取群组的总消息数
        total_messages = db.query(TelegramMessage).filter(TelegramMessage.group_id == group.id).count()
        
        # 应用规则筛选消息
        matched_messages = await _apply_rule_filter(rule, group, db)
        matched_count = len(matched_messages)
        
        # 获取样本消息
        sample_messages = matched_messages[:limit]
        sample_matches = []
        
        for msg in sample_messages:
            sample_matches.append({
                "message_id": msg.message_id,
                "sender_name": msg.sender_name or "Unknown",
                "sender_username": msg.sender_username,
                "text": msg.text[:100] + "..." if msg.text and len(msg.text) > 100 else msg.text,
                "media_type": msg.media_type,
                "file_size": msg.file_size,
                "date": msg.date.isoformat() if msg.date else None,
                "views": msg.views,
                "is_forwarded": msg.is_forwarded
            })
        
        # 生成过滤条件总结
        filter_summary = _generate_filter_summary(rule)
        
        return RuleTestResponse(
            rule_id=rule_id,
            rule_name=rule.name,
            group_id=group.id,
            group_name=group.title or f"Group {group.id}",
            total_messages=total_messages,
            matched_messages=matched_count,
            sample_matches=sample_matches,
            filter_summary=filter_summary
        )
        
    except Exception as e:
        logger.error(f"测试规则 {rule_id} 失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"规则测试失败: {str(e)}")

async def _apply_rule_filter(rule: FilterRule, group: TelegramGroup, db: Session) -> List[TelegramMessage]:
    """应用规则过滤条件筛选消息"""
    
    # 确保规则有足够的数据可供查询
    try:
        sync_result = await rule_sync_service.ensure_rule_data_availability(rule.id, db)
        logger.info(f"规则 {rule.id} 测试时数据可用性检查完成: {sync_result}")
    except Exception as e:
        logger.warning(f"规则测试时数据同步失败，继续使用现有数据: {e}")
    
    query = db.query(TelegramMessage).filter(TelegramMessage.group_id == group.id)
    
    # 关键词过滤
    if rule.keywords:
        keyword_conditions = []
        for keyword in rule.keywords:
            keyword_conditions.append(TelegramMessage.text.contains(keyword))
        if keyword_conditions:
            query = query.filter(or_(*keyword_conditions))
    
    # 排除关键词
    if rule.exclude_keywords:
        for exclude_keyword in rule.exclude_keywords:
            query = query.filter(~TelegramMessage.text.contains(exclude_keyword))
    
    # 媒体类型过滤
    if rule.media_types:
        query = query.filter(TelegramMessage.media_type.in_(rule.media_types))
    
    # 发送者过滤
    if rule.sender_filter:
        query = query.filter(TelegramMessage.sender_username.in_(rule.sender_filter))
    
    # 日期范围过滤
    if rule.date_from:
        query = query.filter(TelegramMessage.date >= rule.date_from)
    
    if rule.date_to:
        query = query.filter(TelegramMessage.date <= rule.date_to)
    
    # 浏览量过滤
    if rule.min_views is not None:
        query = query.filter(TelegramMessage.views >= rule.min_views)
    
    if rule.max_views is not None:
        query = query.filter(TelegramMessage.views <= rule.max_views)
    
    # 文件大小过滤
    if rule.min_file_size is not None:
        query = query.filter(TelegramMessage.file_size >= rule.min_file_size)
    
    if rule.max_file_size is not None:
        query = query.filter(TelegramMessage.file_size <= rule.max_file_size)
    
    # 转发消息过滤
    if not rule.include_forwarded:
        query = query.filter(TelegramMessage.is_forwarded == False)
    
    # 只选择有媒体的消息（与任务执行逻辑保持一致）
    query = query.filter(TelegramMessage.media_type != 'text')
    query = query.filter(TelegramMessage.media_type.isnot(None))
    
    return query.order_by(TelegramMessage.date.desc()).all()

def _generate_filter_summary(rule: FilterRule) -> dict:
    """生成过滤条件总结"""
    summary = {
        "active_filters": [],
        "filter_count": 0
    }
    
    if rule.keywords:
        summary["active_filters"].append(f"包含关键词: {', '.join(rule.keywords)}")
        summary["filter_count"] += 1
    
    if rule.exclude_keywords:
        summary["active_filters"].append(f"排除关键词: {', '.join(rule.exclude_keywords)}")
        summary["filter_count"] += 1
    
    if rule.media_types:
        summary["active_filters"].append(f"媒体类型: {', '.join(rule.media_types)}")
        summary["filter_count"] += 1
    
    if rule.sender_filter:
        summary["active_filters"].append(f"发送者: {', '.join(rule.sender_filter)}")
        summary["filter_count"] += 1
    
    if rule.date_from:
        summary["active_filters"].append(f"开始日期: {rule.date_from.strftime('%Y-%m-%d')}")
        summary["filter_count"] += 1
    
    if rule.date_to:
        summary["active_filters"].append(f"结束日期: {rule.date_to.strftime('%Y-%m-%d')}")
        summary["filter_count"] += 1
    
    if rule.min_views is not None:
        summary["active_filters"].append(f"最小浏览量: {rule.min_views}")
        summary["filter_count"] += 1
    
    if rule.max_views is not None:
        summary["active_filters"].append(f"最大浏览量: {rule.max_views}")
        summary["filter_count"] += 1
    
    if rule.min_file_size is not None:
        summary["active_filters"].append(f"最小文件大小: {rule.min_file_size} 字节")
        summary["filter_count"] += 1
    
    if rule.max_file_size is not None:
        summary["active_filters"].append(f"最大文件大小: {rule.max_file_size} 字节")
        summary["filter_count"] += 1
    
    if not rule.include_forwarded:
        summary["active_filters"].append("排除转发消息")
        summary["filter_count"] += 1
    
    # 默认过滤条件
    summary["active_filters"].append("仅媒体消息")
    summary["filter_count"] += 1
    
    if summary["filter_count"] == 1:  # 只有默认的媒体过滤
        summary["message"] = "当前规则将匹配所有媒体消息"
    else:
        summary["message"] = f"当前规则应用了 {summary['filter_count']} 个过滤条件"
    
    return summary

@router.post("/rules/{rule_id}/validate", response_model=RuleValidationResponse)
async def validate_rule(
    rule_id: int,
    db: Session = Depends(get_db)
):
    """验证规则的完整性和有效性"""
    try:
        # 获取规则
        rule = db.query(FilterRule).filter(FilterRule.id == rule_id).first()
        if not rule:
            raise HTTPException(status_code=404, detail="规则不存在")
        
        validation_errors = []
        validation_warnings = []
        recommended_actions = []
        
        # 检查群组是否存在
        group = db.query(TelegramGroup).filter(TelegramGroup.id == rule.group_id).first()
        if not group:
            validation_errors.append("关联的群组不存在或已被删除")
            recommended_actions.append("请重新选择有效的群组")
        
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
        
        # 检查群组中是否有消息
        if group:
            message_count = db.query(TelegramMessage).filter(TelegramMessage.group_id == group.id).count()
            if message_count == 0:
                validation_warnings.append("关联的群组中没有消息")
                recommended_actions.append("确保群组已同步消息数据")
            
            # 测试规则匹配
            try:
                matched_messages = await _apply_rule_filter(rule, group, db)
                match_count = len(matched_messages)
                
                if match_count == 0:
                    validation_warnings.append("当前规则条件下没有匹配的消息")
                    recommended_actions.append("请调整过滤条件或检查群组消息")
                elif match_count > 10000:
                    validation_warnings.append(f"匹配的消息数量很大 ({match_count})，执行任务可能需要较长时间")
                    recommended_actions.append("考虑添加更多过滤条件来缩小范围")
                    
            except Exception as e:
                validation_errors.append(f"测试规则匹配时出错: {str(e)}")
                recommended_actions.append("请检查规则配置是否正确")
        
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
        
        # 按群组统计
        group_stats = db.query(FilterRule.group_id, db.func.count(FilterRule.id)).group_by(FilterRule.group_id).all()
        
        return {
            "total_rules": total_rules,
            "active_rules": active_rules,
            "inactive_rules": inactive_rules,
            "rules_by_group": [{"group_id": gid, "rule_count": count} for gid, count in group_stats]
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