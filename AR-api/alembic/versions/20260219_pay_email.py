"""add payment_email to onboarding sessions

Revision ID: 20260219_pay_email
Revises: 20260218_onboarding_email
Create Date: 2026-02-19

"""
from alembic import op
import sqlalchemy as sa

revision = "20260219_pay_email"
down_revision = "20260218_onboarding_email"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "onboarding_sessions",
        sa.Column("payment_email", sa.String(), nullable=True),
    )
    op.create_index(
        op.f("ix_onboarding_sessions_payment_email"),
        "onboarding_sessions",
        ["payment_email"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_onboarding_sessions_payment_email"),
        table_name="onboarding_sessions",
    )
    op.drop_column("onboarding_sessions", "payment_email")
