"""
用户设置相关的Pydantic模型
"""
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime

class UserSettingsBase(BaseModel):
    """用户设置基础模型"""
    settings_data: Dict[str, Any] = Field(default_factory=dict)

class UserSettingsCreate(UserSettingsBase):
    """用户设置创建模型"""
    user_id: int

class UserSettingsUpdate(UserSettingsBase):
    """用户设置更新模型"""
    pass

class UserSettingsDB(UserSettingsBase):
    """用户设置数据库模型"""
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True

class UserSettingsOut(BaseModel):
    """用户设置输出模型，直接作为字典返回"""
    language: str = "zh_CN"
    theme: str = "system"
    notificationEnabled: bool = True
    autoDownload: bool = False
    autoDownloadMaxSize: int = 10
    thumbnailsEnabled: bool = True
    timezone: str = "Asia/Shanghai"
    dateFormat: str = "YYYY-MM-DD HH:mm"
    defaultDownloadPath: str = "downloads"
    displayDensity: str = "default"
    previewFilesInline: bool = True
    defaultPageSize: int = 20
    developerMode: bool = False
    
    class Config:
        # 允许额外字段
        extra = "allow"