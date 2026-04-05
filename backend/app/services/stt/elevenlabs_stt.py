from __future__ import annotations

import io
import logging

from elevenlabs.client import AsyncElevenLabs

from app.core.config import settings
from app.services.stt.base import SpeechToTextService

logger = logging.getLogger(__name__)


class ElevenLabsSpeechToTextService(SpeechToTextService):
    def __init__(self, *, api_key: str, model_id: str) -> None:
        self._model_id = model_id
        self._client = AsyncElevenLabs(api_key=api_key, timeout=30.0)

    async def transcribe(self, audio: bytes, *, mime_type: str = "audio/wav") -> str:
        normalized_mime_type = _normalize_mime_type(mime_type)
        extension = normalized_mime_type.split("/")[-1] or "wav"
        audio_file = (f"audio.{extension}", io.BytesIO(audio), normalized_mime_type)

        try:
            result = await self._client.speech_to_text.convert(
                model_id=self._model_id,
                file=audio_file,
                timestamps_granularity="none",
                tag_audio_events=False,
            )
            return result.text
        except Exception:
            logger.exception(
                "ElevenLabs STT failed for mime_type=%s; falling back to stub transcription.",
                normalized_mime_type,
            )
            from app.services.stt.stub import StubSpeechToTextService

            return await StubSpeechToTextService().transcribe(
                audio,
                mime_type=normalized_mime_type,
            )


def build_stt_service() -> SpeechToTextService:
    if settings.elevenlabs_api_key:
        return ElevenLabsSpeechToTextService(
            api_key=settings.elevenlabs_api_key,
            model_id=settings.elevenlabs_stt_model_id,
        )

    from app.services.stt.stub import StubSpeechToTextService

    return StubSpeechToTextService()


def _normalize_mime_type(mime_type: str) -> str:
    value = mime_type.split(";", 1)[0].strip().lower()
    return value or "audio/wav"
