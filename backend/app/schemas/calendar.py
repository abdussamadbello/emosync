"""Pydantic models for calendar event endpoints."""

from __future__ import annotations

import uuid
from datetime import date as date_type
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CalendarEventCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=256)
    date: date_type
    event_type: str = Field(..., max_length=20)
    recurrence: Optional[str] = Field(default=None, pattern=r"^(yearly|monthly|weekly)$")
    notes: Optional[str] = Field(default=None, max_length=5000)
    notify_agent: bool = True


class CalendarEventUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=256)
    date: Optional[date_type] = None
    event_type: Optional[str] = Field(default=None, max_length=20)
    recurrence: Optional[str] = Field(default=None)
    notes: Optional[str] = Field(default=None, max_length=5000)
    notify_agent: Optional[bool] = None


class CalendarEventOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    date: date_type
    event_type: str
    recurrence: Optional[str]
    notes: Optional[str]
    notify_agent: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
