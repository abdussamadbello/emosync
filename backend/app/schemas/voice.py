from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


ClientEventType = Literal[
    "input_text.final",
    "input_audio.append",
    "input_audio.commit",
    "input_audio.clear",
    "turn.cancel",
    "ping",
]

ServerEventType = Literal[
    "session.ready",
    "user.transcript",
    "assistant.text.delta",
    "assistant.text.done",
    "output_audio.chunk",
    "output_audio.done",
    "turn.interrupted",
    "turn.done",
    "error",
    "pong",
]


class VoiceClientEvent(BaseModel):
    type: ClientEventType
    data: dict[str, Any] = Field(default_factory=dict)


class VoiceServerEvent(BaseModel):
    type: ServerEventType
    data: dict[str, Any] = Field(default_factory=dict)
    ts: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class InputTextFinal(BaseModel):
    text: str = Field(..., min_length=1, max_length=32_000)
