#!/usr/bin/env python3
"""
数据库检查和自动修复脚本
检查数据库结构是否与模型匹配，自动运行必要的迁移
"""

import os
import sys
import logging
from pathlib import Path
from typing import List, Dict, Any
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.config import settings
from app.database import Base, get_db
from app.models.telegram import TelegramGroup, TelegramMessage
from app.models.user import User
from app.models.rule import FilterRule
from app.models.log import SystemLog

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DatabaseChecker:
    """数据库检查器"""
    
    def __init__(self):
        self.engine = create_engine(settings.database_url)
        self.inspector = inspect(self.engine)
        self.alembic_cfg = Config(str(project_root / "alembic.ini"))
        self.script_dir = ScriptDirectory.from_config(self.alembic_cfg)
        
    def check_database_exists(self) -> bool:
        """检查数据库是否存在"""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("数据库连接成功")
            return True
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            return False
    
    def get_current_tables(self) -> List[str]:
        """获取当前数据库中的表"""
        try:
            return self.inspector.get_table_names()
        except Exception as e:
            logger.error(f"获取表列表失败: {e}")
            return []
    
    def get_table_columns(self, table_name: str) -> Dict[str, Any]:
        """获取表的列信息"""
        try:
            columns = self.inspector.get_columns(table_name)
            return {col['name']: col for col in columns}
        except Exception as e:
            logger.error(f"获取表 {table_name} 列信息失败: {e}")
            return {}
    
    def check_required_tables(self) -> Dict[str, bool]:
        """检查必需的表是否存在"""
        required_tables = {
            'users': User.__tablename__,
            'telegram_groups': TelegramGroup.__tablename__,
            'telegram_messages': TelegramMessage.__tablename__,
            'filter_rules': FilterRule.__tablename__,
            'system_logs': SystemLog.__tablename__,
            'alembic_version': 'alembic_version'
        }
        
        current_tables = self.get_current_tables()
        table_status = {}
        
        for name, table_name in required_tables.items():
            exists = table_name in current_tables
            table_status[name] = exists
            status = "✓" if exists else "✗"
            logger.info(f"表 {table_name}: {status}")
        
        return table_status
    
    def check_required_columns(self) -> Dict[str, Dict[str, bool]]:
        """检查必需的列是否存在"""
        required_columns = {
            'telegram_messages': [
                'id', 'group_id', 'message_id', 'sender_id', 'sender_username',
                'sender_name', 'text', 'media_type', 'media_path', 'media_size',
                'media_filename', 'view_count', 'is_forwarded', 'forwarded_from',
                'is_own_message',  # 新增字段
                'reply_to_message_id', 'edit_date', 'is_pinned', 'reactions',
                'mentions', 'hashtags', 'urls', 'date', 'created_at', 'updated_at'
            ],
            'telegram_groups': [
                'id', 'telegram_id', 'title', 'username', 'description',
                'member_count', 'is_active', 'created_at', 'updated_at'
            ],
            'users': [
                'id', 'username', 'email', 'full_name', 'hashed_password',
                'is_active', 'is_superuser', 'created_at', 'updated_at'
            ]
        }
        
        column_status = {}
        
        for table_name, columns in required_columns.items():
            if table_name not in self.get_current_tables():
                logger.warning(f"表 {table_name} 不存在，跳过列检查")
                continue
                
            current_columns = self.get_table_columns(table_name)
            table_column_status = {}
            
            for column_name in columns:
                exists = column_name in current_columns
                table_column_status[column_name] = exists
                status = "✓" if exists else "✗"
                if not exists:
                    logger.warning(f"表 {table_name} 缺少列: {column_name}")
                    
            column_status[table_name] = table_column_status
        
        return column_status
    
    def get_current_revision(self) -> str:
        """获取当前数据库的revision"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT version_num FROM alembic_version"))
                row = result.fetchone()
                if row:
                    return row[0]
                else:
                    return "None"
        except Exception as e:
            logger.error(f"获取当前revision失败: {e}")
            return "None"
    
    def get_latest_revision(self) -> str:
        """获取最新的revision"""
        try:
            return self.script_dir.get_current_head()
        except Exception as e:
            logger.error(f"获取最新revision失败: {e}")
            return "None"
    
    def run_migrations(self) -> bool:
        """运行数据库迁移"""
        try:
            logger.info("开始运行数据库迁移...")
            
            # 检查是否需要初始化alembic版本表
            current_revision = self.get_current_revision()
            if current_revision == "None":
                logger.info("初始化alembic版本表...")
                command.stamp(self.alembic_cfg, "head")
            
            # 运行升级
            command.upgrade(self.alembic_cfg, "head")
            logger.info("数据库迁移完成")
            return True
            
        except Exception as e:
            logger.error(f"数据库迁移失败: {e}")
            return False
    
    def create_tables(self) -> bool:
        """创建所有表"""
        try:
            logger.info("创建数据库表...")
            Base.metadata.create_all(bind=self.engine)
            logger.info("数据库表创建完成")
            return True
        except Exception as e:
            logger.error(f"创建数据库表失败: {e}")
            return False
    
    def check_and_repair(self) -> bool:
        """检查并修复数据库"""
        logger.info("开始数据库检查...")
        
        # 检查数据库连接
        if not self.check_database_exists():
            logger.error("数据库连接失败，请检查数据库配置")
            return False
        
        # 检查表结构
        table_status = self.check_required_tables()
        column_status = self.check_required_columns()
        
        # 检查是否需要修复
        missing_tables = [name for name, exists in table_status.items() if not exists]
        missing_columns = {}
        
        for table_name, columns in column_status.items():
            missing_cols = [col for col, exists in columns.items() if not exists]
            if missing_cols:
                missing_columns[table_name] = missing_cols
        
        if missing_tables or missing_columns:
            logger.info("发现数据库结构问题，开始修复...")
            
            if missing_tables:
                logger.info(f"缺少表: {', '.join(missing_tables)}")
            
            if missing_columns:
                for table, cols in missing_columns.items():
                    logger.info(f"表 {table} 缺少列: {', '.join(cols)}")
            
            # 运行迁移
            success = self.run_migrations()
            if not success:
                logger.error("数据库迁移失败")
                return False
            
            # 再次检查
            logger.info("重新检查数据库结构...")
            table_status = self.check_required_tables()
            column_status = self.check_required_columns()
            
            # 验证修复结果
            remaining_issues = []
            for name, exists in table_status.items():
                if not exists:
                    remaining_issues.append(f"表 {name} 仍然缺失")
            
            for table_name, columns in column_status.items():
                for col, exists in columns.items():
                    if not exists:
                        remaining_issues.append(f"表 {table_name} 的列 {col} 仍然缺失")
            
            if remaining_issues:
                logger.error("数据库修复未完全成功:")
                for issue in remaining_issues:
                    logger.error(f"  - {issue}")
                return False
            
            logger.info("数据库结构修复完成")
        else:
            logger.info("数据库结构检查通过")
        
        # 检查版本信息
        current_revision = self.get_current_revision()
        latest_revision = self.get_latest_revision()
        
        logger.info(f"当前数据库版本: {current_revision}")
        logger.info(f"最新模型版本: {latest_revision}")
        
        if current_revision != latest_revision:
            logger.info("数据库版本不是最新，运行升级...")
            if not self.run_migrations():
                logger.error("数据库升级失败")
                return False
        
        logger.info("数据库检查和修复完成")
        return True


def main():
    """主函数"""
    logger.info("=" * 50)
    logger.info("TgGod 数据库检查和修复工具")
    logger.info("=" * 50)
    
    # 检查环境变量
    if not settings.database_url:
        logger.error("未设置数据库连接URL，请检查环境变量")
        return False
    
    logger.info(f"数据库URL: {settings.database_url}")
    
    # 创建检查器
    checker = DatabaseChecker()
    
    # 执行检查和修复
    success = checker.check_and_repair()
    
    if success:
        logger.info("数据库检查和修复成功完成")
        return True
    else:
        logger.error("数据库检查和修复失败")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)