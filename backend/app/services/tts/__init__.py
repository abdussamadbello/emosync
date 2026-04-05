from __future__ import annotations

from typing import Any

from app.services.tts.base import TextToSpeechService
from app.services.tts.stub import StubTextToSpeechService

__all__ = [
    "TextToSpeechService",
    "ElevenLabsTextToSpeechService",
    "StubTextToSpeechService",
    "build_tts_service",
]


def __getattr__(name: str) -> Any:
    if name in {"ElevenLabsTextToSpeechService", "build_tts_service"}:
        from app.services.tts.elevenlabs import ElevenLabsTextToSpeechService, build_tts_service

        return {
            "ElevenLabsTextToSpeechService": ElevenLabsTextToSpeechService,
            "build_tts_service": build_tts_service,
        }[name]
    raise AttributeError(name)
