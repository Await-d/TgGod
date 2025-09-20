"""
错误处理装饰器
提供统一的错误处理、重试、熔断等功能装饰器
"""
import asyncio
import functools
import logging
import time
import random
from typing import Optional, Callable, Type, Union, List, Dict, Any
from dataclasses import dataclass, field

from .exceptions import (
    ServiceError, NetworkError, ExternalServiceError, SystemError,
    ErrorContext, ErrorSeverity
)
from .result_types import ServiceResult


logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """重试配置"""
    max_attempts: int = 3
    base_delay: float = 1.0  # 基础延迟（秒）
    max_delay: float = 60.0  # 最大延迟（秒）
    exponential_base: float = 2.0  # 指数退避的底数
    jitter: bool = True  # 是否添加随机抖动
    retryable_exceptions: List[Type[Exception]] = field(default_factory=lambda: [
        NetworkError, ExternalServiceError, SystemError
    ])

    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """判断是否应该重试"""
        if attempt >= self.max_attempts:
            return False

        # 检查异常类型
        if not any(isinstance(exception, exc_type) for exc_type in self.retryable_exceptions):
            return False

        # 如果是ServiceError，检查是否可重试
        if isinstance(exception, ServiceError):
            return exception.is_retryable()

        return True

    def calculate_delay(self, attempt: int) -> float:
        """计算重试延迟"""
        delay = self.base_delay * (self.exponential_base ** (attempt - 1))
        delay = min(delay, self.max_delay)

        if self.jitter:
            # 添加20%的随机抖动
            jitter_amount = delay * 0.2
            delay += random.uniform(-jitter_amount, jitter_amount)

        return max(0, delay)


@dataclass
class CircuitBreakerConfig:
    """熔断器配置"""
    failure_threshold: int = 5  # 失败阈值
    recovery_timeout: float = 60.0  # 恢复超时时间（秒）
    expected_exception: Type[Exception] = Exception


