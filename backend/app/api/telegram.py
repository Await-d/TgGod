from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db
from ..models.telegram import TelegramGroup, TelegramMessage
from ..services.telegram_service import telegram_service
from ..utils.auth import get_current_active_user
from pydantic import BaseModel
from datetime import datetime
import json
import logging
import asyncio

logger = logging.getLogger(__name__)
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

class MonthInfo(BaseModel):
    year: int
    month: int

class MonthlySyncRequest(BaseModel):
    months: List[MonthInfo]

class MonthlySyncResponse(BaseModel):
    success: bool
    total_messages: int
    months_synced: int
    failed_months: List[dict]
    monthly_stats: List[dict]
    error: Optional[str] = None

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
    media_filename: Optional[str]
    view_count: int
    is_forwarded: bool
    forwarded_from: Optional[str]
    is_own_message: bool
    reply_to_message_id: Optional[int]
    edit_date: Optional[datetime]
    is_pinned: bool
    reactions: Optional[dict]
    mentions: Optional[list]
    hashtags: Optional[list]
    urls: Optional[list]
    date: datetime
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class MessageSendRequest(BaseModel):
    text: str
    reply_to_message_id: Optional[int] = None

class TelegramUserResponse(BaseModel):
    id: int
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    full_name: Optional[str]
    is_self: bool


class MessageSearchRequest(BaseModel):
    query: Optional[str] = None
    sender_username: Optional[str] = None
    media_type: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    has_media: Optional[bool] = None
    is_forwarded: Optional[bool] = None

