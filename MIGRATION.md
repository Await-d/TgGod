# 迁移指南：从三服务架构到单服务架构

## 概述

TgGod 已从三个独立服务合并为单一服务架构，以简化部署和管理。

## 架构对比

### 旧架构（三服务）
```
services:
  backend:     # FastAPI后端 (端口8000)
  frontend:    # React + Nginx (端口80)  
  database:    # 数据挂载容器
```

### 新架构（单服务）
```
services:
  tggod:       # 前端 + 后端 + 数据库 (端口80)
```

## 迁移步骤

### 1. 备份现有数据

```bash
# 停止旧服务
docker-compose down

# 备份数据
mkdir -p backup/$(date +%Y%m%d)
cp -r data/ backup/$(date +%Y%m%d)/
cp -r media/ backup/$(date +%Y%m%d)/
cp -r logs/ backup/$(date +%Y%m%d)/
```

### 2. 更新项目代码

```bash
# 拉取最新代码
git pull origin master

# 或重新克隆项目
git clone <repository-url> TgGod-new
cd TgGod-new
```

### 3. 迁移配置文件

```bash
# 复制旧的环境变量配置
cp ../TgGod-old/.env .env

# 或重新配置
cp .env.example .env
# 编辑 .env 文件
```

### 4. 迁移数据文件

```bash
# 复制数据库文件
cp -r ../TgGod-old/data/ ./

# 复制媒体文件
cp -r ../TgGod-old/media/ ./

# 复制Telegram会话文件（如果存在）
if [ -d "../TgGod-old/backend" ]; then
    mkdir -p telegram_sessions/
    find ../TgGod-old/backend -name "*.session*" -exec cp {} telegram_sessions/ \;
fi
```

### 5. 启动新服务

```bash
# 使用快速启动脚本
./quick-start.sh

# 或手动启动
docker-compose up -d
```

### 6. 验证迁移

```bash
# 检查服务状态
docker-compose ps

# 检查健康状态
curl http://localhost/health

# 检查数据
ls -la data/ media/ logs/ telegram_sessions/
```

## 配置变更

### 端口变更
- **旧**: 前端端口80，后端端口8000
- **新**: 统一端口80

### URL变更
- **前端**: `http://localhost` (无变化)
- **API**: `http://localhost/api/` (无变化)
- **文档**: `http://localhost/docs` (新)

### 环境变量
环境变量配置保持不变，无需修改 `.env` 文件。

## 故障排除

### 1. 服务启动失败

**检查端口冲突**:
```bash
lsof -i :80
# 如果端口被占用，停止相关服务
```

**检查日志**:
```bash
docker-compose logs
```

### 2. 数据访问问题

**检查文件权限**:
```bash
ls -la data/ media/ logs/
# 确保Docker有读写权限
```

**检查数据库文件**:
```bash
ls -la data/tggod.db
# 确保数据库文件存在
```

### 3. Telegram认证问题

**清除旧会话**:
```bash
rm -f telegram_sessions/*
# 重新进行Telegram认证
```

## 回滚方案

如果迁移失败，可以回滚到旧架构：

```bash
# 停止新服务
docker-compose down

# 切换到旧项目目录
cd ../TgGod-old

# 恢复数据（如果有修改）
cp -r ../TgGod-new/data/ ./
cp -r ../TgGod-new/media/ ./

# 启动旧服务
docker-compose up -d
```

## 性能对比

### 资源使用
- **旧架构**: 3个容器，~500MB内存
- **新架构**: 1个容器，~300MB内存

### 启动时间
- **旧架构**: ~30-60秒
- **新架构**: ~20-40秒

### 管理复杂度
- **旧架构**: 需要管理3个服务
- **新架构**: 只需管理1个服务

## 优势总结

1. **简化部署**: 一个命令启动所有服务
2. **资源优化**: 减少容器开销
3. **配置集中**: 统一配置管理
4. **维护便利**: 减少服务间依赖问题
5. **网络简化**: 无需配置服务间网络

## 注意事项

1. **数据备份**: 迁移前一定要备份数据
2. **端口检查**: 确保80端口未被占用
3. **权限问题**: 确保Docker有足够权限访问挂载目录
4. **配置验证**: 迁移后验证所有功能正常
5. **日志监控**: 观察服务启动和运行日志