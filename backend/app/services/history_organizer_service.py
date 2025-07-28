"""
历史文件整理服务
处理已下载文件的重新整理、批量移动、重命名等操作
"""
import os
import shutil
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime
from sqlalchemy.orm import Session

from ..models.rule import DownloadRecord, DownloadTask
from ..models.telegram import TelegramGroup
from .file_organizer_service import FileOrganizerService

logger = logging.getLogger(__name__)


class HistoryOrganizerService:
    """历史文件整理服务"""
    
    def __init__(self):
        self.file_organizer = FileOrganizerService()
    
    def reorganize_single_file(self, 
                              record_id: int, 
                              db: Session,
                              target_path: Optional[str] = None,
                              new_filename: Optional[str] = None) -> Tuple[bool, str, Optional[str]]:
        """
        重新整理单个历史文件
        
        Args:
            record_id: 下载记录ID
            db: 数据库会话
            target_path: 目标路径（可选，如果不提供则根据任务配置自动生成）
            new_filename: 新文件名（可选）
            
        Returns:
            (是否成功, 新文件路径, 错误信息)
        """
        try:
            # 获取下载记录和相关信息
            record = db.query(DownloadRecord).filter(DownloadRecord.id == record_id).first()
            if not record:
                return False, "", "下载记录不存在"
            
            task = db.query(DownloadTask).filter(DownloadTask.id == record.task_id).first()
            if not task:
                return False, "", "关联的下载任务不存在"
            
            group = db.query(TelegramGroup).filter(TelegramGroup.id == task.group_id).first()
            
            # 检查源文件是否存在
            source_path = record.local_file_path
            if not os.path.exists(source_path):
                return False, "", f"源文件不存在: {source_path}"
            
            # 构建模拟的消息对象和任务数据
            mock_message = self._create_mock_message_from_record(record)
            task_data = self._create_task_data_from_task(task, group)
            
            # 如果指定了目标路径，直接使用；否则使用文件组织服务生成
            if target_path:
                # 使用指定的目标路径
                if new_filename:
                    organized_path = os.path.join(target_path, new_filename)
                else:
                    organized_path = os.path.join(target_path, os.path.basename(source_path))
            else:
                # 使用文件组织服务自动生成路径
                original_filename = new_filename if new_filename else os.path.basename(source_path)
                organized_path = self.file_organizer.generate_organized_path(
                    mock_message, task_data, original_filename
                )
            
            # 如果文件已经在目标位置，不需要移动
            if os.path.abspath(source_path) == os.path.abspath(organized_path):
                logger.info(f"文件已在目标位置: {organized_path}")
                return True, organized_path, None
            
            # 检查目标路径是否已存在文件
            if os.path.exists(organized_path):
                # 检查是否为重复文件
                duplicate_path = self.file_organizer.check_duplicate_by_hash(source_path, os.path.dirname(organized_path))
                if duplicate_path and duplicate_path == organized_path:
                    # 是重复文件，删除源文件
                    logger.info(f"发现重复文件，删除源文件: {source_path}")
                    os.remove(source_path)
                    
                    # 更新数据库记录
                    record.local_file_path = organized_path
                    db.commit()
                    
                    return True, organized_path, "文件重复，已删除源文件并使用现有文件"
                else:
                    # 文件不重复但路径冲突，生成新名称
                    base_name, ext = os.path.splitext(organized_path)
                    counter = 1
                    while os.path.exists(organized_path):
                        organized_path = f"{base_name}_{counter}{ext}"
                        counter += 1
            
            # 创建目标目录
            os.makedirs(os.path.dirname(organized_path), exist_ok=True)
            
            # 移动文件
            shutil.move(source_path, organized_path)
            logger.info(f"文件已重新整理: {source_path} -> {organized_path}")
            
            # 更新数据库记录
            record.local_file_path = organized_path
            if new_filename:
                record.file_name = new_filename
            db.commit()
            
            return True, organized_path, None
            
        except Exception as e:
            db.rollback()
            error_msg = f"重新整理文件失败: {str(e)}"
            logger.error(error_msg)
            return False, source_path if 'source_path' in locals() else "", error_msg
    
    def batch_reorganize_files(self, 
                              record_ids: List[int], 
                              db: Session,
                              target_base_path: Optional[str] = None) -> Dict[str, Any]:
        """
        批量重新整理文件
        
        Args:
            record_ids: 下载记录ID列表
            db: 数据库会话
            target_base_path: 目标基础路径（可选）
            
        Returns:
            整理结果统计
        """
        results = {
            "total": len(record_ids),
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "errors": [],
            "organized_files": []
        }
        
        try:
            for record_id in record_ids:
                try:
                    success, new_path, error_msg = self.reorganize_single_file(
                        record_id=record_id,
                        db=db,
                        target_path=target_base_path
                    )
                    
                    if success:
                        results["success"] += 1
                        results["organized_files"].append({
                            "record_id": record_id,
                            "new_path": new_path
                        })
                        if error_msg:  # 可能是跳过的重复文件
                            results["skipped"] += 1
                    else:
                        results["failed"] += 1
                        results["errors"].append({
                            "record_id": record_id,
                            "error": error_msg
                        })
                        
                except Exception as e:
                    results["failed"] += 1
                    results["errors"].append({
                        "record_id": record_id,
                        "error": str(e)
                    })
            
            logger.info(f"批量整理完成: 成功{results['success']}, 失败{results['failed']}, 跳过{results['skipped']}")
            return results
            
        except Exception as e:
            error_msg = f"批量整理失败: {str(e)}"
            logger.error(error_msg)
            results["errors"].append({"general_error": error_msg})
            return results
    
    def batch_move_files(self, 
                        record_ids: List[int], 
                        target_directory: str, 
                        db: Session,
                        preserve_structure: bool = False) -> Dict[str, Any]:
        """
        批量移动文件到指定目录
        
        Args:
            record_ids: 下载记录ID列表
            target_directory: 目标目录
            db: 数据库会话
            preserve_structure: 是否保持原有目录结构
            
        Returns:
            移动结果统计
        """
        results = {
            "total": len(record_ids),
            "success": 0,
            "failed": 0,
            "errors": [],
            "moved_files": []
        }
        
        try:
            # 确保目标目录存在
            os.makedirs(target_directory, exist_ok=True)
            
            for record_id in record_ids:
                try:
                    record = db.query(DownloadRecord).filter(DownloadRecord.id == record_id).first()
                    if not record:
                        results["failed"] += 1
                        results["errors"].append({
                            "record_id": record_id,
                            "error": "下载记录不存在"
                        })
                        continue
                    
                    source_path = record.local_file_path
                    if not os.path.exists(source_path):
                        results["failed"] += 1
                        results["errors"].append({
                            "record_id": record_id,
                            "error": f"源文件不存在: {source_path}"
                        })
                        continue
                    
                    # 确定目标文件路径
                    if preserve_structure:
                        # 保持相对目录结构
                        relative_path = os.path.relpath(source_path, start=os.path.commonpath([source_path]))
                        target_path = os.path.join(target_directory, relative_path)
                    else:
                        # 直接移动到目标目录
                        filename = os.path.basename(source_path)
                        target_path = os.path.join(target_directory, filename)
                    
                    # 处理文件名冲突
                    if os.path.exists(target_path):
                        base_name, ext = os.path.splitext(target_path)
                        counter = 1
                        while os.path.exists(target_path):
                            target_path = f"{base_name}_{counter}{ext}"
                            counter += 1
                    
                    # 创建目标目录
                    os.makedirs(os.path.dirname(target_path), exist_ok=True)
                    
                    # 移动文件
                    shutil.move(source_path, target_path)
                    
                    # 更新数据库记录
                    record.local_file_path = target_path
                    db.commit()
                    
                    results["success"] += 1
                    results["moved_files"].append({
                        "record_id": record_id,
                        "old_path": source_path,
                        "new_path": target_path
                    })
                    
                    logger.info(f"文件已移动: {source_path} -> {target_path}")
                    
                except Exception as e:
                    results["failed"] += 1
                    results["errors"].append({
                        "record_id": record_id,
                        "error": str(e)
                    })
                    logger.error(f"移动文件失败 (记录ID: {record_id}): {e}")
            
            logger.info(f"批量移动完成: 成功{results['success']}, 失败{results['failed']}")
            return results
            
        except Exception as e:
            error_msg = f"批量移动失败: {str(e)}"
            logger.error(error_msg)
            results["errors"].append({"general_error": error_msg})
            return results
    
    def rename_file(self, 
                   record_id: int, 
                   new_filename: str, 
                   db: Session) -> Tuple[bool, str, Optional[str]]:
        """
        重命名单个文件
        
        Args:
            record_id: 下载记录ID
            new_filename: 新文件名
            db: 数据库会话
            
        Returns:
            (是否成功, 新文件路径, 错误信息)
        """
        try:
            record = db.query(DownloadRecord).filter(DownloadRecord.id == record_id).first()
            if not record:
                return False, "", "下载记录不存在"
            
            source_path = record.local_file_path
            if not os.path.exists(source_path):
                return False, "", f"源文件不存在: {source_path}"
            
            # 构建新的文件路径
            directory = os.path.dirname(source_path)
            new_path = os.path.join(directory, new_filename)
            
            # 检查新文件名是否已存在
            if os.path.exists(new_path):
                return False, source_path, f"目标文件名已存在: {new_filename}"
            
            # 重命名文件
            os.rename(source_path, new_path)
            
            # 更新数据库记录
            record.local_file_path = new_path
            record.file_name = new_filename
            db.commit()
            
            logger.info(f"文件已重命名: {source_path} -> {new_path}")
            return True, new_path, None
            
        except Exception as e:
            db.rollback()
            error_msg = f"重命名文件失败: {str(e)}"
            logger.error(error_msg)
            return False, source_path if 'source_path' in locals() else "", error_msg
    
    def cleanup_missing_files(self, db: Session) -> Dict[str, Any]:
        """
        清理数据库中指向不存在文件的记录
        
        Args:
            db: 数据库会话
            
        Returns:
            清理结果统计
        """
        results = {
            "total_checked": 0,
            "missing_files": 0,
            "cleaned_records": []
        }
        
        try:
            # 获取所有下载记录
            records = db.query(DownloadRecord).all()
            results["total_checked"] = len(records)
            
            for record in records:
                if not os.path.exists(record.local_file_path):
                    results["missing_files"] += 1
                    results["cleaned_records"].append({
                        "record_id": record.id,
                        "file_path": record.local_file_path,
                        "file_name": record.file_name
                    })
                    
                    # 可以选择删除记录或标记为缺失
                    # 这里只是标记，不直接删除
                    record.download_status = "missing"
                    record.error_message = "文件不存在于本地路径"
            
            db.commit()
            logger.info(f"清理完成: 检查了{results['total_checked']}个记录，发现{results['missing_files']}个缺失文件")
            return results
            
        except Exception as e:
            db.rollback()
            error_msg = f"清理缺失文件失败: {str(e)}"
            logger.error(error_msg)
            results["error"] = error_msg
            return results
    
    def _create_mock_message_from_record(self, record: DownloadRecord) -> object:
        """从下载记录创建模拟的消息对象"""
        class MockMessage:
            def __init__(self, record):
                self.id = record.id
                self.message_id = record.message_id
                self.date = record.message_date or datetime.now()
                self.text = record.message_text
                self.sender_name = record.sender_name
                self.media_type = record.file_type
                self.media_filename = record.file_name
        
        return MockMessage(record)
    
    def _create_task_data_from_task(self, task: DownloadTask, group: Optional[TelegramGroup]) -> Dict[str, Any]:
        """从任务对象创建任务数据字典"""
        return {
            'task_id': task.id,
            'task_name': task.name,
            'download_path': task.download_path,
            'use_jellyfin_structure': getattr(task, 'use_jellyfin_structure', False),
            'include_metadata': getattr(task, 'include_metadata', False),
            'download_thumbnails': getattr(task, 'download_thumbnails', False),
            'use_series_structure': getattr(task, 'use_series_structure', False),
            'organize_by_date': getattr(task, 'organize_by_date', True),
            'max_filename_length': getattr(task, 'max_filename_length', 150),
            'thumbnail_size': getattr(task, 'thumbnail_size', '400x300'),
            'poster_size': getattr(task, 'poster_size', '600x900'),
            'fanart_size': getattr(task, 'fanart_size', '1920x1080'),
            'group_id': task.group_id,
            'group_name': group.title if group else 'Unknown_Group',
            'subscription_name': task.name,  # 添加订阅名用于Jellyfin格式
            'group_telegram_id': getattr(group, 'telegram_id', None) if group else None
        }
    
    def get_organization_stats(self) -> Dict[str, Any]:
        """获取整理服务的统计信息"""
        return self.file_organizer.get_organization_stats()
    
    def clear_cache(self):
        """清理缓存"""
        self.file_organizer.clear_cache()


# 创建全局历史整理服务实例
history_organizer_service = HistoryOrganizerService()