from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from app.core.config import settings
from app.services.tts.base import TextToSpeechService


class StubTextToSpeechService(TextToSpeechService):
    async def synthesize_stream(
        self,
        text: str,
        *,
        prosody_hint: str | None = None,
    ) -> AsyncIterator[bytes]:
        payload = f"stub-audio|hint={prosody_hint or 'none'}|text={text}".encode("utf-8")
        chunk_size = max(256, settings.voice_chunk_bytes)
        for i in range(0, len(payload), chunk_size):
            await asyncio.sleep(0.005)
            yield payload[i : i + chunk_size]
