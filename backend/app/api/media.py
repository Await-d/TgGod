from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional
import os
import uuid
import logging
from ..database import get_db
from ..models import TelegramMessage
from ..services.telegram_service import TelegramService
import asyncio

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/download/{message_id}")
async def download_media_file(
    message_id: int,
    background_tasks: BackgroundTasks,
    force: bool = False,  # 是否强制重新下载
    db: Session = Depends(get_db)
):
    """
    按需下载媒体文件
    
    Args:
        message_id: 消息ID
        force: 是否强制重新下载（即使已下载）
        db: 数据库会话
    
    Returns:
        下载状态和文件信息
    """
    # 查找消息
    message = db.query(TelegramMessage).filter(TelegramMessage.id == message_id).first()
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="消息不存在"
        )
    
    # 检查是否有媒体文件
    if not message.media_type or not message.media_file_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该消息不包含媒体文件"
        )
    
    # 如果已下载且不强制重新下载，返回现有文件信息
    if message.media_downloaded and message.media_path and not force:
        if os.path.exists(message.media_path):
            return {
                "status": "already_downloaded",
                "message": "文件已存在",
                "file_path": message.media_path,
                "file_size": message.media_size,
                "download_url": f"/media/{os.path.relpath(message.media_path, './media')}"
            }
        else:
            # 文件记录存在但实际文件丢失，重置下载状态
            message.media_downloaded = False
            message.media_path = None
            db.commit()
    
    # 添加后台下载任务
    background_tasks.add_task(
        download_media_background,
        message_id=message_id,
        force=force
    )
    
    return {
        "status": "download_started",
        "message": "下载任务已启动",
        "message_id": message_id,
        "media_type": message.media_type,
        "estimated_size": message.media_size
    }

@router.get("/download-status/{message_id}")
async def get_download_status(
    message_id: int,
    db: Session = Depends(get_db)
):
    """
    获取媒体文件下载状态
    
    Args:
        message_id: 消息ID
        db: 数据库会话
    
    Returns:
        下载状态信息
    """
    message = db.query(TelegramMessage).filter(TelegramMessage.id == message_id).first()
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="消息不存在"
        )
    
    if not message.media_type:
        return {
            "status": "no_media",
            "message": "该消息不包含媒体文件"
        }
    
    if message.media_downloaded and message.media_path:
        if os.path.exists(message.media_path):
            return {
                "status": "downloaded",
                "message": "文件已下载",
                "file_path": message.media_path,
                "file_size": message.media_size,
                "download_url": f"/media/{os.path.relpath(message.media_path, './media')}"
            }
        else:
            return {
                "status": "file_missing",
                "message": "文件记录存在但实际文件丢失"
            }
    
    if message.media_download_error:
        return {
            "status": "download_failed",
            "message": "下载失败",
            "error": message.media_download_error
        }
    
    return {
        "status": "not_downloaded",
        "message": "文件未下载",
        "media_type": message.media_type,
        "file_id": message.media_file_id
    }

@router.delete("/media/{message_id}")
async def delete_media_file(
    message_id: int,
    db: Session = Depends(get_db)
):
    """
    删除本地媒体文件（保留数据库记录）
    
    Args:
        message_id: 消息ID
        db: 数据库会话
    
    Returns:
        删除结果
    """
    message = db.query(TelegramMessage).filter(TelegramMessage.id == message_id).first()
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="消息不存在"
        )
    
    if not message.media_downloaded or not message.media_path:
        return {
            "status": "no_file",
            "message": "没有本地文件可删除"
        }
    
    try:
        # 删除主文件
        if os.path.exists(message.media_path):
            os.remove(message.media_path)
            logger.info(f"已删除媒体文件: {message.media_path}")
        
        # 删除缩略图
        if message.media_thumbnail_path and os.path.exists(message.media_thumbnail_path):
            os.remove(message.media_thumbnail_path)
            logger.info(f"已删除缩略图: {message.media_thumbnail_path}")
        
        # 更新数据库状态
        message.media_downloaded = False
        message.media_path = None
        message.media_thumbnail_path = None
        message.media_download_error = None
        db.commit()
        
        return {
            "status": "deleted",
            "message": "文件已删除",
            "message_id": message_id
        }
        
    except Exception as e:
        logger.error(f"删除媒体文件失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除文件失败: {str(e)}"
        )

async def download_media_background(message_id: int, force: bool = False):
    """
    后台下载媒体文件任务
    
    Args:
        message_id: 消息ID
        force: 是否强制重新下载
    """
    from ..database import SessionLocal
    
    db = SessionLocal()
    try:
        message = db.query(TelegramMessage).filter(TelegramMessage.id == message_id).first()
        if not message:
            logger.error(f"下载任务: 消息 {message_id} 不存在")
            return
        
        if not message.media_file_id:
            logger.error(f"下载任务: 消息 {message_id} 没有文件ID")
            return
        
        # 清除之前的错误信息
        message.media_download_error = None
        db.commit()
        
        try:
            # 创建Telegram服务实例
            telegram_service = TelegramService()
            
            # 构建文件保存路径
            media_dir = f"./media/{message.media_type}s"
            os.makedirs(media_dir, exist_ok=True)
            
            # 生成唯一文件名
            file_extension = ""
            if message.media_filename:
                file_extension = os.path.splitext(message.media_filename)[1]
            elif message.media_type == "photo":
                file_extension = ".jpg"
            elif message.media_type == "video":
                file_extension = ".mp4"
            elif message.media_type == "audio":
                file_extension = ".mp3"
            elif message.media_type == "voice":
                file_extension = ".ogg"
            elif message.media_type == "document":
                file_extension = ".bin"
            
            unique_filename = f"{message.group_id}_{message.message_id}_{uuid.uuid4().hex[:8]}{file_extension}"
            file_path = os.path.join(media_dir, unique_filename)
            
            # 下载文件
            from ..services.media_downloader import get_media_downloader
            downloader = await get_media_downloader()
            
            success = await downloader.download_file(
                file_id=message.media_file_id,
                file_path=file_path,
                chat_id=message.group.telegram_id if message.group else None,
                message_id=message.message_id
            )
            
            if success:
                # 更新数据库记录
                message.media_downloaded = True
                message.media_path = file_path
                
                # 获取实际文件大小
                if os.path.exists(file_path):
                    message.media_size = os.path.getsize(file_path)
                
                logger.info(f"媒体文件下载成功: {file_path}")
            else:
                message.media_download_error = "Telegram API下载失败"
                logger.error(f"媒体文件下载失败: 消息 {message_id}")
                
        except Exception as e:
            error_msg = f"下载过程中发生错误: {str(e)}"
            message.media_download_error = error_msg
            logger.error(f"下载任务异常: {error_msg}")
        
        finally:
            db.commit()
            
    except Exception as e:
        logger.error(f"下载任务数据库操作失败: {str(e)}")
    finally:
        db.close()