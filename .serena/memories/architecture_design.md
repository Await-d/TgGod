# TgGod核心架构设计

## 系统架构
- **前端**: React SPA with TypeScript
- **后端**: FastAPI with async/await
- **数据库**: SQLite with aiosqlite
- **实时通信**: WebSocket for log pushing
- **API设计**: RESTful API + WebSocket

## 关键设计决策
1. **数据库选择**: SQLite替代Redis，简化部署
2. **包管理**: pnpm用于前端开发和构建
3. **状态管理**: Zustand轻量级状态管理
4. **UI框架**: Ant Design提供企业级组件
5. **异步处理**: 全异步Python后端架构

## 核心服务
- **TelegramService**: Telethon客户端封装
- **WebSocketManager**: 实时连接管理
- **DatabaseService**: SQLAlchemy ORM操作
- **TaskService**: 下载任务调度

## API端点结构
- `/api/telegram/` - 群组管理
- `/api/rule/` - 规则配置
- `/api/task/` - 任务管理
- `/api/log/` - 日志查询
- `/ws/{client_id}` - WebSocket连接

## 前端路由
- `/dashboard` - 仪表板
- `/groups` - 群组管理
- `/rules` - 规则配置
- `/downloads` - 下载任务
- `/logs` - 日志查看