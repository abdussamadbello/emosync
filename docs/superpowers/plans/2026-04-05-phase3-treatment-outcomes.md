# Phase 3: Treatment Plans & Outcomes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add treatment plan + goal CRUD, mood trend endpoint, therapeutic context repository for the Historian, expand all three agent nodes with assessment/plan/mood awareness, implement `[suggest:...]` tags in chat, and build the treatment plan frontend page.

**Architecture:** Treatment plans and goals are standard CRUD endpoints. A `therapeutic_context.py` service provides the Historian with direct DB reads for profile, assessments, plans, and moods. The Specialist's prompt is expanded to reference treatment goals and emit `[suggest:...]` tags. The Anchor gains score-aware escalation. The frontend parses suggest tags into action buttons.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2.0 (async), pytest-asyncio, Next.js 15 (App Router), Tailwind CSS

**Spec:** `docs/superpowers/specs/2026-04-04-therapeutic-platform-expansion-design.md` (Sections 6, 7.3, 8)

---

## File Structure

### Backend — New Files

| File | Responsibility |
|------|---------------|
| `backend/app/schemas/treatment.py` | Pydantic schemas for plans + goals |
| `backend/app/api/v1/plans.py` | Treatment plan + goal CRUD router |
| `backend/app/services/therapeutic_context.py` | Direct DB reads for Historian (profile, assessments, plans, moods) |
| `backend/tests/test_plans.py` | Treatment plan + goal endpoint tests |
| `backend/tests/test_therapeutic_context.py` | Therapeutic context service tests |
| `frontend/app/plan/page.tsx` | Treatment plan page |
| `frontend/lib/plan-api.ts` | Frontend plan API client |

### Backend — Modified Files

| File | Change |
|------|--------|
| `backend/app/api/v1/router.py` | Include plans router |
| `backend/app/api/v1/mood.py` | Add GET /mood/trend endpoint |
| `backend/app/schemas/mood.py` | Add MoodTrend schema |
| `backend/app/agent/state.py` | Add new fields (user_profile, assessment_context, etc.) |
| `backend/app/agent/nodes/historian.py` | Load therapeutic context via direct DB |
| `backend/app/agent/nodes/specialist.py` | Reference plans/moods, emit suggest tags |
| `backend/app/agent/nodes/anchor.py` | Score-aware escalation |
| `backend/app/agent/prompts.py` | Expand system prompts |
| `backend/app/services/chat_turn.py` | Pass user_id into agent state |

### Frontend — Modified Files

| File | Change |
|------|--------|
| `frontend/components/chat_view.tsx` | Parse [suggest:...] tags, render action buttons |
| `frontend/components/sidebar.tsx` | Add My Plan link |

---

## Task 1: Treatment Plan Pydantic Schemas

**Files:**
- Create: `backend/app/schemas/treatment.py`

- [ ] **Step 1: Create schemas**

Create `backend/app/schemas/treatment.py`:

```python
"""Pydantic models for treatment plan and goal endpoints."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class GoalCreate(BaseModel):
    description: str = Field(..., min_length=1, max_length=2000)
    target_date: date | None = None
    status: str = Field(default="not_started", pattern=r"^(not_started|in_progress|completed)$")


class GoalUpdate(BaseModel):
    description: str | None = Field(default=None, min_length=1, max_length=2000)
    target_date: date | None = None
    status: str | None = Field(default=None, pattern=r"^(not_started|in_progress|completed)$")
    progress_note: str | None = Field(default=None, max_length=2000)


class GoalOut(BaseModel):
    id: uuid.UUID
    plan_id: uuid.UUID
    description: str
    target_date: date | None
    status: str
    progress_notes: list | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PlanCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=256)


class PlanUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=256)
    status: str | None = Field(default=None, pattern=r"^(active|completed|paused)$")


class PlanOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    status: str
    created_at: datetime
    updated_at: datetime
    goals: list[GoalOut] = []

    model_config = {"from_attributes": True}
```

- [ ] **Step 2: Commit**

