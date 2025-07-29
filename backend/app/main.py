from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from .database import engine, Base
from .config import settings, init_settings
from .api import telegram, rule, log, task, config, auth, user_settings, dashboard, database_check, download_history
from .tasks.message_sync import message_sync_task
import logging
import os
import json
import time

# 配置日志
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
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("Starting TgGod API...")
    
    # 🚀 启动时自动检查和安装必要服务
    try:
        logger.info("🔍 开始检查和安装必要服务...")
        
        from .services.service_installer import run_service_installation
        
        # 运行服务安装检查
        installation_result = await run_service_installation()
        
        if installation_result["success"]:
            logger.info("✅ 服务依赖检查完成")
            
            # 记录安装统计
            stats = {
                "新安装": len(installation_result["installed_services"]),
                "已存在": len(installation_result["already_installed"]),
                "跳过": len(installation_result["skipped_services"]),
                "失败": len(installation_result["failed_services"])
            }
            
            logger.info(f"📊 服务统计: {stats}")
            
            # 如果有安装失败的服务，记录警告
            if installation_result["failed_services"]:
                logger.warning("⚠️ 以下服务安装失败，可能影响某些功能:")
                for failed in installation_result["failed_services"]:
                    logger.warning(f"  - {failed['name']}: {failed['error']}")
                logger.warning("建议手动安装这些服务以确保完整功能")
            
            # 如果有新安装的服务，记录详情
            if installation_result["installed_services"]:
                logger.info("🎉 新安装的服务:")
                for installed in installation_result["installed_services"]:
                    logger.info(f"  - {installed['name']}: {installed['details']}")
        else:
            logger.error(f"❌ 服务依赖检查失败: {installation_result.get('error', '未知错误')}")
            logger.warning("系统将继续启动，但某些功能可能不可用")
            
    except Exception as e:
        logger.error(f"服务安装检查过程异常: {e}")
        logger.warning("系统将继续启动，但建议检查服务依赖")
    
    # 🔍 启动服务监控器
    try:
        from .services.service_monitor import service_monitor
        await service_monitor.start_monitoring()
        logger.info("✅ 服务监控器启动成功")
    except Exception as e:
        logger.error(f"服务监控器启动失败: {e}")
        logger.warning("服务监控功能不可用，但系统将继续运行")

    # 数据库检查和修复
    try:
        logger.info("🔧 开始运行数据库字段修复脚本...")
        from pathlib import Path
        import subprocess
        import sys
        
        project_root = Path(__file__).parent.parent
        
        # 修复脚本列表
        repair_scripts = [
            ("fix_task_fields.py", "任务表字段修复"),
            ("fix_filter_rules_fields.py", "过滤规则表字段修复"), 
            ("fix_incremental_fields.py", "增量查询字段修复"),
            ("remove_rule_group_id_field.py", "移除规则表group_id字段"),
            ("add_advanced_rule_fields.py", "添加高级规则过滤字段"),
            ("create_task_rule_association_table.py", "创建任务-规则多对多关联表")
        ]
        
        for script_name, description in repair_scripts:
            script_path = project_root / script_name
            if script_path.exists():
                logger.info(f"运行{description}脚本...")
                result = subprocess.run([sys.executable, str(script_path)], 
                                      capture_output=True, text=True, cwd=str(project_root))
                if result.returncode == 0:
                    logger.info(f"✅ {description}完成")
                else:
                    logger.error(f"❌ {description}失败: {result.stderr}")
            else:
                logger.warning(f"未找到{script_name}，跳过{description}")
        
        logger.info("🎯 所有数据库字段修复脚本执行完成")
    except Exception as e:
        logger.error(f"运行数据库字段修复脚本失败: {e}")
        logger.warning("将继续启动，但可能出现字段访问错误")

    # 数据库健康检查
    try:
        logger.info("🏥 执行数据库健康检查...")
        from pathlib import Path
        import subprocess
        import sys
        
        health_check_script = Path(__file__).parent.parent / "database_health_check.py"
        if health_check_script.exists():
            result = subprocess.run([sys.executable, str(health_check_script)], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                logger.info("✅ 数据库健康检查完成")
            else:
                logger.warning(f"数据库健康检查异常: {result.stderr}")
        else:
            logger.info("未找到健康检查脚本，跳过检查")
    except Exception as e:
        logger.error(f"数据库健康检查失败: {e}")

    # 重置异常任务状态
    try:
        logger.info("🔧 开始重置异常任务状态...")
        from .database import get_db
        from .models.rule import DownloadTask
        from sqlalchemy.orm import Session
        
        db_gen = get_db()
        db: Session = next(db_gen)
        
        try:
            running_tasks = db.query(DownloadTask).filter(
                DownloadTask.status.in_(["running", "paused"])
            ).all()
            
            reset_count = 0
            for task in running_tasks:
                original_status = task.status
                task.status = "failed"
                task.error_message = f"应用重启时发现任务处于{original_status}状态，已自动重置"
                reset_count += 1
                logger.info(f"重置任务 {task.id}({task.name}) 状态: {original_status} -> failed")
            
            if reset_count > 0:
                db.commit()
                logger.info(f"✅ 成功重置 {reset_count} 个异常任务状态")
            else:
                logger.info("✅ 没有发现需要重置的异常任务状态")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"重置任务状态失败: {e}")
        logger.warning("任务状态可能不同步，建议手动检查")

    # 数据库和其他启动逻辑
    try:
        # 初始化设置
        init_settings()
        logger.info("Settings initialized")
        
        # 初始化任务执行服务
        try:
            from .services.task_execution_service import task_execution_service
            await task_execution_service.initialize()
            logger.info("Task execution service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize task execution service: {e}")
            logger.warning("Task execution service disabled, system will continue startup without it")

        # 启动任务调度器
        try:
            from .services.task_scheduler import task_scheduler
            await task_scheduler.start()
            logger.info("Task scheduler started successfully")
        except ImportError as e:
            logger.error(f"Failed to import task scheduler: {e}")
            logger.warning("Task scheduler disabled, recurring tasks will not work")
        except Exception as e:
            logger.error(f"Failed to start task scheduler: {e}")
            logger.warning("Task scheduler disabled, recurring tasks will not work")
        
        # 启动消息同步任务
        message_sync_task.start()
        logger.info("Message sync task started")

        # 创建默认账户
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
        except Exception as e:
            logger.error(f"系统初始化异常: {e}")
            logger.error("系统将继续启动，但可能缺少默认账户")

    except Exception as e:
        logger.error(f"Startup initialization failed: {e}")
        logger.warning("Some features may not work properly")
    
    # 应用运行中
    yield
    
    # 关闭时执行
    logger.info("Shutting down TgGod API...")
    
    # 停止任务调度器
    try:
        from .services.task_scheduler import task_scheduler
        await task_scheduler.stop()
        logger.info("Task scheduler stopped successfully")
    except Exception as e:
        logger.error(f"Failed to stop task scheduler: {e}")
    
    # 停止消息同步任务
    try:
        message_sync_task.stop()
        logger.info("Message sync task stopped")
    except Exception as e:
        logger.error(f"Failed to stop message sync task: {e}")
    
    # 停止服务监控器
    try:
        from .services.service_monitor import service_monitor
        await service_monitor.stop_monitoring()
        logger.info("Service monitor stopped")
    except Exception as e:
        logger.error(f"Failed to stop service monitor: {e}")
    
    logger.info("TgGod API shutdown complete")

