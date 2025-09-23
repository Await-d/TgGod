"""
服务管理API端点
提供手动触发服务安装、查看安装状态等功能
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import logging
from datetime import datetime

from ..services.service_installer import service_installer
from ..core.migration_runner import run_migrations
from ..config import settings
from ..websocket.manager import websocket_manager

logger = logging.getLogger(__name__)

router = APIRouter()

# 请求/响应模型
class ServiceInstallRequest(BaseModel):
    force_reinstall: Optional[bool] = False
    specific_services: Optional[List[str]] = None
    skip_verification: Optional[bool] = False

class ServiceInstallResponse(BaseModel):
    success: bool
    message: str
    platform_info: Dict[str, Any]
    package_managers: Dict[str, Any]
    installed_services: List[Dict[str, Any]]
    failed_services: List[Dict[str, Any]]
    already_installed: List[str]
    skipped_services: List[Dict[str, Any]]
    total_checks: int
    installation_time: float

class MigrationRequest(BaseModel):
    operation: str  # "upgrade" or "rollback"
    target_migration: Optional[str] = None

class MigrationResponse(BaseModel):
    success: bool
    message: str
    applied_count: int
    failed_count: int
    applied_migrations: List[str]
    failed_migrations: List[str]

@router.get("/platform-info")
async def get_platform_info():
    """获取平台信息和包管理器状态"""
    try:
        platform_info = {
            "system": service_installer.platform_info.system,
            "arch": service_installer.platform_info.arch,
            "is_docker": service_installer.platform_info.is_docker,
            "distro_info": service_installer.platform_info.distro_info
        }
        
        package_managers_info = []
        for pm in service_installer.package_managers:
            package_managers_info.append({
                "name": pm.name,
                "available": pm.available,
                "is_primary": pm == service_installer.best_manager
            })
        
        return {
            "success": True,
            "platform_info": platform_info,
            "package_managers": package_managers_info,
            "best_manager": service_installer.best_manager.name if service_installer.best_manager else None
        }
        
    except Exception as e:
        logger.error(f"获取平台信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取平台信息失败: {str(e)}")

@router.get("/installation-status")
async def get_installation_status():
    """获取当前安装状态"""
    try:
        # 检查关键服务的安装状态
        import shutil
        
        status = {
            "ffmpeg": {
                "installed": shutil.which("ffmpeg") is not None,
                "path": shutil.which("ffmpeg")
            },
            "system_tools": {
                "curl": shutil.which("curl") is not None,
                "wget": shutil.which("wget") is not None,
                "git": shutil.which("git") is not None,
                "unzip": shutil.which("unzip") is not None
            },
            "media_tools": {
                "imagemagick": shutil.which("convert") is not None or shutil.which("magick") is not None,
                "exiftool": shutil.which("exiftool") is not None
            },
            "python_packages": {}
        }
        
        # 检查Python包
        python_packages = ["PIL", "requests", "telethon", "fastapi", "sqlalchemy", "psutil", "cpuinfo"]
        for pkg in python_packages:
            try:
                __import__(pkg)
                status["python_packages"][pkg] = True
            except ImportError:
                status["python_packages"][pkg] = False
        
        # 计算总体状态
        total_checks = (
            1 +  # ffmpeg
            len(status["system_tools"]) +
            len(status["media_tools"]) +
            len(status["python_packages"])
        )
        
        passed_checks = (
            (1 if status["ffmpeg"]["installed"] else 0) +
            sum(1 for v in status["system_tools"].values() if v) +
            sum(1 for v in status["media_tools"].values() if v) +
            sum(1 for v in status["python_packages"].values() if v)
        )
        
        success_rate = (passed_checks / total_checks) * 100 if total_checks > 0 else 0
        
        return {
            "success": True,
            "status": status,
            "summary": {
                "total_checks": total_checks,
                "passed_checks": passed_checks,
                "success_rate": success_rate,
                "is_healthy": success_rate >= 80
            }
        }
        
    except Exception as e:
        logger.error(f"获取安装状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取安装状态失败: {str(e)}")

@router.post("/install", response_model=ServiceInstallResponse)
async def install_services(
    request: ServiceInstallRequest,
    background_tasks: BackgroundTasks
):
    """手动触发服务安装"""
    try:
        logger.info(f"🚀 手动触发服务安装: {request}")
        
        start_time = datetime.now()
        
        # 设置WebSocket管理器以支持实时进度通知
        service_installer.progress_reporter.websocket_manager = websocket_manager
        
        # 执行安装
        result = await service_installer.check_and_install_all()
        
        installation_time = (datetime.now() - start_time).total_seconds()
        
        response = ServiceInstallResponse(
            success=result["success"],
            message="服务安装完成" if result["success"] else "服务安装部分失败",
            platform_info=result["platform_info"],
            package_managers=result["package_managers"],
            installed_services=result["installed_services"],
            failed_services=result["failed_services"],
            already_installed=result["already_installed"],
            skipped_services=result["skipped_services"],
            total_checks=result["total_checks"],
            installation_time=installation_time
        )
        
        logger.info(f"✅ 服务安装完成，耗时: {installation_time:.2f}秒")
        
        return response
        
    except Exception as e:
        logger.error(f"❌ 手动安装服务失败: {e}")
        raise HTTPException(status_code=500, detail=f"服务安装失败: {str(e)}")

@router.post("/package-managers/setup")
async def setup_package_managers():
    """设置包管理器（安装Homebrew、Chocolatey等）"""
    try:
        logger.info("🔧 开始设置包管理器...")
        
        service_installer.progress_reporter.websocket_manager = websocket_manager
        result = await service_installer._setup_package_managers()
        
        if result["success"]:
            return {
                "success": True,
                "message": "包管理器设置成功",
                "details": result.get("details", ""),
                "action": result.get("action", "")
            }
        else:
            raise HTTPException(
                status_code=500, 
                detail=f"包管理器设置失败: {result.get('error', '未知错误')}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 包管理器设置失败: {e}")
        raise HTTPException(status_code=500, detail=f"包管理器设置失败: {str(e)}")

@router.get("/logs/installation")
async def get_installation_logs():
    """获取安装日志"""
    try:
        logs = service_installer.install_log
        return {
            "success": True,
            "logs": logs,
            "count": len(logs)
        }
    except Exception as e:
        logger.error(f"获取安装日志失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取安装日志失败: {str(e)}")

@router.post("/migrations/run", response_model=MigrationResponse)
async def run_database_migrations(request: MigrationRequest):
    """运行数据库迁移"""
    try:
        logger.info(f"🔄 开始运行数据库迁移: {request.operation}")
        
        if request.operation not in ["upgrade", "rollback"]:
            raise HTTPException(
                status_code=400, 
                detail="操作类型必须是 'upgrade' 或 'rollback'"
            )
        
        # 运行迁移
        migrations_dir = str(settings.BASE_DIR / "migrations")
        result = await run_migrations(
            settings.DATABASE_URL,
            migrations_dir,
            websocket_manager
        )
        
        response = MigrationResponse(
            success=result["success"],
            message="数据库迁移完成" if result["success"] else "数据库迁移失败",
            applied_count=result.get("applied_count", 0),
            failed_count=result.get("failed_count", 0),
            applied_migrations=result.get("applied_migrations", []),
            failed_migrations=result.get("failed_migrations", [])
        )
        
        logger.info(f"✅ 数据库迁移完成: {response}")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 数据库迁移失败: {e}")
        raise HTTPException(status_code=500, detail=f"数据库迁移失败: {str(e)}")

@router.get("/migrations/status")
async def get_migration_status():
    """获取迁移状态"""
    try:
        from ..core.migration_runner import MigrationRunner
        
        migrations_dir = str(settings.BASE_DIR / "migrations")
        runner = MigrationRunner(settings.DATABASE_URL, migrations_dir)
        
        pending_migrations = runner.get_pending_migrations()
        migration_history = runner.get_migration_history()
        
        return {
            "success": True,
            "pending_migrations": [m.name for m in pending_migrations],
            "pending_count": len(pending_migrations),
            "migration_history": migration_history,
            "last_migration": migration_history[0] if migration_history else None
        }
        
    except Exception as e:
        logger.error(f"获取迁移状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取迁移状态失败: {str(e)}")

@router.delete("/services/cleanup")
async def cleanup_services():
    """清理服务（清理备份文件等）"""
    try:
        logger.info("🧹 开始清理服务...")
        
        # 清理SQLite备份文件
        service_installer.sqlite_manager.cleanup_old_backups(keep_count=5)
        
        return {
            "success": True,
            "message": "服务清理完成"
        }
        
    except Exception as e:
        logger.error(f"❌ 服务清理失败: {e}")
        raise HTTPException(status_code=500, detail=f"服务清理失败: {str(e)}")

@router.get("/health/detailed")
async def get_detailed_health():
    """获取详细的系统健康状态"""
    try:
        # 获取平台信息
        platform_result = await get_platform_info()
        
        # 获取安装状态
        status_result = await get_installation_status()
        
        # 获取迁移状态  
        migration_result = await get_migration_status()
        
        # 组合详细健康报告
        health_report = {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "platform": platform_result,
            "services": status_result,
            "migrations": migration_result,
            "overall_health": {
                "is_healthy": (
                    platform_result["success"] and
                    status_result["summary"]["is_healthy"] and
                    migration_result["success"] and
                    migration_result["pending_count"] == 0
                ),
                "issues": []
            }
        }
        
        # 检查潜在问题
        if not status_result["summary"]["is_healthy"]:
            health_report["overall_health"]["issues"].append(
                f"服务安装不完整: {status_result['summary']['success_rate']:.1f}%"
            )
        
        if migration_result["pending_count"] > 0:
            health_report["overall_health"]["issues"].append(
                f"有 {migration_result['pending_count']} 个待应用的数据库迁移"
            )
        
        return health_report
        
    except Exception as e:
        logger.error(f"获取详细健康状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取健康状态失败: {str(e)}")