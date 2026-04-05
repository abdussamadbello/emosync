from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock

from app.services.realtime.gemini_live import (
    GeminiLiveVoiceBridge,
    _sanitize_output_text,
    parse_pcm_rate,
)


def test_parse_pcm_rate_reads_rate_parameter() -> None:
    assert parse_pcm_rate("audio/pcm;rate=16000", default=24_000) == 16_000
    assert parse_pcm_rate("audio/pcm", default=24_000) == 24_000
    assert parse_pcm_rate(None, default=24_000) == 24_000


def test_end_audio_uses_audio_stream_end() -> None:
    bridge = GeminiLiveVoiceBridge(conversation_history=[])
    bridge._ws = AsyncMock()

    asyncio.run(bridge.end_audio())

    bridge._ws.send.assert_awaited_once()
    msg = json.loads(bridge._ws.send.call_args[0][0])
    assert msg == {"realtimeInput": {"audioStreamEnd": True}}


def test_send_text_uses_realtime_input() -> None:
    bridge = GeminiLiveVoiceBridge(conversation_history=[])
    bridge._ws = AsyncMock()

    asyncio.run(bridge.send_text("Hello there"))

    bridge._ws.send.assert_awaited_once()
    msg = json.loads(bridge._ws.send.call_args[0][0])
    assert msg["clientContent"]["turns"][0]["parts"][0]["text"] == "Hello there"


def test_message_to_events_emits_transcripts_audio_and_turn_done() -> None:
    bridge = GeminiLiveVoiceBridge(conversation_history=[])

    first = _make_message(
        input_text="I feel overwhelmed",
        output_text="I hear you",
        audio_bytes="AAECAw==", # Base64 for b"\x00\x01\x02\x03"
    )
    second = _make_message(
        output_text="I hear you, and I'm here with you.",
        turn_complete=True,
    )

    first_events = asyncio.run(_collect_events(bridge, first))
    second_events = asyncio.run(_collect_events(bridge, second))

    assert [event.type for event in first_events] == [
        "user.transcript",
        "assistant.text.delta",
        "output_audio.chunk",
    ]
    assert [event.type for event in second_events] == [
        "assistant.text.delta",
        "assistant.text.done",
        "output_audio.done",
        "turn.done",
    ]
    assert second_events[-1].data["assistant_text"] == "I hear you, and I'm here with you."


def test_message_to_events_emits_interrupted_and_resets_turn_state() -> None:
    bridge = GeminiLiveVoiceBridge(conversation_history=[])
    bridge._input_transcript = "Existing user text"
    bridge._output_transcript = "Partial assistant text"
    bridge._output_chunk_count = 3

    events = asyncio.run(_collect_events(bridge, _make_message(interrupted=True)))

    assert [event.type for event in events] == ["turn.interrupted"]
    assert bridge._input_transcript == ""
    assert bridge._output_transcript == ""
    assert bridge._output_chunk_count == 0


def test_sanitize_output_text_preserves_spaces_and_removes_prosody_fragments() -> None:
    assert _sanitize_output_text("It's completely understandable not to feel fine.") == (
        "It's completely understandable not to feel fine."
    )
    assert _sanitize_output_text("It's okay to rest. [gentle, warm tone]") == "It's okay to rest."
    assert _sanitize_output_text("It's okay to rest. [gentle, warm") == "It's okay to rest."


async def _collect_events(bridge: GeminiLiveVoiceBridge, message: dict):
    return [event async for event in bridge._message_to_events(message)]


def _make_message(
    *,
    input_text: str | None = None,
    output_text: str | None = None,
    audio_bytes: str | None = None,
    interrupted: bool = False,
    turn_complete: bool = False,
) -> dict:
    parts = []
    if audio_bytes is not None:
        parts.append({
            "inlineData": {
                "data": audio_bytes,
                "mimeType": "audio/pcm;rate=24000",
            }
        })

    server_content = {}
    if input_text:
        server_content["inputTranscription"] = {"text": input_text}
    if output_text:
        server_content["outputTranscription"] = {"text": output_text}
    if parts:
        server_content["modelTurn"] = {"parts": parts}
    if interrupted:
        server_content["interrupted"] = True
    if turn_complete:
        server_content["turnComplete"] = True

    return {"serverContent": server_content}
