"""
统一日志配置模块
提供结构化日志记录和上下文管理
"""
import logging
import logging.handlers
import json
import sys
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from pathlib import Path
from .batch_logging import (
    BatchConfig, HighPerformanceLogger, configure_batch_logging,
    setup_batch_logging_for_logger, get_batch_metrics, BatchLogHandler
)


class JSONFormatter(logging.Formatter):
    """JSON格式的日志格式化器"""

    def __init__(self, include_extra: bool = True):
        super().__init__()
        self.include_extra = include_extra

    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录为JSON"""
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }

        # 添加异常信息
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # 添加额外字段
        if self.include_extra:
            for key, value in record.__dict__.items():
                if key not in {
                    'name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 'filename',
                    'module', 'exc_info', 'exc_text', 'stack_info', 'lineno', 'funcName',
                    'created', 'msecs', 'relativeCreated', 'thread', 'threadName',
                    'processName', 'process', 'getMessage'
                }:
                    log_data[key] = value

        return json.dumps(log_data, ensure_ascii=False, default=str)


class StructuredLogger:
    """结构化日志记录器"""

    def __init__(self, name: str, level: int = logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

    def info(self, message: str, **kwargs):
        """记录INFO级别日志"""
        self.logger.info(message, extra=kwargs)

    def warning(self, message: str, **kwargs):
        """记录WARNING级别日志"""
        self.logger.warning(message, extra=kwargs)

    def error(self, message: str, **kwargs):
        """记录ERROR级别日志"""
        self.logger.error(message, extra=kwargs)

    def debug(self, message: str, **kwargs):
        """记录DEBUG级别日志"""
        self.logger.debug(message, extra=kwargs)

    def critical(self, message: str, **kwargs):
        """记录CRITICAL级别日志"""
        self.logger.critical(message, extra=kwargs)


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    max_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    console_output: bool = True,
    json_format: bool = True,
    enable_file_logging: bool = True,
    enable_batch_logging: bool = True,
    batch_size: int = 100,
    flush_interval: float = 5.0,
    max_buffer_size: int = 10000
) -> None:
    """
    设置统一的日志配置

    Args:
        log_level: 日志级别
        log_file: 日志文件路径
        max_file_size: 单个日志文件最大大小
        backup_count: 日志文件备份数量
        console_output: 是否输出到控制台
        json_format: 是否使用JSON格式
        enable_file_logging: 是否启用文件日志
    """
    # 转换日志级别
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # 获取根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # 清除现有处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 创建格式化器
    if json_format:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    # 控制台处理器
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(numeric_level)
        root_logger.addHandler(console_handler)

    # 文件处理器选择
    if enable_file_logging and log_file:
        # 确保日志目录存在
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        if enable_batch_logging:
            # 配置批处理日志
            configure_batch_logging(
                batch_size=batch_size,
                flush_interval=flush_interval,
                max_buffer_size=max_buffer_size,
                enable_metrics=True,
                enable_debug=log_level.upper() == "DEBUG"
            )

            # 使用批处理处理器
            batch_handler = BatchLogHandler("default")
            batch_handler.setLevel(numeric_level)
            root_logger.addHandler(batch_handler)
        else:
            # 使用传统RotatingFileHandler
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=max_file_size,
                backupCount=backup_count,
                encoding='utf-8'
            )
            file_handler.setFormatter(formatter)
            file_handler.setLevel(numeric_level)
            root_logger.addHandler(file_handler)

    # 设置第三方库的日志级别
    logging.getLogger("telethon").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)


class LogContext:
    """日志上下文管理器"""

    def __init__(self):
        self._context: Dict[str, Any] = {}

    def set(self, key: str, value: Any):
        """设置上下文值"""
        self._context[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """获取上下文值"""
        return self._context.get(key, default)

    def clear(self):
        """清空上下文"""
        self._context.clear()

    def update(self, **kwargs):
        """批量更新上下文"""
        self._context.update(kwargs)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self._context.copy()


# 全局日志上下文
_log_context = LogContext()


class ContextFilter(logging.Filter):
    """上下文过滤器，自动添加上下文信息到日志记录"""

    def filter(self, record: logging.LogRecord) -> bool:
        """添加上下文信息到日志记录"""
        # 添加全局上下文
        for key, value in _log_context.to_dict().items():
            if not hasattr(record, key):
                setattr(record, key, value)

        return True


def get_logger(name: str, use_batch: bool = True) -> StructuredLogger:
    """获取结构化日志记录器"""
    if use_batch:
        # 使用高性能批处理日志记录器
        return HighPerformanceLogger(name)
    else:
        # 使用传统结构化日志记录器
        logger = StructuredLogger(name)

        # 添加上下文过滤器
        context_filter = ContextFilter()
        logger.logger.addFilter(context_filter)

        return logger


def set_log_context(**kwargs):
    """设置日志上下文"""
    _log_context.update(**kwargs)


def clear_log_context():
    """清空日志上下文"""
    _log_context.clear()


def get_log_context() -> Dict[str, Any]:
    """获取当前日志上下文"""
    return _log_context.to_dict()


class ServiceLoggerMixin:
    """服务日志记录器混合类"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._service_logger = get_logger(self.__class__.__name__)

    def log_operation_start(self, operation: str, **context):
        """记录操作开始"""
        self._service_logger.info(
            f"Starting operation: {operation}",
            operation=operation,
            service=self.__class__.__name__,
            **context
        )

    def log_operation_success(self, operation: str, duration_ms: Optional[float] = None, **context):
        """记录操作成功"""
        log_data = {
            "operation": operation,
            "service": self.__class__.__name__,
            "status": "success",
            **context
        }
        if duration_ms is not None:
            log_data["duration_ms"] = duration_ms

        self._service_logger.info(f"Operation completed: {operation}", **log_data)

    def log_operation_error(self, operation: str, error: Exception, **context):
        """记录操作错误"""
        self._service_logger.error(
            f"Operation failed: {operation}",
            operation=operation,
            service=self.__class__.__name__,
            status="error",
            error_type=type(error).__name__,
            error_message=str(error),
            **context
        )

    def log_operation_warning(self, operation: str, warning: str, **context):
        """记录操作警告"""
        self._service_logger.warning(
            f"Operation warning: {operation}",
            operation=operation,
            service=self.__class__.__name__,
            status="warning",
            warning_message=warning,
            **context
        )


