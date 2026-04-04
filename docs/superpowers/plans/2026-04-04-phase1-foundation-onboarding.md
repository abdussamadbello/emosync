# Phase 1: Foundation & Onboarding — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add all new database tables, user profile model, assessment scoring, onboarding API endpoints, onboarding wizard UI, and route protection so new users complete a structured intake before accessing the app.

**Architecture:** 7 new SQLAlchemy models with an Alembic migration. 3 new API route files (profile, assessments, mood) registered under `/api/v1`. Frontend onboarding wizard at `/onboarding` with 4 steps. Profile auto-created on registration. Route protection redirects incomplete users.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2.0 (async), Alembic, PostgreSQL, pytest-asyncio, Next.js 15 (App Router), Tailwind CSS, Shadcn/ui

**Spec:** `docs/superpowers/specs/2026-04-04-therapeutic-platform-expansion-design.md`

---

## File Structure

### Backend — New Files

| File | Responsibility |
|------|---------------|
| `backend/app/models/user_profile.py` | UserProfile ORM model |
| `backend/app/models/journal_entry.py` | JournalEntry ORM model |
| `backend/app/models/calendar_event.py` | CalendarEvent ORM model |
| `backend/app/models/assessment.py` | Assessment ORM model |
| `backend/app/models/treatment_plan.py` | TreatmentPlan + TreatmentGoal ORM models |
| `backend/app/models/mood_log.py` | MoodLog ORM model |
| `backend/alembic/versions/20260404_0004_therapeutic_tables.py` | Migration for all 7 tables |
| `backend/app/schemas/profile.py` | Pydantic schemas for profile endpoints |
| `backend/app/schemas/assessment.py` | Pydantic schemas for assessment endpoints |
| `backend/app/schemas/mood.py` | Pydantic schemas for mood endpoints |
| `backend/app/services/scoring.py` | PHQ-9 and GAD-7 scoring logic |
| `backend/app/api/v1/profile.py` | Profile API router (GET, PUT, complete-onboarding) |
| `backend/app/api/v1/assessments.py` | Assessment API router (POST, GET, GET latest) |
| `backend/app/api/v1/mood.py` | Mood API router (POST, GET) |
| `backend/tests/test_profile.py` | Profile endpoint tests |
| `backend/tests/test_assessments.py` | Assessment endpoint + scoring tests |
| `backend/tests/test_mood.py` | Mood endpoint tests |

### Backend — Modified Files

| File | Change |
|------|--------|
| `backend/app/models/__init__.py` | Export new models |
| `backend/app/models/user.py` | Add `profile` relationship |
| `backend/app/api/v1/router.py` | Include new routers |
| `backend/app/api/v1/auth.py` | Auto-create UserProfile on register |

### Frontend — New Files

| File | Responsibility |
|------|---------------|
| `frontend/app/onboarding/page.tsx` | Onboarding wizard (4 steps) |
| `frontend/lib/onboarding-api.ts` | API client for profile/assessment/mood endpoints |

### Frontend — Modified Files

| File | Change |
|------|--------|
| `frontend/lib/api.ts` | Add `get_profile` function |
| `frontend/app/layout.tsx` | No changes needed (onboarding is a standalone page) |
| `frontend/components/chat_view.tsx` | Add onboarding redirect check |

---

## Task 1: SQLAlchemy Models

**Files:**
- Create: `backend/app/models/user_profile.py`
- Create: `backend/app/models/journal_entry.py`
- Create: `backend/app/models/calendar_event.py`
- Create: `backend/app/models/assessment.py`
- Create: `backend/app/models/treatment_plan.py`
- Create: `backend/app/models/mood_log.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/models/user.py`

- [ ] **Step 1: Create UserProfile model**

Create `backend/app/models/user_profile.py`:

```python
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    grief_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    grief_subject: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    grief_duration_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    support_system: Mapped[str | None] = mapped_column(String(20), nullable=True)
    prior_therapy: Mapped[bool] = mapped_column(Boolean, default=False)
    preferred_approaches: Mapped[dict | None] = mapped_column(JSON, default=list)
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship("User", back_populates="profile")
```

- [ ] **Step 2: Create JournalEntry model**

Create `backend/app/models/journal_entry.py`:

```python
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.conversation import Conversation
    from app.models.user import User


class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str | None] = mapped_column(String(256), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    mood_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tags: Mapped[dict | None] = mapped_column(JSON, default=list)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship("User")
    conversation: Mapped[Conversation | None] = relationship("Conversation")
```

- [ ] **Step 3: Create CalendarEvent model**

Create `backend/app/models/calendar_event.py`:

```python
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class CalendarEvent(Base):
    __tablename__ = "calendar_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    event_type: Mapped[str] = mapped_column(String(20), nullable=False)
    recurrence: Mapped[str | None] = mapped_column(String(10), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    notify_agent: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship("User")
```

- [ ] **Step 4: Create Assessment model**

Create `backend/app/models/assessment.py`:

```python
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class Assessment(Base):
    __tablename__ = "assessments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    instrument: Mapped[str] = mapped_column(String(10), nullable=False)
    responses: Mapped[dict] = mapped_column(JSON, nullable=False)
    total_score: Mapped[int] = mapped_column(Integer, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="onboarding")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship("User")
```

- [ ] **Step 5: Create TreatmentPlan and TreatmentGoal models**

Create `backend/app/models/treatment_plan.py`:

```python
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class TreatmentPlan(Base):
    __tablename__ = "treatment_plans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship("User")
    goals: Mapped[list[TreatmentGoal]] = relationship(
        "TreatmentGoal", back_populates="plan", cascade="all, delete-orphan"
    )


class TreatmentGoal(Base):
    __tablename__ = "treatment_goals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("treatment_plans.id", ondelete="CASCADE"), nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="not_started")
    progress_notes: Mapped[dict | None] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    plan: Mapped[TreatmentPlan] = relationship("TreatmentPlan", back_populates="goals")
```

- [ ] **Step 6: Create MoodLog model**

Create `backend/app/models/mood_log.py`:

```python
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class MoodLog(Base):
    __tablename__ = "mood_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str | None] = mapped_column(String(30), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="check_in")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship("User")
```

- [ ] **Step 7: Update User model with profile relationship**

In `backend/app/models/user.py`, add inside the `if TYPE_CHECKING:` block:

```python
from app.models.user_profile import UserProfile
```

Add after the `conversations` relationship:

```python
profile: Mapped[UserProfile | None] = relationship("UserProfile", back_populates="user", uselist=False)
```

- [ ] **Step 8: Update models __init__.py**

Replace `backend/app/models/__init__.py` with:

