"""Add data initialization support

Revision ID: 20250920_data_init
Revises: da3b11571a94
Create Date: 2025-09-20 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = '20250920_data_init'
down_revision = 'da3b11571a94'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """升级数据库模式以支持数据初始化功能"""
    
    # 创建数据初始化日志表
    op.create_table(
        'data_initialization_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('migration_id', sa.String(32), nullable=False),
        sa.Column('initialization_type', sa.String(50), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('progress_percentage', sa.Float(), default=0.0),
        sa.Column('items_processed', sa.Integer(), default=0),
        sa.Column('items_successful', sa.Integer(), default=0),
        sa.Column('items_failed', sa.Integer(), default=0),
        sa.Column('current_phase', sa.String(100), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('config_data', sa.JSON(), nullable=True),
        sa.Column('result_data', sa.JSON(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_migration_id', 'migration_id'),
        sa.Index('idx_initialization_type', 'initialization_type'),
        sa.Index('idx_status', 'status'),
        sa.Index('idx_started_at', 'started_at')
    )
    
    # 添加数据源追踪字段到telegram_groups表
    with op.batch_alter_table('telegram_groups', schema=None) as batch_op:
        batch_op.add_column(sa.Column('data_source', sa.String(50), nullable=True, default='telegram_api'))
        batch_op.add_column(sa.Column('import_batch_id', sa.String(32), nullable=True))
        batch_op.add_column(sa.Column('data_quality_score', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('last_data_sync', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('sync_metadata', sa.JSON(), nullable=True))
    
    # 添加数据源追踪字段到telegram_messages表
    with op.batch_alter_table('telegram_messages', schema=None) as batch_op:
        batch_op.add_column(sa.Column('data_source', sa.String(50), nullable=True, default='telegram_api'))
        batch_op.add_column(sa.Column('import_batch_id', sa.String(32), nullable=True))
        batch_op.add_column(sa.Column('data_validation_status', sa.String(20), nullable=True, default='valid'))
        batch_op.add_column(sa.Column('validation_errors', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('source_file_path', sa.String(500), nullable=True))
        batch_op.add_column(sa.Column('original_message_data', sa.JSON(), nullable=True))
    
    # 创建索引以提高查询性能
    op.create_index('idx_groups_data_source', 'telegram_groups', ['data_source'])
    op.create_index('idx_groups_import_batch', 'telegram_groups', ['import_batch_id'])
    op.create_index('idx_groups_last_sync', 'telegram_groups', ['last_data_sync'])
    
    op.create_index('idx_messages_data_source', 'telegram_messages', ['data_source'])
    op.create_index('idx_messages_import_batch', 'telegram_messages', ['import_batch_id'])
    op.create_index('idx_messages_validation_status', 'telegram_messages', ['data_validation_status'])


def downgrade() -> None:
    """降级数据库模式"""
    
    # 删除索引
    op.drop_index('idx_messages_validation_status', table_name='telegram_messages')
    op.drop_index('idx_messages_import_batch', table_name='telegram_messages')
    op.drop_index('idx_messages_data_source', table_name='telegram_messages')
    
    op.drop_index('idx_groups_last_sync', table_name='telegram_groups')
    op.drop_index('idx_groups_import_batch', table_name='telegram_groups')
    op.drop_index('idx_groups_data_source', table_name='telegram_groups')
    
    # 从telegram_messages表删除字段
    with op.batch_alter_table('telegram_messages', schema=None) as batch_op:
        batch_op.drop_column('original_message_data')
        batch_op.drop_column('source_file_path')
        batch_op.drop_column('validation_errors')
        batch_op.drop_column('data_validation_status')
        batch_op.drop_column('import_batch_id')
        batch_op.drop_column('data_source')
    
    # 从telegram_groups表删除字段
    with op.batch_alter_table('telegram_groups', schema=None) as batch_op:
        batch_op.drop_column('sync_metadata')
        batch_op.drop_column('last_data_sync')
        batch_op.drop_column('data_quality_score')
        batch_op.drop_column('import_batch_id')
        batch_op.drop_column('data_source')
    
    # 删除数据初始化日志表
    op.drop_table('data_initialization_logs')