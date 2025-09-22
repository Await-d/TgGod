"""真实数据迁移系统

提供全面的数据迁移和导入功能，支持从各种数据源导入真实数据，
包括Telegram备份、JSON导出、CSV文件等格式。绝不依赖Mock数据。

Features:
    - 多格式数据导入支持
    - 数据完整性验证和修复
    - 增量迁移和全量迁移
    - 迁移进度跟踪和回滚
    - 自动数据清理和优化
    - 详细的迁移报告

Author: TgGod Team
Version: 1.0.0
"""

import asyncio
import json
import csv
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, IO
from pathlib import Path
from dataclasses import dataclass
import hashlib
import shutil

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, text
from sqlalchemy.exc import IntegrityError

from ..database import SessionLocal, Base, engine
from ..models.telegram import TelegramGroup, TelegramMessage
from ..models.rule import FilterRule
from ..models.rule import DownloadTask
from ..core.error_handler import ErrorHandler
from ..core.batch_logging import HighPerformanceLogger

logger = logging.getLogger(__name__)


class MigrationError(Exception):
    """数据迁移过程中的错误"""
    pass


@dataclass
class MigrationConfig:
    """迁移配置"""
    batch_size: int = 100
    max_retries: int = 3
    backup_before_migration: bool = True
    validate_data_integrity: bool = True
    cleanup_temp_files: bool = True
    migration_timeout: int = 3600  # 1小时
    allow_duplicate_handling: bool = True
    preserve_timestamps: bool = True


@dataclass
class MigrationProgress:
    """迁移进度信息"""
    total_items: int = 0
    processed_items: int = 0
    successful_items: int = 0
    failed_items: int = 0
    skipped_items: int = 0
    current_phase: str = "preparing"
    start_time: datetime = None
    estimated_completion: datetime = None
    
    @property
    def progress_percentage(self) -> float:
        if self.total_items == 0:
            return 0.0
        return (self.processed_items / self.total_items) * 100
    
    @property
    def success_rate(self) -> float:
        if self.processed_items == 0:
            return 0.0
        return (self.successful_items / self.processed_items) * 100


