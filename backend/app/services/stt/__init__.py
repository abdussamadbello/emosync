from __future__ import annotations

from typing import Any

from app.services.stt.base import SpeechToTextService
from app.services.stt.stub import StubSpeechToTextService

__all__ = [
    "SpeechToTextService",
    "StubSpeechToTextService",
    "ElevenLabsSpeechToTextService",
    "build_stt_service",
]


def __getattr__(name: str) -> Any:
    if name in {"ElevenLabsSpeechToTextService", "build_stt_service"}:
        from app.services.stt.elevenlabs_stt import ElevenLabsSpeechToTextService, build_stt_service

        return {
            "ElevenLabsSpeechToTextService": ElevenLabsSpeechToTextService,
            "build_stt_service": build_stt_service,
        }[name]
    raise AttributeError(name)
