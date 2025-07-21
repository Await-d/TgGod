from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
import os
import uuid
import logging
import mimetypes
from ..database import get_db, SessionLocal
from ..models import TelegramMessage
import asyncio

router = APIRouter()
logger = logging.getLogger(__name__)

# Request/Response models for batch operations
class BatchDownloadRequest(BaseModel):
    message_ids: List[int]
    force: bool = False
    max_concurrent: int = 3  # Maximum concurrent downloads

class BatchDownloadResponse(BaseModel):
    batch_id: str
    status: str
    message: str
    total_files: int
    started_downloads: List[int]
    already_downloaded: List[int]
    failed_to_start: List[dict]

class BatchStatusResponse(BaseModel):
    batch_id: str
    total_files: int
    completed: int
    downloading: int
    failed: int
    pending: int
    overall_status: str
    files: List[dict]

# 简单的下载队列，防止并发冲突
download_queue = asyncio.Queue()
download_worker_started = False

# 正在下载的消息ID集合，防止重复下载
downloading_messages = set()

# 已取消的下载任务集合
cancelled_downloads = set()

# 批量下载管理
batch_downloads = {}  # batch_id -> {message_ids, status, started_at, max_concurrent}
batch_semaphores = {}  # batch_id -> asyncio.Semaphore for controlling concurrency

def build_media_url(file_path: str) -> str:
    """构建媒体文件的访问URL"""
    if not file_path:
        return ""
    
    # 标准化路径
    normalized_path = os.path.normpath(file_path)
    
    # 如果文件在media目录下，构建相对URL
    if 'media' in normalized_path:
        # 找到media目录的位置
        parts = normalized_path.split(os.sep)
        media_index = -1
        for i, part in enumerate(parts):
            if part == 'media':
                media_index = i
                break
        
        if media_index >= 0 and media_index < len(parts) - 1:
            # 获取media目录后的路径部分
            relative_parts = parts[media_index + 1:]
            return f"/media/{'/'.join(relative_parts)}"
    
    # 如果无法确定，使用文件名
    return f"/media/{os.path.basename(file_path)}"

