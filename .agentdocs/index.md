# TgGod 项目知识库索引

## 项目概述
TgGod 是一个 Telegram 群组规则下载系统，包含 React 前端和 FastAPI 后端。

## 当前任务文档

### 已完成
- `workflow/done/260114-页面全面改造.md` - 前端所有页面的全面改造计划 ✅ (2026-01-17 完成)
- `workflow/260117-聊天界面重构.md` - 聊天界面布局重构方案 ✅ (2026-01-17 完成)

### 进行中
- `workflow/260320-未完成功能修复计划.md` — 项目全面修复计划（P0~P4优先级）

## 技术栈
- **前端**: React 18 + TypeScript + Ant Design 5.x + Zustand
- **后端**: FastAPI + SQLAlchemy + SQLite
- **部署**: Docker + Nginx

## 页面清单
| 页面 | 文件 | 描述 |
|------|------|------|
| 仪表板 | `Dashboard.tsx` | 系统概览和统计 |
| 聊天界面 | `ChatInterface.tsx` | 群组消息浏览 |
| 群组管理 | `Groups.tsx` | Telegram 群组管理 |
| 规则管理 | `Rules.tsx` | 下载规则配置 |
| 任务管理 | `TaskManagement.tsx` | 下载任务管理 |
| 消息管理 | `Messages.tsx` | 消息列表和操作 |
| 下载历史 | `DownloadHistory.tsx` | 下载记录查看 |
| 系统设置 | `Settings.tsx` | 系统配置 |
| 系统状态 | `SystemStatus.tsx` | 系统健康监控 |
| 数据库状态 | `DatabaseStatus.tsx` | 数据库监控 |
| 日志查看 | `Logs.tsx` | 系统日志 |
| 登录 | `Login.tsx` | 用户认证 |

## 相关文档
- `frontend/CLAUDE.md` - 前端开发记忆
- `CLAUDE.md` - 项目整体指导
