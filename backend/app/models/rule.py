from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base

class FilterRule(Base):
    __tablename__ = "filter_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    group_id = Column(Integer, ForeignKey("telegram_groups.id"), nullable=False)
    
    # 过滤条件
    keywords = Column(JSON, nullable=True)  # 包含关键词列表
    exclude_keywords = Column(JSON, nullable=True)  # 排除关键词列表
    sender_filter = Column(JSON, nullable=True)  # 发送者过滤列表
    media_types = Column(JSON, nullable=True)  # 媒体类型过滤列表
    
    # 时间过滤
    date_from = Column(DateTime(timezone=True), nullable=True)
    date_to = Column(DateTime(timezone=True), nullable=True)
    
    # 数值过滤
    min_views = Column(Integer, nullable=True)
    max_views = Column(Integer, nullable=True)
    
    # 文件大小过滤（字节）
    min_file_size = Column(Integer, nullable=True)  # 最小文件大小
    max_file_size = Column(Integer, nullable=True)  # 最大文件大小
    
    # 其他选项
    include_forwarded = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    
    # 同步跟踪字段
    last_sync_time = Column(DateTime(timezone=True), nullable=True)  # 最后同步时间
    last_sync_message_count = Column(Integer, default=0)  # 最后同步的消息数量
    sync_status = Column(String(20), default='pending')  # 同步状态: pending, syncing, completed, failed
    needs_full_resync = Column(Boolean, default=True)  # 是否需要完全重新同步
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系
    group = relationship("TelegramGroup", back_populates="rules")
    tasks = relationship("DownloadTask", back_populates="rule")

class DownloadTask(Base):
    __tablename__ = "download_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    group_id = Column(Integer, ForeignKey("telegram_groups.id"), nullable=False)
    rule_id = Column(Integer, ForeignKey("filter_rules.id"), nullable=False)
    
    # 任务状态
    status = Column(String(50), default="pending")  # pending, running, completed, failed, paused
    progress = Column(Integer, default=0)
    total_messages = Column(Integer, default=0)
    downloaded_messages = Column(Integer, default=0)
    
    # 下载配置
    download_path = Column(String(500), nullable=False)
    
    # Jellyfin 兼容配置
    use_jellyfin_structure = Column(Boolean, default=False)  # 是否使用Jellyfin格式
    include_metadata = Column(Boolean, default=True)  # 是否生成NFO文件
    download_thumbnails = Column(Boolean, default=True)  # 是否下载缩略图
    use_series_structure = Column(Boolean, default=False)  # 是否使用剧集结构
    organize_by_date = Column(Boolean, default=True)  # 是否按日期组织
    max_filename_length = Column(Integer, default=150)  # 最大文件名长度
    
    # 图片尺寸配置 (存储为 "宽x高" 格式)
    thumbnail_size = Column(String(20), default="400x300")  # 缩略图尺寸
    poster_size = Column(String(20), default="600x900")  # 海报图尺寸
    fanart_size = Column(String(20), default="1920x1080")  # 背景图尺寸
    
    # 时间范围过滤（用于下载任务的时间筛选）
    date_from = Column(DateTime(timezone=True), nullable=True)  # 开始时间
    date_to = Column(DateTime(timezone=True), nullable=True)    # 结束时间
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # 错误信息
    error_message = Column(Text, nullable=True)
    
    # 关系
    group = relationship("TelegramGroup", back_populates="tasks")
    rule = relationship("FilterRule", back_populates="tasks")
    logs = relationship("TaskLog", back_populates="task", cascade="all, delete-orphan")
    download_records = relationship("DownloadRecord", back_populates="task", cascade="all, delete-orphan")

class DownloadRecord(Base):
    """下载记录模型 - 记录每个具体下载的文件"""
    __tablename__ = "download_records"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("download_tasks.id"), nullable=False)
    
    # 文件信息
    file_name = Column(String(500), nullable=False)  # 原始文件名
    local_file_path = Column(String(1000), nullable=False)  # 本地存储路径
    file_size = Column(Integer, nullable=True)  # 文件大小（字节）
    file_type = Column(String(50), nullable=True)  # 文件类型（photo, video, document等）
    
    # Telegram消息信息
    message_id = Column(Integer, nullable=False)  # 消息ID
    sender_id = Column(Integer, nullable=True)  # 发送者ID
    sender_name = Column(String(255), nullable=True)  # 发送者名称
    message_date = Column(DateTime(timezone=True), nullable=True)  # 消息发送时间
    message_text = Column(Text, nullable=True)  # 消息文本内容
    
    # 下载状态
    download_status = Column(String(50), default="completed")  # completed, failed, partial
    download_progress = Column(Integer, default=100)  # 下载进度 0-100
    error_message = Column(Text, nullable=True)  # 错误信息
    
    # 时间戳
    download_started_at = Column(DateTime(timezone=True), nullable=True)  # 下载开始时间
    download_completed_at = Column(DateTime(timezone=True), server_default=func.now())  # 下载完成时间
    
    # 关系
    task = relationship("DownloadTask", back_populates="download_records")
