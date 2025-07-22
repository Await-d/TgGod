from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from ..database import Base

class UserSettings(Base):
    """用户设置模型"""
    __tablename__ = "user_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, index=True, nullable=False)
    # 存储为JSON格式
    settings_data = Column(JSON, nullable=False, default={})
    # 上次更新时间
    updated_at = Column(String, default=lambda: datetime.utcnow().isoformat())
    # 创建时间
    created_at = Column(String, default=lambda: datetime.utcnow().isoformat())
    
    # 关联用户
    user = relationship("User", back_populates="settings")