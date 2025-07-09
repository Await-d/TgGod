# TgGod开发和部署指南

## 开发环境搭建
### 后端开发
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 前端开发
```bash
cd frontend
pnpm install
pnpm dev
```

## 配置要求
- Telegram API ID和API Hash
- 环境变量配置(.env文件)
- SQLite数据库自动创建

## Docker部署
```bash
# 一键部署
docker-compose up -d

# 服务访问
# 前端: http://localhost
# 后端: http://localhost:8000
```

## 数据库迁移
- 使用Alembic管理数据库版本
- 自动创建表结构
- 支持SQLite异步操作

## 测试和验证
- 健康检查: `/health`
- API文档: `/docs`
- WebSocket测试: `/ws/test`

## 生产部署注意事项
- 配置HTTPS和域名
- 设置防火墙规则
- 监控日志文件大小
- 定期备份SQLite数据库