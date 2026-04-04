"""add therapeutic platform tables

Revision ID: 0004_therapeutic
Revises: 0003_vector_index
Create Date: 2026-04-04

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSON, UUID

revision: str = "0004_therapeutic"
down_revision: Union[str, None] = "0003_vector_index"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_profiles",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("grief_type", sa.String(50), nullable=True),
        sa.Column("grief_subject", sa.String(1024), nullable=True),
        sa.Column("grief_duration_months", sa.Integer, nullable=True),
        sa.Column("support_system", sa.String(20), nullable=True),
        sa.Column("prior_therapy", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("preferred_approaches", JSON, nullable=True, server_default=sa.text("'[]'::json")),
        sa.Column("onboarding_completed", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )

    op.create_table(
        "journal_entries",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(256), nullable=True),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("mood_score", sa.Integer, nullable=True),
        sa.Column("tags", JSON, nullable=True, server_default=sa.text("'[]'::json")),
        sa.Column("source", sa.String(20), nullable=False, server_default=sa.text("'manual'")),
        sa.Column("conversation_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_journal_entries_user_id", "journal_entries", ["user_id"])

    op.create_table(
        "calendar_events",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("event_type", sa.String(20), nullable=False),
        sa.Column("recurrence", sa.String(10), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("notify_agent", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_calendar_events_user_id", "calendar_events", ["user_id"])

    op.create_table(
        "assessments",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("instrument", sa.String(10), nullable=False),
        sa.Column("responses", JSON, nullable=False),
        sa.Column("total_score", sa.Integer, nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("source", sa.String(20), nullable=False, server_default=sa.text("'onboarding'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_assessments_user_id", "assessments", ["user_id"])

    op.create_table(
        "treatment_plans",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'active'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_treatment_plans_user_id", "treatment_plans", ["user_id"])

    op.create_table(
        "treatment_goals",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("plan_id", UUID(as_uuid=True), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("target_date", sa.Date, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'not_started'")),
        sa.Column("progress_notes", JSON, nullable=True, server_default=sa.text("'[]'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["plan_id"], ["treatment_plans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "mood_logs",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("score", sa.Integer, nullable=False),
        sa.Column("label", sa.String(30), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("source", sa.String(20), nullable=False, server_default=sa.text("'check_in'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_mood_logs_user_id", "mood_logs", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_mood_logs_user_id", table_name="mood_logs")
    op.drop_table("mood_logs")
    op.drop_table("treatment_goals")
    op.drop_index("ix_treatment_plans_user_id", table_name="treatment_plans")
    op.drop_table("treatment_plans")
    op.drop_index("ix_assessments_user_id", table_name="assessments")
    op.drop_table("assessments")
    op.drop_index("ix_calendar_events_user_id", table_name="calendar_events")
    op.drop_table("calendar_events")
    op.drop_index("ix_journal_entries_user_id", table_name="journal_entries")
    op.drop_table("journal_entries")
    op.drop_table("user_profiles")
