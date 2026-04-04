"""Pydantic models for calendar event endpoints."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class CalendarEventCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=256)
    date: date
    event_type: str = Field(..., max_length=20)
    recurrence: str | None = Field(default=None, pattern=r"^(yearly|monthly|weekly)$")
    notes: str | None = Field(default=None, max_length=5000)
    notify_agent: bool = True


class CalendarEventUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=256)
    date: date | None = None
    event_type: str | None = Field(default=None, max_length=20)
    recurrence: str | None = Field(default=None)
    notes: str | None = Field(default=None, max_length=5000)
    notify_agent: bool | None = None


class CalendarEventOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    date: date
    event_type: str
    recurrence: str | None
    notes: str | None
    notify_agent: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
