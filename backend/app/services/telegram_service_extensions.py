"""
Telegram服务扩展模块 - 加固增强功能

这个模块包含Telegram服务的高级功能和监控扩展，
包括自动重连、健康监控、会话管理等加固功能。
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, Any

from .telegram_service import TelegramService, high_perf_logger
from ..core.memory_manager import memory_manager
from ..websocket.manager import websocket_manager


async def add_telegram_monitoring_methods(service: TelegramService):
    """为Telegram服务添加监控方法"""

    async def _auto_reconnect_loop(self):
        """自动重连循环"""
        while not self._shutdown_requested:
            try:
                await asyncio.sleep(self.config.health_check_interval)

                if not self._connected or not self.client or not self.client.is_connected():
                    high_perf_logger.warning("检测到连接丢失，尝试重连")
                    await self._attempt_reconnection()

            except Exception as e:
                high_perf_logger.error(f"自动重连循环错误: {e}")

    async def _attempt_reconnection(self):
        """尝试重连"""
        try:
            high_perf_logger.info("开始自动重连")

            # 断开旧连接
            await self._safe_disconnect()

            # 重新连接
            await self._create_and_connect_client()

            self.health_metrics.auto_reconnects += 1
            high_perf_logger.info("自动重连成功")

            return True

        except Exception as e:
            high_perf_logger.error(f"自动重连失败: {e}")
            return False

    async def _health_check_loop(self):
        """健康检查循环"""
        while not self._shutdown_requested:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                await self._perform_health_check()
                self._last_health_check = time.time()
            except Exception as e:
                high_perf_logger.error(f"健康检查错误: {e}")

    async def _perform_health_check(self) -> Dict[str, Any]:
        """执行健康检查"""
        issues = []
        healthy = True

        try:
            # 检查客户端连接
            if not self._connected or not self.client:
                issues.append("客户端未连接")
                healthy = False
            elif not self.client.is_connected():
                issues.append("客户端连接已断开")
                healthy = False

            # 检查认证状态
            if not self._authenticated:
                issues.append("未认证")

            # 检查熔断器状态
            if self._circuit_breaker_open:
                issues.append("熔断器已打开")
                healthy = False

            # 检查内存使用
            memory_usage = memory_manager.monitor._get_memory_usage()
            if memory_usage['percent'] > 90:
                issues.append(f"内存使用过高: {memory_usage['percent']:.1f}%")

            return {
                'healthy': healthy,
                'issues': issues,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            high_perf_logger.error(f"健康检查执行失败: {e}")
            return {
                'healthy': False,
                'issues': [f"健康检查失败: {str(e)}"],
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

    async def _session_refresh_loop(self):
        """会话刷新循环"""
        while not self._shutdown_requested:
            try:
                await asyncio.sleep(self.config.session_refresh_interval)

                if self._connected and self.client:
                    # 执行轻量API调用来保持会话活跃
                    try:
                        await self.client.get_me()
                        self._last_session_refresh = time.time()
                        high_perf_logger.debug("会话刷新成功")
                    except Exception as e:
                        high_perf_logger.warning(f"会话刷新失败: {e}")

            except Exception as e:
                high_perf_logger.error(f"会话刷新循环错误: {e}")

    def get_service_health(self) -> Dict[str, Any]:
        """获取服务健康状态"""
        return {
            "healthy": self._connected and self._authenticated and not self._circuit_breaker_open,
            "connected": self._connected,
            "authenticated": self._authenticated,
            "circuit_breaker_open": self._circuit_breaker_open,
            "failure_count": self._failure_count,
            "uptime_seconds": time.time() - self._startup_time,
            "metrics": {
                "connection_attempts": self.health_metrics.connection_attempts,
                "successful_connections": self.health_metrics.successful_connections,
                "failed_connections": self.health_metrics.failed_connections,
                "flood_waits": self.health_metrics.flood_waits,
                "circuit_breaker_trips": self.health_metrics.circuit_breaker_trips,
                "auto_reconnects": self.health_metrics.auto_reconnects,
                "messages_synced": self.health_metrics.messages_synced,
                "api_calls_made": self.health_metrics.api_calls_made
            },
            "last_successful_call": self.health_metrics.last_successful_call.isoformat() if self.health_metrics.last_successful_call else None,
            "session_start_time": self.health_metrics.session_start_time.isoformat() if self.health_metrics.session_start_time else None
        }

    async def get_detailed_health_report(self) -> Dict[str, Any]:
        """获取详细健康报告"""
        base_health = self.get_service_health()

        # 添加内存信息
        memory_stats = memory_manager.get_stats()
        base_health["memory"] = memory_stats

        # 添加连接检查
        if self.client:
            base_health["connection_status"] = {
                "is_connected": self.client.is_connected(),
                "is_user_authorized": await self._safe_check_auth(),
                "session_file_exists": os.path.exists(f"{self.session_name}.session")
            }

        return base_health

    async def _safe_check_auth(self) -> bool:
        """安全检查认证状态"""
        try:
            if self.client and self.client.is_connected():
                return await self.client.is_user_authorized()
            return False
        except Exception:
            return False

    def is_authenticated(self) -> bool:
        """检查认证状态"""
        return self._authenticated

    def is_connected(self) -> bool:
        """检查连接状态"""
        return self._connected and self.client and self.client.is_connected()

    # 绑定方法到服务实例
    service._auto_reconnect_loop = _auto_reconnect_loop.__get__(service, TelegramService)
    service._attempt_reconnection = _attempt_reconnection.__get__(service, TelegramService)
    service._health_check_loop = _health_check_loop.__get__(service, TelegramService)
    service._perform_health_check = _perform_health_check.__get__(service, TelegramService)
    service._session_refresh_loop = _session_refresh_loop.__get__(service, TelegramService)
    service.get_service_health = get_service_health.__get__(service, TelegramService)
    service.get_detailed_health_report = get_detailed_health_report.__get__(service, TelegramService)
    service._safe_check_auth = _safe_check_auth.__get__(service, TelegramService)
    service.is_authenticated = is_authenticated.__get__(service, TelegramService)
    service.is_connected = is_connected.__get__(service, TelegramService)