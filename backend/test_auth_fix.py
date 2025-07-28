#!/usr/bin/env python3
"""
测试认证修复的脚本
验证媒体下载器的认证状态缓存机制是否正常工作
"""
import os
import sys
import asyncio
import logging

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_auth_fix():
    """测试认证修复功能"""
    try:
        from app.services.media_downloader import TelegramMediaDownloader, check_main_session_status
        
        logger.info("=== 开始测试认证修复功能 ===")
        
        # 1. 测试主session状态检查
        logger.info("1. 检查主session状态...")
        main_session_valid = await check_main_session_status()
        logger.info(f"主session状态: {'有效' if main_session_valid else '无效'}")
        
        # 2. 测试媒体下载器初始化
        logger.info("2. 测试媒体下载器初始化...")
        downloader = TelegramMediaDownloader()
        
        try:
            await downloader.initialize()
            logger.info("媒体下载器初始化成功")
            
            # 清理资源
            await downloader.cleanup()
            logger.info("媒体下载器清理完成")
            
        except Exception as init_error:
            logger.error(f"媒体下载器初始化失败: {init_error}")
            
        logger.info("=== 测试完成 ===")
        
    except ImportError as e:
        logger.error(f"导入模块失败: {e}")
        logger.error("请确保安装了所有依赖: pip install -r requirements.txt")
        
    except Exception as e:
        logger.error(f"测试过程中发生错误: {e}")

if __name__ == "__main__":
    asyncio.run(test_auth_fix())