```bash
cd backend && git add app/schemas/treatment.py && git commit -m "feat: add Pydantic schemas for treatment plans and goals"
```

---

## Task 2: Treatment Plan + Goal CRUD Endpoints

**Files:**
- Create: `backend/app/api/v1/plans.py`
- Create: `backend/tests/test_plans.py`
- Modify: `backend/app/api/v1/router.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_plans.py`:

```python
"""Tests for treatment plan and goal endpoints."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient) -> str:
    email = f"plan_{uuid.uuid4().hex[:8]}@example.com"
    r = await client.post("/api/v1/auth/register", json={"email": email, "password": "secret1234"})
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_create_plan(client: AsyncClient) -> None:
    token = await _register(client)
    r = await client.post(
        "/api/v1/plans",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Grief recovery plan"},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["title"] == "Grief recovery plan"
    assert data["status"] == "active"
    assert data["goals"] == []


@pytest.mark.asyncio
async def test_list_plans(client: AsyncClient) -> None:
    token = await _register(client)
    await client.post("/api/v1/plans", headers={"Authorization": f"Bearer {token}"}, json={"title": "Plan 1"})
    await client.post("/api/v1/plans", headers={"Authorization": f"Bearer {token}"}, json={"title": "Plan 2"})
    r = await client.get("/api/v1/plans", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert len(r.json()) == 2


@pytest.mark.asyncio
async def test_get_plan_with_goals(client: AsyncClient) -> None:
    token = await _register(client)
    plan_r = await client.post("/api/v1/plans", headers={"Authorization": f"Bearer {token}"}, json={"title": "Test plan"})
    plan_id = plan_r.json()["id"]
    await client.post(
        f"/api/v1/plans/{plan_id}/goals",
        headers={"Authorization": f"Bearer {token}"},
        json={"description": "Practice mindfulness daily"},
    )
    r = await client.get(f"/api/v1/plans/{plan_id}", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert len(data["goals"]) == 1
    assert data["goals"][0]["description"] == "Practice mindfulness daily"
    assert data["goals"][0]["status"] == "not_started"


@pytest.mark.asyncio
async def test_update_plan(client: AsyncClient) -> None:
    token = await _register(client)
    plan_r = await client.post("/api/v1/plans", headers={"Authorization": f"Bearer {token}"}, json={"title": "Old"})
    plan_id = plan_r.json()["id"]
    r = await client.patch(
        f"/api/v1/plans/{plan_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "New", "status": "paused"},
    )
    assert r.status_code == 200
    assert r.json()["title"] == "New"
    assert r.json()["status"] == "paused"


@pytest.mark.asyncio
async def test_add_goal(client: AsyncClient) -> None:
    token = await _register(client)
    plan_r = await client.post("/api/v1/plans", headers={"Authorization": f"Bearer {token}"}, json={"title": "Plan"})
    plan_id = plan_r.json()["id"]
    r = await client.post(
        f"/api/v1/plans/{plan_id}/goals",
        headers={"Authorization": f"Bearer {token}"},
        json={"description": "Write in journal 3x/week", "target_date": "2026-05-01"},
    )
    assert r.status_code == 201
    assert r.json()["description"] == "Write in journal 3x/week"
    assert r.json()["target_date"] == "2026-05-01"


@pytest.mark.asyncio
async def test_update_goal_with_progress_note(client: AsyncClient) -> None:
    token = await _register(client)
    plan_r = await client.post("/api/v1/plans", headers={"Authorization": f"Bearer {token}"}, json={"title": "Plan"})
    plan_id = plan_r.json()["id"]
    goal_r = await client.post(
        f"/api/v1/plans/{plan_id}/goals",
        headers={"Authorization": f"Bearer {token}"},
        json={"description": "Goal"},
    )
    goal_id = goal_r.json()["id"]
    r = await client.patch(
        f"/api/v1/goals/{goal_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "in_progress", "progress_note": "Started this week"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "in_progress"
    assert len(r.json()["progress_notes"]) == 1
    assert r.json()["progress_notes"][0]["note"] == "Started this week"


@pytest.mark.asyncio
async def test_delete_goal(client: AsyncClient) -> None:
    token = await _register(client)
    plan_r = await client.post("/api/v1/plans", headers={"Authorization": f"Bearer {token}"}, json={"title": "Plan"})
    plan_id = plan_r.json()["id"]
    goal_r = await client.post(
        f"/api/v1/plans/{plan_id}/goals",
        headers={"Authorization": f"Bearer {token}"},
        json={"description": "Goal to delete"},
    )
    goal_id = goal_r.json()["id"]
    r = await client.delete(f"/api/v1/goals/{goal_id}", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 204
```

- [ ] **Step 2: Implement plans router**

Create `backend/app/api/v1/plans.py`:

```python
"""Treatment plan and goal endpoints."""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.treatment_plan import TreatmentGoal, TreatmentPlan
from app.models.user import User
from app.schemas.treatment import GoalCreate, GoalOut, GoalUpdate, PlanCreate, PlanOut, PlanUpdate

router = APIRouter(tags=["plans"])


@router.post("/plans", response_model=PlanOut, status_code=status.HTTP_201_CREATED)
async def create_plan(
    body: PlanCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TreatmentPlan:
    plan = TreatmentPlan(user_id=current_user.id, title=body.title)
    db.add(plan)
    await db.commit()
    await db.refresh(plan, ["goals"])
    return plan


@router.get("/plans", response_model=list[PlanOut])
async def list_plans(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[TreatmentPlan]:
    result = await db.execute(
        select(TreatmentPlan)
        .where(TreatmentPlan.user_id == current_user.id)
        .options(selectinload(TreatmentPlan.goals))
        .order_by(TreatmentPlan.updated_at.desc())
    )
    return list(result.scalars().all())


@router.get("/plans/{plan_id}", response_model=PlanOut)
async def get_plan(
    plan_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TreatmentPlan:
    result = await db.execute(
        select(TreatmentPlan)
        .where(TreatmentPlan.id == plan_id, TreatmentPlan.user_id == current_user.id)
        .options(selectinload(TreatmentPlan.goals))
    )
    plan = result.scalar_one_or_none()
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found.")
    return plan


@router.patch("/plans/{plan_id}", response_model=PlanOut)
async def update_plan(
    plan_id: uuid.UUID,
    body: PlanUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TreatmentPlan:
    result = await db.execute(
        select(TreatmentPlan)
        .where(TreatmentPlan.id == plan_id, TreatmentPlan.user_id == current_user.id)
        .options(selectinload(TreatmentPlan.goals))
    )
    plan = result.scalar_one_or_none()
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found.")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(plan, key, value)
    await db.commit()
    await db.refresh(plan, ["goals"])
    return plan


@router.post("/plans/{plan_id}/goals", response_model=GoalOut, status_code=status.HTTP_201_CREATED)
async def add_goal(
    plan_id: uuid.UUID,
    body: GoalCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TreatmentGoal:
    result = await db.execute(
        select(TreatmentPlan).where(
            TreatmentPlan.id == plan_id, TreatmentPlan.user_id == current_user.id
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found.")
    goal = TreatmentGoal(
        plan_id=plan_id,
        description=body.description,
        target_date=body.target_date,
        status=body.status,
    )
    db.add(goal)
    await db.commit()
    await db.refresh(goal)
    return goal


@router.patch("/goals/{goal_id}", response_model=GoalOut)
async def update_goal(
    goal_id: uuid.UUID,
    body: GoalUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TreatmentGoal:
    result = await db.execute(
        select(TreatmentGoal)
        .join(TreatmentPlan, TreatmentGoal.plan_id == TreatmentPlan.id)
        .where(TreatmentGoal.id == goal_id, TreatmentPlan.user_id == current_user.id)
    )
    goal = result.scalar_one_or_none()
    if goal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found.")

    update_data = body.model_dump(exclude_unset=True)
    progress_note = update_data.pop("progress_note", None)

    for key, value in update_data.items():
        setattr(goal, key, value)

    if progress_note:
        notes = list(goal.progress_notes or [])
        notes.append({"date": str(date.today()), "note": progress_note})
        goal.progress_notes = notes

    await db.commit()
    await db.refresh(goal)
    return goal


@router.delete("/goals/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_goal(
    goal_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(
        select(TreatmentGoal)
        .join(TreatmentPlan, TreatmentGoal.plan_id == TreatmentPlan.id)
        .where(TreatmentGoal.id == goal_id, TreatmentPlan.user_id == current_user.id)
    )
    goal = result.scalar_one_or_none()
    if goal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found.")
    await db.delete(goal)
    await db.commit()
```

