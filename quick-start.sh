#!/bin/bash

# TgGod 快速启动脚本

set -e

echo "🚀 TgGod 单服务快速启动"
echo "========================"

# 检查是否有旧服务在运行
if docker-compose ps | grep -q "Up"; then
    echo "📋 发现运行中的服务，正在停止..."
    docker-compose down
fi

# 创建必要目录
echo "📁 创建数据目录..."
mkdir -p data media logs telegram_sessions

# 检查环境变量
if [ ! -f .env ]; then
    echo "⚙️  创建环境变量文件..."
    cp .env.example .env
    echo "⚠️  请编辑 .env 文件配置Telegram API信息后重新运行"
    exit 1
fi

# 构建并启动服务
echo "🔨 构建和启动服务..."
docker-compose up -d --build

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 10

# 检查服务状态
if docker-compose ps | grep -q "Up"; then
    echo "✅ 服务启动成功！"
    echo ""
    echo "📊 服务信息："
    echo "   - 前端应用: http://localhost"
    echo "   - API文档: http://localhost/docs"
    echo "   - 健康检查: http://localhost/health"
    echo ""
    echo "📋 管理命令："
    echo "   - 查看日志: docker-compose logs -f"
    echo "   - 停止服务: docker-compose down"
    echo "   - 重启服务: docker-compose restart"
    echo ""
    echo "📂 数据文件位置："
    echo "   - 数据库: ./data/tggod.db"
    echo "   - 媒体文件: ./media/"
    echo "   - 日志文件: ./logs/"
    echo "   - Telegram会话: ./telegram_sessions/"
    
    # 显示服务状态
    echo ""
    echo "🔍 当前服务状态："
    docker-compose ps
else
    echo "❌ 服务启动失败！"
    echo ""
    echo "查看错误日志："
    docker-compose logs
fi