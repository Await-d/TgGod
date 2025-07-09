# TgGod - Telegram群组规则下载系统

基于React前端和Python后端的Telegram群组消息规则下载系统，支持实时日志推送。

## 功能特性

- 🔍 **智能规则过滤**: 关键词、时间范围、发送者等多维度过滤
- 📥 **批量下载**: 支持文本、图片、视频等多种媒体类型
- 📊 **实时监控**: 下载进度、统计图表、任务状态
- 🔔 **日志推送**: WebSocket实时通知 + 多渠道推送
- 🎨 **现代化UI**: React + TypeScript + Ant Design

## 项目结构

```
TgGod/
├── backend/          # Python后端
├── frontend/         # React前端
├── docker/           # Docker配置
├── docs/             # 文档
└── README.md
```

## 技术栈

- **前端**: React, TypeScript, Ant Design, Socket.io
- **后端**: Python, FastAPI, Telethon, SQLAlchemy
- **数据库**: SQLite (默认)
- **部署**: Docker

## 开发状态

🚧 项目正在开发中...

当前进度: 6/6 - 🎉 **项目完成！** 🎉

## 功能特性

### 📊 仪表板
- 实时统计图表
- 任务进度监控
- 系统状态总览

### 👥 群组管理
- 添加/删除Telegram群组
- 消息同步和统计
- 群组状态控制

### 🔧 规则配置
- 多维度过滤规则
- 关键词、媒体类型、时间范围过滤
- 发送者筛选

### 📥 下载任务
- 批量下载任务创建
- 实时进度监控
- 任务状态控制

### 📋 日志系统
- 实时日志推送
- 多级别日志分类
- WebSocket实时通信

## 快速开始

### 使用Docker部署

```bash
# 1. 克隆项目
git clone <repository-url>
cd TgGod

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入您的Telegram API信息

# 3. 启动服务
docker-compose up -d

# 4. 访问应用
# 前端: http://localhost
# 后端: http://localhost:8000
```

### 本地开发

```bash
# 后端开发
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# 前端开发
cd frontend
pnpm install
pnpm dev
```

详细部署指南请参考 [docs/deployment.md](docs/deployment.md)