@router.post("/batch-download", response_model=BatchDownloadResponse)
async def start_batch_download(
    request: BatchDownloadRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    批量下载多个媒体文件
    
    Args:
        request: 批量下载请求，包含消息ID列表和配置
        background_tasks: 后台任务管理器
        db: 数据库会话
    
    Returns:
        批量下载状态和信息
    """
    if not request.message_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="消息ID列表不能为空"
        )
    
    if len(request.message_ids) > 50:  # 限制单次批量下载数量
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="单次批量下载最多支持50个文件"
        )
    
    # 验证并分类消息
    valid_messages = []
    already_downloaded = []
    failed_to_start = []
    
    for message_id in request.message_ids:
        message = db.query(TelegramMessage).filter(TelegramMessage.id == message_id).first()
        if not message:
            failed_to_start.append({
                "message_id": message_id,
                "reason": "消息不存在"
            })
            continue
        
        if not message.media_type or not message.media_file_id:
            failed_to_start.append({
                "message_id": message_id,
                "reason": "该消息不包含媒体文件"
            })
            continue
        
        # 检查是否已下载
        if message.media_downloaded and message.media_path and not request.force:
            if os.path.exists(message.media_path):
                already_downloaded.append(message_id)
                continue
            else:
                # 文件记录存在但实际文件丢失，重置下载状态
                try:
                    message.media_downloaded = False
                    message.media_path = None
                    db.commit()
                    valid_messages.append(message_id)
                except Exception as e:
                    logger.warning(f"重置消息 {message_id} 下载状态失败: {str(e)}")
                    db.rollback()
                    failed_to_start.append({
                        "message_id": message_id,
                        "reason": f"重置下载状态失败: {str(e)}"
                    })
        else:
            valid_messages.append(message_id)
    
    if not valid_messages:
        return BatchDownloadResponse(
            batch_id="",
            status="no_files_to_download",
            message="没有需要下载的文件",
            total_files=len(request.message_ids),
            started_downloads=[],
            already_downloaded=already_downloaded,
            failed_to_start=failed_to_start
        )
    
    # 生成批量下载ID
    batch_id = f"batch_{uuid.uuid4().hex[:8]}"
    
    # 记录批量下载信息
    from datetime import datetime, timezone
    global batch_downloads, batch_semaphores
    
    batch_downloads[batch_id] = {
        "message_ids": valid_messages,
        "total_files": len(valid_messages),
        "status": "started",
        "started_at": datetime.now(timezone.utc),
        "max_concurrent": min(request.max_concurrent, 5),  # 最多5个并发
        "force": request.force
    }
    
    # 创建信号量控制并发数
    batch_semaphores[batch_id] = asyncio.Semaphore(batch_downloads[batch_id]["max_concurrent"])
    
    # 启动下载工作进程（如果还没启动）
    global download_worker_started
    if not download_worker_started:
        background_tasks.add_task(start_download_worker)
        download_worker_started = True
    
    # 启动批量下载管理器
    background_tasks.add_task(batch_download_manager, batch_id)
    
    logger.info(f"批量下载任务启动: {batch_id}, 文件数量: {len(valid_messages)}")
    
    return BatchDownloadResponse(
        batch_id=batch_id,
        status="started",
        message=f"批量下载任务已启动，包含 {len(valid_messages)} 个文件",
        total_files=len(request.message_ids),
        started_downloads=valid_messages,
        already_downloaded=already_downloaded,
        failed_to_start=failed_to_start
    )

@router.get("/batch-status/{batch_id}", response_model=BatchStatusResponse)
async def get_batch_download_status(
    batch_id: str,
    db: Session = Depends(get_db)
):
    """
    获取批量下载状态
    
    Args:
        batch_id: 批量下载ID
        db: 数据库会话
    
    Returns:
        批量下载状态信息
    """
    global batch_downloads
    
    if batch_id not in batch_downloads:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="批量下载任务不存在"
        )
    
    batch_info = batch_downloads[batch_id]
    message_ids = batch_info["message_ids"]
    
    # 获取所有文件的状态
    files_status = []
    completed = 0
    downloading = 0
    failed = 0
    pending = 0
    
    for message_id in message_ids:
        message = db.query(TelegramMessage).filter(TelegramMessage.id == message_id).first()
        if not message:
            files_status.append({
                "message_id": message_id,
                "status": "not_found",
                "progress": 0,
                "error": "消息不存在"
            })
            failed += 1
            continue
        
        file_status = {
            "message_id": message_id,
            "media_type": message.media_type,
            "media_filename": message.media_filename,
            "progress": message.download_progress or 0,
            "downloaded_size": message.downloaded_size or 0,
            "total_size": message.media_size or 0,
            "download_speed": message.download_speed or 0,
            "estimated_time_remaining": message.estimated_time_remaining or 0
        }
        
        if message.media_downloaded and message.media_path:
            if os.path.exists(message.media_path):
                file_status["status"] = "completed"
                file_status["file_path"] = message.media_path
                file_status["download_url"] = build_media_url(message.media_path)
                completed += 1
            else:
                file_status["status"] = "file_missing"
                file_status["error"] = "文件记录存在但实际文件丢失"
                failed += 1
        elif message.media_download_error:
            if message.media_download_error == "下载已取消":
                file_status["status"] = "cancelled"
            else:
                file_status["status"] = "failed"
            file_status["error"] = message.media_download_error
            failed += 1
        elif message_id in downloading_messages:
            file_status["status"] = "downloading"
            downloading += 1
        else:
            file_status["status"] = "pending"
            pending += 1
        
        files_status.append(file_status)
    
    # 确定总体状态
    total_files = len(message_ids)
    if completed == total_files:
        overall_status = "completed"
    elif failed == total_files:
        overall_status = "failed"
    elif downloading > 0 or pending > 0:
        overall_status = "in_progress"
    else:
        overall_status = "unknown"
    
    return BatchStatusResponse(
        batch_id=batch_id,
        total_files=total_files,
        completed=completed,
        downloading=downloading,
        failed=failed,
        pending=pending,
        overall_status=overall_status,
        files=files_status
    )

@router.post("/batch-cancel/{batch_id}")
async def cancel_batch_download(
    batch_id: str,
    db: Session = Depends(get_db)
):
    """
    取消批量下载任务
    
    Args:
        batch_id: 批量下载ID
        db: 数据库会话
    
    Returns:
        取消结果
    """
    global batch_downloads, cancelled_downloads
    
    if batch_id not in batch_downloads:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="批量下载任务不存在"
        )
    
    batch_info = batch_downloads[batch_id]
    message_ids = batch_info["message_ids"]
    
    # 标记批量任务为取消状态
    batch_info["status"] = "cancelled"
    
    # 取消所有相关的单个下载任务
    cancelled_count = 0
    for message_id in message_ids:
        if message_id in downloading_messages:
            cancelled_downloads.add(message_id)
            cancelled_count += 1
            
            # 更新数据库状态
            try:
                message = db.query(TelegramMessage).filter(TelegramMessage.id == message_id).first()
                if message and not message.media_downloaded:
                    message.download_progress = 0
                    message.downloaded_size = 0
                    message.download_speed = 0
                    message.estimated_time_remaining = 0
                    message.download_started_at = None
                    message.media_download_error = "下载已取消"
                db.commit()
            except Exception as e:
                logger.error(f"取消下载时数据库更新失败 (消息 {message_id}): {str(e)}")
                db.rollback()
    
    logger.info(f"批量下载任务已取消: {batch_id}, 取消了 {cancelled_count} 个下载")
    
    return {
        "status": "cancelled",
        "message": f"批量下载任务已取消，取消了 {cancelled_count} 个下载",
        "batch_id": batch_id,
        "cancelled_downloads": cancelled_count,
        "total_files": len(message_ids)
    }

async def batch_download_manager(batch_id: str):
    """
    批量下载管理器，负责控制并发下载
    
    Args:
        batch_id: 批量下载ID
    """
    global batch_downloads, batch_semaphores
    
    if batch_id not in batch_downloads:
        logger.error(f"批量下载管理器: 任务 {batch_id} 不存在")
        return
    
    batch_info = batch_downloads[batch_id]
    message_ids = batch_info["message_ids"]
    force = batch_info.get("force", False)
    semaphore = batch_semaphores.get(batch_id)
    
    if not semaphore:
        logger.error(f"批量下载管理器: 任务 {batch_id} 没有对应的信号量")
        return
    
    logger.info(f"批量下载管理器启动: {batch_id}, 并发数: {batch_info['max_concurrent']}")
    
    # 创建下载任务
    download_tasks = []
    for message_id in message_ids:
        if batch_info["status"] == "cancelled":
            logger.info(f"批量下载任务已取消，停止创建新的下载任务: {batch_id}")
            break
        
        # 使用信号量控制并发
        task = asyncio.create_task(batch_download_single_file(batch_id, message_id, force, semaphore))
        download_tasks.append(task)
    
    # 等待所有下载任务完成
    if download_tasks:
        try:
            await asyncio.gather(*download_tasks, return_exceptions=True)
        except Exception as e:
            logger.error(f"批量下载管理器异常: {batch_id}, 错误: {str(e)}")
    
    # 清理资源
    if batch_id in batch_semaphores:
        del batch_semaphores[batch_id]
    
    # 更新批量任务状态
    if batch_id in batch_downloads:
        if batch_downloads[batch_id]["status"] != "cancelled":
            batch_downloads[batch_id]["status"] = "completed"
    
    logger.info(f"批量下载管理器完成: {batch_id}")

async def batch_download_single_file(batch_id: str, message_id: int, force: bool, semaphore: asyncio.Semaphore):
    """
    批量下载中的单个文件下载任务
    
    Args:
        batch_id: 批量下载ID
        message_id: 消息ID
        force: 是否强制重新下载
        semaphore: 并发控制信号量
    """
    # 获取信号量，控制并发数
    async with semaphore:
        # 检查批量任务是否已取消
        global batch_downloads
        if batch_id in batch_downloads and batch_downloads[batch_id]["status"] == "cancelled":
            logger.info(f"批量下载已取消，跳过文件下载: batch={batch_id}, message={message_id}")
            return
        
        # 检查单个文件是否已经在下载中
        global downloading_messages
        if message_id in downloading_messages:
            logger.info(f"文件已在下载队列中，跳过: message={message_id}")
            return
        
        try:
            # 添加到下载中的集合
            downloading_messages.add(message_id)
            
            # 将下载任务添加到队列
            await download_queue.put((message_id, force))
            logger.info(f"批量下载文件已添加到队列: batch={batch_id}, message={message_id}")
            
        except Exception as e:
            logger.error(f"批量下载单个文件时发生异常: batch={batch_id}, message={message_id}, 错误: {str(e)}")
            # 确保从下载集合中移除
            downloading_messages.discard(message_id)

@router.post("/start-download/{message_id}")
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
                "download_url": build_media_url(message.media_path)
            }
        else:
            # 文件记录存在但实际文件丢失，重置下载状态
            try:
                message.media_downloaded = False
                message.media_path = None
                db.commit()
            except Exception as commit_error:
                logger.warning(f"重置下载状态时数据库提交失败: {str(commit_error)}")
                db.rollback()
                # 即使提交失败，也继续执行下载任务
    
    # 检查是否已经在下载队列中
    global downloading_messages
    if message_id in downloading_messages:
        return {
            "status": "download_in_progress",
            "message": "该文件正在下载中，请稍候",
            "message_id": message_id,
            "media_type": message.media_type
        }
    
    # 启动下载工作进程（如果还没启动）
    global download_worker_started
    if not download_worker_started:
        background_tasks.add_task(start_download_worker)
        download_worker_started = True
    
    # 添加到下载中的集合
    downloading_messages.add(message_id)
    
    # 将下载任务添加到队列
    await download_queue.put((message_id, force))
    
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
                "download_url": build_media_url(message.media_path),
                "progress": 100,
                "downloaded_size": message.media_size or 0,
                "total_size": message.media_size or 0,
                "download_speed": 0,
                "estimated_time_remaining": 0
            }
        else:
            return {
                "status": "file_missing",
                "message": "文件记录存在但实际文件丢失"
            }
    
    if message.media_download_error:
        if message.media_download_error == "下载已取消":
            return {
                "status": "cancelled",
                "message": "下载已取消",
                "error": message.media_download_error
            }
        else:
            return {
                "status": "download_failed",
                "message": "下载失败",
                "error": message.media_download_error
            }
    
    # 检查是否正在下载中
    global downloading_messages
    if message_id in downloading_messages:
        return {
            "status": "downloading",
            "message": "文件正在下载中",
            "progress": message.download_progress or 0,
            "downloaded_size": message.downloaded_size or 0,
            "total_size": message.media_size or 0,
            "download_speed": message.download_speed or 0,
            "estimated_time_remaining": message.estimated_time_remaining or 0,
            "download_started_at": message.download_started_at.isoformat() if message.download_started_at else None,
            "media_type": message.media_type,
            "file_id": message.media_file_id
        }
    
    return {
        "status": "not_downloaded",
        "message": "文件未下载",
        "media_type": message.media_type,
        "file_id": message.media_file_id
    }

@router.post("/cancel-download/{message_id}")
async def cancel_download(
    message_id: int,
    db: Session = Depends(get_db)
):
    """
    取消正在进行的媒体文件下载
    
    Args:
        message_id: 消息ID
        db: 数据库会话
    
    Returns:
        取消下载结果
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
    
    # 检查是否正在下载中
    global downloading_messages, cancelled_downloads
    if message_id not in downloading_messages:
        return {
            "status": "not_downloading",
            "message": "该文件当前未在下载中"
        }
    
    # 标记为已取消
    cancelled_downloads.add(message_id)
    
    try:
        # 重置下载状态
        message.download_progress = 0
        message.downloaded_size = 0
        message.download_speed = 0
        message.estimated_time_remaining = 0
        message.download_started_at = None
        message.media_download_error = "下载已取消"
        db.commit()
        
        logger.info(f"下载取消成功: 消息 {message_id}")
        
        return {
            "status": "cancelled",
            "message": "下载已取消",
            "message_id": message_id
        }
        
    except Exception as e:
        logger.error(f"取消下载时数据库更新失败: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"取消下载失败: {str(e)}"
        )

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

@router.get("/download/{message_id}")
async def serve_media_file(
    message_id: int,
    db: Session = Depends(get_db)
):
    """
    提供媒体文件下载服务
    
    Args:
        message_id: 消息ID
        db: 数据库会话
    
    Returns:
        媒体文件响应
    """
    message = db.query(TelegramMessage).filter(TelegramMessage.id == message_id).first()
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="消息不存在"
        )
    
    if not message.media_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该消息不包含媒体文件"
        )
    
    if not message.media_downloaded or not message.media_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="媒体文件未下载"
        )
    
    if not os.path.exists(message.media_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="媒体文件不存在"
        )
    
    try:
        # 获取MIME类型
        mime_type, _ = mimetypes.guess_type(message.media_path)
        if not mime_type:
            # 根据媒体类型设置默认MIME类型
            mime_type_mapping = {
                'photo': 'image/jpeg',
                'video': 'video/mp4',
                'document': 'application/octet-stream',
                'audio': 'audio/mpeg',
                'voice': 'audio/ogg'
            }
            mime_type = mime_type_mapping.get(message.media_type, 'application/octet-stream')
        
        # 设置文件名
        filename = message.media_filename or f"media_{message_id}"
        
        return FileResponse(
            path=message.media_path,
            media_type=mime_type,
            filename=filename
        )
    except Exception as e:
        logger.error(f"提供媒体文件失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"提供媒体文件失败: {str(e)}"
        )

