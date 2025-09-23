"""
统一的平台管理器 - 跨平台系统管理和依赖安装
支持 Linux/macOS/Windows 三大平台的统一接口
"""

import platform
import subprocess
import shutil
import os
import logging
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import asyncio
from pathlib import Path

logger = logging.getLogger(__name__)

class PlatformType(Enum):
    """支持的平台类型"""
    LINUX = "linux"
    MACOS = "darwin"
    WINDOWS = "windows"
    UNKNOWN = "unknown"

class PackageManagerType(Enum):
    """支持的包管理器类型"""
    APT = "apt"
    YUM = "yum"
    DNF = "dnf"
    PACMAN = "pacman"
    HOMEBREW = "homebrew"
    WINGET = "winget"
    CHOCOLATEY = "chocolatey"
    SCOOP = "scoop"

@dataclass
class PlatformInfo:
    """平台信息数据类"""
    system: str
    platform_type: PlatformType
    version: str
    architecture: str
    machine: str
    node: str
    processor: str
    is_linux: bool = field(init=False)
    is_macos: bool = field(init=False)
    is_windows: bool = field(init=False)
    
    def __post_init__(self):
        self.is_linux = self.platform_type == PlatformType.LINUX
        self.is_macos = self.platform_type == PlatformType.MACOS
        self.is_windows = self.platform_type == PlatformType.WINDOWS

@dataclass
class CommandResult:
    """命令执行结果"""
    success: bool
    stdout: str
    stderr: str
    return_code: int
    command: str

class PackageManager(ABC):
    """包管理器抽象基类"""
    
    def __init__(self, name: str, command: str):
        self.name = name
        self.command = command
        self.available = self._check_availability()
    
    def _check_availability(self) -> bool:
        """检查包管理器是否可用"""
        try:
            return shutil.which(self.command) is not None
        except Exception as e:
            logger.warning(f"检查包管理器 {self.name} 可用性失败: {e}")
            return False
    
    @abstractmethod
    async def install_package(self, package: str, **kwargs) -> CommandResult:
        """安装包"""
        pass
    
    @abstractmethod
    async def update_package_list(self) -> CommandResult:
        """更新包列表"""
        pass
    
    @abstractmethod
    async def check_package_installed(self, package: str) -> bool:
        """检查包是否已安装"""
        pass

class AptManager(PackageManager):
    """APT包管理器(Ubuntu/Debian)"""
    
    def __init__(self):
        super().__init__("APT", "apt")
    
    async def install_package(self, package: str, **kwargs) -> CommandResult:
        """安装APT包"""
        cmd = ["sudo", "apt", "install", "-y", package]
        return await self._run_command(cmd)
    
    async def update_package_list(self) -> CommandResult:
        """更新APT包列表"""
        cmd = ["sudo", "apt", "update"]
        return await self._run_command(cmd)
    
    async def check_package_installed(self, package: str) -> bool:
        """检查APT包是否已安装"""
        cmd = ["dpkg", "-l", package]
        result = await self._run_command(cmd)
        return result.success and "ii" in result.stdout
    
    async def _run_command(self, cmd: List[str]) -> CommandResult:
        """执行命令"""
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            return CommandResult(
                success=process.returncode == 0,
                stdout=stdout.decode('utf-8'),
                stderr=stderr.decode('utf-8'),
                return_code=process.returncode,
                command=' '.join(cmd)
            )
        except Exception as e:
            logger.error(f"执行命令失败 {' '.join(cmd)}: {e}")
            return CommandResult(
                success=False,
                stdout="",
                stderr=str(e),
                return_code=-1,
                command=' '.join(cmd)
            )

