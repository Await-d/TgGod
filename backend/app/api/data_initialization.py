"""数据初始化API端点

提供完整的数据初始化和迁移功能的RESTful API接口。
绝不使用Mock数据，只提供真实数据的初始化和设置指导。

Endpoints:
    - GET /api/data-initialization/status - 获取初始化状态
    - POST /api/data-initialization/start - 开始完整初始化
    - POST /api/data-initialization/quick-setup - 快速设置向导
    - POST /api/data-initialization/migrate - 数据迁移
    - GET /api/data-initialization/progress/{migration_id} - 获取迁移进度
    - POST /api/data-initialization/rollback/{migration_id} - 回滚迁移

Author: TgGod Team
Version: 1.0.0
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
import asyncio
import json
from datetime import datetime

from ..database import get_db
from ..utils.complete_data_initialization import CompleteDataInitializer, initialize_system_data, quick_setup, get_system_status
from ..migrations.real_data_migration import RealDataMigrator, MigrationConfig, migrate_telegram_export, migrate_csv_data, get_migration_status
from ..core.error_handler import ErrorHandler
from ..core.batch_logging import BatchLogger

router = APIRouter(prefix="/api/data-initialization", tags=["data-initialization"])
error_handler = ErrorHandler()
batch_logger = BatchLogger("data_initialization_api")

# 请求/响应模型
class InitializationStatusResponse(BaseModel):
    """初始化状态响应模型"""
    database_connected: bool
    groups_available: int
    messages_available: int
    rules_configured: int
    tasks_available: int
    last_sync: Optional[datetime]
    initialization_required: bool
    recommendations: List[str] = []
    error: Optional[str] = None

class InitializationStartRequest(BaseModel):
    """初始化启动请求模型"""
    force_reinitialize: bool = False
    include_sample_data: bool = True
    skip_telegram_check: bool = False

class QuickSetupResponse(BaseModel):
    """快速设置响应模型"""
    success: bool
    steps: List[Dict[str, Any]]
    recommendations: List[str] = []
    next_actions: List[str] = []

class MigrationRequest(BaseModel):
    """数据迁移请求模型"""
    migration_type: str = Field(..., description="迁移类型: telegram_export, csv_file")
    source_file_path: Optional[str] = None
    mapping_config: Optional[Dict[str, str]] = None
    config: Optional[Dict[str, Any]] = None

class MigrationProgressResponse(BaseModel):
    """迁移进度响应模型"""
    migration_id: str
    current_phase: str
    progress_percentage: float
    items_processed: int
    items_successful: int
    items_failed: int
    success_rate: float
    estimated_completion: Optional[datetime]
    elapsed_time: float

# 全局变量存储活跃的迁移任务
active_migrations: Dict[str, RealDataMigrator] = {}


@router.get("/status", response_model=InitializationStatusResponse)
async def get_initialization_status(db: Session = Depends(get_db)):
    """获取系统初始化状态
    
    返回当前系统的数据初始化状态，包括数据统计和建议。
    """
    try:
        batch_logger.info("获取数据初始化状态")
        
        status = get_system_status()
        
        # 添加建议
        recommendations = []
        if status["initialization_required"]:
            if status["groups_available"] == 0:
                recommendations.append("建议添加Telegram群组以获取真实数据")
            if status["messages_available"] < 50:
                recommendations.append("建议同步更多消息数据以改善演示效果")
            if status["rules_configured"] == 0:
                recommendations.append("建议配置过滤规则以自动化下载管理")
        
        return InitializationStatusResponse(
            **status,
            recommendations=recommendations
        )
        
    except Exception as e:
        batch_logger.error(f"获取初始化状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取初始化状态失败: {str(e)}")


@router.post("/start")
async def start_initialization(
    request: InitializationStartRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """开始完整的数据初始化流程
    
    启动完整的数据初始化过程，包括Telegram连接、群组发现、
    消息同步、规则验证和任务系统检查。
    """
    try:
        batch_logger.info("开始完整数据初始化", extra={
            "force_reinitialize": request.force_reinitialize,
            "include_sample_data": request.include_sample_data
        })
        
        # 检查是否需要强制重新初始化
        if not request.force_reinitialize:
            status = get_system_status()
            if not status["initialization_required"]:
                return JSONResponse(
                    status_code=200,
                    content={
                        "message": "系统已初始化完成",
                        "status": status,
                        "suggestion": "如需重新初始化，请设置 force_reinitialize=true"
                    }
                )
        
        # 在后台启动初始化任务
        background_tasks.add_task(
            _perform_background_initialization,
            request.dict(),
            db
        )
        
        return JSONResponse(
            status_code=202,
            content={
                "message": "数据初始化已启动",
                "status": "processing",
                "note": "初始化正在后台进行，请通过 /status 端点查看进度"
            }
        )
        
    except Exception as e:
        batch_logger.error(f"启动初始化失败: {e}")
        raise HTTPException(status_code=500, detail=f"启动初始化失败: {str(e)}")


async def _perform_background_initialization(request_data: Dict[str, Any], db: Session):
    """在后台执行初始化任务"""
    try:
        initializer = CompleteDataInitializer(db)
        result = await initializer.perform_complete_initialization()
        
        batch_logger.info("后台初始化完成", extra={
            "success": result.get("success", False),
            "steps_completed": len(result.get("steps_completed", [])),
            "errors": len(result.get("errors", []))
        })
        
    except Exception as e:
        batch_logger.error(f"后台初始化失败: {e}")


@router.post("/quick-setup", response_model=QuickSetupResponse)
async def quick_setup_wizard(db: Session = Depends(get_db)):
    """快速设置向导
    
    提供简化的快速设置流程，适用于快速体验系统功能。
    自动完成基础配置和数据同步。
    """
    try:
        batch_logger.info("开始快速设置向导")
        
        result = await quick_setup()
        
        # 生成下一步操作建议
        next_actions = []
        if result["success"]:
            next_actions.extend([
                "访问群组管理页面查看同步的群组",
                "检查规则配置并根据需要调整",
                "开始创建下载任务测试功能"
            ])
        else:
            next_actions.extend([
                "检查Telegram连接配置",
                "确认已加入至少一个Telegram群组",
                "查看系统日志获取详细错误信息"
            ])
        
        return QuickSetupResponse(
            success=result["success"],
            steps=result["steps"],
            recommendations=[],
            next_actions=next_actions
        )
        
    except Exception as e:
        batch_logger.error(f"快速设置失败: {e}")
        raise HTTPException(status_code=500, detail=f"快速设置失败: {str(e)}")


@router.post("/migrate")
async def start_data_migration(
    migration_request: MigrationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """启动数据迁移任务
    
    支持从Telegram导出文件或CSV文件迁移数据。
    迁移任务在后台异步执行。
    """
    try:
        batch_logger.info(f"启动数据迁移: {migration_request.migration_type}")
        
        # 验证迁移配置
        if migration_request.migration_type == "telegram_export":
            if not migration_request.source_file_path:
                raise HTTPException(status_code=400, detail="Telegram导出迁移需要提供源文件路径")
        elif migration_request.migration_type == "csv_file":
            if not migration_request.source_file_path or not migration_request.mapping_config:
                raise HTTPException(status_code=400, detail="CSV迁移需要提供源文件路径和字段映射配置")
        else:
            raise HTTPException(status_code=400, detail=f"不支持的迁移类型: {migration_request.migration_type}")
        
        # 创建迁移配置
        config = MigrationConfig()
        if migration_request.config:
            for key, value in migration_request.config.items():
                if hasattr(config, key):
                    setattr(config, key, value)
        
        # 创建迁移器
        migrator = RealDataMigrator(config, db)
        migration_id = migrator.migration_id
        
        # 存储活跃迁移
        active_migrations[migration_id] = migrator
        
        # 在后台启动迁移任务
        background_tasks.add_task(
            _perform_background_migration,
            migration_id,
            migration_request.dict()
        )
        
        return JSONResponse(
            status_code=202,
            content={
                "message": "数据迁移已启动",
                "migration_id": migration_id,
                "status": "processing",
                "progress_endpoint": f"/api/data-initialization/progress/{migration_id}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        batch_logger.error(f"启动迁移失败: {e}")
        raise HTTPException(status_code=500, detail=f"启动迁移失败: {str(e)}")


async def _perform_background_migration(migration_id: str, migration_data: Dict[str, Any]):
    """在后台执行迁移任务"""
    try:
        migrator = active_migrations.get(migration_id)
        if not migrator:
            batch_logger.error(f"未找到迁移器: {migration_id}")
            return
        
        migration_type = migration_data["migration_type"]
        
        if migration_type == "telegram_export":
            result = await migrator.migrate_from_telegram_export(
                migration_data["source_file_path"]
            )
        elif migration_type == "csv_file":
            result = await migrator.migrate_from_csv_file(
                migration_data["source_file_path"],
                migration_data["mapping_config"]
            )
        
        batch_logger.info(f"迁移完成: {migration_id}", extra={
            "success": result.get("success", False),
            "migration_type": migration_type
        })
        
    except Exception as e:
        batch_logger.error(f"后台迁移失败: {migration_id} - {e}")
    finally:
        # 清理活跃迁移
        if migration_id in active_migrations:
            del active_migrations[migration_id]


@router.get("/progress/{migration_id}", response_model=MigrationProgressResponse)
async def get_migration_progress(migration_id: str):
    """获取迁移进度
    
    返回指定迁移任务的详细进度信息。
    """
    try:
        migrator = active_migrations.get(migration_id)
        if not migrator:
            # 尝试从状态文件获取
            status = get_migration_status(migration_id)
            if "error" in status:
                raise HTTPException(status_code=404, detail="未找到指定的迁移任务")
            return MigrationProgressResponse(**status)
        
        progress = migrator.get_migration_progress()
        return MigrationProgressResponse(**progress)
        
    except HTTPException:
        raise
    except Exception as e:
        batch_logger.error(f"获取迁移进度失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取迁移进度失败: {str(e)}")


@router.post("/rollback/{migration_id}")
async def rollback_migration(migration_id: str, db: Session = Depends(get_db)):
    """回滚数据迁移
    
    将指定的迁移回滚到迁移前的状态。
    需要存在相应的备份数据。
    """
    try:
        batch_logger.info(f"开始回滚迁移: {migration_id}")
        
        migrator = RealDataMigrator(db=db)
        result = await migrator.rollback_migration(migration_id)
        
        if result["success"]:
            return JSONResponse(
                status_code=200,
                content={
                    "message": f"迁移 {migration_id} 回滚成功",
                    "rollback_details": result
                }
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"迁移回滚失败: {result.get('error', '未知错误')}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        batch_logger.error(f"回滚迁移失败: {e}")
        raise HTTPException(status_code=500, detail=f"回滚迁移失败: {str(e)}")


@router.post("/upload-export")
async def upload_export_file(
    file: UploadFile = File(...),
    migration_type: str = Form(...),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """上传导出文件并启动迁移
    
    允许用户上传Telegram导出文件或CSV文件，
    系统自动保存文件并启动相应的迁移任务。
    """
    try:
        # 验证文件类型
        allowed_extensions = {
            "telegram_export": [".json", ".zip"],
            "csv_file": [".csv"]
        }
        
        if migration_type not in allowed_extensions:
            raise HTTPException(status_code=400, detail=f"不支持的迁移类型: {migration_type}")
        
        file_extension = "." + file.filename.split(".")[-1].lower()
        if file_extension not in allowed_extensions[migration_type]:
            raise HTTPException(
                status_code=400,
                detail=f"{migration_type} 不支持 {file_extension} 格式文件"
            )
        
        # 保存上传的文件
        import tempfile
        import shutil
        from pathlib import Path
        
        upload_dir = Path("uploads/data_migration")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        saved_filename = f"{migration_type}_{timestamp}_{file.filename}"
        saved_file_path = upload_dir / saved_filename
        
        with open(saved_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 启动迁移任务
        migration_request = MigrationRequest(
            migration_type=migration_type,
            source_file_path=str(saved_file_path)
        )
        
        # 对于CSV文件，提供默认的字段映射
        if migration_type == "csv_file":
            migration_request.mapping_config = {
                "id": "message_id",
                "group_id": "group_id", 
                "text": "text",
                "date": "date",
                "sender": "sender_username"
            }
        
        return await start_data_migration(migration_request, background_tasks, db)
        
    except HTTPException:
        raise
    except Exception as e:
        batch_logger.error(f"上传文件迁移失败: {e}")
        raise HTTPException(status_code=500, detail=f"上传文件迁移失败: {str(e)}")


@router.get("/recommendations")
async def get_initialization_recommendations(db: Session = Depends(get_db)):
    """获取数据初始化建议
    
    基于当前系统状态提供个性化的数据初始化建议。
    """
    try:
        status = get_system_status()
        recommendations = []
        
        # 基于状态生成建议
        if not status["database_connected"]:
            recommendations.append({
                "type": "critical",
                "title": "数据库连接问题",
                "description": "数据库连接失败，请检查数据库配置",
                "actions": ["检查DATABASE_URL配置", "确认数据库服务运行", "查看数据库日志"]
            })
        
        if status["groups_available"] == 0:
            recommendations.append({
                "type": "important",
                "title": "添加Telegram群组",
                "description": "系统中没有群组数据，建议添加群组",
                "actions": [
                    "确保已配置Telegram API",
                    "加入一些活跃的群组",
                    "使用快速设置向导同步群组"
                ]
            })
        
        if status["messages_available"] < 50:
            recommendations.append({
                "type": "suggestion",
                "title": "增加消息数据",
                "description": "消息数据较少，建议同步更多历史消息",
                "actions": [
                    "等待群组产生更多消息",
                    "导入Telegram历史数据",
                    "加入更活跃的群组"
                ]
            })
        
        if status["rules_configured"] == 0:
            recommendations.append({
                "type": "suggestion",
                "title": "配置过滤规则",
                "description": "没有配置过滤规则，建议设置自动化规则",
                "actions": [
                    "访问规则管理页面",
                    "创建基础的媒体类型过滤规则",
                    "设置文件大小限制规则"
                ]
            })
        
        return JSONResponse(
            status_code=200,
            content={
                "system_status": status,
                "recommendations": recommendations,
                "quick_actions": [
                    {"title": "快速设置", "endpoint": "/api/data-initialization/quick-setup"},
                    {"title": "完整初始化", "endpoint": "/api/data-initialization/start"},
                    {"title": "数据迁移", "endpoint": "/api/data-initialization/migrate"}
                ]
            }
        )
        
    except Exception as e:
        batch_logger.error(f"获取初始化建议失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取初始化建议失败: {str(e)}")


@router.delete("/cleanup")
async def cleanup_initialization_data(db: Session = Depends(get_db)):
    """清理初始化数据
    
    清理初始化过程中产生的临时数据和测试数据。
    """
    try:
        batch_logger.info("开始清理初始化数据")
        
        initializer = CompleteDataInitializer(db)
        initializer.cleanup_initialization_data()
        
        # 清理上传的文件
        import shutil
        from pathlib import Path
        
        upload_dir = Path("uploads/data_migration")
        if upload_dir.exists():
            shutil.rmtree(upload_dir)
            upload_dir.mkdir(parents=True, exist_ok=True)
        
        # 清理临时文件
        temp_dir = Path("temp")
        if temp_dir.exists():
            for migration_dir in temp_dir.glob("migration_*"):
                if migration_dir.is_dir():
                    shutil.rmtree(migration_dir)
        
        return JSONResponse(
            status_code=200,
            content={
                "message": "初始化数据清理完成",
                "cleaned_items": [
                    "验证任务数据",
                    "上传的迁移文件",
                    "临时迁移目录"
                ]
            }
        )
        
    except Exception as e:
        batch_logger.error(f"清理初始化数据失败: {e}")
        raise HTTPException(status_code=500, detail=f"清理初始化数据失败: {str(e)}")


# 错误处理
@router.exception_handler(Exception)
async def data_initialization_exception_handler(request, exc):
    """数据初始化API的统一错误处理"""
    return await error_handler.handle_api_error(request, exc)