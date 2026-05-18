"""add downloaded_videos table

Revision ID: 20260506_downloaded_videos
Revises: 20260331_conv_msg_payload
Create Date: 2026-05-06

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260506_downloaded_videos"
down_revision = "20260331_conv_msg_payload"
branch_labels = None
depends_on = None


def upgrade() -> None:
    scope_enum = postgresql.ENUM(
        "browse",
        "detail",
        name="cantodownloadsourcescope",
        create_type=False,
    )
    scope_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "downloaded_videos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("video_id", sa.String(), nullable=False),
        sa.Column("video_title", sa.String(), nullable=False),
        sa.Column("thumbnail_url", sa.String(), nullable=True),
        sa.Column("source_scope", scope_enum, nullable=False),
        sa.Column(
            "request_filters",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "downloaded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_downloaded_videos_id"), "downloaded_videos", ["id"], unique=False)
    op.create_index(op.f("ix_downloaded_videos_user_id"), "downloaded_videos", ["user_id"], unique=False)
    op.create_index(op.f("ix_downloaded_videos_video_id"), "downloaded_videos", ["video_id"], unique=False)
    op.create_index(
        op.f("ix_downloaded_videos_downloaded_at"),
        "downloaded_videos",
        ["downloaded_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_downloaded_videos_downloaded_at"), table_name="downloaded_videos")
    op.drop_index(op.f("ix_downloaded_videos_video_id"), table_name="downloaded_videos")
    op.drop_index(op.f("ix_downloaded_videos_user_id"), table_name="downloaded_videos")
    op.drop_index(op.f("ix_downloaded_videos_id"), table_name="downloaded_videos")
    op.drop_table("downloaded_videos")

    op.execute("DROP TYPE IF EXISTS cantodownloadsourcescope")
