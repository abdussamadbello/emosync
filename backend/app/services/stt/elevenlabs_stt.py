from __future__ import annotations

import io

from elevenlabs.client import AsyncElevenLabs

from app.core.config import settings
from app.services.stt.base import SpeechToTextService


class ElevenLabsSpeechToTextService(SpeechToTextService):
    def __init__(self, *, api_key: str, model_id: str) -> None:
        self._model_id = model_id
        self._client = AsyncElevenLabs(api_key=api_key, timeout=30.0)

    async def transcribe(self, audio: bytes, *, mime_type: str = "audio/wav") -> str:
        extension = mime_type.split("/")[-1].split(";")[0] or "wav"
        audio_file = (f"audio.{extension}", io.BytesIO(audio), mime_type)

        result = await self._client.speech_to_text.convert(
            model_id=self._model_id,
            file=audio_file,
            timestamps_granularity="none",
            tag_audio_events=False,
        )
        return result.text


def build_stt_service() -> SpeechToTextService:
    if settings.elevenlabs_api_key:
        return ElevenLabsSpeechToTextService(
            api_key=settings.elevenlabs_api_key,
            model_id=settings.elevenlabs_stt_model_id,
        )

    from app.services.stt.stub import StubSpeechToTextService

    return StubSpeechToTextService()
