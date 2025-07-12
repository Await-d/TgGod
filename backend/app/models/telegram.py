from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, BigInteger, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base

class TelegramGroup(Base):
    __tablename__ = "telegram_groups"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)
    title = Column(String(255), nullable=False)
    username = Column(String(255), nullable=True, index=True)
    description = Column(Text, nullable=True)
    member_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系
    messages = relationship("TelegramMessage", back_populates="group", cascade="all, delete-orphan")
    rules = relationship("FilterRule", back_populates="group", cascade="all, delete-orphan")
    tasks = relationship("DownloadTask", back_populates="group", cascade="all, delete-orphan")

class TelegramMessage(Base):
    __tablename__ = "telegram_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("telegram_groups.id"), nullable=False)
    message_id = Column(BigInteger, nullable=False)
    sender_id = Column(BigInteger, nullable=True)
    sender_username = Column(String(255), nullable=True)
    sender_name = Column(String(255), nullable=True)
    text = Column(Text, nullable=True)
    media_type = Column(String(50), nullable=True)  # photo, video, document, audio, voice, sticker
    media_path = Column(String(500), nullable=True)  # 本地文件路径（仅下载后存在）
    media_size = Column(BigInteger, nullable=True)
    media_filename = Column(String(255), nullable=True)
    media_file_id = Column(String(255), nullable=True)  # Telegram文件ID（用于下载）
    media_file_unique_id = Column(String(255), nullable=True)  # Telegram唯一文件ID
    media_downloaded = Column(Boolean, default=False)  # 是否已下载到本地
    media_download_url = Column(String(500), nullable=True)  # Telegram下载链接（临时）
    media_download_error = Column(Text, nullable=True)  # 下载失败错误信息
    media_thumbnail_path = Column(String(500), nullable=True)  # 缩略图路径
    view_count = Column(Integer, default=0)
    is_forwarded = Column(Boolean, default=False)
    forwarded_from = Column(String(255), nullable=True)  # 转发来源名称
    forwarded_from_id = Column(BigInteger, nullable=True)  # 转发来源ID（用户ID或群组ID）
    forwarded_from_type = Column(String(20), nullable=True)  # 转发来源类型：user, group, channel
    forwarded_date = Column(DateTime(timezone=True), nullable=True)  # 原消息发送时间
    is_own_message = Column(Boolean, default=False)  # 是否为当前用户发送的消息
    
    # 新增字段
    reply_to_message_id = Column(BigInteger, nullable=True)  # 回复的消息ID
    edit_date = Column(DateTime(timezone=True), nullable=True)  # 编辑时间
    is_pinned = Column(Boolean, default=False)  # 是否置顶
    reactions = Column(JSON, nullable=True)  # 消息反应（点赞等）
    mentions = Column(JSON, nullable=True)  # 提及的用户
    hashtags = Column(JSON, nullable=True)  # 话题标签
    urls = Column(JSON, nullable=True)  # 消息中的链接
    
    date = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系
    group = relationship("TelegramGroup", back_populates="messages")
    
    # 创建复合索引
    __table_args__ = (
        {"mysql_engine": "InnoDB"},
    )