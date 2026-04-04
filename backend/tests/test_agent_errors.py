"""Tests for agent pipeline error handling and fallback behavior."""

from __future__ import annotations

import pytest

from app.services.chat_turn import run_turn_full, _strip_trailing_prosody_hint


@pytest.mark.asyncio
async def test_stub_response_when_no_api_key():
    """Without GEMINI_API_KEY, run_turn_full returns a deterministic stub."""
    text, prosody = await run_turn_full(
        user_message="I'm feeling sad today",
        conversation_id="00000000-0000-0000-0000-000000000001",
        user_message_id="00000000-0000-0000-0000-000000000002",
        conversation_history=[],
    )
    assert "[stub assistant]" in text
    assert "feeling sad today" in text
    assert prosody is not None


@pytest.mark.asyncio
async def test_stub_response_truncates_long_message():
    """Stub response truncates user messages longer than 120 chars."""
    long_msg = "x" * 200
    text, _ = await run_turn_full(
        user_message=long_msg,
        conversation_id="00000000-0000-0000-0000-000000000001",
        user_message_id="00000000-0000-0000-0000-000000000002",
    )
    assert "..." in text


class TestStripProsodyHint:
    def test_strips_trailing_hint(self):
        text = "I understand how you feel. [speak slowly, warm tone]"
        cleaned, hint = _strip_trailing_prosody_hint(text)
        assert cleaned == "I understand how you feel."
        assert hint == "speak slowly, warm tone"

    def test_no_hint_returns_none(self):
        text = "I understand how you feel."
        cleaned, hint = _strip_trailing_prosody_hint(text)
        assert cleaned == text
        assert hint is None

    def test_empty_brackets_returns_none(self):
        text = "Hello []"
        cleaned, hint = _strip_trailing_prosody_hint(text)
        # Empty brackets don't match the 1-100 char pattern
        assert hint is None

    def test_mid_text_brackets_not_stripped(self):
        text = "I see [your point] and I agree."
        cleaned, hint = _strip_trailing_prosody_hint(text)
        # Not trailing, so no strip
        assert hint is None