```python
from app.models.base import Base
from app.models.assessment import Assessment
from app.models.calendar_event import CalendarEvent
from app.models.conversation import Conversation
from app.models.embedding_chunk import EmbeddingChunk
from app.models.journal_entry import JournalEntry
from app.models.message import Message
from app.models.mood_log import MoodLog
from app.models.treatment_plan import TreatmentGoal, TreatmentPlan
from app.models.user import User
from app.models.user_profile import UserProfile

__all__ = [
    "Base",
    "Assessment",
    "CalendarEvent",
    "Conversation",
    "EmbeddingChunk",
    "JournalEntry",
    "Message",
    "MoodLog",
    "TreatmentGoal",
    "TreatmentPlan",
    "User",
    "UserProfile",
]
```

- [ ] **Step 9: Commit models**

```bash
cd backend
git add app/models/user_profile.py app/models/journal_entry.py app/models/calendar_event.py app/models/assessment.py app/models/treatment_plan.py app/models/mood_log.py app/models/__init__.py app/models/user.py
git commit -m "feat: add SQLAlchemy models for therapeutic platform tables"
```

---

## Task 2: Alembic Migration

**Files:**
- Create: `backend/alembic/versions/20260404_0004_therapeutic_tables.py`

- [ ] **Step 1: Create migration file**

Create `backend/alembic/versions/20260404_0004_therapeutic_tables.py`:

```python
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
```

- [ ] **Step 2: Verify migration applies**

Run: `cd backend && uv run python -m alembic upgrade head`
Expected: Migration applies without errors.

- [ ] **Step 3: Verify downgrade works**

Run: `cd backend && uv run python -m alembic downgrade -1`
Expected: Tables dropped without errors.

Run: `cd backend && uv run python -m alembic upgrade head`
Expected: Tables recreated.

- [ ] **Step 4: Commit migration**

```bash
cd backend
git add alembic/versions/20260404_0004_therapeutic_tables.py
git commit -m "feat: add Alembic migration for therapeutic platform tables"
```

---

## Task 3: Assessment Scoring Logic

**Files:**
- Create: `backend/app/services/scoring.py`
- Create: `backend/tests/test_scoring.py`

- [ ] **Step 1: Write failing tests for scoring**

Create `backend/tests/test_scoring.py`:

```python
"""Tests for PHQ-9 and GAD-7 assessment scoring."""

from __future__ import annotations

import pytest

from app.services.scoring import score_assessment


def test_phq9_minimal() -> None:
    responses = {f"q{i}": 0 for i in range(1, 10)}
    total, severity = score_assessment("phq9", responses)
    assert total == 0
    assert severity == "minimal"


def test_phq9_mild() -> None:
    # Score = 7 → mild (5-9)
    responses = {f"q{i}": 0 for i in range(1, 10)}
    responses["q1"] = 3
    responses["q2"] = 2
    responses["q3"] = 2
    total, severity = score_assessment("phq9", responses)
    assert total == 7
    assert severity == "mild"


def test_phq9_moderate() -> None:
    # Score = 12 → moderate (10-14)
    responses = {f"q{i}": 1 for i in range(1, 10)}
    responses["q1"] = 3
    responses["q2"] = 2
    total, severity = score_assessment("phq9", responses)
    assert total == 12
    assert severity == "moderate"


def test_phq9_moderately_severe() -> None:
    # Score = 17 → moderately_severe (15-19)
    responses = {f"q{i}": 2 for i in range(1, 10)}
    responses["q9"] = 1
    total, severity = score_assessment("phq9", responses)
    assert total == 17
    assert severity == "moderately_severe"


def test_phq9_severe() -> None:
    responses = {f"q{i}": 3 for i in range(1, 10)}
    total, severity = score_assessment("phq9", responses)
    assert total == 27
    assert severity == "severe"


def test_gad7_minimal() -> None:
    responses = {f"q{i}": 0 for i in range(1, 8)}
    total, severity = score_assessment("gad7", responses)
    assert total == 0
    assert severity == "minimal"


def test_gad7_mild() -> None:
    responses = {f"q{i}": 1 for i in range(1, 8)}
    total, severity = score_assessment("gad7", responses)
    assert total == 7
    assert severity == "mild"


def test_gad7_moderate() -> None:
    responses = {f"q{i}": 2 for i in range(1, 8)}
    total, severity = score_assessment("gad7", responses)
    assert total == 14
    assert severity == "moderate"


def test_gad7_severe() -> None:
    responses = {f"q{i}": 3 for i in range(1, 8)}
    total, severity = score_assessment("gad7", responses)
    assert total == 21
    assert severity == "severe"


def test_unknown_instrument_raises() -> None:
    with pytest.raises(ValueError, match="Unknown instrument"):
        score_assessment("unknown", {"q1": 0})


def test_missing_question_raises() -> None:
    responses = {f"q{i}": 0 for i in range(1, 8)}  # only 7, PHQ-9 needs 9
    with pytest.raises(ValueError, match="Missing"):
        score_assessment("phq9", responses)


def test_invalid_score_raises() -> None:
    responses = {f"q{i}": 0 for i in range(1, 10)}
    responses["q1"] = 5  # out of range 0-3
    with pytest.raises(ValueError, match="out of range"):
        score_assessment("phq9", responses)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run python -m pytest tests/test_scoring.py -v`
Expected: All tests FAIL with `ModuleNotFoundError` or `ImportError`.

- [ ] **Step 3: Implement scoring logic**

Create `backend/app/services/scoring.py`:

```python
"""PHQ-9 and GAD-7 assessment scoring."""

from __future__ import annotations

_INSTRUMENTS: dict[str, tuple[int, list[tuple[int, str]]]] = {
    "phq9": (
        9,
        [
            (4, "minimal"),
            (9, "mild"),
            (14, "moderate"),
            (19, "moderately_severe"),
            (27, "severe"),
        ],
    ),
    "gad7": (
        7,
        [
            (4, "minimal"),
            (9, "mild"),
            (14, "moderate"),
            (21, "severe"),
        ],
    ),
}


def score_assessment(instrument: str, responses: dict[str, int]) -> tuple[int, str]:
    """Score an assessment and return (total_score, severity).

    Args:
        instrument: "phq9" or "gad7"
        responses: {"q1": 0, "q2": 1, ...} with values 0-3

    Returns:
        (total_score, severity_label)

    Raises:
        ValueError: if instrument unknown, questions missing, or scores out of range.
    """
    if instrument not in _INSTRUMENTS:
        raise ValueError(f"Unknown instrument: {instrument}")

    num_questions, thresholds = _INSTRUMENTS[instrument]
    expected_keys = {f"q{i}" for i in range(1, num_questions + 1)}
    missing = expected_keys - set(responses.keys())
    if missing:
        raise ValueError(f"Missing questions: {sorted(missing)}")

    total = 0
    for key in expected_keys:
        val = responses[key]
        if not isinstance(val, int) or val < 0 or val > 3:
            raise ValueError(f"{key} value {val} out of range (0-3)")
        total += val

    severity = thresholds[-1][1]  # default to highest
    for threshold, label in thresholds:
        if total <= threshold:
            severity = label
            break

    return total, severity
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run python -m pytest tests/test_scoring.py -v`
Expected: All 12 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/services/scoring.py tests/test_scoring.py
git commit -m "feat: add PHQ-9 and GAD-7 assessment scoring logic with tests"
```

---

## Task 4: Pydantic Schemas

**Files:**
- Create: `backend/app/schemas/profile.py`
- Create: `backend/app/schemas/assessment.py`
- Create: `backend/app/schemas/mood.py`

- [ ] **Step 1: Create profile schemas**

Create `backend/app/schemas/profile.py`:

```python
"""Pydantic models for user profile endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ProfileUpdate(BaseModel):
    grief_type: str | None = Field(default=None, max_length=50)
    grief_subject: str | None = Field(default=None, max_length=1024)
    grief_duration_months: int | None = Field(default=None, ge=0)
    support_system: str | None = Field(default=None, max_length=20)
    prior_therapy: bool | None = None
    preferred_approaches: list[str] | None = None


class ProfileOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    grief_type: str | None
    grief_subject: str | None
    grief_duration_months: int | None
    support_system: str | None
    prior_therapy: bool
    preferred_approaches: list[str] | None
    onboarding_completed: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 2: Create assessment schemas**

Create `backend/app/schemas/assessment.py`:

```python
"""Pydantic models for assessment endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class AssessmentCreate(BaseModel):
    instrument: str = Field(..., pattern=r"^(phq9|gad7)$")
    responses: dict[str, int] = Field(..., min_length=1)
    source: str = Field(default="onboarding", max_length=20)


class AssessmentOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    instrument: str
    responses: dict[str, int]
    total_score: int
    severity: str
    source: str
    created_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 3: Create mood schemas**

Create `backend/app/schemas/mood.py`:

```python
"""Pydantic models for mood log endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class MoodCreate(BaseModel):
    score: int = Field(..., ge=1, le=10)
    label: str | None = Field(default=None, max_length=30)
    notes: str | None = Field(default=None, max_length=2048)
    source: str = Field(default="check_in", max_length=20)


class MoodOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    score: int
    label: str | None
    notes: str | None
    source: str
    created_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 4: Commit schemas**

```bash
cd backend
git add app/schemas/profile.py app/schemas/assessment.py app/schemas/mood.py
git commit -m "feat: add Pydantic schemas for profile, assessment, and mood"
```

---

## Task 5: Profile API Endpoints

**Files:**
- Create: `backend/app/api/v1/profile.py`
- Create: `backend/tests/test_profile.py`
- Modify: `backend/app/api/v1/router.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_profile.py`:

```python
"""Tests for user profile endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, email: str = "profile@example.com") -> str:
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "secret1234"},
    )
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_get_profile_after_register(client: AsyncClient) -> None:
    token = await _register(client)
    r = await client.get(
        "/api/v1/profile/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["onboarding_completed"] is False
    assert data["grief_type"] is None


@pytest.mark.asyncio
async def test_update_profile(client: AsyncClient) -> None:
    token = await _register(client)
    r = await client.put(
        "/api/v1/profile/me",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "grief_type": "loss",
            "grief_subject": "my grandmother",
            "grief_duration_months": 6,
            "support_system": "some",
            "prior_therapy": True,
            "preferred_approaches": ["cbt", "journaling"],
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["grief_type"] == "loss"
    assert data["grief_subject"] == "my grandmother"
    assert data["grief_duration_months"] == 6
    assert data["support_system"] == "some"
    assert data["prior_therapy"] is True
    assert data["preferred_approaches"] == ["cbt", "journaling"]
    assert data["onboarding_completed"] is False


@pytest.mark.asyncio
async def test_complete_onboarding(client: AsyncClient) -> None:
    token = await _register(client)
    r = await client.post(
        "/api/v1/profile/complete-onboarding",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["onboarding_completed"] is True


@pytest.mark.asyncio
async def test_get_profile_unauthenticated(client: AsyncClient) -> None:
    r = await client.get("/api/v1/profile/me")
    assert r.status_code == 401
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run python -m pytest tests/test_profile.py -v`
Expected: FAIL — routes don't exist yet.

- [ ] **Step 3: Implement profile router**

Create `backend/app/api/v1/profile.py`:

```python
"""Profile endpoints: get, update, complete onboarding."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.user_profile import UserProfile
from app.schemas.profile import ProfileOut, ProfileUpdate

router = APIRouter(prefix="/profile", tags=["profile"])


async def _get_or_create_profile(user: User, db: AsyncSession) -> UserProfile:
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user.id)
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        profile = UserProfile(user_id=user.id)
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
    return profile


@router.get("/me", response_model=ProfileOut)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfile:
    return await _get_or_create_profile(current_user, db)


