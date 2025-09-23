"""TgGod应用配置模块

该模块定义了TgGod系统的所有配置项目，包括:

- 数据库连接配置
- Telegram API凭据配置
- 安全和认证配置
- 媒体文件存储配置
- 日志和监控配置
- 用户默认设置

Features:
    - 支持环境变量和数据库双重配置源
    - 缓存机制提高配置访问性能
    - 类型安全的配置属性访问
    - 自动目录创建和初始化
    - 灵活的默认值设置

Author: TgGod Team
Version: 1.0.0
"""

from sqlalchemy.orm import Session
from typing import List, Optional
import os
import json

class Settings:
    """TgGod应用配置类

    管理应用程序的所有配置参数，支持从环境变量和数据库
    中动态加载配置。包含内置缓存机制以提高性能。

    Attributes:
        _cache (dict): 配置值缓存字典

    Methods:
        get_db(): 获取数据库连接
        clear_cache(): 清空配置缓存
        各类配置属性: 提供类型安全的配置访问

    Note:
        所有配置项都支持环境变量覆盖，环境变量优先级更高
    """
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
        """从数据库获取配置值

        使用缓存机制和优化的数据库访问进行配置加载。
        支持错误处理和重试机制。

        Args:
            key (str): 配置键名
            default: 默认值，当配置不存在或获取失败时返回

        Returns:
            Any: 配置值或默认值

        Note:
            - 首次访问时从数据库加载并缓存
            - 后续访问直接从缓存返回
            - 数据库访问失败时返回默认值
        """
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
        """获取列表类型的配置值

        从数据库中获取JSON格式的列表配置，自动进行反序列化。

        Args:
            key (str): 配置键名
            default (List[str], optional): 默认列表值

        Returns:
            List[str]: 配置列表或默认列表

        Example:
            allowed_origins = self._get_list_config("allowed_origins", ["http://localhost"])

        Note:
            如果JSON解析失败，会返回默认列表
        """
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
        """获取整数类型的配置值

        从数据库中获取字符串配置并转换为整数类型。

        Args:
            key (str): 配置键名
            default (int): 默认整数值

        Returns:
            int: 配置整数值或默认值

        Example:
            port = self._get_int_config("api_port", 8000)

        Note:
            如果类型转换失败，会返回默认整数值
        """
        value = self._get_config(key, str(default))
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    def _get_float_config(self, key: str, default: float = 0.0):
        """获取浮点数类型的配置值

        从数据库中获取字符串配置并转换为浮点数类型。

        Args:
            key (str): 配置键名
            default (float): 默认浮点数值

        Returns:
            float: 配置浮点数值或默认值
        """
        value = self._get_config(key, str(default))
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    def clear_cache(self):
        """清除配置缓存

        删除所有缓存的配置值，强制下次访问时从数据库重新加载。

        Note:
            在配置变更后调用此方法以确保获取最新的配置值
        """
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
    def enable_batch_logging(self) -> bool:
        """是否启用批处理日志"""
        return self._get_config("enable_batch_logging", "true").lower() == "true"

    @property
    def log_batch_size(self) -> int:
        """日志批次大小"""
        return self._get_int_config("log_batch_size", 100)

    @property
    def log_flush_interval(self) -> float:
        """日志刷新间隔(秒)"""
        return self._get_float_config("log_flush_interval", 5.0)

    @property
    def log_max_buffer_size(self) -> int:
        """日志最大缓冲区大小"""
        return self._get_int_config("log_max_buffer_size", 10000)

    @property
    def log_max_memory_mb(self) -> int:
        """日志最大内存使用量(MB)"""
        return self._get_int_config("log_max_memory_mb", 50)
    
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
    def redis_url(self) -> str:
        """Redis连接URL"""
        return self._get_config("redis_url", "redis://localhost:6379/0")

    @property
    def redis_password(self) -> Optional[str]:
        """Redis密码"""
        return self._get_config("redis_password")

    @property
    def session_encryption_key(self) -> Optional[str]:
        """会话加密密钥"""
        env_key = os.environ.get("SESSION_ENCRYPTION_KEY")
        if env_key:
            return env_key
        return self._get_config("session_encryption_key") or self.secret_key

    @property
    def default_user_settings(self) -> dict:
        """默认用户设置配置

        定义新用户的初始设置值，包括界面主题、语言、
        下载参数、通知设置等。

        Returns:
            dict: 默认设置字典，包含以下项目:
                - language: 界面语言
                - theme: 主题模式(明亮/黑暗/自动)
                - notification_enabled: 是否开启通知
                - auto_download: 是否自动下载
                - auto_download_max_size: 自动下载最大文件大小(MB)
                - thumbnails_enabled: 是否生成缩略图
                - timezone: 时区设置
                - date_format: 日期格式
                - default_download_path: 默认下载路径
                - display_density: 界面密度
                - preview_files_inline: 是否内联预览文件
                - default_page_size: 默认分页大小
                - developer_mode: 是否开启开发者模式

        Note:
            这些设置可以在用户登录后通过设置页面修改
        """
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
    """初始化应用设置

    创建必要的目录结构和默认配置项目，确保应用程序
    能够正常启动和运行。

    Operations:
        - 创建媒体文件存储目录
        - 创建日志文件目录
        - 创建数据库文件目录
        - 创建Telegram会话目录
        - 初始化默认配置值
        - 检查用户设置表结构

    Raises:
        Exception: 当目录创建或配置初始化失败时

    Note:
        该函数在应用程序启动时被调用，失败不会阻止应用程序继续运行
    """
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
    """获取默认用户设置配置

    返回新用户的默认设置配置，包括界面、下载、通知等所有选项。

    Returns:
        dict: 包含全部默认设置的字典

    Example:
        {
            "language": "zh_CN",
            "theme": "system",
            "notification_enabled": True,
            "auto_download": False,
            ...
        }

    Note:
        该函数在用户注册或初始化时被调用
    """
    return settings.default_user_settings