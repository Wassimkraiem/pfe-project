"""add is_custom_quote to onboarding_sessions

Revision ID: 20260213_is_custom
Revises: 66e0e13a4fa3
Create Date: 2026-02-13

"""
from alembic import op
import sqlalchemy as sa

revision = "20260213_is_custom"
down_revision = "66e0e13a4fa3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "onboarding_sessions",
        sa.Column(
            "is_custom_quote",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("onboarding_sessions", "is_custom_quote")
