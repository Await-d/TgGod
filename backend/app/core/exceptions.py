"""
统一异常处理模块
定义项目中所有服务使用的标准异常类型和错误处理机制
"""
import time
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from enum import Enum
from dataclasses import dataclass, field


class ErrorSeverity(Enum):
    """错误严重程度"""
    LOW = "low"          # 轻微错误，不影响核心功能
    MEDIUM = "medium"    # 中等错误，影响部分功能
    HIGH = "high"        # 严重错误，影响核心功能
    CRITICAL = "critical" # 致命错误，系统无法正常运行


class ErrorCategory(Enum):
    """错误分类"""
    BUSINESS = "business"           # 业务逻辑错误
    SYSTEM = "system"              # 系统级错误
    EXTERNAL_SERVICE = "external"   # 外部服务错误
    CONFIGURATION = "configuration" # 配置错误
    VALIDATION = "validation"       # 数据验证错误
    AUTHENTICATION = "auth"         # 认证授权错误
    NETWORK = "network"            # 网络错误
    DATABASE = "database"          # 数据库错误
    FILE_SYSTEM = "filesystem"     # 文件系统错误


@dataclass
class ErrorContext:
    """错误上下文信息"""
    service_name: str
    operation_name: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    error_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    task_id: Optional[int] = None
    request_id: Optional[str] = None
    additional_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式用于日志记录"""
        return {
            "error_id": self.error_id,
            "service_name": self.service_name,
            "operation_name": self.operation_name,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "task_id": self.task_id,
            "request_id": self.request_id,
            "additional_data": self.additional_data
        }


class ServiceError(Exception):
    """服务错误基类"""

    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        error_code: Optional[str] = None,
        context: Optional[ErrorContext] = None,
        original_error: Optional[Exception] = None,
        suggested_action: Optional[str] = None,
        retry_after: Optional[int] = None
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.error_code = error_code or self._generate_error_code()
        self.context = context or ErrorContext(
            service_name="unknown",
            operation_name="unknown"
        )
        self.original_error = original_error
        self.suggested_action = suggested_action
        self.retry_after = retry_after
        self.created_at = datetime.now(timezone.utc)

    def _generate_error_code(self) -> str:
        """生成错误码"""
        return f"{self.category.value.upper()}_{int(time.time())}"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        error_dict = {
            "error_code": self.error_code,
            "message": self.message,
            "category": self.category.value,
            "severity": self.severity.value,
            "created_at": self.created_at.isoformat(),
            "context": self.context.to_dict() if self.context else None,
            "suggested_action": self.suggested_action,
            "retry_after": self.retry_after
        }

        if self.original_error:
            error_dict["original_error"] = {
                "type": type(self.original_error).__name__,
                "message": str(self.original_error)
            }

        return error_dict

    def is_retryable(self) -> bool:
        """判断是否可重试"""
        # 默认情况下，系统错误和外部服务错误可重试
        return self.category in [ErrorCategory.SYSTEM, ErrorCategory.EXTERNAL_SERVICE, ErrorCategory.NETWORK]


class BusinessError(ServiceError):
    """业务逻辑错误"""

    def __init__(self, message: str, **kwargs):
        kwargs.setdefault('category', ErrorCategory.BUSINESS)
        kwargs.setdefault('severity', ErrorSeverity.LOW)
        super().__init__(message, **kwargs)

    def is_retryable(self) -> bool:
        """业务错误通常不可重试"""
        return False


class ValidationError(BusinessError):
    """数据验证错误"""

    def __init__(self, message: str, field_name: Optional[str] = None, **kwargs):
        kwargs.setdefault('category', ErrorCategory.VALIDATION)
        super().__init__(message, **kwargs)
        self.field_name = field_name
        if field_name and self.context:
            self.context.additional_data["field_name"] = field_name


class AuthenticationError(ServiceError):
    """认证错误"""

    def __init__(self, message: str, **kwargs):
        kwargs.setdefault('category', ErrorCategory.AUTHENTICATION)
        kwargs.setdefault('severity', ErrorSeverity.HIGH)
        super().__init__(message, **kwargs)

    def is_retryable(self) -> bool:
        """认证错误通常不可重试"""
        return False


class SystemError(ServiceError):
    """系统级错误"""

    def __init__(self, message: str, **kwargs):
        kwargs.setdefault('category', ErrorCategory.SYSTEM)
        kwargs.setdefault('severity', ErrorSeverity.HIGH)
        super().__init__(message, **kwargs)


class ExternalServiceError(ServiceError):
    """外部服务错误"""

    def __init__(self, message: str, service_name: str, **kwargs):
        kwargs.setdefault('category', ErrorCategory.EXTERNAL_SERVICE)
        kwargs.setdefault('severity', ErrorSeverity.MEDIUM)
        super().__init__(message, **kwargs)
        self.service_name = service_name
        if self.context:
            self.context.additional_data["external_service"] = service_name


class ConfigurationError(ServiceError):
    """配置错误"""

    def __init__(self, message: str, config_key: Optional[str] = None, **kwargs):
        kwargs.setdefault('category', ErrorCategory.CONFIGURATION)
        kwargs.setdefault('severity', ErrorSeverity.HIGH)
        super().__init__(message, **kwargs)
        self.config_key = config_key
        if config_key and self.context:
            self.context.additional_data["config_key"] = config_key

    def is_retryable(self) -> bool:
        """配置错误通常不可重试"""
        return False


class NetworkError(ServiceError):
    """网络错误"""

    def __init__(self, message: str, **kwargs):
        kwargs.setdefault('category', ErrorCategory.NETWORK)
        kwargs.setdefault('severity', ErrorSeverity.MEDIUM)
        super().__init__(message, **kwargs)


class DatabaseError(ServiceError):
    """数据库错误"""

    def __init__(self, message: str, **kwargs):
        kwargs.setdefault('category', ErrorCategory.DATABASE)
        kwargs.setdefault('severity', ErrorSeverity.HIGH)
        super().__init__(message, **kwargs)


class FileSystemError(ServiceError):
    """文件系统错误"""

    def __init__(self, message: str, file_path: Optional[str] = None, **kwargs):
        kwargs.setdefault('category', ErrorCategory.FILE_SYSTEM)
        kwargs.setdefault('severity', ErrorSeverity.MEDIUM)
        super().__init__(message, **kwargs)
        self.file_path = file_path
        if file_path and self.context:
            self.context.additional_data["file_path"] = file_path


# 专门针对TgGod项目的异常类
class TelegramServiceError(ExternalServiceError):
    """Telegram服务错误"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, service_name="telegram", **kwargs)


