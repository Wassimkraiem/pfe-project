"""add customer_id to payments

Revision ID: 20260223_add_payment_customer_id
Revises: 20260219_pay_email
Create Date: 2026-02-23

"""
from alembic import op
import sqlalchemy as sa

revision = "20260223_add_payment_customer_id"
down_revision = "20260219_pay_email"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "payments",
        sa.Column("customer_id", sa.String(), nullable=True),
    )
    op.create_index(
        op.f("ix_payments_customer_id"),
        "payments",
        ["customer_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_payments_customer_id"), table_name="payments")
    op.drop_column("payments", "customer_id")
