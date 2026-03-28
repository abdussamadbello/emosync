from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    title: str | None = Field(default=None, max_length=512)
    user_id: uuid.UUID | None = None


class ConversationOut(BaseModel):
    id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageOut(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class StreamTurnRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=32_000)