class MediaDownloadError(ServiceError):
    """媒体下载错误"""

    def __init__(self, message: str, media_type: Optional[str] = None, **kwargs):
        kwargs.setdefault('category', ErrorCategory.EXTERNAL_SERVICE)
        super().__init__(message, **kwargs)
        self.media_type = media_type
        if media_type and self.context:
            self.context.additional_data["media_type"] = media_type


class TaskExecutionError(ServiceError):
    """任务执行错误"""

    def __init__(self, message: str, task_id: Optional[int] = None, **kwargs):
        kwargs.setdefault('category', ErrorCategory.BUSINESS)
        super().__init__(message, **kwargs)
        if task_id:
            self.context.task_id = task_id


class FileOrganizationError(ServiceError):
    """文件组织错误"""

    def __init__(self, message: str, source_path: Optional[str] = None, **kwargs):
        kwargs.setdefault('category', ErrorCategory.FILE_SYSTEM)
        super().__init__(message, **kwargs)
        if source_path and self.context:
            self.context.additional_data["source_path"] = source_path


# 错误工厂函数，用于快速创建常见错误
def create_validation_error(message: str, field_name: str, context: Optional[ErrorContext] = None) -> ValidationError:
    """创建验证错误"""
    return ValidationError(message, field_name=field_name, context=context)


def create_config_error(message: str, config_key: str, context: Optional[ErrorContext] = None) -> ConfigurationError:
    """创建配置错误"""
    return ConfigurationError(message, config_key=config_key, context=context)


def create_telegram_error(message: str, context: Optional[ErrorContext] = None, original_error: Optional[Exception] = None) -> TelegramServiceError:
    """创建Telegram服务错误"""
    return TelegramServiceError(message, context=context, original_error=original_error)


def create_network_timeout_error(operation: str, timeout_seconds: int, context: Optional[ErrorContext] = None) -> NetworkError:
    """创建网络超时错误"""
    message = f"Operation '{operation}' timed out after {timeout_seconds} seconds"
    error = NetworkError(message, context=context, retry_after=timeout_seconds * 2)
    if context:
        context.additional_data.update({
            "timeout_seconds": timeout_seconds,
            "operation": operation
        })
    return error