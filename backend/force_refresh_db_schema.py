#!/usr/bin/env python3
"""
强制刷新SQLAlchemy数据库表结构
"""

import os
import sys
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def force_refresh_schema():
    """强制刷新数据库表结构"""
    
    # 使用与应用相同的数据库配置
    database_url = os.environ.get("DATABASE_URL", "sqlite:////app/data/tggod.db")
    logger.info(f"数据库URL: {database_url}")
    
    try:
        # 创建引擎，关闭连接池避免缓存
        engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False} if "sqlite" in database_url else {},
            pool_pre_ping=True,
            pool_recycle=-1,  # 禁用连接池回收
            echo=True  # 开启SQL日志
        )
        
        # 创建会话
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = SessionLocal()
        
        logger.info("连接数据库成功")
        
        # 直接查询表结构
        logger.info("检查filter_rules表结构...")
        result = session.execute(text("PRAGMA table_info(filter_rules)"))
        columns = result.fetchall()
        
        logger.info("当前filter_rules表字段:")
        field_names = []
        for col in columns:
            field_names.append(col[1])
            logger.info(f"  {col[1]}: {col[2]} (nullable: {not col[3]}, default: {col[4]})")
        
        # 检查必需的同步字段
        required_sync_fields = ['last_sync_time', 'last_sync_message_count', 'sync_status', 'needs_full_resync']
        missing_fields = [field for field in required_sync_fields if field not in field_names]
        
        if missing_fields:
            logger.error(f"缺失字段: {missing_fields}")
            
            # 尝试添加缺失字段
            for field_name in missing_fields:
                if field_name == 'last_sync_time':
                    sql = "ALTER TABLE filter_rules ADD COLUMN last_sync_time DATETIME"
                elif field_name == 'last_sync_message_count':
                    sql = "ALTER TABLE filter_rules ADD COLUMN last_sync_message_count INTEGER DEFAULT 0"
                elif field_name == 'sync_status':
                    sql = "ALTER TABLE filter_rules ADD COLUMN sync_status VARCHAR(20) DEFAULT 'pending'"
                elif field_name == 'needs_full_resync':
                    sql = "ALTER TABLE filter_rules ADD COLUMN needs_full_resync BOOLEAN DEFAULT 1"
                
                try:
                    logger.info(f"执行: {sql}")
                    session.execute(text(sql))
                    session.commit()
                    logger.info(f"✓ 添加字段 {field_name} 成功")
                except Exception as e:
                    logger.error(f"添加字段 {field_name} 失败: {e}")
                    session.rollback()
        else:
            logger.info("✓ 所有必需字段都存在")
        
        # 测试查询这些字段
        logger.info("测试查询同步字段...")
        try:
            result = session.execute(text("""
                SELECT id, name, last_sync_time, last_sync_message_count, sync_status, needs_full_resync 
                FROM filter_rules 
                LIMIT 1
            """))
            row = result.fetchone()
            if row:
                logger.info(f"查询测试成功: {row}")
            else:
                logger.info("表中暂无数据")
        except Exception as e:
            logger.error(f"查询测试失败: {e}")
            return False
        
        # 强制刷新SQLAlchemy元数据
        logger.info("强制刷新SQLAlchemy元数据...")
        engine.dispose()  # 关闭所有连接
        
        return True
        
    except Exception as e:
        logger.error(f"刷新失败: {e}")
        return False
    finally:
        if 'session' in locals():
            session.close()

if __name__ == "__main__":
    logger.info("开始强制刷新数据库表结构...")
    success = force_refresh_schema()
    if success:
        logger.info("✅ 刷新完成，建议重启应用")
    else:
        logger.error("❌ 刷新失败")