from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid
from collections.abc import AsyncIterator
from datetime import date, timedelta
from typing import Any

from app.core.config import settings

"""Agent integration boundary (M3 → M4).

`run_turn` is the single hook the HTTP layer calls.  When `GEMINI_API_KEY` is
configured, it runs the full LangGraph grief-coach pipeline (Historian →
Specialist → Anchor).  Otherwise it falls back to a deterministic stub so
local dev and CI work without an API key.
"""

logger = logging.getLogger(__name__)


def _extract_suggestions(text: str) -> tuple[str, dict[str, Any] | None]:
    """Split the suggestions JSON block from the response text.

    Returns (clean_text, suggestions_dict). If no valid block is found,
    suggestions_dict is None and clean_text is the original text.
    """
    pattern = r"```suggestions\s*\n(.*?)```"
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        return text, None

    clean = text[: match.start()].rstrip()
    try:
        suggestions = json.loads(match.group(1).strip())
        return clean, suggestions
    except (json.JSONDecodeError, ValueError):
        logger.warning("Malformed suggestions block; ignoring.")
        return clean, None


async def _persist_plan(user_id: str, plan_data: dict[str, Any]) -> None:
    """Save an AI-generated treatment plan to the database.

    Marks any existing active plan as completed before creating the new one.
    """
    from app.core.database import get_async_session
    from app.models.treatment_plan import TreatmentGoal, TreatmentPlan

    uid = uuid.UUID(user_id)
    title = plan_data.get("title", "Healing Plan")
    goals = plan_data.get("goals", [])

    async with get_async_session() as session:
        async with session.begin():
            # Mark existing active plans as completed
            from sqlalchemy import update
            await session.execute(
                update(TreatmentPlan)
                .where(TreatmentPlan.user_id == uid, TreatmentPlan.status == "active")
                .values(status="completed")
            )

            plan = TreatmentPlan(user_id=uid, title=title, status="active")
            session.add(plan)
            await session.flush()

            for goal in goals:
                target = None
                if goal.get("target_date"):
                    try:
                        target = date.fromisoformat(goal["target_date"])
                    except ValueError:
                        target = date.today() + timedelta(days=30)
                session.add(
                    TreatmentGoal(
                        plan_id=plan.id,
                        description=goal.get("description", ""),
                        target_date=target,
                        status="not_started",
                    )
                )


async def run_turn(
    *,
    user_message: str,
    conversation_id: str,
    user_message_id: str,
    conversation_history: list[dict[str, str]] | None = None,
    user_id: str | None = None,
) -> AsyncIterator[str]:
    """Yield text fragments for the assistant reply.

    When GEMINI_API_KEY is set, the full agentic pipeline is used.
    Otherwise a deterministic stub is returned (useful for tests / local dev).
    """
    text, _prosody_hint, _suggestions = await run_turn_full(
        user_message=user_message,
        conversation_id=conversation_id,
        user_message_id=user_message_id,
        conversation_history=conversation_history,
        user_id=user_id,
    )

    words = text.split()
    for i, word in enumerate(words):
        token = word + (" " if i < len(words) - 1 else "")
        yield token


async def run_turn_full(
    *,
    user_message: str,
    conversation_id: str,
    user_message_id: str,
    conversation_history: list[dict[str, str]] | None = None,
    user_id: str | None = None,
) -> tuple[str, str | None, dict[str, Any] | None]:
    """Return (display_text, prosody_hint, suggestions).

    The text is always safe for display. Prosody is returned separately for
    voice synthesis pipelines. Suggestions is the parsed JSON block (or None).
    """
    if not settings.gemini_api_key:
        text = await _stub_response_text(
            user_message=user_message,
            conversation_id=conversation_id,
            user_message_id=user_message_id,
        )
        return text, "gentle, warm tone", None

    final_text = await _agent_response_text(
        user_message=user_message,
        conversation_id=conversation_id,
        user_message_id=user_message_id,
        conversation_history=conversation_history or [],
        user_id=user_id,
    )

    # Extract suggestions block before stripping prosody
    text_no_suggestions, suggestions = _extract_suggestions(final_text)
    cleaned, prosody = _strip_trailing_prosody_hint(text_no_suggestions)

    # Persist auto-generated plan if present
    if suggestions and suggestions.get("plan_generation") and user_id:
        try:
            await _persist_plan(user_id, suggestions["plan_generation"])
        except Exception:
            logger.exception("Failed to persist auto-generated plan.")

    return cleaned, prosody, suggestions


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


class StreamResult:
    """Accumulates streamed tokens and post-stream metadata."""

    def __init__(self) -> None:
        self.full_text: str = ""
        self.suggestions: dict[str, Any] | None = None


async def stream_turn(
    *,
    user_message: str,
    conversation_id: str,
    user_message_id: str,
    conversation_history: list[dict[str, str]] | None = None,
    user_id: str | None = None,
    result: StreamResult | None = None,
) -> AsyncIterator[str]:
    """Yield tokens in real-time as the Anchor LLM generates them.

    Runs Historian → Specialist through the pre-anchor graph, then streams
    the Anchor's output token-by-token.  Falls back to the stub in dev mode.

    The caller can pass a ``StreamResult`` to collect the full text and
    suggestions after the stream completes.
    """
    if result is None:
        result = StreamResult()

    if not settings.gemini_api_key:
        text = await _stub_response_text(
            user_message=user_message,
            conversation_id=conversation_id,
            user_message_id=user_message_id,
        )
        result.full_text = text
        for word in text.split():
            yield word + " "
        return

    from app.agent.graph import pre_anchor_graph
    from app.agent.nodes.anchor import stream_anchor
    from app.agent.state import AgentState

    initial_state: AgentState = {
        "user_message": user_message,
        "conversation_id": conversation_id,
        "conversation_history": conversation_history or [],
        "calendar_context": [],
        "journal_context": [],
        "user_id": str(user_id) if user_id else "",
    }

    fallback = (
        "I hear you, and what you're feeling is completely valid. "
        "I'm having a brief difficulty, but I'm still here with you. "
        "Could you tell me a bit more about what's on your mind?"
    )

    try:
        # Run Historian → Specialist (non-streaming)
        pre_state = await pre_anchor_graph.ainvoke(initial_state)

        # Stream Anchor output token-by-token
        raw_chunks: list[str] = []
        async for token in stream_anchor(pre_state):
            raw_chunks.append(token)
            yield token

        raw_text = "".join(raw_chunks)
    except Exception:
        logger.exception("Streaming pipeline failed; returning fallback.")
        raw_text = fallback
        yield fallback

    # Post-stream: extract suggestions and prosody from the accumulated text
    text_no_suggestions, suggestions = _extract_suggestions(raw_text)
    cleaned, _prosody = _strip_trailing_prosody_hint(text_no_suggestions)

    result.full_text = cleaned
    result.suggestions = suggestions

    # Persist plan if generated
    if suggestions and suggestions.get("plan_generation") and user_id:
        try:
            await _persist_plan(user_id, suggestions["plan_generation"])
        except Exception:
            logger.exception("Failed to persist auto-generated plan.")


async def _agent_response_text(
    *,
    user_message: str,
    conversation_id: str,
    user_message_id: str,
    conversation_history: list[dict[str, str]],
    user_id: str | None = None,
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
        "user_id": str(user_id) if user_id else "",
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
