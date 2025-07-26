#!/usr/bin/env python3
"""
最小化启动测试
用于确定具体的错误位置
"""
import sys
import os
import logging

# 设置最小日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_step(step_name, test_func):
    """测试步骤包装器"""
    try:
        logger.info(f"🔍 开始测试: {step_name}")
        test_func()
        logger.info(f"✅ 测试通过: {step_name}")
        return True
    except Exception as e:
        logger.error(f"❌ 测试失败: {step_name} - {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def test_basic_imports():
    """测试基本导入"""
    from app.config import settings
    from app.database import engine, Base

def test_model_imports():
    """测试模型导入"""
    from app.models.rule import DownloadTask, FilterRule
    from app.models.telegram import TelegramGroup, TelegramMessage

def test_service_imports():
    """测试服务导入"""
    # 测试不依赖其他服务的基础服务
    from app.services.task_scheduler import TaskScheduler
    
def test_database_creation():
    """测试数据库表创建"""
    from app.database import engine, Base
    # 只导入必要的模型
    from app.models import rule, telegram, log, user
    Base.metadata.create_all(bind=engine)

def main():
    """主测试函数"""
    logger.info("🚀 开始最小化启动测试...")
    
    tests = [
        ("基本配置和数据库导入", test_basic_imports),
        ("数据库模型导入", test_model_imports),
        ("服务组件导入", test_service_imports),
        ("数据库表创建", test_database_creation),
    ]
    
    failed_tests = []
    
    for test_name, test_func in tests:
        if not test_step(test_name, test_func):
            failed_tests.append(test_name)
            # 继续测试其他步骤
    
    if failed_tests:
        logger.error(f"❌ 以下测试失败: {', '.join(failed_tests)}")
        return 1
    else:
        logger.info("🎉 所有最小化测试通过！")
        return 0

if __name__ == "__main__":
    sys.exit(main())