- [ ] **Step 3: Register router, run tests, commit**

Add to `router.py`: `from app.api.v1 import plans` + `api_router.include_router(plans.router)`

Run: `cd backend && uv run python -m pytest tests/test_plans.py -v`

```bash
git add app/api/v1/plans.py app/api/v1/router.py tests/test_plans.py
git commit -m "feat: add treatment plan and goal CRUD endpoints"
```

---

## Task 3: Mood Trend Endpoint

**Files:**
- Modify: `backend/app/api/v1/mood.py`
- Modify: `backend/app/schemas/mood.py`

- [ ] **Step 1: Add MoodTrend schema**

Add to `backend/app/schemas/mood.py`:

```python
class MoodTrend(BaseModel):
    average: float
    direction: str  # "up", "down", "stable"
    count: int
    period_days: int
```

- [ ] **Step 2: Add trend endpoint to mood router**

Add to `backend/app/api/v1/mood.py`:

```python
from datetime import datetime, timedelta, timezone

from sqlalchemy import func as sa_func

from app.schemas.mood import MoodTrend


@router.get("/trend", response_model=MoodTrend)
async def get_mood_trend(
    days: int = Query(default=14, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(
            sa_func.avg(MoodLog.score).label("avg"),
            sa_func.count(MoodLog.id).label("cnt"),
        ).where(
            MoodLog.user_id == current_user.id,
            MoodLog.created_at >= cutoff,
        )
    )
    row = result.one()
    avg_score = float(row.avg) if row.avg is not None else 0.0
    count = row.cnt

    # Determine direction by comparing first half vs second half
    midpoint = datetime.now(timezone.utc) - timedelta(days=days // 2)
    first_half = await db.execute(
        select(sa_func.avg(MoodLog.score)).where(
            MoodLog.user_id == current_user.id,
            MoodLog.created_at >= cutoff,
            MoodLog.created_at < midpoint,
        )
    )
    second_half = await db.execute(
        select(sa_func.avg(MoodLog.score)).where(
            MoodLog.user_id == current_user.id,
            MoodLog.created_at >= midpoint,
        )
    )
    first_avg = first_half.scalar() or 0
    second_avg = second_half.scalar() or 0

    if second_avg > first_avg + 0.5:
        direction = "up"
    elif second_avg < first_avg - 0.5:
        direction = "down"
    else:
        direction = "stable"

    return {"average": round(avg_score, 1), "direction": direction, "count": count, "period_days": days}
```

- [ ] **Step 3: Commit**

```bash
cd backend && git add app/api/v1/mood.py app/schemas/mood.py
git commit -m "feat: add mood trend endpoint (GET /mood/trend)"
```

---

## Task 4: Therapeutic Context Repository

**Files:**
- Create: `backend/app/services/therapeutic_context.py`

This provides direct DB reads for the Historian: profile, latest assessments, active plan, recent moods.

- [ ] **Step 1: Create the service**

Create `backend/app/services/therapeutic_context.py`:

