"""
服务监控器 - 监控系统服务健康状态
定期检查必要服务的运行状态和可用性
"""
import os
import shutil
import subprocess
import logging
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

class ServiceMonitor:
    """系统服务健康状态监控器"""
    
    def __init__(self):
        self.last_check_time = None
        self.check_interval = 300  # 5分钟检查一次
        self.service_status = {}
        self.monitoring = False
        
    async def start_monitoring(self):
        """启动服务监控"""
        if self.monitoring:
            logger.warning("服务监控已在运行")
            return
            
        self.monitoring = True
        logger.info("🔍 启动服务健康监控...")
        
        # 立即进行一次检查
        await self.check_all_services()
        
        # 启动定期检查任务
        asyncio.create_task(self._monitoring_loop())
        
    async def stop_monitoring(self):
        """停止服务监控"""
        self.monitoring = False
        logger.info("⏹️ 服务监控已停止")
    
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
                logger.error(f"服务监控循环异常: {e}")
                await asyncio.sleep(60)  # 发生错误时等待1分钟再重试
    
    async def check_all_services(self) -> Dict[str, any]:
        """检查所有服务状态"""
        logger.debug("🔍 开始服务健康检查...")
        
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
                results["services"][service_name] = service_result
                
                # 根据检查结果更新整体状态
                if service_result["status"] == "error":
                    results["overall_status"] = "unhealthy"
                    results["errors"].append(f"{service_name}: {service_result.get('message', '检查失败')}")
                elif service_result["status"] == "warning":
                    if results["overall_status"] == "healthy":
                        results["overall_status"] = "degraded"
                    results["warnings"].append(f"{service_name}: {service_result.get('message', '检查警告')}")
                    
            except Exception as e:
                logger.error(f"检查服务 {service_name} 时异常: {e}")
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
        
        # 根据状态记录日志
        if results["overall_status"] == "healthy":
            logger.debug("✅ 所有服务健康检查通过")
        elif results["overall_status"] == "degraded":
            logger.warning(f"⚠️ 服务状态降级，警告: {len(results['warnings'])} 个")
            for warning in results["warnings"]:
                logger.warning(f"  - {warning}")
        else:
            logger.error(f"❌ 服务状态不健康，错误: {len(results['errors'])} 个")
            for error in results["errors"]:
                logger.error(f"  - {error}")
        
        return results
    
    async def _check_ffmpeg(self) -> Dict[str, any]:
        """检查FFmpeg状态"""
        try:
            if not shutil.which("ffmpeg"):
                return {
                    "status": "error",
                    "message": "FFmpeg未安装或不在PATH中",
                    "available": False
                }
            
            # 检查FFmpeg版本和功能
            result = subprocess.run(
                ["ffmpeg", "-version"], 
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode == 0:
                version_line = result.stdout.split('\n')[0]
                return {
                    "status": "healthy",
                    "message": version_line,
                    "available": True,
                    "version": version_line
                }
            else:
                return {
                    "status": "error",
                    "message": f"FFmpeg运行异常: {result.stderr}",
                    "available": False
                }
                
        except subprocess.TimeoutExpired:
            return {
                "status": "warning",
                "message": "FFmpeg响应超时",
                "available": False
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"FFmpeg检查异常: {str(e)}",
                "available": False
            }
    
    async def _check_fonts(self) -> Dict[str, any]:
        """检查字体可用性"""
        try:
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
                return {
                    "status": "healthy",
                    "message": f"找到 {len(available_fonts)} 个系统字体",
                    "available": True,
                    "fonts": available_fonts
                }
            else:
                return {
                    "status": "warning",
                    "message": "未找到系统字体，将使用默认字体",
                    "available": False,
                    "fonts": []
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"字体检查异常: {str(e)}",
                "available": False
            }
    
    async def _check_python_dependencies(self) -> Dict[str, any]:
        """检查Python依赖"""
        try:
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
                return {
                    "status": "healthy",
                    "message": f"所有 {len(available_packages)} 个Python依赖可用",
                    "available": True,
                    "packages": available_packages
                }
            else:
                return {
                    "status": "error",
                    "message": f"缺少 {len(missing_packages)} 个Python依赖",
                    "available": False,
                    "missing": missing_packages
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Python依赖检查异常: {str(e)}",
                "available": False
            }
    
    async def _check_system_tools(self) -> Dict[str, any]:
        """检查系统工具"""
        try:
            tools = ["curl", "wget", "git", "unzip"]
            available_tools = []
            missing_tools = []
            
            for tool in tools:
                if shutil.which(tool):
                    available_tools.append(tool)
                else:
                    missing_tools.append(tool)
            
            if not missing_tools:
                return {
                    "status": "healthy",
                    "message": f"所有系统工具可用: {', '.join(available_tools)}",
                    "available": True,
                    "tools": available_tools
                }
            elif len(missing_tools) <= 2:
                return {
                    "status": "warning",
                    "message": f"部分工具缺失: {', '.join(missing_tools)}",
                    "available": True,
                    "missing": missing_tools
                }
            else:
                return {
                    "status": "error",
                    "message": f"多个系统工具缺失: {', '.join(missing_tools)}",
                    "available": False,
                    "missing": missing_tools
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"系统工具检查异常: {str(e)}",
                "available": False
            }
    
    async def _check_system_monitoring(self) -> Dict[str, any]:
        """检查系统监控包可用性"""
        try:
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
                logger.warning(f"psutil功能测试异常: {e}")
            
            # 检查cpuinfo
            try:
                import cpuinfo
                monitoring_status["cpuinfo"] = True
                
                # 测试cpuinfo基本功能
                cpu_info = cpuinfo.get_cpu_info()
                
            except ImportError:
                pass
            except Exception as e:
                logger.warning(f"cpuinfo功能测试异常: {e}")
            
            # 检查GPUtil (可选)
            try:
                import GPUtil
                monitoring_status["GPUtil"] = True
            except ImportError:
                pass
            
            available_packages = [pkg for pkg, available in monitoring_status.items() if available]
            missing_packages = [pkg for pkg, available in monitoring_status.items() if not available and pkg != "GPUtil"]
            
            if not missing_packages:
                return {
                    "status": "healthy",
                    "message": f"系统监控包完整: {', '.join(available_packages)}",
                    "available": True,
                    "packages": available_packages
                }
            elif len(missing_packages) == 1:
                return {
                    "status": "warning",
                    "message": f"缺少监控包: {', '.join(missing_packages)}",
                    "available": True,
                    "missing": missing_packages
                }
            else:
                return {
                    "status": "error",
                    "message": f"缺少关键监控包: {', '.join(missing_packages)}",
                    "available": False,
                    "missing": missing_packages
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"系统监控检查异常: {str(e)}",
                "available": False
            }

    async def _check_disk_space(self) -> Dict[str, any]:
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
            
            if usage_percent > 90:
                status = "error"
                message = f"磁盘空间严重不足: {usage_percent:.1f}% 已使用"
            elif usage_percent > 80:
                status = "warning"
                message = f"磁盘空间不足: {usage_percent:.1f}% 已使用"
            else:
                status = "healthy"
                message = f"磁盘空间充足: {available_gb:.1f}GB 可用"
            
            return {
                "status": status,
                "message": message,
                "available": True,
                "total_gb": round(total_gb, 2),
                "available_gb": round(available_gb, 2),
                "used_gb": round(used_gb, 2),
                "usage_percent": round(usage_percent, 1)
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"磁盘空间检查异常: {str(e)}",
                "available": False
            }
    
    async def _check_memory(self) -> Dict[str, any]:
        """检查内存使用情况"""
        try:
            # 读取内存信息 (Linux)
            if os.path.exists('/proc/meminfo'):
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
                
                if usage_percent > 90:
                    status = "error"
                    message = f"内存使用过高: {usage_percent:.1f}% 已使用"
                elif usage_percent > 80:
                    status = "warning"
                    message = f"内存使用较高: {usage_percent:.1f}% 已使用"
                else:
                    status = "healthy"
                    message = f"内存使用正常: {available_mb:.0f}MB 可用"
                
                return {
                    "status": status,
                    "message": message,
                    "available": True,
                    "total_mb": round(total_mb, 1),
                    "available_mb": round(available_mb, 1),
                    "used_mb": round(used_mb, 1),
                    "usage_percent": round(usage_percent, 1)
                }
            else:
                return {
                    "status": "warning",
                    "message": "无法获取内存信息 (非Linux系统)",
                    "available": False
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"内存检查异常: {str(e)}",
                "available": False
            }

    
    async def _check_cpu(self) -> Dict[str, any]:
        """检查CPU使用情况 (使用psutil)"""
        try:
            try:
                import psutil
            except ImportError:
                return {
                    "status": "warning",
                    "message": "psutil未安装，无法获取CPU信息",
                    "available": False
                }
            
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
            if cpu_percent > 90:
                status = "error"
                message = f"CPU使用率过高: {cpu_percent:.1f}%"
            elif cpu_percent > 80:
                status = "warning"
                message = f"CPU使用率较高: {cpu_percent:.1f}%"
            else:
                status = "healthy"
                message = f"CPU使用率正常: {cpu_percent:.1f}%"
            
            result = {
                "status": status,
                "message": message,
                "available": True,
                "cpu_percent": cpu_percent,
                "cpu_count": cpu_count,
                "cpu_count_logical": cpu_count_logical
            }
            
            if current_freq:
                result["cpu_freq_mhz"] = round(current_freq, 1)
            
            if load_avg:
                result["load_avg"] = [round(x, 2) for x in load_avg]
            
            return result
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"CPU检查异常: {str(e)}",
                "available": False
            }
    
    async def _check_network(self) -> Dict[str, any]:
        """检查网络状态 (使用psutil)"""
        try:
            try:
                import psutil
            except ImportError:
                return {
                    "status": "warning",
                    "message": "psutil未安装，无法获取网络信息",
                    "available": False
                }
            
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
            network_status = "healthy"
            if not active_interfaces:
                network_status = "warning"
                message = "未检测到活跃的网络接口"
            elif net_connections > 1000:
                network_status = "warning"
                message = f"网络连接数较多: {net_connections}"
            else:
                message = f"网络状态正常，活跃接口: {len(active_interfaces)} 个"
            
            return {
                "status": network_status,
                "message": message,
                "available": True,
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv,
                "connections": net_connections,
                "active_interfaces": active_interfaces
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"网络检查异常: {str(e)}",
                "available": False
            }
    
    def get_service_status(self) -> Dict[str, any]:
        """获取当前服务状态"""
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
    
    def get_service_summary(self) -> Dict[str, any]:
        """获取服务状态摘要"""
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

# 全局服务监控器实例
service_monitor = ServiceMonitor()