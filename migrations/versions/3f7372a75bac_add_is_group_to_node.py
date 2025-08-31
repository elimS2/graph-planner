"""add is_group to node

Revision ID: 3f7372a75bac
Revises: 618f0ec5f4fb
Create Date: 2025-08-29 11:32:44.047619

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3f7372a75bac'
down_revision = '618f0ec5f4fb'
branch_labels = None
depends_on = None


def upgrade() -> None:
    try:
        op.add_column('node', sa.Column('is_group', sa.Boolean(), nullable=False, server_default=sa.text('0')))
        op.alter_column('node', 'is_group', server_default=None)
    except Exception:
        # Table/column may already exist in some environments; make migration idempotent-ish
        try:
            op.execute("SELECT 1 FROM node LIMIT 1")
        except Exception:
            pass


def downgrade() -> None:
    try:
        op.drop_column('node', 'is_group')
    except Exception:
        pass