@router.get("/groups", response_model=List[GroupResponse])
async def get_groups(
    skip: int = Query(0, ge=0),
    limit: int = Query(1000, ge=1, le=1000),
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
    search: Optional[str] = Query(None, description="搜索消息内容"),
    sender_username: Optional[str] = Query(None, description="按发送者用户名过滤"),
    media_type: Optional[str] = Query(None, description="按媒体类型过滤"),
    has_media: Optional[bool] = Query(None, description="是否包含媒体"),
    is_forwarded: Optional[bool] = Query(None, description="是否为转发消息"),
    is_pinned: Optional[bool] = Query(None, description="是否为置顶消息"),
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """获取群组消息（支持搜索和过滤）"""
    
    # 检查群组是否存在
    group = db.query(TelegramGroup).filter(TelegramGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="群组不存在")
    
    # 构建查询
    query = db.query(TelegramMessage).filter(TelegramMessage.group_id == group_id)
    
    # 应用过滤条件
    if search:
        query = query.filter(TelegramMessage.text.contains(search))
    
    if sender_username:
        query = query.filter(TelegramMessage.sender_username == sender_username)
    
    if media_type:
        query = query.filter(TelegramMessage.media_type == media_type)
    
    if has_media is not None:
        if has_media:
            query = query.filter(TelegramMessage.media_type.isnot(None))
        else:
            query = query.filter(TelegramMessage.media_type.is_(None))
    
    if is_forwarded is not None:
        query = query.filter(TelegramMessage.is_forwarded == is_forwarded)
    
    if is_pinned is not None:
        query = query.filter(TelegramMessage.is_pinned == is_pinned)
    
    if start_date:
        query = query.filter(TelegramMessage.date >= start_date)
    
    if end_date:
        query = query.filter(TelegramMessage.date <= end_date)
    
    # 排序和分页逻辑：
    # 1. 如果是置顶消息，按照置顶时间排序（最新置顶的在前）
    # 2. 普通消息按照日期排序，先获取最新的消息（倒序），然后对结果进行正序排列
    # 3. 这样前端就不需要做任何排序操作
    
    if is_pinned is True:
        # 置顶消息按照消息ID降序排列（最新置顶的在前）
        messages_desc = query.order_by(TelegramMessage.id.desc()).offset(skip).limit(limit).all()
        # 反转为正序（最早置顶的在前，最新置顶的在后）
        messages = list(reversed(messages_desc))
    else:
        # 获取消息（降序获取最新的）
        messages_desc = query.order_by(TelegramMessage.date.desc()).offset(skip).limit(limit).all()
        # 反转为正序（最老消息在前，最新消息在后）
        messages = list(reversed(messages_desc))
    
    return messages


@router.get("/groups/{group_id}/messages/{message_id}", response_model=MessageResponse)
async def get_message_detail(
    group_id: int,
    message_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """获取单条消息详情"""
    
    # 检查群组是否存在
    group = db.query(TelegramGroup).filter(TelegramGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="群组不存在")
    
    # 获取消息
    message = db.query(TelegramMessage).filter(
        TelegramMessage.group_id == group_id,
        TelegramMessage.message_id == message_id
    ).first()
    
    if not message:
        raise HTTPException(status_code=404, detail="消息不存在")
    
    return message


@router.get("/groups/{group_id}/messages/{message_id}/replies", response_model=List[MessageResponse])
async def get_message_replies(
    group_id: int,
    message_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """获取消息的回复"""
    
    # 检查群组是否存在
    group = db.query(TelegramGroup).filter(TelegramGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="群组不存在")
    
    # 获取回复消息
    replies = db.query(TelegramMessage).filter(
        TelegramMessage.group_id == group_id,
        TelegramMessage.reply_to_message_id == message_id
    ).order_by(TelegramMessage.date.asc()).offset(skip).limit(limit).all()
    
    return replies

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
        # 决定使用哪个标识符来获取消息
        group_identifier = None
        
        # 优先使用username
        if group.username:
            group_identifier = group.username
            logger.info(f"使用群组用户名获取消息: {group.username}")
        # 其次使用telegram_id
        elif group.telegram_id:
            group_identifier = group.telegram_id
            logger.info(f"使用群组ID获取消息: {group.telegram_id}")
        else:
            raise HTTPException(
                status_code=400, 
                detail="群组缺少必要的标识符(username或telegram_id)"
            )
        
        # 获取消息
        messages = await telegram_service.get_messages(group_identifier, limit=limit)
        
        # 保存到数据库
        saved_count = await telegram_service.save_messages_to_db(group_id, messages, db)
        
        # 如果有新消息，通过WebSocket推送消息统计更新
        if saved_count > 0:
            try:
                from ..websocket.manager import websocket_manager
                
                # 推送消息统计更新
                stats_data = {
                    "group_id": group_id,
                    "new_messages": saved_count,
                    "total_fetched": len(messages),
                    "sync_time": datetime.now().isoformat()
                }
                
                await websocket_manager.send_message_stats(stats_data)
                
            except Exception as ws_error:
                logger.error(f"WebSocket推送失败: {ws_error}")
                # 不影响API响应
        
        return {
            "message": f"成功同步 {saved_count} 条消息", 
            "total_fetched": len(messages),
            "total_saved": saved_count
        }
    
    except Exception as e:
        logger.error(f"同步群组消息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/groups/{group_id}/sync-monthly", response_model=MonthlySyncResponse)
async def sync_group_messages_monthly(
    group_id: int,
    request: MonthlySyncRequest,
    db: Session = Depends(get_db)
):
    """按月同步群组消息"""
    # 检查群组是否存在
    group = db.query(TelegramGroup).filter(TelegramGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="群组不存在")
    
    try:
        # 决定使用哪个标识符来获取消息
        group_identifier = None
        
        # 优先使用username
        if group.username:
            group_identifier = group.username
            logger.info(f"使用群组用户名按月同步: {group.username}")
        # 其次使用telegram_id
        elif group.telegram_id:
            group_identifier = group.telegram_id
            logger.info(f"使用群组ID按月同步: {group.telegram_id}")
        else:
            raise HTTPException(
                status_code=400, 
                detail="群组缺少必要的标识符(username或telegram_id)"
            )
        
        # 转换月份数据
        months_data = [{"year": month.year, "month": month.month} for month in request.months]
        
        # 执行按月同步
        result = await telegram_service.sync_messages_by_month(group_identifier, months_data)
        
        # 通过WebSocket推送更新
        try:
            from ..websocket import websocket_manager
            await websocket_manager.send_message(
                f"group_{group_id}",
                {
                    "type": "monthly_sync_complete",
                    "data": result
                }
            )
        except Exception as ws_e:
            logger.warning(f"WebSocket推送失败: {ws_e}")
        
        return MonthlySyncResponse(**result)
    
    except Exception as e:
        logger.error(f"按月同步群组消息失败: {e}")
        raise HTTPException(status_code=500, detail=f"按月同步失败: {str(e)}")

@router.get("/groups/{group_id}/default-sync-months")
async def get_default_sync_months(
    group_id: int,
    count: int = Query(3, ge=1, le=12),
    db: Session = Depends(get_db)
):
    """获取默认的同步月份（最近N个月）"""
    # 检查群组是否存在
    group = db.query(TelegramGroup).filter(TelegramGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="群组不存在")
    
    try:
        months = await telegram_service.get_default_sync_months(count)
        return {"months": months}
    
    except Exception as e:
        logger.error(f"获取默认同步月份失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取默认同步月份失败: {str(e)}")

@router.post("/sync-all-groups-monthly", response_model=dict)
async def sync_all_groups_monthly(
    request: MonthlySyncRequest,
    db: Session = Depends(get_db)
):
    """对所有活跃群组执行按月同步"""
    try:
        # 获取所有活跃群组
        active_groups = db.query(TelegramGroup).filter(
            TelegramGroup.is_active == True
        ).all()
        
        if not active_groups:
            return {"message": "没有活跃群组", "synced_groups": 0}
        
        # 转换月份数据
        months_data = [{"year": month.year, "month": month.month} for month in request.months]
        
        # 批量同步结果
        batch_result = {
            "success": True,
            "total_groups": len(active_groups),
            "synced_groups": 0,
            "failed_groups": [],
            "total_messages": 0,
            "group_results": []
        }
        
        # 逐个群组同步
        for group in active_groups:
            try:
                # 决定使用哪个标识符
                group_identifier = group.username if group.username else group.telegram_id
                
                if not group_identifier:
                    logger.warning(f"群组 {group.title} 缺少标识符，跳过")
                    batch_result["failed_groups"].append({
                        "group_id": group.id,
                        "title": group.title,
                        "error": "缺少标识符"
                    })
                    continue
                
                # 执行同步
                result = await telegram_service.sync_messages_by_month(group_identifier, months_data)
                
                if result["success"]:
                    batch_result["synced_groups"] += 1
                    batch_result["total_messages"] += result["total_messages"]
                    batch_result["group_results"].append({
                        "group_id": group.id,
                        "title": group.title,
                        "result": result
                    })
                else:
                    batch_result["failed_groups"].append({
                        "group_id": group.id,
                        "title": group.title,
                        "error": result.get("error", "同步失败")
                    })
                
                # 添加延迟以避免API限制
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"群组 {group.title} 同步失败: {e}")
                batch_result["failed_groups"].append({
                    "group_id": group.id,
                    "title": group.title,
                    "error": str(e)
                })
        
        # 通过WebSocket推送更新
        try:
            from ..websocket import websocket_manager
            await websocket_manager.broadcast({
                "type": "batch_monthly_sync_complete",
                "data": batch_result
            })
        except Exception as ws_e:
            logger.warning(f"WebSocket推送失败: {ws_e}")
        
        return batch_result
        
    except Exception as e:
        logger.error(f"批量按月同步失败: {e}")
        raise HTTPException(status_code=500, detail=f"批量按月同步失败: {str(e)}")

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
    
    # 统计各类型媒体消息数量
    photo_messages = db.query(TelegramMessage).filter(
        TelegramMessage.group_id == group_id,
        TelegramMessage.media_type == 'photo'
    ).count()
    
    video_messages = db.query(TelegramMessage).filter(
        TelegramMessage.group_id == group_id,
        TelegramMessage.media_type == 'video'
    ).count()
    
    document_messages = db.query(TelegramMessage).filter(
        TelegramMessage.group_id == group_id,
        TelegramMessage.media_type == 'document'
    ).count()
    
    audio_messages = db.query(TelegramMessage).filter(
        TelegramMessage.group_id == group_id,
        TelegramMessage.media_type.in_(['audio', 'voice'])
    ).count()
    
    # 统计转发消息数量
    forwarded_messages = db.query(TelegramMessage).filter(
        TelegramMessage.group_id == group_id,
        TelegramMessage.is_forwarded == True
    ).count()
    
    # 统计置顶消息数量
    pinned_messages = db.query(TelegramMessage).filter(
        TelegramMessage.group_id == group_id,
        TelegramMessage.is_pinned == True
    ).count()
    
    # 统计有反应的消息数量
    messages_with_reactions = db.query(TelegramMessage).filter(
        TelegramMessage.group_id == group_id,
        TelegramMessage.reactions.isnot(None)
    ).count()
    
    return {
        "total_messages": total_messages,
        "media_messages": media_messages,
        "text_messages": total_messages - media_messages,
        "photo_messages": photo_messages,
        "video_messages": video_messages,
        "document_messages": document_messages,
        "audio_messages": audio_messages,
        "forwarded_messages": forwarded_messages,
        "pinned_messages": pinned_messages,
        "messages_with_reactions": messages_with_reactions,
        "member_count": group.member_count
    }


@router.post("/groups/{group_id}/send", response_model=dict)
async def send_message_to_group(
    group_id: int,
    message_request: MessageSendRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """发送消息到群组"""
    
    # 检查群组是否存在
    group = db.query(TelegramGroup).filter(TelegramGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="群组不存在")
    
    try:
        # 发送消息
        message_id = await telegram_service.send_message(
            group.username,
            message_request.text,
            reply_to_message_id=message_request.reply_to_message_id
        )
        
        if message_id:
            # 发送消息成功后，通过WebSocket推送消息更新
            try:
                from ..websocket.manager import websocket_manager
                
                # 构造消息数据
                message_data = {
                    "chat_id": group_id,
                    "message_id": message_id,
                    "text": message_request.text,
                    "sender_name": current_user.full_name or current_user.username,
                    "sender_username": current_user.username,
                    "date": datetime.now().isoformat(),
                    "is_own_message": True,
                    "reply_to_message_id": message_request.reply_to_message_id
                }
                
                # 广播新消息
                await websocket_manager.send_message(message_data)
                
            except Exception as ws_error:
                logger.error(f"WebSocket推送失败: {ws_error}")
                # 不影响API响应
            
            return {
                "success": True,
                "message_id": message_id,
                "message": "消息发送成功"
            }
        else:
            raise HTTPException(status_code=500, detail="消息发送失败")
    
    except Exception as e:
        logger.error(f"发送消息失败: {e}")
        raise HTTPException(status_code=500, detail=f"发送消息失败: {str(e)}")


@router.post("/groups/{group_id}/messages/{message_id}/reply", response_model=dict)
async def reply_to_message(
    group_id: int,
    message_id: int,
    text: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """回复消息"""
    
    # 检查群组是否存在
    group = db.query(TelegramGroup).filter(TelegramGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="群组不存在")
    
    # 检查要回复的消息是否存在
    original_message = db.query(TelegramMessage).filter(
        TelegramMessage.group_id == group_id,
        TelegramMessage.message_id == message_id
    ).first()
    
    if not original_message:
        raise HTTPException(status_code=404, detail="要回复的消息不存在")
    
    try:
        # 回复消息
        reply_message_id = await telegram_service.send_message(
            group.username,
            text,
            reply_to_message_id=message_id
        )
        
        if reply_message_id:
            return {
                "success": True,
                "message_id": reply_message_id,
                "reply_to_message_id": message_id,
                "message": "回复发送成功"
            }
        else:
            raise HTTPException(status_code=500, detail="回复发送失败")
    
    except Exception as e:
        logger.error(f"回复消息失败: {e}")
        raise HTTPException(status_code=500, detail=f"回复消息失败: {str(e)}")


@router.delete("/groups/{group_id}/messages/{message_id}")
async def delete_message(
    group_id: int,
    message_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """删除消息"""
    
    # 检查群组是否存在
    group = db.query(TelegramGroup).filter(TelegramGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="群组不存在")
    
    # 检查消息是否存在
    message = db.query(TelegramMessage).filter(
        TelegramMessage.group_id == group_id,
        TelegramMessage.message_id == message_id
    ).first()
    
    if not message:
        raise HTTPException(status_code=404, detail="消息不存在")
    
    try:
        # 删除Telegram消息
        success = await telegram_service.delete_message(group.username, message_id)
        
        if success:
            # 从数据库中删除消息记录
            db.delete(message)
            db.commit()
            
            return {"success": True, "message": "消息删除成功"}
        else:
            raise HTTPException(status_code=500, detail="消息删除失败")
    
    except Exception as e:
        logger.error(f"删除消息失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除消息失败: {str(e)}")


@router.post("/groups/{group_id}/messages/search", response_model=List[MessageResponse])
async def search_messages(
    group_id: int,
    search_request: MessageSearchRequest,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """搜索群组消息"""
    
    # 检查群组是否存在
    group = db.query(TelegramGroup).filter(TelegramGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="群组不存在")
    
    # 构建查询
    query = db.query(TelegramMessage).filter(TelegramMessage.group_id == group_id)
    
    # 应用搜索条件
    if search_request.query:
        query = query.filter(TelegramMessage.text.contains(search_request.query))
    
    if search_request.sender_username:
        query = query.filter(TelegramMessage.sender_username == search_request.sender_username)
    
    if search_request.media_type:
        query = query.filter(TelegramMessage.media_type == search_request.media_type)
    
    if search_request.has_media is not None:
        if search_request.has_media:
            query = query.filter(TelegramMessage.media_type.isnot(None))
        else:
            query = query.filter(TelegramMessage.media_type.is_(None))
    
    if search_request.is_forwarded is not None:
        query = query.filter(TelegramMessage.is_forwarded == search_request.is_forwarded)
    
    if search_request.start_date:
        query = query.filter(TelegramMessage.date >= search_request.start_date)
    
    if search_request.end_date:
        query = query.filter(TelegramMessage.date <= search_request.end_date)
    
    # 排序和分页
    messages = query.order_by(TelegramMessage.date.desc()).offset(skip).limit(limit).all()
    
    return messages


# Telegram认证相关API
class AuthStatusResponse(BaseModel):
    is_authorized: bool
    user_info: Optional[dict] = None
    message: str

class AuthCodeRequest(BaseModel):
    phone: str

class AuthLoginRequest(BaseModel):
    phone: str
    code: str
    password: Optional[str] = None

class AuthState(BaseModel):
    phone: str
    phone_code_hash: str
    
# 临时存储认证状态 (生产环境应使用Redis等持久化存储)
auth_sessions = {}

@router.get("/auth/status", response_model=AuthStatusResponse)
async def get_auth_status():
    """获取Telegram认证状态"""
    try:
        await telegram_service.initialize()
        is_authorized = await telegram_service.client.is_user_authorized()
        
        if is_authorized:
            me = await telegram_service.client.get_me()
            user_info = {
                "id": me.id,
                "first_name": me.first_name,
                "last_name": me.last_name,
                "username": me.username,
                "phone": me.phone
            }
            await telegram_service.disconnect()
            return AuthStatusResponse(
                is_authorized=True,
                user_info=user_info,
                message="已授权"
            )
        else:
            await telegram_service.disconnect()
            return AuthStatusResponse(
                is_authorized=False,
                message="未授权，需要进行手机验证"
            )
    except Exception as e:
        logger.error(f"获取认证状态失败: {e}")
        await telegram_service.disconnect()
        return AuthStatusResponse(
            is_authorized=False,
            message=f"获取认证状态失败: {str(e)}"
        )

@router.post("/auth/send-code")
async def send_auth_code(request: AuthCodeRequest):
    """发送验证码"""
    try:
        # 确保每次都重新初始化客户端
        await telegram_service.disconnect()  # 先断开现有连接
        await telegram_service.initialize()
        
        logger.info(f"准备发送验证码到: {request.phone}")
        # 发送验证码并获取phone_code_hash
        result = await telegram_service.client.send_code_request(request.phone)
        
        # 保存认证状态
        session_key = f"auth_{request.phone}"
        auth_sessions[session_key] = AuthState(
            phone=request.phone,
            phone_code_hash=result.phone_code_hash
        )
        
        await telegram_service.disconnect()
        
        return {
            "success": True,
            "message": "验证码已发送",
            "session_key": session_key  # 返回session key给前端
        }
    except Exception as e:
        logger.error(f"发送验证码失败: {e}")
        await telegram_service.disconnect()
        raise HTTPException(status_code=500, detail=f"发送验证码失败: {str(e)}")

@router.post("/auth/login")
async def login_with_code(request: AuthLoginRequest):
    """使用验证码登录"""
    try:
        # 获取认证状态
        session_key = f"auth_{request.phone}"
        if session_key not in auth_sessions:
            raise HTTPException(status_code=400, detail="请先发送验证码")
        
        auth_state = auth_sessions[session_key]
        
        # 确保每次都重新初始化客户端
        await telegram_service.disconnect()  # 先断开现有连接
        await telegram_service.initialize()
        
        try:
            # 使用phone_code_hash进行登录
            await telegram_service.client.sign_in(
                phone=request.phone,
                code=request.code,
                phone_code_hash=auth_state.phone_code_hash
            )
        except Exception as auth_error:
            # 检查是否需要两步验证
            if "Two-step verification" in str(auth_error) or "SessionPasswordNeeded" in str(auth_error):
                if not request.password:
                    await telegram_service.disconnect()
                    raise HTTPException(
                        status_code=400, 
                        detail="需要两步验证密码"
                    )
                # 使用两步验证密码
                await telegram_service.client.sign_in(password=request.password)
            else:
                raise auth_error
        
        # 获取用户信息
        me = await telegram_service.client.get_me()
        user_info = {
            "id": me.id,
            "first_name": me.first_name,
            "last_name": me.last_name,
            "username": me.username,
            "phone": me.phone
        }
        
        await telegram_service.disconnect()
        
        # 清除认证状态
        if session_key in auth_sessions:
            del auth_sessions[session_key]
        
        return {
            "success": True,
            "message": "登录成功",
            "user_info": user_info
        }
        
    except Exception as e:
        logger.error(f"登录失败: {e}")
        await telegram_service.disconnect()
        raise HTTPException(status_code=500, detail=f"登录失败: {str(e)}")

@router.post("/auth/logout")
async def logout():
    """登出"""
    try:
        await telegram_service.initialize()
        await telegram_service.client.log_out()
        await telegram_service.disconnect()
        
        return {
            "success": True,
            "message": "登出成功"
        }
    except Exception as e:
        logger.error(f"登出失败: {e}")
        await telegram_service.disconnect()
        raise HTTPException(status_code=500, detail=f"登出失败: {str(e)}")

@router.get("/sync-status")
async def get_sync_status():
    """获取消息同步状态"""
    try:
        from ..tasks.message_sync import message_sync_task
        
        return {
            "success": True,
            "data": message_sync_task.get_sync_status()
        }
    except Exception as e:
        logger.error(f"获取同步状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取同步状态失败: {str(e)}")

@router.post("/sync-control")
async def control_sync(action: str):
    """控制消息同步任务"""
    try:
        from ..tasks.message_sync import message_sync_task
        
        if action == "start":
            message_sync_task.start()
            return {"success": True, "message": "同步任务已启动"}
        elif action == "stop":
            message_sync_task.stop()
            return {"success": True, "message": "同步任务已停止"}
        else:
            raise HTTPException(status_code=400, detail="无效的操作")
    except Exception as e:
        logger.error(f"控制同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"控制同步任务失败: {str(e)}")

@router.post("/groups/{group_id}/enable-realtime")
async def enable_realtime_sync(group_id: int, enabled: bool = True):
    """启用/禁用群组实时同步"""
    try:
        from ..tasks.message_sync import message_sync_task
        
        if enabled:
            message_sync_task.add_group(group_id, interval=30)
            return {"success": True, "message": f"群组 {group_id} 实时同步已启用"}
        else:
            message_sync_task.remove_group(group_id)
            return {"success": True, "message": f"群组 {group_id} 实时同步已禁用"}
    except Exception as e:
        logger.error(f"设置实时同步失败: {e}")
        raise HTTPException(status_code=500, detail=f"设置实时同步失败: {str(e)}")

@router.post("/sync-groups")
async def sync_telegram_groups(db: Session = Depends(get_db)):
    """从Telegram同步群组列表到数据库"""
    try:
        await telegram_service.initialize()
        
        # 检查是否已授权
        is_authorized = await telegram_service.client.is_user_authorized()
        if not is_authorized:
            await telegram_service.disconnect()
            raise HTTPException(status_code=401, detail="Telegram未授权，请先完成认证")
        
        # 获取对话列表
        dialogs = await telegram_service.client.get_dialogs()
        groups = [d for d in dialogs if d.is_group or d.is_channel]
        
        synced_count = 0
        errors = []
        
        for i, dialog in enumerate(groups):
            try:
                # 添加延迟以避免flood wait
                if i > 0 and i % 5 == 0:
                    logger.info(f"处理第{i}个群组，暂停2秒避免频率限制...")
                    await asyncio.sleep(2)
                
                # 直接传递dialog.entity，避免ID查找问题
                group_info = await telegram_service.get_group_info(dialog.entity)
                if group_info:
                    # 检查群组是否已存在
                    existing_group = db.query(TelegramGroup).filter(
                        TelegramGroup.telegram_id == group_info["telegram_id"]
                    ).first()
                    
                    if existing_group:
                        # 更新现有群组信息
                        for key, value in group_info.items():
                            setattr(existing_group, key, value)
                        logger.info(f"更新群组: {group_info['title']}")
                    else:
                        # 创建新群组
                        new_group = TelegramGroup(**group_info)
                        db.add(new_group)
                        logger.info(f"新增群组: {group_info['title']}")
                    
                    synced_count += 1
                else:
                    logger.warning(f"跳过群组 {getattr(dialog, 'name', 'Unknown')}，无法获取信息")
                    
            except Exception as e:
                error_msg = f"同步群组 {getattr(dialog, 'name', 'Unknown')} 失败: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
                
                # 如果是flood wait错误，增加延迟
                if "flood" in str(e).lower() or "wait" in str(e).lower():
                    logger.info("检测到频率限制，等待5秒...")
                    await asyncio.sleep(5)
        
        db.commit()
        await telegram_service.disconnect()
        
        return {
            "success": True,
            "message": f"成功同步 {synced_count} 个群组",
            "synced_count": synced_count,
            "total_groups": len(groups),
            "errors": errors
        }
        
    except Exception as e:
        logger.error(f"同步群组失败: {e}")
        await telegram_service.disconnect()
        raise HTTPException(status_code=500, detail=f"同步群组失败: {str(e)}")

@router.post("/test-connection")
async def test_telegram_connection():
    """测试Telegram连接和群组获取"""
    try:
        await telegram_service.initialize()
        
        # 检查是否已授权
        is_authorized = await telegram_service.client.is_user_authorized()
        
        if not is_authorized:
            await telegram_service.disconnect()
            return {
                "success": False,
                "message": "未授权，请先完成Telegram认证",
                "connection_status": "unauthorized"
            }
        
        # 获取用户信息
        me = await telegram_service.client.get_me()
        
        # 尝试获取对话列表
        dialogs = await telegram_service.client.get_dialogs()
        groups = [d for d in dialogs if d.is_group or d.is_channel]
        
        await telegram_service.disconnect()
        
        return {
            "success": True,
            "message": "连接测试成功",
            "connection_status": "connected",
            "user_info": {
                "id": me.id,
                "first_name": me.first_name,
                "last_name": me.last_name,
                "username": me.username,
                "phone": me.phone
            },
            "stats": {
                "total_dialogs": len(dialogs),
                "total_groups": len(groups),
                "groups_preview": [
                    {
                        "id": group.entity.id,
                        "name": group.name,
                        "is_channel": group.is_channel
                    }
                    for group in groups[:5]  # 前5个群组预览
                ]
            }
        }
        
    except Exception as e:
        logger.error(f"连接测试失败: {e}")
        await telegram_service.disconnect()
        return {
            "success": False,
            "message": f"连接测试失败: {str(e)}",
            "connection_status": "error"
        }

@router.get("/media-info")
async def get_media_info():
    """获取媒体文件信息"""
    try:
        from ..config import settings
        import os
        
        media_root = settings.media_root
        
        info = {
            "media_root": media_root,
            "media_exists": os.path.exists(media_root),
            "directories": {}
        }
        
        if os.path.exists(media_root):
            for subdir in ["photos", "videos", "audios", "documents"]:
                subdir_path = os.path.join(media_root, subdir)
                info["directories"][subdir] = {
                    "exists": os.path.exists(subdir_path),
                    "path": subdir_path,
                    "files": []
                }
                
                if os.path.exists(subdir_path):
                    files = os.listdir(subdir_path)
                    info["directories"][subdir]["files"] = files[:5]  # 只显示前5个文件
                    info["directories"][subdir]["count"] = len(files)
        
        return info
        
    except Exception as e:
        return {"error": str(e)}

@router.get("/me", response_model=TelegramUserResponse)
async def get_current_telegram_user():
    """获取当前 Telegram 用户信息"""
    try:
        # 确保 Telegram 客户端已连接
        await telegram_service.initialize()
        
        # 获取当前用户信息
        me = await telegram_service.client.get_me()
        
        if me:
            full_name = ""
            if me.first_name:
                full_name = me.first_name
            if me.last_name:
                full_name += f" {me.last_name}" if full_name else me.last_name
            
            return TelegramUserResponse(
                id=me.id,
                username=me.username,
                first_name=me.first_name,
                last_name=me.last_name,
                full_name=full_name.strip() if full_name else None,
                is_self=True
            )
        else:
            raise HTTPException(status_code=500, detail="无法获取当前用户信息")
    
    except Exception as e:
        logger.error(f"获取当前用户信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取当前用户信息失败: {str(e)}")