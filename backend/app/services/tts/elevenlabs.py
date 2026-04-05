from __future__ import annotations

from collections.abc import AsyncIterator
import logging

from elevenlabs.client import AsyncElevenLabs
from elevenlabs.types import VoiceSettings

from app.core.config import settings
from app.services.tts.base import TextToSpeechService

logger = logging.getLogger(__name__)


class ElevenLabsTextToSpeechService(TextToSpeechService):
    def __init__(self, *, api_key: str, voice_id: str, model_id: str) -> None:
        self._voice_id = voice_id
        self._model_id = model_id
        self._client = AsyncElevenLabs(api_key=api_key, timeout=30.0)

    async def synthesize_stream(
        self,
        text: str,
        *,
        prosody_hint: str | None = None,
    ) -> AsyncIterator[bytes]:
        try:
            stream = self._client.text_to_speech.convert_as_stream(
                self._voice_id,
                text=text,
                model_id=self._model_id,
                output_format=settings.voice_output_format,
                voice_settings=_prosody_to_voice_settings(prosody_hint),
            )

            async for chunk in stream:
                if chunk:
                    yield chunk
        except Exception:
            logger.exception("ElevenLabs TTS failed; falling back to stub audio.")
            from app.services.tts.stub import StubTextToSpeechService

            async for chunk in StubTextToSpeechService().synthesize_stream(
                text,
                prosody_hint=prosody_hint,
            ):
                yield chunk


def build_tts_service() -> TextToSpeechService:
    if settings.elevenlabs_api_key:
        return ElevenLabsTextToSpeechService(
            api_key=settings.elevenlabs_api_key,
            voice_id=settings.elevenlabs_voice_id,
            model_id=settings.elevenlabs_model_id,
        )

    from app.services.tts.stub import StubTextToSpeechService

    return StubTextToSpeechService()


def _prosody_to_voice_settings(prosody_hint: str | None) -> VoiceSettings:
    hint = (prosody_hint or "").lower()

    stability = 0.55
    similarity_boost = 0.7
    style = 0.2
    use_speaker_boost = True

    if "slow" in hint or "measured" in hint:
        stability = 0.7
    if "gentle" in hint or "warm" in hint:
        similarity_boost = 0.8
        style = 0.1

    return VoiceSettings(
        stability=stability,
        similarity_boost=similarity_boost,
        style=style,
        use_speaker_boost=use_speaker_boost,
    )
