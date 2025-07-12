#!/usr/bin/env python3
"""
强制修复转发消息字段脚本
专门用于生产环境下强制添加缺失的转发消息字段
"""

import os
import sys
import logging
from pathlib import Path
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import SQLAlchemyError

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from app.config import settings
except ImportError:
    # 如果无法导入设置，使用默认配置
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./tggod.db')
    print(f"使用环境变量或默认数据库URL: {DATABASE_URL}")
else:
    DATABASE_URL = settings.database_url
    print(f"使用配置文件数据库URL: {DATABASE_URL}")

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def force_add_forwarded_columns():
    """强制添加转发消息字段"""
    logger.info("开始强制添加转发消息字段...")
    
    try:
        # 创建数据库连接
        engine = create_engine(DATABASE_URL)
        inspector = inspect(engine)
        
        # 检查表是否存在
        if not inspector.has_table('telegram_messages'):
            logger.error("telegram_messages表不存在！")
            return False
        
        # 获取现有列
        existing_columns = set()
        try:
            columns = inspector.get_columns('telegram_messages')
            existing_columns = {col['name'] for col in columns}
            logger.info(f"表telegram_messages现有列数量: {len(existing_columns)}")
        except Exception as e:
            logger.error(f"无法获取现有列信息: {e}")
            return False
        
        # 定义需要添加的转发消息字段
        forwarded_columns = {
            'forwarded_from_id': 'BIGINT',
            'forwarded_from_type': 'VARCHAR(20)',
            'forwarded_date': 'DATETIME'
        }
        
        added_columns = []
        failed_columns = []
        
        with engine.connect() as conn:
            # 开始事务
            trans = conn.begin()
            
            try:
                for column_name, column_type in forwarded_columns.items():
                    if column_name not in existing_columns:
                        try:
                            sql = f"ALTER TABLE telegram_messages ADD COLUMN {column_name} {column_type}"
                            logger.info(f"执行SQL: {sql}")
                            conn.execute(text(sql))
                            added_columns.append(column_name)
                            logger.info(f"✅ 成功添加列: {column_name}")
                        except Exception as e:
                            logger.error(f"❌ 添加列 {column_name} 失败: {e}")
                            failed_columns.append(column_name)
                            # 不回滚，继续尝试其他列
                    else:
                        logger.info(f"📋 列 {column_name} 已存在，跳过")
                
                # 提交事务
                trans.commit()
                
                if added_columns:
                    logger.info(f"🎉 成功添加 {len(added_columns)} 个转发消息字段: {', '.join(added_columns)}")
                
                if failed_columns:
                    logger.warning(f"⚠️  {len(failed_columns)} 个字段添加失败: {', '.join(failed_columns)}")
                
                if not added_columns and not failed_columns:
                    logger.info("✅ 所有转发消息字段已存在，无需修改")
                
                return len(failed_columns) == 0
                
            except Exception as e:
                trans.rollback()
                logger.error(f"❌ 事务执行失败，已回滚: {e}")
                return False
                
    except Exception as e:
        logger.error(f"❌ 数据库连接或操作失败: {e}")
        return False

def verify_columns():
    """验证转发消息字段是否存在"""
    logger.info("验证转发消息字段...")
    
    try:
        engine = create_engine(DATABASE_URL)
        inspector = inspect(engine)
        
        if not inspector.has_table('telegram_messages'):
            logger.error("telegram_messages表不存在！")
            return False
        
        columns = inspector.get_columns('telegram_messages')
        existing_columns = {col['name'] for col in columns}
        
        required_forwarded_columns = ['forwarded_from_id', 'forwarded_from_type', 'forwarded_date']
        missing_columns = []
        
        for col in required_forwarded_columns:
            if col in existing_columns:
                logger.info(f"✅ 字段 {col} 存在")
            else:
                logger.error(f"❌ 字段 {col} 缺失")
                missing_columns.append(col)
        
        if missing_columns:
            logger.error(f"验证失败，缺失字段: {', '.join(missing_columns)}")
            return False
        else:
            logger.info("🎉 所有转发消息字段验证通过！")
            return True
            
    except Exception as e:
        logger.error(f"验证过程中出错: {e}")
        return False

def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("转发消息字段强制修复工具")
    logger.info("=" * 60)
    
    # 先验证现状
    if verify_columns():
        logger.info("所有字段已存在，无需修复")
        return True
    
    # 执行修复
    logger.info("检测到缺失字段，开始修复...")
    success = force_add_forwarded_columns()
    
    if success:
        # 再次验证
        logger.info("修复完成，进行最终验证...")
        if verify_columns():
            logger.info("🎉 转发消息字段修复成功！")
            return True
        else:
            logger.error("❌ 修复后验证失败")
            return False
    else:
        logger.error("❌ 修复过程失败")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)