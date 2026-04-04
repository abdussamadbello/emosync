"""Pydantic models for journal entry endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class JournalCreate(BaseModel):
    title: str | None = Field(default=None, max_length=256)
    content: str = Field(..., min_length=1, max_length=50000)
    mood_score: int | None = Field(default=None, ge=1, le=10)
    tags: list[str] = Field(default_factory=list)
    source: str = Field(default="manual", max_length=20)
    conversation_id: uuid.UUID | None = None


class JournalUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=256)
    content: str | None = Field(default=None, min_length=1, max_length=50000)
    mood_score: int | None = Field(default=None, ge=1, le=10)
    tags: list[str] | None = None


class JournalOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str | None
    content: str
    mood_score: int | None
    tags: list[str] | None
    source: str
    conversation_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
