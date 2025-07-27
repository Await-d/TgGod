# 项目构建限制

## 重要限制
- **不允许使用 `npm run build` 指令**
- **不允许执行 Docker 构建操作**
- 前端可以使用 `npx tsc --noEmit` 检查 TypeScript 类型错误
- 可以使用 `npx` 进行类型检查和代码验证

## 开发建议
- 使用 TypeScript 编译器进行静态检查
- 通过 `npx` 运行开发工具和检查命令
- 避免触发任何构建或部署流程

## 项目特点
- TgGod 是一个 Telegram 群组规则下载系统
- 前端: React + TypeScript + Ant Design
- 后端: Python + FastAPI + Telethon + SQLAlchemy
- 部署: Docker 单服务架构