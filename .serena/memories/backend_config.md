# 后端技术配置

## 数据库配置
- **数据库**: SQLite (`sqlite:///./tggod.db`)
- **ORM**: SQLAlchemy 2.0.23
- **异步支持**: aiosqlite 0.19.0
- **迁移工具**: Alembic 1.12.1

## 核心依赖
- **Web框架**: FastAPI 0.104.1 + Uvicorn 0.24.0
- **Telegram API**: Telethon 1.32.1
- **WebSocket**: websockets 11.0.3
- **认证**: python-jose + passlib (JWT + bcrypt)
- **文件处理**: Pillow, aiofiles
- **数据处理**: pandas, openpyxl

## 关键配置
- **媒体存储**: `./media` 目录
- **日志存储**: `./logs/app.log`
- **CORS**: 允许localhost:3000,3001
- **文件上传**: 最大100MB

## 环境变量
需要配置：
- `TELEGRAM_API_ID` 和 `TELEGRAM_API_HASH`
- `SECRET_KEY` (JWT认证)
- SMTP设置(邮件通知,可选)

## 已完成文件
- `backend/app/config.py` - 配置管理
- `backend/app/database.py` - 数据库连接
- `backend/app/main.py` - FastAPI应用入口
- `backend/requirements.txt` - 依赖清单