#!/usr/bin/env python3
"""
生产环境启动脚本
包含完整的数据库检查和初始化
"""

import os
import sys
import logging
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """主函数"""
    logger.info("=" * 50)
    logger.info("TgGod 生产环境启动")
    logger.info("=" * 50)
    
    # 1. 检查环境变量
    logger.info("检查环境配置...")
    from app.config import settings
    
    if not settings.database_url:
        logger.error("未设置数据库连接URL")
        return False
    
    logger.info(f"数据库URL: {settings.database_url}")
    
    # 2. 数据库检查和初始化
    logger.info("开始数据库检查...")
    
    try:
        from check_database import DatabaseChecker
        checker = DatabaseChecker()
        
        # 执行数据库检查和修复
        success = checker.check_and_repair()
        
        if not success:
            logger.error("数据库检查失败，无法启动应用")
            return False
        
        logger.info("数据库检查完成")
        
    except Exception as e:
        logger.error(f"数据库检查过程中发生错误: {e}")
        return False
    
    # 3. 启动应用
    logger.info("启动 FastAPI 应用...")
    
    try:
        import uvicorn
        from app.main import app
        
        # 获取配置
        host = os.getenv("HOST", "0.0.0.0")
        port = int(os.getenv("PORT", "8000"))
        workers = int(os.getenv("WORKERS", "1"))
        
        logger.info(f"应用将在 {host}:{port} 启动")
        logger.info(f"工作进程数: {workers}")
        
        # 启动服务器
        if workers > 1:
            # 多进程模式
            uvicorn.run(
                "app.main:app",
                host=host,
                port=port,
                workers=workers,
                log_level="debug",
                access_log=True,
                use_colors=True
            )
        else:
            # 单进程模式
            uvicorn.run(
                app,
                host=host,
                port=port,
                log_level="debug",
                access_log=True,
                use_colors=True
            )
        
    except Exception as e:
        logger.error(f"应用启动失败: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)