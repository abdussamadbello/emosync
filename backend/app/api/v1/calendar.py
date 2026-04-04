"""Calendar event endpoints: CRUD + date range/type filter."""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.calendar_event import CalendarEvent
from app.models.user import User
from app.schemas.calendar import CalendarEventCreate, CalendarEventOut, CalendarEventUpdate

router = APIRouter(prefix="/calendar", tags=["calendar"])


@router.post("", response_model=CalendarEventOut, status_code=status.HTTP_201_CREATED)
async def create_event(
    body: CalendarEventCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CalendarEvent:
    event = CalendarEvent(
        user_id=current_user.id,
        title=body.title,
        date=body.date,
        event_type=body.event_type,
        recurrence=body.recurrence,
        notes=body.notes,
        notify_agent=body.notify_agent,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


@router.get("", response_model=list[CalendarEventOut])
async def list_events(
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    event_type: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CalendarEvent]:
    stmt = (
        select(CalendarEvent)
        .where(CalendarEvent.user_id == current_user.id)
        .order_by(CalendarEvent.date.asc())
    )
    if from_date:
        stmt = stmt.where(CalendarEvent.date >= from_date)
    if to_date:
        stmt = stmt.where(CalendarEvent.date <= to_date)
    if event_type:
        stmt = stmt.where(CalendarEvent.event_type == event_type)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/{event_id}", response_model=CalendarEventOut)
async def get_event(
    event_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CalendarEvent:
    result = await db.execute(
        select(CalendarEvent).where(
            CalendarEvent.id == event_id,
            CalendarEvent.user_id == current_user.id,
        )
    )
    event = result.scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar event not found.")
    return event


@router.patch("/{event_id}", response_model=CalendarEventOut)
async def update_event(
    event_id: uuid.UUID,
    body: CalendarEventUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CalendarEvent:
    result = await db.execute(
        select(CalendarEvent).where(
            CalendarEvent.id == event_id,
            CalendarEvent.user_id == current_user.id,
        )
    )
    event = result.scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar event not found.")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(event, key, value)
    await db.commit()
    await db.refresh(event)
    return event


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(
        select(CalendarEvent).where(
            CalendarEvent.id == event_id,
            CalendarEvent.user_id == current_user.id,
        )
    )
    event = result.scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar event not found.")

    await db.delete(event)
    await db.commit()
