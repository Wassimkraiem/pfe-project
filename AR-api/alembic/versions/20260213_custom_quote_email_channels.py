"""remove user_id, add email and channels to custom_quotes

Revision ID: 20260213_cq_email
Revises: 20260213_is_custom
Create Date: 2026-02-13

"""
from alembic import op
import sqlalchemy as sa

revision = "20260213_cq_email"
down_revision = "20260213_is_custom"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Clear existing rows (breaking change: custom quotes now use email+channels)
    op.execute("DELETE FROM custom_quotes")
    op.drop_constraint(
        "custom_quotes_user_id_fkey",
        "custom_quotes",
        type_="foreignkey",
    )
    op.drop_index(op.f("ix_custom_quotes_user_id"), table_name="custom_quotes")
    op.drop_column("custom_quotes", "user_id")
    op.add_column(
        "custom_quotes",
        sa.Column("email", sa.String(), nullable=False),
    )
    op.add_column(
        "custom_quotes",
        sa.Column("channels", sa.JSON(), nullable=False),
    )
    op.create_index(
        op.f("ix_custom_quotes_email"),
        "custom_quotes",
        ["email"],
        unique=False,
    )


def downgrade() -> None:
    op.execute("DELETE FROM custom_quotes")
    op.drop_index(op.f("ix_custom_quotes_email"), table_name="custom_quotes")
    op.drop_column("custom_quotes", "channels")
    op.drop_column("custom_quotes", "email")
    op.add_column(
        "custom_quotes",
        sa.Column("user_id", sa.Integer(), nullable=False),
    )
    op.create_foreign_key(
        "custom_quotes_user_id_fkey",
        "custom_quotes",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        op.f("ix_custom_quotes_user_id"),
        "custom_quotes",
        ["user_id"],
        unique=False,
    )
