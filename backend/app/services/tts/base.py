from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol


class TextToSpeechService(Protocol):
    async def synthesize_stream(
        self,
        text: str,
        *,
        prosody_hint: str | None = None,
    ) -> AsyncIterator[bytes]:
        """Convert text into streamed audio chunks."""
