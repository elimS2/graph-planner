"""add link_open_in_new_tab to node

Revision ID: b2c3d4e5f6a7
Revises: a1f2c3d4e5b6
Create Date: 2025-08-31 00:00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6a7'
down_revision = 'a1f2c3d4e5b6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    try:
        op.add_column('node', sa.Column('link_open_in_new_tab', sa.Boolean(), nullable=False, server_default=sa.text('1')))
        op.alter_column('node', 'link_open_in_new_tab', server_default=None)
    except Exception:
        pass


def downgrade() -> None:
    try:
        op.drop_column('node', 'link_open_in_new_tab')
    except Exception:
        pass


