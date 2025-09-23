"""
自定义异常类
"""

from enum import Enum
from typing import Optional, Any, Dict

class ErrorCategory(Enum):
    """错误分类"""
    SYSTEM = "system"
    BUSINESS = "business"
    VALIDATION = "validation"
    NETWORK = "network"
    DATABASE = "database"
    EXTERNAL = "external"

class ErrorSeverity(Enum):
    """错误严重程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorContext:
    """错误上下文"""
    def __init__(self, **kwargs):
        self.context = kwargs
    
    def __repr__(self):
        return f"ErrorContext({self.context})"

# 基础异常类
class ServiceError(Exception):
    """服务错误基类"""
    pass

class BusinessError(Exception):
    """业务逻辑错误"""
    pass

class DatabaseError(ServiceError):
    """数据库错误"""
    pass

class ValidationError(BusinessError):
    """验证错误"""
    pass

class AuthenticationError(ServiceError):
    """认证错误"""
    pass

class SystemError(ServiceError):
    """系统错误"""
    pass

class ExternalServiceError(ServiceError):
    """外部服务错误"""
    pass

class ConfigurationError(ServiceError):
    """配置错误"""
    pass

class NetworkError(ServiceError):
    """网络错误"""
    pass

class FileSystemError(ServiceError):
    """文件系统错误"""
    pass

# 特定服务异常
class TelegramServiceError(ExternalServiceError):
    """Telegram服务错误"""
    pass

class MediaDownloadError(ServiceError):
    """媒体下载错误"""
    pass

class TaskExecutionError(ServiceError):
    """任务执行错误"""
    pass

class FileOrganizationError(ServiceError):
    """文件组织错误"""
    pass

class SessionStoreError(ServiceError):
    """会话存储错误"""
    pass

class CircuitBreakerError(ServiceError):
    """熔断器错误"""
    pass

class MigrationError(ServiceError):
    """数据库迁移错误"""
    pass

class TempFileError(ServiceError):
    """临时文件管理错误"""
    pass

class PlatformError(ServiceError):
    """平台相关错误"""
    pass

# 错误创建辅助函数
def create_validation_error(message: str, field: Optional[str] = None, **kwargs) -> ValidationError:
    """创建验证错误"""
    error_msg = f"Validation error: {message}"
    if field:
        error_msg = f"{error_msg} (field: {field})"
    return ValidationError(error_msg)

def create_config_error(key: str, message: str) -> ConfigurationError:
    """创建配置错误"""
    return ConfigurationError(f"Config error for '{key}': {message}")

def create_telegram_error(message: str, **kwargs) -> TelegramServiceError:
    """创建Telegram错误"""
    return TelegramServiceError(f"Telegram error: {message}")

def create_network_timeout_error(service: str, timeout: float) -> NetworkError:
    """创建网络超时错误"""
    return NetworkError(f"Network timeout for {service} after {timeout}s")