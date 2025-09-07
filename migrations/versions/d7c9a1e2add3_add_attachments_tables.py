"""add attachments tables

Revision ID: d7c9a1e2add3
Revises: 3f7372a75bac
Create Date: 2025-09-07 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd7c9a1e2add3'
down_revision = '3f7372a75bac'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # attachment table
    op.create_table(
        'attachment',
        sa.Column('id', sa.String(), primary_key=True, nullable=False),
        sa.Column('created_at', sa.String(), nullable=False),
        sa.Column('updated_at', sa.String(), nullable=False),
        sa.Column('uploader_user_id', sa.String(), sa.ForeignKey('user.id', ondelete=None), nullable=False),
        sa.Column('mime_type', sa.String(), nullable=False),
        sa.Column('kind', sa.String(), nullable=False),
        sa.Column('original_name', sa.String(), nullable=True),
        sa.Column('storage_path', sa.String(), nullable=False),
        sa.Column('size_bytes', sa.Integer(), nullable=True),
        sa.Column('width', sa.Integer(), nullable=True),
        sa.Column('height', sa.Integer(), nullable=True),
        sa.Column('checksum_sha256', sa.String(), nullable=True),
        sa.Column('meta_json', sa.Text(), nullable=True),
        sa.UniqueConstraint('storage_path', name='uq_attachment_storage_path'),
        sa.UniqueConstraint('checksum_sha256', name='uq_attachment_checksum'),
    )

    # bridge table comment_attachment
    op.create_table(
        'comment_attachment',
        sa.Column('comment_id', sa.String(), sa.ForeignKey('comment.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('attachment_id', sa.String(), sa.ForeignKey('attachment.id', ondelete='CASCADE'), primary_key=True),
    )


def downgrade() -> None:
    try:
        op.drop_table('comment_attachment')
    except Exception:
        pass
    try:
        op.drop_table('attachment')
    except Exception:
        pass


