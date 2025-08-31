"""add is_hidden to node

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2025-08-31 00:10:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c3d4e5f6a7b8'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    try:
        op.add_column('node', sa.Column('is_hidden', sa.Boolean(), nullable=False, server_default=sa.text('0')))
        # Remove server_default to match application default handling
        op.alter_column('node', 'is_hidden', server_default=None)
    except Exception:
        # Be resilient if column already exists or DB lacks table (older envs)
        pass


def downgrade() -> None:
    try:
        op.drop_column('node', 'is_hidden')
    except Exception:
        pass


