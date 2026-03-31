"""add CUSTOM_QUOTE_PRICE_SUBMITTED to onboardingemailcode enum

Revision ID: 20260304_cq_price_email
Revises: f33d29b9cd8b
Create Date: 2026-03-04

"""
from alembic import op

revision = "20260304_cq_price_email"
down_revision = "f33d29b9cd8b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE onboardingemailcode ADD VALUE 'CUSTOM_QUOTE_PRICE_SUBMITTED'"
    )


def downgrade() -> None:
    # PostgreSQL does not support removing enum values; would require recreating the type
    pass
