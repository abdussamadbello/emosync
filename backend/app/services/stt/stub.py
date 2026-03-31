from __future__ import annotations

from app.services.stt.base import SpeechToTextService


class StubSpeechToTextService(SpeechToTextService):
    async def transcribe(self, audio: bytes, *, mime_type: str = "audio/wav") -> str:
        if not audio:
            return ""
        return f"[stub transcript] Received {len(audio)} bytes of {mime_type}."
