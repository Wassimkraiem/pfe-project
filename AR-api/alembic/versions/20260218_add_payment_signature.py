"""add signature to payments

Revision ID: 20260218_payment_signature
Revises: 20260216_pre_pay_reminder
Create Date: 2026-02-18

"""
from alembic import op
import sqlalchemy as sa

revision = "20260218_payment_signature"
down_revision = "20260216_pre_pay_reminder"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "payments",
        sa.Column("signature", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("payments", "signature")
