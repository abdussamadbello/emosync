"""Mood log endpoints: create and list."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func as sa_func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.mood_log import MoodLog
from app.models.user import User
from app.schemas.mood import MoodCreate, MoodOut, MoodTrend

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
