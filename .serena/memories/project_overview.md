# TgGod 项目概述

## 项目简介
TgGod是一个基于React前端和Python后端的Telegram群组消息规则下载系统，支持实时日志推送。

## 核心功能
- 智能规则过滤：关键词、时间范围、发送者等多维度过滤
- 批量下载：支持文本、图片、视频等多种媒体类型
- 实时监控：下载进度、统计图表、任务状态
- 日志推送：WebSocket实时通知 + 多渠道推送
- 现代化UI：React + TypeScript + Ant Design

## 技术栈
- **前端**: React, TypeScript, Ant Design, Socket.io
- **后端**: Python, FastAPI, Telethon, SQLAlchemy
- **数据库**: SQLite (默认)
- **部署**: Docker

## 项目结构
```
TgGod/
├── backend/          # Python后端服务
│   ├── app/
│   │   ├── api/      # API路由
│   │   ├── models/   # 数据模型
│   │   ├── services/ # 业务逻辑
│   │   ├── utils/    # 工具函数
│   │   └── websocket/ # WebSocket管理
│   └── requirements.txt
├── frontend/         # React前端应用
└── docker/           # Docker部署配置
```

## 开发状态
当前阶段：后端基础配置完成，正在开发前端React环境和后续功能。