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
