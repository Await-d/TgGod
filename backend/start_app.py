#!/usr/bin/env python3
"""
应用启动脚本
在启动应用之前检查和修复数据库
"""

import os
import sys
import logging
import asyncio
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from check_database import DatabaseChecker

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_and_repair_database():
    """检查并修复数据库"""
    logger.info("启动前检查数据库...")
    
    checker = DatabaseChecker()
    success = checker.check_and_repair()
    
    if not success:
        logger.error("数据库检查失败，无法启动应用")
        return False
    
    logger.info("数据库检查完成，准备启动应用...")
    return True

def main():
    """主函数"""
    logger.info("TgGod 应用启动器")
    logger.info("=" * 40)
    
    # 检查数据库
    if not check_and_repair_database():
        logger.error("应用启动失败")
        return False
    
    # 启动应用
    try:
        logger.info("启动 FastAPI 应用...")
        
        # 导入并启动应用
        import uvicorn
        from app.main import app
        
        # 获取配置
        host = os.getenv("HOST", "0.0.0.0")
        port = int(os.getenv("PORT", "8000"))
        
        logger.info(f"应用将在 {host}:{port} 启动")
        
        # 启动服务器
        uvicorn.run(
            app,
            host=host,
            port=port,
            reload=os.getenv("RELOAD", "false").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "info").lower()
        )
        
    except Exception as e:
        logger.error(f"应用启动失败: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)