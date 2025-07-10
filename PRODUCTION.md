# 生产环境部署指南

## Drone CI 配置

TgGod 已配置为使用 Drone CI 进行自动化部署。以下是生产环境配置的详细说明。

### 配置概览

- **架构**: 单服务架构（前端 + 后端 + 数据库）
- **容器名**: `tggod`
- **端口**: `10200:80`
- **网络**: `1panel-network`
- **数据挂载**: `/volume1/docker/apps/tggod/`

### 环境变量配置

在 Drone 中需要配置以下 Secret 环境变量：

```bash
# Telegram API 配置
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_BOT_TOKEN=your_bot_token

# 安全配置
SECRET_KEY=your_secret_key_change_in_production
```

### 目录结构

生产环境中的数据目录结构：

```
/volume1/docker/apps/tggod/
├── data/                    # SQLite 数据库
├── media/                   # 媒体文件
├── logs/                    # 日志文件
├── telegram_sessions/       # Telegram 会话文件
└── config/                  # 配置文件
```

### 部署流程

1. **代码推送触发**
   - 推送到 `master` 分支自动触发部署

2. **清理阶段**
   ```bash
   # 清理 Docker 缓存
   docker system prune -f --volumes
   docker builder prune -f
   
   # 停止旧容器
   docker stop tggod || true
   docker rm tggod || true
   ```

3. **构建阶段**
   ```bash
   # 构建单服务镜像
   docker build -t tggod:latest . --no-cache
   ```

4. **部署阶段**
   ```bash
   # 创建目录并设置权限
   mkdir -p /volume1/docker/apps/tggod/{data,media,logs,telegram_sessions,config}
   chmod -R 755 /volume1/docker/apps/tggod
   chown -R 1000:1000 /volume1/docker/apps/tggod
   
   # 启动容器
   docker run -d --name tggod \
     --network 1panel-network \
     -p 10200:80 \
     -v /volume1/docker/apps/tggod/data:/app/data \
     -v /volume1/docker/apps/tggod/media:/app/media \
     -v /volume1/docker/apps/tggod/logs:/app/logs \
     -v /volume1/docker/apps/tggod/telegram_sessions:/app/telegram_sessions \
     --restart unless-stopped \
     -e TZ=Asia/Shanghai \
     -e DATABASE_URL=sqlite:///./data/tggod.db \
     -e MEDIA_ROOT=/app/media \
     -e LOG_FILE=/app/logs/app.log \
     -e PYTHONUNBUFFERED=1 \
     -e TELEGRAM_API_ID="$TELEGRAM_API_ID" \
     -e TELEGRAM_API_HASH="$TELEGRAM_API_HASH" \
     -e TELEGRAM_BOT_TOKEN="$TELEGRAM_BOT_TOKEN" \
     -e SECRET_KEY="$SECRET_KEY" \
     tggod:latest
   ```

5. **验证阶段**
   ```bash
   # 健康检查
   curl -f http://localhost:10200/health
   
   # 检查容器日志
   docker logs --tail 20 tggod
   
   # 验证服务端点
   curl -s http://localhost:10200/
   curl -s http://localhost:10200/docs
   ```

### 访问地址

部署完成后的访问地址：

- **前端应用**: http://localhost:10200
- **API 文档**: http://localhost:10200/docs
- **健康检查**: http://localhost:10200/health

### 监控和维护

#### 查看日志
```bash
# 实时日志
docker logs -f tggod

# 最近日志
docker logs --tail 100 tggod
```

#### 重启服务
```bash
docker restart tggod
```

#### 更新部署
```bash
# 手动触发更新（推送代码到 master 分支）
git push origin master
```

#### 数据备份
```bash
# 备份数据库
cp /volume1/docker/apps/tggod/data/tggod.db /backup/tggod_$(date +%Y%m%d_%H%M%S).db

# 备份媒体文件
tar -czf /backup/media_$(date +%Y%m%d_%H%M%S).tar.gz /volume1/docker/apps/tggod/media/

# 备份 Telegram 会话
tar -czf /backup/sessions_$(date +%Y%m%d_%H%M%S).tar.gz /volume1/docker/apps/tggod/telegram_sessions/
```

### 故障排除

#### 1. 容器启动失败

**检查容器状态**:
```bash
docker ps -a | grep tggod
```

**查看详细日志**:
```bash
docker logs tggod
```

**常见问题**:
- 端口 10200 被占用
- 环境变量未正确设置
- 挂载目录权限问题

#### 2. 健康检查失败

**检查服务状态**:
```bash
curl -v http://localhost:10200/health
```

**检查网络连接**:
```bash
docker network ls
docker network inspect 1panel-network
```

#### 3. 数据库问题

**检查数据库文件**:
```bash
ls -la /volume1/docker/apps/tggod/data/
```

**检查权限**:
```bash
ls -la /volume1/docker/apps/tggod/
```

### 安全配置

1. **环境变量安全**:
   - 确保所有敏感信息存储在 Drone Secrets 中
   - 定期更换 SECRET_KEY

2. **网络安全**:
   - 使用内部网络 `1panel-network`
   - 仅暴露必要的端口

3. **文件权限**:
   - 设置合适的目录权限 (755)
   - 使用非 root 用户 (1000:1000)

### 性能优化

1. **Docker 缓存管理**:
   - 定期清理无用镜像和容器
   - 限制缓存存储大小

2. **日志轮转**:
   - 配置 Docker 日志驱动
   - 设置日志文件大小限制

3. **资源限制**:
   ```bash
   # 可选：添加资源限制
   --memory="512m" --cpus="1.0"
   ```

### 版本管理

- **镜像标签**: 使用 `latest` 标签跟踪最新版本
- **回滚策略**: 保留前一个版本的镜像用于快速回滚
- **发布流程**: master 分支推送 → 自动构建 → 自动部署