class HomebrewManager(PackageManager):
    """Homebrew包管理器(macOS)"""
    
    def __init__(self):
        super().__init__("Homebrew", "brew")
        self.install_script_url = "https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh"
    
    async def install_package(self, package: str, **kwargs) -> CommandResult:
        """安装Homebrew包"""
        cmd = ["brew", "install", package]
        if kwargs.get("cask", False):
            cmd = ["brew", "install", "--cask", package]
        return await self._run_command(cmd)
    
    async def update_package_list(self) -> CommandResult:
        """更新Homebrew"""
        cmd = ["brew", "update"]
        return await self._run_command(cmd)
    
    async def check_package_installed(self, package: str) -> bool:
        """检查Homebrew包是否已安装"""
        cmd = ["brew", "list", package]
        result = await self._run_command(cmd)
        return result.success
    
    async def install_homebrew(self) -> CommandResult:
        """自动安装Homebrew"""
        if self.available:
            return CommandResult(
                success=True,
                stdout="Homebrew已安装",
                stderr="",
                return_code=0,
                command="brew --version"
            )
        
        try:
            logger.info("开始安装Homebrew...")
            
            # 下载并执行Homebrew安装脚本
            cmd = [
                "/bin/bash", "-c",
                f"$(curl -fsSL {self.install_script_url})"
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, "NONINTERACTIVE": "1"}  # 非交互式安装
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                # 重新检查可用性
                self.available = self._check_availability()
                if not self.available:
                    # 尝试添加到PATH
                    homebrew_paths = [
                        "/opt/homebrew/bin/brew",  # Apple Silicon
                        "/usr/local/bin/brew"      # Intel
                    ]
                    
                    for brew_path in homebrew_paths:
                        if os.path.exists(brew_path):
                            os.environ["PATH"] = f"{os.path.dirname(brew_path)}:{os.environ.get('PATH', '')}"
                            self.available = True
                            break
                
                logger.info("Homebrew安装成功")
                return CommandResult(
                    success=True,
                    stdout=stdout.decode('utf-8'),
                    stderr=stderr.decode('utf-8'),
                    return_code=0,
                    command=' '.join(cmd)
                )
            else:
                logger.error(f"Homebrew安装失败: {stderr.decode('utf-8')}")
                return CommandResult(
                    success=False,
                    stdout=stdout.decode('utf-8'),
                    stderr=stderr.decode('utf-8'),
                    return_code=process.returncode,
                    command=' '.join(cmd)
                )
        
        except Exception as e:
            logger.error(f"Homebrew安装异常: {e}")
            return CommandResult(
                success=False,
                stdout="",
                stderr=str(e),
                return_code=-1,
                command="install homebrew"
            )
    
    async def _run_command(self, cmd: List[str]) -> CommandResult:
        """执行命令"""
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            return CommandResult(
                success=process.returncode == 0,
                stdout=stdout.decode('utf-8'),
                stderr=stderr.decode('utf-8'),
                return_code=process.returncode,
                command=' '.join(cmd)
            )
        except Exception as e:
            logger.error(f"执行命令失败 {' '.join(cmd)}: {e}")
            return CommandResult(
                success=False,
                stdout="",
                stderr=str(e),
                return_code=-1,
                command=' '.join(cmd)
            )

class WingetManager(PackageManager):
    """Winget包管理器(Windows)"""
    
    def __init__(self):
        super().__init__("Winget", "winget")
    
    async def install_package(self, package: str, **kwargs) -> CommandResult:
        """安装Winget包"""
        cmd = ["winget", "install", "--id", package, "--silent", "--accept-package-agreements", "--accept-source-agreements"]
        return await self._run_command(cmd)
    
    async def update_package_list(self) -> CommandResult:
        """更新Winget源"""
        cmd = ["winget", "source", "update"]
        return await self._run_command(cmd)
    
    async def check_package_installed(self, package: str) -> bool:
        """检查Winget包是否已安装"""
        cmd = ["winget", "list", "--id", package]
        result = await self._run_command(cmd)
        return result.success and package in result.stdout
    
    async def _run_command(self, cmd: List[str]) -> CommandResult:
        """执行命令"""
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                shell=True  # Windows需要shell=True
            )
            stdout, stderr = await process.communicate()
            
            return CommandResult(
                success=process.returncode == 0,
                stdout=stdout.decode('utf-8', errors='ignore'),
                stderr=stderr.decode('utf-8', errors='ignore'),
                return_code=process.returncode,
                command=' '.join(cmd)
            )
        except Exception as e:
            logger.error(f"执行命令失败 {' '.join(cmd)}: {e}")
            return CommandResult(
                success=False,
                stdout="",
                stderr=str(e),
                return_code=-1,
                command=' '.join(cmd)
            )

