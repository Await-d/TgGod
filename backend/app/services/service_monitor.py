"""
服务监控器 - 监控系统服务健康状态 (重构版本)
定期检查必要服务的运行状态和可用性，使用统一的错误处理框架
"""
import os
import shutil
import subprocess
import asyncio
from typing import Dict, Optional, Any
from datetime import datetime, timedelta

from ..core import (
    ServiceResult, HealthCheckResult, SystemError, ExternalServiceError,
    NetworkError, FileSystemError, handle_service_errors, timeout,
    performance_monitor, ServiceLoggerMixin, create_error_context,
    operation_context, robust_service_method, RetryConfig
)


class ServiceMonitor(ServiceLoggerMixin):
    """系统服务健康状态监控器 (重构版本)"""

    def __init__(self):
        super().__init__()
        self.last_check_time: Optional[datetime] = None
        self.check_interval = 300  # 5分钟检查一次
        self.service_status: Dict[str, Any] = {}
        self.monitoring = False

    @handle_service_errors("ServiceMonitor", "start_monitoring")
    async def start_monitoring(self) -> ServiceResult[None]:
        """启动服务监控"""
        if self.monitoring:
            warning_msg = "服务监控已在运行"
            self.log_operation_warning("start_monitoring", warning_msg)
            return ServiceResult.success_result(None, warnings=[warning_msg])

        self.monitoring = True
        self.log_operation_start("start_monitoring")

        # 立即进行一次检查
        initial_check = await self.check_all_services()
        if not initial_check.success:
            self.monitoring = False
            return ServiceResult.error_result(initial_check.error)

        # 启动定期检查任务
        asyncio.create_task(self._monitoring_loop())

        self.log_operation_success("start_monitoring")
        return ServiceResult.success_result(None)

    @handle_service_errors("ServiceMonitor", "stop_monitoring")
    async def stop_monitoring(self) -> ServiceResult[None]:
        """停止服务监控"""
        self.monitoring = False
        self.log_operation_success("stop_monitoring")
        return ServiceResult.success_result(None)

    async def _monitoring_loop(self):
        """监控循环"""
        while self.monitoring:
            try:
                await asyncio.sleep(self.check_interval)
                if self.monitoring:
                    await self.check_all_services()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.log_operation_error("monitoring_loop", e)
                await asyncio.sleep(60)  # 发生错误时等待1分钟再重试

    @robust_service_method(
        service_name="ServiceMonitor",
        operation_name="check_all_services",
        timeout_seconds=120.0
    )
    async def check_all_services(self) -> ServiceResult[Dict[str, Any]]:
        """检查所有服务状态"""
        check_time = datetime.now()
        results = {
            "check_time": check_time.isoformat(),
            "services": {},
            "overall_status": "healthy",
            "warnings": [],
            "errors": []
        }

        # 检查各种服务
        service_checks = [
            ("ffmpeg", self._check_ffmpeg),
            ("fonts", self._check_fonts),
            ("python_deps", self._check_python_dependencies),
            ("system_tools", self._check_system_tools),
            ("system_monitoring", self._check_system_monitoring),
            ("disk_space", self._check_disk_space),
            ("memory", self._check_memory),
            ("cpu", self._check_cpu),
            ("network", self._check_network)
        ]

        for service_name, check_func in service_checks:
            try:
                service_result = await check_func()
                if service_result.success:
                    results["services"][service_name] = service_result.data

                    # 根据检查结果更新整体状态
                    health_data = service_result.data
                    if health_data["status"] == "error":
                        results["overall_status"] = "unhealthy"
                        results["errors"].append(f"{service_name}: {health_data.get('message', '检查失败')}")
                    elif health_data["status"] == "warning":
                        if results["overall_status"] == "healthy":
                            results["overall_status"] = "degraded"
                        results["warnings"].append(f"{service_name}: {health_data.get('message', '检查警告')}")

                else:
                    # 服务检查失败
                    results["services"][service_name] = {
                        "status": "error",
                        "message": f"检查异常: {service_result.error.message}",
                        "available": False
                    }
                    results["overall_status"] = "unhealthy"
                    results["errors"].append(f"{service_name}: 检查异常")

            except Exception as e:
                # 这里不应该到达，因为使用了装饰器，但保留作为安全网
                context = create_error_context("ServiceMonitor", "check_all_services")
                error = SystemError(f"Unexpected error checking {service_name}: {e}", context=context, original_error=e)
                results["services"][service_name] = {
                    "status": "error",
                    "message": f"检查异常: {str(e)}",
                    "available": False
                }
                results["overall_status"] = "unhealthy"
                results["errors"].append(f"{service_name}: 检查异常")

        # 更新缓存
        self.service_status = results
        self.last_check_time = check_time

        # 记录结果摘要
        if results["overall_status"] == "healthy":
            self.log_operation_success("check_all_services", result_summary="所有服务健康")
        elif results["overall_status"] == "degraded":
            self.log_operation_warning("check_all_services", f"服务状态降级，警告: {len(results['warnings'])} 个")
        else:
            self.log_operation_error("check_all_services", Exception(f"服务状态不健康，错误: {len(results['errors'])} 个"))

        return ServiceResult.success_result(results)

    @timeout(30.0)
    @handle_service_errors("ServiceMonitor", "check_ffmpeg")
    async def _check_ffmpeg(self) -> ServiceResult[HealthCheckResult]:
        """检查FFmpeg状态"""
        if not shutil.which("ffmpeg"):
            return ServiceResult.success_result(HealthCheckResult(
                service_name="ffmpeg",
                is_healthy=False,
                status_message="FFmpeg未安装或不在PATH中"
            ))

        try:
            # 检查FFmpeg版本和功能
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True, text=True, timeout=10
            )

            if result.returncode == 0:
                version_line = result.stdout.split('\n')[0]
                return ServiceResult.success_result(HealthCheckResult(
                    service_name="ffmpeg",
                    is_healthy=True,
                    status_message=version_line,
                    details={"version": version_line}
                ))
            else:
                error_msg = f"FFmpeg运行异常: {result.stderr}"
                return ServiceResult.success_result(HealthCheckResult(
                    service_name="ffmpeg",
                    is_healthy=False,
                    status_message=error_msg
                ))

        except subprocess.TimeoutExpired:
            context = create_error_context("ServiceMonitor", "check_ffmpeg")
            error = NetworkError("FFmpeg响应超时", context=context)
            return ServiceResult.error_result(error)
        except Exception as e:
            context = create_error_context("ServiceMonitor", "check_ffmpeg")
            error = SystemError(f"FFmpeg检查异常: {str(e)}", context=context, original_error=e)
            return ServiceResult.error_result(error)

    @handle_service_errors("ServiceMonitor", "check_fonts")
    async def _check_fonts(self) -> ServiceResult[HealthCheckResult]:
        """检查字体可用性"""
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/TTF/simhei.ttf",
            "/System/Library/Fonts/PingFang.ttc",
            "/Windows/Fonts/msyh.ttc"
        ]

        available_fonts = []
        for font_path in font_paths:
            if os.path.exists(font_path):
                available_fonts.append(os.path.basename(font_path))

        if available_fonts:
            return ServiceResult.success_result(HealthCheckResult(
                service_name="fonts",
                is_healthy=True,
                status_message=f"找到 {len(available_fonts)} 个系统字体",
                details={"fonts": available_fonts}
            ))
        else:
            return ServiceResult.success_result(HealthCheckResult(
                service_name="fonts",
                is_healthy=False,
                status_message="未找到系统字体，将使用默认字体",
                details={"fonts": []}
            ))

    @handle_service_errors("ServiceMonitor", "check_python_dependencies")
    async def _check_python_dependencies(self) -> ServiceResult[HealthCheckResult]:
        """检查Python依赖"""
        required_packages = {
            "PIL": "Pillow - 图像处理",
            "requests": "HTTP请求库",
            "telethon": "Telegram客户端",
            "fastapi": "Web框架",
            "sqlalchemy": "数据库ORM"
        }

        missing_packages = []
        available_packages = []

        for import_name, description in required_packages.items():
            try:
                __import__(import_name)
                available_packages.append(description)
            except ImportError:
                missing_packages.append(description)

        if not missing_packages:
            return ServiceResult.success_result(HealthCheckResult(
                service_name="python_deps",
                is_healthy=True,
                status_message=f"所有 {len(available_packages)} 个Python依赖可用",
                details={"packages": available_packages}
            ))
        else:
            return ServiceResult.success_result(HealthCheckResult(
                service_name="python_deps",
                is_healthy=False,
                status_message=f"缺少 {len(missing_packages)} 个Python依赖",
                details={"missing": missing_packages}
            ))

    @handle_service_errors("ServiceMonitor", "check_system_tools")
    async def _check_system_tools(self) -> ServiceResult[HealthCheckResult]:
        """检查系统工具"""
        tools = ["curl", "wget", "git", "unzip"]
        available_tools = []
        missing_tools = []

        for tool in tools:
            if shutil.which(tool):
                available_tools.append(tool)
            else:
                missing_tools.append(tool)

        if not missing_tools:
            return ServiceResult.success_result(HealthCheckResult(
                service_name="system_tools",
                is_healthy=True,
                status_message=f"所有系统工具可用: {', '.join(available_tools)}",
                details={"tools": available_tools}
            ))
        elif len(missing_tools) <= 2:
            return ServiceResult.success_result(HealthCheckResult(
                service_name="system_tools",
                is_healthy=True,
                status_message=f"部分工具缺失: {', '.join(missing_tools)}",
                details={"missing": missing_tools}
            ))
        else:
            return ServiceResult.success_result(HealthCheckResult(
                service_name="system_tools",
                is_healthy=False,
                status_message=f"多个系统工具缺失: {', '.join(missing_tools)}",
                details={"missing": missing_tools}
            ))

    @handle_service_errors("ServiceMonitor", "check_system_monitoring")
    async def _check_system_monitoring(self) -> ServiceResult[HealthCheckResult]:
        """检查系统监控包可用性"""
        monitoring_status = {
            "psutil": False,
            "cpuinfo": False,
            "GPUtil": False
        }

        # 检查psutil
        try:
            import psutil
            monitoring_status["psutil"] = True
            # 测试psutil基本功能
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
        except ImportError:
            pass
        except Exception as e:
            self.log_operation_warning("check_system_monitoring", f"psutil功能测试异常: {e}")

        # 检查cpuinfo
        try:
            import cpuinfo
            monitoring_status["cpuinfo"] = True
            # 测试cpuinfo基本功能
            cpu_info = cpuinfo.get_cpu_info()
        except ImportError:
            pass
        except Exception as e:
            self.log_operation_warning("check_system_monitoring", f"cpuinfo功能测试异常: {e}")

        # 检查GPUtil (可选)
        try:
            import GPUtil
            monitoring_status["GPUtil"] = True
        except ImportError:
            pass

        available_packages = [pkg for pkg, available in monitoring_status.items() if available]
        missing_packages = [pkg for pkg, available in monitoring_status.items() if not available and pkg != "GPUtil"]

        if not missing_packages:
            return ServiceResult.success_result(HealthCheckResult(
                service_name="system_monitoring",
                is_healthy=True,
                status_message=f"系统监控包完整: {', '.join(available_packages)}",
                details={"packages": available_packages}
            ))
        elif len(missing_packages) == 1:
            return ServiceResult.success_result(HealthCheckResult(
                service_name="system_monitoring",
                is_healthy=True,
                status_message=f"缺少监控包: {', '.join(missing_packages)}",
                details={"missing": missing_packages}
            ))
        else:
            return ServiceResult.success_result(HealthCheckResult(
                service_name="system_monitoring",
                is_healthy=False,
                status_message=f"缺少关键监控包: {', '.join(missing_packages)}",
                details={"missing": missing_packages}
            ))

    @handle_service_errors("ServiceMonitor", "check_disk_space")
    async def _check_disk_space(self) -> ServiceResult[HealthCheckResult]:
        """检查磁盘空间"""
        try:
            # 检查当前工作目录所在磁盘的空间
            statvfs = os.statvfs('.')

            # 计算空间 (字节)
            total = statvfs.f_frsize * statvfs.f_blocks
            available = statvfs.f_frsize * statvfs.f_available
            used = total - available

            # 转换为GB
            total_gb = total / (1024**3)
            available_gb = available / (1024**3)
            used_gb = used / (1024**3)

            # 计算使用百分比
            usage_percent = (used / total) * 100

            is_healthy = usage_percent < 90
            if usage_percent > 90:
                status_message = f"磁盘空间严重不足: {usage_percent:.1f}% 已使用"
            elif usage_percent > 80:
                status_message = f"磁盘空间不足: {usage_percent:.1f}% 已使用"
            else:
                status_message = f"磁盘空间充足: {available_gb:.1f}GB 可用"

            return ServiceResult.success_result(HealthCheckResult(
                service_name="disk_space",
                is_healthy=is_healthy,
                status_message=status_message,
                details={
                    "total_gb": round(total_gb, 2),
                    "available_gb": round(available_gb, 2),
                    "used_gb": round(used_gb, 2),
                    "usage_percent": round(usage_percent, 1)
                }
            ))

        except Exception as e:
            context = create_error_context("ServiceMonitor", "check_disk_space")
            error = FileSystemError(f"磁盘空间检查异常: {str(e)}", context=context, original_error=e)
            return ServiceResult.error_result(error)

    @handle_service_errors("ServiceMonitor", "check_memory")
    async def _check_memory(self) -> ServiceResult[HealthCheckResult]:
        """检查内存使用情况"""
        # 读取内存信息 (Linux)
        if not os.path.exists('/proc/meminfo'):
            return ServiceResult.success_result(HealthCheckResult(
                service_name="memory",
                is_healthy=True,
                status_message="无法获取内存信息 (非Linux系统)"
            ))

        with open('/proc/meminfo', 'r') as f:
            meminfo = f.read()

        # 解析内存信息
        memory_data = {}
        for line in meminfo.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                memory_data[key.strip()] = value.strip()

        # 提取关键数据 (KB)
        total_kb = int(memory_data['MemTotal'].split()[0])
        available_kb = int(memory_data.get('MemAvailable', memory_data.get('MemFree', '0')).split()[0])

        # 转换为MB
        total_mb = total_kb / 1024
        available_mb = available_kb / 1024
        used_mb = total_mb - available_mb

        # 计算使用百分比
        usage_percent = (used_mb / total_mb) * 100

        is_healthy = usage_percent < 90
        if usage_percent > 90:
            status_message = f"内存使用过高: {usage_percent:.1f}% 已使用"
        elif usage_percent > 80:
            status_message = f"内存使用较高: {usage_percent:.1f}% 已使用"
        else:
            status_message = f"内存使用正常: {available_mb:.0f}MB 可用"

        return ServiceResult.success_result(HealthCheckResult(
            service_name="memory",
            is_healthy=is_healthy,
            status_message=status_message,
            details={
                "total_mb": round(total_mb, 1),
                "available_mb": round(available_mb, 1),
                "used_mb": round(used_mb, 1),
                "usage_percent": round(usage_percent, 1)
            }
        ))

    @handle_service_errors("ServiceMonitor", "check_cpu")
    async def _check_cpu(self) -> ServiceResult[HealthCheckResult]:
        """检查CPU使用情况 (使用psutil)"""
        try:
            import psutil
        except ImportError:
            return ServiceResult.success_result(HealthCheckResult(
                service_name="cpu",
                is_healthy=True,
                status_message="psutil未安装，无法获取CPU信息"
            ))

        # 获取CPU使用率
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        cpu_count_logical = psutil.cpu_count(logical=True)

        # 获取CPU频率
        try:
            cpu_freq = psutil.cpu_freq()
            current_freq = cpu_freq.current if cpu_freq else None
        except:
            current_freq = None

        # 获取负载平均值 (Linux)
        try:
            load_avg = os.getloadavg()
        except:
            load_avg = None

        # 评估CPU状态
        is_healthy = cpu_percent < 90
        if cpu_percent > 90:
            status_message = f"CPU使用率过高: {cpu_percent:.1f}%"
        elif cpu_percent > 80:
            status_message = f"CPU使用率较高: {cpu_percent:.1f}%"
        else:
            status_message = f"CPU使用率正常: {cpu_percent:.1f}%"

        details = {
            "cpu_percent": cpu_percent,
            "cpu_count": cpu_count,
            "cpu_count_logical": cpu_count_logical
        }

        if current_freq:
            details["cpu_freq_mhz"] = round(current_freq, 1)

        if load_avg:
            details["load_avg"] = [round(x, 2) for x in load_avg]

        return ServiceResult.success_result(HealthCheckResult(
            service_name="cpu",
            is_healthy=is_healthy,
            status_message=status_message,
            details=details
        ))

    @handle_service_errors("ServiceMonitor", "check_network")
    async def _check_network(self) -> ServiceResult[HealthCheckResult]:
        """检查网络状态 (使用psutil)"""
        try:
            import psutil
        except ImportError:
            return ServiceResult.success_result(HealthCheckResult(
                service_name="network",
                is_healthy=True,
                status_message="psutil未安装，无法获取网络信息"
            ))

        # 获取网络接口统计
        net_io = psutil.net_io_counters()
        net_connections = len(psutil.net_connections())

        # 获取网络接口信息
        net_if_addrs = psutil.net_if_addrs()
        active_interfaces = []

        for interface, addrs in net_if_addrs.items():
            for addr in addrs:
                if addr.family == 2:  # AF_INET (IPv4)
                    if not addr.address.startswith('127.'):  # 排除回环地址
                        active_interfaces.append({
                            "interface": interface,
                            "ip": addr.address
                        })

        # 检查网络连通性 (简单测试)
        is_healthy = True
        if not active_interfaces:
            is_healthy = False
            status_message = "未检测到活跃的网络接口"
        elif net_connections > 1000:
            status_message = f"网络连接数较多: {net_connections}"
        else:
            status_message = f"网络状态正常，活跃接口: {len(active_interfaces)} 个"

        return ServiceResult.success_result(HealthCheckResult(
            service_name="network",
            is_healthy=is_healthy,
            status_message=status_message,
            details={
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv,
                "connections": net_connections,
                "active_interfaces": active_interfaces
            }
        ))

    @handle_service_errors("ServiceMonitor", "get_service_status", return_result_type=False)
    def get_service_status(self) -> Dict[str, Any]:
        """获取当前服务状态 (保持向后兼容)"""
        if not self.service_status:
            return {
                "status": "unknown",
                "message": "尚未进行服务检查",
                "last_check": None
            }

        return {
            "status": self.service_status.get("overall_status", "unknown"),
            "last_check": self.last_check_time.isoformat() if self.last_check_time else None,
            "details": self.service_status
        }

    @handle_service_errors("ServiceMonitor", "get_service_summary", return_result_type=False)
    def get_service_summary(self) -> Dict[str, Any]:
        """获取服务状态摘要 (保持向后兼容)"""
        if not self.service_status:
            return {"message": "尚未进行服务检查"}

        services = self.service_status.get("services", {})
        summary = {
            "total_services": len(services),
            "healthy_services": 0,
            "warning_services": 0,
            "error_services": 0,
            "overall_status": self.service_status.get("overall_status", "unknown"),
            "last_check": self.last_check_time.isoformat() if self.last_check_time else None
        }

        for service_name, service_data in services.items():
            status = service_data.get("status", "unknown")
            if status == "healthy":
                summary["healthy_services"] += 1
            elif status == "warning":
                summary["warning_services"] += 1
            elif status == "error":
                summary["error_services"] += 1

        return summary


