"""add-renewal-suspension-fields-to-users

Revision ID: 20260319_renewal_suspend
Revises: 20260305_payment_signed_at
Create Date: 2026-03-19

"""
# pylint: disable=no-member
from alembic import op
import sqlalchemy as sa

revision = "20260319_renewal_suspend"
down_revision = "20260305_payment_signed_at"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("renewal_failed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("renewal_grace_ends_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "canto_access_suspended",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "canto_access_suspended")
    op.drop_column("users", "renewal_grace_ends_at")
    op.drop_column("users", "renewal_failed_at")