# 创建FastAPI应用
app = FastAPI(
    title="TgGod API",
    description="Telegram群组规则下载系统API",
    version="1.0.0",
    lifespan=lifespan
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
    logger.error(f"全局异常捕获: {request.method} {request.url} - {type(exc).__name__}: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)}
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger.warning(f"HTTP异常: {request.method} {request.url} - 状态码: {exc.status_code} - 详情: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

# 添加请求日志中间件
@app.middleware("http")
async def log_requests(request, call_next):
    start_time = time.time()
    
    try:
        # 记录请求信息
        logger.info(f"🔵 请求开始: {request.method} {request.url}")
        logger.debug(f"🔵 请求头: {dict(request.headers)}")
        
        # 处理请求
        response = await call_next(request)
        
        # 记录响应信息
        process_time = time.time() - start_time
        logger.info(f"🟢 请求完成: {request.method} {request.url} - 状态码: {response.status_code} - 耗时: {process_time:.4f}s")
        
        return response
        
    except Exception as e:
        # 记录错误信息
        process_time = time.time() - start_time
        logger.error(f"❌ 请求失败: {request.method} {request.url} - 错误: {str(e)} - 耗时: {process_time:.4f}s")
        
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
        async def dispatch(self, request, call_next):
            try:
                response = await call_next(request)
                
                # 为媒体文件添加适当的MIME类型和头部
                if request.url.path.startswith('/media/'):
                    file_ext = request.url.path.split('.')[-1].lower()
                    
                    # 视频文件类型
                    if file_ext in ['mp4', 'avi', 'mov', 'wmv', 'flv', 'webm', 'mkv']:
                        response.headers["Accept-Ranges"] = "bytes"
                        response.headers["Content-Type"] = f"video/{file_ext}"
                        if file_ext == 'mp4':
                            response.headers["Content-Type"] = "video/mp4"
                        elif file_ext == 'webm':
                            response.headers["Content-Type"] = "video/webm"
                        elif file_ext == 'avi':
                            response.headers["Content-Type"] = "video/x-msvideo"
                    
                    # 图片文件类型  
                    elif file_ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']:
                        response.headers["Content-Type"] = f"image/{file_ext}"
                        if file_ext in ['jpg', 'jpeg']:
                            response.headers["Content-Type"] = "image/jpeg"
                    
                    # 音频文件类型
                    elif file_ext in ['mp3', 'wav', 'ogg', 'flac', 'aac']:
                        response.headers["Content-Type"] = f"audio/{file_ext}"
                        if file_ext == 'mp3':
                            response.headers["Content-Type"] = "audio/mpeg"
                    
                    # 设置缓存头部
                    response.headers["Cache-Control"] = "public, max-age=3600"
                    response.headers["Access-Control-Allow-Origin"] = "*"
                    response.headers["Access-Control-Allow-Methods"] = "GET, HEAD, OPTIONS"
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
app.include_router(log.router, prefix="/api/log", tags=["log"])
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

# 根路径
@app.get("/")
async def root():
    return {"message": "TgGod API is running"}

# 健康检查
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# WebSocket端点
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
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
                        logger.info(f"Client {client_id} subscribed to group {group_id}")
                        
                        # 将群组添加到同步任务
                        message_sync_task.add_group(int(group_id), interval=30)
                        
                        # 发送订阅确认
                        await websocket_manager.send_personal_message({
                            "type": "subscription_confirmed",
                            "data": {"group_id": group_id}
                        }, client_id)
                
                elif message_type == "unsubscribe_group":
                    # 取消订阅群组消息
                    group_id = message.get("group_id")
                    if group_id and group_id in client_subscriptions:
                        client_subscriptions.remove(group_id)
                        logger.info(f"Client {client_id} unsubscribed from group {group_id}")
                        
                        # 发送取消订阅确认
                        await websocket_manager.send_personal_message({
                            "type": "unsubscription_confirmed",
                            "data": {"group_id": group_id}
                        }, client_id)
                
                elif message_type == "ping":
                    # 心跳检测
                    await websocket_manager.send_personal_message({
                        "type": "pong"
                    }, client_id)
                
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON received from client {client_id}")
            except Exception as e:
                logger.error(f"Error processing message from client {client_id}: {e}")
                
    except WebSocketDisconnect:
        websocket_manager.disconnect(client_id)
        logger.info(f"Client {client_id} disconnected from groups: {client_subscriptions}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)