class ChocolateyManager(PackageManager):
    """Chocolatey包管理器(Windows)"""
    
    def __init__(self):
        super().__init__("Chocolatey", "choco")
        self.install_script_url = "https://chocolatey.org/install.ps1"
    
    async def install_package(self, package: str, **kwargs) -> CommandResult:
        """安装Chocolatey包"""
        cmd = ["choco", "install", package, "-y"]
        return await self._run_command(cmd)
    
    async def update_package_list(self) -> CommandResult:
        """更新Chocolatey"""
        cmd = ["choco", "upgrade", "chocolatey"]
        return await self._run_command(cmd)
    
    async def check_package_installed(self, package: str) -> bool:
        """检查Chocolatey包是否已安装"""
        cmd = ["choco", "list", "--local-only", package]
        result = await self._run_command(cmd)
        return result.success and package in result.stdout
    
    async def install_chocolatey(self) -> CommandResult:
        """自动安装Chocolatey"""
        if self.available:
            return CommandResult(
                success=True,
                stdout="Chocolatey已安装",
                stderr="",
                return_code=0,
                command="choco --version"
            )
        
        try:
            logger.info("开始安装Chocolatey...")
            
            # 使用PowerShell安装Chocolatey
            cmd = [
                "powershell", "-Command",
                f"Set-ExecutionPolicy Bypass -Scope Process -Force; "
                f"[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; "
                f"iex ((New-Object System.Net.WebClient).DownloadString('{self.install_script_url}'))"
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                shell=True
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                # 重新检查可用性
                self.available = self._check_availability()
                logger.info("Chocolatey安装成功")
                return CommandResult(
                    success=True,
                    stdout=stdout.decode('utf-8', errors='ignore'),
                    stderr=stderr.decode('utf-8', errors='ignore'),
                    return_code=0,
                    command=' '.join(cmd)
                )
            else:
                logger.error(f"Chocolatey安装失败: {stderr.decode('utf-8', errors='ignore')}")
                return CommandResult(
                    success=False,
                    stdout=stdout.decode('utf-8', errors='ignore'),
                    stderr=stderr.decode('utf-8', errors='ignore'),
                    return_code=process.returncode,
                    command=' '.join(cmd)
                )
        
        except Exception as e:
            logger.error(f"Chocolatey安装异常: {e}")
            return CommandResult(
                success=False,
                stdout="",
                stderr=str(e),
                return_code=-1,
                command="install chocolatey"
            )
    
    async def _run_command(self, cmd: List[str]) -> CommandResult:
        """执行命令"""
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                shell=True
            )
            stdout, stderr = await process.communicate()
            
            return CommandResult(
                success=process.returncode == 0,
                stdout=stdout.decode('utf-8', errors='ignore'),
                stderr=stderr.decode('utf-8', errors='ignore'),
                return_code=process.returncode,
                command=' '.join(cmd)
            )
        except Exception as e:
            logger.error(f"执行命令失败 {' '.join(cmd)}: {e}")
            return CommandResult(
                success=False,
                stdout="",
                stderr=str(e),
                return_code=-1,
                command=' '.join(cmd)
            )

