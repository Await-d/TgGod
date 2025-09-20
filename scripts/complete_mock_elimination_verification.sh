#!/bin/bash
#
# Complete Mock Elimination Verification Script
# 专精于生产部署和系统验证的DevOps工程师实现
#
# 实现完整的生产部署验证，进行全面的Mock消除验证和完整的系统就绪性验证
# 确保零Mock代码存在，全面的系统验证是强制性的

set -e  # Exit on any error

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
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

# 配置变量
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SERVICE_URL="${SERVICE_URL:-http://localhost}"
TIMEOUT="${TIMEOUT:-30}"
REPORT_FILE="${PROJECT_ROOT}/production_validation_report.json"

# 验证计数器
VALIDATION_COUNT=0
SUCCESS_COUNT=0
WARNING_COUNT=0
FAILED_COUNT=0

# 结果数组
declare -a VALIDATION_RESULTS=()

# 添加验证结果
add_result() {
    local component="$1"
    local status="$2"
    local message="$3"
    local details="${4:-{}}"
    
    VALIDATION_COUNT=$((VALIDATION_COUNT + 1))
    
    case "$status" in
        "success") 
            SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
            log_success "$component: $message"
            ;;
        "warning") 
            WARNING_COUNT=$((WARNING_COUNT + 1))
            log_warning "$component: $message"
            ;;
        "failed") 
            FAILED_COUNT=$((FAILED_COUNT + 1))
            log_error "$component: $message"
            ;;
    esac
    
    # 添加到结果数组
    VALIDATION_RESULTS+=("{\"component\":\"$component\",\"status\":\"$status\",\"message\":\"$message\",\"details\":$details,\"timestamp\":\"$(date -Iseconds)\"}")
}