```python
"""Direct DB reads for therapeutic context — used by Historian node."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_async_session
from app.models.assessment import Assessment
from app.models.mood_log import MoodLog
from app.models.treatment_plan import TreatmentPlan
from app.models.user_profile import UserProfile


async def get_profile(user_id: str) -> dict[str, Any] | None:
    uid = uuid.UUID(user_id)
    async with get_async_session() as db:
        profile = await db.get(UserProfile, uid)
        if profile is None:
            result = await db.execute(select(UserProfile).where(UserProfile.user_id == uid))
            profile = result.scalar_one_or_none()
        if profile is None:
            return None
        return {
            "grief_type": profile.grief_type,
            "grief_subject": profile.grief_subject,
            "support_system": profile.support_system,
            "prior_therapy": profile.prior_therapy,
            "preferred_approaches": profile.preferred_approaches,
        }


async def get_latest_assessment(user_id: str, instrument: str = "phq9") -> dict[str, Any] | None:
    uid = uuid.UUID(user_id)
    async with get_async_session() as db:
        result = await db.execute(
            select(Assessment)
            .where(Assessment.user_id == uid, Assessment.instrument == instrument)
            .order_by(Assessment.created_at.desc())
            .limit(1)
        )
        assessment = result.scalar_one_or_none()
        if assessment is None:
            return None
        return {
            "instrument": assessment.instrument,
            "total_score": assessment.total_score,
            "severity": assessment.severity,
            "created_at": assessment.created_at.isoformat() if assessment.created_at else None,
        }


async def get_active_plan(user_id: str) -> dict[str, Any] | None:
    uid = uuid.UUID(user_id)
    async with get_async_session() as db:
        result = await db.execute(
            select(TreatmentPlan)
            .where(TreatmentPlan.user_id == uid, TreatmentPlan.status == "active")
            .options(selectinload(TreatmentPlan.goals))
            .order_by(TreatmentPlan.updated_at.desc())
            .limit(1)
        )
        plan = result.scalar_one_or_none()
        if plan is None:
            return None
        return {
            "title": plan.title,
            "goals": [
                {"description": g.description, "status": g.status, "target_date": str(g.target_date) if g.target_date else None}
                for g in plan.goals
            ],
        }


async def get_recent_moods(user_id: str, limit: int = 7) -> list[dict[str, Any]]:
    uid = uuid.UUID(user_id)
    async with get_async_session() as db:
        result = await db.execute(
            select(MoodLog)
            .where(MoodLog.user_id == uid)
            .order_by(MoodLog.created_at.desc())
            .limit(limit)
        )
        return [
            {"score": m.score, "label": m.label, "created_at": m.created_at.isoformat() if m.created_at else None}
            for m in result.scalars().all()
        ]
```

- [ ] **Step 2: Commit**

```bash
cd backend && git add app/services/therapeutic_context.py
git commit -m "feat: add therapeutic context repository for Historian"
```

---

## Task 5: Expand AgentState + Historian

**Files:**
- Modify: `backend/app/agent/state.py`
- Modify: `backend/app/agent/nodes/historian.py`
- Modify: `backend/app/services/chat_turn.py`

- [ ] **Step 1: Add new fields to AgentState**

Add to `backend/app/agent/state.py` after the existing fields:

```python
    # --- Therapeutic context (loaded by Historian) ---
    user_id: str
    user_profile: dict
    assessment_context: dict
    treatment_plan: dict
    recent_moods: list[dict]
```

- [ ] **Step 2: Pass user_id into agent state from chat_turn.py**

Read `backend/app/services/chat_turn.py` and find where `initial_state` is constructed for the graph invocation. Add `"user_id": str(user_id)` to the state dict. The `user_id` should already be available from the caller context.

- [ ] **Step 3: Update Historian to load therapeutic context**

In `backend/app/agent/nodes/historian.py`, add import:

```python
from app.services import therapeutic_context
```

In `historian_node`, add therapeutic context loading to the existing `asyncio.gather`. The current gather has 3 items (journal, CBT, calendar). Add 4 more:

```python
    user_id = state.get("user_id", "")

    journal_results, query_chunks, calendar_ctx, profile, phq9, plan, moods = await asyncio.gather(
        retrieve_journal_context(user_message, query_embedding=query_embedding),
        retrieve_relevant_chunks(user_message, top_k=5, query_embedding=query_embedding),
        _load_calendar_context(calendar_service, state),
        therapeutic_context.get_profile(user_id) if user_id else _noop_none(),
        therapeutic_context.get_latest_assessment(user_id, "phq9") if user_id else _noop_none(),
        therapeutic_context.get_active_plan(user_id) if user_id else _noop_none(),
        therapeutic_context.get_recent_moods(user_id) if user_id else _noop_list(),
    )
```

