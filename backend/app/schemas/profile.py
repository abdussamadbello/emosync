"""Pydantic models for user profile endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ProfileUpdate(BaseModel):
    grief_type: str | None = Field(default=None, max_length=50)
    grief_subject: str | None = Field(default=None, max_length=1024)
    grief_duration_months: int | None = Field(default=None, ge=0)
    support_system: str | None = Field(default=None, max_length=20)
    prior_therapy: bool | None = None
    preferred_approaches: list[str] | None = None


class ProfileOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    grief_type: str | None
    grief_subject: str | None
    grief_duration_months: int | None
    support_system: str | None
    prior_therapy: bool
    preferred_approaches: list[str] | None
    onboarding_completed: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
