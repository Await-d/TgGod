from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Literal

class UserSettingsBase(BaseModel):
    """用户设置基础模型"""
    language: Optional[str] = "zh_CN"
    theme: Optional[Literal["light", "dark", "system"]] = "system"
    notification_enabled: Optional[bool] = True
    auto_download: Optional[bool] = False
    auto_download_max_size: Optional[int] = 10  # MB
    thumbnails_enabled: Optional[bool] = True
    timezone: Optional[str] = "Asia/Shanghai"
    date_format: Optional[str] = "YYYY-MM-DD HH:mm"
    default_download_path: Optional[str] = "downloads"
    display_density: Optional[Literal["default", "compact", "comfortable"]] = "default"
    preview_files_inline: Optional[bool] = True
    default_page_size: Optional[int] = 20
    developer_mode: Optional[bool] = False
    
    class Config:
        orm_mode = True

class UserSettingsCreate(UserSettingsBase):
    """用于创建用户设置的模型"""
    pass

class UserSettingsUpdate(BaseModel):
    """用于更新用户设置的模型"""
    settings_data: Dict[str, Any] = Field(...)

class UserSettingsResponse(BaseModel):
    """用户设置响应模型"""
    id: int
    user_id: int
    settings_data: Dict[str, Any]
    updated_at: str
    created_at: str
    
    class Config:
        orm_mode = True

class UserSettingsOut(BaseModel):
    """简化的用户设置输出模型"""
    language: str = "zh_CN"
    theme: str = "system"
    notification_enabled: bool = True
    auto_download: bool = False
    auto_download_max_size: int = 10
    thumbnails_enabled: bool = True
    timezone: str = "Asia/Shanghai"
    date_format: str = "YYYY-MM-DD HH:mm"
    default_download_path: str = "downloads"
    display_density: str = "default"
    preview_files_inline: bool = True
    default_page_size: int = 20
    developer_mode: bool = False