#!/usr/bin/env python3
"""
媒体下载器测试脚本
用于验证Telegram媒体下载功能是否正常
"""

import asyncio
import logging
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.media_downloader import get_media_downloader
from app.config import settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def test_media_downloader():
    """测试媒体下载器初始化和基本功能"""
    try:
        logger.info("开始测试Telegram媒体下载器...")
        
        # 检查配置
        logger.info(f"API ID: {settings.telegram_api_id}")
        logger.info(f"API Hash: {'已设置' if settings.telegram_api_hash else '未设置'}")
        
        if not settings.telegram_api_id or not settings.telegram_api_hash:
            logger.error("Telegram API配置不完整，请检查配置文件")
            return False
        
        # 初始化下载器
        downloader = await get_media_downloader()
        logger.info("媒体下载器初始化成功")
        
        # 检查连接状态
        if downloader.client and downloader.client.is_connected():
            logger.info("Telegram客户端连接正常")
            
            # 检查认证状态
            if await downloader.client.is_user_authorized():
                logger.info("Telegram客户端认证成功")
                
                # 获取当前用户信息
                me = await downloader.client.get_me()
                logger.info(f"当前用户: {me.first_name} {me.last_name or ''} (@{me.username or 'N/A'})")
                
                return True
            else:
                logger.error("Telegram客户端未认证")
                return False
        else:
            logger.error("Telegram客户端连接失败")
            return False
            
    except Exception as e:
        logger.error(f"测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 清理资源
        try:
            if 'downloader' in locals() and downloader:
                await downloader.close()
        except:
            pass

async def test_session_file():
    """检查session文件状态"""
    try:
        session_path = "./telegram_sessions/tggod_session.session"
        
        if os.path.exists(session_path):
            size = os.path.getsize(session_path)
            logger.info(f"Session文件存在: {session_path} (大小: {size} bytes)")
            
            if size > 0:
                logger.info("Session文件有内容，应该包含认证信息")
                return True
            else:
                logger.warning("Session文件为空，可能需要重新认证")
                return False
        else:
            logger.warning(f"Session文件不存在: {session_path}")
            logger.info("请先运行主程序进行Telegram认证")
            return False
    except Exception as e:
        logger.error(f"检查session文件失败: {e}")
        return False

async def main():
    """主测试函数"""
    logger.info("=" * 50)
    logger.info("Telegram媒体下载器测试")
    logger.info("=" * 50)
    
    # 测试session文件
    logger.info("1. 检查Session文件...")
    session_ok = await test_session_file()
    
    if not session_ok:
        logger.error("Session文件问题，请先运行主程序完成Telegram认证")
        return
    
    # 测试下载器
    logger.info("\n2. 测试媒体下载器...")
    downloader_ok = await test_media_downloader()
    
    if downloader_ok:
        logger.info("\n✅ 媒体下载器测试通过")
        logger.info("媒体下载功能应该可以正常工作")
    else:
        logger.error("\n❌ 媒体下载器测试失败")
        logger.error("请检查Telegram认证状态和API配置")

if __name__ == "__main__":
    asyncio.run(main())