@router.put("/me", response_model=ProfileOut)
async def update_profile(
    body: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfile:
    profile = await _get_or_create_profile(current_user, db)
    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(profile, key, value)
    await db.commit()
    await db.refresh(profile)
    return profile


@router.post("/complete-onboarding", response_model=ProfileOut)
async def complete_onboarding(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfile:
    profile = await _get_or_create_profile(current_user, db)
    profile.onboarding_completed = True
    await db.commit()
    await db.refresh(profile)
    return profile
```

- [ ] **Step 4: Register profile router**

In `backend/app/api/v1/router.py`, add:

```python
from app.api.v1 import auth, chat, health, profile, voice

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(chat.router)
api_router.include_router(voice.router)
api_router.include_router(profile.router)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && uv run python -m pytest tests/test_profile.py -v`
Expected: All 4 tests PASS.

- [ ] **Step 6: Commit**

```bash
cd backend
git add app/api/v1/profile.py app/api/v1/router.py tests/test_profile.py
git commit -m "feat: add profile API endpoints (GET, PUT, complete-onboarding)"
```

---

## Task 6: Assessment API Endpoints

**Files:**
- Create: `backend/app/api/v1/assessments.py`
- Create: `backend/tests/test_assessments.py`
- Modify: `backend/app/api/v1/router.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_assessments.py`:

```python
"""Tests for assessment endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, email: str = "assess@example.com") -> str:
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "secret1234"},
    )
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_submit_phq9(client: AsyncClient) -> None:
    token = await _register(client)
    responses = {f"q{i}": 1 for i in range(1, 10)}  # score = 9 → mild
    r = await client.post(
        "/api/v1/assessments",
        headers={"Authorization": f"Bearer {token}"},
        json={"instrument": "phq9", "responses": responses, "source": "onboarding"},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["instrument"] == "phq9"
    assert data["total_score"] == 9
    assert data["severity"] == "mild"
    assert data["source"] == "onboarding"


@pytest.mark.asyncio
async def test_submit_gad7(client: AsyncClient) -> None:
    token = await _register(client)
    responses = {f"q{i}": 2 for i in range(1, 8)}  # score = 14 → moderate
    r = await client.post(
        "/api/v1/assessments",
        headers={"Authorization": f"Bearer {token}"},
        json={"instrument": "gad7", "responses": responses},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["total_score"] == 14
    assert data["severity"] == "moderate"


@pytest.mark.asyncio
async def test_submit_invalid_instrument(client: AsyncClient) -> None:
    token = await _register(client)
    r = await client.post(
        "/api/v1/assessments",
        headers={"Authorization": f"Bearer {token}"},
        json={"instrument": "invalid", "responses": {"q1": 0}},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_list_assessments(client: AsyncClient) -> None:
    token = await _register(client)
    responses = {f"q{i}": 0 for i in range(1, 10)}
    await client.post(
        "/api/v1/assessments",
        headers={"Authorization": f"Bearer {token}"},
        json={"instrument": "phq9", "responses": responses},
    )
    r = await client.get(
        "/api/v1/assessments",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["instrument"] == "phq9"


@pytest.mark.asyncio
async def test_get_latest_assessment(client: AsyncClient) -> None:
    token = await _register(client)
    # Submit two PHQ-9s
    for score_val in [0, 2]:
        responses = {f"q{i}": score_val for i in range(1, 10)}
        await client.post(
            "/api/v1/assessments",
            headers={"Authorization": f"Bearer {token}"},
            json={"instrument": "phq9", "responses": responses},
        )
    r = await client.get(
        "/api/v1/assessments/latest",
        headers={"Authorization": f"Bearer {token}"},
        params={"instrument": "phq9"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["total_score"] == 18  # second submission: 2*9 = 18


@pytest.mark.asyncio
async def test_get_latest_no_results(client: AsyncClient) -> None:
    token = await _register(client)
    r = await client.get(
        "/api/v1/assessments/latest",
        headers={"Authorization": f"Bearer {token}"},
        params={"instrument": "phq9"},
    )
    assert r.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run python -m pytest tests/test_assessments.py -v`
Expected: FAIL — routes don't exist.

- [ ] **Step 3: Implement assessment router**

Create `backend/app/api/v1/assessments.py`:

```python
"""Assessment endpoints: submit, list, get latest."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.assessment import Assessment
from app.models.user import User
from app.schemas.assessment import AssessmentCreate, AssessmentOut
from app.services.scoring import score_assessment

router = APIRouter(prefix="/assessments", tags=["assessments"])


@router.post("", response_model=AssessmentOut, status_code=status.HTTP_201_CREATED)
async def submit_assessment(
    body: AssessmentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Assessment:
    try:
        total_score, severity = score_assessment(body.instrument, body.responses)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    assessment = Assessment(
        user_id=current_user.id,
        instrument=body.instrument,
        responses=body.responses,
        total_score=total_score,
        severity=severity,
        source=body.source,
    )
    db.add(assessment)
    await db.commit()
    await db.refresh(assessment)
    return assessment


@router.get("", response_model=list[AssessmentOut])
async def list_assessments(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Assessment]:
    result = await db.execute(
        select(Assessment)
        .where(Assessment.user_id == current_user.id)
        .order_by(Assessment.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/latest", response_model=AssessmentOut)
async def get_latest_assessment(
    instrument: str = Query(..., pattern=r"^(phq9|gad7)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Assessment:
    result = await db.execute(
        select(Assessment)
        .where(Assessment.user_id == current_user.id, Assessment.instrument == instrument)
        .order_by(Assessment.created_at.desc())
        .limit(1)
    )
    assessment = result.scalar_one_or_none()
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No {instrument} assessment found.",
        )
    return assessment
```

- [ ] **Step 4: Register assessment router**

In `backend/app/api/v1/router.py`, add the import and include:

```python
from app.api.v1 import assessments, auth, chat, health, profile, voice

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(chat.router)
api_router.include_router(voice.router)
api_router.include_router(profile.router)
api_router.include_router(assessments.router)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && uv run python -m pytest tests/test_assessments.py -v`
Expected: All 6 tests PASS.

- [ ] **Step 6: Commit**

```bash
cd backend
git add app/api/v1/assessments.py app/api/v1/router.py tests/test_assessments.py
git commit -m "feat: add assessment API endpoints (submit, list, get latest)"
```

---

## Task 7: Mood API Endpoints

**Files:**
- Create: `backend/app/api/v1/mood.py`
- Create: `backend/tests/test_mood.py`
- Modify: `backend/app/api/v1/router.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_mood.py`:

```python
"""Tests for mood log endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, email: str = "mood@example.com") -> str:
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "secret1234"},
    )
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_log_mood(client: AsyncClient) -> None:
    token = await _register(client)
    r = await client.post(
        "/api/v1/mood",
        headers={"Authorization": f"Bearer {token}"},
        json={"score": 7, "label": "hopeful", "source": "onboarding"},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["score"] == 7
    assert data["label"] == "hopeful"
    assert data["source"] == "onboarding"


@pytest.mark.asyncio
async def test_log_mood_minimal(client: AsyncClient) -> None:
    token = await _register(client)
    r = await client.post(
        "/api/v1/mood",
        headers={"Authorization": f"Bearer {token}"},
        json={"score": 3},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["score"] == 3
    assert data["label"] is None
    assert data["source"] == "check_in"


@pytest.mark.asyncio
async def test_log_mood_invalid_score(client: AsyncClient) -> None:
    token = await _register(client)
    r = await client.post(
        "/api/v1/mood",
        headers={"Authorization": f"Bearer {token}"},
        json={"score": 11},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_list_moods(client: AsyncClient) -> None:
    token = await _register(client)
    for score in [3, 5, 7]:
        await client.post(
            "/api/v1/mood",
            headers={"Authorization": f"Bearer {token}"},
            json={"score": score},
        )
    r = await client.get(
        "/api/v1/mood",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 3
    # Most recent first
    assert data[0]["score"] == 7
    assert data[2]["score"] == 3
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run python -m pytest tests/test_mood.py -v`
Expected: FAIL — routes don't exist.

- [ ] **Step 3: Implement mood router**

Create `backend/app/api/v1/mood.py`:

```python
"""Mood log endpoints: create and list."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.mood_log import MoodLog
from app.models.user import User
from app.schemas.mood import MoodCreate, MoodOut

router = APIRouter(prefix="/mood", tags=["mood"])


@router.post("", response_model=MoodOut, status_code=status.HTTP_201_CREATED)
async def log_mood(
    body: MoodCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MoodLog:
    mood = MoodLog(
        user_id=current_user.id,
        score=body.score,
        label=body.label,
        notes=body.notes,
        source=body.source,
    )
    db.add(mood)
    await db.commit()
    await db.refresh(mood)
    return mood


@router.get("", response_model=list[MoodOut])
async def list_moods(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MoodLog]:
    result = await db.execute(
        select(MoodLog)
        .where(MoodLog.user_id == current_user.id)
        .order_by(MoodLog.created_at.desc())
    )
    return list(result.scalars().all())
```

- [ ] **Step 4: Register mood router**

In `backend/app/api/v1/router.py`:

```python
from app.api.v1 import assessments, auth, chat, health, mood, profile, voice

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(chat.router)
api_router.include_router(voice.router)
api_router.include_router(profile.router)
api_router.include_router(assessments.router)
api_router.include_router(mood.router)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && uv run python -m pytest tests/test_mood.py -v`
Expected: All 4 tests PASS.

- [ ] **Step 6: Commit**

```bash
cd backend
git add app/api/v1/mood.py app/api/v1/router.py tests/test_mood.py
git commit -m "feat: add mood log API endpoints (create, list)"
```

---

## Task 8: Auto-Create Profile on Registration

**Files:**
- Modify: `backend/app/api/v1/auth.py`
- Modify: `backend/tests/test_profile.py`

- [ ] **Step 1: Write a test that verifies profile exists after registration**

Add to `backend/tests/test_profile.py`:

```python
@pytest.mark.asyncio
async def test_profile_auto_created_on_register(client: AsyncClient) -> None:
    """Profile should exist immediately after registration without explicit creation."""
    token = await _register(client, email="auto@example.com")
    r = await client.get(
        "/api/v1/profile/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["onboarding_completed"] is False
    assert data["user_id"] is not None
```

- [ ] **Step 2: Run to confirm it passes**

This already passes because `_get_or_create_profile` creates on first GET. But we want eager creation at registration time so the profile row is guaranteed to exist.

Run: `cd backend && uv run python -m pytest tests/test_profile.py -v`
Expected: All 5 tests PASS.

- [ ] **Step 3: Add profile creation to registration endpoint**

In `backend/app/api/v1/auth.py`, add import:

```python
from app.models.user_profile import UserProfile
```

After `await db.refresh(user)` in the `register` function, add:

```python
    profile = UserProfile(user_id=user.id)
    db.add(profile)
    await db.commit()
```

- [ ] **Step 4: Run all profile and auth tests**

Run: `cd backend && uv run python -m pytest tests/test_profile.py tests/test_auth.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/api/v1/auth.py tests/test_profile.py
git commit -m "feat: auto-create user profile on registration"
```

---

## Task 9: Run Full Backend Test Suite

- [ ] **Step 1: Run all tests to verify nothing is broken**

Run: `cd backend && uv run python -m pytest -v`
Expected: All existing + new tests PASS.

- [ ] **Step 2: Fix any failures if needed**

If any existing tests fail due to new model imports or DB schema changes, fix them.

- [ ] **Step 3: Commit any fixes**

```bash
cd backend
git add -u
git commit -m "fix: resolve test compatibility with new therapeutic models"
```

---

## Task 10: Frontend Onboarding API Client

**Files:**
- Create: `frontend/lib/onboarding-api.ts`
- Modify: `frontend/lib/api.ts`

- [ ] **Step 1: Add get_profile to api.ts**

In `frontend/lib/api.ts`, add the interface and function:

```typescript
/** Shape of the user profile response */
export interface UserProfile {
  id: string;
  user_id: string;
  grief_type: string | null;
  grief_subject: string | null;
  grief_duration_months: number | null;
  support_system: string | null;
  prior_therapy: boolean;
  preferred_approaches: string[] | null;
  onboarding_completed: boolean;
  created_at: string;
  updated_at: string;
}

/**
 * Fetches the current user's profile.
 */
export async function get_profile(token: string): Promise<UserProfile> {
  const res = await fetch(`${API_BASE}/api/v1/profile/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!res.ok) {
    handle_auth_error(res);
    throw new Error(`Failed to fetch profile (${res.status})`);
  }

  return res.json() as Promise<UserProfile>;
}
```

- [ ] **Step 2: Create onboarding-api.ts**

Create `frontend/lib/onboarding-api.ts`:

```typescript
/**
 * API client for onboarding-related endpoints.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface ProfileUpdate {
  grief_type?: string;
  grief_subject?: string;
  grief_duration_months?: number;
  support_system?: string;
  prior_therapy?: boolean;
  preferred_approaches?: string[];
}

interface AssessmentSubmission {
  instrument: "phq9" | "gad7";
  responses: Record<string, number>;
  source: string;
}

interface AssessmentResult {
  id: string;
  instrument: string;
  total_score: number;
  severity: string;
  source: string;
  created_at: string;
}

interface MoodSubmission {
  score: number;
  label?: string;
  source: string;
}

function auth_headers(token: string): Record<string, string> {
  return {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
  };
}

export async function update_profile(
  token: string,
  data: ProfileUpdate
): Promise<void> {
  const res = await fetch(`${API_BASE}/api/v1/profile/me`, {
    method: "PUT",
    headers: auth_headers(token),
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Profile update failed (${res.status})`);
}

export async function submit_assessment(
  token: string,
  data: AssessmentSubmission
): Promise<AssessmentResult> {
  const res = await fetch(`${API_BASE}/api/v1/assessments`, {
    method: "POST",
    headers: auth_headers(token),
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Assessment submit failed (${res.status})`);
  return res.json() as Promise<AssessmentResult>;
}

export async function log_mood(
  token: string,
  data: MoodSubmission
): Promise<void> {
  const res = await fetch(`${API_BASE}/api/v1/mood`, {
    method: "POST",
    headers: auth_headers(token),
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Mood log failed (${res.status})`);
}

export async function complete_onboarding(token: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/v1/profile/complete-onboarding`, {
    method: "POST",
    headers: auth_headers(token),
  });
  if (!res.ok) throw new Error(`Complete onboarding failed (${res.status})`);
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/api.ts frontend/lib/onboarding-api.ts
git commit -m "feat: add frontend API client for onboarding endpoints"
```

---

## Task 11: Onboarding Wizard Page

**Files:**
- Create: `frontend/app/onboarding/page.tsx`

This is a single-page wizard with 4 steps managed by local state. Each step submits data to the backend before advancing.

- [ ] **Step 1: Create the onboarding page**

Create `frontend/app/onboarding/page.tsx`:

```tsx
"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { ChevronRight, ChevronLeft, Sparkles } from "lucide-react";
import { get_token, get_profile } from "@/lib/api";
import {
  update_profile,
  submit_assessment,
  log_mood,
  complete_onboarding,
} from "@/lib/onboarding-api";

/* ------------------------------------------------------------------ */
/*  PHQ-9 Questions                                                    */
/* ------------------------------------------------------------------ */
const PHQ9_QUESTIONS = [
  "Little interest or pleasure in doing things",
  "Feeling down, depressed, or hopeless",
  "Trouble falling or staying asleep, or sleeping too much",
  "Feeling tired or having little energy",
  "Poor appetite or overeating",
  "Feeling bad about yourself — or that you are a failure",
  "Trouble concentrating on things",
  "Moving or speaking slowly, or being fidgety/restless",
  "Thoughts that you would be better off dead, or of hurting yourself",
];

/* ------------------------------------------------------------------ */
/*  GAD-7 Questions                                                    */
/* ------------------------------------------------------------------ */
const GAD7_QUESTIONS = [
  "Feeling nervous, anxious, or on edge",
  "Not being able to stop or control worrying",
  "Worrying too much about different things",
  "Trouble relaxing",
  "Being so restless that it's hard to sit still",
  "Becoming easily annoyed or irritable",
  "Feeling afraid, as if something awful might happen",
];

const ANSWER_OPTIONS = [
  { value: 0, label: "Not at all" },
  { value: 1, label: "Several days" },
  { value: 2, label: "More than half the days" },
  { value: 3, label: "Nearly every day" },
];

const EMOTION_LABELS = [
  "anxious",
  "sad",
  "numb",
  "hopeful",
  "calm",
  "angry",
  "other",
];

/* ================================================================== */
/*  Main Component                                                     */
/* ================================================================== */
export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [is_loading, setIsLoading] = useState(false);
  const [is_checking, setIsChecking] = useState(true);
  const [error, setError] = useState("");
  const [token, setToken] = useState("");

  // Step 1 state
  const [grief_type, setGriefType] = useState("");
  const [grief_subject, setGriefSubject] = useState("");
  const [grief_duration, setGriefDuration] = useState<number | null>(null);

  // Step 2 state
  const [support_system, setSupportSystem] = useState("");
  const [prior_therapy, setPriorTherapy] = useState(false);
  const [preferred_approaches, setPreferredApproaches] = useState<string[]>([]);

  // Step 3 state
  const [phq9_responses, setPhq9Responses] = useState<Record<string, number>>({});
  const [gad7_responses, setGad7Responses] = useState<Record<string, number>>({});
  const [phq9_result, setPhq9Result] = useState<{ total_score: number; severity: string } | null>(null);
  const [gad7_result, setGad7Result] = useState<{ total_score: number; severity: string } | null>(null);

  // Step 4 state
  const [mood_score, setMoodScore] = useState(5);
  const [mood_label, setMoodLabel] = useState("");

  /* ---- Auth check on mount ---- */
  useEffect(() => {
    const t = get_token();
    if (!t) {
      router.replace("/auth/login");
      return;
    }
    setToken(t);
    get_profile(t)
      .then((profile) => {
        if (profile.onboarding_completed) {
          router.replace("/");
        } else {
          setIsChecking(false);
        }
      })
      .catch(() => {
        router.replace("/auth/login");
      });
  }, [router]);

  if (is_checking) return null;

  /* ---- Step handlers ---- */

  async function handle_step1_next() {
    if (!grief_type) {
      setError("Please select what brings you here.");
      return;
    }
    setIsLoading(true);
    setError("");
    try {
      await update_profile(token, {
        grief_type,
        grief_subject: grief_subject || undefined,
        grief_duration_months: grief_duration ?? undefined,
      });
      setStep(2);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to save.");
    } finally {
      setIsLoading(false);
    }
  }

  async function handle_step2_next() {
    if (!support_system) {
      setError("Please select your support level.");
      return;
    }
    setIsLoading(true);
    setError("");
    try {
      await update_profile(token, {
        support_system,
        prior_therapy,
        preferred_approaches,
      });
      setStep(3);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to save.");
    } finally {
      setIsLoading(false);
    }
  }

  async function handle_step3_next() {
    const phq9_complete = PHQ9_QUESTIONS.every((_, i) => `q${i + 1}` in phq9_responses);
    const gad7_complete = GAD7_QUESTIONS.every((_, i) => `q${i + 1}` in gad7_responses);
    if (!phq9_complete || !gad7_complete) {
      setError("Please answer all questions before continuing.");
      return;
    }
    setIsLoading(true);
    setError("");
    try {
      const [phq9, gad7] = await Promise.all([
        submit_assessment(token, {
          instrument: "phq9",
          responses: phq9_responses,
          source: "onboarding",
        }),
        submit_assessment(token, {
          instrument: "gad7",
          responses: gad7_responses,
          source: "onboarding",
        }),
      ]);
      setPhq9Result({ total_score: phq9.total_score, severity: phq9.severity });
      setGad7Result({ total_score: gad7.total_score, severity: gad7.severity });
      setStep(4);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to submit assessments.");
    } finally {
      setIsLoading(false);
    }
  }

  async function handle_finish() {
    setIsLoading(true);
    setError("");
    try {
      await log_mood(token, {
        score: mood_score,
        label: mood_label || undefined,
        source: "onboarding",
      });
      await complete_onboarding(token);
      router.push("/");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to complete onboarding.");
    } finally {
      setIsLoading(false);
    }
  }

  /* ---- Toggle approach helper ---- */
  function toggle_approach(approach: string) {
    setPreferredApproaches((prev) =>
      prev.includes(approach)
        ? prev.filter((a) => a !== approach)
        : [...prev, approach]
    );
  }

  /* ---- Render ---- */
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4 py-12">
      <div className="w-full max-w-lg">
        {/* Header */}
        <div className="mb-8 flex flex-col items-center gap-3">
          <Link href="/" className="flex items-center gap-2.5">
            <Image src="/logo.png" alt="EmoSync" width={36} height={36} className="rounded-sm" />
            <span className="text-xl font-semibold tracking-tight">EmoSync</span>
          </Link>
          <p className="text-sm text-muted-foreground">
            Step {step} of 4
          </p>
          {/* Progress bar */}
          <div className="flex w-full max-w-xs gap-1.5">
            {[1, 2, 3, 4].map((s) => (
              <div
                key={s}
                className={`h-1.5 flex-1 rounded-full transition-colors ${
                  s <= step ? "bg-primary" : "bg-muted"
                }`}
              />
            ))}
          </div>
        </div>

        {/* Card */}
        <div className="rounded-xl border border-border bg-card p-6 shadow-sm">
          {error && (
            <p className="mb-4 rounded-lg bg-destructive/10 px-3 py-2 text-xs text-destructive">
              {error}
            </p>
          )}

          {/* ---- STEP 1: Welcome ---- */}
          {step === 1 && (
            <div className="flex flex-col gap-5">
              <div>
                <h2 className="text-lg font-semibold">What brings you to EmoSync?</h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  This helps us understand how to support you best.
                </p>
              </div>

              <div className="flex flex-col gap-2">
                {[
                  { value: "loss", label: "Loss of someone" },
                  { value: "breakup", label: "Breakup or divorce" },
                  { value: "life_transition", label: "Life transition" },
                  { value: "other", label: "Something else" },
                ].map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => setGriefType(opt.value)}
                    className={`rounded-lg border px-4 py-3 text-left text-sm transition-colors ${
                      grief_type === opt.value
                        ? "border-primary bg-primary/5 font-medium"
                        : "border-border hover:border-primary/50"
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium text-foreground">
                  Would you like to share more? <span className="text-muted-foreground">(optional)</span>
                </label>
                <textarea
                  value={grief_subject}
                  onChange={(e) => setGriefSubject(e.target.value)}
                  placeholder="e.g., my grandmother, a relationship..."
                  rows={2}
                  className="rounded-lg border border-input bg-transparent px-3 py-2 text-sm outline-none placeholder:text-muted-foreground focus:border-ring focus:ring-2 focus:ring-ring/30"
                />
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium text-foreground">
                  How long ago? <span className="text-muted-foreground">(optional)</span>
                </label>
                <div className="flex flex-wrap gap-2">
                  {[
                    { value: 0, label: "Less than 1 month" },
                    { value: 2, label: "1–3 months" },
                    { value: 5, label: "3–6 months" },
                    { value: 9, label: "6–12 months" },
                    { value: 18, label: "1–2 years" },
                    { value: 30, label: "2+ years" },
                  ].map((opt) => (
                    <button
                      key={opt.value}
                      type="button"
                      onClick={() => setGriefDuration(opt.value)}
                      className={`rounded-full border px-3 py-1 text-xs transition-colors ${
                        grief_duration === opt.value
                          ? "border-primary bg-primary/5 font-medium"
                          : "border-border hover:border-primary/50"
                      }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>

              <Button onClick={handle_step1_next} disabled={is_loading} className="w-full">
                {is_loading ? "Saving…" : "Continue"}
                {!is_loading && <ChevronRight className="ml-1 size-4" />}
              </Button>
            </div>
          )}

          {/* ---- STEP 2: Support ---- */}
          {step === 2 && (
            <div className="flex flex-col gap-5">
              <div>
                <h2 className="text-lg font-semibold">Your support & preferences</h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  We&apos;ll tailor our approach to what works for you.
                </p>
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium">Do you have people you can talk to?</label>
                <div className="flex flex-col gap-2">
                  {[
                    { value: "strong", label: "I have strong support" },
                    { value: "some", label: "Some support" },
                    { value: "none", label: "Not much support" },
                  ].map((opt) => (
                    <button
                      key={opt.value}
                      type="button"
                      onClick={() => setSupportSystem(opt.value)}
                      className={`rounded-lg border px-4 py-3 text-left text-sm transition-colors ${
                        support_system === opt.value
                          ? "border-primary bg-primary/5 font-medium"
                          : "border-border hover:border-primary/50"
                      }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="flex items-center justify-between">
                <label className="text-sm font-medium">Have you done therapy before?</label>
                <button
                  type="button"
                  onClick={() => setPriorTherapy(!prior_therapy)}
                  className={`relative h-6 w-11 rounded-full transition-colors ${
                    prior_therapy ? "bg-primary" : "bg-muted"
                  }`}
                >
                  <span
                    className={`absolute left-0.5 top-0.5 size-5 rounded-full bg-white transition-transform ${
                      prior_therapy ? "translate-x-5" : ""
                    }`}
                  />
                </button>
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium">What sounds helpful?</label>
                <div className="flex flex-wrap gap-2">
                  {["Journaling", "CBT exercises", "Mindfulness", "Just talking", "Guided prompts"].map(
                    (approach) => (
                      <button
                        key={approach}
                        type="button"
                        onClick={() => toggle_approach(approach.toLowerCase())}
                        className={`rounded-full border px-3 py-1.5 text-xs transition-colors ${
                          preferred_approaches.includes(approach.toLowerCase())
                            ? "border-primary bg-primary/5 font-medium"
                            : "border-border hover:border-primary/50"
                        }`}
                      >
                        {approach}
                      </button>
                    )
                  )}
                </div>
              </div>

              <div className="flex gap-3">
                <Button variant="outline" onClick={() => setStep(1)} className="flex-1">
                  <ChevronLeft className="mr-1 size-4" /> Back
                </Button>
                <Button onClick={handle_step2_next} disabled={is_loading} className="flex-1">
                  {is_loading ? "Saving…" : "Continue"}
                  {!is_loading && <ChevronRight className="ml-1 size-4" />}
                </Button>
              </div>
            </div>
          )}

          {/* ---- STEP 3: Assessments ---- */}
          {step === 3 && (
            <div className="flex flex-col gap-5">
              <div>
                <h2 className="text-lg font-semibold">Quick check-in</h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  Over the last 2 weeks, how often have you been bothered by the following?
                </p>
              </div>

              {/* PHQ-9 */}
              <div className="flex flex-col gap-3">
                <h3 className="text-sm font-medium text-muted-foreground">Part 1 of 2 — Mood</h3>
                {PHQ9_QUESTIONS.map((q, i) => (
                  <div key={`phq9-${i}`} className="flex flex-col gap-1.5">
                    <p className="text-sm">{q}</p>
                    <div className="flex gap-1">
                      {ANSWER_OPTIONS.map((opt) => (
                        <button
                          key={opt.value}
                          type="button"
                          onClick={() =>
                            setPhq9Responses((prev) => ({ ...prev, [`q${i + 1}`]: opt.value }))
                          }
                          className={`flex-1 rounded border px-1 py-1.5 text-xs transition-colors ${
                            phq9_responses[`q${i + 1}`] === opt.value
                              ? "border-primary bg-primary/10 font-medium"
                              : "border-border hover:border-primary/50"
                          }`}
                        >
                          {opt.label}
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>

              {/* GAD-7 */}
              <div className="flex flex-col gap-3">
                <h3 className="text-sm font-medium text-muted-foreground">Part 2 of 2 — Anxiety</h3>
                {GAD7_QUESTIONS.map((q, i) => (
                  <div key={`gad7-${i}`} className="flex flex-col gap-1.5">
                    <p className="text-sm">{q}</p>
                    <div className="flex gap-1">
                      {ANSWER_OPTIONS.map((opt) => (
                        <button
                          key={opt.value}
                          type="button"
                          onClick={() =>
                            setGad7Responses((prev) => ({ ...prev, [`q${i + 1}`]: opt.value }))
                          }
                          className={`flex-1 rounded border px-1 py-1.5 text-xs transition-colors ${
                            gad7_responses[`q${i + 1}`] === opt.value
                              ? "border-primary bg-primary/10 font-medium"
                              : "border-border hover:border-primary/50"
                          }`}
                        >
                          {opt.label}
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>

              <div className="flex gap-3">
                <Button variant="outline" onClick={() => setStep(2)} className="flex-1">
                  <ChevronLeft className="mr-1 size-4" /> Back
                </Button>
                <Button onClick={handle_step3_next} disabled={is_loading} className="flex-1">
                  {is_loading ? "Submitting…" : "Continue"}
                  {!is_loading && <ChevronRight className="ml-1 size-4" />}
                </Button>
              </div>
            </div>
          )}

          {/* ---- STEP 4: Summary ---- */}
          {step === 4 && (
            <div className="flex flex-col gap-5">
              <div>
                <h2 className="text-lg font-semibold">How are you feeling right now?</h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  One last check before we begin.
                </p>
              </div>

              {/* Mood slider */}
              <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span>Very low</span>
                  <span className="text-lg font-semibold text-foreground">{mood_score}</span>
                  <span>Very good</span>
                </div>
                <input
                  type="range"
                  min={1}
                  max={10}
                  value={mood_score}
                  onChange={(e) => setMoodScore(Number(e.target.value))}
                  className="w-full accent-primary"
                />
              </div>

              {/* Emotion label */}
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium">
                  What word fits? <span className="text-muted-foreground">(optional)</span>
                </label>
                <div className="flex flex-wrap gap-2">
                  {EMOTION_LABELS.map((label) => (
                    <button
                      key={label}
                      type="button"
                      onClick={() => setMoodLabel(mood_label === label ? "" : label)}
                      className={`rounded-full border px-3 py-1 text-xs transition-colors ${
                        mood_label === label
                          ? "border-primary bg-primary/5 font-medium"
                          : "border-border hover:border-primary/50"
                      }`}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Summary card */}
              <div className="rounded-lg bg-muted/50 p-4 text-sm">
                <h3 className="mb-2 font-medium">Here&apos;s what I know about you</h3>
                <ul className="flex flex-col gap-1 text-muted-foreground">
                  <li>Reason: <span className="text-foreground">{grief_type.replace("_", " ")}</span></li>
                  <li>Support: <span className="text-foreground">{support_system}</span></li>
                  {phq9_result && (
                    <li>
                      PHQ-9: <span className="text-foreground">{phq9_result.total_score}/27 ({phq9_result.severity.replace("_", " ")})</span>
                    </li>
                  )}
                  {gad7_result && (
                    <li>
                      GAD-7: <span className="text-foreground">{gad7_result.total_score}/21 ({gad7_result.severity})</span>
                    </li>
                  )}
                </ul>
              </div>

              <div className="flex gap-3">
                <Button variant="outline" onClick={() => setStep(3)} className="flex-1">
                  <ChevronLeft className="mr-1 size-4" /> Back
                </Button>
                <Button onClick={handle_finish} disabled={is_loading} className="flex-1">
                  {is_loading ? (
                    <span className="flex items-center gap-2">
                      <Sparkles className="size-4 animate-spin" />
                      Starting…
                    </span>
                  ) : (
                    "Start your first conversation"
                  )}
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify the page renders**

Run the frontend dev server: `cd frontend && npm run dev`
Navigate to `http://localhost:3000/onboarding` — the wizard should render Step 1.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/onboarding/page.tsx
git commit -m "feat: add onboarding wizard page (4-step intake flow)"
```

---

## Task 12: Route Protection (Onboarding Redirect)

**Files:**
- Modify: `frontend/components/chat_view.tsx`
- Modify: `frontend/app/auth/login/page.tsx`

- [ ] **Step 1: Add onboarding redirect to chat_view.tsx**

In `frontend/components/chat_view.tsx`, in the existing `useEffect` that checks auth on mount (the one that calls `get_token()` and `get_current_user()`), add a profile check after the user is loaded:

After the existing `get_current_user(token)` call succeeds, add:

```typescript
import { get_profile } from "@/lib/api";

// Inside the existing auth useEffect, after get_current_user succeeds:
const profile = await get_profile(token);
if (!profile.onboarding_completed) {
  router.replace("/onboarding");
  return;
}
```

- [ ] **Step 2: Redirect to onboarding after login if not completed**

In `frontend/app/auth/login/page.tsx`, in the `handle_submit` function, after the user is fetched and display name is saved, add a profile check:

```typescript
import { get_profile } from "@/lib/api";

// After save_display_name(user.display_name ?? user.email):
const profile = await get_profile(access_token);
if (!profile.onboarding_completed) {
  router.push("/onboarding");
} else {
  router.push("/");
}
```

Replace the existing `router.push("/")` at the end of `handle_submit` with the above conditional.

- [ ] **Step 3: Do the same in register page**

In `frontend/app/auth/register/page.tsx`, after successful registration and token save, redirect to `/onboarding` instead of `/`:

Replace `router.push("/")` with `router.push("/onboarding")`.

- [ ] **Step 4: Verify the flow manually**

1. Register a new user → should redirect to `/onboarding`
2. Complete onboarding → should redirect to `/`
3. Login again → should go to `/` (onboarding already completed)
4. Visit `/onboarding` with completed profile → should redirect to `/`

- [ ] **Step 5: Commit**

```bash
git add frontend/components/chat_view.tsx frontend/app/auth/login/page.tsx frontend/app/auth/register/page.tsx
git commit -m "feat: add onboarding route protection (redirect if not completed)"
```

---

## Task 13: Final Integration Test

- [ ] **Step 1: Run full backend test suite**

Run: `cd backend && uv run python -m pytest -v`
Expected: All tests PASS (existing + scoring + profile + assessment + mood).

- [ ] **Step 2: Run linter**

Run: `cd backend && uv run ruff check .`
Expected: No errors.

- [ ] **Step 3: Verify migration chain**

Run: `cd backend && uv run python -m alembic check`
Expected: No pending migrations.

- [ ] **Step 4: Manual E2E test**

Start the stack: `make up`
1. Register → redirected to `/onboarding`
2. Complete all 4 steps → redirected to `/`
3. Chat works normally
4. Login again → goes straight to `/` (onboarding completed)

- [ ] **Step 5: Final commit if any fixes needed**

```bash
git add -u
git commit -m "fix: resolve integration issues from Phase 1 onboarding"
```