# 性能日志记录器
class PerformanceLogger:
    """性能监控日志记录器"""

    def __init__(self, name: str = "performance"):
        self.logger = get_logger(name)

    def log_timing(self, operation: str, duration_ms: float, **context):
        """记录操作耗时"""
        self.logger.info(
            f"Performance: {operation}",
            operation=operation,
            duration_ms=duration_ms,
            **context
        )

    def log_slow_operation(self, operation: str, duration_ms: float, threshold_ms: float, **context):
        """记录慢操作"""
        self.logger.warning(
            f"Slow operation detected: {operation}",
            operation=operation,
            duration_ms=duration_ms,
            threshold_ms=threshold_ms,
            slowness_ratio=duration_ms / threshold_ms,
            **context
        )

    def log_resource_usage(self, operation: str, **resource_metrics):
        """记录资源使用情况"""
        self.logger.info(
            f"Resource usage: {operation}",
            operation=operation,
            **resource_metrics
        )


# 审计日志记录器
class AuditLogger:
    """审计日志记录器"""

    def __init__(self, name: str = "audit"):
        self.logger = get_logger(name)

    def log_user_action(self, user_id: str, action: str, resource: str, **context):
        """记录用户操作"""
        self.logger.info(
            f"User action: {action}",
            user_id=user_id,
            action=action,
            resource=resource,
            **context
        )

    def log_system_event(self, event_type: str, description: str, **context):
        """记录系统事件"""
        self.logger.info(
            f"System event: {event_type}",
            event_type=event_type,
            description=description,
            **context
        )

    def log_security_event(self, event_type: str, severity: str, description: str, **context):
        """记录安全事件"""
        self.logger.warning(
            f"Security event: {event_type}",
            event_type=event_type,
            severity=severity,
            description=description,
            **context
        )


# 全局日志记录器实例
performance_logger = PerformanceLogger()
audit_logger = AuditLogger()


def configure_service_logging():
    """配置服务日志记录"""
    from ..config import settings

    # 获取配置
    log_level = getattr(settings, 'log_level', 'INFO')
    log_file = getattr(settings, 'log_file', './logs/app.log')

    # 获取批处理配置
    batch_enabled = getattr(settings, 'enable_batch_logging', True)
    batch_size = getattr(settings, 'log_batch_size', 100)
    flush_interval = getattr(settings, 'log_flush_interval', 5.0)
    max_buffer_size = getattr(settings, 'log_max_buffer_size', 10000)

    # 设置日志
    setup_logging(
        log_level=log_level,
        log_file=log_file,
        console_output=True,
        json_format=True,
        enable_file_logging=True,
        enable_batch_logging=batch_enabled,
        batch_size=batch_size,
        flush_interval=flush_interval,
        max_buffer_size=max_buffer_size
    )

    # 设置全局上下文
    set_log_context(
        application="TgGod",
        environment=getattr(settings, 'environment', 'development')
    )

    print(f"服务日志配置完成 - 批处理: {batch_enabled}, 批次大小: {batch_size}")