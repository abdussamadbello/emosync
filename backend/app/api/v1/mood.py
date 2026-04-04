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
