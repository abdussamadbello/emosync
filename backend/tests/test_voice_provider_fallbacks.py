from __future__ import annotations

import pytest

from app.services.stt.elevenlabs_stt import (
    ElevenLabsSpeechToTextService,
    _normalize_mime_type,
)
from app.services.tts.elevenlabs import ElevenLabsTextToSpeechService


@pytest.mark.asyncio
async def test_stt_falls_back_to_stub_and_normalizes_mime_type(monkeypatch: pytest.MonkeyPatch) -> None:
    service = ElevenLabsSpeechToTextService(api_key="test-key", model_id="scribe_v2")

    async def raise_stt_failure(**_: object) -> object:
        raise RuntimeError("provider unavailable")

    captured: dict[str, str] = {}

    async def fake_stub_transcribe(self, audio: bytes, *, mime_type: str = "audio/wav") -> str:
        captured["mime_type"] = mime_type
        return f"stubbed {len(audio)} bytes"

    monkeypatch.setattr(service._client.speech_to_text, "convert", raise_stt_failure)
    monkeypatch.setattr(
        "app.services.stt.stub.StubSpeechToTextService.transcribe",
        fake_stub_transcribe,
    )

    result = await service.transcribe(
        b"abc123",
        mime_type="audio/webm;codecs=opus",
    )

    assert result == "stubbed 6 bytes"
    assert captured["mime_type"] == "audio/webm"


@pytest.mark.asyncio
async def test_tts_falls_back_to_stub_audio(monkeypatch: pytest.MonkeyPatch) -> None:
    service = ElevenLabsTextToSpeechService(
        api_key="test-key",
        voice_id="voice-id",
        model_id="eleven_turbo_v2_5",
    )

    def raise_tts_failure(*_: object, **__: object) -> object:
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(service._client.text_to_speech, "convert_as_stream", raise_tts_failure)

    chunks: list[bytes] = []
    async for chunk in service.synthesize_stream("Hello fallback", prosody_hint="warm tone"):
        chunks.append(chunk)

    payload = b"".join(chunks)

    assert payload
    assert b"stub-audio" in payload
    assert b"Hello fallback" in payload


def test_normalize_mime_type_strips_codec_suffix() -> None:
    assert _normalize_mime_type("audio/webm;codecs=opus") == "audio/webm"
    assert _normalize_mime_type(" audio/wav ") == "audio/wav"
