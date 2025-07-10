# TgGod 单服务部署指南

## 概述

TgGod 现已合并为单一服务架构，包含：
- 前端 React 应用（通过 Nginx 提供静态文件服务）
- 后端 FastAPI 服务
- SQLite 数据库（外部挂载）

## 部署步骤

### 1. 环境准备

确保安装了以下软件：
- Docker
- Docker Compose

### 2. 克隆项目

```bash
git clone <repository-url>
cd TgGod
```

### 3. 环境变量配置

复制环境变量模板：
```bash
cp .env.example .env
```

编辑 `.env` 文件，设置必要的环境变量：
```env
# Telegram API 配置
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_BOT_TOKEN=your_bot_token

# 安全配置
SECRET_KEY=your_secret_key_here
```

### 4. 创建数据目录

```bash
mkdir -p data media logs telegram_sessions
```

### 5. 启动服务

```bash
docker-compose up -d
```

### 6. 访问应用

- 前端应用：http://localhost
- API 文档：http://localhost/docs
- 健康检查：http://localhost/health

## 目录结构

```
TgGod/
├── data/                    # 数据库文件（外部挂载）
├── media/                   # 媒体文件（外部挂载）
├── logs/                    # 日志文件（外部挂载）
├── telegram_sessions/       # Telegram会话文件（外部挂载）
├── Dockerfile              # 单服务 Docker 镜像
├── docker-compose.yml      # 单服务编排文件
├── nginx.conf              # Nginx 配置
└── start.sh               # 启动脚本
```

## 数据持久化

所有重要数据都存储在外部挂载的目录中：

- **数据库**: `./data/tggod.db`
- **媒体文件**: `./media/`
- **日志文件**: `./logs/app.log`
- **Telegram会话**: `./telegram_sessions/`

## 服务管理

### 启动服务
```bash
docker-compose up -d
```

### 停止服务
```bash
docker-compose down
```

### 重启服务
```bash
docker-compose restart
```

### 查看日志
```bash
docker-compose logs -f
```

### 更新应用
```bash
git pull
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## 端口说明

- **80**: 前端应用和API服务（通过Nginx代理）
- **内部8000**: 后端FastAPI服务（不对外暴露）

## 健康检查

服务包含健康检查功能：
- 检查URL: `http://localhost/health`
- 检查间隔: 30秒
- 超时时间: 10秒
- 重试次数: 3次

## 故障排除

### 1. 服务启动失败

检查日志：
```bash
docker-compose logs
```

常见问题：
- 端口冲突：确保80端口未被占用
- 环境变量缺失：检查 `.env` 文件配置
- 权限问题：确保数据目录有写入权限

### 2. 数据库连接问题

检查数据库文件是否正确创建：
```bash
ls -la data/
```

如果数据库文件不存在，重启服务：
```bash
docker-compose restart
```

### 3. Telegram认证问题

检查Telegram会话文件：
```bash
ls -la telegram_sessions/
```

如果需要重新认证，删除会话文件：
```bash
rm -f telegram_sessions/*
```

## 备份和恢复

### 备份数据
```bash
# 备份数据库
cp data/tggod.db backup/tggod_$(date +%Y%m%d_%H%M%S).db

# 备份媒体文件
tar -czf backup/media_$(date +%Y%m%d_%H%M%S).tar.gz media/

# 备份Telegram会话
tar -czf backup/sessions_$(date +%Y%m%d_%H%M%S).tar.gz telegram_sessions/
```

### 恢复数据
```bash
# 停止服务
docker-compose down

# 恢复数据库
cp backup/tggod_YYYYMMDD_HHMMSS.db data/tggod.db

# 恢复媒体文件
tar -xzf backup/media_YYYYMMDD_HHMMSS.tar.gz

# 恢复Telegram会话
tar -xzf backup/sessions_YYYYMMDD_HHMMSS.tar.gz

# 重启服务
docker-compose up -d
```

## 升级说明

从三服务架构升级到单服务架构：

1. 备份现有数据
2. 停止旧服务：`docker-compose down`
3. 更新代码：`git pull`
4. 重新构建：`docker-compose build --no-cache`
5. 启动新服务：`docker-compose up -d`

## 性能优化

1. **数据库优化**：定期清理旧数据和日志
2. **媒体文件管理**：定期清理不需要的媒体文件
3. **日志轮转**：配置日志轮转避免日志文件过大
4. **资源监控**：监控CPU和内存使用情况

## 安全建议

1. 定期更新环境变量中的密钥
2. 限制容器的资源使用
3. 使用防火墙限制访问
4. 定期备份重要数据
5. 监控服务日志异常情况