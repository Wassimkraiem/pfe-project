"""add pre-payment reminder tracking fields

Revision ID: 20260216_pre_pay_reminder
Revises: 20260216_email_reminder
Create Date: 2026-02-16

"""
from alembic import op
import sqlalchemy as sa

revision = "20260216_pre_pay_reminder"
down_revision = "20260216_email_reminder"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "onboarding_sessions",
        sa.Column("pre_payment_email_sent_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "onboarding_sessions",
        sa.Column(
            "pre_payment_email_sent_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )


def downgrade() -> None:
    op.drop_column("onboarding_sessions", "pre_payment_email_sent_count")
    op.drop_column("onboarding_sessions", "pre_payment_email_sent_at")