class RealDataMigrator:
    """真实数据迁移器
    
    提供全面的数据迁移功能，支持多种数据源和格式，
    确保数据的完整性和一致性。
    """
    
    def __init__(self, config: MigrationConfig = None, db: Session = None):
        """初始化迁移器
        
        Args:
            config: 迁移配置
            db: 数据库会话
        """
        self.config = config or MigrationConfig()
        self.db = db or SessionLocal()
        self.error_handler = ErrorHandler()
        self.batch_logger = HighPerformanceLogger("data_migration")
        self.progress = MigrationProgress()
        self.migration_id = self._generate_migration_id()
        self.temp_dir = Path(f"temp/migration_{self.migration_id}")
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
    def _generate_migration_id(self) -> str:
        """生成唯一的迁移ID"""
        return hashlib.md5(
            f"{datetime.now().isoformat()}_{id(self)}".encode()
        ).hexdigest()[:12]
    
    async def migrate_from_telegram_export(self, export_file_path: str) -> Dict[str, Any]:
        """从Telegram导出文件迁移数据
        
        支持Telegram Desktop的JSON导出格式
        
        Args:
            export_file_path: 导出文件路径
            
        Returns:
            迁移结果报告
        """
        migration_report = {
            "migration_id": self.migration_id,
            "source_type": "telegram_export",
            "source_file": export_file_path,
            "started_at": datetime.now(),
            "phases": [],
            "success": False
        }
        
        try:
            self.batch_logger.info(f"开始从Telegram导出文件迁移: {export_file_path}")
            self.progress.start_time = datetime.now()
            
            # 阶段1: 验证和解析导出文件
            await self._validate_telegram_export_file(export_file_path, migration_report)
            
            # 阶段2: 备份现有数据
            if self.config.backup_before_migration:
                await self._backup_existing_data(migration_report)
            
            # 阶段3: 解析导出数据
            export_data = await self._parse_telegram_export(export_file_path, migration_report)
            
            # 阶段4: 迁移群组数据
            await self._migrate_groups_from_export(export_data, migration_report)
            
            # 阶段5: 迁移消息数据
            await self._migrate_messages_from_export(export_data, migration_report)
            
            # 阶段6: 数据完整性验证
            if self.config.validate_data_integrity:
                await self._validate_migrated_data(migration_report)
            
            # 阶段7: 清理和优化
            await self._finalize_migration(migration_report)
            
            migration_report["success"] = True
            migration_report["completed_at"] = datetime.now()
            
        except Exception as e:
            migration_report["error"] = str(e)
            migration_report["failed_at"] = datetime.now()
            await self._handle_migration_failure(migration_report, e)
        
        finally:
            if self.config.cleanup_temp_files:
                await self._cleanup_temp_files()
        
        return migration_report
    
    async def _validate_telegram_export_file(self, file_path: str, report: Dict[str, Any]):
        """验证Telegram导出文件"""
        phase_name = "file_validation"
        self.progress.current_phase = phase_name
        
        try:
            export_path = Path(file_path)
            if not export_path.exists():
                raise MigrationError(f"导出文件不存在: {file_path}")
            
            # 检查文件格式
            if export_path.suffix.lower() not in ['.json', '.zip']:
                raise MigrationError(f"不支持的文件格式: {export_path.suffix}")
            
            # 检查文件大小
            file_size = export_path.stat().st_size
            if file_size == 0:
                raise MigrationError("导出文件为空")
            
            # 预估处理时间
            estimated_processing_time = file_size / (1024 * 1024) * 2  # 2分钟/MB
            self.progress.estimated_completion = (
                datetime.now() + timedelta(seconds=estimated_processing_time)
            )
            
            report["phases"].append({
                "phase": phase_name,
                "status": "completed",
                "details": {
                    "file_size": file_size,
                    "estimated_time": estimated_processing_time
                }
            })
            
        except Exception as e:
            report["phases"].append({
                "phase": phase_name,
                "status": "failed",
                "error": str(e)
            })
            raise
    
    async def _backup_existing_data(self, report: Dict[str, Any]):
        """备份现有数据"""
        phase_name = "data_backup"
        self.progress.current_phase = phase_name
        
        try:
            backup_dir = Path(f"backups/migration_{self.migration_id}")
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # 备份群组数据
            groups = self.db.query(TelegramGroup).all()
            groups_backup = [
                {
                    "id": g.id,
                    "telegram_id": g.telegram_id,
                    "title": g.title,
                    "username": g.username,
                    "description": g.description,
                    "member_count": g.member_count,
                    "is_active": g.is_active,
                    "created_at": g.created_at.isoformat() if g.created_at else None,
                    "updated_at": g.updated_at.isoformat() if g.updated_at else None
                }
                for g in groups
            ]
            
            with open(backup_dir / "groups_backup.json", 'w', encoding='utf-8') as f:
                json.dump(groups_backup, f, ensure_ascii=False, indent=2)
            
            # 备份消息数据（限制数量避免文件过大）
            recent_messages = self.db.query(TelegramMessage).order_by(
                TelegramMessage.created_at.desc()
            ).limit(10000).all()
            
            messages_backup = [
                {
                    "id": m.id,
                    "group_id": m.group_id,
                    "message_id": m.message_id,
                    "sender_username": m.sender_username,
                    "text": m.text,
                    "media_type": m.media_type,
                    "date": m.date.isoformat() if m.date else None,
                    "created_at": m.created_at.isoformat() if m.created_at else None
                }
                for m in recent_messages
            ]
            
            with open(backup_dir / "messages_backup.json", 'w', encoding='utf-8') as f:
                json.dump(messages_backup, f, ensure_ascii=False, indent=2)
            
            report["phases"].append({
                "phase": phase_name,
                "status": "completed",
                "details": {
                    "backup_directory": str(backup_dir),
                    "groups_backed_up": len(groups_backup),
                    "messages_backed_up": len(messages_backup)
                }
            })
            
        except Exception as e:
            report["phases"].append({
                "phase": phase_name,
                "status": "failed",
                "error": str(e)
            })
            raise
    
    async def _parse_telegram_export(self, file_path: str, report: Dict[str, Any]) -> Dict[str, Any]:
        """解析Telegram导出数据"""
        phase_name = "data_parsing"
        self.progress.current_phase = phase_name
        
        try:
            export_path = Path(file_path)
            
            if export_path.suffix.lower() == '.json':
                # 直接JSON文件
                with open(export_path, 'r', encoding='utf-8') as f:
                    export_data = json.load(f)
            elif export_path.suffix.lower() == '.zip':
                # 压缩包，需要解压
                import zipfile
                with zipfile.ZipFile(export_path, 'r') as zip_ref:
                    zip_ref.extractall(self.temp_dir)
                    
                # 查找JSON文件
                json_files = list(self.temp_dir.glob("*.json"))
                if not json_files:
                    raise MigrationError("压缩包中未找到JSON文件")
                
                with open(json_files[0], 'r', encoding='utf-8') as f:
                    export_data = json.load(f)
            else:
                raise MigrationError(f"不支持的文件格式: {export_path.suffix}")
            
            # 验证数据结构
            if not isinstance(export_data, dict):
                raise MigrationError("导出数据格式不正确")
            
            # 统计数据量
            chats = export_data.get('chats', {}).get('list', [])
            total_messages = sum(len(chat.get('messages', [])) for chat in chats)
            
            self.progress.total_items = len(chats) + total_messages
            
            report["phases"].append({
                "phase": phase_name,
                "status": "completed",
                "details": {
                    "total_chats": len(chats),
                    "total_messages": total_messages,
                    "data_structure_valid": True
                }
            })
            
            return export_data
            
        except Exception as e:
            report["phases"].append({
                "phase": phase_name,
                "status": "failed",
                "error": str(e)
            })
            raise
    
    async def _migrate_groups_from_export(self, export_data: Dict[str, Any], report: Dict[str, Any]):
        """从导出数据迁移群组"""
        phase_name = "groups_migration"
        self.progress.current_phase = phase_name
        
        try:
            chats = export_data.get('chats', {}).get('list', [])
            migrated_groups = []
            failed_groups = []
            
            for chat_data in chats:
                try:
                    # 过滤掉私聊，只处理群组和频道
                    if chat_data.get('type') not in ['supergroup', 'group', 'channel']:
                        self.progress.skipped_items += 1
                        continue
                    
                    telegram_id = chat_data.get('id')
                    if not telegram_id:
                        self.progress.failed_items += 1
                        continue
                    
                    # 检查是否已存在
                    existing_group = self.db.query(TelegramGroup).filter(
                        TelegramGroup.telegram_id == telegram_id
                    ).first()
                    
                    if existing_group:
                        # 更新现有群组
                        existing_group.title = chat_data.get('name', '')
                        existing_group.description = chat_data.get('about', '')
                        existing_group.member_count = chat_data.get('members_count', 0)
                        existing_group.updated_at = datetime.now()
                        group = existing_group
                    else:
                        # 创建新群组
                        group = TelegramGroup(
                            telegram_id=telegram_id,
                            title=chat_data.get('name', ''),
                            username=chat_data.get('username'),
                            description=chat_data.get('about'),
                            member_count=chat_data.get('members_count', 0),
                            is_active=True
                        )
                        self.db.add(group)
                    
                    self.db.commit()
                    migrated_groups.append({
                        "id": group.id,
                        "telegram_id": telegram_id,
                        "title": group.title,
                        "action": "updated" if existing_group else "created"
                    })
                    
                    self.progress.successful_items += 1
                    
                except Exception as e:
                    failed_groups.append({
                        "telegram_id": chat_data.get('id'),
                        "name": chat_data.get('name', 'Unknown'),
                        "error": str(e)
                    })
                    self.progress.failed_items += 1
                
                self.progress.processed_items += 1
            
            report["phases"].append({
                "phase": phase_name,
                "status": "completed",
                "details": {
                    "migrated_groups": migrated_groups,
                    "failed_groups": failed_groups,
                    "total_processed": len(chats),
                    "successful": len(migrated_groups),
                    "failed": len(failed_groups)
                }
            })
            
        except Exception as e:
            report["phases"].append({
                "phase": phase_name,
                "status": "failed",
                "error": str(e)
            })
            raise
    
    async def _migrate_messages_from_export(self, export_data: Dict[str, Any], report: Dict[str, Any]):
        """从导出数据迁移消息"""
        phase_name = "messages_migration"
        self.progress.current_phase = phase_name
        
        try:
            chats = export_data.get('chats', {}).get('list', [])
            migrated_messages = []
            failed_messages = []
            
            for chat_data in chats:
                chat_id = chat_data.get('id')
                if not chat_id:
                    continue
                
                # 找到对应的数据库群组
                db_group = self.db.query(TelegramGroup).filter(
                    TelegramGroup.telegram_id == chat_id
                ).first()
                
                if not db_group:
                    continue
                
                messages = chat_data.get('messages', [])
                batch_messages = []
                
                for msg_data in messages:
                    try:
                        message_id = msg_data.get('id')
                        if not message_id:
                            continue
                        
                        # 检查消息是否已存在
                        existing_message = self.db.query(TelegramMessage).filter(
                            and_(
                                TelegramMessage.group_id == db_group.id,
                                TelegramMessage.message_id == message_id
                            )
                        ).first()
                        
                        if existing_message and not self.config.allow_duplicate_handling:
                            self.progress.skipped_items += 1
                            continue
                        
                        # 解析消息数据
                        message = self._parse_message_data(msg_data, db_group.id)
                        
                        if existing_message:
                            # 更新现有消息
                            for key, value in message.items():
                                if hasattr(existing_message, key):
                                    setattr(existing_message, key, value)
                            existing_message.updated_at = datetime.now()
                        else:
                            # 创建新消息
                            new_message = TelegramMessage(**message)
                            batch_messages.append(new_message)
                        
                        self.progress.successful_items += 1
                        
                        # 批量提交
                        if len(batch_messages) >= self.config.batch_size:
                            self.db.add_all(batch_messages)
                            self.db.commit()
                            migrated_messages.extend([
                                {"group_id": db_group.id, "message_id": msg.message_id}
                                for msg in batch_messages
                            ])
                            batch_messages.clear()
                        
                    except Exception as e:
                        failed_messages.append({
                            "group_id": db_group.id,
                            "message_id": msg_data.get('id'),
                            "error": str(e)
                        })
                        self.progress.failed_items += 1
                    
                    self.progress.processed_items += 1
                
                # 提交剩余的消息
                if batch_messages:
                    self.db.add_all(batch_messages)
                    self.db.commit()
                    migrated_messages.extend([
                        {"group_id": db_group.id, "message_id": msg.message_id}
                        for msg in batch_messages
                    ])
            
            report["phases"].append({
                "phase": phase_name,
                "status": "completed",
                "details": {
                    "migrated_messages_count": len(migrated_messages),
                    "failed_messages_count": len(failed_messages),
                    "successful_rate": self.progress.success_rate
                }
            })
            
        except Exception as e:
            report["phases"].append({
                "phase": phase_name,
                "status": "failed",
                "error": str(e)
            })
            raise
    
    def _parse_message_data(self, msg_data: Dict[str, Any], group_id: int) -> Dict[str, Any]:
        """解析单条消息数据"""
        message = {
            "group_id": group_id,
            "message_id": msg_data.get('id'),
            "text": msg_data.get('text', ''),
            "date": self._parse_datetime(msg_data.get('date')),
            "sender_username": None,
            "sender_name": None,
            "media_type": None,
            "media_filename": None,
            "is_forwarded": False,
            "created_at": datetime.now()
        }
        
        # 解析发送者信息
        from_info = msg_data.get('from')
        if from_info:
            message["sender_username"] = from_info.get('username')
            message["sender_name"] = from_info.get('first_name', '') + ' ' + from_info.get('last_name', '')
            message["sender_id"] = from_info.get('id')
        
        # 解析媒体信息
        if 'photo' in msg_data:
            message["media_type"] = "photo"
            message["media_filename"] = msg_data.get('photo', '')
        elif 'video' in msg_data:
            message["media_type"] = "video"
            message["media_filename"] = msg_data.get('video', '')
        elif 'document' in msg_data:
            message["media_type"] = "document"
            message["media_filename"] = msg_data.get('document', '')
        elif 'audio' in msg_data:
            message["media_type"] = "audio"
            message["media_filename"] = msg_data.get('audio', '')
        
        # 解析转发信息
        if 'forwarded_from' in msg_data:
            message["is_forwarded"] = True
            message["forwarded_from"] = msg_data['forwarded_from'].get('name', '')
            message["forwarded_date"] = self._parse_datetime(msg_data.get('forwarded_date'))
        
        # 解析回复信息
        if 'reply_to_message_id' in msg_data:
            message["reply_to_message_id"] = msg_data['reply_to_message_id']
        
        # 解析编辑信息
        if 'edited' in msg_data:
            message["edit_date"] = self._parse_datetime(msg_data['edited'])
        
        return message
    
    def _parse_datetime(self, date_str: str) -> Optional[datetime]:
        """解析日期时间字符串"""
        if not date_str:
            return None
        
        try:
            # Telegram导出通常使用ISO格式
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            try:
                # 尝试其他常见格式
                return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                return None
    
    async def migrate_from_csv_file(self, csv_file_path: str, mapping_config: Dict[str, str]) -> Dict[str, Any]:
        """从CSV文件迁移数据
        
        Args:
            csv_file_path: CSV文件路径
            mapping_config: 字段映射配置
            
        Returns:
            迁移结果报告
        """
        migration_report = {
            "migration_id": self.migration_id,
            "source_type": "csv_file",
            "source_file": csv_file_path,
            "started_at": datetime.now(),
            "phases": [],
            "success": False
        }
        
        try:
            self.batch_logger.info(f"开始从CSV文件迁移: {csv_file_path}")
            
            # 读取CSV文件
            csv_data = await self._read_csv_file(csv_file_path, mapping_config, migration_report)
            
            # 处理CSV数据
            await self._process_csv_data(csv_data, mapping_config, migration_report)
            
            migration_report["success"] = True
            migration_report["completed_at"] = datetime.now()
            
        except Exception as e:
            migration_report["error"] = str(e)
            migration_report["failed_at"] = datetime.now()
            await self._handle_migration_failure(migration_report, e)
        
        return migration_report
    
    async def _read_csv_file(self, file_path: str, mapping_config: Dict[str, str], report: Dict[str, Any]) -> List[Dict[str, Any]]:
        """读取CSV文件"""
        phase_name = "csv_reading"
        
        try:
            csv_data = []
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    csv_data.append(row)
            
            self.progress.total_items = len(csv_data)
            
            report["phases"].append({
                "phase": phase_name,
                "status": "completed",
                "details": {
                    "rows_read": len(csv_data),
                    "columns": list(csv_data[0].keys()) if csv_data else []
                }
            })
            
            return csv_data
            
        except Exception as e:
            report["phases"].append({
                "phase": phase_name,
                "status": "failed",
                "error": str(e)
            })
            raise
    
    async def _process_csv_data(self, csv_data: List[Dict[str, Any]], mapping_config: Dict[str, str], report: Dict[str, Any]):
        """处理CSV数据"""
        phase_name = "csv_processing"
        
        try:
            processed_records = []
            failed_records = []
            
            for row in csv_data:
                try:
                    # 根据映射配置转换数据
                    converted_data = {}
                    for csv_field, db_field in mapping_config.items():
                        if csv_field in row:
                            converted_data[db_field] = row[csv_field]
                    
                    # 根据数据类型创建相应的数据库记录
                    if 'group_data' in converted_data:
                        record = self._create_group_from_csv(converted_data)
                    elif 'message_data' in converted_data:
                        record = self._create_message_from_csv(converted_data)
                    else:
                        # 默认处理逻辑
                        record = converted_data
                    
                    processed_records.append(record)
                    self.progress.successful_items += 1
                    
                except Exception as e:
                    failed_records.append({
                        "row_data": row,
                        "error": str(e)
                    })
                    self.progress.failed_items += 1
                
                self.progress.processed_items += 1
            
            # 批量插入数据库
            await self._batch_insert_records(processed_records)
            
            report["phases"].append({
                "phase": phase_name,
                "status": "completed",
                "details": {
                    "processed_records": len(processed_records),
                    "failed_records": len(failed_records),
                    "success_rate": self.progress.success_rate
                }
            })
            
        except Exception as e:
            report["phases"].append({
                "phase": phase_name,
                "status": "failed",
                "error": str(e)
            })
            raise
    
    async def _batch_insert_records(self, records: List[Any]):
        """批量插入记录"""
        batch_size = self.config.batch_size
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            self.db.add_all(batch)
            self.db.commit()
    
    async def _validate_migrated_data(self, report: Dict[str, Any]):
        """验证迁移的数据完整性"""
        phase_name = "data_validation"
        
        try:
            validation_results = {
                "groups_validation": await self._validate_groups_data(),
                "messages_validation": await self._validate_messages_data(),
                "relationships_validation": await self._validate_relationships(),
                "data_consistency": await self._check_data_consistency()
            }
            
            # 计算整体验证得分
            total_checks = sum(len(v) for v in validation_results.values())
            passed_checks = sum(
                sum(1 for check in v.values() if check.get("status") == "passed")
                for v in validation_results.values()
            )
            
            validation_score = (passed_checks / total_checks) * 100 if total_checks > 0 else 0
            
            report["phases"].append({
                "phase": phase_name,
                "status": "completed",
                "details": {
                    "validation_results": validation_results,
                    "validation_score": validation_score,
                    "data_integrity_ok": validation_score >= 95
                }
            })
            
        except Exception as e:
            report["phases"].append({
                "phase": phase_name,
                "status": "failed",
                "error": str(e)
            })
            raise
    
    async def _validate_groups_data(self) -> Dict[str, Any]:
        """验证群组数据"""
        validations = {}
        
        # 检查必填字段
        groups_with_missing_title = self.db.query(func.count(TelegramGroup.id)).filter(
            or_(TelegramGroup.title.is_(None), TelegramGroup.title == '')
        ).scalar()
        
        validations["required_fields"] = {
            "status": "passed" if groups_with_missing_title == 0 else "failed",
            "missing_title_count": groups_with_missing_title
        }
        
        # 检查重复数据
        duplicate_groups = self.db.query(func.count(TelegramGroup.telegram_id)).group_by(
            TelegramGroup.telegram_id
        ).having(func.count(TelegramGroup.telegram_id) > 1).all()
        
        validations["duplicates"] = {
            "status": "passed" if len(duplicate_groups) == 0 else "failed",
            "duplicate_count": len(duplicate_groups)
        }
        
        return validations
    
    async def _validate_messages_data(self) -> Dict[str, Any]:
        """验证消息数据"""
        validations = {}
        
        # 检查必填字段
        messages_with_missing_data = self.db.query(func.count(TelegramMessage.id)).filter(
            or_(
                TelegramMessage.message_id.is_(None),
                TelegramMessage.group_id.is_(None),
                TelegramMessage.date.is_(None)
            )
        ).scalar()
        
        validations["required_fields"] = {
            "status": "passed" if messages_with_missing_data == 0 else "failed",
            "missing_data_count": messages_with_missing_data
        }
        
        # 检查外键完整性
        orphaned_messages = self.db.query(func.count(TelegramMessage.id)).outerjoin(
            TelegramGroup
        ).filter(TelegramGroup.id.is_(None)).scalar()
        
        validations["foreign_keys"] = {
            "status": "passed" if orphaned_messages == 0 else "failed",
            "orphaned_messages": orphaned_messages
        }
        
        return validations
    
    async def _validate_relationships(self) -> Dict[str, Any]:
        """验证数据关系"""
        validations = {}
        
        # 检查群组-消息关系
        groups_with_messages = self.db.query(func.count(func.distinct(TelegramMessage.group_id))).scalar()
        total_active_groups = self.db.query(func.count(TelegramGroup.id)).filter(
            TelegramGroup.is_active == True
        ).scalar()
        
        coverage_percentage = (groups_with_messages / total_active_groups) * 100 if total_active_groups > 0 else 0
        
        validations["group_message_coverage"] = {
            "status": "passed" if coverage_percentage >= 50 else "warning",
            "coverage_percentage": coverage_percentage,
            "groups_with_messages": groups_with_messages,
            "total_active_groups": total_active_groups
        }
        
        return validations
    
    async def _check_data_consistency(self) -> Dict[str, Any]:
        """检查数据一致性"""
        consistency_checks = {}
        
        # 检查时间戳一致性
        future_messages = self.db.query(func.count(TelegramMessage.id)).filter(
            TelegramMessage.date > datetime.now()
        ).scalar()
        
        consistency_checks["timestamp_consistency"] = {
            "status": "passed" if future_messages == 0 else "failed",
            "future_messages_count": future_messages
        }
        
        # 检查数据范围合理性
        very_old_messages = self.db.query(func.count(TelegramMessage.id)).filter(
            TelegramMessage.date < datetime(2013, 1, 1)  # Telegram发布前
        ).scalar()
        
        consistency_checks["date_range_validity"] = {
            "status": "passed" if very_old_messages == 0 else "warning",
            "pre_telegram_messages": very_old_messages
        }
        
        return consistency_checks
    
    async def _finalize_migration(self, report: Dict[str, Any]):
        """完成迁移的最终处理"""
        phase_name = "finalization"
        
        try:
            # 更新统计信息
            await self._update_database_statistics()
            
            # 优化数据库
            await self._optimize_database()
            
            # 生成迁移摘要
            migration_summary = await self._generate_migration_summary()
            
            report["phases"].append({
                "phase": phase_name,
                "status": "completed",
                "details": {
                    "migration_summary": migration_summary,
                    "optimization_completed": True
                }
            })
            
        except Exception as e:
            report["phases"].append({
                "phase": phase_name,
                "status": "failed",
                "error": str(e)
            })
            raise
    
    async def _update_database_statistics(self):
        """更新数据库统计信息"""
        try:
            # 更新SQLite统计信息
            self.db.execute(text("ANALYZE"))
            self.db.commit()
        except Exception as e:
            logger.warning(f"更新数据库统计信息失败: {e}")
    
    async def _optimize_database(self):
        """优化数据库"""
        try:
            # 清理和优化SQLite数据库
            self.db.execute(text("VACUUM"))
            self.db.commit()
        except Exception as e:
            logger.warning(f"数据库优化失败: {e}")
    
    async def _generate_migration_summary(self) -> Dict[str, Any]:
        """生成迁移摘要"""
        summary = {
            "migration_id": self.migration_id,
            "total_processing_time": (
                datetime.now() - self.progress.start_time
            ).total_seconds() if self.progress.start_time else 0,
            "items_processed": self.progress.processed_items,
            "success_rate": self.progress.success_rate,
            "final_data_counts": {
                "groups": self.db.query(func.count(TelegramGroup.id)).scalar(),
                "messages": self.db.query(func.count(TelegramMessage.id)).scalar(),
                "active_groups": self.db.query(func.count(TelegramGroup.id)).filter(
                    TelegramGroup.is_active == True
                ).scalar()
            }
        }
        
        return summary
    
    async def _handle_migration_failure(self, report: Dict[str, Any], error: Exception):
        """处理迁移失败"""
        try:
            # 记录详细错误信息
            self.batch_logger.error(f"迁移失败: {error}", extra={
                "migration_id": self.migration_id,
                "progress": {
                    "processed": self.progress.processed_items,
                    "successful": self.progress.successful_items,
                    "failed": self.progress.failed_items
                }
            })
            
            # 尝试回滚（如果有备份）
            backup_dir = Path(f"backups/migration_{self.migration_id}")
            if backup_dir.exists():
                report["rollback_available"] = True
                report["rollback_instructions"] = [
                    f"备份数据位于: {backup_dir}",
                    "可以使用备份数据恢复到迁移前状态",
                    "请联系管理员执行数据恢复"
                ]
            
        except Exception as cleanup_error:
            logger.error(f"处理迁移失败时出错: {cleanup_error}")
    
    async def _cleanup_temp_files(self):
        """清理临时文件"""
        try:
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
                self.batch_logger.info(f"已清理临时目录: {self.temp_dir}")
        except Exception as e:
            logger.warning(f"清理临时文件失败: {e}")
    
    def get_migration_progress(self) -> Dict[str, Any]:
        """获取迁移进度"""
        return {
            "migration_id": self.migration_id,
            "current_phase": self.progress.current_phase,
            "progress_percentage": self.progress.progress_percentage,
            "items_processed": self.progress.processed_items,
            "items_successful": self.progress.successful_items,
            "items_failed": self.progress.failed_items,
            "items_skipped": self.progress.skipped_items,
            "success_rate": self.progress.success_rate,
            "estimated_completion": self.progress.estimated_completion,
            "elapsed_time": (
                datetime.now() - self.progress.start_time
            ).total_seconds() if self.progress.start_time else 0
        }
    
    async def rollback_migration(self, migration_id: str) -> Dict[str, Any]:
        """回滚指定的迁移
        
        Args:
            migration_id: 要回滚的迁移ID
            
        Returns:
            回滚结果报告
        """
        rollback_report = {
            "migration_id": migration_id,
            "rollback_started_at": datetime.now(),
            "success": False
        }
        
        try:
            backup_dir = Path(f"backups/migration_{migration_id}")
            if not backup_dir.exists():
                raise MigrationError(f"未找到迁移 {migration_id} 的备份数据")
            
            # 恢复群组数据
            groups_backup_file = backup_dir / "groups_backup.json"
            if groups_backup_file.exists():
                with open(groups_backup_file, 'r', encoding='utf-8') as f:
                    groups_backup = json.load(f)
                
                # 清除当前群组数据并恢复备份
                self.db.query(TelegramGroup).delete()
                for group_data in groups_backup:
                    group = TelegramGroup(**{
                        k: v for k, v in group_data.items()
                        if k != 'id' and v is not None
                    })
                    self.db.add(group)
                
                self.db.commit()
            
            # 恢复消息数据
            messages_backup_file = backup_dir / "messages_backup.json"
            if messages_backup_file.exists():
                with open(messages_backup_file, 'r', encoding='utf-8') as f:
                    messages_backup = json.load(f)
                
                # 清除当前消息数据并恢复备份
                self.db.query(TelegramMessage).delete()
                for message_data in messages_backup:
                    message = TelegramMessage(**{
                        k: v for k, v in message_data.items()
                        if k != 'id' and v is not None
                    })
                    self.db.add(message)
                
                self.db.commit()
            
            rollback_report["success"] = True
            rollback_report["completed_at"] = datetime.now()
            
        except Exception as e:
            rollback_report["error"] = str(e)
            rollback_report["failed_at"] = datetime.now()
        
        return rollback_report
    
    def __del__(self):
        """析构函数，确保资源清理"""
        if hasattr(self, 'db') and self.db:
            self.db.close()


# 便捷函数
async def migrate_telegram_export(export_file_path: str, config: MigrationConfig = None) -> Dict[str, Any]:
    """便捷的Telegram导出迁移函数"""
    migrator = RealDataMigrator(config)
    try:
        return await migrator.migrate_from_telegram_export(export_file_path)
    finally:
        del migrator


async def migrate_csv_data(csv_file_path: str, mapping_config: Dict[str, str], config: MigrationConfig = None) -> Dict[str, Any]:
    """便捷的CSV数据迁移函数"""
    migrator = RealDataMigrator(config)
    try:
        return await migrator.migrate_from_csv_file(csv_file_path, mapping_config)
    finally:
        del migrator


def get_migration_status(migration_id: str) -> Dict[str, Any]:
    """获取迁移状态"""
    # 这里可以实现基于文件或数据库的迁移状态跟踪
    status_file = Path(f"temp/migration_{migration_id}/status.json")
    if status_file.exists():
        with open(status_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    return {"error": "未找到指定的迁移状态"}