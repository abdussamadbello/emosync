"""Pydantic models for treatment plan and goal endpoints."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class GoalCreate(BaseModel):
    description: str = Field(..., min_length=1, max_length=2000)
    target_date: date | None = None
    status: str = Field(default="not_started", pattern=r"^(not_started|in_progress|completed)$")


class GoalUpdate(BaseModel):
    description: str | None = Field(default=None, min_length=1, max_length=2000)
    target_date: date | None = None
    status: str | None = Field(default=None, pattern=r"^(not_started|in_progress|completed)$")
    progress_note: str | None = Field(default=None, max_length=2000)


class GoalOut(BaseModel):
    id: uuid.UUID
    plan_id: uuid.UUID
    description: str
    target_date: date | None
    status: str
    progress_notes: list | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PlanCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=256)


class PlanUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=256)
    status: str | None = Field(default=None, pattern=r"^(active|completed|paused)$")


class PlanOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    status: str
    created_at: datetime
    updated_at: datetime
    goals: list[GoalOut] = []

    model_config = {"from_attributes": True}
