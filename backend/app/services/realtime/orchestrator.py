from __future__ import annotations

import base64
import uuid
from collections.abc import AsyncIterator

from app.schemas.voice import VoiceServerEvent
from app.services.chat_turn import run_turn_full
from app.services.tts.base import TextToSpeechService


class VoiceOrchestrator:
    def __init__(self, tts_service: TextToSpeechService) -> None:
        self._tts_service = tts_service

    async def stream_transcript_turn(
        self,
        *,
        transcript: str,
        conversation_id: uuid.UUID,
        user_message_id: uuid.UUID,
        conversation_history: list[dict[str, str]],
    ) -> AsyncIterator[VoiceServerEvent]:
        assistant_text, prosody_hint = await run_turn_full(
            user_message=transcript,
            conversation_id=str(conversation_id),
            user_message_id=str(user_message_id),
            conversation_history=conversation_history,
        )

        words = assistant_text.split()
        for i, word in enumerate(words):
            token = word + (" " if i < len(words) - 1 else "")
            yield VoiceServerEvent(type="assistant.text.delta", data={"text": token})

        yield VoiceServerEvent(type="assistant.text.done", data={"text": assistant_text})

        chunk_count = 0
        async for chunk in self._tts_service.synthesize_stream(
            assistant_text,
            prosody_hint=prosody_hint,
        ):
            chunk_count += 1
            yield VoiceServerEvent(
                type="output_audio.chunk",
                data={"audio_b64": base64.b64encode(chunk).decode("ascii")},
            )

        yield VoiceServerEvent(type="output_audio.done", data={"chunks": chunk_count})
        yield VoiceServerEvent(type="turn.done", data={"assistant_text": assistant_text})
