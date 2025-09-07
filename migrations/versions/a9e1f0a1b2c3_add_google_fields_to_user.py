"""add google fields to user

Revision ID: a9e1f0a1b2c3
Revises: d7c9a1e2add3
Create Date: 2025-09-07 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a9e1f0a1b2c3'
down_revision = 'd7c9a1e2add3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('user') as batch_op:
        batch_op.add_column(sa.Column('google_sub', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('avatar_url', sa.String(), nullable=True))
        batch_op.create_unique_constraint('uq_user_google_sub', ['google_sub'])


def downgrade() -> None:
    try:
        with op.batch_alter_table('user') as batch_op:
            try:
                batch_op.drop_constraint('uq_user_google_sub', type_='unique')
            except Exception:
                pass
            try:
                batch_op.drop_column('avatar_url')
            except Exception:
                pass
            try:
                batch_op.drop_column('google_sub')
            except Exception:
                pass
    except Exception:
        pass


