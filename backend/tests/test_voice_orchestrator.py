from __future__ import annotations

import uuid

import pytest

from app.services.realtime.orchestrator import VoiceOrchestrator
from app.services.tts.stub import StubTextToSpeechService


@pytest.mark.asyncio
async def test_orchestrator_emits_text_and_audio_events() -> None:
    orchestrator = VoiceOrchestrator(tts_service=StubTextToSpeechService())

    events = []
    async for event in orchestrator.stream_transcript_turn(
        transcript="I feel overwhelmed today",
        conversation_id=uuid.uuid4(),
        user_message_id=uuid.uuid4(),
        conversation_history=[],
    ):
        events.append(event.type)

    assert "assistant.text.delta" in events
    assert "assistant.text.done" in events
    assert "output_audio.chunk" in events
    assert events[-1] == "turn.done"
