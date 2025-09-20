#!/bin/bash
#
# Production Deployment Start Script
# TgGod Single Service Architecture
#

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 等待数据库初始化
wait_for_database() {
    log_info "等待数据库初始化..."
    
    # 确保数据目录存在
    mkdir -p /app/data
    
    # 如果数据库不存在，等待应用创建
    if [[ ! -f "/app/data/tggod.db" ]]; then
        log_info "数据库文件不存在，将在应用启动时创建"
    fi
}

# 启动Nginx
start_nginx() {
    log_info "启动Nginx服务..."
    
    # 测试Nginx配置
    nginx -t
    
    # 启动Nginx
    nginx -g "daemon on;"
    
    log_success "Nginx已启动"
}

# 启动后端应用
start_backend() {
    log_info "启动TgGod后端应用..."
    
    # 设置Python路径
    export PYTHONPATH="/app:$PYTHONPATH"
    
    # 启动FastAPI应用
    cd /app
    
    # 使用uvicorn启动应用
    exec uvicorn app.main:app \
        --host 0.0.0.0 \
        --port 8000 \
        --workers 1 \
        --log-level info \
        --access-log \
        --use-colors
}

# 主启动流程
main() {
    log_info "=== TgGod 生产部署启动 ==="
    
    # 创建必要目录
    mkdir -p /app/data /app/media /app/logs /app/telegram_sessions
    
    # 设置权限
    chmod 755 /app/data /app/media /app/logs /app/telegram_sessions
    
    # 等待数据库
    wait_for_database
    
    # 启动Nginx
    start_nginx
    
    # 启动后端应用（这会阻塞）
    start_backend
}

# 错误处理
trap 'log_error "启动脚本异常退出"; exit 1' ERR

# 脚本入口
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi