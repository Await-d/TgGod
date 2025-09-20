"""
错误处理核心模块
提供统一的错误处理、日志记录和监控功能
"""
import logging
import traceback
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timezone
from contextlib import contextmanager

from .exceptions import ServiceError, ErrorContext, ErrorSeverity
from .result_types import ServiceResult


class ErrorLogger:
    """统一错误日志记录器"""

    def __init__(self, logger_name: str = __name__):
        self.logger = logging.getLogger(logger_name)
        self.sensitive_fields = {"password", "token", "secret", "key", "auth", "credential"}

    def _sanitize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """清理敏感数据"""
        if not isinstance(data, dict):
            return data

        sanitized = {}
        for key, value in data.items():
            key_lower = key.lower()
            if any(sensitive in key_lower for sensitive in self.sensitive_fields):
                sanitized[key] = "***REDACTED***"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_data(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    self._sanitize_data(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                sanitized[key] = value
        return sanitized

    def log_error(self, error: ServiceError, additional_context: Optional[Dict[str, Any]] = None):
        """记录错误日志"""
        log_data = error.to_dict()

        # 添加额外上下文
        if additional_context:
            log_data.setdefault("additional_context", {}).update(
                self._sanitize_data(additional_context)
            )

        # 添加堆栈信息
        if error.original_error:
            log_data["stack_trace"] = traceback.format_exception(
                type(error.original_error),
                error.original_error,
                error.original_error.__traceback__
            )

        # 根据严重程度选择日志级别
        if error.severity == ErrorSeverity.CRITICAL:
            self.logger.critical("Critical service error", extra=log_data)
        elif error.severity == ErrorSeverity.HIGH:
            self.logger.error("High severity service error", extra=log_data)
        elif error.severity == ErrorSeverity.MEDIUM:
            self.logger.warning("Medium severity service error", extra=log_data)
        else:
            self.logger.info("Low severity service error", extra=log_data)

    def log_operation_start(self, service_name: str, operation_name: str, context: Dict[str, Any]):
        """记录操作开始"""
        sanitized_context = self._sanitize_data(context)
        self.logger.info(
            f"Starting operation: {service_name}.{operation_name}",
            extra={
                "service_name": service_name,
                "operation_name": operation_name,
                "context": sanitized_context,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )

    def log_operation_success(self, service_name: str, operation_name: str, duration_ms: float, result_summary: Optional[str] = None):
        """记录操作成功"""
        self.logger.info(
            f"Operation completed successfully: {service_name}.{operation_name}",
            extra={
                "service_name": service_name,
                "operation_name": operation_name,
                "duration_ms": duration_ms,
                "result_summary": result_summary,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )

    def log_operation_warning(self, service_name: str, operation_name: str, warning_message: str):
        """记录操作警告"""
        self.logger.warning(
            f"Operation warning: {service_name}.{operation_name}: {warning_message}",
            extra={
                "service_name": service_name,
                "operation_name": operation_name,
                "warning_message": warning_message,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )


class ErrorMetrics:
    """错误指标收集器"""

    def __init__(self):
        self.error_counts: Dict[str, int] = {}
        self.error_rates: Dict[str, List[datetime]] = {}
        self.service_health: Dict[str, bool] = {}

    def record_error(self, service_name: str, operation_name: str, error: ServiceError):
        """记录错误指标"""
        key = f"{service_name}.{operation_name}"
        error_type = error.category.value

        # 计数
        count_key = f"{key}.{error_type}"
        self.error_counts[count_key] = self.error_counts.get(count_key, 0) + 1

        # 记录时间（用于计算错误率）
        if key not in self.error_rates:
            self.error_rates[key] = []
        self.error_rates[key].append(datetime.now(timezone.utc))

        # 保留最近1小时的记录
        one_hour_ago = datetime.now(timezone.utc).timestamp() - 3600
        self.error_rates[key] = [
            ts for ts in self.error_rates[key]
            if ts.timestamp() > one_hour_ago
        ]

        # 更新服务健康状态
        self._update_service_health(service_name)

    def record_success(self, service_name: str, operation_name: str):
        """记录成功指标"""
        self._update_service_health(service_name)

    def _update_service_health(self, service_name: str):
        """更新服务健康状态"""
        # 简单的健康检查：如果最近5分钟内错误率超过50%，标记为不健康
        five_minutes_ago = datetime.now(timezone.utc).timestamp() - 300
        recent_errors = sum(
            len([ts for ts in timestamps if ts.timestamp() > five_minutes_ago])
            for key, timestamps in self.error_rates.items()
            if key.startswith(service_name)
        )

        # 这里需要更复杂的逻辑来确定健康状态
        # 简化版本：如果最近5分钟内有超过10个错误，标记为不健康
        self.service_health[service_name] = recent_errors < 10

    def get_error_summary(self) -> Dict[str, Any]:
        """获取错误摘要"""
        return {
            "total_errors": sum(self.error_counts.values()),
            "error_counts_by_type": self.error_counts.copy(),
            "service_health": self.service_health.copy(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


class ErrorHandler:
    """统一错误处理器"""

    def __init__(self):
        self.logger = ErrorLogger()
        self.metrics = ErrorMetrics()
        self.error_callbacks: List[Callable[[ServiceError], None]] = []

    def add_error_callback(self, callback: Callable[[ServiceError], None]):
        """添加错误回调函数"""
        self.error_callbacks.append(callback)

    def handle_error(
        self,
        error: ServiceError,
        service_name: str,
        operation_name: str,
        additional_context: Optional[Dict[str, Any]] = None
    ):
        """处理错误"""
        # 更新错误上下文
        if error.context.service_name == "unknown":
            error.context.service_name = service_name
        if error.context.operation_name == "unknown":
            error.context.operation_name = operation_name

        # 记录日志
        self.logger.log_error(error, additional_context)

        # 记录指标
        self.metrics.record_error(service_name, operation_name, error)

        # 执行回调
        for callback in self.error_callbacks:
            try:
                callback(error)
            except Exception as e:
                self.logger.logger.error(f"Error in error callback: {e}")

    def handle_success(self, service_name: str, operation_name: str, duration_ms: float, result_summary: Optional[str] = None):
        """处理成功操作"""
        self.logger.log_operation_success(service_name, operation_name, duration_ms, result_summary)
        self.metrics.record_success(service_name, operation_name)

    def create_context(
        self,
        service_name: str,
        operation_name: str,
        user_id: Optional[str] = None,
        task_id: Optional[int] = None,
        request_id: Optional[str] = None,
        **additional_data
    ) -> ErrorContext:
        """创建错误上下文"""
        return ErrorContext(
            service_name=service_name,
            operation_name=operation_name,
            user_id=user_id,
            task_id=task_id,
            request_id=request_id,
            additional_data=additional_data
        )

    @contextmanager
    def operation_context(
        self,
        service_name: str,
        operation_name: str,
        log_start: bool = True,
        **context_data
    ):
        """操作上下文管理器"""
        start_time = datetime.now(timezone.utc)

        if log_start:
            self.logger.log_operation_start(service_name, operation_name, context_data)

        try:
            yield self.create_context(service_name, operation_name, **context_data)

            # 操作成功
            duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            self.handle_success(service_name, operation_name, duration_ms)

        except ServiceError as e:
            self.handle_error(e, service_name, operation_name, context_data)
            raise
        except Exception as e:
            # 包装普通异常
            from .exceptions import SystemError
            context = self.create_context(service_name, operation_name, **context_data)
            error = SystemError(
                message=f"Unexpected error in {operation_name}: {str(e)}",
                context=context,
                original_error=e
            )
            self.handle_error(error, service_name, operation_name, context_data)
            raise error

    def get_health_status(self) -> Dict[str, Any]:
        """获取健康状态"""
        return {
            "overall_health": all(self.metrics.service_health.values()),
            "service_health": self.metrics.service_health,
            "error_summary": self.metrics.get_error_summary(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# 全局错误处理器实例
global_error_handler = ErrorHandler()


# 便捷函数
def log_error(error: ServiceError, service_name: str, operation_name: str, **context):
    """记录错误的便捷函数"""
    global_error_handler.handle_error(error, service_name, operation_name, context)


def log_success(service_name: str, operation_name: str, duration_ms: float, result_summary: Optional[str] = None):
    """记录成功的便捷函数"""
    global_error_handler.handle_success(service_name, operation_name, duration_ms, result_summary)


def create_error_context(service_name: str, operation_name: str, **kwargs) -> ErrorContext:
    """创建错误上下文的便捷函数"""
    return global_error_handler.create_context(service_name, operation_name, **kwargs)


def operation_context(service_name: str, operation_name: str, **kwargs):
    """操作上下文的便捷函数"""
    return global_error_handler.operation_context(service_name, operation_name, **kwargs)


# 兼容性适配器
class LegacyErrorAdapter:
    """用于保持向后兼容性的错误适配器"""

    @staticmethod
    def convert_result_to_legacy(result: ServiceResult, legacy_format: str = "bool") -> Any:
        """将ServiceResult转换为传统格式"""
        if legacy_format == "bool":
            return result.success
        elif legacy_format == "data_or_none":
            return result.data if result.success else None
        elif legacy_format == "dict":
            if result.success:
                return {"success": True, "data": result.data}
            else:
                return {"success": False, "error": str(result.error)}
        else:
            return result

    @staticmethod
    def convert_legacy_to_result(value: Any, service_name: str, operation_name: str) -> ServiceResult:
        """将传统返回值转换为ServiceResult"""
        if isinstance(value, ServiceResult):
            return value
        elif isinstance(value, bool):
            if value:
                return ServiceResult.success_result(value)
            else:
                from .exceptions import SystemError
                context = create_error_context(service_name, operation_name)
                error = SystemError(f"Operation {operation_name} failed", context=context)
                return ServiceResult.error_result(error)
        elif isinstance(value, dict) and "success" in value:
            if value["success"]:
                return ServiceResult.success_result(value.get("data"))
            else:
                from .exceptions import SystemError
                context = create_error_context(service_name, operation_name)
                error = SystemError(value.get("error", "Unknown error"), context=context)
                return ServiceResult.error_result(error)
        else:
            return ServiceResult.success_result(value)