# 全局服务监控器实例 (保持向后兼容)
service_monitor = ServiceMonitor()

# 兼容性适配器
class ServiceMonitorAdapter:
    """服务监控器适配器，提供向后兼容的接口"""

    def __init__(self, monitor: ServiceMonitor):
        self.monitor = monitor

    async def start_monitoring(self):
        """向后兼容的启动监控方法"""
        result = await self.monitor.start_monitoring()
        if not result.success:
            raise Exception(f"Failed to start monitoring: {result.error.message}")

    async def stop_monitoring(self):
        """向后兼容的停止监控方法"""
        result = await self.monitor.stop_monitoring()
        if not result.success:
            raise Exception(f"Failed to stop monitoring: {result.error.message}")

    async def check_all_services(self) -> Dict[str, Any]:
        """向后兼容的检查所有服务方法"""
        result = await self.monitor.check_all_services()
        if result.success:
            return result.data
        else:
            # 返回错误信息但不抛出异常，保持原有行为
            return {
                "check_time": datetime.now().isoformat(),
                "services": {},
                "overall_status": "error",
                "warnings": [],
                "errors": [result.error.message]
            }

    def get_service_status(self) -> Dict[str, Any]:
        """向后兼容的获取服务状态方法"""
        return self.monitor.get_service_status()

    def get_service_summary(self) -> Dict[str, Any]:
        """向后兼容的获取服务摘要方法"""
        return self.monitor.get_service_summary()


# 创建兼容适配器实例
service_monitor_adapter = ServiceMonitorAdapter(service_monitor)

# 为了完全向后兼容，替换全局实例的方法
service_monitor.start_monitoring_original = service_monitor.start_monitoring
service_monitor.stop_monitoring_original = service_monitor.stop_monitoring
service_monitor.check_all_services_original = service_monitor.check_all_services

# 替换为适配器方法
service_monitor.start_monitoring = service_monitor_adapter.start_monitoring
service_monitor.stop_monitoring = service_monitor_adapter.stop_monitoring
service_monitor.check_all_services = service_monitor_adapter.check_all_services