async def start_download_worker():
    """启动下载工作进程，串行处理下载队列"""
    logger.info("下载工作进程已启动")
    
    while True:
        try:
            # 从队列获取下载任务
            message_id, force = await download_queue.get()
            logger.info(f"处理下载任务: 消息 {message_id}")
            
            try:
                # 检查是否已被取消
                if message_id in cancelled_downloads:
                    logger.info(f"下载任务已被取消，跳过执行: 消息 {message_id}")
                    cancelled_downloads.discard(message_id)
                else:
                    # 执行下载
                    await download_media_background(message_id, force)
            finally:
                # 无论成功失败，都从下载中集合移除
                downloading_messages.discard(message_id)
                # 清理取消标记
                cancelled_downloads.discard(message_id)
            
            # 标记任务完成
            download_queue.task_done()
            
        except Exception as e:
            logger.error(f"下载工作进程异常: {str(e)}")
            # 继续处理下一个任务
            continue

async def download_media_background(message_id: int, force: bool = False):
    """
    后台下载媒体文件任务（串行执行，无并发冲突）
    
    Args:
        message_id: 消息ID
        force: 是否强制重新下载（当前未使用，因为force检查在队列前完成）
    """
    # Note: force parameter is currently unused as force checking is done before queueing
    _ = force  # Suppress unused parameter warning
    from ..database import SessionLocal
    
    # 使用短连接获取消息信息
    db = SessionLocal()
    try:
        message = db.query(TelegramMessage).filter(TelegramMessage.id == message_id).first()
        if not message:
            logger.error(f"下载任务: 消息 {message_id} 不存在")
            return
        
        if not message.media_file_id:
            logger.error(f"下载任务: 消息 {message_id} 没有文件ID")
            return
        
        # 获取必要的信息后立即关闭连接
        media_file_id = message.media_file_id
        media_type = message.media_type
        media_filename = message.media_filename
        group_id = message.group_id
        message_id_telegram = message.message_id
        group_telegram_id = message.group.telegram_id if message.group else None
        
    finally:
        db.close()
    
    # 清除之前的错误信息（单独的数据库操作）
    db = SessionLocal()
    try:
        message = db.query(TelegramMessage).filter(TelegramMessage.id == message_id).first()
        if message:
            message.media_download_error = None
            db.commit()
    except Exception as e:
        logger.warning(f"清除错误信息失败: {e}")
        db.rollback()
    finally:
        db.close()
        
    # 执行实际下载（不持有数据库连接）
    file_path = None
    download_error = None
    download_success = False
    
    try:
        # 构建文件保存路径
        media_dir = f"./media/{media_type}s"
        os.makedirs(media_dir, exist_ok=True)
        
        # 生成唯一文件名
        file_extension = ""
        if media_filename:
            file_extension = os.path.splitext(media_filename)[1]
        elif media_type == "photo":
            file_extension = ".jpg"
        elif media_type == "video":
            file_extension = ".mp4"
        elif media_type == "audio":
            file_extension = ".mp3"
        elif media_type == "voice":
            file_extension = ".ogg"
        elif media_type == "document":
            file_extension = ".bin"
        
        unique_filename = f"{group_id}_{message_id_telegram}_{uuid.uuid4().hex[:8]}{file_extension}"
        file_path = os.path.join(media_dir, unique_filename)
        
        # 下载文件
        from ..services.media_downloader import get_media_downloader
        import time
        
        # 创建进度回调函数
        last_update_time = time.time()
        last_downloaded_size = 0
        
        def progress_callback(current_bytes, total_bytes, progress_percent):
            nonlocal last_update_time, last_downloaded_size
            
            # 检查是否已被取消
            if message_id in cancelled_downloads:
                logger.info(f"下载已被取消，停止进度更新: 消息 {message_id}")
                # 使用特定的异常类型而不是通用Exception，便于上层区分
                class DownloadCancelledException(Exception):
                    pass
                raise DownloadCancelledException("下载已取消")
            
            try:
                current_time = time.time()
                time_diff = current_time - last_update_time
                
                # 每秒最多更新一次数据库
                if time_diff >= 1.0:
                    # 计算下载速度
                    size_diff = current_bytes - last_downloaded_size
                    download_speed = size_diff / time_diff if time_diff > 0 else 0
                    
                    # 计算预计剩余时间
                    remaining_bytes = total_bytes - current_bytes
                    estimated_time = remaining_bytes / download_speed if download_speed > 0 else 0
                    
                    # 更新数据库
                    db_update = SessionLocal()
                    try:
                        msg = db_update.query(TelegramMessage).filter(TelegramMessage.id == message_id).first()
                        if msg:
                            msg.download_progress = progress_percent
                            msg.downloaded_size = current_bytes
                            msg.download_speed = int(download_speed)
                            msg.estimated_time_remaining = int(estimated_time)
                            if not msg.download_started_at:
                                from datetime import datetime, timezone
                                msg.download_started_at = datetime.now(timezone.utc)
                            db_update.commit()
                    except Exception as e:
                        logger.error(f"更新下载进度失败: {e}")
                        db_update.rollback()
                    finally:
                        db_update.close()
                    
                    last_update_time = current_time
                    last_downloaded_size = current_bytes
                    
                    logger.info(f"下载进度 {message_id}: {progress_percent}% ({current_bytes}/{total_bytes} bytes, {download_speed:.0f} B/s)")
                    
            except Exception as e:
                logger.error(f"进度回调执行失败: {e}")
        
        try:
            downloader = await get_media_downloader()
            
            download_success = await downloader.download_file(
                file_id=media_file_id,
                file_path=file_path,
                chat_id=group_telegram_id,
                message_id=message_id_telegram,
                progress_callback=progress_callback
            )
            
            if download_success:
                logger.info(f"媒体文件下载成功: {file_path}")
            else:
                download_error = "Telegram API下载失败"
                logger.error(f"媒体文件下载失败: 消息 {message_id}")
                
        except Exception as download_err:
            download_error = f"下载器错误: {str(download_err)}"
            logger.error(f"媒体下载器异常: {download_error}")
            
            # 如果是认证错误，提供更详细的信息
            if "EOF when reading a line" in str(download_err) or "AuthKeyUnregisteredError" in str(download_err):
                download_error = "Telegram认证失败，请检查API配置和session状态"
                logger.error("Telegram认证失败，可能需要重新登录或检查API配置")
            # 判断是否是取消下载导致的异常
            elif "下载已取消" in str(download_err):
                download_error = "下载已被用户取消"
                logger.info(f"下载正常取消: {download_error}")
                # 删除可能创建的部分文件
                if file_path and os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        logger.info(f"已删除取消下载的不完整文件: {file_path}")
                    except Exception as del_err:
                        logger.warning(f"删除不完整文件失败: {del_err}")
            
    except Exception as e:
        download_error = f"下载过程中发生错误: {str(e)}"
        logger.error(f"下载任务异常: {download_error}")
    
    # 最后更新数据库状态（单独的短连接）
    db = SessionLocal()
    try:
        message = db.query(TelegramMessage).filter(TelegramMessage.id == message_id).first()
        if message:
            if download_success and file_path:
                message.media_downloaded = True
                message.media_path = file_path
                message.media_download_error = None
                
                # 设置完成状态的进度信息
                message.download_progress = 100
                message.download_speed = 0
                message.estimated_time_remaining = 0
                
                # 获取实际文件大小
                if os.path.exists(file_path):
                    actual_size = os.path.getsize(file_path)
                    message.media_size = actual_size
                    message.downloaded_size = actual_size
            else:
                message.media_download_error = download_error
                # 重置进度信息
                message.download_progress = 0
                message.downloaded_size = 0
                message.download_speed = 0
                message.estimated_time_remaining = 0
            
            db.commit()
            logger.info(f"数据库状态更新完成: 消息 {message_id}")
            
    except Exception as e:
        logger.error(f"更新数据库状态失败: {str(e)}")
        db.rollback()
    finally:
        db.close()