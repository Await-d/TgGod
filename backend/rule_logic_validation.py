#!/usr/bin/env python3
"""
规则逻辑验证脚本
检查规则执行逻辑的完整性和一致性
"""

import ast
import os
from pathlib import Path

def check_filter_logic_consistency():
    """检查过滤逻辑一致性"""
    print("🔍 检查规则过滤逻辑一致性...")
    
    # 读取规则 API 中的过滤逻辑
    rule_api_path = Path("app/api/rule.py")
    task_service_path = Path("app/services/task_execution_service.py")
    
    if not rule_api_path.exists() or not task_service_path.exists():
        print("❌ 找不到必要的文件")
        return False
    
    with open(rule_api_path, 'r', encoding='utf-8') as f:
        rule_api_content = f.read()
    
    with open(task_service_path, 'r', encoding='utf-8') as f:
        task_service_content = f.read()
    
    # 检查关键过滤条件
    filter_conditions = [
        "rule.keywords",
        "rule.exclude_keywords", 
        "rule.media_types",
        "rule.sender_filter",
        "rule.min_views",
        "rule.max_views",
        "rule.min_file_size",
        "rule.max_file_size",
        "rule.include_forwarded",
        "media_type != 'text'",
        "media_type.isnot(None)"
    ]
    
    missing_in_api = []
    missing_in_service = []
    
    for condition in filter_conditions:
        if condition not in rule_api_content:
            missing_in_api.append(condition)
        if condition not in task_service_content:
            missing_in_service.append(condition)
    
    if missing_in_api:
        print(f"❌ 规则 API 中缺少过滤条件: {missing_in_api}")
        return False
        
    if missing_in_service:
        print(f"❌ 任务服务中缺少过滤条件: {missing_in_service}")
        return False
    
    print("✅ 过滤逻辑一致性检查通过")
    return True

def check_api_endpoints():
    """检查 API 端点完整性"""
    print("🔍 检查 API 端点完整性...")
    
    rule_api_path = Path("app/api/rule.py")
    
    if not rule_api_path.exists():
        print("❌ 规则 API 文件不存在")
        return False
    
    with open(rule_api_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查必要的端点
    required_endpoints = [
        '@router.get("/rules"',
        '@router.post("/rules"', 
        '@router.get("/rules/{rule_id}"',
        '@router.put("/rules/{rule_id}"',
        '@router.delete("/rules/{rule_id}"',
        '@router.post("/rules/{rule_id}/test"',
        '@router.post("/rules/{rule_id}/validate"',
        '@router.get("/rules/stats"'
    ]
    
    missing_endpoints = []
    for endpoint in required_endpoints:
        if endpoint not in content:
            missing_endpoints.append(endpoint)
    
    if missing_endpoints:
        print(f"❌ 缺少 API 端点: {missing_endpoints}")
        return False
    
    print("✅ API 端点完整性检查通过")
    return True

def check_response_models():
    """检查响应模型完整性"""
    print("🔍 检查响应模型完整性...")
    
    rule_api_path = Path("app/api/rule.py")
    
    if not rule_api_path.exists():
        print("❌ 规则 API 文件不存在")
        return False
    
    with open(rule_api_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查必要的模型
    required_models = [
        "class RuleCreate",
        "class RuleUpdate", 
        "class RuleResponse",
        "class RuleTestResponse",
        "class RuleValidationResponse"
    ]
    
    missing_models = []
    for model in required_models:
        if model not in content:
            missing_models.append(model)
    
    if missing_models:
        print(f"❌ 缺少响应模型: {missing_models}")
        return False
    
    print("✅ 响应模型完整性检查通过")
    return True

def check_task_date_range_logic():
    """检查任务日期范围逻辑"""
    print("🔍 检查任务日期范围逻辑...")
    
    task_service_path = Path("app/services/task_execution_service.py")
    
    if not task_service_path.exists():
        print("❌ 任务服务文件不存在")
        return False
    
    with open(task_service_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查是否处理任务的日期范围
    if "task.date_from" not in content or "task.date_to" not in content:
        print("❌ 任务服务未处理任务的日期范围")
        return False
    
    # 检查是否优先使用任务日期范围
    if "task.date_from if task.date_from else rule.date_from" not in content:
        print("❌ 未正确处理任务和规则日期范围的优先级")
        return False
    
    print("✅ 任务日期范围逻辑检查通过")
    return True

def check_jellyfin_integration():
    """检查 Jellyfin 集成逻辑"""
    print("🔍 检查 Jellyfin 集成逻辑...")
    
    task_service_path = Path("app/services/task_execution_service.py")
    jellyfin_service_path = Path("app/services/jellyfin_media_service.py")
    
    if not task_service_path.exists():
        print("❌ 任务服务文件不存在")
        return False
        
    if not jellyfin_service_path.exists():
        print("❌ Jellyfin 服务文件不存在")
        return False
    
    with open(task_service_path, 'r', encoding='utf-8') as f:
        task_content = f.read()
    
    # 检查 Jellyfin 集成
    jellyfin_checks = [
        "use_jellyfin_structure",
        "jellyfin_service",
        "JellyfinMediaService",
        "download_media_with_jellyfin_structure"
    ]
    
    missing_checks = []
    for check in jellyfin_checks:
        if check not in task_content:
            missing_checks.append(check)
    
    if missing_checks:
        print(f"❌ Jellyfin 集成缺少组件: {missing_checks}")
        return False
    
    print("✅ Jellyfin 集成逻辑检查通过")
    return True

def check_error_handling():
    """检查错误处理"""
    print("🔍 检查错误处理...")
    
    files_to_check = [
        "app/api/rule.py",
        "app/api/task.py", 
        "app/services/task_execution_service.py"
    ]
    
    for file_path in files_to_check:
        if not Path(file_path).exists():
            print(f"❌ 文件不存在: {file_path}")
            return False
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否有 try-except 块
        if "try:" not in content or "except" not in content:
            print(f"❌ {file_path} 缺少错误处理")
            return False
        
        # 检查是否有日志记录
        if "logger.error" not in content:
            print(f"❌ {file_path} 缺少错误日志")
            return False
    
    print("✅ 错误处理检查通过")
    return True

def main():
    """主函数"""
    print("开始规则逻辑验证...")
    print("=" * 60)
    
    checks = [
        ("过滤逻辑一致性", check_filter_logic_consistency),
        ("API 端点完整性", check_api_endpoints),
        ("响应模型完整性", check_response_models),
        ("任务日期范围逻辑", check_task_date_range_logic),
        ("Jellyfin 集成逻辑", check_jellyfin_integration),
        ("错误处理", check_error_handling),
    ]
    
    passed = 0
    total = len(checks)
    
    for check_name, check_func in checks:
        print(f"\n{check_name}:")
        print("-" * 40)
        
        try:
            if check_func():
                passed += 1
            else:
                print(f"❌ {check_name} 检查失败")
        except Exception as e:
            print(f"❌ {check_name} 检查异常: {e}")
    
    print("\n" + "=" * 60)
    print(f"验证完成! 通过: {passed}/{total}")
    
    if passed == total:
        print("🎉 所有检查通过! 规则执行逻辑正常")
        return True
    else:
        print(f"⚠️ {total - passed} 个检查失败")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)