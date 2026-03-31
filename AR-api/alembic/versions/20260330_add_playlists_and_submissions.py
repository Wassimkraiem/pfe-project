"""add playlists, playlist_videos, and video_submissions tables

Revision ID: 20260330_playlists_subs
Revises: 20260330_conversations
Create Date: 2026-03-30

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260330_playlists_subs"
down_revision = "20260330_conversations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "playlists",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_playlists_id"), "playlists", ["id"], unique=False)
    op.create_index(
        op.f("ix_playlists_user_id"), "playlists", ["user_id"], unique=False
    )

    op.create_table(
        "playlist_videos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("playlist_id", sa.Integer(), nullable=False),
        sa.Column("video_id", sa.String(255), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["playlist_id"], ["playlists.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("playlist_id", "video_id", name="uq_playlist_video"),
    )
    op.create_index(
        op.f("ix_playlist_videos_id"), "playlist_videos", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_playlist_videos_playlist_id"),
        "playlist_videos",
        ["playlist_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_playlist_videos_video_id"),
        "playlist_videos",
        ["video_id"],
        unique=False,
    )

    submissionstatus_enum = postgresql.ENUM(
        "pending", "approved", "rejected",
        name="submissionstatus",
        create_type=False,
    )
    submissionstatus_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "video_submissions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("video_url", sa.String(2048), nullable=False),
        sa.Column("tags", postgresql.JSONB(), nullable=True),
        sa.Column("category", sa.String(255), nullable=True),
        sa.Column(
            "status",
            submissionstatus_enum,
            nullable=False,
            server_default="pending",
        ),
        sa.Column("admin_notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_video_submissions_id"),
        "video_submissions",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_video_submissions_user_id"),
        "video_submissions",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_video_submissions_user_id"), table_name="video_submissions"
    )
    op.drop_index(
        op.f("ix_video_submissions_id"), table_name="video_submissions"
    )
    op.drop_table("video_submissions")

    op.drop_index(
        op.f("ix_playlist_videos_video_id"), table_name="playlist_videos"
    )
    op.drop_index(
        op.f("ix_playlist_videos_playlist_id"), table_name="playlist_videos"
    )
    op.drop_index(
        op.f("ix_playlist_videos_id"), table_name="playlist_videos"
    )
    op.drop_table("playlist_videos")

    op.drop_index(op.f("ix_playlists_user_id"), table_name="playlists")
    op.drop_index(op.f("ix_playlists_id"), table_name="playlists")
    op.drop_table("playlists")

    op.execute("DROP TYPE IF EXISTS submissionstatus")
