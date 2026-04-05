"""Calendar MCP service — real DB queries replacing mock data."""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import Any

from sqlalchemy import select

from app.core.database import get_async_session
from app.models.calendar_event import CalendarEvent
from .schema import CalendarContext


class CalendarService:
    async def get_context(self, user_id: str) -> CalendarContext:
        """Get upcoming events for agent context (replaces mock data)."""
        today = date.today()
        upcoming_window = today + timedelta(days=7)

        uid = uuid.UUID(user_id)
        async with get_async_session() as db:
            result = await db.execute(
                select(CalendarEvent).where(
                    CalendarEvent.user_id == uid,
                    CalendarEvent.notify_agent.is_(True),
                    CalendarEvent.date >= today,
                    CalendarEvent.date <= upcoming_window,
                )
            )
            events = result.scalars().all()

        from .schema import CalendarEvent as CalendarEventSchema

        relevant_today = []
        upcoming = []
        for event in events:
            event_obj = CalendarEventSchema(
                id=str(event.id),
                title=event.title,
                date=event.date.isoformat(),
                type=event.event_type,
                metadata={"recurrence": event.recurrence, "notes": event.notes},
            )
            if event.date == today:
                relevant_today.append(event_obj)
            upcoming.append(event_obj)

        return CalendarContext(
            relevant_today=relevant_today,
            upcoming_events=upcoming,
        )

    async def get_triggers(self, user_id: str, days: int = 7) -> list[dict[str, Any]]:
        """Get anniversary/trigger events within N days."""
        today = date.today()
        window = today + timedelta(days=days)
        uid = uuid.UUID(user_id)

        async with get_async_session() as db:
            result = await db.execute(
                select(CalendarEvent).where(
                    CalendarEvent.user_id == uid,
                    CalendarEvent.event_type.in_(("anniversary", "trigger")),
                    CalendarEvent.date >= today,
                    CalendarEvent.date <= window,
                )
            )
            events = result.scalars().all()

        return [
            {
                "id": str(e.id),
                "title": e.title,
                "date": e.date.isoformat(),
                "event_type": e.event_type,
                "notes": e.notes,
            }
            for e in events
        ]

    async def get_by_date(self, user_id: str, target_date: date) -> list[dict[str, Any]]:
        """Get events on a specific date."""
        uid = uuid.UUID(user_id)
        async with get_async_session() as db:
            result = await db.execute(
                select(CalendarEvent).where(
                    CalendarEvent.user_id == uid,
                    CalendarEvent.date == target_date,
                )
            )
            events = result.scalars().all()

        return [
            {
                "id": str(e.id),
                "title": e.title,
                "date": e.date.isoformat(),
                "event_type": e.event_type,
                "notes": e.notes,
            }
            for e in events
        ]
