from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from datetime import datetime
from ..models.user_settings import UserSettings
from ..models.user import User

class UserSettingsService:
    def get_settings(self, db: Session, user_id: int) -> Optional[UserSettings]:
        """获取用户设置"""
        return db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
    
    def create_settings(self, db: Session, user_id: int, settings_data: Dict[str, Any]) -> UserSettings:
        """创建用户设置"""
        # 检查用户是否存在
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"用户ID {user_id} 不存在")
            
        # 创建设置记录
        settings = UserSettings(
            user_id=user_id,
            settings_data=settings_data,
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat()
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
        return settings
    
    def update_settings(self, db: Session, user_id: int, settings_data: Dict[str, Any]) -> Optional[UserSettings]:
        """更新用户设置"""
        settings = self.get_settings(db, user_id)
        
        if not settings:
            # 如果设置不存在，则创建一个新的
            return self.create_settings(db, user_id, settings_data)
        
        # 更新现有设置
        settings.settings_data = settings_data
        settings.updated_at = datetime.utcnow().isoformat()
        db.commit()
        db.refresh(settings)
        return settings
    
    def delete_settings(self, db: Session, user_id: int) -> bool:
        """删除用户设置（重置为默认）"""
        settings = self.get_settings(db, user_id)
        if not settings:
            return False
            
        db.delete(settings)
        db.commit()
        return True
    
    def ensure_user_settings_table_exists(self, db: Session) -> bool:
        """确保用户设置表存在"""
        from sqlalchemy import inspect
        inspector = inspect(db.bind)
        
        # 检查表是否存在
        has_table = "user_settings" in inspector.get_table_names()
        
        # 如果表不存在，这里我们不做任何操作
        # 表的创建将由数据库迁移或自动修复脚本处理
        return has_table
    
    def get_default_settings(self) -> Dict[str, Any]:
        """获取默认用户设置"""
        return {
            "language": "zh_CN",
            "theme": "system",
            "notification_enabled": True,
            "auto_download": False,
            "auto_download_max_size": 10,
            "thumbnails_enabled": True,
            "timezone": "Asia/Shanghai",
            "date_format": "YYYY-MM-DD HH:mm",
            "default_download_path": "downloads",
            "display_density": "default",
            "preview_files_inline": True,
            "default_page_size": 20,
            "developer_mode": False
        }

# 创建服务实例
user_settings_service = UserSettingsService()