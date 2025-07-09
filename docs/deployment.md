# TgGod 部署指南

## 快速开始

### 1. 环境准备

确保您的系统已安装：
- Docker & Docker Compose
- Node.js 18+ (如果本地开发)
- Python 3.11+ (如果本地开发)

### 2. 获取Telegram API密钥

1. 访问 https://my.telegram.org/auth
2. 使用您的手机号码登录
3. 创建一个新的应用程序
4. 获取 `API ID` 和 `API Hash`

### 3. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑环境变量
nano .env
```

在 `.env` 文件中配置：
- `TELEGRAM_API_ID`: 您的Telegram API ID
- `TELEGRAM_API_HASH`: 您的Telegram API Hash
- `SECRET_KEY`: 生成一个强密码用于JWT认证

### 4. 使用Docker部署

```bash
# 构建并启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

### 5. 访问应用

- 前端界面: http://localhost
- 后端API: http://localhost:8000
- API文档: http://localhost:8000/docs

## 本地开发

### 后端开发

```bash
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 运行数据库迁移
alembic upgrade head

# 启动开发服务器
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 前端开发

```bash
cd frontend

# 安装依赖
pnpm install

# 启动开发服务器
pnpm dev
```

## 数据库迁移

```bash
cd backend

# 创建新的迁移文件
alembic revision --autogenerate -m "描述你的变更"

# 应用迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1
```

## 目录结构

```
TgGod/
├── backend/                 # Python后端
│   ├── app/
│   │   ├── api/            # API路由
│   │   ├── models/         # 数据模型
│   │   ├── services/       # 业务逻辑
│   │   ├── websocket/      # WebSocket处理
│   │   └── ...
│   ├── alembic/            # 数据库迁移
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/               # React前端
│   ├── src/
│   │   ├── components/     # 组件
│   │   ├── pages/         # 页面
│   │   ├── services/      # API服务
│   │   ├── store/         # 状态管理
│   │   └── ...
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml      # Docker编排
└── README.md
```

## 功能特性

### 群组管理
- 添加Telegram群组
- 同步群组消息
- 查看群组统计信息

### 规则配置
- 关键词过滤
- 媒体类型筛选
- 时间范围限制
- 发送者过滤

### 下载任务
- 创建下载任务
- 实时进度监控
- 任务状态控制

### 日志系统
- 实时日志推送
- 日志级别过滤
- 任务和系统日志分类

## 故障排除

### 常见问题

1. **Telegram API连接失败**
   - 检查API ID和Hash是否正确
   - 确保网络连接正常
   - 检查防火墙设置

2. **数据库连接错误**
   - 检查数据库文件路径
   - 确保有写入权限
   - 运行数据库迁移

3. **WebSocket连接失败**
   - 检查端口是否被占用
   - 确保前后端端口配置正确

### 查看日志

```bash
# 查看所有服务日志
docker-compose logs

# 查看特定服务日志
docker-compose logs backend
docker-compose logs frontend

# 实时查看日志
docker-compose logs -f
```

## 安全建议

1. **环境变量安全**
   - 使用强密码作为SECRET_KEY
   - 不要在代码中硬编码敏感信息
   - 定期更换API密钥

2. **网络安全**
   - 使用HTTPS (生产环境)
   - 配置防火墙规则
   - 限制API访问来源

3. **数据备份**
   - 定期备份数据库
   - 备份下载的媒体文件
   - 制定灾难恢复计划

## 贡献指南

1. Fork项目
2. 创建功能分支
3. 提交变更
4. 创建Pull Request

## 许可证

本项目采用MIT许可证 - 详见LICENSE文件