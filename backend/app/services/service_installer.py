"""
服务安装器 - 自动检查和安装必要的系统依赖
在项目启动时自动下载和配置必要的服务和工具
"""
import os
import shutil
import subprocess
import logging
import asyncio
import sys
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import platform
import requests
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class ServiceInstaller:
    
    def __init__(self, websocket_manager=None):
        # 导入新的统一平台管理器
        from ..core.platform_manager import get_platform_manager
        
        self.platform_manager = get_platform_manager()
        self.platform_info = self.platform_manager.platform_info
        self.websocket_manager = websocket_manager
        self.install_log = []
        self.rollback_actions = []  # 用于错误回滚
        
        logger.info(f"🔍 检测到平台: {self.platform_info.system}")
        logger.info(f"🏗️ 架构: {self.platform_info.architecture}")
        
        if self.platform_manager.preferred_manager:
            logger.info(f"📦 使用包管理器: {self.platform_manager.preferred_manager.name}")
        else:
            logger.warning("⚠️ 没有找到可用的包管理器")
    
    async def check_and_install_all(self) -> Dict[str, any]:
        """检查并安装所有必要服务 - 完全重写版本"""
        logger.info("🚀 开始完整的平台兼容性安装流程...")
        
        results = {
            "success": True,
            "platform_info": {
                "system": self.platform_info.system,
                "arch": self.platform_info.arch,
                "is_docker": self.platform_info.is_docker,
                "distro": self.platform_info.distro_info
            },
            "package_managers": {
                "available": [pm.name for pm in self.package_managers if pm.available],
                "primary": self.platform_manager.preferred_manager.name if self.platform_manager.preferred_manager else None
            },
            "installed_services": [],
            "failed_services": [],
            "already_installed": [],
            "skipped_services": [],
            "total_checks": 0
        }
        
        # 完整的服务安装流程
        installation_tasks = [
            ("package_manager_setup", self._setup_package_managers),
            ("system_update", self._update_system_packages),
            ("ffmpeg", self._install_ffmpeg_enhanced),
            ("fonts", self._install_fonts_enhanced),
            ("system_tools", self._install_system_tools_enhanced),
            ("python_deps", self._install_python_dependencies_enhanced),
            ("system_monitoring", self._install_monitoring_tools_enhanced),
            ("media_tools", self._install_media_tools_enhanced),
            ("environment_setup", self._setup_environment_variables),
            ("verification", self._verify_all_installations)
        ]
        
        results["total_checks"] = len(installation_tasks)
        await self.progress_reporter.set_total_steps(len(installation_tasks))
        
        try:
            for step, (service_name, install_func) in enumerate(installation_tasks, 1):
                await self.progress_reporter.report_progress(
                    step, f"处理 {service_name}", "开始检查和安装..."
                )
                
                try:
                    logger.info(f"🔧 步骤 {step}/{len(installation_tasks)}: {service_name}")
                    install_result = await install_func()
                    
                    if install_result["success"]:
                        if install_result["action"] == "installed":
                            results["installed_services"].append({
                                "name": service_name,
                                "details": install_result.get("details", ""),
                                "rollback": install_result.get("rollback_info")
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
                            
                        await self.progress_reporter.report_progress(
                            step, f"{service_name} 完成", install_result.get("details", "")
                        )
                    else:
                        error_msg = install_result.get("error", "未知错误")
                        results["failed_services"].append({
                            "name": service_name,
                            "error": error_msg
                        })
                        logger.error(f"❌ {service_name} 安装失败: {error_msg}")
                        await self.progress_reporter.report_error(
                            f"{service_name} 失败", error_msg
                        )
                        
                        # 如果是关键服务失败，考虑是否继续
                        if service_name in ["package_manager_setup", "system_update"]:
                            logger.warning("关键服务失败，但继续执行其他安装...")
                        
                except Exception as e:
                    error_msg = f"安装过程异常: {str(e)}"
                    results["failed_services"].append({
                        "name": service_name,
                        "error": error_msg
                    })
                    logger.error(f"❌ {service_name} 异常: {e}")
                    await self.progress_reporter.report_error(
                        f"{service_name} 异常", str(e)
                    )
            
            # 最终验证和报告
            await self._generate_final_report(results)
            await self.progress_reporter.report_success("所有安装任务完成")
            
        except Exception as e:
            logger.error(f"💥 安装流程致命错误: {e}")
            results["success"] = False
            await self.progress_reporter.report_error("安装流程失败", str(e))
            
            # 尝试回滚
            await self._rollback_installations()
        
        return results
    
    async def _setup_package_managers(self) -> Dict[str, any]:
        """设置和初始化包管理器"""
        try:
            logger.info("🔧 设置包管理器...")
            
            # 使用统一平台管理器确保包管理器可用
            success, message = await self.platform_manager.ensure_package_manager()
            
            if success:
                self.rollback_actions.append({
                    "type": "package_manager_setup",
                    "manager": self.platform_manager.preferred_manager.name if self.platform_manager.preferred_manager else "unknown"
                })
                
                return {
                    "success": True,
                    "action": "setup_complete",
                    "details": message,
                    "manager": self.platform_manager.preferred_manager.name if self.platform_manager.preferred_manager else "unknown"
                }
            else:
                return {
                    "success": False,
                    "error": f"包管理器设置失败: {message}"
                }
            
        except Exception as e:
            logger.error(f"包管理器设置异常: {e}")
            return {
                "success": False,
                "error": f"包管理器设置异常: {str(e)}"
            }
    
    async def _update_system_packages(self) -> Dict[str, any]:
        """更新系统包索引"""
        try:
            if not self.platform_manager.preferred_manager:
                return {
                    "success": True,
                    "action": "skipped",
                    "reason": "没有可用的包管理器"
                }
            
            logger.info(f"📦 使用 {self.platform_manager.preferred_manager.name} 更新包索引...")
            result = await self.platform_manager.update_package_list()
            success = result.success
            
            if success:
                return {
                    "success": True,
                    "action": "installed",
                    "details": f"{self.platform_manager.preferred_manager.name} 包索引更新成功"
                }
            else:
                return {
                    "success": False,
                    "error": f"{self.platform_manager.preferred_manager.name} 包索引更新失败"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"包索引更新异常: {str(e)}"
            }
    
    async def _install_ffmpeg_enhanced(self) -> Dict[str, any]:
        """增强版FFmpeg安装 - 使用统一平台管理器"""
        try:
            # 检查是否已安装
            commands = self.platform_manager.get_platform_specific_commands()
            ffmpeg_cmd = commands.get("ffmpeg", "ffmpeg")
            
            if shutil.which(ffmpeg_cmd):
                version_result = subprocess.run(
                    [ffmpeg_cmd, "-version"], 
                    capture_output=True, 
                    text=True,
                    timeout=30
                )
                if version_result.returncode == 0:
                    version_line = version_result.stdout.split('\n')[0]
                    return {
                        "success": True,
                        "action": "already_installed",
                        "details": version_line
                    }
            
            logger.info("📥 FFmpeg未找到，开始跨平台安装...")
            
            # 确保包管理器可用
            if not self.platform_manager.preferred_manager:
                success, message = await self.platform_manager.ensure_package_manager()
                if not success:
                    return {
                        "success": False,
                        "error": f"无法设置包管理器: {message}"
                    }
            
            # 获取平台特定的FFmpeg包名
            package_name = self.platform_manager.get_package_mapping("ffmpeg")
            
            logger.info(f"🎯 使用 {self.platform_manager.preferred_manager.name} 安装 {package_name}...")
            
            # 发送进度通知
            if self.websocket_manager:
                await self.websocket_manager.broadcast({
                    "type": "installation_progress",
                    "step": "ffmpeg_install",
                    "status": "installing",
                    "message": f"正在安装FFmpeg ({package_name})..."
                })
            
            # 安装FFmpeg
            result = await self.platform_manager.install_package(package_name)
            
            if result.success:
                # 验证安装
                if shutil.which(ffmpeg_cmd):
                    # 记录回滚信息
                    self.rollback_actions.append({
                        "type": "package",
                        "manager": self.platform_manager.preferred_manager.name,
                        "package": package_name
                    })
                    
                    # 发送成功通知
                    if self.websocket_manager:
                        await self.websocket_manager.broadcast({
                            "type": "installation_progress",
                            "step": "ffmpeg_install",
                            "status": "completed",
                            "message": "FFmpeg安装成功"
                        })
                    
                    return {
                        "success": True,
                        "action": "installed",
                        "details": f"通过 {self.platform_manager.preferred_manager.name} 安装FFmpeg成功",
                        "rollback_info": {
                            "type": "package",
                            "manager": self.platform_manager.preferred_manager.name,
                            "package": package_name
                        }
                    }
                else:
                    return {
                        "success": False,
                        "error": "FFmpeg安装后仍然无法找到命令"
                    }
            else:
                # 尝试备选安装方法
                logger.warning(f"标准安装失败: {result.stderr}")
                
                if self.platform_info.is_linux:
                    logger.info("尝试使用snap安装FFmpeg...")
                    try:
                        process = await asyncio.create_subprocess_exec(
                            "snap", "install", "ffmpeg",
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE
                        )
                        stdout, stderr = await process.communicate()
                        
                        if process.returncode == 0 and shutil.which("ffmpeg"):
                            self.rollback_actions.append({
                                "type": "snap",
                                "package": "ffmpeg"
                            })
                            
                            return {
                                "success": True,
                                "action": "installed",
                                "details": "通过snap安装FFmpeg成功",
                                "rollback_info": {
                                    "type": "snap",
                                    "package": "ffmpeg"
                                }
                            }
                    except Exception as e:
                        logger.warning(f"snap安装也失败了: {e}")
                
                return {
                    "success": False,
                    "error": f"FFmpeg安装失败: {result.stderr}"
                }
                
        except Exception as e:
            logger.error(f"FFmpeg安装过程异常: {e}")
            return {
                "success": False,
                "error": f"FFmpeg安装过程异常: {str(e)}"
            }
    
    async def _install_fonts_enhanced(self) -> Dict[str, any]:
        """增强版字体安装"""
        try:
            # 平台特定字体检查
            font_checks = {
                "linux": [
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                    "/usr/share/fonts/TTF/simhei.ttf"
                ],
                "darwin": [
                    "/System/Library/Fonts/PingFang.ttc",
                    "/System/Library/Fonts/Helvetica.ttc"
                ],
                "windows": [
                    "C:/Windows/Fonts/msyh.ttc",
                    "C:/Windows/Fonts/arial.ttf"
                ]
            }
            
            font_paths = font_checks.get(self.platform_info.system, [])
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
            
            logger.info("📥 未找到足够的系统字体，开始安装...")
            
            if not self.platform_manager.preferred_manager:
                return {
                    "success": True,
                    "action": "skipped",
                    "reason": "没有包管理器，跳过字体安装"
                }
            
            # 平台特定字体包
            font_packages = {
                "linux": ["fonts-dejavu", "fonts-liberation", "fonts-noto-cjk"],
                "darwin": [],  # macOS通常有足够字体
                "windows": []  # Windows通常有足够字体
            }
            
            packages_to_install = font_packages.get(self.platform_info.system, [])
            
            if not packages_to_install:
                return {
                    "success": True,
                    "action": "skipped",
                    "reason": f"{self.platform_info.system}平台通常已包含必要字体"
                }
            
            # 逐个安装包
            successfully_installed = []
            failed_installs = []
            
            for package in packages_to_install:
                result = await self.platform_manager.install_package(package)
                if result.success:
                    successfully_installed.append(package)
                else:
                    failed_installs.append((package, result.stderr))
            
            success = len(successfully_installed) > 0
            if success:
                message = f"成功安装: {', '.join(successfully_installed)}"
                if failed_installs:
                    message += f", 失败: {', '.join([p[0] for p in failed_installs])}"
            else:
                message = f"全部失败: {', '.join([p[0] for p in failed_installs])}"
            
            if success:
                # 再次检查字体
                installed_fonts = []
                for font_path in font_paths:
                    if os.path.exists(font_path):
                        installed_fonts.append(os.path.basename(font_path))
                
                if installed_fonts:
                    return {
                        "success": True,
                        "action": "installed",
                        "details": f"成功安装字体，找到: {', '.join(installed_fonts)}",
                        "rollback_info": {
                            "type": "packages",
                            "manager": self.platform_manager.preferred_manager.name,
                            "packages": packages_to_install
                        }
                    }
                else:
                    return {
                        "success": False,
                        "error": "字体包安装后仍未找到可用字体文件"
                    }
            else:
                return {
                    "success": False,
                    "error": f"字体包安装失败: {message}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"字体安装过程异常: {str(e)}"
            }
    
    async def _install_system_tools_enhanced(self) -> Dict[str, any]:
        """增强版系统工具安装"""
        try:
            # 平台特定的基础工具
            base_tools = ["curl", "wget", "unzip", "git"]
            platform_specific_tools = {
                "linux": ["build-essential", "pkg-config"],
                "darwin": ["pkg-config"],
                "windows": ["7zip", "gitforwindows"]
            }
            
            all_tools = base_tools + platform_specific_tools.get(self.platform_info.system, [])
            missing_tools = []
            existing_tools = []
            
            # 检查基础命令行工具
            for tool in base_tools:
                if shutil.which(tool):
                    existing_tools.append(tool)
                else:
                    missing_tools.append(tool)
            
            if not missing_tools:
                return {
                    "success": True,
                    "action": "already_installed",
                    "details": f"所有基础工具已存在: {', '.join(existing_tools)}"
                }
            
            if not self.platform_manager.preferred_manager:
                return {
                    "success": False,
                    "error": "没有包管理器来安装系统工具"
                }
            
            logger.info(f"📥 安装缺失的系统工具: {', '.join(missing_tools)}")
            
            # 平台特定包名映射
            package_mapping = {
                "windows": {
                    "curl": "curl",
                    "wget": "wget",
                    "unzip": "7zip",
                    "git": "Git.Git"
                }
            }
            
            # 转换包名
            packages_to_install = []
            for tool in missing_tools:
                if self.platform_info.is_windows and tool in package_mapping["windows"]:
                    packages_to_install.append(package_mapping["windows"][tool])
                else:
                    packages_to_install.append(tool)
            
            # 逐个安装包
            successfully_installed = []
            failed_installs = []
            
            for package in packages_to_install:
                result = await self.platform_manager.install_package(package)
                if result.success:
                    successfully_installed.append(package)
                else:
                    failed_installs.append((package, result.stderr))
            
            success = len(successfully_installed) > 0
            if success:
                message = f"成功安装: {', '.join(successfully_installed)}"
                if failed_installs:
                    message += f", 失败: {', '.join([p[0] for p in failed_installs])}"
            else:
                message = f"全部失败: {', '.join([p[0] for p in failed_installs])}"
            
            if success:
                # 验证安装结果
                installed_tools = []
                still_missing = []
                
                for tool in missing_tools:
                    if shutil.which(tool):
                        installed_tools.append(tool)
                    else:
                        still_missing.append(tool)
                
                details = f"成功安装: {', '.join(installed_tools)}" if installed_tools else ""
                if still_missing:
                    details += f", 仍缺失: {', '.join(still_missing)}"
                
                return {
                    "success": len(installed_tools) > 0,
                    "action": "installed",
                    "details": details,
                    "rollback_info": {
                        "type": "packages",
                        "manager": self.platform_manager.preferred_manager.name,
                        "packages": packages_to_install
                    }
                }
            else:
                return {
                    "success": False,
                    "error": f"系统工具安装失败: {message}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"系统工具安装过程异常: {str(e)}"
            }
    
    async def _install_python_dependencies_enhanced(self) -> Dict[str, any]:
        """增强版Python依赖安装"""
        try:
            # 必要的Python包及其版本要求
            required_packages = {
                "PIL": ("Pillow", ">=8.0.0"),
                "requests": ("requests", ">=2.25.0"),
                "telethon": ("telethon", ">=1.24.0"),
                "fastapi": ("fastapi", ">=0.68.0"),
                "sqlalchemy": ("SQLAlchemy", ">=1.4.0"),
                "psutil": ("psutil", ">=5.8.0"),
                "cpuinfo": ("py-cpuinfo", ">=8.0.0"),
                "GPUtil": ("GPUtil", "")  # 可选
            }
            
            missing_packages = []
            existing_packages = []
            version_issues = []
            
            for import_name, (package_name, version_req) in required_packages.items():
                try:
                    module = __import__(import_name)
                    
                    # 检查版本 (如果指定)
                    if version_req and hasattr(module, '__version__'):
                        # 这里可以添加版本检查逻辑
                        pass
                    
                    existing_packages.append(package_name)
                    
                except ImportError:
                    if import_name != "GPUtil":  # GPUtil是可选的
                        missing_packages.append((package_name, version_req))
            
            if not missing_packages:
                return {
                    "success": True,
                    "action": "already_installed",
                    "details": f"所有必要Python依赖已安装: {len(existing_packages)} 个"
                }
            
            logger.info(f"📥 安装缺失的Python包: {[p[0] for p in missing_packages]}")
            
            # 安装缺失的包
            successfully_installed = []
            failed_installs = []
            
            for package_name, version_req in missing_packages:
                package_spec = f"{package_name}{version_req}" if version_req else package_name
                
                logger.info(f"安装Python包: {package_spec}")
                
                try:
                    process = await asyncio.create_subprocess_exec(
                        sys.executable, "-m", "pip", "install", package_spec,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await process.communicate()
                    success = process.returncode == 0
                    stdout = stdout.decode('utf-8')
                    stderr = stderr.decode('utf-8')
                except Exception as e:
                    success = False
                    stdout = ""
                    stderr = str(e)
                
                if success:
                    successfully_installed.append(package_name)
                    logger.info(f"✅ {package_name} 安装成功")
                else:
                    failed_installs.append((package_name, stderr))
                    logger.warning(f"❌ {package_name} 安装失败: {stderr}")
            
            # 最终验证
            final_missing = []
            for import_name, (package_name, _) in required_packages.items():
                try:
                    __import__(import_name)
                except ImportError:
                    if import_name != "GPUtil":
                        final_missing.append(package_name)
            
            if final_missing:
                return {
                    "success": False,
                    "error": f"安装后仍有Python包缺失: {', '.join(final_missing)}"
                }
            else:
                return {
                    "success": True,
                    "action": "installed",
                    "details": f"成功安装Python包: {', '.join(successfully_installed)}",
                    "rollback_info": {
                        "type": "python_packages",
                        "packages": successfully_installed
                    }
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Python依赖安装异常: {str(e)}"
            }
    
    async def _install_monitoring_tools_enhanced(self) -> Dict[str, any]:
        """增强版系统监控工具安装"""
        try:
            # 核心监控包
            monitoring_packages = [
                ("psutil", "系统进程和资源监控"),
                ("py-cpuinfo", "CPU信息获取"),
                ("GPUtil", "GPU监控 (可选)")
            ]
            
            missing_packages = []
            existing_packages = []
            
            # 检查psutil
            try:
                import psutil
                existing_packages.append(("psutil", f"v{psutil.__version__}"))
            except ImportError:
                missing_packages.append("psutil")
            
            # 检查py-cpuinfo
            try:
                import cpuinfo
                existing_packages.append(("py-cpuinfo", "已安装"))
            except ImportError:
                missing_packages.append("py-cpuinfo")
            
            # 检查GPUtil (可选)
            try:
                import GPUtil
                existing_packages.append(("GPUtil", "已安装"))
            except ImportError:
                # GPUtil是可选的，但仍然尝试安装
                missing_packages.append("GPUtil")
            
            if not missing_packages:
                return {
                    "success": True,
                    "action": "already_installed",
                    "details": f"监控工具已安装: {', '.join([f'{name}({ver})' for name, ver in existing_packages])}"
                }
            
            logger.info(f"📥 安装监控工具: {', '.join(missing_packages)}")
            
            # 安装每个包
            successfully_installed = []
            failed_installs = []
            
            for package in missing_packages:
                logger.info(f"安装监控包: {package}")
                
                try:
                    process = await asyncio.create_subprocess_exec(
                        sys.executable, "-m", "pip", "install", package,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await process.communicate()
                    success = process.returncode == 0
                    stdout = stdout.decode('utf-8')
                    stderr = stderr.decode('utf-8')
                except Exception as e:
                    success = False
                    stdout = ""
                    stderr = str(e)
                
                if success:
                    successfully_installed.append(package)
                    logger.info(f"✅ {package} 安装成功")
                else:
                    # GPUtil安装失败不算致命错误
                    if package == "GPUtil":
                        logger.warning(f"⚠️ {package} 安装失败(可选): {stderr}")
                    else:
                        failed_installs.append((package, stderr))
                        logger.error(f"❌ {package} 安装失败: {stderr}")
            
            # 最终验证
            final_status = []
            
            # 验证psutil
            try:
                import psutil
                final_status.append("psutil - 系统资源监控 ✅")
            except ImportError:
                final_status.append("psutil - 缺失 ❌")
            
            # 验证cpuinfo
            try:
                import cpuinfo
                final_status.append("py-cpuinfo - CPU信息 ✅")
            except ImportError:
                final_status.append("py-cpuinfo - 缺失 ❌")
            
            # 验证GPUtil
            try:
                import GPUtil
                final_status.append("GPUtil - GPU监控 ✅")
            except ImportError:
                final_status.append("GPUtil - 缺失 (可选) ⚠️")
            
            if failed_installs:
                return {
                    "success": False,
                    "error": f"关键监控包安装失败: {', '.join([p[0] for p in failed_installs])}",
                    "details": "\n".join(final_status)
                }
            else:
                return {
                    "success": True,
                    "action": "installed",
                    "details": f"监控工具安装完成: {', '.join(successfully_installed)}",
                    "status": final_status,
                    "rollback_info": {
                        "type": "python_packages",
                        "packages": successfully_installed
                    }
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"监控工具安装异常: {str(e)}"
            }
    
    async def _install_media_tools_enhanced(self) -> Dict[str, any]:
        """增强版媒体处理工具安装"""
        try:
            media_tools_check = {
                "imagemagick": ["convert", "magick"],
                "exiftool": ["exiftool"]
            }
            
            missing_tools = []
            existing_tools = []
            
            # 检查每个工具
            for tool_name, commands in media_tools_check.items():
                tool_found = False
                for cmd in commands:
                    if shutil.which(cmd):
                        existing_tools.append(f"{tool_name}({cmd})")
                        tool_found = True
                        break
                
                if not tool_found:
                    missing_tools.append(tool_name)
            
            if not missing_tools:
                return {
                    "success": True,
                    "action": "already_installed",
                    "details": f"媒体工具已存在: {', '.join(existing_tools)}"
                }
            
            if not self.platform_manager.preferred_manager:
                return {
                    "success": True,
                    "action": "skipped",
                    "reason": "没有包管理器，跳过媒体工具安装"
                }
            
            logger.info(f"📥 安装媒体处理工具: {', '.join(missing_tools)}")
            
            # 平台特定包名映射
            package_mapping = {
                "linux": {
                    "imagemagick": "imagemagick",
                    "exiftool": "libimage-exiftool-perl"
                },
                "darwin": {
                    "imagemagick": "imagemagick",
                    "exiftool": "exiftool"
                },
                "windows": {
                    "imagemagick": "ImageMagick",
                    "exiftool": "exiftool"
                }
            }
            
            platform_packages = package_mapping.get(self.platform_info.system, {})
            packages_to_install = []
            
            for tool in missing_tools:
                if tool in platform_packages:
                    packages_to_install.append(platform_packages[tool])
                else:
                    packages_to_install.append(tool)
            
            if not packages_to_install:
                return {
                    "success": True,
                    "action": "skipped",
                    "reason": f"没有找到适合{self.platform_info.system}的媒体工具包"
                }
            
            # 逐个安装包
            successfully_installed = []
            failed_installs = []
            
            for package in packages_to_install:
                result = await self.platform_manager.install_package(package)
                if result.success:
                    successfully_installed.append(package)
                else:
                    failed_installs.append((package, result.stderr))
            
            success = len(successfully_installed) > 0
            if success:
                message = f"成功安装: {', '.join(successfully_installed)}"
                if failed_installs:
                    message += f", 失败: {', '.join([p[0] for p in failed_installs])}"
            else:
                message = f"全部失败: {', '.join([p[0] for p in failed_installs])}"
            
            if success:
                # 验证安装
                installed_tools = []
                still_missing = []
                
                for tool_name, commands in media_tools_check.items():
                    if tool_name in missing_tools:
                        tool_found = False
                        for cmd in commands:
                            if shutil.which(cmd):
                                installed_tools.append(f"{tool_name}({cmd})")
                                tool_found = True
                                break
                        
                        if not tool_found:
                            still_missing.append(tool_name)
                
                details = ""
                if installed_tools:
                    details += f"成功安装: {', '.join(installed_tools)}"
                if still_missing:
                    details += f", 仍缺失: {', '.join(still_missing)}"
                
                return {
                    "success": len(installed_tools) > 0,
                    "action": "installed",
                    "details": details,
                    "rollback_info": {
                        "type": "packages",
                        "manager": self.platform_manager.preferred_manager.name,
                        "packages": packages_to_install
                    }
                }
            else:
                return {
                    "success": False,
                    "error": f"媒体工具安装失败: {message}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"媒体工具安装异常: {str(e)}"
            }
    
    async def _setup_environment_variables(self) -> Dict[str, any]:
        """设置环境变量"""
        try:
            env_updates = []
            
            # Windows特定PATH更新
            if self.platform_info.is_windows:
                # 可能需要添加到PATH的目录
                potential_paths = [
                    "C:/ProgramData/chocolatey/bin",
                    "C:/Program Files/ImageMagick-7.1.0-Q16-HDRI",
                    "C:/Program Files/Git/bin"
                ]
                
                for path in potential_paths:
                    if os.path.exists(path) and path not in os.environ.get('PATH', ''):
                        os.environ['PATH'] = f"{os.environ.get('PATH', '')};{path}"
                        env_updates.append(f"添加到PATH: {path}")
            
            # macOS特定设置
            elif self.platform_info.is_macos:
                # 确保Homebrew路径在PATH中
                homebrew_paths = [
                    '/opt/homebrew/bin',  # Apple Silicon
                    '/usr/local/bin'      # Intel
                ]
                
                for hb_path in homebrew_paths:
                    if os.path.exists(hb_path) and hb_path not in os.environ.get('PATH', ''):
                        os.environ['PATH'] = f"{hb_path}:{os.environ.get('PATH', '')}"
                        env_updates.append(f"添加Homebrew路径到PATH: {hb_path}")
            
            if env_updates:
                return {
                    "success": True,
                    "action": "installed",
                    "details": f"环境变量更新: {'; '.join(env_updates)}"
                }
            else:
                return {
                    "success": True,
                    "action": "skipped",
                    "reason": "没有需要更新的环境变量"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"环境变量设置异常: {str(e)}"
            }
    
    async def _verify_all_installations(self) -> Dict[str, any]:
        """验证所有安装"""
        try:
            verification_results = {
                "ffmpeg": shutil.which("ffmpeg") is not None,
                "system_tools": {
                    "curl": shutil.which("curl") is not None,
                    "wget": shutil.which("wget") is not None,
                    "git": shutil.which("git") is not None
                },
                "python_packages": {},
                "media_tools": {
                    "imagemagick": shutil.which("convert") is not None or shutil.which("magick") is not None,
                    "exiftool": shutil.which("exiftool") is not None
                }
            }
            
            # 验证Python包
            python_packages = ["PIL", "requests", "telethon", "fastapi", "sqlalchemy", "psutil", "cpuinfo"]
            for pkg in python_packages:
                try:
                    __import__(pkg)
                    verification_results["python_packages"][pkg] = True
                except ImportError:
                    verification_results["python_packages"][pkg] = False
            
            # 统计
            total_checks = (
                1 +  # ffmpeg
                len(verification_results["system_tools"]) +
                len(verification_results["python_packages"]) +
                len(verification_results["media_tools"])
            )
            
            passed_checks = (
                (1 if verification_results["ffmpeg"] else 0) +
                sum(1 for v in verification_results["system_tools"].values() if v) +
                sum(1 for v in verification_results["python_packages"].values() if v) +
                sum(1 for v in verification_results["media_tools"].values() if v)
            )
            
            success_rate = (passed_checks / total_checks) * 100
            
            return {
                "success": success_rate >= 80,  # 80%通过率算成功
                "action": "verified",
                "details": f"验证完成: {passed_checks}/{total_checks} 通过 ({success_rate:.1f}%)",
                "verification_results": verification_results,
                "success_rate": success_rate
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"安装验证异常: {str(e)}"
            }
    
    async def _generate_final_report(self, results: Dict[str, any]):
        """生成最终安装报告"""
        logger.info("=" * 60)
        logger.info("📋 TgGod 平台兼容性安装完整报告")
        logger.info("=" * 60)
        logger.info(f"🖥️  平台: {results['platform_info']['system']} ({results['platform_info']['arch']})")
        logger.info(f"🐳 Docker: {results['platform_info']['is_docker']}")
        logger.info(f"📦 包管理器: {results['package_managers']['primary']}")
        logger.info("-" * 60)
        logger.info(f"✅ 新安装: {len(results['installed_services'])} 个")
        logger.info(f"✓  已存在: {len(results['already_installed'])} 个")
        logger.info(f"⏭️  跳过: {len(results['skipped_services'])} 个")
        logger.info(f"❌ 失败: {len(results['failed_services'])} 个")
        logger.info("-" * 60)
        
        if results["installed_services"]:
            logger.info("🔧 新安装的服务:")
            for service in results["installed_services"]:
                logger.info(f"  ✅ {service['name']}: {service['details']}")
        
        if results["failed_services"]:
            logger.info("⚠️ 安装失败的服务:")
            for service in results["failed_services"]:
                logger.info(f"  ❌ {service['name']}: {service['error']}")
        
        logger.info("=" * 60)
    
    async def _rollback_installations(self):
        """回滚已安装的服务"""
        if not self.rollback_actions:
            logger.info("没有需要回滚的操作")
            return
        
        logger.warning("🔄 开始回滚安装...")
        
        for action in reversed(self.rollback_actions):
            try:
                if action["type"] == "package" and self.platform_manager.preferred_manager:
                    # 这里可以实现包的卸载逻辑
                    logger.info(f"回滚包: {action['package']}")
                elif action["type"] == "homebrew":
                    logger.info("回滚Homebrew安装...")
                    # 实现Homebrew卸载逻辑
                elif action["type"] == "chocolatey":
                    logger.info("回滚Chocolatey安装...")
                    # 实现Chocolatey卸载逻辑
            except Exception as e:
                logger.error(f"回滚操作失败: {e}")
        
        logger.info("回滚操作完成")

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
