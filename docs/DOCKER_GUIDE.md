# TgGod Docker 部署完整指南

本指南提供了 TgGod 项目的详细 Docker 部署说明，包括开发环境和生产环境的配置。

## 📋 目录

- [快速开始](#-快速开始)
- [镜像信息](#-镜像信息)
- [环境配置](#-环境配置)
- [部署方式](#-部署方式)
- [数据管理](#-数据管理)
- [监控运维](#-监控运维)
- [故障排除](#-故障排除)
- [最佳实践](#-最佳实践)

## 🚀 快速开始

### 最简单的部署方式

```bash
# 1. 创建工作目录
mkdir tggod && cd tggod

# 2. 创建必要的数据目录
mkdir -p data media logs telegram_sessions

# 3. 创建环境配置文件
cat > .env << 'EOF'
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_BOT_TOKEN=your_bot_token
SECRET_KEY=$(openssl rand -hex 32)
JWT_SECRET_KEY=$(openssl rand -hex 32)
EOF

# 4. 运行容器
docker run -d \
  --name tggod \
  -p 80:80 \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/media:/app/media \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/telegram_sessions:/app/telegram_sessions \
  await2719/tggod:latest

# 5. 检查服务状态
curl http://localhost/health
```

### 使用 docker-compose (推荐)

```bash
# 1. 下载配置文件
curl -o docker-compose.yml https://raw.githubusercontent.com/Await-d/TgGod/master/docker-compose.yml
curl -o .env.example https://raw.githubusercontent.com/Await-d/TgGod/master/.env.example

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件

# 3. 启动服务
docker-compose up -d
```

## 🐳 镜像信息

### 官方镜像

**镜像地址：** `await2719/tggod`

**支持的架构：**
- `linux/amd64` (Intel/AMD 64位)
- `linux/arm64` (ARM64/Apple Silicon)

**可用标签：**
- `latest` - 最新稳定版本
- `v1.x.x` - 指定版本号
- `main` - 主分支最新构建 (可能不稳定)

### 镜像信息查看

```bash
# 查看镜像详情
docker image inspect await2719/tggod:latest

# 查看镜像大小
docker images | grep tggod

# 拉取指定版本
docker pull await2719/tggod:v1.0.0
```

## ⚙️ 环境配置

### 必需的环境变量

| 变量名 | 说明 | 获取方式 | 示例 |
|--------|------|----------|------|
| `TELEGRAM_API_ID` | Telegram API ID | [my.telegram.org](https://my.telegram.org/apps) | `123456` |
| `TELEGRAM_API_HASH` | Telegram API Hash | [my.telegram.org](https://my.telegram.org/apps) | `abcdef123456...` |
| `TELEGRAM_BOT_TOKEN` | Bot Token | [@BotFather](https://t.me/BotFather) | `123456:ABC-DEF...` |
| `SECRET_KEY` | 应用密钥 | 随机生成 | `openssl rand -hex 32` |

### 可选的环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `JWT_SECRET_KEY` | 同 SECRET_KEY | JWT 签名密钥 |
| `DATABASE_URL` | `sqlite:////app/data/tggod.db` | 数据库连接 |
| `MEDIA_ROOT` | `/app/media` | 媒体文件目录 |
| `LOG_FILE` | `/app/logs/app.log` | 日志文件路径 |
| `LOG_LEVEL` | `INFO` | 日志级别 |

### 环境文件示例

```bash
# .env 文件内容
# ==================

# Telegram API 配置 (必需)
TELEGRAM_API_ID=123456
TELEGRAM_API_HASH=your_api_hash_from_telegram
TELEGRAM_BOT_TOKEN=123456:ABC-DEF-your-bot-token

# 安全配置 (必需)
SECRET_KEY=a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456
JWT_SECRET_KEY=f1e2d3c4b5a6789012345678901234567890fedcba1234567890fedcba123456

# 数据库配置 (可选)
DATABASE_URL=sqlite:////app/data/tggod.db

# 路径配置 (可选)
MEDIA_ROOT=/app/media
LOG_FILE=/app/logs/app.log

# 日志配置 (可选)
LOG_LEVEL=INFO
```

## 🛠️ 部署方式

### 方式一：docker-compose (推荐)

**完整的 docker-compose.yml：**

```yaml
version: '3.8'

services:
  tggod:
    image: await2719/tggod:latest
    container_name: tggod
    restart: unless-stopped

    ports:
      - "80:80"

    volumes:
      # 数据持久化
      - ./data:/app/data
      - ./media:/app/media
      - ./logs:/app/logs
      - ./telegram_sessions:/app/telegram_sessions

    environment:
      # 从 .env 文件读取环境变量
      - TELEGRAM_API_ID=${TELEGRAM_API_ID}
      - TELEGRAM_API_HASH=${TELEGRAM_API_HASH}
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - SECRET_KEY=${SECRET_KEY}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY:-${SECRET_KEY}}
      - DATABASE_URL=sqlite:////app/data/tggod.db
      - MEDIA_ROOT=/app/media
      - LOG_FILE=/app/logs/app.log

    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

    # 资源限制 (可选)
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '0.5'
        reservations:
          memory: 512M
          cpus: '0.25'

# 命名卷 (可选，用于显式声明)
volumes:
  data:
    driver: local
  media:
    driver: local
  logs:
    driver: local
  telegram_sessions:
    driver: local
```

### 方式二：Docker Run

```bash
# 基础运行命令
docker run -d \
  --name tggod \
  --restart unless-stopped \
  -p 80:80 \
  -e TELEGRAM_API_ID=your_api_id \
  -e TELEGRAM_API_HASH=your_api_hash \
  -e TELEGRAM_BOT_TOKEN=your_bot_token \
  -e SECRET_KEY=$(openssl rand -hex 32) \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/media:/app/media \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/telegram_sessions:/app/telegram_sessions \
  await2719/tggod:latest

# 带有资源限制的运行命令
docker run -d \
  --name tggod \
  --restart unless-stopped \
  --memory=1g \
  --cpus=0.5 \
  -p 80:80 \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/media:/app/media \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/telegram_sessions:/app/telegram_sessions \
  await2719/tggod:latest
```

### 方式三：Docker Swarm (集群部署)

```yaml
# docker-stack.yml
version: '3.8'

services:
  tggod:
    image: await2719/tggod:latest

    ports:
      - "80:80"

    volumes:
      - data:/app/data
      - media:/app/media
      - logs:/app/logs
      - sessions:/app/telegram_sessions

    environment:
      - TELEGRAM_API_ID=${TELEGRAM_API_ID}
      - TELEGRAM_API_HASH=${TELEGRAM_API_HASH}
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - SECRET_KEY=${SECRET_KEY}

    deploy:
      replicas: 1
      restart_policy:
        condition: on-failure
        max_attempts: 3
      resources:
        limits:
          memory: 1G
          cpus: '0.5'
      placement:
        constraints:
          - node.role == manager

volumes:
  data:
    driver: local
  media:
    driver: local
  logs:
    driver: local
  sessions:
    driver: local
```

```bash
# 部署到 Swarm
docker stack deploy -c docker-stack.yml tggod-stack
```

## 💾 数据管理

### 目录结构

```
项目根目录/
├── data/                    # 数据库文件
│   └── tggod.db            # SQLite 数据库
├── media/                   # 下载的媒体文件
│   ├── images/             # 图片文件
│   ├── videos/             # 视频文件
│   ├── documents/          # 文档文件
│   └── audio/              # 音频文件
├── logs/                    # 应用日志
│   ├── app.log             # 主应用日志
│   ├── telegram.log        # Telegram 客户端日志
│   └── download.log        # 下载任务日志
└── telegram_sessions/       # Telegram 会话文件
    ├── user.session        # 用户会话
    └── bot.session         # Bot 会话
```

### 备份策略

**1. 定期备份脚本：**

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/path/to/backups"
PROJECT_DIR="/path/to/tggod"
DATE=$(date +%Y%m%d_%H%M%S)

# 创建备份目录
mkdir -p "$BACKUP_DIR/$DATE"

# 停止服务
cd "$PROJECT_DIR"
docker-compose down

# 备份数据
tar -czf "$BACKUP_DIR/$DATE/data.tar.gz" data/
tar -czf "$BACKUP_DIR/$DATE/media.tar.gz" media/
tar -czf "$BACKUP_DIR/$DATE/sessions.tar.gz" telegram_sessions/
cp -r logs/ "$BACKUP_DIR/$DATE/"

# 重启服务
docker-compose up -d

echo "Backup completed: $BACKUP_DIR/$DATE"
```

**2. 自动化备份 (crontab)：**

```bash
# 每天凌晨 2 点自动备份
0 2 * * * /path/to/backup.sh

# 每周清理超过 30 天的备份
0 3 * * 0 find /path/to/backups -type d -mtime +30 -exec rm -rf {} \;
```

### 数据迁移

**迁移到新服务器：**

```bash
# 1. 在源服务器上备份
docker-compose down
tar -czf tggod_backup.tar.gz data/ media/ telegram_sessions/

# 2. 传输到目标服务器
scp tggod_backup.tar.gz user@new-server:/path/to/tggod/

# 3. 在目标服务器上恢复
cd /path/to/tggod
tar -xzf tggod_backup.tar.gz
docker-compose up -d
```

## 📊 监控运维

### 健康检查

```bash
# 检查服务健康状态
curl -f http://localhost/health

# 检查容器状态
docker ps
docker inspect tggod

# 查看资源使用情况
docker stats tggod
```

### 日志管理

```bash
# 查看实时日志
docker-compose logs -f

# 查看特定服务日志
docker logs tggod -f

# 查看最近 100 行日志
docker logs tggod --tail 100

# 查看指定时间段的日志
docker logs tggod --since "2024-01-01T00:00:00" --until "2024-01-02T00:00:00"
```

### 日志轮转配置

```yaml
# docker-compose.yml 中添加日志配置
services:
  tggod:
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "3"
```

### 监控脚本

```bash
#!/bin/bash
# monitor.sh - 服务监控脚本

SERVICE_NAME="tggod"
WEBHOOK_URL="https://hooks.slack.com/your/webhook/url"

# 检查容器是否运行
if ! docker ps | grep -q "$SERVICE_NAME"; then
    echo "❌ $SERVICE_NAME is not running!"

    # 发送告警通知
    curl -X POST -H 'Content-type: application/json' \
        --data '{"text":"🚨 TgGod service is down!"}' \
        "$WEBHOOK_URL"

    # 尝试重启
    docker-compose restart
fi

# 检查健康状态
if ! curl -f http://localhost/health >/dev/null 2>&1; then
    echo "❌ $SERVICE_NAME health check failed!"

    # 查看容器日志
    docker logs "$SERVICE_NAME" --tail 50

    # 发送告警
    curl -X POST -H 'Content-type: application/json' \
        --data '{"text":"🚨 TgGod health check failed!"}' \
        "$WEBHOOK_URL"
fi

echo "✅ $SERVICE_NAME is healthy"
```

## 🔧 故障排除

### 常见问题诊断

**1. 容器无法启动**

```bash
# 查看详细错误信息
docker-compose logs tggod

# 检查端口是否被占用
netstat -tlnp | grep :80
lsof -i :80

# 检查磁盘空间
df -h

# 检查权限
ls -la data/ media/ logs/ telegram_sessions/
```

**2. Telegram 认证失败**

```bash
# 检查 API 凭据
echo "API_ID: $TELEGRAM_API_ID"
echo "API_HASH: $TELEGRAM_API_HASH"
echo "BOT_TOKEN: $TELEGRAM_BOT_TOKEN"

# 清除会话文件重新认证
rm -rf telegram_sessions/*
docker-compose restart

# 查看 Telegram 相关日志
docker logs tggod | grep -i telegram
```

**3. 数据库问题**

```bash
# 检查数据库文件
ls -la data/tggod.db

# 检查数据库完整性
docker exec -it tggod sqlite3 /app/data/tggod.db ".schema"

# 备份并重置数据库
cp data/tggod.db data/tggod.db.backup
rm data/tggod.db
docker-compose restart
```

**4. 性能问题**

```bash
# 查看资源使用情况
docker stats tggod

# 检查磁盘 I/O
iostat -x 1

# 检查内存使用
free -h

# 查看容器内进程
docker exec -it tggod top
```

### 调试模式

```bash
# 启用调试模式
docker-compose down
docker-compose -f docker-compose.yml -f docker-compose.debug.yml up -d

# 进入容器进行调试
docker exec -it tggod bash

# 查看详细的应用日志
docker exec -it tggod tail -f /app/logs/app.log
```

### 重置服务

```bash
# 完全重置服务（谨慎操作）
docker-compose down -v
docker rmi await2719/tggod:latest
rm -rf data/ logs/
mkdir -p data logs media telegram_sessions
docker-compose up -d
```

## 🏆 最佳实践

### 生产环境部署

1. **使用固定版本标签**
   ```yaml
   image: await2719/tggod:v1.0.0  # 而不是 latest
   ```

2. **设置资源限制**
   ```yaml
   deploy:
     resources:
       limits:
         memory: 1G
         cpus: '0.5'
   ```

3. **配置健康检查**
   ```yaml
   healthcheck:
     test: ["CMD", "curl", "-f", "http://localhost/health"]
     interval: 30s
     timeout: 10s
     retries: 3
   ```

4. **使用外部网络**
   ```yaml
   networks:
     - traefik
   ```

### 安全配置

1. **使用强密码**
   ```bash
   openssl rand -base64 32
   ```

2. **限制容器权限**
   ```yaml
   security_opt:
     - no-new-privileges:true
   user: "1000:1000"
   ```

3. **只暴露必要端口**
   ```yaml
   ports:
     - "127.0.0.1:80:80"  # 只绑定本地接口
   ```

### 维护建议

1. **定期更新镜像**
   ```bash
   docker-compose pull
   docker-compose up -d
   ```

2. **定期清理**
   ```bash
   docker system prune -f
   docker image prune -f
   ```

3. **监控磁盘使用**
   ```bash
   du -sh data/ media/ logs/
   ```

4. **备份策略**
   - 每日备份数据库
   - 每周备份媒体文件
   - 每月备份完整系统

## 📚 相关资源

- [Docker 官方文档](https://docs.docker.com/)
- [Docker Compose 参考](https://docs.docker.com/compose/)
- [Telegram API 文档](https://core.telegram.org/api)
- [TgGod 项目文档](../CLAUDE.md)

---

**需要帮助？**

如果遇到问题，请：
1. 查看 [故障排除](#-故障排除) 章节
2. 检查 [GitHub Issues](https://github.com/Await-d/TgGod/issues)
3. 创建新的 Issue 描述您的问题