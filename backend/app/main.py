from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .config import settings, init_settings
from .database import engine, Base
from .api import telegram, rule, log, task, config, auth
from .websocket.manager import WebSocketManager
import logging
import os

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
    try:
        while True:
            # 保持连接活跃
            await websocket.receive_text()
    except WebSocketDisconnect:
        websocket_manager.disconnect(client_id)
        logger.info(f"Client {client_id} disconnected")

# 启动事件
@app.on_event("startup")
async def startup_event():
    logger.info("Starting TgGod API...")
    # 创建数据库表
    Base.metadata.create_all(bind=engine)
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)