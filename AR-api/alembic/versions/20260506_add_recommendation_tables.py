"""add recommendation tables

Revision ID: 20260506_recommendations
Revises: 20260506_downloaded_videos
Create Date: 2026-05-06

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260506_recommendations"
down_revision = "20260506_downloaded_videos"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_interest_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "category_weights",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "tag_weights",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "entity_weights",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_user_interest_profile_user_id"),
    )
    op.create_index(op.f("ix_user_interest_profiles_id"), "user_interest_profiles", ["id"], unique=False)
    op.create_index(op.f("ix_user_interest_profiles_user_id"), "user_interest_profiles", ["user_id"], unique=False)

    op.create_table(
        "user_search_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("query", sa.String(), nullable=False),
        sa.Column(
            "parsed_intent",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_search_events_id"), "user_search_events", ["id"], unique=False)
    op.create_index(op.f("ix_user_search_events_user_id"), "user_search_events", ["user_id"], unique=False)

    op.create_table(
        "user_video_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("video_id", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column(
            "event_context",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_video_events_id"), "user_video_events", ["id"], unique=False)
    op.create_index(op.f("ix_user_video_events_user_id"), "user_video_events", ["user_id"], unique=False)
    op.create_index(op.f("ix_user_video_events_video_id"), "user_video_events", ["video_id"], unique=False)
    op.create_index(op.f("ix_user_video_events_event_type"), "user_video_events", ["event_type"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_user_video_events_event_type"), table_name="user_video_events")
    op.drop_index(op.f("ix_user_video_events_video_id"), table_name="user_video_events")
    op.drop_index(op.f("ix_user_video_events_user_id"), table_name="user_video_events")
    op.drop_index(op.f("ix_user_video_events_id"), table_name="user_video_events")
    op.drop_table("user_video_events")

    op.drop_index(op.f("ix_user_search_events_user_id"), table_name="user_search_events")
    op.drop_index(op.f("ix_user_search_events_id"), table_name="user_search_events")
    op.drop_table("user_search_events")

    op.drop_index(op.f("ix_user_interest_profiles_user_id"), table_name="user_interest_profiles")
    op.drop_index(op.f("ix_user_interest_profiles_id"), table_name="user_interest_profiles")
    op.drop_table("user_interest_profiles")
