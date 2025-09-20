"""
TgGod 核心模块
统一的错误处理、日志记录和结果类型
"""
from .exceptions import (
    ServiceError, BusinessError, ValidationError, AuthenticationError,
    SystemError, ExternalServiceError, ConfigurationError, NetworkError,
    DatabaseError, FileSystemError, TelegramServiceError, MediaDownloadError,
    TaskExecutionError, FileOrganizationError, ErrorContext, ErrorCategory,
    ErrorSeverity, create_validation_error, create_config_error,
    create_telegram_error, create_network_timeout_error
)

from .result_types import (
    ServiceResult, PaginatedResult, BatchResult, HealthCheckResult,
    TaskProgressResult, StringResult, IntResult, BoolResult, DictResult,
    ListResult, VoidResult, void_success, create_success, create_error,
    ResultCombiner
)

from .decorators import (
    handle_service_errors, retry_on_failure, circuit_breaker, timeout,
    performance_monitor, robust_service_method, RetryConfig,
    CircuitBreakerConfig
)

from .error_handler import (
    ErrorHandler, ErrorLogger, ErrorMetrics, global_error_handler,
    log_error, log_success, create_error_context, operation_context,
    LegacyErrorAdapter
)

from .logging_config import (
    setup_logging, get_logger, set_log_context, clear_log_context,
    get_log_context, ServiceLoggerMixin, PerformanceLogger, AuditLogger,
    performance_logger, audit_logger, configure_service_logging
)

__all__ = [
    # 异常类
    "ServiceError", "BusinessError", "ValidationError", "AuthenticationError",
    "SystemError", "ExternalServiceError", "ConfigurationError", "NetworkError",
    "DatabaseError", "FileSystemError", "TelegramServiceError", "MediaDownloadError",
    "TaskExecutionError", "FileOrganizationError", "ErrorContext", "ErrorCategory",
    "ErrorSeverity",

    # 异常工厂函数
    "create_validation_error", "create_config_error", "create_telegram_error",
    "create_network_timeout_error",

    # 结果类型
    "ServiceResult", "PaginatedResult", "BatchResult", "HealthCheckResult",
    "TaskProgressResult", "StringResult", "IntResult", "BoolResult", "DictResult",
    "ListResult", "VoidResult", "ResultCombiner",

    # 结果工厂函数
    "void_success", "create_success", "create_error",

    # 装饰器
    "handle_service_errors", "retry_on_failure", "circuit_breaker", "timeout",
    "performance_monitor", "robust_service_method", "RetryConfig",
    "CircuitBreakerConfig",

    # 错误处理器
    "ErrorHandler", "ErrorLogger", "ErrorMetrics", "global_error_handler",
    "LegacyErrorAdapter",

    # 错误处理便捷函数
    "log_error", "log_success", "create_error_context", "operation_context",

    # 日志系统
    "setup_logging", "get_logger", "set_log_context", "clear_log_context",
    "get_log_context", "ServiceLoggerMixin", "PerformanceLogger", "AuditLogger",
    "performance_logger", "audit_logger", "configure_service_logging"
]