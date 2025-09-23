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
    """回滚规则同步跟踪字段 - 使用表重建策略"""
    try:
        from backend.app.core.sqlite_migration_manager import SQLiteMigrationManager
        from sqlalchemy import inspect

        # 创建迁移管理器
        migration_manager = SQLiteMigrationManager(engine.url)

        logger.info("🔄 开始回滚规则同步跟踪字段...")

        with engine.connect() as connection:
            # 删除索引
            try:
                connection.execute(text("DROP INDEX IF EXISTS idx_filter_rules_sync_status"))
                connection.execute(text("DROP INDEX IF EXISTS idx_filter_rules_last_sync_time"))
                logger.info("✅ 索引删除成功")
            except Exception as e:
                logger.warning(f"⚠️ 删除索引时出现问题: {e}")

            # 使用迁移管理器删除列
            columns_to_drop = [
                'last_sync_time',
                'last_sync_message_count',
                'sync_status',
                'needs_full_resync'
            ]

            # 检查列是否存在
            inspector = inspect(engine)
            existing_columns = [col['name'] for col in inspector.get_columns('filter_rules')]
            actual_columns_to_drop = [col for col in columns_to_drop if col in existing_columns]

            if actual_columns_to_drop:
                logger.info(f"🗑️ 准备删除列: {', '.join(actual_columns_to_drop)}")

                success = migration_manager.rebuild_table_drop_columns(
                    'filter_rules',
                    actual_columns_to_drop
                )

                if success:
                    logger.info("✅ 规则同步跟踪字段回滚完成")
                else:
                    raise Exception("表重建失败")
            else:
                logger.info("ℹ️ 没有找到需要删除的同步跟踪字段")

            connection.commit()

    except Exception as e:
        logger.error(f"❌ 回滚规则同步跟踪字段失败: {e}")
        raise

if __name__ == "__main__":
    upgrade()