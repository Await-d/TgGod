from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
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

# 创建FastAPI应用
app = FastAPI(
    title="TgGod API",
    description="Telegram群组规则下载系统API",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加请求日志中间件
@app.middleware("http")
async def log_requests(request, call_next):
    start_time = time.time()
    
    # 记录请求信息
    logger.info(f"🔵 请求开始: {request.method} {request.url}")
    logger.info(f"🔵 请求头: {dict(request.headers)}")
    
    # 处理请求
    response = await call_next(request)
    
    # 记录响应信息
    process_time = time.time() - start_time
    logger.info(f"🟢 请求完成: {request.method} {request.url} - 状态码: {response.status_code} - 耗时: {process_time:.4f}s")
    
    return response

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
app.include_router(task.router, prefix="/api/task", tags=["task"])
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

# 启动事件
@app.on_event("startup")
async def startup_event():
    logger.info("Starting TgGod API...")
    
    # 使用新的数据库检查器进行启动时检查
    try:
        logger.info("🔧 开始数据库结构检查和自动修复...")
        
        from .utils.database_checker import database_checker
        
        # 运行启动检查
        check_success = database_checker.run_startup_check()
        
        if check_success:
            logger.info("✅ 数据库结构检查和修复完成")
        else:
            logger.warning("⚠️ 数据库结构存在问题，但系统将继续启动")
            logger.warning("建议手动运行 'alembic upgrade head' 来完成数据库迁移")
        
    except Exception as e:
        logger.error(f"数据库结构检查失败: {e}")
        logger.info("尝试使用传统方式创建数据库表...")
        
        # 传统数据库创建方式作为备选
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("✅ 使用传统方式创建数据库表成功")
        except Exception as create_error:
            logger.error(f"❌ 创建数据库表失败: {create_error}")
    
    # 检查和修复数据库字段（保留原有逻辑作为备用）
    try:
        logger.info("🔧 运行传统数据库字段检查...")
        
        # 导入数据库修复工具
        from pathlib import Path
        import sys
        import sqlite3
        
        project_root = Path(__file__).parent.parent
        sys.path.insert(0, str(project_root))
        
        # 使用我们的数据库修复工具
        from fix_database_schema import fix_telegram_messages_table, get_database_path
        
        # 获取数据库路径并修复
        db_path = get_database_path()
        logger.info(f"数据库路径: {db_path}")
        
        success = fix_telegram_messages_table(db_path)
        
        if success:
            logger.info("✅ 传统数据库字段检查和修复完成")
        else:
            logger.error("❌ 传统数据库字段修复失败")
        
        # 运行用户设置表迁移
        logger.info("🔧 正在检查用户设置表...")
        try:
            # 尝试导入迁移模块
            migration_file = project_root / "migrations" / "add_user_settings_table.py"
            
            if migration_file.exists():
                logger.info(f"找到用户设置迁移脚本: {migration_file}")
                from importlib.util import spec_from_file_location, module_from_spec
                
                # 动态导入迁移模块
                spec = spec_from_file_location("add_user_settings_table", migration_file)
                migration_module = module_from_spec(spec)
                spec.loader.exec_module(migration_module)
                
                # 运行迁移
                user_settings_success, user_settings_message = migration_module.run_migration()
                if user_settings_success:
                    logger.info(f"✅ 用户设置表检查完成: {user_settings_message}")
                else:
                    logger.warning(f"⚠️ 用户设置表检查警告: {user_settings_message}")
            else:
                logger.warning(f"未找到用户设置迁移脚本，将跳过自动迁移")
        except Exception as e:
            logger.error(f"运行用户设置迁移时出错: {e}")
            logger.warning("将继续启动，但用户设置表可能不存在")
            
    except Exception as e:
        logger.error(f"数据库检查过程中发生错误: {e}")
        logger.info("将使用传统方式创建表...")
        
        # 创建数据库表（传统方式）
        Base.metadata.create_all(bind=engine)
        
    # 执行其他数据库检查和自动修复
    try:
        # 检查utils/db_utils.py是否存在
        db_utils_file = Path(__file__).parent / "utils" / "db_utils.py"
        
        if db_utils_file.exists():
            logger.info(f"找到数据库工具脚本: {db_utils_file}")
            
            # 导入工具模块
            from .utils.db_utils import check_and_fix_database_on_startup
            from .database import SessionLocal
            
            db = SessionLocal()
            try:
                # 检查和修复数据库
                db_check_results = check_and_fix_database_on_startup(db)
                logger.info(f"🔧 数据库自动检查结果: {db_check_results['status']}")
                
                # 输出详细信息
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
            
            # 确保基本表结构存在
            logger.info("创建基本表结构...")
            Base.metadata.create_all(bind=engine)
    except Exception as e:
        logger.error(f"数据库自动检查和修复过程中出现错误: {e}")
        logger.warning("系统将继续启动，但数据库结构可能不完整")
    
    # 启动消息同步任务
    message_sync_task.start()
    logger.info("Message sync task started")
    
    # 初始化任务执行服务
    try:
        from .services.task_execution_service import task_execution_service
        await task_execution_service.initialize()
        logger.info("Task execution service initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize task execution service: {e}")
    
    logger.info("Database tables created successfully")
    
    # 初始化设置
    init_settings()
    logger.info("Settings initialized")
    
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
                if "error" in init_result:
                    logger.error(f"错误详情: {init_result['error']}")
                    
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"系统初始化异常: {e}")
        logger.error("系统将继续启动，但可能缺少默认账户")

# 关闭事件
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down TgGod API...")
    
    # 停止消息同步任务
    message_sync_task.stop()
    logger.info("Message sync task stopped")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)