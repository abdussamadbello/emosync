"""Pydantic models for assessment endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class AssessmentCreate(BaseModel):
    instrument: str = Field(..., pattern=r"^(phq9|gad7)$")
    responses: dict[str, int] = Field(..., min_length=1)
    source: str = Field(default="onboarding", max_length=20)


class AssessmentOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    instrument: str
    responses: dict[str, int]
    total_score: int
    severity: str
    source: str
    created_at: datetime

    model_config = {"from_attributes": True}
