# TgGod 架构设计和目录结构

## 整体架构

### 单服务架构设计
TgGod 采用单服务容器化架构，将前端、后端、数据库整合到一个Docker容器中：

```
┌─────────────────────────────────────┐
│           Docker Container          │
│  ┌─────────────┐  ┌───────────────┐ │
│  │   Nginx     │  │   FastAPI     │ │
│  │   (Port 80) │→ │   (Port 8000) │ │
│  │             │  │               │ │
│  │  Frontend   │  │   Backend     │ │
│  │  Static     │  │   API         │ │
│  └─────────────┘  └───────────────┘ │
│                                     │
│  ┌─────────────────────────────────┐ │
│  │        SQLite Database         │ │
│  │      (External Volume)         │ │
│  └─────────────────────────────────┘ │
└─────────────────────────────────────┘
```

### 核心组件交互
```
Frontend (React) ←→ WebSocket ←→ Backend (FastAPI)
                                      ↓
                               Telegram Service
                                      ↓
                               SQLite Database
                                      ↓
                               Media Files Storage
```

## 目录结构详解

### 项目根目录
```
TgGod/
├── backend/                 # Python后端服务
├── frontend/                # React前端应用
├── .github/                 # GitHub Actions CI/CD
├── .spec-workflow/          # 规范工作流配置
├── .claude/                 # Claude AI工具配置
├── .serena/                 # Serena开发工具配置
├── docker-compose.yml       # Docker编排配置
├── Dockerfile              # 单服务镜像构建
├── nginx.conf              # Nginx配置
├── .env.example            # 环境变量模板
├── README.md               # 项目文档
└── CLAUDE.md               # Claude开发指南
```

### 后端目录结构 (`backend/`)
```
backend/
├── app/                     # 主应用目录
│   ├── main.py             # FastAPI入口点
│   ├── config.py           # 配置管理
│   ├── database.py         # 数据库连接和会话
│   ├── api/                # REST API路由
│   │   ├── __init__.py
│   │   ├── telegram.py     # Telegram群组管理API
│   │   ├── rule.py         # 过滤规则管理API
│   │   ├── task.py         # 任务管理API
│   │   ├── media.py        # 媒体文件API
│   │   └── dashboard.py    # 仪表板数据API
│   ├── models/             # 数据库模型
│   │   ├── __init__.py
│   │   ├── telegram.py     # Telegram相关模型
│   │   ├── rule.py         # 规则和任务模型
│   │   └── user.py         # 用户管理模型
│   ├── services/           # 业务逻辑服务
│   │   ├── __init__.py
│   │   ├── telegram_service.py      # Telegram客户端服务
│   │   ├── media_downloader.py      # 媒体下载服务
│   │   ├── file_organizer_service.py # 文件组织服务
│   │   ├── task_scheduler.py        # 任务调度服务
│   │   ├── task_execution_service.py # 任务执行服务
│   │   ├── service_monitor.py       # 系统监控服务
│   │   └── service_installer.py     # 依赖安装服务
│   ├── websocket/          # WebSocket通信
│   │   ├── __init__.py
│   │   └── manager.py      # WebSocket连接管理
│   ├── utils/              # 工具函数
│   │   ├── __init__.py
│   │   ├── database_checker.py      # 数据库健康检查
│   │   ├── db_optimization.py       # 数据库优化
│   │   └── enhanced_db_session.py   # 增强数据库会话
│   ├── core/               # 核心功能模块
│   │   ├── __init__.py
│   │   └── batch_logging.py         # 批量日志处理
│   └── schemas/            # Pydantic数据模式
│       ├── __init__.py
│       ├── telegram.py     # Telegram数据模式
│       ├── rule.py         # 规则数据模式
│       └── user.py         # 用户数据模式
├── alembic/                # 数据库迁移
├── migrations/             # 自定义迁移脚本
├── requirements.txt        # Python依赖
├── Dockerfile             # 后端Docker构建文件
└── README.md              # 后端文档
```