class PlatformManager:
    """统一的平台管理器"""
    
    def __init__(self):
        self.platform_info = self._detect_platform()
        self.package_managers = self._init_package_managers()
        self.available_managers = [pm for pm in self.package_managers if pm.available]
        self.preferred_manager = self._get_preferred_manager()
        
        logger.info(f"平台检测: {self.platform_info.system} {self.platform_info.version}")
        logger.info(f"可用包管理器: {[pm.name for pm in self.available_managers]}")
    
    def _detect_platform(self) -> PlatformInfo:
        """检测当前平台信息"""
        system = platform.system().lower()
        
        if system == "linux":
            platform_type = PlatformType.LINUX
        elif system == "darwin":
            platform_type = PlatformType.MACOS
        elif system == "windows":
            platform_type = PlatformType.WINDOWS
        else:
            platform_type = PlatformType.UNKNOWN
        
        return PlatformInfo(
            system=system,
            platform_type=platform_type,
            version=platform.version(),
            architecture=platform.architecture()[0],
            machine=platform.machine(),
            node=platform.node(),
            processor=platform.processor()
        )
    
    def _init_package_managers(self) -> List[PackageManager]:
        """初始化包管理器"""
        managers = []
        
        if self.platform_info.is_linux:
            managers.extend([
                AptManager(),
                # 可以添加其他Linux包管理器
            ])
        elif self.platform_info.is_macos:
            managers.append(HomebrewManager())
        elif self.platform_info.is_windows:
            managers.extend([
                WingetManager(),
                ChocolateyManager(),
            ])
        
        return managers
    
    def _get_preferred_manager(self) -> Optional[PackageManager]:
        """获取首选包管理器"""
        if not self.available_managers:
            return None
        
        # 平台首选顺序
        preference_order = {
            PlatformType.LINUX: ["APT", "DNF", "YUM", "PACMAN"],
            PlatformType.MACOS: ["Homebrew"],
            PlatformType.WINDOWS: ["Winget", "Chocolatey", "Scoop"]
        }
        
        preferred_names = preference_order.get(self.platform_info.platform_type, [])
        
        for name in preferred_names:
            for manager in self.available_managers:
                if manager.name == name:
                    return manager
        
        # 如果没有找到首选的，返回第一个可用的
        return self.available_managers[0] if self.available_managers else None
    
    async def ensure_package_manager(self) -> Tuple[bool, str]:
        """确保有可用的包管理器"""
        if self.preferred_manager:
            return True, f"使用 {self.preferred_manager.name}"
        
        # 尝试安装包管理器
        if self.platform_info.is_macos:
            homebrew = next((pm for pm in self.package_managers if pm.name == "Homebrew"), None)
            if homebrew:
                result = await homebrew.install_homebrew()
                if result.success:
                    self.available_managers.append(homebrew)
                    self.preferred_manager = homebrew
                    return True, "Homebrew安装成功"
                else:
                    return False, f"Homebrew安装失败: {result.stderr}"
        
        elif self.platform_info.is_windows:
            # 尝试安装Chocolatey
            chocolatey = next((pm for pm in self.package_managers if pm.name == "Chocolatey"), None)
            if chocolatey:
                result = await chocolatey.install_chocolatey()
                if result.success:
                    self.available_managers.append(chocolatey)
                    self.preferred_manager = chocolatey
                    return True, "Chocolatey安装成功"
                else:
                    return False, f"Chocolatey安装失败: {result.stderr}"
        
        return False, "无法安装包管理器"
    
    async def install_package(self, package: str, **kwargs) -> CommandResult:
        """安装包"""
        if not self.preferred_manager:
            success, message = await self.ensure_package_manager()
            if not success:
                return CommandResult(
                    success=False,
                    stdout="",
                    stderr=f"无可用包管理器: {message}",
                    return_code=-1,
                    command=f"install {package}"
                )
        
        return await self.preferred_manager.install_package(package, **kwargs)
    
    async def check_package_installed(self, package: str) -> bool:
        """检查包是否已安装"""
        if not self.preferred_manager:
            return False
        
        return await self.preferred_manager.check_package_installed(package)
    
    async def update_package_list(self) -> CommandResult:
        """更新包列表"""
        if not self.preferred_manager:
            return CommandResult(
                success=False,
                stdout="",
                stderr="无可用包管理器",
                return_code=-1,
                command="update"
            )
        
        return await self.preferred_manager.update_package_list()
    
    def get_platform_specific_paths(self) -> Dict[str, str]:
        """获取平台特定的路径"""
        if self.platform_info.is_windows:
            return {
                "home": os.environ.get("USERPROFILE", "C:\\Users\\Default"),
                "temp": os.environ.get("TEMP", "C:\\Windows\\Temp"),
                "app_data": os.environ.get("APPDATA", ""),
                "local_app_data": os.environ.get("LOCALAPPDATA", ""),
                "program_files": os.environ.get("PROGRAMFILES", "C:\\Program Files"),
            }
        else:
            return {
                "home": os.path.expanduser("~"),
                "temp": "/tmp",
                "usr_local": "/usr/local",
                "opt": "/opt",
            }
    
    def get_platform_specific_commands(self) -> Dict[str, str]:
        """获取平台特定的命令"""
        if self.platform_info.is_windows:
            return {
                "ffmpeg": "ffmpeg.exe",
                "ffprobe": "ffprobe.exe",
                "python": "python.exe",
                "pip": "pip.exe",
                "where": "where",
            }
        else:
            return {
                "ffmpeg": "ffmpeg",
                "ffprobe": "ffprobe",
                "python": "python3",
                "pip": "pip3",
                "which": "which",
            }
    
    async def check_system_resources(self) -> Dict[str, Any]:
        """检查系统资源"""
        try:
            import psutil
            
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                "cpu_percent": cpu_percent,
                "memory_total": memory.total,
                "memory_available": memory.available,
                "memory_percent": memory.percent,
                "disk_total": disk.total,
                "disk_used": disk.used,
                "disk_free": disk.free,
                "disk_percent": (disk.used / disk.total) * 100,
                "platform": self.platform_info.system,
                "architecture": self.platform_info.architecture,
            }
        except ImportError:
            logger.warning("psutil未安装，无法获取系统资源信息")
            return {
                "platform": self.platform_info.system,
                "architecture": self.platform_info.architecture,
            }
    
    def get_package_mapping(self, package_name: str) -> str:
        """获取平台特定的包名映射"""
        # 常见包名映射
        mappings = {
            "ffmpeg": {
                PlatformType.LINUX: "ffmpeg",
                PlatformType.MACOS: "ffmpeg",
                PlatformType.WINDOWS: "FFmpeg"  # Chocolatey包名
            },
            "git": {
                PlatformType.LINUX: "git",
                PlatformType.MACOS: "git",
                PlatformType.WINDOWS: "Git.Git"  # Winget包名
            },
            "python": {
                PlatformType.LINUX: "python3",
                PlatformType.MACOS: "python@3.11",
                PlatformType.WINDOWS: "Python.Python.3.11"
            }
        }
        
        platform_mapping = mappings.get(package_name, {})
        return platform_mapping.get(self.platform_info.platform_type, package_name)

# 全局平台管理器实例
_platform_manager_instance = None

def get_platform_manager() -> PlatformManager:
    """获取平台管理器单例"""
    global _platform_manager_instance
    if _platform_manager_instance is None:
        _platform_manager_instance = PlatformManager()
    return _platform_manager_instance