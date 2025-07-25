from sqlalchemy.orm import Session
from typing import List, Optional
import os
import json

class Settings:
    def __init__(self):
        self._cache = {}
    
    def get_db(self) -> Session:
        # 延迟导入避免循环依赖
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        
        # 直接使用环境变量避免循环导入
        database_url = os.environ.get("DATABASE_URL", "sqlite:////app/data/tggod.db")
        
        if "sqlite" in database_url:
            engine = create_engine(
                database_url,
                connect_args={
                    "check_same_thread": False,
                    "timeout": 30,
                    "isolation_level": None,
                },
                pool_pre_ping=True,
                pool_recycle=3600,
                echo=False
            )
        else:
            engine = create_engine(
                database_url,
                pool_pre_ping=True,
                pool_recycle=3600,
                echo=False
            )
        
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        return SessionLocal()
    
    def _get_config(self, key: str, default=None):
        """从数据库获取配置，带缓存和优化的数据库访问"""
        if key in self._cache:
            return self._cache[key]
        
        try:
            # 使用优化的数据库会话
            from .utils.db_optimization import optimized_db_session
            with optimized_db_session(autocommit=False, max_retries=3) as db:
                from .services.config_service import config_service
                value = config_service.get_config(key, db)
                if value is not None:
                    self._cache[key] = value
                    return value
                return default
        except Exception as e:
            print(f"获取配置失败 {key}: {e}")
            return default
    
    def _get_list_config(self, key: str, default: List[str] = None):
        """获取列表类型的配置"""
        if default is None:
            default = []
        
        value = self._get_config(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return default
        return default
    
    def _get_int_config(self, key: str, default: int = 0):
        """获取整数类型的配置"""
        value = self._get_config(key, str(default))
        try:
            return int(value)
        except (ValueError, TypeError):
            return default
    
    def clear_cache(self):
        """清除缓存"""
        self._cache.clear()
    
    @property
    def database_url(self) -> str:
        # 默认使用外部挂载目录中的SQLite数据库
        default_db_path = os.environ.get("DATABASE_URL", "sqlite:////app/data/tggod.db")
        return self._get_config("database_url", default_db_path)
    
    @property
    def telegram_api_id(self) -> int:
        # 优先从环境变量读取
        env_value = os.environ.get("TELEGRAM_API_ID")
        if env_value and env_value != "your_api_id_here":
            try:
                return int(env_value)
            except ValueError:
                pass
        return self._get_int_config("telegram_api_id")
    
    @property
    def telegram_api_hash(self) -> str:
        # 优先从环境变量读取
        env_value = os.environ.get("TELEGRAM_API_HASH")
        if env_value and env_value != "your_api_hash_here":
            return env_value
        return self._get_config("telegram_api_hash", "")
    
    @property
    def telegram_bot_token(self) -> Optional[str]:
        return self._get_config("telegram_bot_token")
    
    @property
    def secret_key(self) -> str:
        return self._get_config("secret_key", "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7")
    
    @property
    def jwt_secret_key(self) -> str:
        return self._get_config("jwt_secret_key", "88e8d3e709d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b")
    
    @property
    def default_admin_username(self) -> str:
        return self._get_config("default_admin_username", "admin")
    
    @property
    def default_admin_password(self) -> str:
        return self._get_config("default_admin_password", "admin123")
    
    @property
    def default_admin_email(self) -> str:
        return self._get_config("default_admin_email", "admin@tggod.local")
    
    @property
    def algorithm(self) -> str:
        return "HS256"
    
    @property
    def access_token_expire_minutes(self) -> int:
        return 30
    
    @property
    def allowed_origins(self) -> List[str]:
        return self._get_list_config("allowed_origins", ["http://localhost:3000", "http://localhost:3001"])
    
    @property
    def media_root(self) -> str:
        # 默认使用外部挂载目录中的媒体文件夹
        default_media_path = os.environ.get("MEDIA_ROOT", "/app/media")
        return self._get_config("media_root", default_media_path)
    
    @property
    def max_file_size(self) -> str:
        return "100MB"
    
    @property
    def log_level(self) -> str:
        return self._get_config("log_level", "INFO")
    
    @property
    def log_file(self) -> str:
        # 默认使用外部挂载目录中的日志文件
        default_log_path = os.environ.get("LOG_FILE", "/app/logs/app.log")
        return self._get_config("log_file", default_log_path)
    
    @property
    def smtp_host(self) -> str:
        return self._get_config("smtp_host", "smtp.gmail.com")
    
    @property
    def smtp_port(self) -> int:
        return self._get_int_config("smtp_port", 587)
    
    @property
    def smtp_username(self) -> str:
        return self._get_config("smtp_username", "")
    
    @property
    def smtp_password(self) -> str:
        return self._get_config("smtp_password", "")
    
    @property
    def smtp_from(self) -> str:
        return self._get_config("smtp_from", "")
    
    @property
    def ws_host(self) -> str:
        return "localhost"
    
    @property
    def ws_port(self) -> int:
        return 8001
    
    @property
    def default_user_settings(self) -> dict:
        """默认用户设置配置"""
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

# 创建全局设置实例
settings = Settings()

def init_settings():
    """初始化设置 - 创建必要的目录和默认配置"""
    db = None
    try:
        # 确保所有必要的目录存在
        os.makedirs(settings.media_root, exist_ok=True)
        os.makedirs(os.path.dirname(settings.log_file), exist_ok=True)
        
        # 确保数据库目录存在
        db_path = settings.database_url.replace("sqlite:///", "")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # 确保Telegram会话目录存在
        os.makedirs("/app/telegram_sessions", exist_ok=True)
        
        # 初始化默认配置
        db = settings.get_db()
        from .services.config_service import config_service
        config_service.init_default_configs(db)
        
        # 确保用户设置表存在
        try:
            from .services.user_settings_service import user_settings_service
            user_settings_service.ensure_user_settings_table_exists(db)
            print("用户设置表检查完成")
        except Exception as e:
            print(f"用户设置表检查失败: {e}")
        
        print("设置初始化完成")
    except Exception as e:
        print(f"设置初始化失败: {e}")
    finally:
        if db:
            db.close()

def get_default_user_settings():
    """获取默认用户设置"""
    return settings.default_user_settings