"""add body_html to comment

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2025-09-03 00:00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd4e5f6a7b8c9'
down_revision = 'c3d4e5f6a7b8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    try:
        op.add_column('comment', sa.Column('body_html', sa.Text(), nullable=True))
    except Exception:
        # Be resilient if the column already exists
        pass


def downgrade() -> None:
    try:
        op.drop_column('comment', 'body_html')
    except Exception:
        pass


