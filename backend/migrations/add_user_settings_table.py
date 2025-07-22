"""
用户设置表迁移脚本
用于创建user_settings表，如果不存在的话
"""
import os
import sys
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, JSON, MetaData, Table, inspect
import json
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_database_url():
    """从环境变量或配置文件获取数据库URL"""
    try:
        # 首先尝试从配置中获取
        try:
            from app.config import settings
            return settings.database_url
        except ImportError:
            # 如果无法导入，则使用环境变量或默认值
            return os.environ.get("DATABASE_URL", "sqlite:////app/data/tggod.db")
    except Exception as e:
        logger.error(f"获取数据库URL时出错: {e}")
        return "sqlite:////app/data/tggod.db"

def create_user_settings_table():
    """创建user_settings表"""
    database_url = get_database_url()
    logger.info(f"使用数据库URL: {database_url}")
    
    # 创建引擎
    if "sqlite" in database_url:
        engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False},
            echo=False
        )
    else:
        engine = create_engine(database_url, echo=False)
    
    # 获取元数据
    metadata = MetaData()
    
    # 检查表是否已存在
    inspector = inspect(engine)
    if "user_settings" in inspector.get_table_names():
        logger.info("user_settings表已存在，跳过创建")
        return
    
    # 定义user_settings表
    Table(
        "user_settings",
        metadata,
        Column("id", Integer, primary_key=True, index=True),
        Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True),
        Column("settings_data", JSON, nullable=False),
        Column("updated_at", String, nullable=False),
        Column("created_at", String, nullable=False),
    )
    
    # 创建表
    metadata.create_all(engine)
    logger.info("成功创建user_settings表")

def run_migration():
    """运行迁移"""
    try:
        create_user_settings_table()
        return True, "用户设置表迁移成功"
    except Exception as e:
        logger.error(f"用户设置表迁移失败: {e}")
        return False, f"用户设置表迁移失败: {e}"

if __name__ == "__main__":
    success, message = run_migration()
    if success:
        logger.info(message)
        sys.exit(0)
    else:
        logger.error(message)
        sys.exit(1)