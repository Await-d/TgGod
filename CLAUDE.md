# CLAUDE.md

此文件为 Claude Code (claude.ai/code) 在此代码仓库中工作时提供指导。

在项目根目录下创建一个todo 文件（不存在则创建），你需要先将我们商量好的代办任务添加到todo文件中，每完成一个任务对应的任务标记已完成，这样方便我们实时跟踪开发进度。

合理使用 Task 工具创建多个子代理来提高开发效率，每个子代理负责一个独立的任务，互不干扰，支持并行执行。

## TgGod - Telegram群组规则下载系统

这是一个单服务架构应用，结合了React前端、FastAPI后端和SQLite数据库，用于基于可定制规则从Telegram群组下载媒体文件。

## 开发命令

### 快速启动
```bash
# 一键部署
./scripts/deployment/quick-start.sh

# 手动部署测试
./scripts/deployment/deploy-test.sh
```

### 后端开发
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 运行开发服务器
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 运行数据库迁移（如需手动修复）
# 注意：修复脚本已归档到 backend/scripts/archive/
# python backend/scripts/archive/fix_database_schema.py
# python backend/scripts/archive/fix_task_fields.py
```

### 前端开发
```bash
cd frontend
pnpm install
pnpm dev        # 开发服务器端口3000
pnpm build      # 生产构建
pnpm preview    # 预览生产构建
```

### Docker部署
```bash
# 单服务架构
docker-compose up -d --build
docker-compose logs -f              # 查看日志
docker-compose down                 # 停止服务
docker-compose restart              # 重启服务

# 健康检查
curl http://localhost/health
```

### 测试
```bash
# 测试服务依赖
python simple_test.py

# 测试服务安装器
python test_service_installer.py
```

## 架构概述

### 单服务架构
应用作为单个Docker容器运行，结合：
- **前端**：React应用由Nginx在80端口提供服务
- **后端**：FastAPI服务器在内部8000端口运行
- **数据库**：SQLite数据库外部卷挂载
- **静态文件**：媒体、日志和Telegram会话外部挂载

### 核心组件

**后端 (`backend/app/`)**
- `main.py`：带有生命周期管理和服务自动安装的FastAPI应用
- `api/`：按域组织的REST API端点（telegram、rule、media等）
- `services/`：业务逻辑服务包括：
  - `service_installer.py`：自动安装系统依赖（ffmpeg、字体、监控工具）
  - `service_monitor.py`：实时系统健康监控
  - `telegram_service.py`：使用Telethon的Telegram客户端管理
  - `media_downloader.py`：处理媒体文件下载和会话管理
  - `file_organizer_service.py`：组织下载文件并生成NFO元数据
  - `task_scheduler.py`：后台任务管理
- `models/`：SQLAlchemy数据库模型
- `websocket/`：实时WebSocket通信

**前端 (`frontend/src/`)**
- React + TypeScript + Ant Design
- Zustand状态管理
- 实时WebSocket集成
- 页面：仪表板、群组、规则、任务、日志、设置

### 数据库架构
SQLite数据库外部挂载在 `./data/tggod.db`。主要表：
- `telegram_groups`：管理的Telegram群组
- `telegram_messages`：下载的消息和元数据
- `filter_rules`：基于规则的过滤配置
- `download_tasks`：后台下载任务
- `user_settings`：用户偏好和配置

### 服务依赖
应用自动安装和监控系统依赖：
- **FFmpeg**：视频处理和缩略图生成
- **系统字体**：生成图片中的文本渲染
- **Python监控包**：psutil、py-cpuinfo用于系统指标
- **媒体工具**：ImageMagick、ExifTool用于高级处理

## 配置

### 环境变量 (`.env`)
```bash
# 必需的Telegram API凭据
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_BOT_TOKEN=your_bot_token

# 安全密钥（生产环境中更改）
SECRET_KEY=your_secret_key
JWT_SECRET_KEY=your_jwt_secret

# 可选数据库和路径
DATABASE_URL=sqlite:///./data/tggod.db
MEDIA_ROOT=/app/media
LOG_FILE=/app/logs/app.log
```

### 数据持久化
所有重要数据外部挂载：
- `./data/`：数据库文件
- `./media/`：下载的媒体文件
- `./logs/`：应用日志
- `./telegram_sessions/`：Telegram客户端会话

## 开发模式

### API设计
- `/api/`前缀下的RESTful端点
- 带有自动OpenAPI文档的FastAPI，访问 `/docs`
- WebSocket端点：`/ws/{client_id}` 用于实时更新
- 服务健康端点：`/api/health/*`

### 服务管理
- 应用使用现代FastAPI生命周期管理（非弃用的on_event）
- 服务通过 `service_installer.py` 在启动时自动安装依赖
- 通过 `service_monitor.py` 实时系统监控
- 所有服务优雅处理故障并继续运行

### 数据库操作
- 带有会话管理的SQLAlchemy ORM
- 根目录中的数据库架构自动迁移脚本
- 启动时自动数据库健康检查
- 支持适当会话处理的并发操作

### 前端状态管理
- 全局状态的Zustand stores（认证、设置、websocket）
- 通过WebSocket集成的实时更新
- 支持深色/浅色模式的主题系统
- 可配置密度设置的响应式设计

## 常见问题和解决方案

### 应用启动
如果应用启动失败，检查：
1. `.env` 中的环境变量配置正确
2. 必需目录存在：`data/`、`media/`、`logs/`、`telegram_sessions/`
3. 系统依赖已安装（由服务安装器自动处理）
4. 端口80未被其他服务占用

### 数据库问题
- 数据库迁移在启动时自动运行
- 如果出现架构问题，可使用归档的修复脚本：参见 `backend/scripts/archive/README.md`
- 数据库健康检查：`/api/database/check`

### 服务依赖
- 系统依赖在启动时自动安装
- 检查服务状态：`/api/health/services`
- 服务安装器日志中有手动安装命令

## API端点

开发和测试的关键端点：

### 系统健康
- `GET /health` - 基本健康检查
- `GET /api/health/services` - 详细服务健康状态
- `GET /api/system/resources` - 系统资源使用情况
- `POST /api/services/install` - 强制服务安装

### 核心功能
- `/api/telegram/*` - Telegram群组管理
- `/api/rule/*` - 过滤规则配置
- `/api/media/*` - 媒体文件操作
- `/api/task/*` - 下载任务管理
- `/api/dashboard/*` - 统计和监控

该应用包括全面的日志记录、错误处理和自动依赖管理，以确保在各种部署环境中可靠运行。