Add simple no-op helpers:

```python
async def _noop_none():
    return None

async def _noop_list():
    return []
```

Add therapeutic context to the return dict:

```python
    return {
        "calendar_context": calendar_context,
        "journal_context": journal_context,
        "cbt_chunks": query_chunks,
        "historian_briefing": briefing,
        "user_profile": profile or {},
        "assessment_context": phq9 or {},
        "treatment_plan": plan or {},
        "recent_moods": moods or [],
    }
```

- [ ] **Step 4: Commit**

```bash
cd backend && git add app/agent/state.py app/agent/nodes/historian.py app/services/chat_turn.py
git commit -m "feat: expand Historian with therapeutic context (profile, assessments, plans, moods)"
```

---

## Task 6: Expand Specialist with Therapeutic Awareness + Suggest Tags

**Files:**
- Modify: `backend/app/agent/nodes/specialist.py`
- Modify: `backend/app/agent/prompts.py`

- [ ] **Step 1: Add therapeutic context to Specialist prompt builder**

In `backend/app/agent/nodes/specialist.py`, update `_build_specialist_prompt` to include therapeutic context after the historian briefing section:

```python
    # Therapeutic context
    profile = state.get("user_profile", {})
    if profile:
        parts.append(f"\n## User profile")
        parts.append(f"Grief type: {profile.get('grief_type', 'unknown')}")
        parts.append(f"Support system: {profile.get('support_system', 'unknown')}")
        approaches = profile.get('preferred_approaches', [])
        if approaches:
            parts.append(f"Preferred approaches: {', '.join(approaches)}")

    assessment = state.get("assessment_context", {})
    if assessment:
        parts.append(f"\n## Latest assessment")
        parts.append(f"{assessment.get('instrument', 'PHQ-9').upper()}: {assessment.get('total_score', '?')}/27 ({assessment.get('severity', 'unknown')})")

    plan = state.get("treatment_plan", {})
    if plan:
        parts.append(f"\n## Active treatment plan: {plan.get('title', 'Untitled')}")
        for g in plan.get("goals", []):
            parts.append(f"- [{g.get('status', '?')}] {g.get('description', '')}")

    moods = state.get("recent_moods", [])
    if moods:
        scores = [m["score"] for m in moods if "score" in m]
        if scores:
            avg = sum(scores) / len(scores)
            parts.append(f"\n## Recent mood trend: avg {avg:.1f}/10 over {len(scores)} entries")
```

- [ ] **Step 2: Update Specialist system prompt to emit suggest tags**

In `backend/app/agent/prompts.py`, add to the end of `SPECIALIST_SYSTEM` (before the closing `\"`):

```
\n\n## Interactive coaching actions
When contextually appropriate, you may include ONE of these tags at the very \
end of your response (after your main text, before any prosody hint):
- [suggest:journal] — after emotional disclosure, invite user to write about it
- [suggest:mood_check] — at end of session or when mood shift is detected
- [suggest:assessment] — when 2+ weeks since last assessment
- [suggest:goal_update] — when user discusses progress on a known treatment goal

Only include a tag if it genuinely fits the moment. Most responses need no tag.\
```

- [ ] **Step 3: Commit**

```bash
cd backend && git add app/agent/nodes/specialist.py app/agent/prompts.py
git commit -m "feat: expand Specialist with therapeutic awareness and suggest tags"
```

---

## Task 7: Expand Anchor with Score-Aware Escalation

**Files:**
- Modify: `backend/app/agent/nodes/anchor.py`
- Modify: `backend/app/agent/prompts.py`

- [ ] **Step 1: Add assessment context to Anchor prompt**

In `backend/app/agent/nodes/anchor.py`, update `_build_anchor_prompt` to include assessment context:

