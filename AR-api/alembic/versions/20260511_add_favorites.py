"""add user favorites table

Revision ID: 20260511_favorites
Revises: 20260506_recommendations
Create Date: 2026-05-11

"""

from alembic import op
import sqlalchemy as sa


revision = "20260511_favorites"
down_revision = "20260506_recommendations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_favorites",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("video_id", sa.String(length=255), nullable=False),
        sa.Column("video_title", sa.String(length=500), nullable=True),
        sa.Column("thumbnail_url", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "video_id", name="uq_user_favorite"),
    )
    op.create_index(op.f("ix_user_favorites_id"), "user_favorites", ["id"], unique=False)
    op.create_index(
        op.f("ix_user_favorites_user_id"), "user_favorites", ["user_id"], unique=False
    )
    op.create_index(
        op.f("ix_user_favorites_video_id"), "user_favorites", ["video_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_user_favorites_video_id"), table_name="user_favorites")
    op.drop_index(op.f("ix_user_favorites_user_id"), table_name="user_favorites")
    op.drop_index(op.f("ix_user_favorites_id"), table_name="user_favorites")
    op.drop_table("user_favorites")
