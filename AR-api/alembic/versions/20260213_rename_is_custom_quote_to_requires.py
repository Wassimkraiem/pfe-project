"""rename is_custom_quote to requires_custom_quote

Revision ID: 20260213_rename_cq
Revises: 20260213_cq_email
Create Date: 2026-02-13

"""
from alembic import op

revision = "20260213_rename_cq"
down_revision = "20260213_cq_email"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "onboarding_sessions",
        "is_custom_quote",
        new_column_name="requires_custom_quote",
    )


def downgrade() -> None:
    op.alter_column(
        "onboarding_sessions",
        "requires_custom_quote",
        new_column_name="is_custom_quote",
    )
