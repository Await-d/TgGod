#!/usr/bin/env python3
"""
生产环境数据库初始化脚本
确保数据库表结构正确创建
"""

import os
import sys
import logging
from pathlib import Path
from typing import List, Dict, Any
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.config import settings
from app.database import Base

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def init_database():
    """初始化数据库"""
    logger.info("开始初始化数据库...")
    
    try:
        # 创建数据库引擎
        engine = create_engine(settings.database_url, echo=False)
        
        # 1. 创建所有表
        logger.info("创建数据库表...")
        Base.metadata.create_all(bind=engine)
        logger.info("数据库表创建完成")
        
        # 2. 初始化 Alembic 版本表
        logger.info("初始化 Alembic 版本管理...")
        alembic_cfg = Config(str(project_root / "alembic.ini"))
        
        # 检查 alembic_version 表是否存在
        with engine.connect() as conn:
            try:
                result = conn.execute(text("SELECT version_num FROM alembic_version"))
                result.fetchone()
                logger.info("Alembic 版本表已存在")
            except Exception:
                logger.info("Alembic 版本表不存在，正在创建...")
                # 标记为最新版本
                command.stamp(alembic_cfg, "head")
                logger.info("Alembic 版本表创建完成")
        
        # 3. 验证表结构
        logger.info("验证数据库结构...")
        from sqlalchemy import inspect
        
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        required_tables = [
            'users', 'telegram_groups', 'telegram_messages', 
            'filter_rules', 'system_logs', 'alembic_version'
        ]
        
        missing_tables = [t for t in required_tables if t not in tables]
        if missing_tables:
            logger.error(f"缺少表: {missing_tables}")
            return False
        
        logger.info(f"数据库验证通过，共有 {len(tables)} 个表")
        
        # 4. 验证关键字段
        logger.info("验证关键字段...")
        columns = inspector.get_columns('telegram_messages')
        column_names = [col['name'] for col in columns]
        
        # 检查基础字段
        required_columns = ['is_own_message', 'is_forwarded', 'is_pinned']
        missing_columns = [col for col in required_columns if col not in column_names]
        
        # 检查下载进度字段
        download_progress_columns = [
            'download_progress', 'downloaded_size', 'download_speed', 
            'estimated_time_remaining', 'download_started_at'
        ]
        missing_download_columns = [col for col in download_progress_columns if col not in column_names]
        
        all_missing = missing_columns + missing_download_columns
        
        if all_missing:
            logger.error(f"telegram_messages 表缺少字段: {all_missing}")
            
            # 尝试运行数据库修复工具
            logger.info("尝试自动修复缺少的字段...")
            try:
                from fix_database_schema import fix_telegram_messages_table
                db_path = str(project_root / "tggod.db") if settings.database_url.startswith("sqlite:///./") else settings.database_url.replace("sqlite:///", "")
                success = fix_telegram_messages_table(db_path)
                if success:
                    logger.info("✅ 字段修复成功")
                    # 重新验证
                    columns = inspector.get_columns('telegram_messages')
                    column_names = [col['name'] for col in columns]
                    final_missing = [col for col in all_missing if col not in column_names]
                    if final_missing:
                        logger.error(f"修复后仍缺少字段: {final_missing}")
                        return False
                else:
                    logger.error("❌ 字段修复失败")
                    return False
            except Exception as repair_error:
                logger.error(f"字段修复过程中出错: {repair_error}")
                return False
        
        logger.info("所有关键字段验证通过")
        
        logger.info("数据库初始化完成!")
        return True
        
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        return False

def main():
    """主函数"""
    logger.info("=" * 50)
    logger.info("TgGod 生产环境数据库初始化")
    logger.info("=" * 50)
    
    # 检查环境变量
    if not settings.database_url:
        logger.error("未设置数据库连接URL")
        return False
    
    logger.info(f"数据库URL: {settings.database_url}")
    
    # 初始化数据库
    success = init_database()
    
    if success:
        logger.info("数据库初始化成功!")
        logger.info("可以安全启动应用程序")
        return True
    else:
        logger.error("数据库初始化失败!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)