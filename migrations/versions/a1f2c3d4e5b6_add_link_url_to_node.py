"""add link_url to node

Revision ID: a1f2c3d4e5b6
Revises: 3f7372a75bac
Create Date: 2025-08-31 00:00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1f2c3d4e5b6'
down_revision = '3f7372a75bac'
branch_labels = None
depends_on = None


def upgrade() -> None:
    try:
        op.add_column('node', sa.Column('link_url', sa.String(), nullable=True))
    except Exception:
        # Make tolerant if column already exists
        pass


def downgrade() -> None:
    try:
        op.drop_column('node', 'link_url')
    except Exception:
        pass


