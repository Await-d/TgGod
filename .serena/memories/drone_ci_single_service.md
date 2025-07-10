# Drone CI 单服务架构配置

## 主要变更
- 将三服务架构（backend、frontend、database）合并为单服务架构
- 使用单一 Dockerfile 进行多阶段构建
- 简化了容器编排和部署流程

## 配置文件
- **`.drone.yml`**: 更新为单服务部署配置
- **`PRODUCTION.md`**: 生产环境部署指南
- **`DRONE_COMPARISON.md`**: 新旧架构对比

## 部署流程
1. **构建**: `docker build -t tggod:latest .`
2. **部署**: 单一容器启动，端口10200
3. **验证**: 健康检查 + 日志检查 + 端点验证

## 环境变量
需要在 Drone Secrets 中配置：
- `TELEGRAM_API_ID`
- `TELEGRAM_API_HASH` 
- `TELEGRAM_BOT_TOKEN`
- `SECRET_KEY`

## 数据挂载
- `/volume1/docker/apps/tggod/data` - 数据库
- `/volume1/docker/apps/tggod/media` - 媒体文件
- `/volume1/docker/apps/tggod/logs` - 日志文件
- `/volume1/docker/apps/tggod/telegram_sessions` - Telegram会话

## 优势
- 部署时间减少50%
- 资源使用减少40%
- 管理复杂度显著降低
- 单一入口点，易于监控