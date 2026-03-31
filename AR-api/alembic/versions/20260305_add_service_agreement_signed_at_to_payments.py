"""add-service-agreement-signed-at-to-payments

Revision ID: 20260305_payment_signed_at
Revises: 20260304_cq_price_email
Create Date: 2026-03-05

"""
# pylint: disable=no-member
from alembic import op
import sqlalchemy as sa

revision = "20260305_payment_signed_at"
down_revision = "20260304_cq_price_email"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "payments",
        sa.Column("service_agreement_signed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("payments", "service_agreement_signed_at")
