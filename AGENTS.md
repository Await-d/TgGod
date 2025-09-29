# Repository Guidelines

本指南面向所有参与 TgGod 的贡献者，帮助快速掌握架构、开发流程与质量基准。所有贡献前请在 issue 或讨论中同步预期影响与回滚计划，必要时安排结对审查保障交付质量。请始终贯彻 KISS、YAGNI、SOLID 与 DRY 原则，以最小实现满足需求、保持职责清晰并避免重复实现。

## Project Structure & 模块组织
- **backend/app**：FastAPI 入口、配置、SQLAlchemy 模型、API、服务层与 websocket 管理，按领域拆分到 `api/`、`models/`、`services/`、`utils/`。
- **frontend/src**：React + TypeScript 页面、组件、Zustand 状态与 API 适配层；公用资源置于 `components/` 与 `utils/`。
- **scripts/** 与根级 `docker-compose.yml`：部署脚本与容器编排，`scripts/deployment/quick-start.sh` 提供一键启动。
- **data/` `media/` `logs/` `telegram_sessions/`**：数据库、媒体与会话缓存挂载目录，部署前需准备持久化卷。

## Architecture Overview
- 默认单容器架构：Nginx 提供前端静态资源，FastAPI 在 8000 端口服务 API，SQLite 外挂至 `./data`。
- 内部事件依赖服务层（`services/`）调度 Telethon 客户端；前端通过 REST + WebSocket 同步任务状态。

## Build, Test & Development Commands
- `docker-compose up -d --build`：构建并启动前后端及数据库，适合验收集成变更。
- `cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8001`：本地开发后端，热重载并执行数据库自检。
- `cd frontend && pnpm install && pnpm start`：安装依赖并启动前端调试服务器（代理本地 3001 后端）。
- `cd frontend && pnpm test`：运行 React 单元测试；`pnpm build` 生成生产构建。

## Coding Style & 命名规范
- Python 采用 4 空格缩进、PEP 8 命名；抽象接口置于 `services/` 或 `core/`，文档字符串使用中文说明输入输出。
- TypeScript 组件使用函数式 + Hooks，小驼峰函数/变量，大驼峰组件/类型；启用 React Scripts 自带 ESLint 和 Prettier 对齐格式。
- 提交逻辑前复用现有工具函数，拒绝重复判断或魔术常量。

## Testing Guidelines
- 后端逐步完善 `backend/tests/<domain>/test_*.py`，使用 pytest + async 测试夹具验证规则引擎、下载调度与通知。
- 前端测试文件放在与组件同级的 `*.test.tsx`，覆盖状态切换、数据渲染和关键交互；必要时补充快照。
- Schema、API 或 WebSocket 变更需在 PR 中记录手动验证（Postman 调用或前端演示）。

## Commit & Pull Request Guidelines
- 遵循 Conventional Commits，例如 `feat(dashboard): ...`、`fix(backend): ...`；信息描述动机、范围与用户影响，建议使用中文。
- PR 描述包含摘要、测试结果、关联 issue、部署影响；UI 变更附截图或短视频，保持 PR 模块化可随时回滚。
- 变更保持单一职责，提交前确认 Docker 构建、关键脚本无告警，并同步更新相关文档。

## Security & 配置提示
- 所有密钥、Telegram API ID 与 session 文件仅存 `.env` 或挂载目录，严禁提交仓库。
- 配置最小权限的挂载目录，定期清理过期 session 与冗余媒体，避免泄露。
- 引入新依赖前检查许可证并锁定版本（`requirements.txt`、`pnpm-lock.yaml`），必要时附兼容性说明。
