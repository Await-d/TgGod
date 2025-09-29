"""
数据库检查API
提供数据库结构检查和状态查询的API接口
"""

from fastapi import APIRouter, HTTPException
from ..utils.database_checker import database_checker

router = APIRouter()

@router.get("/check")
async def check_database_structure():
    """检查数据库结构完整性"""
    try:
        check_results = database_checker.check_database_structure()
        return {
            "success": True,
            "data": check_results,
            "message": f"数据库检查完成，发现 {check_results['issues_found']} 个问题"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"数据库检查失败: {str(e)}")

@router.post("/repair")
async def repair_database_structure():
    """修复数据库结构问题"""
    try:
        # 先检查结构
        check_results = database_checker.check_database_structure()
        
        if check_results['status'] == 'healthy':
            return {
                "success": True,
                "data": {
                    "repaired_tables": [],
                    "repaired_columns": {},
                    "failed_repairs": [],
                    "success": True
                },
                "message": "数据库结构完整，无需修复"
            }
        
        # 执行修复
        repair_results = database_checker.repair_database_structure(check_results)
        
        return {
            "success": repair_results['success'],
            "data": {
                "check_results": check_results,
                "repair_results": repair_results
            },
            "message": f"修复完成，成功修复 {check_results.get('fixed_issues', 0)} 个问题"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"数据库修复失败: {str(e)}")

@router.get("/info")
async def get_database_info():
    """获取数据库基本信息"""
    try:
        db_info = database_checker.get_database_info()
        return {
            "success": True,
            "data": db_info,
            "message": "获取数据库信息成功"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取数据库信息失败: {str(e)}")

@router.get("/health")
async def database_health_check():
    """数据库健康检查"""
    try:
        check_results = database_checker.check_database_structure()
        db_info = database_checker.get_database_info()
        
        health_status = {
            "status": check_results['status'],
            "issues_count": check_results['issues_found'],
            "tables_count": db_info.get('table_count', 0),
            "last_check": "刚刚"
        }
        
        return {
            "success": True,
            "data": health_status,
            "message": f"数据库健康状态: {check_results['status']}"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"数据库健康检查失败: {str(e)}")

@router.post("/startup-check")
async def run_startup_check():
    """手动运行启动时数据库检查"""
    try:
        check_success = database_checker.run_startup_check()
        
        return {
            "success": check_success,
            "data": {
                "check_passed": check_success
            },
            "message": "启动检查完成" if check_success else "启动检查发现问题"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动检查失败: {str(e)}")