"""add download progress fields

Revision ID: f1a2b3c4d5e6
Revises: ef08cb95a96a
Create Date: 2025-01-20 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'f1a2b3c4d5e6'
down_revision = 'ef08cb95a96a'
branch_labels = None
depends_on = None


def upgrade():
    """Add download progress fields to telegram_messages table"""
    # 添加下载进度相关字段
    op.add_column('telegram_messages', sa.Column('download_progress', sa.Integer(), default=0))
    op.add_column('telegram_messages', sa.Column('downloaded_size', sa.BigInteger(), default=0))
    op.add_column('telegram_messages', sa.Column('download_speed', sa.Integer(), default=0))
    op.add_column('telegram_messages', sa.Column('estimated_time_remaining', sa.Integer(), default=0))
    op.add_column('telegram_messages', sa.Column('download_started_at', sa.DateTime(timezone=True), nullable=True))


def downgrade():
    """Remove download progress fields from telegram_messages table"""
    op.drop_column('telegram_messages', 'download_started_at')
    op.drop_column('telegram_messages', 'estimated_time_remaining')
    op.drop_column('telegram_messages', 'download_speed')
    op.drop_column('telegram_messages', 'downloaded_size')
    op.drop_column('telegram_messages', 'download_progress')