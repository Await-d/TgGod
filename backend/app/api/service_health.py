"""
服务健康检查API
提供系统服务状态查询和健康检查接口
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging

from ..services.service_monitor import service_monitor
from ..services.service_installer import service_installer

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/health/services", response_model=Dict[str, Any])
async def get_services_health():
    """
    获取所有服务的健康状态
    """
    try:
        # 执行一次健康检查
        health_result = await service_monitor.check_all_services()
        
        return {
            "success": True,
            "data": health_result
        }
        
    except Exception as e:
        logger.error(f"获取服务健康状态失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取服务健康状态失败: {str(e)}"
        )

@router.get("/health/summary", response_model=Dict[str, Any])
async def get_health_summary():
    """
    获取服务健康状态摘要
    """
    try:
        summary = service_monitor.get_service_summary()
        
        return {
            "success": True,
            "data": summary
        }
        
    except Exception as e:
        logger.error(f"获取健康状态摘要失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取健康状态摘要失败: {str(e)}"
        )

@router.get("/health/status", response_model=Dict[str, Any])
async def get_current_status():
    """
    获取当前缓存的服务状态 (不重新检查)
    """
    try:
        status = service_monitor.get_service_status()
        
        return {
            "success": True,
            "data": status
        }
        
    except Exception as e:
        logger.error(f"获取当前服务状态失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取当前服务状态失败: {str(e)}"
        )

@router.post("/health/check", response_model=Dict[str, Any])
async def force_health_check():
    """
    强制执行服务健康检查
    """
    try:
        logger.info("接收到强制健康检查请求")
        health_result = await service_monitor.check_all_services()
        
        return {
            "success": True,
            "message": "健康检查完成",
            "data": health_result
        }
        
    except Exception as e:
        logger.error(f"强制健康检查失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"健康检查失败: {str(e)}"
        )

@router.post("/services/install", response_model=Dict[str, Any])
async def install_services():
    """
    执行服务安装检查和安装
    """
    try:
        logger.info("接收到服务安装请求")
        
        from ..services.service_installer import run_service_installation
        installation_result = await run_service_installation()
        
        return {
            "success": installation_result["success"],
            "message": "服务安装检查完成",
            "data": installation_result
        }
        
    except Exception as e:
        logger.error(f"服务安装失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"服务安装失败: {str(e)}"
        )

@router.get("/services/dependencies", response_model=Dict[str, Any])
async def get_service_dependencies():
    """
    获取系统服务依赖信息
    """
    try:
        dependencies = {
            "required_services": [
                {
                    "name": "ffmpeg",
                    "description": "视频处理和缩略图生成",
                    "critical": True,
                    "install_command": "apt-get install ffmpeg"
                },
                {
                    "name": "fonts",
                    "description": "系统字体支持",
                    "critical": False,
                    "install_command": "apt-get install fonts-dejavu fonts-liberation"
                },
                {
                    "name": "python_deps",
                    "description": "Python依赖包",
                    "critical": True,
                    "install_command": "pip install -r requirements.txt"
                },
                {
                    "name": "system_tools",
                    "description": "系统基础工具 (curl, wget, git等)",
                    "critical": False,
                    "install_command": "apt-get install curl wget git unzip"
                }
            ],
            "optional_services": [
                {
                    "name": "imagemagick",
                    "description": "高级图像处理",
                    "critical": False,
                    "install_command": "apt-get install imagemagick"
                },
                {
                    "name": "exiftool",
                    "description": "元数据处理",
                    "critical": False,
                    "install_command": "apt-get install libimage-exiftool-perl"
                }
            ]
        }
        
        return {
            "success": True,
            "data": dependencies
        }
        
    except Exception as e:
        logger.error(f"获取服务依赖信息失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取服务依赖信息失败: {str(e)}"
        )

@router.get("/system/info", response_model=Dict[str, Any])
async def get_system_info():
    """
    获取系统信息
    """
    try:
        import platform
        import os
        
        system_info = {
            "system": platform.system(),
            "platform": platform.platform(),
            "architecture": platform.machine(),
            "python_version": platform.python_version(),
            "is_docker": os.path.exists('/.dockerenv'),
            "working_directory": os.getcwd(),
            "user": os.getenv('USER', 'unknown'),
            "environment": {
                "PATH": os.getenv('PATH', '').split(':')[:5],  # 只显示前5个路径
                "PYTHONPATH": os.getenv('PYTHONPATH', 'not_set')
            }
        }
        
        return {
            "success": True,
            "data": system_info
        }
        
    except Exception as e:
        logger.error(f"获取系统信息失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取系统信息失败: {str(e)}"
        )

@router.get("/system/resources", response_model=Dict[str, Any])
async def get_system_resources():
    """
    获取详细的系统资源使用情况
    """
    try:
        resources = {}
        
        # 尝试使用psutil获取详细信息
        try:
            import psutil
            
            # CPU信息
            resources["cpu"] = {
                "usage_percent": psutil.cpu_percent(interval=1),
                "count": psutil.cpu_count(),
                "count_logical": psutil.cpu_count(logical=True)
            }
            
            # 添加CPU频率信息
            try:
                cpu_freq = psutil.cpu_freq()
                if cpu_freq:
                    resources["cpu"]["frequency"] = {
                        "current": cpu_freq.current,
                        "min": cpu_freq.min,
                        "max": cpu_freq.max
                    }
            except:
                pass
            
            # 内存信息
            memory = psutil.virtual_memory()
            resources["memory"] = {
                "total": memory.total,
                "available": memory.available,
                "used": memory.used,
                "percentage": memory.percent
            }
            
            # 磁盘信息
            try:
                disk = psutil.disk_usage('/')
                resources["disk"] = {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percentage": (disk.used / disk.total) * 100
                }
            except:
                pass
            
            # 网络信息
            try:
                net_io = psutil.net_io_counters()
                resources["network"] = {
                    "bytes_sent": net_io.bytes_sent,
                    "bytes_recv": net_io.bytes_recv,
                    "packets_sent": net_io.packets_sent,
                    "packets_recv": net_io.packets_recv
                }
                
                # 网络接口
                net_if_addrs = psutil.net_if_addrs()
                interfaces = {}
                for interface, addrs in net_if_addrs.items():
                    interface_info = []
                    for addr in addrs:
                        if addr.family == 2:  # IPv4
                            interface_info.append({
                                "ip": addr.address,
                                "netmask": addr.netmask
                            })
                    if interface_info:
                        interfaces[interface] = interface_info
                resources["network"]["interfaces"] = interfaces
                
            except:
                pass
            
            # 进程信息
            try:
                processes = psutil.pids()
                resources["processes"] = {
                    "total_count": len(processes),
                    "running": len([p for p in psutil.process_iter(['status']) if p.info['status'] == 'running'])
                }
            except:
                pass
            
        except ImportError:
            resources["error"] = "psutil未安装，无法获取详细资源信息"
        
        # 尝试获取CPU详细信息
        try:
            import cpuinfo
            cpu_info = cpuinfo.get_cpu_info()
            resources["cpu_detail"] = {
                "brand": cpu_info.get('brand_raw', 'Unknown'),
                "arch": cpu_info.get('arch', 'Unknown'),
                "bits": cpu_info.get('bits', 'Unknown'),
                "hz": cpu_info.get('hz_actual_friendly', 'Unknown')
            }
        except ImportError:
            resources["cpu_detail"] = {"error": "py-cpuinfo未安装"}
        except Exception as e:
            resources["cpu_detail"] = {"error": f"获取CPU详细信息失败: {str(e)}"}
        
        return {
            "success": True,
            "data": resources
        }
        
    except Exception as e:
        logger.error(f"获取系统资源信息失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取系统资源信息失败: {str(e)}"
        )

@router.get("/system/performance", response_model=Dict[str, Any])
async def get_system_performance():
    """
    获取系统性能指标
    """
    try:
        performance = {}
        
        try:
            import psutil
            
            # CPU性能
            cpu_times = psutil.cpu_times()
            performance["cpu"] = {
                "usage_percent": psutil.cpu_percent(interval=1),
                "per_cpu": psutil.cpu_percent(interval=1, percpu=True),
                "times": {
                    "user": cpu_times.user,
                    "system": cpu_times.system,
                    "idle": cpu_times.idle
                }
            }
            
            # 内存性能
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            performance["memory"] = {
                "virtual": {
                    "total": memory.total,
                    "used": memory.used,
                    "available": memory.available,
                    "percentage": memory.percent
                },
                "swap": {
                    "total": swap.total,
                    "used": swap.used,
                    "free": swap.free,
                    "percentage": swap.percent
                }
            }
            
            # 磁盘IO
            try:
                disk_io = psutil.disk_io_counters()
                if disk_io:
                    performance["disk_io"] = {
                        "read_bytes": disk_io.read_bytes,
                        "write_bytes": disk_io.write_bytes,
                        "read_count": disk_io.read_count,
                        "write_count": disk_io.write_count
                    }
            except:
                pass
            
            # 网络IO
            try:
                net_io = psutil.net_io_counters()
                performance["network_io"] = {
                    "bytes_sent": net_io.bytes_sent,
                    "bytes_recv": net_io.bytes_recv,
                    "packets_sent": net_io.packets_sent,
                    "packets_recv": net_io.packets_recv,
                    "errin": net_io.errin,
                    "errout": net_io.errout,
                    "dropin": net_io.dropin,
                    "dropout": net_io.dropout
                }
            except:
                pass
            
            # 系统负载 (Linux)
            try:
                load_avg = os.getloadavg()
                performance["load_average"] = {
                    "1min": load_avg[0],
                    "5min": load_avg[1],
                    "15min": load_avg[2]
                }
            except:
                pass
            
        except ImportError:
            performance["error"] = "psutil未安装，无法获取性能指标"
        
        return {
            "success": True,
            "data": performance
        }
        
    except Exception as e:
        logger.error(f"获取系统性能指标失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取系统性能指标失败: {str(e)}"
        )
