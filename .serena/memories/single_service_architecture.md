# 单服务架构合并总结

## 架构变更
- **之前**: 三个独立服务（backend、frontend、database）
- **现在**: 单一服务（前端 + 后端 + 数据库）

## 主要变更

### 1. 服务架构
- 使用多阶段Docker构建
- 前端编译为静态文件，通过Nginx服务
- 后端FastAPI运行在8000端口
- Nginx反向代理API请求到后端

### 2. 数据库配置
- SQLite数据库文件外部挂载到 `./data/tggod.db`
- 媒体文件挂载到 `./media/`
- 日志文件挂载到 `./logs/`
- Telegram会话文件挂载到 `./telegram_sessions/`

### 3. 配置文件
- `Dockerfile`: 多阶段构建配置
- `docker-compose.yml`: 单服务编排
- `nginx.conf`: Nginx配置，处理静态文件和API代理
- `start.sh`: 启动脚本，同时启动Nginx和FastAPI

### 4. 端口变更
- 对外端口：80（统一入口）
- 内部端口：8000（FastAPI，不对外暴露）

## 优势
1. **部署简化**: 只需一个服务
2. **资源优化**: 减少容器数量
3. **配置集中**: 统一管理配置
4. **数据持久化**: 所有数据外部挂载