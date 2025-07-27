#!/usr/bin/env python3
"""
测试SQLAlchemy text()表达式修复
"""
import sys
import os
import asyncio
import logging

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 配置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_task_db_manager():
    """测试任务数据库管理器的SQLAlchemy修复"""
    try:
        from app.services.task_db_manager import task_db_manager
        logger.info("🧪 开始测试任务数据库管理器...")
        
        # 测试进度更新会话
        async with task_db_manager.get_task_session(999, "progress") as session:
            # 这应该不会引发SQLAlchemy text()错误
            logger.info("✅ 进度更新会话测试成功")
        
        # 测试批量查询会话
        async with task_db_manager.get_task_session(999, "batch_query") as session:
            # 这应该不会引发SQLAlchemy text()错误
            logger.info("✅ 批量查询会话测试成功")
            
        # 测试快速状态更新
        await task_db_manager.quick_status_update(999, "testing")
        logger.info("✅ 快速状态更新测试成功")
        
        logger.info("🎉 所有SQLAlchemy text()修复测试通过!")
        return True
        
    except Exception as e:
        logger.error(f"❌ SQLAlchemy text()修复测试失败: {e}", exc_info=True)
        return False

def test_imports():
    """测试关键模块导入"""
    try:
        from sqlalchemy import text
        logger.info("✅ SQLAlchemy text导入成功")
        
        from app.services.task_db_manager import task_db_manager
        logger.info("✅ 任务数据库管理器导入成功")
        
        from app.services.task_execution_service import task_execution_service
        logger.info("✅ 任务执行服务导入成功")
        
        return True
    except Exception as e:
        logger.error(f"❌ 模块导入失败: {e}", exc_info=True)
        return False

async def main():
    """主测试函数"""
    logger.info("=" * 50)
    logger.info("SQLAlchemy text()表达式修复验证测试")
    logger.info("=" * 50)
    
    # 测试1: 模块导入
    logger.info("📦 测试1: 模块导入测试")
    if not test_imports():
        logger.error("模块导入测试失败，退出")
        return False
    
    # 测试2: 任务数据库管理器
    logger.info("📊 测试2: 任务数据库管理器测试")
    if not await test_task_db_manager():
        logger.error("任务数据库管理器测试失败")
        return False
    
    logger.info("=" * 50)
    logger.info("🎉 所有测试通过! SQLAlchemy text()错误已修复")
    logger.info("=" * 50)
    return True

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"测试执行失败: {e}", exc_info=True)
        sys.exit(1)