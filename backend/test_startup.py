#!/usr/bin/env python3
"""
应用启动测试脚本
用于验证应用的关键组件能否正常导入和初始化
"""
import sys
import os
import asyncio
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_imports():
    """测试关键模块的导入"""
    try:
        logger.info("测试模块导入...")
        
        # 测试数据库模型导入
        from app.models.rule import DownloadTask, FilterRule
        logger.info("✅ 数据库模型导入成功")
        
        # 测试数据库连接
        from app.database import engine, Base
        logger.info("✅ 数据库连接模块导入成功")
        
        # 测试配置
        from app.config import settings
        logger.info("✅ 配置模块导入成功")
        
        # 测试API模块
        from app.api import task, rule, telegram
        logger.info("✅ API模块导入成功")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 模块导入失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

async def test_services():
    """测试服务组件的导入和基本初始化"""
    try:
        logger.info("测试服务组件...")
        
        # 测试任务调度器导入
        from app.services.task_scheduler import TaskScheduler
        scheduler = TaskScheduler()
        logger.info("✅ 任务调度器创建成功")
        
        # 测试任务执行服务导入
        from app.services.task_execution_service import TaskExecutionService
        execution_service = TaskExecutionService()
        logger.info("✅ 任务执行服务创建成功")
        
        # 测试媒体下载器导入
        from app.services.media_downloader import TelegramMediaDownloader
        downloader = TelegramMediaDownloader()
        logger.info("✅ 媒体下载器创建成功")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 服务组件测试失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

async def test_database():
    """测试数据库表创建"""
    try:
        logger.info("测试数据库表创建...")
        
        from app.database import engine, Base
        from app.models import rule, telegram, log, user
        
        # 创建所有表
        Base.metadata.create_all(bind=engine)
        logger.info("✅ 数据库表创建成功")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 数据库表创建失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

async def main():
    """主测试函数"""
    logger.info("🚀 开始应用启动测试...")
    
    # 测试模块导入
    if not await test_imports():
        sys.exit(1)
    
    # 测试服务组件
    if not await test_services():
        sys.exit(1)
    
    # 测试数据库
    if not await test_database():
        sys.exit(1)
    
    logger.info("✅ 所有测试通过！应用组件可以正常导入和初始化")
    logger.info("🎉 应用应该能够正常启动")

if __name__ == "__main__":
    asyncio.run(main())