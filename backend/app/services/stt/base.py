from __future__ import annotations

from typing import Protocol


class SpeechToTextService(Protocol):
    async def transcribe(self, audio: bytes, *, mime_type: str = "audio/wav") -> str:
        """Convert audio bytes into text."""
