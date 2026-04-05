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
