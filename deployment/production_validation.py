#!/usr/bin/env python3
"""
Complete Production Deployment Validation System
专精于生产部署和系统验证的DevOps工程师实现

实现完整的生产部署验证，进行全面的Mock消除验证和完整的系统就绪性验证
确保零Mock代码存在，全面的系统验证是强制性的
"""

import os
import sys
import json
import time
import logging
import subprocess
import requests
import sqlite3
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    """验证结果数据类"""
    component: str
    status: str  # 'success', 'warning', 'failed'
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None

class ProductionValidator:
    """完整生产部署验证器"""
    
    def __init__(self, base_url: str = "http://localhost", timeout: int = 30):
        self.base_url = base_url
        self.timeout = timeout
        self.results: List[ValidationResult] = []
        self.project_root = Path(__file__).parent.parent
        
    def add_result(self, component: str, status: str, message: str, details: Dict[str, Any] = None):
        """添加验证结果"""
        result = ValidationResult(
            component=component,
            status=status,
            message=message,
            details=details or {},
            timestamp=datetime.now()
        )
        self.results.append(result)
        logger.info(f"[{status.upper()}] {component}: {message}")
        
    def validate_mock_elimination(self) -> bool:
        """验证Mock代码完全消除"""
        logger.info("开始Mock代码消除验证...")
        
        mock_patterns = [
            'mock_task_execution_service',
            'MockTaskExecutionService',
            'USE_MOCK',
            'is_mock_mode',
            'mock_mode',
            'MOCK_MODE',
            'MockMode',
            'mock_enabled',
            'enable_mock'
        ]
        
        excluded_dirs = {'.git', '__pycache__', 'node_modules', '.next', 'dist', 'build', '.spec-workflow', 'deployment', 'venv', 'env', '.env', 'logs', 'data', 'media', 'telegram_sessions', 'tests'}
        mock_violations = []
        
        # 扫描所有源代码文件
        for root, dirs, files in os.walk(self.project_root):
            # 过滤排除目录
            dirs[:] = [d for d in dirs if d not in excluded_dirs]
            
            for file in files:
                # 排除特定文件
                if file in ['production_validation_report.json', 'complete_production_validation.json', 'doc_coverage_report.json'] or file.endswith(('.log', '.tmp')):
                    continue
                    
                if file.endswith(('.py', '.js', '.jsx', '.ts', '.tsx', '.json', '.yml', '.yaml')):
                    file_path = Path(root) / file
                    try:
                        content = file_path.read_text(encoding='utf-8')
                        for pattern in mock_patterns:
                            if pattern in content:
                                # 检查是否在注释或字符串中
                                lines = content.split('\n')
                                for i, line in enumerate(lines, 1):
                                    if pattern in line:
                                        # 简单检查：如果不是纯注释行
                                        stripped = line.strip()
                                        if not (stripped.startswith('#') or stripped.startswith('//')):
                                            mock_violations.append({
                                                'file': str(file_path.relative_to(self.project_root)),
                                                'line': i,
                                                'pattern': pattern,
                                                'content': line.strip()
                                            })
                    except (UnicodeDecodeError, PermissionError):
                        continue
        
        if mock_violations:
            self.add_result(
                "Mock消除验证",
                "failed",
                f"发现 {len(mock_violations)} 个Mock代码违规",
                {"violations": mock_violations}
            )
            return False
        else:
            self.add_result(
                "Mock消除验证",
                "success",
                "已确认零Mock代码存在"
            )
            return True
    
    def validate_docker_deployment(self) -> bool:
        """验证Docker部署配置"""
        logger.info("验证Docker部署配置...")
        
        try:
            # 检查Docker Compose文件
            compose_file = self.project_root / "docker-compose.yml"
            if not compose_file.exists():
                self.add_result("Docker配置", "failed", "docker-compose.yml文件不存在")
                return False
            
            # 检查Dockerfile
            dockerfile = self.project_root / "Dockerfile"
            if not dockerfile.exists():
                self.add_result("Docker配置", "failed", "Dockerfile文件不存在")
                return False
            
            # 检查必要的挂载目录
            required_dirs = ['data', 'media', 'logs', 'telegram_sessions']
            missing_dirs = []
            for dir_name in required_dirs:
                dir_path = self.project_root / dir_name
                if not dir_path.exists():
                    missing_dirs.append(dir_name)
            
            if missing_dirs:
                self.add_result(
                    "Docker配置",
                    "warning",
                    f"缺少挂载目录: {', '.join(missing_dirs)}"
                )
            
            self.add_result("Docker配置", "success", "Docker配置验证通过")
            return True
            
        except Exception as e:
            self.add_result("Docker配置", "failed", f"Docker配置验证失败: {str(e)}")
            return False
    
    def validate_service_health(self) -> bool:
        """验证服务健康状态"""
        logger.info("验证服务健康状态...")
        
        try:
            # 基础健康检查
            response = requests.get(f"{self.base_url}/health", timeout=self.timeout)
            if response.status_code == 200:
                health_data = response.json()
                self.add_result(
                    "基础健康检查",
                    "success",
                    "服务基础健康检查通过",
                    health_data
                )
            else:
                self.add_result(
                    "基础健康检查",
                    "failed",
                    f"健康检查失败，状态码: {response.status_code}"
                )
                return False
                
        except requests.RequestException as e:
            self.add_result(
                "基础健康检查",
                "failed",
                f"无法连接到服务: {str(e)}"
            )
            return False
        
        try:
            # 详细服务健康检查
            response = requests.get(f"{self.base_url}/api/health/services", timeout=self.timeout)
            if response.status_code == 200:
                services_data = response.json()
                self.add_result(
                    "服务健康检查",
                    "success",
                    "详细服务健康检查通过",
                    services_data
                )
            else:
                self.add_result(
                    "服务健康检查",
                    "warning",
                    f"服务健康API返回状态码: {response.status_code}"
                )
                
        except requests.RequestException as e:
            self.add_result(
                "服务健康检查",
                "warning",
                f"服务健康API连接失败: {str(e)}"
            )
        
        return True
    
    def validate_database_integrity(self) -> bool:
        """验证数据库完整性"""
        logger.info("验证数据库完整性...")
        
        try:
            # 检查数据库文件
            db_path = self.project_root / "data" / "tggod.db"
            if not db_path.exists():
                self.add_result(
                    "数据库完整性",
                    "warning",
                    "数据库文件不存在，将在首次运行时创建"
                )
                return True
            
            # 连接数据库并检查表结构
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            # 检查关键表是否存在
            required_tables = [
                'telegram_groups',
                'telegram_messages', 
                'filter_rules',
                'download_tasks',
                'user_settings'
            ]
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = [row[0] for row in cursor.fetchall()]
            
            missing_tables = [t for t in required_tables if t not in existing_tables]
            
            if missing_tables:
                self.add_result(
                    "数据库完整性",
                    "warning",
                    f"缺少数据库表: {', '.join(missing_tables)}"
                )
            else:
                self.add_result(
                    "数据库完整性",
                    "success",
                    "数据库结构验证通过"
                )
            
            conn.close()
            return True
            
        except Exception as e:
            self.add_result(
                "数据库完整性",
                "failed",
                f"数据库验证失败: {str(e)}"
            )
            return False
    
    def validate_api_endpoints(self) -> bool:
        """验证API端点可用性"""
        logger.info("验证API端点可用性...")
        
        critical_endpoints = [
            "/api/telegram/groups",
            "/api/rule/rules",
            "/api/task/tasks",
            "/api/dashboard/stats",
            "/api/database/check"
        ]
        
        endpoint_results = {}
        all_passed = True
        
        for endpoint in critical_endpoints:
            try:
                response = requests.get(f"{self.base_url}{endpoint}", timeout=self.timeout)
                endpoint_results[endpoint] = {
                    "status_code": response.status_code,
                    "accessible": response.status_code < 500
                }
                if response.status_code >= 500:
                    all_passed = False
            except requests.RequestException as e:
                endpoint_results[endpoint] = {
                    "status_code": 0,
                    "accessible": False,
                    "error": str(e)
                }
                all_passed = False
        
        status = "success" if all_passed else "warning"
        message = "所有关键API端点可访问" if all_passed else "部分API端点不可访问"
        
        self.add_result(
            "API端点验证",
            status,
            message,
            endpoint_results
        )
        
        return all_passed
    
    def validate_environment_config(self) -> bool:
        """验证环境配置"""
        logger.info("验证环境配置...")
        
        required_env_vars = [
            'TELEGRAM_API_ID',
            'TELEGRAM_API_HASH', 
            'SECRET_KEY'
        ]
        
        missing_vars = []
        for var in required_env_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            self.add_result(
                "环境配置",
                "warning",
                f"缺少环境变量: {', '.join(missing_vars)}"
            )
        else:
            self.add_result(
                "环境配置",
                "success",
                "环境配置验证通过"
            )
        
        return len(missing_vars) == 0
    
    def validate_file_permissions(self) -> bool:
        """验证文件权限"""
        logger.info("验证文件权限...")
        
        try:
            # 检查数据目录权限
            data_dir = self.project_root / "data"
            if data_dir.exists():
                if not os.access(data_dir, os.W_OK):
                    self.add_result(
                        "文件权限",
                        "failed",
                        "数据目录没有写权限"
                    )
                    return False
            
            # 检查媒体目录权限
            media_dir = self.project_root / "media"
            if media_dir.exists():
                if not os.access(media_dir, os.W_OK):
                    self.add_result(
                        "文件权限",
                        "failed",
                        "媒体目录没有写权限"
                    )
                    return False
            
            self.add_result(
                "文件权限",
                "success",
                "文件权限验证通过"
            )
            return True
            
        except Exception as e:
            self.add_result(
                "文件权限",
                "failed",
                f"文件权限验证失败: {str(e)}"
            )
            return False
    
    def validate_system_dependencies(self) -> bool:
        """验证系统依赖"""
        logger.info("验证系统依赖...")
        
        required_commands = [
            'ffmpeg',
            'curl',
            'python3'
        ]
        
        missing_commands = []
        for cmd in required_commands:
            try:
                subprocess.run([cmd, '--version'], 
                             capture_output=True, 
                             check=True, 
                             timeout=10)
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                missing_commands.append(cmd)
        
        if missing_commands:
            self.add_result(
                "系统依赖",
                "failed",
                f"缺少系统依赖: {', '.join(missing_commands)}"
            )
            return False
        else:
            self.add_result(
                "系统依赖",
                "success",
                "系统依赖验证通过"
            )
            return True
    
    def run_complete_validation(self) -> Dict[str, Any]:
        """运行完整的生产验证"""
        logger.info("开始完整生产部署验证...")
        start_time = datetime.now()
        
        # 执行所有验证
        validations = [
            ("Mock代码消除验证", self.validate_mock_elimination),
            ("Docker部署配置", self.validate_docker_deployment),
            ("环境配置验证", self.validate_environment_config),
            ("文件权限验证", self.validate_file_permissions),
            ("系统依赖验证", self.validate_system_dependencies),
            ("数据库完整性验证", self.validate_database_integrity),
            ("服务健康验证", self.validate_service_health),
            ("API端点验证", self.validate_api_endpoints)
        ]
        
        failed_count = 0
        warning_count = 0
        success_count = 0
        
        for name, validation_func in validations:
            try:
                result = validation_func()
                if not result:
                    failed_count += 1
            except Exception as e:
                self.add_result(name, "failed", f"验证过程异常: {str(e)}")
                failed_count += 1
        
        # 统计结果
        for result in self.results:
            if result.status == "failed":
                failed_count += 1
            elif result.status == "warning":
                warning_count += 1
            elif result.status == "success":
                success_count += 1
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # 生成验证报告
        overall_status = "failed" if failed_count > 0 else ("warning" if warning_count > 0 else "success")
        
        validation_report = {
            "overall_status": overall_status,
            "summary": {
                "total_validations": len(self.results),
                "success_count": success_count,
                "warning_count": warning_count,
                "failed_count": failed_count,
                "duration_seconds": duration
            },
            "validations": [
                {
                    "component": result.component,
                    "status": result.status,
                    "message": result.message,
                    "details": result.details,
                    "timestamp": result.timestamp.isoformat() if result.timestamp else None
                }
                for result in self.results
            ],
            "production_ready": overall_status == "success",
            "mock_eliminated": all(
                result.status in ["success", "warning"] 
                for result in self.results 
                if "Mock" in result.component
            ),
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"验证完成 - 状态: {overall_status}, 成功: {success_count}, 警告: {warning_count}, 失败: {failed_count}")
        
        return validation_report

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="TgGod生产部署验证工具")
    parser.add_argument("--url", default="http://localhost", help="服务基础URL")
    parser.add_argument("--timeout", type=int, default=30, help="请求超时时间(秒)")
    parser.add_argument("--output", help="输出报告文件路径")
    parser.add_argument("--json", action="store_true", help="以JSON格式输出")
    
    args = parser.parse_args()
    
    # 创建验证器实例
    validator = ProductionValidator(base_url=args.url, timeout=args.timeout)
    
    # 运行验证
    report = validator.run_complete_validation()
    
    # 输出结果
    if args.json:
        output = json.dumps(report, indent=2, ensure_ascii=False)
    else:
        # 格式化输出
        output = f"""
=== TgGod 生产部署验证报告 ===
时间: {report['timestamp']}
总体状态: {report['overall_status'].upper()}
生产就绪: {'是' if report['production_ready'] else '否'}
Mock已消除: {'是' if report['mock_eliminated'] else '否'}

=== 验证摘要 ===
总验证数: {report['summary']['total_validations']}
成功: {report['summary']['success_count']}
警告: {report['summary']['warning_count']}
失败: {report['summary']['failed_count']}
耗时: {report['summary']['duration_seconds']:.2f}秒

=== 详细结果 ===
"""
        
        for validation in report['validations']:
            status_symbol = {
                'success': '✅',
                'warning': '⚠️', 
                'failed': '❌'
            }.get(validation['status'], '❓')
            
            output += f"{status_symbol} {validation['component']}: {validation['message']}\n"
            if validation['details']:
                output += f"   详情: {json.dumps(validation['details'], ensure_ascii=False)}\n"
        
        output += f"\n=== 验证完成 ===\n"
    
    # 保存或打印输出
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(output)
        print(f"验证报告已保存到: {args.output}")
    else:
        print(output)
    
    # 设置退出代码
    sys.exit(0 if report['overall_status'] == 'success' else 1)

if __name__ == "__main__":
    main()