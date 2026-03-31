"""add onboarding emails and reminder tracking

Revision ID: 20260218_onboarding_email
Revises: 20260218_payment_signature
Create Date: 2026-02-18

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260218_onboarding_email"
down_revision = "20260218_payment_signature"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "onboarding_emails",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("onboarding_session_id", sa.Integer(), nullable=False),
        sa.Column("recipient_email", sa.String(), nullable=False),
        sa.Column(
            "email_code",
            sa.Enum(
                "PRE_PAYMENT_REMINDER",
                "ACCOUNT_SETUP_REMINDER",
                "ALREADY_PAID_ONBOARDING",
                "CUSTOM_QUOTE_REQUEST",
                "PAYMENT_CONFIRMATION",
                name="onboardingemailcode",
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("QUEUED", "SENT", "FAILED", name="emailstatus"),
            nullable=False,
            server_default=sa.text("'SENT'"),
        ),
        sa.Column("sent_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["onboarding_session_id"], ["onboarding_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_onboarding_emails_onboarding_session_id"),
        "onboarding_emails",
        ["onboarding_session_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_onboarding_emails_recipient_email"),
        "onboarding_emails",
        ["recipient_email"],
        unique=False,
    )
    op.create_index(
        op.f("ix_onboarding_emails_email_code"),
        "onboarding_emails",
        ["email_code"],
        unique=False,
    )
    op.create_index(
        op.f("ix_onboarding_emails_id"),
        "onboarding_emails",
        ["id"],
        unique=False,
    )

    op.add_column(
        "onboarding_sessions",
        sa.Column("last_reminder_sent_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "onboarding_sessions",
        sa.Column(
            "reminders_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )

    op.drop_column("onboarding_sessions", "email_sent_count")
    op.drop_column("onboarding_sessions", "email_sent_at")
    op.drop_column("onboarding_sessions", "pre_payment_email_sent_count")
    op.drop_column("onboarding_sessions", "pre_payment_email_sent_at")


def downgrade() -> None:
    op.add_column(
        "onboarding_sessions",
        sa.Column("pre_payment_email_sent_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "onboarding_sessions",
        sa.Column(
            "pre_payment_email_sent_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "onboarding_sessions",
        sa.Column("email_sent_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "onboarding_sessions",
        sa.Column(
            "email_sent_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )

    op.drop_column("onboarding_sessions", "reminders_count")
    op.drop_column("onboarding_sessions", "last_reminder_sent_at")

    op.drop_index(op.f("ix_onboarding_emails_id"), table_name="onboarding_emails")
    op.drop_index(op.f("ix_onboarding_emails_email_code"), table_name="onboarding_emails")
    op.drop_index(op.f("ix_onboarding_emails_recipient_email"), table_name="onboarding_emails")
    op.drop_index(op.f("ix_onboarding_emails_onboarding_session_id"), table_name="onboarding_emails")
    op.drop_table("onboarding_emails")

    op.execute("DROP TYPE IF EXISTS emailstatus")
    op.execute("DROP TYPE IF EXISTS onboardingemailcode")