# Mock代码消除验证
validate_mock_elimination() {
    log_info "开始Mock代码完全消除验证..."
    
    # Mock模式搜索模式 - 专门针对TgGod项目的Mock代码
    local mock_patterns=(
        "mock_task_execution_service"
        "MockTaskExecutionService"
        "USE_MOCK"
        "is_mock_mode"
        "mock_mode"
        "MOCK_MODE"
        "MockMode"
        "mock_enabled"
        "enable_mock"
    )
    
    # 排除目录和文件
    local exclude_dirs=(".git" "__pycache__" "node_modules" ".next" "dist" "build" ".spec-workflow" "deployment" "venv" "env" ".env" "logs" "data" "media" "telegram_sessions" "tests")
    local exclude_files=("production_validation_report.json" "doc_coverage_report.json" "*.log" "*.tmp")
    
    local violations_found=0
    local temp_file=$(mktemp)
    
    # 构建find排除参数
    local exclude_args=""
    for dir in "${exclude_dirs[@]}"; do
        exclude_args="$exclude_args -not -path '*/$dir/*'"
    done
    for file in "${exclude_files[@]}"; do
        exclude_args="$exclude_args -not -name '$file'"
    done
    
    # 搜索Mock代码
    for pattern in "${mock_patterns[@]}"; do
        log_info "搜索模式: $pattern"
        
        # 在源代码文件中搜索
        eval "find '$PROJECT_ROOT' -type f \\( -name '*.py' -o -name '*.js' -o -name '*.jsx' -o -name '*.ts' -o -name '*.tsx' -o -name '*.json' -o -name '*.yml' -o -name '*.yaml' \\) $exclude_args" | while read -r file; do
            if grep -l "$pattern" "$file" 2>/dev/null; then
                # 检查是否在注释中
                grep -n "$pattern" "$file" | while IFS=: read -r line_num content; do
                    # 简单检查：如果不是纯注释行
                    if [[ ! "$content" =~ ^[[:space:]]*# ]] && [[ ! "$content" =~ ^[[:space:]]*// ]]; then
                        echo "VIOLATION: $file:$line_num - $pattern" >> "$temp_file"
                        violations_found=$((violations_found + 1))
                    fi
                done
            fi
        done
    done
    
    # 检查违规结果
    if [[ -s "$temp_file" ]]; then
        local violation_details=$(cat "$temp_file" | head -20)  # 限制输出行数
        add_result "Mock代码消除验证" "failed" "发现Mock代码违规" "{\"violations\": \"$violation_details\"}"
        rm -f "$temp_file"
        return 1
    else
        add_result "Mock代码消除验证" "success" "已确认零Mock代码存在" "{}"
        rm -f "$temp_file"
        return 0
    fi
}

# Docker部署配置验证
validate_docker_deployment() {
    log_info "验证Docker部署配置..."
    
    # 检查docker-compose.yml
    if [[ ! -f "$PROJECT_ROOT/docker-compose.yml" ]]; then
        add_result "Docker配置" "failed" "docker-compose.yml文件不存在" "{}"
        return 1
    fi
    
    # 检查Dockerfile
    if [[ ! -f "$PROJECT_ROOT/Dockerfile" ]]; then
        add_result "Docker配置" "failed" "Dockerfile文件不存在" "{}"
        return 1
    fi
    
    # 检查必要的挂载目录
    local required_dirs=("data" "media" "logs" "telegram_sessions")
    local missing_dirs=()
    
    for dir in "${required_dirs[@]}"; do
        if [[ ! -d "$PROJECT_ROOT/$dir" ]]; then
            missing_dirs+=("$dir")
        fi
    done
    
    if [[ ${#missing_dirs[@]} -gt 0 ]]; then
        add_result "Docker配置" "warning" "缺少挂载目录: ${missing_dirs[*]}" "{\"missing_dirs\": [\"$(IFS='","'; echo "${missing_dirs[*]}")\"]}"
    else
        add_result "Docker配置" "success" "Docker配置验证通过" "{}"
    fi
    
    return 0
}

# 环境配置验证
validate_environment_config() {
    log_info "验证环境配置..."
    
    local required_env_vars=("TELEGRAM_API_ID" "TELEGRAM_API_HASH" "SECRET_KEY")
    local missing_vars=()
    
    # 尝试加载.env文件
    if [[ -f "$PROJECT_ROOT/.env" ]]; then
        source "$PROJECT_ROOT/.env" 2>/dev/null || true
    fi
    
    for var in "${required_env_vars[@]}"; do
        if [[ -z "${!var}" ]]; then
            missing_vars+=("$var")
        fi
    done
    
    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        add_result "环境配置" "warning" "缺少环境变量: ${missing_vars[*]}" "{\"missing_vars\": [\"$(IFS='","'; echo "${missing_vars[*]}")\"]}"
        return 1
    else
        add_result "环境配置" "success" "环境配置验证通过" "{}"
        return 0
    fi
}

# 文件权限验证
validate_file_permissions() {
    log_info "验证文件权限..."
    
    local permission_errors=()
    
    # 检查数据目录权限
    if [[ -d "$PROJECT_ROOT/data" ]]; then
        if [[ ! -w "$PROJECT_ROOT/data" ]]; then
            permission_errors+=("data目录没有写权限")
        fi
    fi
    
    # 检查媒体目录权限
    if [[ -d "$PROJECT_ROOT/media" ]]; then
        if [[ ! -w "$PROJECT_ROOT/media" ]]; then
            permission_errors+=("media目录没有写权限")
        fi
    fi
    
    # 检查日志目录权限
    if [[ -d "$PROJECT_ROOT/logs" ]]; then
        if [[ ! -w "$PROJECT_ROOT/logs" ]]; then
            permission_errors+=("logs目录没有写权限")
        fi
    fi
    
    if [[ ${#permission_errors[@]} -gt 0 ]]; then
        add_result "文件权限" "failed" "文件权限错误: ${permission_errors[*]}" "{\"errors\": [\"$(IFS='","'; echo "${permission_errors[*]}")\"]}"
        return 1
    else
        add_result "文件权限" "success" "文件权限验证通过" "{}"
        return 0
    fi
}

# 系统依赖验证
validate_system_dependencies() {
    log_info "验证系统依赖..."
    
    local required_commands=("curl" "python3")
    local missing_commands=()
    
    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            missing_commands+=("$cmd")
        fi
    done
    
    if [[ ${#missing_commands[@]} -gt 0 ]]; then
        add_result "系统依赖" "failed" "缺少系统依赖: ${missing_commands[*]}" "{\"missing_commands\": [\"$(IFS='","'; echo "${missing_commands[*]}")\"]}"
        return 1
    else
        add_result "系统依赖" "success" "系统依赖验证通过" "{}"
        return 0
    fi
}

# 数据库完整性验证
validate_database_integrity() {
    log_info "验证数据库完整性..."
    
    local db_path="$PROJECT_ROOT/data/tggod.db"
    
    if [[ ! -f "$db_path" ]]; then
        add_result "数据库完整性" "warning" "数据库文件不存在，将在首次运行时创建" "{}"
        return 0
    fi
    
    # 检查数据库是否可访问
    if command -v sqlite3 &> /dev/null; then
        if sqlite3 "$db_path" "SELECT name FROM sqlite_master WHERE type='table';" &> /dev/null; then
            add_result "数据库完整性" "success" "数据库文件可访问" "{}"
            return 0
        else
            add_result "数据库完整性" "failed" "数据库文件损坏或不可访问" "{}"
            return 1
        fi
    else
        add_result "数据库完整性" "warning" "无法验证数据库完整性（sqlite3命令不可用）" "{}"
        return 0
    fi
}

# 服务健康验证
validate_service_health() {
    log_info "验证服务健康状态..."
    
    # 基础健康检查
    if curl -f -s --max-time "$TIMEOUT" "$SERVICE_URL/health" > /dev/null; then
        add_result "服务健康检查" "success" "基础健康检查通过" "{}"
    else
        add_result "服务健康检查" "failed" "基础健康检查失败" "{}"
        return 1
    fi
    
    # 详细服务健康检查
    if curl -f -s --max-time "$TIMEOUT" "$SERVICE_URL/api/health/services" > /dev/null; then
        add_result "详细服务健康" "success" "详细服务健康检查通过" "{}"
    else
        add_result "详细服务健康" "warning" "详细服务健康检查失败" "{}"
    fi
    
    return 0
}

# API端点验证
validate_api_endpoints() {
    log_info "验证API端点可用性..."
    
    local critical_endpoints=(
        "/api/telegram/groups"
        "/api/rule/rules"
        "/api/task/tasks"
        "/api/dashboard/stats"
        "/api/database/check"
    )
    
    local failed_endpoints=()
    
    for endpoint in "${critical_endpoints[@]}"; do
        if ! curl -f -s --max-time "$TIMEOUT" "$SERVICE_URL$endpoint" > /dev/null; then
            failed_endpoints+=("$endpoint")
        fi
    done
    
    if [[ ${#failed_endpoints[@]} -gt 0 ]]; then
        add_result "API端点验证" "warning" "部分API端点不可访问: ${failed_endpoints[*]}" "{\"failed_endpoints\": [\"$(IFS='","'; echo "${failed_endpoints[*]}")\"]}"
    else
        add_result "API端点验证" "success" "所有关键API端点可访问" "{}"
    fi
    
    return 0
}

# 生成验证报告
generate_report() {
    log_info "生成验证报告..."
    
    local overall_status="success"
    if [[ $FAILED_COUNT -gt 0 ]]; then
        overall_status="failed"
    elif [[ $WARNING_COUNT -gt 0 ]]; then
        overall_status="warning"
    fi
    
    local production_ready="false"
    local mock_eliminated="false"
    
    if [[ "$overall_status" == "success" ]]; then
        production_ready="true"
    fi
    
    # 检查是否所有Mock验证都通过
    mock_eliminated="true"
    for result in "${VALIDATION_RESULTS[@]}"; do
        if echo "$result" | grep -q "Mock.*failed"; then
            mock_eliminated="false"
            break
        fi
    done
    
    # 生成JSON报告
    cat > "$REPORT_FILE" << EOF
{
  "overall_status": "$overall_status",
  "summary": {
    "total_validations": $VALIDATION_COUNT,
    "success_count": $SUCCESS_COUNT,
    "warning_count": $WARNING_COUNT,
    "failed_count": $FAILED_COUNT,
    "duration_seconds": $(date +%s)
  },
  "validations": [
    $(IFS=','; echo "${VALIDATION_RESULTS[*]}")
  ],
  "production_ready": $production_ready,
  "mock_eliminated": $mock_eliminated,
  "timestamp": "$(date -Iseconds)"
}
EOF

    log_success "验证报告已生成: $REPORT_FILE"
}

# 创建必要目录
create_required_directories() {
    log_info "创建必要的目录..."
    
    local required_dirs=("data" "media" "logs" "telegram_sessions")
    
    for dir in "${required_dirs[@]}"; do
        local dir_path="$PROJECT_ROOT/$dir"
        if [[ ! -d "$dir_path" ]]; then
            mkdir -p "$dir_path"
            log_info "创建目录: $dir_path"
        fi
    done
}

# 主验证流程
main() {
    log_info "=== TgGod 完整生产部署验证开始 ==="
    log_info "项目根目录: $PROJECT_ROOT"
    log_info "服务URL: $SERVICE_URL"
    log_info "超时时间: $TIMEOUT 秒"
    
    # 创建必要目录
    create_required_directories
    
    # 执行所有验证
    local validations=(
        "validate_mock_elimination"
        "validate_docker_deployment"
        "validate_environment_config"
        "validate_file_permissions"
        "validate_system_dependencies"
        "validate_database_integrity"
        "validate_service_health"
        "validate_api_endpoints"
    )
    
    for validation in "${validations[@]}"; do
        $validation || true  # 继续执行其他验证，即使某个验证失败
    done
    
    # 生成报告
    generate_report
    
    # 输出摘要
    echo
    log_info "=== 验证摘要 ==="
    log_info "总验证数: $VALIDATION_COUNT"
    log_success "成功: $SUCCESS_COUNT"
    log_warning "警告: $WARNING_COUNT"
    log_error "失败: $FAILED_COUNT"
    
    echo
    if [[ $FAILED_COUNT -eq 0 ]]; then
        log_success "=== 生产部署验证完成 - 总体状态: 通过 ==="
        if [[ -f "$REPORT_FILE" ]] && grep -q '"mock_eliminated": true' "$REPORT_FILE"; then
            log_success "✅ Mock代码已完全消除"
        fi
        if [[ -f "$REPORT_FILE" ]] && grep -q '"production_ready": true' "$REPORT_FILE"; then
            log_success "✅ 系统已准备好生产部署"
        fi
        exit 0
    else
        log_error "=== 生产部署验证完成 - 总体状态: 失败 ==="
        log_error "请检查失败项目并修复后重新验证"
        exit 1
    fi
}

# 脚本入口点
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi