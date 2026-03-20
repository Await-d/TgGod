"""TgGod主应用模块

这是TgGod Telegram群组规则下载系统的主要应用程序入口点。
该模块负责:

- FastAPI应用程序的初始化和配置
- 应用程序生命周期管理(启动/关闭)
- 服务依赖的自动安装和监控
- 数据库结构的检查和修复
- API路由的注册和WebSocket连接管理
- 全局异常处理和请求日志记录
- 静态媒体文件服务

Author: TgGod Team
Version: 1.0.0
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from .database import engine, Base
from .config import settings, init_settings
from .core.startup_pipeline import StartupPipeline, StartupStage
from .api import (
    telegram,
    rule,
    log,
    task,
    config,
    auth,
    user_settings,
    dashboard,
    database_check,
    download_history,
    real_data_api,
    data_initialization,
    complete_health_monitoring,
    services,
)
from .tasks.message_sync import message_sync_task
import logging
import os
import json
import time

# 初始化日志系统（优先使用批处理日志）
try:
    from .core.logging_config import configure_service_logging

    configure_service_logging()
    print("✅ 批处理日志系统初始化成功")
except Exception as e:
    # 降级到传统日志系统
    print(f"⚠️ 批处理日志初始化失败，使用传统日志: {e}")

    try:
        log_level = settings.log_level.upper()
    except Exception as e:
        log_level = "INFO"
        print(f"获取日志级别失败，使用默认INFO: {e}")

    try:
        log_file = settings.log_file
    except Exception as e:
        log_file = "/app/logs/app.log"
        print(f"获取日志文件路径失败，使用默认路径: {e}")
        # 确保日志目录存在
        os.makedirs(os.path.dirname(log_file), exist_ok=True)

    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
    )

# 获取高性能日志记录器
try:
    from .core.logging_config import get_logger

    logger = get_logger(__name__, use_batch=True)
except Exception:
    logger = logging.getLogger(__name__)


async def _run_dependency_stage() -> None:
    """安装依赖并启动监控组件"""
    try:
        logger.info("🔍 开始检查和安装必要服务...")

        from .services.service_installer import service_installer

        install_mode = getattr(settings, "install_mode", "full") or "full"
        install_mode = install_mode.lower()

        service_installer.progress_reporter.websocket_manager = websocket_manager

        if install_mode == "skip":
            logger.info("INSTALL_MODE=skip，跳过依赖安装阶段")
            installation_result = {
                "success": True,
                "installed_services": [],
                "failed_services": [],
                "already_installed": [],
                "skipped_services": ["all"],
            }
        elif install_mode == "minimal":
            logger.info("INSTALL_MODE=minimal，仅执行依赖检测")
            installation_result = await service_installer.verify_dependencies()
        else:
            installation_result = await service_installer.check_and_install_all()

        if installation_result["success"]:
            logger.info("✅ 服务依赖检查完成")

            stats = {
                "新安装": len(installation_result["installed_services"]),
                "已存在": len(installation_result["already_installed"]),
                "跳过": len(installation_result["skipped_services"]),
                "失败": len(installation_result["failed_services"]),
            }
            logger.info(f"📊 服务统计: {stats}")

            if installation_result["failed_services"]:
                logger.warning("⚠️ 以下服务安装失败，可能影响某些功能:")
                for failed in installation_result["failed_services"]:
                    logger.warning(f"  - {failed['name']}: {failed['error']}")
                logger.warning("建议手动安装这些服务以确保完整功能")

            if installation_result["installed_services"]:
                logger.info("🎉 新安装的服务:")
                for installed in installation_result["installed_services"]:
                    logger.info(f"  - {installed['name']}: {installed['details']}")
        else:
            logger.error(
                f"❌ 服务依赖检查失败: {installation_result.get('error', '未知错误')}"
            )
            logger.warning("系统将继续启动，但某些功能可能不可用")

    except Exception as e:  # noqa: BLE001
        logger.error(f"服务安装检查过程异常: {e}")
        logger.warning("系统将继续启动，但建议检查服务依赖")

    try:
        from .services.service_monitor import service_monitor

        await service_monitor.start_monitoring()
        logger.info("✅ 服务监控器启动成功")
    except Exception as e:  # noqa: BLE001
        logger.error(f"服务监控器启动失败: {e}")
        logger.warning("服务监控功能不可用，但系统将继续运行")

    try:
        from .core.session_store import get_session_store

        await get_session_store()
        logger.info("✅ Redis会话存储初始化成功")
    except Exception as e:  # noqa: BLE001
        logger.error(f"Redis会话存储初始化失败: {e}")
        logger.warning("会话存储功能可能不可用，建议检查Redis连接")

    try:
        from .services.complete_health_monitoring import (
            start_complete_health_monitoring,
        )

        await start_complete_health_monitoring()
        logger.info("✅ 完整健康监控和自动恢复系统启动成功")
    except Exception as e:  # noqa: BLE001
        logger.error(f"完整健康监控系统启动失败: {e}")
        logger.warning("自动恢复功能不可用，但系统将继续运行")

    try:
        from .websocket.production_status_manager import production_status_manager

        await production_status_manager.start_monitoring()
        logger.info("✅ 生产状态管理器启动成功")
    except Exception as e:  # noqa: BLE001
        logger.error(f"生产状态管理器启动失败: {e}")
        logger.warning("实时状态监控不可用，但系统将继续运行")


async def _run_database_stage() -> None:
    """执行数据库检查、修复与优化"""
    try:
        logger.info("🔧 开始数据库结构检查和自动修复...")
        from .utils.database_checker import get_database_checker

        database_checker = get_database_checker()
        check_success = database_checker.run_startup_check()

        if check_success:
            logger.info("✅ 数据库结构检查和修复完成")
        else:
            logger.warning("⚠️ 数据库结构存在问题，但系统将继续启动")
            logger.warning("建议手动运行 'alembic upgrade head' 来完成数据库迁移")
    except Exception as e:  # noqa: BLE001
        logger.error(f"数据库结构检查失败: {e}")
        logger.info("尝试使用传统方式创建数据库表...")
        try:
            from .database import engine, Base
            from . import models  # 导入所有模型以注册到Base.metadata

            Base.metadata.create_all(bind=engine)
            logger.info("✅ 使用传统方式创建数据库表成功")
        except Exception as create_error:  # noqa: BLE001
            logger.error(f"❌ 创建数据库表失败: {create_error}")

    try:
        logger.info("🔧 运行传统数据库字段检查...")
        from pathlib import Path
        import sys

        project_root = Path(__file__).parent.parent
        sys.path.insert(0, str(project_root))

        from fix_database_schema import fix_telegram_messages_table, get_database_path

        db_path = get_database_path()
        logger.info(f"数据库路径: {db_path}")

        success = fix_telegram_messages_table(db_path)
        if success:
            logger.info("✅ 传统数据库字段检查和修复完成")
        else:
            logger.error("❌ 传统数据库字段修复失败")
    except Exception as e:  # noqa: BLE001
        logger.error(f"传统数据库字段检查失败: {e}")

    try:
        logger.info("🔧 正在检查用户设置表和下载状态字段...")
        from importlib.util import spec_from_file_location, module_from_spec
        from pathlib import Path

        project_root = Path(__file__).parent.parent

        migrations = [
            ("add_user_settings_table", "用户设置表"),
            ("add_is_downloading_field", "下载状态字段"),
        ]

        for migration_name, migration_desc in migrations:
            migration_file = project_root / "migrations" / f"{migration_name}.py"
            if migration_file.exists():
                logger.info(f"找到{migration_desc}迁移脚本: {migration_file}")

                spec = spec_from_file_location(migration_name, migration_file)
                migration_module = module_from_spec(spec)
                spec.loader.exec_module(migration_module)

                success, message = migration_module.run_migration()
                if success:
                    logger.info(f"✅ {migration_desc}检查完成: {message}")
                else:
                    logger.warning(f"⚠️ {migration_desc}检查警告: {message}")
            else:
                logger.warning(f"未找到{migration_desc}迁移脚本，将跳过自动迁移")
    except Exception as e:  # noqa: BLE001
        logger.error(f"运行数据库迁移脚本时出错: {e}")
        logger.warning("将继续启动，但数据库表结构可能不完整")

    try:
        from pathlib import Path

        db_utils_file = Path(__file__).parent / "utils" / "db_utils.py"
        if db_utils_file.exists():
            logger.info(f"找到数据库工具脚本: {db_utils_file}")

            from .utils.db_utils import check_and_fix_database_on_startup
            from .database import SessionLocal

            db = SessionLocal()
            try:
                db_check_results = check_and_fix_database_on_startup(db)
                logger.info(f"🔧 数据库自动检查结果: {db_check_results['status']}")

                for table, detail in db_check_results.get("details", {}).items():
                    if detail["status"] == "error":
                        logger.error(f"❌ 表 {table}: {detail['message']}")
                    elif detail["status"] == "fixed":
                        logger.info(f"✅ 表 {table}: {detail['message']}")
                    else:
                        logger.debug(f"✓ 表 {table}: {detail['message']}")
            finally:
                db.close()
        else:
            logger.warning("未找到数据库工具脚本，跳过自动检查")
            from .database import engine, Base

            logger.info("创建基本表结构...")
            Base.metadata.create_all(bind=engine)
    except Exception as e:  # noqa: BLE001
        logger.error(f"数据库自动检查和修复过程中出现错误: {e}")
        logger.warning("系统将继续启动，但数据库结构可能不完整")

    try:
        logger.info("🔧 开始运行数据库字段修复脚本...")
        from pathlib import Path
        import subprocess
        import sys

        project_root = Path(__file__).parent.parent
        repair_scripts = [
            ("scripts/database/fix_task_fields.py", "任务表字段修复"),
            ("scripts/database/fix_filter_rules_fields.py", "过滤规则表字段修复"),
            ("scripts/database/fix_incremental_fields.py", "增量查询字段修复"),
            (
                "scripts/database/remove_rule_group_id_field.py",
                "移除规则表group_id字段",
            ),
            ("scripts/database/add_advanced_rule_fields.py", "添加高级规则过滤字段"),
            (
                "scripts/database/create_task_rule_association_table.py",
                "创建任务-规则多对多关联表",
            ),
        ]

        for script_name, description in repair_scripts:
            script_path = project_root / script_name
            if script_path.exists():
                logger.info(f"运行{description}脚本...")
                result = subprocess.run(
                    [sys.executable, str(script_path)],
                    capture_output=True,
                    text=True,
                    cwd=str(project_root),
                )
                if result.returncode == 0:
                    logger.info(f"✅ {description}完成")
                else:
                    logger.error(f"❌ {description}失败: {result.stderr}")
            else:
                logger.warning(f"未找到{script_name}，跳过{description}")

        logger.info("🎯 所有数据库字段修复脚本执行完成")
    except Exception as e:  # noqa: BLE001
        logger.error(f"运行数据库字段修复脚本失败: {e}")
        logger.warning("将继续启动，但可能出现字段访问错误")

    try:
        logger.info("🏥 执行数据库健康检查...")
        from pathlib import Path
        import subprocess
        import sys

        health_check_script = Path(__file__).parent.parent / "database_health_check.py"
        if health_check_script.exists():
            result = subprocess.run(
                [sys.executable, str(health_check_script)],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                logger.info("✅ 数据库健康检查完成")
            else:
                logger.warning(f"数据库健康检查异常: {result.stderr}")
        else:
            logger.info("未找到健康检查脚本，跳过检查")
    except Exception as e:  # noqa: BLE001
        logger.error(f"数据库健康检查失败: {e}")

    try:
        logger.info("🔧 开始重置异常任务状态...")
        from .database import get_db
        from .models.rule import DownloadTask
        from sqlalchemy.orm import Session

        db_gen = get_db()
        db: Session = next(db_gen)

        try:
            running_tasks = (
                db.query(DownloadTask)
                .filter(DownloadTask.status.in_(["running", "paused"]))
                .all()
            )

            reset_count = 0
            for task in running_tasks:
                original_status = task.status
                task.status = "failed"
                task.error_message = (
                    f"应用重启时发现任务处于{original_status}状态，已自动重置"
                )
                reset_count += 1
                logger.info(
                    f"重置任务 {task.id}({task.name}) 状态: {original_status} -> failed"
                )

            if reset_count > 0:
                db.commit()
                logger.info(f"✅ 成功重置 {reset_count} 个异常任务状态")
            else:
                logger.info("✅ 没有发现需要重置的异常任务状态")
        finally:
            db.close()
    except Exception as e:  # noqa: BLE001
        logger.error(f"重置任务状态失败: {e}")
        logger.warning("任务状态可能不同步，建议手动检查")

    try:
        logger.info("🔧 初始化数据库连接池优化...")
        from .utils.db_optimization import initialize_database_optimization
        from .services.connection_pool_monitor import initialize_pool_monitoring
        from .utils.enhanced_db_session import initialize_session_management
        from .services.connection_pool_tuner import initialize_pool_tuning

        initialize_database_optimization()
        initialize_pool_monitoring()
        initialize_session_management()
        initialize_pool_tuning()

        logger.info("✅ 数据库连接池优化初始化完成")
    except Exception as e:  # noqa: BLE001
        logger.error(f"数据库连接池优化初始化失败: {e}")
        logger.warning("连接池监控功能可能不可用")


async def _run_service_stage() -> None:
    """初始化业务服务与默认数据"""
    try:
        init_settings()
        logger.info("Settings initialized")

        try:
            from .services.task_execution_service import task_execution_service

            await task_execution_service.initialize()
            logger.info("Task execution service initialized successfully")
        except Exception as e:  # noqa: BLE001
            logger.error(f"Failed to initialize task execution service: {e}")
            logger.warning(
                "Task execution service disabled, system will continue startup without it"
            )

        try:
            from .api.real_data_api import initialize_real_data_provider

            await initialize_real_data_provider()
            logger.info("Real data provider initialized successfully")
        except Exception as e:  # noqa: BLE001
            logger.error(f"Failed to initialize real data provider: {e}")
            logger.warning("Real data provider disabled, some features may not work")

        try:
            from .core.service_locator import service_locator, ServiceConfig
            from .services.task_execution_service import TaskExecutionService
            from .core.temp_file_manager import temp_file_manager

            service_locator.register(
                "temp_file_manager",
                instance=temp_file_manager,
                config=ServiceConfig(singleton=True),
            )

            task_execution_service = TaskExecutionService()
            service_locator.register(
                "task_execution_service",
                instance=task_execution_service,
                config=ServiceConfig(singleton=True),
            )

            await task_execution_service.initialize()
            logger.info("Services registered and initialized successfully")
        except Exception as e:  # noqa: BLE001
            logger.error(f"Failed to register services: {e}")
            logger.warning("Service registration failed, some features may not work")

        try:
            from .services.task_scheduler import task_scheduler

            await task_scheduler.start()
            logger.info("Task scheduler started successfully")
        except ImportError as e:
            logger.error(f"Failed to import task scheduler: {e}")
            logger.warning("Task scheduler disabled, recurring tasks will not work")
        except Exception as e:  # noqa: BLE001
            logger.error(f"Failed to start task scheduler: {e}")
            logger.warning("Task scheduler disabled, recurring tasks will not work")

        message_sync_task.start()
        logger.info("Message sync task started")

        try:
            from .services.user_service import user_service
            from .database import SessionLocal

            db = SessionLocal()
            try:
                init_result = user_service.initialize_system(db)

                if init_result["success"]:
                    admin_info = user_service.get_admin_info()
                    system_status = init_result["system_status"]

                    logger.info("=" * 50)
                    logger.info("TgGod 系统初始化完成")
                    logger.info("=" * 50)
                    logger.info(f"总用户数: {system_status['total_users']}")
                    logger.info(f"管理员数: {system_status['admin_users']}")
                    logger.info(f"默认管理员: {admin_info['username']}")
                    logger.info(f"默认密码: {admin_info['password']}")
                    logger.info("⚠️  首次登录后请立即修改密码！")
                    logger.info("=" * 50)
                else:
                    logger.error(f"系统初始化失败: {init_result['message']}")
            finally:
                db.close()
        except Exception as e:  # noqa: BLE001
            logger.error(f"系统初始化异常: {e}")
            logger.error("系统将继续启动，但可能缺少默认账户")

    except Exception as e:  # noqa: BLE001
        logger.error(f"Startup initialization failed: {e}")
        logger.warning("Some features may not work properly")


async def _shutdown_runtime() -> None:
    """关闭运行中的服务与资源"""
    logger.info("开始关闭 TgGod API", shutdown_phase="start")

    try:
        from .services.task_scheduler import task_scheduler

        await task_scheduler.stop()
        logger.info("任务调度器停止成功", component="task_scheduler")
    except Exception as e:  # noqa: BLE001
        logger.error("停止任务调度器失败", error=str(e), component="task_scheduler")

    try:
        message_sync_task.stop()
        logger.info("消息同步任务停止成功", component="message_sync")
    except Exception as e:  # noqa: BLE001
        logger.error("停止消息同步任务失败", error=str(e), component="message_sync")

    try:
        from .core.session_store import close_session_store

        await close_session_store()
        logger.info("Redis会话存储关闭成功", component="session_store")
    except Exception as e:  # noqa: BLE001
        logger.error("关闭Redis会话存储失败", error=str(e), component="session_store")

    try:
        from .services.complete_health_monitoring import stop_complete_health_monitoring

        await stop_complete_health_monitoring()
        logger.info("完整健康监控系统停止成功", component="complete_health_monitoring")
    except Exception as e:  # noqa: BLE001
        logger.error(
            "停止完整健康监控系统失败",
            error=str(e),
            component="complete_health_monitoring",
        )

    try:
        from .websocket.production_status_manager import production_status_manager

        await production_status_manager.stop_monitoring()
        logger.info("生产状态管理器停止成功", component="production_status_manager")
    except Exception as e:  # noqa: BLE001
        logger.error(
            "停止生产状态管理器失败",
            error=str(e),
            component="production_status_manager",
        )

    try:
        from .services.service_monitor import service_monitor

        await service_monitor.stop_monitoring()
        logger.info("服务监控器停止成功", component="service_monitor")
    except Exception as e:  # noqa: BLE001
        logger.error("停止服务监控器失败", error=str(e), component="service_monitor")

    try:
        from .api.real_data_api import cleanup_real_data_provider

        await cleanup_real_data_provider()
        logger.info("真实数据提供者清理成功", component="real_data_provider")
    except Exception as e:  # noqa: BLE001
        logger.error(
            "清理真实数据提供者失败", error=str(e), component="real_data_provider"
        )

    try:
        from .core.temp_file_manager import temp_file_manager

        temp_file_manager.shutdown()
        logger.info("临时文件管理器关闭成功", component="temp_file_manager")
    except Exception as e:  # noqa: BLE001
        logger.error(
            "关闭临时文件管理器失败", error=str(e), component="temp_file_manager"
        )

    try:
        from .core.batch_logging import BatchLogHandler

        logger.info("关闭批处理日志系统", component="batch_logging")
        BatchLogHandler.shutdown_all()
        logger.info("批处理日志系统关闭完成", component="batch_logging")
    except Exception as e:  # noqa: BLE001
        print(f"关闭批处理日志系统失败: {e}")

    logger.info("TgGod API 关闭完成", shutdown_phase="complete")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI应用程序生命周期管理器"""
    logger.info("Starting TgGod API...")

    pipeline = StartupPipeline(
        stages=[
            StartupStage(
                name="dependencies",
                runner=_run_dependency_stage,
                description="安装系统依赖并启动监控",
            ),
            StartupStage(
                name="database",
                runner=_run_database_stage,
                description="执行数据库检查与修复",
            ),
            StartupStage(
                name="services",
                runner=_run_service_stage,
                description="初始化业务服务与默认数据",
            ),
        ],
        logger=logger,
    )

    try:
        await pipeline.run()
    except Exception:  # noqa: BLE001
        logger.exception("启动管线执行失败")
        raise

    try:
        yield
    finally:
        await _shutdown_runtime()


# 创建FastAPI应用
app = FastAPI(
    title="TgGod API",
    description="Telegram群组规则下载系统API",
    version="1.0.0",
    lifespan=lifespan,
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 全局异常处理器
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器

    捕获并处理应用程序中未被处理的异常，记录错误日志并返回
    标准化的错误响应。

    Args:
        request (Request): HTTP请求对象
        exc (Exception): 捕获的异常对象

    Returns:
        JSONResponse: 包含错误信息的JSON响应

    Note:
        - 返回500状态码表示内部服务器错误
        - 错误详情会被记录到日志中用于调试
        - 生产环境中应避免暴露敏感的错误信息
    """
    logger.error(
        f"全局异常捕获: {request.method} {request.url} - {type(exc).__name__}: {str(exc)}"
    )
    return JSONResponse(
        status_code=500, content={"detail": "Internal server error", "error": str(exc)}
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """HTTP异常处理器

    处理标准的HTTP异常(如404、403等)，记录警告日志并返回
    格式化的错误响应。

    Args:
        request (Request): HTTP请求对象
        exc (StarletteHTTPException): HTTP异常对象

    Returns:
        JSONResponse: 包含异常状态码和详情的JSON响应

    Examples:
        - 404 Not Found: 资源不存在
        - 403 Forbidden: 权限不足
        - 400 Bad Request: 请求参数错误
    """
    logger.warning(
        f"HTTP异常: {request.method} {request.url} - 状态码: {exc.status_code} - 详情: {exc.detail}"
    )
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


# 添加请求日志中间件
@app.middleware("http")
async def log_requests(request, call_next):
    """HTTP请求日志记录中间件

    记录所有HTTP请求的详细信息，包括请求方法、URL、处理时间
    和响应状态码，用于监控和调试。

    Args:
        request: HTTP请求对象
        call_next: 下一个中间件或路由处理器

    Returns:
        Response: HTTP响应对象

    Logs:
        - 请求开始: 方法、URL、请求头(debug级别)
        - 请求完成: 状态码、处理耗时
        - 请求失败: 错误信息和处理耗时

    Note:
        处理时间精确到毫秒，有助于性能分析
    """
    start_time = time.time()

    try:
        # 记录请求信息
        logger.info(f"🔵 请求开始: {request.method} {request.url}")
        logger.debug(f"🔵 请求头: {dict(request.headers)}")

        # 处理请求
        response = await call_next(request)

        # 记录响应信息
        process_time = time.time() - start_time
        logger.info(
            f"🟢 请求完成: {request.method} {request.url} - 状态码: {response.status_code} - 耗时: {process_time:.4f}s"
        )

        return response

    except Exception as e:
        # 记录错误信息
        process_time = time.time() - start_time
        logger.error(
            f"❌ 请求失败: {request.method} {request.url} - 错误: {str(e)} - 耗时: {process_time:.4f}s"
        )

        # 重新抛出异常，让FastAPI处理
        raise


# 静态文件服务
# 确保媒体目录存在
os.makedirs(settings.media_root, exist_ok=True)
os.makedirs(os.path.join(settings.media_root, "photos"), exist_ok=True)
os.makedirs(os.path.join(settings.media_root, "videos"), exist_ok=True)
os.makedirs(os.path.join(settings.media_root, "audios"), exist_ok=True)
os.makedirs(os.path.join(settings.media_root, "documents"), exist_ok=True)

if os.path.exists(settings.media_root):
    # 配置媒体文件服务，支持视频流
    from starlette.responses import FileResponse
    from starlette.middleware.base import BaseHTTPMiddleware

    class MediaHeaders(BaseHTTPMiddleware):
        """媒体文件HTTP头处理中间件

        为不同类型的媒体文件添加适当的MIME类型和HTTP头部信息，
        支持视频流播放、图片显示和音频播放。

        支持的媒体类型:
            - 视频: mp4, avi, mov, wmv, flv, webm, mkv
            - 图片: jpg, jpeg, png, gif, bmp, webp
            - 音频: mp3, wav, ogg, flac, aac

        Features:
            - 设置正确的Content-Type头
            - 添加Range支持用于视频流
            - 配置跨域访问头
            - 设置缓存控制策略
        """

        async def dispatch(self, request, call_next):
            try:
                response = await call_next(request)

                # 为媒体文件添加适当的MIME类型和头部
                if request.url.path.startswith("/media/"):
                    file_ext = request.url.path.split(".")[-1].lower()

                    # 视频文件类型
                    if file_ext in ["mp4", "avi", "mov", "wmv", "flv", "webm", "mkv"]:
                        response.headers["Accept-Ranges"] = "bytes"
                        response.headers["Content-Type"] = f"video/{file_ext}"
                        if file_ext == "mp4":
                            response.headers["Content-Type"] = "video/mp4"
                        elif file_ext == "webm":
                            response.headers["Content-Type"] = "video/webm"
                        elif file_ext == "avi":
                            response.headers["Content-Type"] = "video/x-msvideo"

                    # 图片文件类型
                    elif file_ext in ["jpg", "jpeg", "png", "gif", "bmp", "webp"]:
                        response.headers["Content-Type"] = f"image/{file_ext}"
                        if file_ext in ["jpg", "jpeg"]:
                            response.headers["Content-Type"] = "image/jpeg"

                    # 音频文件类型
                    elif file_ext in ["mp3", "wav", "ogg", "flac", "aac"]:
                        response.headers["Content-Type"] = f"audio/{file_ext}"
                        if file_ext == "mp3":
                            response.headers["Content-Type"] = "audio/mpeg"

                    # 设置缓存头部
                    response.headers["Cache-Control"] = "public, max-age=3600"
                    response.headers["Access-Control-Allow-Origin"] = "*"
                    response.headers["Access-Control-Allow-Methods"] = (
                        "GET, HEAD, OPTIONS"
                    )
                    response.headers["Access-Control-Allow-Headers"] = "Range"

                return response

            except Exception as e:
                logger.error(f"MediaHeaders中间件错误: {str(e)}")
                # 重新抛出异常，让上层处理
                raise

    # 添加媒体文件处理中间件
    app.add_middleware(MediaHeaders)

    # 挂载静态文件服务
    app.mount("/media", StaticFiles(directory=settings.media_root), name="media")

# 导入WebSocket管理器（使用全局单例）
from .websocket.manager import websocket_manager

# 注册API路由
app.include_router(telegram.router, prefix="/api/telegram", tags=["telegram"])
app.include_router(rule.router, prefix="/api/rule", tags=["rule"])
# 同时添加 /api/rules 路径的支持
app.include_router(rule.router, prefix="/api", tags=["rule"])
app.include_router(log.router, prefix="/api", tags=["log"])
app.include_router(task.router, prefix="/api", tags=["task"])
app.include_router(config.router, prefix="/api/config", tags=["config"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])

# 用户设置API
app.include_router(user_settings.router, prefix="/api/user", tags=["user"])

# 仪表盘API
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])

# 媒体文件API
from .api import media

app.include_router(media.router, prefix="/api/media", tags=["media"])

# 数据库检查API
app.include_router(database_check.router, prefix="/api/database", tags=["database"])

# 下载历史API
app.include_router(download_history.router, prefix="/api", tags=["download_history"])

# 服务健康检查API
from .api import service_health

app.include_router(service_health.router, prefix="/api", tags=["service_health"])

# 实时状态控制API
from .api import realtime_controls

app.include_router(realtime_controls.router, prefix="/api", tags=["realtime_controls"])

# 连接池监控API
from .api import connection_pool

app.include_router(connection_pool.router, prefix="/api", tags=["connection_pool"])

# 批处理日志监控API
from .api import batch_logging_metrics

app.include_router(batch_logging_metrics.router, prefix="/api", tags=["batch_logging"])

# 完整真实数据提供者API
app.include_router(real_data_api.router, tags=["real_data"])

# 数据初始化和迁移API
app.include_router(data_initialization.router, tags=["data_initialization"])

# 完整健康监控和自动恢复API
app.include_router(
    complete_health_monitoring.router,
    prefix="/api",
    tags=["complete_health_monitoring"],
)

# 服务管理和迁移API
app.include_router(services.router, prefix="/api/services", tags=["services"])


# 根路径
@app.get("/")
async def root():
    """API根端点

    返回简单的状态信息，用于验证API服务是否正常运行。

    Returns:
        Dict[str, str]: 包含运行状态消息的字典

    Example:
        GET /
        Response: {"message": "TgGod API is running"}
    """
    return {"message": "TgGod API is running"}


# 健康检查
@app.get("/health")
async def health_check():
    """API健康检查端点

    提供基础的健康状态检查，用于负载均衡器、监控系统
    或容器编排平台确认服务可用性。

    Returns:
        Dict[str, str]: 健康状态信息

    Example:
        GET /health
        Response: {"status": "healthy"}

    Note:
        更详细的健康检查请使用 /api/health/* 端点
    """
    return {"status": "healthy"}


# WebSocket端点
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket连接端点

    建立WebSocket连接以实现实时双向通信，支持群组消息订阅、
    任务状态更新和系统通知推送。

    Args:
        websocket (WebSocket): WebSocket连接对象
        client_id (str): 客户端唯一标识符

    Message Types:
        - subscribe_group: 订阅群组消息更新
        - unsubscribe_group: 取消订阅群组消息
        - ping: 心跳检测消息

    Response Types:
        - subscription_confirmed: 订阅确认
        - unsubscription_confirmed: 取消订阅确认
        - pong: 心跳响应
        - group_message: 群组新消息通知
        - task_update: 任务状态更新

    Example:
        # 订阅群组消息
        {
            "type": "subscribe_group",
            "group_id": "123456"
        }

    Raises:
        WebSocketDisconnect: 客户端断开连接

    Note:
        连接断开时会自动清理客户端订阅状态
    """
    await websocket_manager.connect(websocket, client_id)

    # 存储客户端订阅的群组
    client_subscriptions = set()

    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                message_type = message.get("type")

                if message_type == "subscribe_group":
                    # 订阅群组消息
                    group_id = message.get("group_id")
                    if group_id:
                        client_subscriptions.add(group_id)
                        logger.info(
                            f"Client {client_id} subscribed to group {group_id}"
                        )

                        # 将群组添加到同步任务
                        message_sync_task.add_group(int(group_id), interval=30)

                        # 发送订阅确认
                        await websocket_manager.send_personal_message(
                            {
                                "type": "subscription_confirmed",
                                "data": {"group_id": group_id},
                            },
                            client_id,
                        )

                elif message_type == "unsubscribe_group":
                    # 取消订阅群组消息
                    group_id = message.get("group_id")
                    if group_id and group_id in client_subscriptions:
                        client_subscriptions.remove(group_id)
                        logger.info(
                            f"Client {client_id} unsubscribed from group {group_id}"
                        )

                        # 发送取消订阅确认
                        await websocket_manager.send_personal_message(
                            {
                                "type": "unsubscription_confirmed",
                                "data": {"group_id": group_id},
                            },
                            client_id,
                        )

                elif message_type == "ping":
                    # 心跳检测
                    await websocket_manager.send_personal_message(
                        {"type": "pong"}, client_id
                    )

            except json.JSONDecodeError:
                logger.error(f"Invalid JSON received from client {client_id}")
            except Exception as e:
                logger.error(f"Error processing message from client {client_id}: {e}")

    except WebSocketDisconnect:
        websocket_manager.disconnect(client_id)
        logger.info(
            f"Client {client_id} disconnected from groups: {client_subscriptions}"
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
