"""add payload column to conversation_messages

Revision ID: 20260331_conv_msg_payload
Revises: 20260330_playlists_subs
Create Date: 2026-03-31

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260331_conv_msg_payload"
down_revision = "20260330_playlists_subs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "conversation_messages",
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("conversation_messages", "payload")
