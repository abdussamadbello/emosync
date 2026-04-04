"""Tests for voice WebSocket edge cases."""

from __future__ import annotations

import pytest
from app.main import app
from app.schemas.voice import ServerEventType


def test_user_transcript_in_server_event_types():
    """user.transcript must be a valid ServerEventType for the voice protocol."""
    valid_types: tuple[str, ...] = ServerEventType.__args__  # type: ignore[attr-defined]
    assert "user.transcript" in valid_types


@pytest.mark.asyncio
async def test_voice_ws_rejects_unauthenticated():
    """WebSocket without auth should be closed with 1008 policy violation."""
    from starlette.testclient import TestClient

    with TestClient(app) as tc:
        import uuid

        fake_id = str(uuid.uuid4())
        with pytest.raises(Exception):
            # Starlette test client raises on policy close
            with tc.websocket_connect(f"/api/v1/voice/ws/{fake_id}"):
                pass


class TestAudioBufferEdgeCases:
    """Tests for the AudioBuffer used in voice handling."""

    def test_append_within_limit(self):
        from app.services.audio.buffer import AudioBuffer

        buf = AudioBuffer(max_bytes=100)
        buf.append(b"hello")
        assert buf.size == 5

    def test_append_exceeds_limit_raises(self):
        from app.services.audio.buffer import AudioBuffer

        buf = AudioBuffer(max_bytes=10)
        buf.append(b"12345")
        with pytest.raises(ValueError, match="Audio buffer limit exceeded"):
            buf.append(b"1234567890")

    def test_flush_returns_all_data(self):
        from app.services.audio.buffer import AudioBuffer

        buf = AudioBuffer(max_bytes=100)
        buf.append(b"hello")
        buf.append(b"world")
        data = buf.flush()
        assert data == b"helloworld"
        assert buf.size == 0

    def test_reset_clears_buffer(self):
        from app.services.audio.buffer import AudioBuffer

        buf = AudioBuffer(max_bytes=100)
        buf.append(b"data")
        buf.reset()
        assert buf.size == 0
        assert buf.flush() == b""
