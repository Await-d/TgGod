# TgGod - Telegram智能媒体下载管理系统

<div align="center">

[![GitHub stars](https://img.shields.io/github/stars/Await-d/TgGod?style=flat-square)](https://github.com/Await-d/TgGod/stargazers)
[![GitHub issues](https://img.shields.io/github/issues/Await-d/TgGod?style=flat-square)](https://github.com/Await-d/TgGod/issues)
[![Docker Pulls](https://img.shields.io/docker/pulls/await2719/tggod?style=flat-square)](https://hub.docker.com/r/await2719/tggod)
[![License](https://img.shields.io/github/license/Await-d/TgGod?style=flat-square)](LICENSE)

🚀 **基于规则的 Telegram 群组媒体智能下载系统**

[English](README_EN.md) | 简体中文

</div>

---

## ✨ 项目介绍

TgGod 是一个功能强大的 Telegram 群组媒体下载管理系统，通过智能规则过滤和自动化下载，帮助用户高效管理和归档 Telegram 群组中的媒体内容。采用现代化技术栈，提供直观的 Web 界面和完善的 API 支持。

### 🎯 核心特点

- **🤖 智能过滤** - 多维度规则引擎，精准筛选所需内容
- **⚡ 高性能下载** - 并发下载支持，断点续传，速度优化
- **📱 响应式界面** - 适配桌面和移动设备，随时随地管理
- **🔔 实时通知** - WebSocket 推送，及时掌握下载进度
- **🐳 容器化部署** - 一键部署，开箱即用
- **🔐 安全可靠** - 数据加密存储，会话安全管理

## 🚀 功能特性

### 核心功能
- **🔍 智能规则过滤**
  - 多维度过滤：关键词、正则表达式、媒体类型、文件大小
  - 时间范围筛选：精确到秒的时间控制
  - 发送者过滤：支持用户名、用户ID筛选
  - 组合规则：AND/OR逻辑组合，满足复杂筛选需求

- **📥 高效下载管理**
  - 批量下载：一键下载符合规则的所有媒体
  - 断点续传：网络中断自动恢复
  - 并发控制：智能调度，避免触发限制
  - 文件去重：自动识别重复文件

- **📊 实时监控仪表板**
  - 下载进度实时显示
  - 系统资源监控（CPU、内存、磁盘）
  - 任务队列可视化
  - 历史数据统计图表

- **🔔 智能通知系统**
  - WebSocket 实时推送
  - 多级别日志分类
  - 异常自动告警
  - 下载完成通知

- **🎨 现代化用户界面**
  - 响应式设计，完美适配各种设备
  - 深色/浅色主题切换
  - 拖拽式操作
  - 国际化支持（中文/英文）

## 项目结构

```
TgGod/
├── backend/          # Python后端
├── frontend/         # React前端
├── docker/           # Docker配置
├── docs/             # 文档
└── README.md
```

## 技术栈

- **前端**: React, TypeScript, Ant Design, Socket.io
- **后端**: Python, FastAPI, Telethon, SQLAlchemy
- **数据库**: SQLite (外部挂载)
- **部署**: Docker (单服务架构)

## 快速开始

### 🚀 方式一：使用预构建 Docker 镜像 (推荐)

```bash
# 1. 创建项目目录
mkdir tggod && cd tggod

# 2. 下载配置文件
wget https://raw.githubusercontent.com/Await-d/TgGod/master/docker-compose.yml
wget https://raw.githubusercontent.com/Await-d/TgGod/master/.env.example

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，配置您的Telegram API信息

# 4. 启动服务 (自动拉取最新镜像)
docker-compose up -d

# 5. 访问应用
# 前端界面: http://localhost
# API文档: http://localhost/docs
```

### 🔧 方式二：从源码构建

```bash
# 1. 克隆项目
git clone https://github.com/Await-d/TgGod.git
cd TgGod

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，配置Telegram API信息

# 3. 启动服务
docker-compose up -d --build

# 4. 访问应用
# 前端: http://localhost
# API: http://localhost/docs
```

### ⚡ 方式三：一键启动脚本

```bash
git clone https://github.com/Await-d/TgGod.git
cd TgGod
./scripts/deployment/quick-start.sh
```

## 服务架构

**单服务架构** - 前端 + 后端 + 数据库合并为一个容器：
- **端口**: 80 (统一入口)
- **前端**: Nginx 提供静态文件服务
- **后端**: FastAPI 运行在内部8000端口
- **数据库**: SQLite 外部挂载持久化
- **文件**: 媒体、日志、会话文件外部挂载

## 数据持久化

所有重要数据都挂载到外部目录：
```
./data/              # 数据库文件
./media/             # 媒体文件
./logs/              # 日志文件
./telegram_sessions/ # Telegram会话
```

## 📸 界面预览

<details>
<summary>点击查看界面截图</summary>

### 仪表板
![Dashboard](docs/images/dashboard.png)

### 规则管理
![Rules](docs/images/rules.png)

### 下载任务
![Tasks](docs/images/tasks.png)

### 实时日志
![Logs](docs/images/logs.png)

</details>

## 🎯 适用场景

- **📚 内容归档** - 保存重要群组的历史消息和媒体
- **🎬 媒体收集** - 自动收集特定类型的图片、视频
- **📰 信息监控** - 监控特定关键词的消息
- **💾 数据备份** - 定期备份群组内容
- **🔍 内容筛选** - 从海量消息中筛选有价值的信息

## 功能特性

### 📊 仪表板
- 实时统计图表
- 任务进度监控
- 系统状态总览

### 👥 群组管理
- 添加/删除Telegram群组
- 消息同步和统计
- 群组状态控制

### 🔧 规则配置
- 多维度过滤规则
- 关键词、媒体类型、时间范围过滤
- 发送者筛选

### 📥 下载任务
- 批量下载任务创建
- 实时进度监控
- 任务状态控制

### 📋 日志系统
- 实时日志推送
- 多级别日志分类
- WebSocket实时通信

## 🐳 Docker 部署方式

### 预构建镜像 (推荐)

我们提供了官方 Docker 镜像，支持多架构部署：

```bash
# 拉取最新镜像
docker pull await2719/tggod:latest

# 或指定版本 (例如)
docker pull await2719/tggod:v1.0.0

# 查看所有可用版本
docker search await2719/tggod
```

**支持的架构：**
- `linux/amd64` (x86_64)
- `linux/arm64` (ARM64/Apple Silicon)

### 完整部署示例

#### 1. 使用 docker-compose (推荐)

```yaml
# docker-compose.yml
services:
  tggod:
    image: await2719/tggod:latest
    container_name: tggod
    ports:
      - "80:80"
    volumes:
      - ./data:/app/data
      - ./media:/app/media
      - ./logs:/app/logs
      - ./telegram_sessions:/app/telegram_sessions
    environment:
      - DATABASE_URL=sqlite:////app/data/tggod.db
      - TELEGRAM_API_ID=${TELEGRAM_API_ID}
      - TELEGRAM_API_HASH=${TELEGRAM_API_HASH}
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - SECRET_KEY=${SECRET_KEY}
      - MEDIA_ROOT=/app/media
      - LOG_FILE=/app/logs/app.log
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

#### 2. 使用 docker run

```bash
# 创建数据目录
mkdir -p data media logs telegram_sessions

# 运行容器
docker run -d \
  --name tggod \
  -p 80:80 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/media:/app/media \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/telegram_sessions:/app/telegram_sessions \
  -e TELEGRAM_API_ID=your_api_id \
  -e TELEGRAM_API_HASH=your_api_hash \
  -e TELEGRAM_BOT_TOKEN=your_bot_token \
  -e SECRET_KEY=your_secret_key \
  await2719/tggod:latest
```

### 🔧 环境变量配置

创建 `.env` 文件：

```bash
# Telegram API 配置 (必需)
# 从 https://my.telegram.org/apps 获取
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash

# Telegram Bot Token (必需)
# 从 @BotFather 获取
TELEGRAM_BOT_TOKEN=your_bot_token

# 安全配置 (必需)
# 生成随机字符串作为密钥
SECRET_KEY=your_secret_key_32_chars_long
JWT_SECRET_KEY=your_jwt_secret_32_chars_long

# 可选配置 (有默认值)
DATABASE_URL=sqlite:////app/data/tggod.db
MEDIA_ROOT=/app/media
LOG_FILE=/app/logs/app.log
```

**获取 Telegram API 凭据：**

1. 访问 https://my.telegram.org/apps
2. 登录您的 Telegram 账号
3. 创建新应用获取 `API_ID` 和 `API_HASH`
4. 联系 @BotFather 创建 Bot 获取 `BOT_TOKEN`

**生成安全密钥：**

```bash
# 生成随机密钥
openssl rand -hex 32
# 或者使用 Python
python -c "import secrets; print(secrets.token_hex(32))"
```

### 📁 数据持久化

重要数据目录说明：

| 目录 | 用途 | 重要性 |
|------|------|--------|
| `./data/` | SQLite 数据库文件 | ⭐⭐⭐ 必须备份 |
| `./media/` | 下载的媒体文件 | ⭐⭐⭐ 重要数据 |
| `./logs/` | 应用日志文件 | ⭐⭐ 调试用 |
| `./telegram_sessions/` | Telegram 会话文件 | ⭐⭐⭐ 避免重复认证 |

### 🚀 快速启动命令

```bash
# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 更新镜像
docker-compose pull && docker-compose up -d
```

### 🔍 健康检查

```bash
# 检查服务状态
curl http://localhost/health

# 查看容器状态
docker ps

# 进入容器调试
docker exec -it tggod bash
```

### 本地开发

```bash
# 后端开发
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# 前端开发
cd frontend
pnpm install
pnpm dev
```

### 🚨 故障排除

**常见问题：**

1. **端口冲突**
   ```bash
   # 检查端口占用
   netstat -tlnp | grep :80
   # 或使用 lsof
   lsof -i :80

   # 修改端口映射
   # 编辑 docker-compose.yml
   ports:
     - "8080:80"  # 改为 8080 端口访问
   ```

2. **权限问题**
   ```bash
   # 修复目录权限
   sudo chown -R $USER:$USER data media logs telegram_sessions

   # 确保目录存在
   mkdir -p data media logs telegram_sessions
   ```

3. **数据库错误**
   ```bash
   # 查看数据库状态
   docker exec -it tggod ls -la /app/data/

   # 重置数据库 (谨慎操作)
   docker-compose down
   rm -rf data/tggod.db
   docker-compose up -d
   ```

4. **Telegram 认证失败**
   ```bash
   # 检查 API 凭据是否正确
   docker logs tggod | grep -i telegram

   # 重新认证 (删除会话文件)
   rm -rf telegram_sessions/*
   docker-compose restart
   ```

5. **容器启动失败**
   ```bash
   # 查看详细日志
   docker-compose logs tggod

   # 查看容器状态
   docker ps -a

   # 进入容器调试
   docker exec -it tggod bash
   ```

## 🔄 自动化部署

项目配置了 GitHub Actions 自动化流水线：

- **自动构建**: 推送到 `master` 分支自动构建新版本
- **多架构镜像**: 支持 `linux/amd64` 和 `linux/arm64`
- **版本管理**: 自动版本号管理和 Changelog 生成
- **Docker Hub**: 自动推送到 `await2719/tggod`

**拉取最新版本：**
```bash
docker-compose pull && docker-compose up -d
```

## 📚 相关文档

- [详细部署指南](CLAUDE.md)
- [API 文档](http://localhost/docs) (启动后访问)
- [开发指南](frontend/CLAUDE.md)
- [故障排除](docs/)

## 🤝 贡献指南

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'feat: add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 打开 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

- 感谢 [Telethon](https://github.com/LonamiWebs/Telethon) 提供强大的 Telegram API
- 感谢 [FastAPI](https://github.com/tiangolo/fastapi) 提供高性能的 Web 框架
- 感谢所有贡献者的支持

## 📞 联系方式

- **Issues**: [GitHub Issues](https://github.com/Await-d/TgGod/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Await-d/TgGod/discussions)

## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=Await-d/TgGod&type=Date)](https://star-history.com/#Await-d/TgGod&Date)

<div align="center">

**如果这个项目对您有帮助，请给我们一个 ⭐ Star！**

[![GitHub Star](https://img.shields.io/github/stars/Await-d/TgGod?style=social)](https://github.com/Await-d/TgGod)

</div>