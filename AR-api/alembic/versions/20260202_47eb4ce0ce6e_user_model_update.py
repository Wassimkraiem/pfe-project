"""user model update

Revision ID: 47eb4ce0ce6e
Revises: 20260201_initial
Create Date: 2026-02-02 14:19:49.707765

"""
from alembic import op
import sqlalchemy as sa


revision = '47eb4ce0ce6e'
down_revision = '20260201_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False))
    op.add_column('users', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'updated_at')
    op.drop_column('users', 'created_at')