### 前端目录结构 (`frontend/`)
```
frontend/
├── src/                    # 源代码目录
│   ├── index.tsx          # React应用入口
│   ├── App.tsx            # 主应用组件
│   ├── components/        # 可复用组件
│   │   ├── Layout/        # 布局组件
│   │   │   ├── MainLayout.tsx      # 主布局
│   │   │   └── Sidebar.tsx         # 侧边栏
│   │   ├── UserSettings/  # 用户设置组件
│   │   ├── Charts/        # 图表组件
│   │   └── ProtectedRoute.tsx      # 路由保护组件
│   ├── pages/             # 页面组件
│   │   ├── Dashboard.tsx           # 仪表板页面
│   │   ├── Groups.tsx              # 群组管理页面
│   │   ├── Rules.tsx               # 规则配置页面
│   │   ├── TaskManagement.tsx      # 任务管理页面
│   │   ├── Logs.tsx                # 日志查看页面
│   │   ├── Settings.tsx            # 设置页面
│   │   ├── Login.tsx               # 登录页面
│   │   └── ChatInterface.tsx       # 聊天界面页面
│   ├── services/          # API服务层
│   │   ├── api.ts         # API客户端配置
│   │   ├── websocket.ts   # WebSocket服务
│   │   ├── telegram.ts    # Telegram API服务
│   │   ├── rule.ts        # 规则API服务
│   │   └── task.ts        # 任务API服务
│   ├── store/             # 状态管理
│   │   ├── index.ts       # 状态导出
│   │   ├── auth.ts        # 认证状态
│   │   ├── global.ts      # 全局状态
│   │   ├── websocket.ts   # WebSocket状态
│   │   └── userSettings.ts # 用户设置状态
│   ├── types/             # TypeScript类型定义
│   │   ├── telegram.ts    # Telegram类型
│   │   ├── rule.ts        # 规则类型
│   │   ├── task.ts        # 任务类型
│   │   └── api.ts         # API响应类型
│   ├── hooks/             # 自定义React Hooks
│   ├── utils/             # 工具函数
│   └── styles/            # 样式文件
│       ├── themes.css     # 主题样式
│       └── index.css      # 全局样式
├── public/                # 静态资源
├── package.json           # 依赖配置
├── tsconfig.json          # TypeScript配置
├── Dockerfile            # 前端Docker构建文件
└── nginx.conf            # Nginx配置
```

## 数据库架构

### 核心数据表
```sql
-- Telegram群组管理
telegram_groups (id, title, username, chat_id, ...)

-- Telegram消息存储
telegram_messages (id, message_id, group_id, content, media_type, ...)

-- 过滤规则配置
filter_rules (id, name, keywords, media_types, date_from, date_to, ...)

-- 下载任务管理
download_tasks (id, name, group_id, status, progress, ...)

-- 任务-规则关联表
task_rule_associations (task_id, rule_id, is_active, ...)

-- 下载记录
download_records (id, task_id, message_id, file_path, status, ...)

-- 用户设置
user_settings (id, user_id, setting_key, setting_value, ...)
```

### 数据关系
- 群组 (1:N) 消息
- 任务 (M:N) 规则 (通过关联表)
- 任务 (1:N) 下载记录
- 消息 (1:1) 下载记录 (可选)

## 服务模块设计

### 后端服务架构
```
┌─────────────────┐
│   FastAPI App   │
├─────────────────┤
│ API Routers     │ ← HTTP请求处理
├─────────────────┤
│ Service Layer   │ ← 业务逻辑层
├─────────────────┤
│ Data Models     │ ← 数据访问层
├─────────────────┤
│ SQLite Database │ ← 数据存储层
└─────────────────┘
```

### 关键服务模块
1. **TelegramService**: Telegram客户端管理
2. **MediaDownloader**: 媒体文件下载
3. **TaskScheduler**: 后台任务调度
4. **ServiceMonitor**: 系统健康监控
5. **FileOrganizer**: 文件整理和元数据

### 前端状态架构
```
┌─────────────────┐
│ React Components│
├─────────────────┤
│ Zustand Stores  │ ← 状态管理
├─────────────────┤
│ API Services    │ ← HTTP/WebSocket
├─────────────────┤
│ Backend APIs    │ ← 数据源
└─────────────────┘
```

## 部署架构

### Docker单服务模式
- **优势**: 简化部署、统一管理、减少网络复杂度
- **数据持久化**: 外部卷挂载关键数据
- **服务发现**: 内部端口通信，外部统一入口
- **扩展性**: 支持未来微服务拆分

### 外部数据卷
```
./data/              # SQLite数据库文件
./media/             # 下载的媒体文件
./logs/              # 应用日志文件
./telegram_sessions/ # Telegram会话文件
```

### 健康检查和监控
- HTTP健康检查端点
- 系统资源监控
- 服务状态检查
- 自动重启机制

## 扩展点设计

### 插件化设计
- 过滤规则扩展
- 文件处理扩展
- 通知推送扩展
- 存储后端扩展

### 配置化管理
- 环境变量配置
- 数据库配置
- 服务参数调优
- 功能开关控制