#!/usr/bin/env python3
"""
生产环境启动脚本
包含完整的数据库检查和初始化
修复Docker日志输出问题
"""

import os
import sys
import logging
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 确保标准输出不被缓冲，重要！
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# 设置环境变量确保 Python 输出不缓冲
os.environ['PYTHONUNBUFFERED'] = '1'

# 设置日志 - 强制输出到控制台
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)  # 明确指定输出到 stdout
    ],
    force=True  # 强制重新配置已存在的日志配置
)
logger = logging.getLogger(__name__)

def main():
    """主函数"""
    # 确保输出立即刷新
    print("=" * 50, flush=True)
    print("TgGod 生产环境启动", flush=True)
    print("=" * 50, flush=True)
    
    logger.info("=" * 50)
    logger.info("TgGod 生产环境启动")
    logger.info("=" * 50)
    
    # 1. 检查环境变量
    logger.info("检查环境配置...")
    sys.stdout.flush()  # 强制刷新输出
    
    from app.config import settings
    
    if not settings.database_url:
        logger.error("未设置数据库连接URL")
        sys.stdout.flush()
        return False
    
    logger.info(f"数据库URL: {settings.database_url}")
    sys.stdout.flush()
    
    # 2. 数据库检查和初始化
    logger.info("开始数据库检查...")
    sys.stdout.flush()
    
    try:
        from check_database import DatabaseChecker
        checker = DatabaseChecker()
        
        # 执行数据库检查和修复
        success = checker.check_and_repair()
        
        if not success:
            logger.error("数据库检查失败，无法启动应用")
            sys.stdout.flush()
            return False
        
        logger.info("数据库检查完成")
        sys.stdout.flush()
        
    except Exception as e:
        logger.error(f"数据库检查过程中发生错误: {e}")
        sys.stdout.flush()
        return False
    
    # 3. 启动应用前的最后检查
    logger.info("准备启动 FastAPI 应用...")
    sys.stdout.flush()
    
    # 恢复原始的 stdout/stderr，确保 uvicorn 能正确输出
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    
    try:
        import uvicorn
        from app.main import app
        
        # 获取配置
        host = os.getenv("HOST", "0.0.0.0")
        port = int(os.getenv("PORT", "8000"))
        workers = int(os.getenv("WORKERS", "1"))
        
        logger.info(f"应用将在 {host}:{port} 启动")
        logger.info(f"工作进程数: {workers}")
        logger.info("切换到 uvicorn 日志输出...")
        sys.stdout.flush()
        
        # 确保 uvicorn 使用原始的输出流
        sys.stdout = original_stdout
        sys.stderr = original_stderr
        
        # 启动服务器
        if workers > 1:
            # 多进程模式
            uvicorn.run(
                "app.main:app",
                host=host,
                port=port,
                workers=workers,
                log_level="info",
                access_log=True,
                use_colors=False,  # 在容器中禁用颜色
                loop="asyncio"
            )
        else:
            # 单进程模式
            uvicorn.run(
                app,
                host=host,
                port=port,
                log_level="info",
                access_log=True,
                use_colors=False,  # 在容器中禁用颜色
                loop="asyncio"
            )
        
    except Exception as e:
        logger.error(f"应用启动失败: {e}")
        sys.stdout.flush()
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)