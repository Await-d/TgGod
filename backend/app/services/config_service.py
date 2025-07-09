from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from ..models.config import SystemConfig
import json
import logging

logger = logging.getLogger(__name__)

class ConfigService:
    def __init__(self):
        self.cache = {}
        self.default_configs = {
            "telegram_api_id": {
                "value": "",
                "description": "Telegram API ID from https://my.telegram.org",
                "is_encrypted": False
            },
            "telegram_api_hash": {
                "value": "",
                "description": "Telegram API Hash from https://my.telegram.org",
                "is_encrypted": True
            },
            "secret_key": {
                "value": "your-secret-key-here",
                "description": "JWT Secret Key for authentication",
                "is_encrypted": True
            },
            "database_url": {
                "value": "sqlite:///./tggod.db",
                "description": "Database connection URL",
                "is_encrypted": False
            },
            "log_level": {
                "value": "INFO",
                "description": "Application log level (DEBUG, INFO, WARNING, ERROR)",
                "is_encrypted": False
            },
            "log_file": {
                "value": "./logs/app.log",
                "description": "Log file path",
                "is_encrypted": False
            },
            "media_root": {
                "value": "./media",
                "description": "Media files storage directory",
                "is_encrypted": False
            },
            "allowed_origins": {
                "value": '["http://localhost:3000", "http://127.0.0.1:3000"]',
                "description": "CORS allowed origins (JSON array)",
                "is_encrypted": False
            }
        }
    
    def get_config(self, key: str, db: Session) -> Optional[str]:
        """获取配置值"""
        if key in self.cache:
            return self.cache[key]
        
        config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
        if config:
            self.cache[key] = config.value
            return config.value
        
        # 返回默认值
        if key in self.default_configs:
            return self.default_configs[key]["value"]
        
        return None
    
    def set_config(self, key: str, value: str, db: Session) -> bool:
        """设置配置值"""
        try:
            config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
            
            if config:
                config.value = value
            else:
                config = SystemConfig(
                    key=key,
                    value=value,
                    description=self.default_configs.get(key, {}).get("description", ""),
                    is_encrypted=self.default_configs.get(key, {}).get("is_encrypted", False)
                )
                db.add(config)
            
            db.commit()
            self.cache[key] = value
            return True
            
        except Exception as e:
            logger.error(f"设置配置失败: {e}")
            db.rollback()
            return False
    
    def get_all_configs(self, db: Session) -> Dict[str, Any]:
        """获取所有配置"""
        configs = {}
        db_configs = db.query(SystemConfig).all()
        
        # 先加载默认配置
        for key, default in self.default_configs.items():
            configs[key] = {
                "value": default["value"],
                "description": default["description"],
                "is_encrypted": default["is_encrypted"]
            }
        
        # 覆盖数据库中的配置
        for config in db_configs:
            configs[config.key] = {
                "value": config.value,
                "description": config.description,
                "is_encrypted": config.is_encrypted
            }
        
        return configs
    
    def init_default_configs(self, db: Session):
        """初始化默认配置"""
        for key, default in self.default_configs.items():
            existing = db.query(SystemConfig).filter(SystemConfig.key == key).first()
            if not existing:
                config = SystemConfig(
                    key=key,
                    value=default["value"],
                    description=default["description"],
                    is_encrypted=default["is_encrypted"]
                )
                db.add(config)
        
        try:
            db.commit()
            logger.info("默认配置初始化完成")
        except Exception as e:
            logger.error(f"初始化默认配置失败: {e}")
            db.rollback()
    
    def get_telegram_config(self, db: Session) -> Dict[str, str]:
        """获取Telegram配置"""
        return {
            "api_id": self.get_config("telegram_api_id", db),
            "api_hash": self.get_config("telegram_api_hash", db)
        }
    
    def clear_cache(self):
        """清除缓存"""
        self.cache.clear()

# 创建全局配置服务实例
config_service = ConfigService()