```python
    # Assessment context for escalation
    assessment = state.get("assessment_context", {})
    if assessment:
        parts.append(f"\n## Assessment context")
        parts.append(f"{assessment.get('instrument', 'PHQ-9').upper()}: score {assessment.get('total_score', '?')}, severity: {assessment.get('severity', 'unknown')}")

    # Calendar triggers
    calendar = state.get("calendar_context", [])
    if calendar:
        parts.append(f"\n## Upcoming events")
        for event in calendar:
            parts.append(f"- {event}")
```

- [ ] **Step 2: Update Anchor system prompt with escalation rules**

In `backend/app/agent/prompts.py`, add to `ANCHOR_SYSTEM` before the closing `\"`:

```
\n\n7. **Score-aware escalation** — If the assessment context shows PHQ-9 >= 20 \
   or GAD-7 >= 15 (severe), ALWAYS include crisis resources regardless of \
   message content.
8. **Calendar sensitivity** — If an anniversary or trigger event is within 3 \
   days, use extra-gentle tone and validate the difficulty of that time.\
```

- [ ] **Step 3: Commit**

```bash
cd backend && git add app/agent/nodes/anchor.py app/agent/prompts.py
git commit -m "feat: expand Anchor with score-aware escalation and calendar sensitivity"
```

---

## Task 8: Frontend Plan API Client + Page

**Files:**
- Create: `frontend/lib/plan-api.ts`
- Create: `frontend/app/plan/page.tsx`
- Modify: `frontend/components/sidebar.tsx`

- [ ] **Step 1: Create plan API client**

Create `frontend/lib/plan-api.ts` with functions for: list_plans, get_plan, create_plan, update_plan, add_goal, update_goal, delete_goal, get_mood_trend.

- [ ] **Step 2: Create plan page**

Create `frontend/app/plan/page.tsx` — a "use client" page showing:
- Active plan card with title, status, progress bar
- Goal list with description, status badge, target date, progress notes
- "Add Goal" inline form
- Assessment history (table from GET /assessments)
- Mood trend sparkline
- "Take Assessment" button → modal

- [ ] **Step 3: Add "My Plan" to sidebar**

Read and edit `frontend/components/sidebar.tsx` — add a link to `/plan` using the `ClipboardList` icon from lucide-react, between Calendar and Settings.

- [ ] **Step 4: Commit**

```bash
git add frontend/lib/plan-api.ts frontend/app/plan/ frontend/components/sidebar.tsx
git commit -m "feat: add treatment plan frontend (plan page, goal management, sidebar link)"
```

---

## Task 9: Chat Action Buttons (Suggest Tags)

**Files:**
- Modify: `frontend/components/chat_view.tsx`

- [ ] **Step 1: Parse suggest tags from assistant messages**

In `frontend/components/chat_view.tsx`, add a utility function that extracts `[suggest:...]` tags from message text and returns the cleaned text + tag:

```typescript
function parse_suggest_tag(text: string): { clean_text: string; suggest: string | null } {
  const match = text.match(/\[suggest:(journal|mood_check|assessment|goal_update)\]/);
  if (!match) return { clean_text: text, suggest: null };
  return {
    clean_text: text.replace(match[0], "").trim(),
    suggest: match[1],
  };
}
```

- [ ] **Step 2: Render action buttons below assistant messages that have suggest tags**

When rendering assistant messages, use `parse_suggest_tag` and if a tag is found, render a button below the message. For now, buttons link to the relevant page:
- `journal` → `/journal/new`
- `mood_check` → POST to `/api/v1/mood` via a small modal
- `assessment` → link to `/plan` (where assessment modal lives)
- `goal_update` → link to `/plan`

- [ ] **Step 3: Commit**

```bash
git add frontend/components/chat_view.tsx
git commit -m "feat: parse [suggest:...] tags and render action buttons in chat"
```

---

## Task 10: Run Full Test Suite

- [ ] **Step 1: Run all backend tests**

Run: `cd backend && uv run python -m pytest -v`

- [ ] **Step 2: Run linter**

Run: `cd backend && uv run ruff check .`

- [ ] **Step 3: Fix and commit if needed**

```bash
git add -u && git commit -m "fix: resolve Phase 3 integration issues"
```
