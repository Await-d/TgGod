#!/bin/bash

# 测试构建和部署脚本

echo "=== TgGod 单服务部署测试 ==="

# 1. 检查必要的目录
echo "1. 创建必要的目录..."
mkdir -p data media logs telegram_sessions

# 2. 检查环境变量文件
echo "2. 检查环境变量配置..."
if [ ! -f .env ]; then
    echo "   .env 文件不存在，复制示例文件..."
    cp .env.example .env
    echo "   ⚠️  请编辑 .env 文件配置Telegram API信息"
fi

# 3. 验证Docker配置
echo "3. 验证Docker配置..."
if docker-compose config > /dev/null 2>&1; then
    echo "   ✅ Docker配置验证成功"
else
    echo "   ❌ Docker配置验证失败"
    exit 1
fi

# 4. 检查端口占用
echo "4. 检查端口占用..."
if lsof -i :80 > /dev/null 2>&1; then
    echo "   ⚠️  端口80已被占用，请停止相关服务"
else
    echo "   ✅ 端口80可用"
fi

# 5. 构建镜像（仅验证，不实际构建）
echo "5. 准备构建配置..."
echo "   📋 构建配置:"
echo "   - 前端: React + Nginx"
echo "   - 后端: FastAPI"
echo "   - 数据库: SQLite (外部挂载)"
echo "   - 端口: 80"

echo ""
echo "=== 部署准备完成 ==="
echo ""
echo "下一步操作："
echo "1. 编辑 .env 文件配置 Telegram API 信息"
echo "2. 运行: docker-compose up -d"
echo "3. 访问: http://localhost"
echo ""
echo "管理命令："
echo "- 查看日志: docker-compose logs -f"
echo "- 停止服务: docker-compose down"
echo "- 重启服务: docker-compose restart"
echo ""