class CircuitBreakerState:
    """熔断器状态"""
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def can_execute(self) -> bool:
        """判断是否可以执行"""
        if self.state == "CLOSED":
            return True
        elif self.state == "OPEN":
            if time.time() - self.last_failure_time > self.config.recovery_timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        else:  # HALF_OPEN
            return True

    def record_success(self):
        """记录成功"""
        self.failure_count = 0
        self.state = "CLOSED"

    def record_failure(self):
        """记录失败"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.config.failure_threshold:
            self.state = "OPEN"


# 全局熔断器状态存储
_circuit_breakers: Dict[str, CircuitBreakerState] = {}


def handle_service_errors(
    service_name: str,
    operation_name: str,
    return_result_type: bool = True,
    log_errors: bool = True
):
    """
    统一服务错误处理装饰器

    Args:
        service_name: 服务名称
        operation_name: 操作名称
        return_result_type: 是否返回ServiceResult类型（False则重新抛出异常）
        log_errors: 是否记录错误日志
    """
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            context = ErrorContext(
                service_name=service_name,
                operation_name=operation_name
            )

            try:
                result = await func(*args, **kwargs)

                # 如果函数已经返回ServiceResult，直接返回
                if isinstance(result, ServiceResult):
                    return result
                elif return_result_type:
                    return ServiceResult.success_result(result)
                else:
                    return result

            except ServiceError as e:
                # 更新错误上下文
                if e.context.service_name == "unknown":
                    e.context = context

                if log_errors:
                    logger.error(
                        f"Service error in {service_name}.{operation_name}: {e.message}",
                        extra=e.to_dict()
                    )

                if return_result_type:
                    return ServiceResult.error_result(e)
                else:
                    raise

            except Exception as e:
                # 包装普通异常为ServiceError
                error = SystemError(
                    message=f"Unexpected error in {operation_name}: {str(e)}",
                    context=context,
                    original_error=e
                )

                if log_errors:
                    logger.error(
                        f"Unexpected error in {service_name}.{operation_name}: {str(e)}",
                        extra=error.to_dict(),
                        exc_info=True
                    )

                if return_result_type:
                    return ServiceResult.error_result(error)
                else:
                    raise error

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            context = ErrorContext(
                service_name=service_name,
                operation_name=operation_name
            )

            try:
                result = func(*args, **kwargs)

                if isinstance(result, ServiceResult):
                    return result
                elif return_result_type:
                    return ServiceResult.success_result(result)
                else:
                    return result

            except ServiceError as e:
                if e.context.service_name == "unknown":
                    e.context = context

                if log_errors:
                    logger.error(
                        f"Service error in {service_name}.{operation_name}: {e.message}",
                        extra=e.to_dict()
                    )

                if return_result_type:
                    return ServiceResult.error_result(e)
                else:
                    raise

            except Exception as e:
                error = SystemError(
                    message=f"Unexpected error in {operation_name}: {str(e)}",
                    context=context,
                    original_error=e
                )

                if log_errors:
                    logger.error(
                        f"Unexpected error in {service_name}.{operation_name}: {str(e)}",
                        extra=error.to_dict(),
                        exc_info=True
                    )

                if return_result_type:
                    return ServiceResult.error_result(error)
                else:
                    raise error

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def retry_on_failure(config: Optional[RetryConfig] = None):
    """
    重试装饰器

    Args:
        config: 重试配置，如果为None则使用默认配置
    """
    retry_config = config or RetryConfig()

    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(1, retry_config.max_attempts + 1):
                try:
                    result = await func(*args, **kwargs)

                    # 如果前面有失败，记录重试成功
                    if attempt > 1:
                        logger.info(
                            f"Retry successful for {func.__name__} on attempt {attempt}"
                        )

                    return result

                except Exception as e:
                    last_exception = e

                    if not retry_config.should_retry(e, attempt):
                        logger.error(
                            f"Max retries exceeded or non-retryable error for {func.__name__}: {e}"
                        )
                        raise

                    if attempt < retry_config.max_attempts:
                        delay = retry_config.calculate_delay(attempt)
                        logger.warning(
                            f"Attempt {attempt} failed for {func.__name__}: {e}. "
                            f"Retrying in {delay:.2f} seconds..."
                        )
                        await asyncio.sleep(delay)

            # 如果所有重试都失败了
            logger.error(f"All retry attempts failed for {func.__name__}")
            raise last_exception

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(1, retry_config.max_attempts + 1):
                try:
                    result = func(*args, **kwargs)

                    if attempt > 1:
                        logger.info(
                            f"Retry successful for {func.__name__} on attempt {attempt}"
                        )

                    return result

                except Exception as e:
                    last_exception = e

                    if not retry_config.should_retry(e, attempt):
                        logger.error(
                            f"Max retries exceeded or non-retryable error for {func.__name__}: {e}"
                        )
                        raise

                    if attempt < retry_config.max_attempts:
                        delay = retry_config.calculate_delay(attempt)
                        logger.warning(
                            f"Attempt {attempt} failed for {func.__name__}: {e}. "
                            f"Retrying in {delay:.2f} seconds..."
                        )
                        time.sleep(delay)

            logger.error(f"All retry attempts failed for {func.__name__}")
            raise last_exception

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def circuit_breaker(
    name: str,
    config: Optional[CircuitBreakerConfig] = None
):
    """
    熔断器装饰器

    Args:
        name: 熔断器名称，用于标识不同的熔断器
        config: 熔断器配置
    """
    breaker_config = config or CircuitBreakerConfig()

    def decorator(func):
        # 确保熔断器状态存在
        if name not in _circuit_breakers:
            _circuit_breakers[name] = CircuitBreakerState(breaker_config)

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            breaker = _circuit_breakers[name]

            if not breaker.can_execute():
                error_msg = f"Circuit breaker '{name}' is OPEN. Service temporarily unavailable."
                logger.warning(error_msg)
                raise ExternalServiceError(
                    message=error_msg,
                    service_name=name,
                    suggested_action="Wait for circuit breaker to recover"
                )

            try:
                result = await func(*args, **kwargs)
                breaker.record_success()
                return result

            except breaker_config.expected_exception as e:
                breaker.record_failure()
                logger.warning(f"Circuit breaker '{name}' recorded failure: {e}")
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            breaker = _circuit_breakers[name]

            if not breaker.can_execute():
                error_msg = f"Circuit breaker '{name}' is OPEN. Service temporarily unavailable."
                logger.warning(error_msg)
                raise ExternalServiceError(
                    message=error_msg,
                    service_name=name,
                    suggested_action="Wait for circuit breaker to recover"
                )

            try:
                result = func(*args, **kwargs)
                breaker.record_success()
                return result

            except breaker_config.expected_exception as e:
                breaker.record_failure()
                logger.warning(f"Circuit breaker '{name}' recorded failure: {e}")
                raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def timeout(seconds: float):
    """
    超时装饰器

    Args:
        seconds: 超时时间（秒）
    """
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
            except asyncio.TimeoutError:
                from .exceptions import create_network_timeout_error, ErrorContext
                context = ErrorContext(
                    service_name=getattr(func, '__module__', 'unknown'),
                    operation_name=func.__name__
                )
                raise create_network_timeout_error(func.__name__, int(seconds), context)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # 对于同步函数，无法实现真正的超时，只能记录警告
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time
                if elapsed > seconds:
                    logger.warning(
                        f"Function {func.__name__} took {elapsed:.2f}s, "
                        f"longer than expected timeout {seconds}s"
                    )
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                if elapsed > seconds:
                    logger.warning(
                        f"Function {func.__name__} failed after {elapsed:.2f}s, "
                        f"longer than expected timeout {seconds}s"
                    )
                raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def performance_monitor(log_slow_calls: bool = True, slow_threshold: float = 1.0):
    """
    性能监控装饰器

    Args:
        log_slow_calls: 是否记录慢调用
        slow_threshold: 慢调用阈值（秒）
    """
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                elapsed = time.time() - start_time

                if log_slow_calls and elapsed > slow_threshold:
                    logger.warning(
                        f"Slow call detected: {func.__name__} took {elapsed:.2f}s"
                    )

                # 可以在这里添加性能指标收集
                logger.debug(f"{func.__name__} completed in {elapsed:.3f}s")

                return result
            except Exception as e:
                elapsed = time.time() - start_time
                logger.debug(f"{func.__name__} failed after {elapsed:.3f}s: {e}")
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time

                if log_slow_calls and elapsed > slow_threshold:
                    logger.warning(
                        f"Slow call detected: {func.__name__} took {elapsed:.2f}s"
                    )

                logger.debug(f"{func.__name__} completed in {elapsed:.3f}s")
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                logger.debug(f"{func.__name__} failed after {elapsed:.3f}s: {e}")
                raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# 组合装饰器，用于常见的组合场景
def robust_service_method(
    service_name: str,
    operation_name: str,
    retry_config: Optional[RetryConfig] = None,
    timeout_seconds: Optional[float] = None,
    circuit_breaker_name: Optional[str] = None
):
    """
    组合装饰器，提供完整的错误处理、重试、超时、熔断功能

    Args:
        service_name: 服务名称
        operation_name: 操作名称
        retry_config: 重试配置
        timeout_seconds: 超时时间
        circuit_breaker_name: 熔断器名称
    """
    def decorator(func):
        # 应用装饰器的顺序很重要
        result_func = func

        # 1. 最内层：错误处理
        result_func = handle_service_errors(service_name, operation_name)(result_func)

        # 2. 性能监控
        result_func = performance_monitor()(result_func)

        # 3. 重试机制
        if retry_config:
            result_func = retry_on_failure(retry_config)(result_func)

        # 4. 超时控制
        if timeout_seconds:
            result_func = timeout(timeout_seconds)(result_func)

        # 5. 最外层：熔断器
        if circuit_breaker_name:
            result_func = circuit_breaker(circuit_breaker_name)(result_func)

        return result_func

    return decorator