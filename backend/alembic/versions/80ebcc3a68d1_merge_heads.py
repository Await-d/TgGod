"""Merge heads

Revision ID: 80ebcc3a68d1
Revises: f1a2b3c4d5e6, da3b11571a94
Create Date: 2025-07-24 22:07:23.583829

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '80ebcc3a68d1'
down_revision = ('f1a2b3c4d5e6', 'da3b11571a94')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass