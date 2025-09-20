"""
统一返回结果类型
定义服务方法的标准返回格式，确保API响应的一致性
"""
from typing import TypeVar, Generic, Optional, List, Dict, Any, Union
from dataclasses import dataclass, field
from .exceptions import ServiceError


T = TypeVar('T')


@dataclass
class ServiceResult(Generic[T]):
    """服务方法统一返回结果"""
    success: bool
    data: Optional[T] = None
    error: Optional[ServiceError] = None
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def success_result(cls, data: T, warnings: Optional[List[str]] = None, metadata: Optional[Dict[str, Any]] = None) -> 'ServiceResult[T]':
        """创建成功结果"""
        return cls(
            success=True,
            data=data,
            warnings=warnings or [],
            metadata=metadata or {}
        )

    @classmethod
    def error_result(cls, error: ServiceError, warnings: Optional[List[str]] = None) -> 'ServiceResult[T]':
        """创建错误结果"""
        return cls(
            success=False,
            error=error,
            warnings=warnings or []
        )

    @classmethod
    def from_exception(cls, exception: Exception, service_name: str, operation_name: str) -> 'ServiceResult[T]':
        """从异常创建错误结果"""
        if isinstance(exception, ServiceError):
            return cls.error_result(exception)
        else:
            # 将普通异常包装为ServiceError
            from .exceptions import SystemError, ErrorContext
            context = ErrorContext(service_name=service_name, operation_name=operation_name)
            error = SystemError(
                message=str(exception),
                context=context,
                original_error=exception
            )
            return cls.error_result(error)

    def add_warning(self, warning: str) -> 'ServiceResult[T]':
        """添加警告信息"""
        self.warnings.append(warning)
        return self

    def add_metadata(self, key: str, value: Any) -> 'ServiceResult[T]':
        """添加元数据"""
        self.metadata[key] = value
        return self

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，用于API响应"""
        result = {
            "success": self.success,
            "data": self.data,
            "warnings": self.warnings,
            "metadata": self.metadata
        }

        if self.error:
            result["error"] = self.error.to_dict()

        return result

    def unwrap(self) -> T:
        """
        获取结果数据，如果是错误结果则抛出异常
        注意：这个方法会改变错误处理的语义，仅在确定需要异常传播时使用
        """
        if not self.success:
            raise self.error or RuntimeError("Unknown error occurred")
        return self.data

    def unwrap_or(self, default: T) -> T:
        """获取结果数据，如果是错误结果则返回默认值"""
        return self.data if self.success else default

    def map(self, func) -> 'ServiceResult':
        """对成功结果的数据应用函数转换"""
        if self.success:
            try:
                new_data = func(self.data)
                return ServiceResult.success_result(new_data, self.warnings, self.metadata)
            except Exception as e:
                from .exceptions import SystemError, ErrorContext
                context = ErrorContext(service_name="mapper", operation_name="map")
                error = SystemError(f"Error during result mapping: {e}", context=context, original_error=e)
                return ServiceResult.error_result(error, self.warnings)
        else:
            return self

    def and_then(self, func) -> 'ServiceResult':
        """链式操作，对成功结果应用返回ServiceResult的函数"""
        if self.success:
            try:
                result = func(self.data)
                if isinstance(result, ServiceResult):
                    # 合并警告和元数据
                    result.warnings.extend(self.warnings)
                    result.metadata.update(self.metadata)
                    return result
                else:
                    raise ValueError("Function must return ServiceResult")
            except Exception as e:
                from .exceptions import SystemError, ErrorContext
                context = ErrorContext(service_name="chain", operation_name="and_then")
                error = SystemError(f"Error during chained operation: {e}", context=context, original_error=e)
                return ServiceResult.error_result(error, self.warnings)
        else:
            return self


@dataclass
class PaginatedResult(Generic[T]):
    """分页结果"""
    items: List[T]
    total_count: int
    page: int
    page_size: int
    has_next: bool
    has_previous: bool

    @property
    def total_pages(self) -> int:
        """总页数"""
        return (self.total_count + self.page_size - 1) // self.page_size


@dataclass
class BatchResult(Generic[T]):
    """批量操作结果"""
    successful_items: List[T] = field(default_factory=list)
    failed_items: List[Dict[str, Any]] = field(default_factory=list)  # 包含item和error信息
    total_processed: int = 0
    success_count: int = 0
    failure_count: int = 0

    def add_success(self, item: T):
        """添加成功项"""
        self.successful_items.append(item)
        self.success_count += 1
        self.total_processed += 1

    def add_failure(self, item: Any, error: ServiceError):
        """添加失败项"""
        self.failed_items.append({
            "item": item,
            "error": error.to_dict()
        })
        self.failure_count += 1
        self.total_processed += 1

    @property
    def success_rate(self) -> float:
        """成功率"""
        return self.success_count / self.total_processed if self.total_processed > 0 else 0.0

    @property
    def is_fully_successful(self) -> bool:
        """是否全部成功"""
        return self.failure_count == 0 and self.success_count > 0

    @property
    def is_partially_successful(self) -> bool:
        """是否部分成功"""
        return self.success_count > 0 and self.failure_count > 0

    @property
    def is_fully_failed(self) -> bool:
        """是否全部失败"""
        return self.success_count == 0 and self.failure_count > 0


@dataclass
class HealthCheckResult:
    """健康检查结果"""
    service_name: str
    is_healthy: bool
    status_message: str
    response_time_ms: Optional[float] = None
    last_checked: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskProgressResult:
    """任务进度结果"""
    task_id: int
    status: str  # pending, running, completed, failed, cancelled
    progress_percentage: float
    current_step: str
    total_steps: int
    completed_steps: int
    estimated_remaining_time: Optional[int] = None  # 秒
    error_message: Optional[str] = None
    result_data: Optional[Dict[str, Any]] = None


# 类型别名，用于常见的结果类型
StringResult = ServiceResult[str]
IntResult = ServiceResult[int]
BoolResult = ServiceResult[bool]
DictResult = ServiceResult[Dict[str, Any]]
ListResult = ServiceResult[List[Any]]

# 空结果类型，用于不返回数据的操作
VoidResult = ServiceResult[None]


def void_success(warnings: Optional[List[str]] = None) -> VoidResult:
    """创建空的成功结果"""
    return ServiceResult.success_result(None, warnings)


def create_success(data: T, message: Optional[str] = None) -> ServiceResult[T]:
    """便捷函数：创建成功结果"""
    metadata = {"message": message} if message else {}
    return ServiceResult.success_result(data, metadata=metadata)


def create_error(error: ServiceError) -> ServiceResult[Any]:
    """便捷函数：创建错误结果"""
    return ServiceResult.error_result(error)


# 结果组合器
class ResultCombiner:
    """结果组合器，用于处理多个ServiceResult"""

    @staticmethod
    def combine_results(*results: ServiceResult) -> ServiceResult[List[Any]]:
        """
        组合多个结果，如果所有结果都成功则返回成功，否则返回第一个错误
        """
        data = []
        all_warnings = []
        all_metadata = {}

        for result in results:
            if not result.success:
                return ServiceResult.error_result(result.error, all_warnings)

            data.append(result.data)
            all_warnings.extend(result.warnings)
            all_metadata.update(result.metadata)

        return ServiceResult.success_result(data, all_warnings, all_metadata)

    @staticmethod
    def combine_partial(*results: ServiceResult) -> BatchResult:
        """
        部分组合多个结果，收集所有成功和失败的结果
        """
        batch_result = BatchResult()

        for i, result in enumerate(results):
            if result.success:
                batch_result.add_success(result.data)
            else:
                batch_result.add_failure(f"result_{i}", result.error)

        return batch_result