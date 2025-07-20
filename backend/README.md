# TgGod Backend

TgGod 是一个 Telegram 群组规则下载系统的后端服务，基于 FastAPI + SQLAlchemy 开发。

## 项目结构

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI应用入口
│   ├── config.py         # 配置管理
│   ├── database.py       # 数据库连接
│   ├── models/           # 数据模型
│   │   ├── __init__.py
│   │   ├── telegram.py   # Telegram相关模型
│   │   ├── rule.py       # 规则模型
│   │   └── log.py        # 日志模型
│   ├── api/              # API路由
│   │   ├── __init__.py
│   │   ├── telegram.py   # Telegram API
│   │   ├── rule.py       # 规则管理API
│   │   ├── media.py      # 媒体文件API
│   │   └── log.py        # 日志API
│   ├── services/         # 业务逻辑
│   │   ├── __init__.py
│   │   ├── telegram_service.py
│   │   ├── media_downloader.py  # 媒体下载服务
│   │   ├── rule_service.py
│   │   └── notification_service.py
│   ├── utils/            # 工具函数
│   │   ├── __init__.py
│   │   ├── logger.py
│   │   └── helpers.py
│   └── websocket/        # WebSocket处理
│       ├── __init__.py
│       └── manager.py
├── fix_database_schema.py   # 数据库字段修复工具
├── init_database.py         # 数据库初始化脚本
├── requirements.txt         # Python依赖
├── Dockerfile              # Docker配置
└── .env.example            # 环境变量示例
```

## 自动化启动流程

### 数据库自动修复机制

应用启动时会自动执行以下检查和修复步骤：

1. **数据库字段检查**
   - 自动检测缺失的下载进度字段
   - 检查基础业务字段完整性
   - 实时显示检查进度

2. **自动字段修复**
   - 发现缺失字段时自动添加
   - 支持的修复字段：
     - `download_progress` - 下载进度 (0-100)
     - `downloaded_size` - 已下载字节数
     - `download_speed` - 下载速度 (bytes/sec)
     - `estimated_time_remaining` - 预计剩余时间
     - `download_started_at` - 下载开始时间

3. **启动日志示例**
   ```
   🔧 正在检查数据库字段...
   数据库路径: /app/data/tggod.db
   📋 检查telegram_messages表的字段...
   ✓ 列已存在: telegram_messages.download_progress
   ✅ 数据库字段检查和修复完成
   ```

### 手动运行修复工具

如果需要单独运行数据库修复：

```bash
# 激活虚拟环境
source venv/bin/activate

# 运行数据库字段修复工具
python fix_database_schema.py

# 或运行完整数据库初始化
python init_database.py
```

## 启动应用

```bash
# 开发模式
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# 生产模式
python -m app.main
```

## 主要功能特性

- ✅ **自动数据库修复** - 启动时自动检查和修复缺失字段
- ✅ **实时下载进度** - 支持媒体文件下载进度跟踪
- ✅ **WebSocket通信** - 实时消息推送和状态更新
- ✅ **媒体文件管理** - 支持图片、视频、音频、文档下载
- ✅ **规则引擎** - 智能消息过滤和下载规则
- ✅ **用户认证** - JWT Token 认证系统

## 环境要求

- Python 3.11+
- SQLAlchemy 2.0+
- FastAPI 0.100+
- Telethon (Telegram API客户端)