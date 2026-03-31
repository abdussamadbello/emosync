from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import AsyncIterator

from app.core.config import settings

"""Agent integration boundary (M3 → M4).

`run_turn` is the single hook the HTTP layer calls.  When `GEMINI_API_KEY` is
configured, it runs the full LangGraph grief-coach pipeline (Historian →
Specialist → Anchor).  Otherwise it falls back to a deterministic stub so
local dev and CI work without an API key.
"""

logger = logging.getLogger(__name__)


async def run_turn(
    *,
    user_message: str,
    conversation_id: str,
    user_message_id: str,
    conversation_history: list[dict[str, str]] | None = None,
) -> AsyncIterator[str]:
    """Yield text fragments for the assistant reply.

    When GEMINI_API_KEY is set, the full agentic pipeline is used.
    Otherwise a deterministic stub is returned (useful for tests / local dev).
    """
    text, _prosody_hint = await run_turn_full(
        user_message=user_message,
        conversation_id=conversation_id,
        user_message_id=user_message_id,
        conversation_history=conversation_history,
    )

    words = text.split()
    for i, word in enumerate(words):
        token = word + (" " if i < len(words) - 1 else "")
        yield token
        await asyncio.sleep(0.01)


async def run_turn_full(
    *,
    user_message: str,
    conversation_id: str,
    user_message_id: str,
    conversation_history: list[dict[str, str]] | None = None,
) -> tuple[str, str | None]:
    """Return assistant text and optional prosody hint.

    The text is always safe for display. Prosody is returned separately for
    voice synthesis pipelines.
    """
    if not settings.gemini_api_key:
        text = await _stub_response_text(
            user_message=user_message,
            conversation_id=conversation_id,
            user_message_id=user_message_id,
        )
        return text, "gentle, warm tone"

    final_text = await _agent_response_text(
        user_message=user_message,
        conversation_id=conversation_id,
        user_message_id=user_message_id,
        conversation_history=conversation_history or [],
    )
    cleaned, prosody = _strip_trailing_prosody_hint(final_text)
    return cleaned, prosody


async def _stub_response(
    *,
    user_message: str,
    conversation_id: str,
    user_message_id: str,
) -> AsyncIterator[str]:
    """Deterministic stub — no API key required."""
    preview = user_message.strip().replace("\n", " ")
    if len(preview) > 120:
        preview = preview[:117] + "..."
    stub = (
        f"[stub assistant] Thanks for sharing. (conversation={conversation_id[:8]}…, "
        f"msg={user_message_id[:8]}…) You said: {preview}"
    )
    for part in stub.split():
        yield part + " "
        await asyncio.sleep(0.02)


async def _stub_response_text(
    *,
    user_message: str,
    conversation_id: str,
    user_message_id: str,
) -> str:
    preview = user_message.strip().replace("\n", " ")
    if len(preview) > 120:
        preview = preview[:117] + "..."
    return (
        f"[stub assistant] Thanks for sharing. (conversation={conversation_id[:8]}…, "
        f"msg={user_message_id[:8]}…) You said: {preview}"
    )


async def _agent_response(
    *,
    user_message: str,
    conversation_id: str,
    user_message_id: str,
    conversation_history: list[dict[str, str]],
) -> AsyncIterator[str]:
    """Run the full Historian → Specialist → Anchor pipeline via LangGraph."""
    final_text = await _agent_response_text(
        user_message=user_message,
        conversation_id=conversation_id,
        user_message_id=user_message_id,
        conversation_history=conversation_history,
    )

    # Strip prosody hint before streaming to text (e.g. "[speak slowly, warm tone]")
    cleaned_text, _prosody = _strip_trailing_prosody_hint(final_text)

    # Stream word-by-word for SSE token events
    words = cleaned_text.split()
    for i, word in enumerate(words):
        token = word + (" " if i < len(words) - 1 else "")
        yield token
        await asyncio.sleep(0.01)


async def _agent_response_text(
    *,
    user_message: str,
    conversation_id: str,
    user_message_id: str,
    conversation_history: list[dict[str, str]],
) -> str:
    """Run the full Historian → Specialist → Anchor pipeline and return full text."""
    from app.agent.graph import grief_coach_graph
    from app.agent.state import AgentState

    initial_state: AgentState = {
        "user_message": user_message,
        "conversation_id": conversation_id,
        "conversation_history": conversation_history,
        "calendar_context": [],
        "journal_context": [],
    }

    try:
        result = await grief_coach_graph.ainvoke(initial_state)
        final_text = result.get("final_response", "")
    except Exception:
        logger.exception("Agent pipeline failed; returning fallback.")
        final_text = (
            "I hear you, and what you're feeling is completely valid. "
            "I'm having a brief difficulty, but I'm still here with you. "
            "Could you tell me a bit more about what's on your mind?"
        )

    return final_text


def _strip_trailing_prosody_hint(text: str) -> tuple[str, str | None]:
    """Extract trailing prosody hint from the final response.

    Expected shape: "... [speak slowly, warm tone]".
    """
    match = re.search(r"\[([^\[\]]{1,100})\]\s*$", text)
    if not match:
        return text, None
    hint = match.group(1).strip()
    cleaned = text[: match.start()].rstrip()
    return cleaned, hint or None
