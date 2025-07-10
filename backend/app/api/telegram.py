from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db
from ..models.telegram import TelegramGroup, TelegramMessage
from ..services.telegram_service import telegram_service
from ..utils.auth import get_current_active_user
from pydantic import BaseModel
from datetime import datetime
import logging

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
    search: Optional[str] = Query(None, description="搜索消息内容"),
    sender_username: Optional[str] = Query(None, description="按发送者用户名过滤"),
    media_type: Optional[str] = Query(None, description="按媒体类型过滤"),
    has_media: Optional[bool] = Query(None, description="是否包含媒体"),
    is_forwarded: Optional[bool] = Query(None, description="是否为转发消息"),
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
    
    if start_date:
        query = query.filter(TelegramMessage.date >= start_date)
    
    if end_date:
        query = query.filter(TelegramMessage.date <= end_date)
    
    # 排序和分页
    messages = query.order_by(TelegramMessage.date.desc()).offset(skip).limit(limit).all()
    
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
        await telegram_service.client.send_code_request(request.phone)
        await telegram_service.disconnect()
        
        return {
            "success": True,
            "message": "验证码已发送"
        }
    except Exception as e:
        logger.error(f"发送验证码失败: {e}")
        await telegram_service.disconnect()
        raise HTTPException(status_code=500, detail=f"发送验证码失败: {str(e)}")

@router.post("/auth/login")
async def login_with_code(request: AuthLoginRequest):
    """使用验证码登录"""
    try:
        # 确保每次都重新初始化客户端
        await telegram_service.disconnect()  # 先断开现有连接
        await telegram_service.initialize()
        
        try:
            # 尝试使用验证码登录
            await telegram_service.client.sign_in(request.phone, request.code)
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