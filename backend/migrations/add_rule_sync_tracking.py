"""
添加规则同步跟踪字段

这个迁移为FilterRule表添加以下字段：
- last_sync_time: 最后同步时间
- last_sync_message_count: 最后同步的消息数量
- sync_status: 同步状态 ('pending', 'syncing', 'completed', 'failed')
- needs_full_resync: 是否需要完全重新同步（规则修改后设为True）
"""

from sqlalchemy import text
from backend.app.database import engine
import logging

logger = logging.getLogger(__name__)

def upgrade():
    """添加规则同步跟踪字段"""
    try:
        with engine.connect() as connection:
            # 添加同步跟踪字段 - SQLite需要分别添加每个字段
            connection.execute(text("""
                ALTER TABLE filter_rules 
                ADD COLUMN last_sync_time TIMESTAMP WITH TIME ZONE
            """))
            
            connection.execute(text("""
                ALTER TABLE filter_rules 
                ADD COLUMN last_sync_message_count INTEGER DEFAULT 0
            """))
            
            connection.execute(text("""
                ALTER TABLE filter_rules 
                ADD COLUMN sync_status VARCHAR(20) DEFAULT 'pending'
            """))
            
            connection.execute(text("""
                ALTER TABLE filter_rules 
                ADD COLUMN needs_full_resync BOOLEAN DEFAULT TRUE
            """))
            
            # 创建索引以提高查询性能
            connection.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_filter_rules_sync_status 
                ON filter_rules(sync_status)
            """))
            
            connection.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_filter_rules_last_sync_time 
                ON filter_rules(last_sync_time)
            """))
            
            connection.commit()
            logger.info("规则同步跟踪字段添加成功")
            
    except Exception as e:
        logger.error(f"添加规则同步跟踪字段失败: {e}")
        raise

def downgrade():
    """回滚规则同步跟踪字段"""
    try:
        with engine.connect() as connection:
            # 删除索引
            connection.execute(text("DROP INDEX IF EXISTS idx_filter_rules_sync_status"))
            connection.execute(text("DROP INDEX IF EXISTS idx_filter_rules_last_sync_time"))
            
            # SQLite不支持DROP COLUMN，需要重建表
            # 为简化，这里只是警告而不实际删除字段
            logger.warning("SQLite不支持删除字段，sync字段将保留但不使用")
            
            connection.commit()
            logger.info("规则同步跟踪字段回滚完成（字段保留）")
            
    except Exception as e:
        logger.error(f"回滚规则同步跟踪字段失败: {e}")
        raise

if __name__ == "__main__":
    upgrade()