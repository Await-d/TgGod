#!/bin/bash

# 设置错误处理
set -e

# 创建必要的目录
mkdir -p /app/data /app/media /app/logs /app/telegram_sessions

# 等待一下确保目录创建完成
sleep 2

# 启动nginx
echo "Starting Nginx..."
nginx -t  # 测试nginx配置
nginx &

# 等待nginx启动
sleep 3

# 启动后端服务
echo "Starting FastAPI backend..."
cd /app
exec uvicorn app.main:app --host 0.0.0.0 --port 8001