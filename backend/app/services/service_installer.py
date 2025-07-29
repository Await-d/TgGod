"""
服务安装器 - 自动检查和安装必要的系统依赖
在项目启动时自动下载和配置必要的服务和工具
"""
import os
import shutil
import subprocess
import logging
import asyncio
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import platform
import requests
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class ServiceInstaller:
    """系统服务和依赖自动安装器"""
    
    def __init__(self):
        self.system = platform.system().lower()
        self.arch = platform.machine().lower()
        self.is_docker = self._check_if_docker()
        self.install_log = []
        
    def _check_if_docker(self) -> bool:
        """检查是否在Docker容器中运行"""
        try:
            return os.path.exists('/.dockerenv') or os.path.exists('/proc/1/cgroup')
        except:
            return False
    
    async def check_and_install_all(self) -> Dict[str, any]:
        """检查并安装所有必要服务"""
        logger.info("🚀 开始检查和安装必要服务...")
        
        results = {
            "success": True,
            "installed_services": [],
            "failed_services": [],
            "already_installed": [],
            "skipped_services": [],
            "total_checks": 0
        }
        
        # 服务检查列表
        services_to_check = [
            ("ffmpeg", self._install_ffmpeg),
            ("fonts", self._install_fonts),
            ("system_tools", self._install_system_tools),
            ("python_deps", self._check_python_dependencies),
            ("system_monitoring", self._install_system_monitoring),
            ("media_tools", self._install_media_tools)
        ]
        
        results["total_checks"] = len(services_to_check)
        
        for service_name, install_func in services_to_check:
            try:
                logger.info(f"🔍 检查服务: {service_name}")
                install_result = await install_func()
                
                if install_result["success"]:
                    if install_result["action"] == "installed":
                        results["installed_services"].append({
                            "name": service_name,
                            "details": install_result.get("details", "")
                        })
                        logger.info(f"✅ {service_name} 安装成功")
                    elif install_result["action"] == "already_installed":
                        results["already_installed"].append(service_name)
                        logger.info(f"✓ {service_name} 已存在")
                    elif install_result["action"] == "skipped":
                        results["skipped_services"].append({
                            "name": service_name,
                            "reason": install_result.get("reason", "未知原因")
                        })
                        logger.info(f"⏭️ {service_name} 已跳过: {install_result.get('reason', '')}")
                else:
                    results["failed_services"].append({
                        "name": service_name,
                        "error": install_result.get("error", "未知错误")
                    })
                    logger.error(f"❌ {service_name} 安装失败: {install_result.get('error', '')}")
                    
            except Exception as e:
                results["failed_services"].append({
                    "name": service_name,
                    "error": str(e)
                })
                logger.error(f"❌ {service_name} 检查过程异常: {e}")
                results["success"] = False
        
        # 汇总结果
        logger.info("=" * 50)
        logger.info("📋 服务安装汇总报告")
        logger.info("=" * 50)
        logger.info(f"✅ 新安装: {len(results['installed_services'])} 个")
        logger.info(f"✓ 已存在: {len(results['already_installed'])} 个")
        logger.info(f"⏭️ 跳过: {len(results['skipped_services'])} 个")
        logger.info(f"❌ 失败: {len(results['failed_services'])} 个")
        
        if results["installed_services"]:
            logger.info("新安装的服务:")
            for service in results["installed_services"]:
                logger.info(f"  - {service['name']}: {service['details']}")
        
        if results["failed_services"]:
            logger.warning("安装失败的服务:")
            for service in results["failed_services"]:
                logger.warning(f"  - {service['name']}: {service['error']}")
        
        logger.info("=" * 50)
        
        return results
    
    async def _install_ffmpeg(self) -> Dict[str, any]:
        """安装FFmpeg"""
        try:
            # 检查是否已安装
            if shutil.which("ffmpeg"):
                version_result = subprocess.run(["ffmpeg", "-version"], 
                                              capture_output=True, text=True)
                if version_result.returncode == 0:
                    version_line = version_result.stdout.split('\n')[0]
                    return {
                        "success": True,
                        "action": "already_installed",
                        "details": version_line
                    }
            
            logger.info("📥 FFmpeg未找到，开始安装...")
            
            if self.is_docker or self.system == "linux":
                # Docker或Linux环境
                install_commands = [
                    ["apt-get", "update"],
                    ["apt-get", "install", "-y", "ffmpeg"]
                ]
                
                for cmd in install_commands:
                    logger.info(f"执行命令: {' '.join(cmd)}")
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    
                    if result.returncode != 0:
                        # 尝试使用snap安装
                        if "ffmpeg" in cmd:
                            logger.info("尝试使用snap安装FFmpeg...")
                            snap_result = subprocess.run(["snap", "install", "ffmpeg"], 
                                                       capture_output=True, text=True)
                            if snap_result.returncode == 0:
                                return {
                                    "success": True,
                                    "action": "installed",
                                    "details": "通过snap安装"
                                }
                        
                        return {
                            "success": False,
                            "error": f"命令执行失败: {result.stderr}"
                        }
                
                # 验证安装
                if shutil.which("ffmpeg"):
                    return {
                        "success": True,
                        "action": "installed",
                        "details": "通过apt-get安装"
                    }
                else:
                    return {
                        "success": False,
                        "error": "安装后仍然无法找到ffmpeg命令"
                    }
            
            elif self.system == "darwin":  # macOS
                # 尝试使用Homebrew安装
                if shutil.which("brew"):
                    result = subprocess.run(["brew", "install", "ffmpeg"], 
                                          capture_output=True, text=True)
                    if result.returncode == 0:
                        return {
                            "success": True,
                            "action": "installed",
                            "details": "通过Homebrew安装"
                        }
                
                return {
                    "success": False,
                    "error": "macOS需要先安装Homebrew，然后手动运行: brew install ffmpeg"
                }
            
            else:  # Windows或其他
                return {
                    "success": True,
                    "action": "skipped",
                    "reason": f"不支持在{self.system}系统上自动安装FFmpeg，请手动安装"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"FFmpeg安装过程异常: {str(e)}"
            }
    
    async def _install_fonts(self) -> Dict[str, any]:
        """安装必要字体"""
        try:
            # 检查字体目录
            font_paths = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/TTF/simhei.ttf",
                "/System/Library/Fonts/PingFang.ttc",  # macOS
                "/Windows/Fonts/msyh.ttc"  # Windows
            ]
            
            existing_fonts = []
            for font_path in font_paths:
                if os.path.exists(font_path):
                    existing_fonts.append(os.path.basename(font_path))
            
            if existing_fonts:
                return {
                    "success": True,
                    "action": "already_installed",
                    "details": f"找到字体: {', '.join(existing_fonts)}"
                }
            
            logger.info("📥 未找到系统字体，开始安装...")
            
            if self.is_docker or self.system == "linux":
                # 安装常用字体包
                install_commands = [
                    ["apt-get", "update"],
                    ["apt-get", "install", "-y", "fonts-dejavu", "fonts-liberation", "fonts-noto-cjk"]
                ]
                
                for cmd in install_commands:
                    logger.info(f"执行命令: {' '.join(cmd)}")
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    
                    if result.returncode != 0:
                        logger.warning(f"字体安装命令失败: {result.stderr}")
                
                # 检查安装结果
                for font_path in font_paths:
                    if os.path.exists(font_path):
                        return {
                            "success": True,
                            "action": "installed",
                            "details": f"成功安装字体包，找到: {os.path.basename(font_path)}"
                        }
                
                return {
                    "success": False,
                    "error": "字体安装后仍未找到可用字体文件"
                }
            
            else:
                return {
                    "success": True,
                    "action": "skipped",
                    "reason": f"{self.system}系统通常已包含必要字体"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"字体安装过程异常: {str(e)}"
            }
    
    async def _install_system_tools(self) -> Dict[str, any]:
        """安装系统工具"""
        try:
            tools_to_check = ["curl", "wget", "unzip", "git"]
            missing_tools = []
            existing_tools = []
            
            # 检查哪些工具缺失
            for tool in tools_to_check:
                if shutil.which(tool):
                    existing_tools.append(tool)
                else:
                    missing_tools.append(tool)
            
            if not missing_tools:
                return {
                    "success": True,
                    "action": "already_installed",
                    "details": f"所有工具已存在: {', '.join(existing_tools)}"
                }
            
            logger.info(f"📥 安装缺失的系统工具: {', '.join(missing_tools)}")
            
            if self.is_docker or self.system == "linux":
                # 安装缺失的工具
                cmd = ["apt-get", "install", "-y"] + missing_tools
                logger.info(f"执行命令: {' '.join(cmd)}")
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    installed_tools = []
                    still_missing = []
                    
                    # 验证安装结果
                    for tool in missing_tools:
                        if shutil.which(tool):
                            installed_tools.append(tool)
                        else:
                            still_missing.append(tool)
                    
                    if installed_tools:
                        details = f"成功安装: {', '.join(installed_tools)}"
                        if still_missing:
                            details += f", 仍缺失: {', '.join(still_missing)}"
                        
                        return {
                            "success": True,
                            "action": "installed",
                            "details": details
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"工具安装失败: {', '.join(missing_tools)}"
                        }
                else:
                    return {
                        "success": False,
                        "error": f"安装命令执行失败: {result.stderr}"
                    }
            
            else:
                return {
                    "success": True,
                    "action": "skipped",
                    "reason": f"{self.system}系统需要手动安装: {', '.join(missing_tools)}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"系统工具安装过程异常: {str(e)}"
            }
    
    async def _check_python_dependencies(self) -> Dict[str, any]:
        """检查Python依赖"""
        try:
            # 必要的Python包
            required_packages = {
                "PIL": "Pillow",
                "requests": "requests", 
                "telethon": "telethon",
                "fastapi": "fastapi",
                "sqlalchemy": "SQLAlchemy",
                "psutil": "psutil",
                "cpuinfo": "py-cpuinfo"
            }
            
            missing_packages = []
            existing_packages = []
            
            for import_name, package_name in required_packages.items():
                try:
                    __import__(import_name)
                    existing_packages.append(package_name)
                except ImportError:
                    missing_packages.append(package_name)
            
            if not missing_packages:
                return {
                    "success": True,
                    "action": "already_installed",
                    "details": f"所有Python依赖已安装: {len(existing_packages)} 个"
                }
            
            logger.info(f"📥 发现缺失的Python包: {', '.join(missing_packages)}")
            
            # 尝试安装缺失的包
            for package in missing_packages:
                logger.info(f"安装Python包: {package}")
                result = subprocess.run([
                    "pip", "install", package
                ], capture_output=True, text=True)
                
                if result.returncode != 0:
                    logger.warning(f"Python包 {package} 安装失败: {result.stderr}")
            
            # 重新检查
            still_missing = []
            for import_name, package_name in required_packages.items():
                try:
                    __import__(import_name)
                except ImportError:
                    still_missing.append(package_name)
            
            if still_missing:
                return {
                    "success": False,
                    "error": f"仍有Python包缺失: {', '.join(still_missing)}"
                }
            else:
                return {
                    "success": True,
                    "action": "installed",
                    "details": f"成功安装Python包: {', '.join(missing_packages)}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Python依赖检查异常: {str(e)}"
            }
    
    async def _install_system_monitoring(self) -> Dict[str, any]:
        """安装系统资源监控包"""
        try:
            # 需要检查的监控包
            monitoring_packages = {
                "psutil": "系统进程和资源监控",
                "cpuinfo": "CPU信息获取",
                "GPUtil": "GPU监控 (可选)"
            }
            
            missing_packages = []
            existing_packages = []
            
            # 检查psutil
            try:
                import psutil
                existing_packages.append("psutil")
            except ImportError:
                missing_packages.append("psutil")
            
            # 检查py-cpuinfo
            try:
                import cpuinfo
                existing_packages.append("py-cpuinfo")
            except ImportError:
                missing_packages.append("py-cpuinfo")
            
            # 检查GPUtil (可选)
            try:
                import GPUtil
                existing_packages.append("GPUtil")
            except ImportError:
                # GPUtil是可选的，不强制要求
                pass
            
            if not missing_packages:
                return {
                    "success": True,
                    "action": "already_installed",
                    "details": f"系统监控包已安装: {', '.join(existing_packages)}"
                }
            
            logger.info(f"📥 安装缺失的系统监控包: {', '.join(missing_packages)}")
            
            # 尝试安装缺失的包
            successfully_installed = []
            failed_installs = []
            
            for package in missing_packages:
                logger.info(f"安装监控包: {package}")
                
                # 特殊处理包名映射
                pip_package_name = package
                if package == "py-cpuinfo":
                    pip_package_name = "py-cpuinfo"
                elif package == "psutil":
                    pip_package_name = "psutil"
                
                result = subprocess.run([
                    "pip", "install", pip_package_name
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    successfully_installed.append(package)
                    logger.info(f"✅ {package} 安装成功")
                else:
                    failed_installs.append(package)
                    logger.warning(f"❌ {package} 安装失败: {result.stderr}")
            
            # 验证安装结果
            final_check = []
            
            # 重新检查psutil
            try:
                import psutil
                final_check.append("psutil - 系统资源监控")
            except ImportError:
                pass
            
            # 重新检查cpuinfo
            try:
                import cpuinfo
                final_check.append("py-cpuinfo - CPU信息")
            except ImportError:
                pass
            
            if successfully_installed:
                details = f"成功安装: {', '.join(successfully_installed)}"
                if failed_installs:
                    details += f", 安装失败: {', '.join(failed_installs)}"
                
                return {
                    "success": True,
                    "action": "installed",
                    "details": details,
                    "installed": final_check
                }
            else:
                return {
                    "success": False,
                    "error": f"所有监控包安装失败: {', '.join(failed_installs)}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"系统监控包安装过程异常: {str(e)}"
            }

    async def _install_media_tools(self) -> Dict[str, any]:
        """安装媒体处理工具"""
        try:
            media_tools = ["imagemagick", "exiftool"]
            missing_tools = []
            existing_tools = []
            
            # 检查ImageMagick
            if shutil.which("convert") or shutil.which("magick"):
                existing_tools.append("imagemagick")
            else:
                missing_tools.append("imagemagick")
            
            # 检查ExifTool
            if shutil.which("exiftool"):
                existing_tools.append("exiftool")
            else:
                missing_tools.append("exiftool")
            
            if not missing_tools:
                return {
                    "success": True,
                    "action": "already_installed",
                    "details": f"媒体工具已存在: {', '.join(existing_tools)}"
                }
            
            if not self.is_docker and self.system != "linux":
                return {
                    "success": True,
                    "action": "skipped",
                    "reason": f"媒体工具在{self.system}上需要手动安装"
                }
            
            logger.info(f"📥 安装媒体处理工具: {', '.join(missing_tools)}")
            
            install_packages = []
            if "imagemagick" in missing_tools:
                install_packages.append("imagemagick")
            if "exiftool" in missing_tools:
                install_packages.extend(["libimage-exiftool-perl", "exiftool"])
            
            if install_packages:
                cmd = ["apt-get", "install", "-y"] + install_packages
                logger.info(f"执行命令: {' '.join(cmd)}")
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    return {
                        "success": True,
                        "action": "installed", 
                        "details": f"成功安装媒体工具: {', '.join(install_packages)}"
                    }
                else:
                    return {
                        "success": False,
                        "error": f"媒体工具安装失败: {result.stderr}"
                    }
            
            return {
                "success": True,
                "action": "skipped",
                "reason": "没有需要安装的媒体工具"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"媒体工具安装过程异常: {str(e)}"
            }
    
    async def download_and_install_service(self, service_name: str, download_url: str, 
                                         install_path: str) -> Dict[str, any]:
        """下载并安装外部服务"""
        try:
            logger.info(f"📥 开始下载服务: {service_name}")
            logger.info(f"下载地址: {download_url}")
            logger.info(f"安装路径: {install_path}")
            
            # 确保安装目录存在
            os.makedirs(os.path.dirname(install_path), exist_ok=True)
            
            # 下载文件
            response = requests.get(download_url, stream=True, timeout=30)
            response.raise_for_status()
            
            # 保存文件
            with open(install_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # 设置执行权限
            os.chmod(install_path, 0o755)
            
            logger.info(f"✅ {service_name} 下载安装完成: {install_path}")
            
            return {
                "success": True,
                "action": "installed",
                "details": f"已下载到: {install_path}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"下载安装 {service_name} 失败: {str(e)}"
            }

# 全局服务安装器实例
service_installer = ServiceInstaller()

async def run_service_installation():
    """运行服务安装检查"""
    try:
        return await service_installer.check_and_install_all()
    except Exception as e:
        logger.error(f"服务安装过程出现异常: {e}")
        return {
            "success": False,
            "error": str(e),
            "installed_services": [],
            "failed_services": [],
            "already_installed": [],
            "skipped_services": []
        }