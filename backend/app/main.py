from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .config import settings, init_settings
from .database import engine, Base
from .api import telegram, rule, log, task, config, auth
from .websocket.manager import WebSocketManager
from .tasks.message_sync import message_sync_task
import logging
import os
import json

# 配置日志
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(settings.log_file),
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

# 静态文件服务
if os.path.exists(settings.media_root):
    app.mount("/media", StaticFiles(directory=settings.media_root), name="media")

# WebSocket管理器
websocket_manager = WebSocketManager()

# 注册API路由
app.include_router(telegram.router, prefix="/api/telegram", tags=["telegram"])
app.include_router(rule.router, prefix="/api/rule", tags=["rule"])
app.include_router(log.router, prefix="/api/log", tags=["log"])
app.include_router(task.router, prefix="/api/task", tags=["task"])
app.include_router(config.router, prefix="/api/config", tags=["config"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])

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
    
    # 检查和修复数据库
    try:
        from pathlib import Path
        import sys
        
        # 导入数据库检查器
        project_root = Path(__file__).parent.parent
        sys.path.insert(0, str(project_root))
        
        from check_database import DatabaseChecker
        
        logger.info("正在检查数据库结构...")
        checker = DatabaseChecker()
        success = checker.check_and_repair()
        
        if success:
            logger.info("数据库检查和修复完成")
        else:
            logger.error("数据库检查和修复失败，但应用将继续启动")
            
    except Exception as e:
        logger.error(f"数据库检查过程中发生错误: {e}")
        logger.info("将使用传统方式创建表...")
        
        # 创建数据库表（传统方式）
        Base.metadata.create_all(bind=engine)
    
    # 启动消息同步任务
    message_sync_task.start()
    logger.info("Message sync task started")
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