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
    
    # 其他选项
    include_forwarded = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    
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