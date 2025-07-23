"""
用户设置服务 - 提供用户设置的增删改查功能
"""
from sqlalchemy.orm import Session
from sqlalchemy import text, inspect
import json
from typing import Dict, Any, Optional, Tuple
import logging
from datetime import datetime

from ..models.user_settings import UserSettings
from ..config import get_default_user_settings

logger = logging.getLogger(__name__)

class UserSettingsService:
    def get_settings(self, db: Session, user_id: int) -> Optional[UserSettings]:
        """
        获取用户设置
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            
        Returns:
            用户设置对象或None
        """
        return db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
    
    def get_default_settings(self) -> Dict[str, Any]:
        """
        获取默认设置
        
        Returns:
            默认设置字典
        """
        return get_default_user_settings()
    
    def create_settings(self, db: Session, user_id: int, settings_data: Dict[str, Any]) -> UserSettings:
        """
        创建用户设置
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            settings_data: 设置数据
            
        Returns:
            创建的用户设置对象
        """
        # 确保设置数据是有效的JSON
        settings_json = json.dumps(settings_data)
        
        # 创建设置对象
        db_settings = UserSettings(
            user_id=user_id,
            settings_data=settings_json
        )
        
        db.add(db_settings)
        db.commit()
        db.refresh(db_settings)
        
        return db_settings
    
    def update_settings(self, db: Session, user_id: int, settings_data: Dict[str, Any]) -> UserSettings:
        """
        更新用户设置
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            settings_data: 设置数据
            
        Returns:
            更新后的用户设置对象
        """
        # 查找现有设置
        db_settings = self.get_settings(db, user_id)
        
        # 如果不存在，则创建新设置
        if not db_settings:
            return self.create_settings(db, user_id, settings_data)
        
        # 获取现有设置数据
        try:
            current_data = json.loads(db_settings.settings_data)
        except (json.JSONDecodeError, TypeError):
            current_data = {}
        
        # 合并设置数据
        merged_data = {**current_data, **settings_data}
        
        # 更新设置
        db_settings.settings_data = json.dumps(merged_data)
        db_settings.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(db_settings)
        
        return db_settings
    
    def delete_settings(self, db: Session, user_id: int) -> bool:
        """
        删除用户设置
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            
        Returns:
            是否成功删除
        """
        db_settings = self.get_settings(db, user_id)
        
        if not db_settings:
            return False
        
        db.delete(db_settings)
        db.commit()
        
        return True
    
    def ensure_user_settings_table_exists(self, db: Session) -> Tuple[bool, str]:
        """
        确保用户设置表存在
        
        Args:
            db: 数据库会话
            
        Returns:
            (成功标志, 消息)
        """
        try:
            inspector = inspect(db.bind)
            
            # 检查表是否存在
            if 'user_settings' not in inspector.get_table_names():
                # 创建表
                db.execute(text("""
                    CREATE TABLE IF NOT EXISTS user_settings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        settings_data TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                    )
                """))
                
                # 创建索引
                db.execute(text("""
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_user_settings_user_id 
                    ON user_settings(user_id)
                """))
                
                db.commit()
                return True, "用户设置表已创建"
            
            return True, "用户设置表已存在"
        except Exception as e:
            return False, f"确保用户设置表存在时发生错误: {str(e)}"

# 创建全局服务实例
user_settings_service = UserSettingsService()