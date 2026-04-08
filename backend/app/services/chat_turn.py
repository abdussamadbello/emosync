from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid
from collections.abc import AsyncIterator
from datetime import date, timedelta
from typing import Any

from app.agent.context import (
    MAX_HISTORY_MESSAGES,
    MAX_USER_MESSAGE_CHARS,
    trim_conversation_history,
    truncate_text,
)
from app.agent.routing import TurnRoute, decide_turn_route
from app.core.config import settings

"""Agent integration boundary (M3 → M4).

`run_turn` is the single hook the HTTP layer calls.  When `GEMINI_API_KEY` is
configured, it runs the full LangGraph grief-coach pipeline (Historian →
Specialist → Anchor).  Otherwise it falls back to a deterministic stub so
local dev and CI work without an API key.
"""

logger = logging.getLogger(__name__)


def _prepare_turn_inputs(
    *,
    user_message: str,
    conversation_history: list[dict[str, str]] | None,
) -> tuple[str, list[dict[str, str]], TurnRoute]:
    """Trim oversized context before routing the turn."""
    trimmed_message = truncate_text(user_message, MAX_USER_MESSAGE_CHARS)
    trimmed_history = trim_conversation_history(
        conversation_history,
        max_messages=MAX_HISTORY_MESSAGES,
    )
    route = decide_turn_route(trimmed_message, trimmed_history)
    return trimmed_message, trimmed_history, route


def _build_initial_state(
    *,
    user_message: str,
    conversation_id: str,
    conversation_history: list[dict[str, str]],
    user_id: str | None,
    route: TurnRoute,
) -> dict[str, Any]:
    return {
        "user_message": user_message,
        "conversation_id": conversation_id,
        "conversation_history": conversation_history,
        "calendar_context": [],
        "journal_context": [],
        "user_id": str(user_id) if user_id else "",
        "route_mode": route.mode,
        "route_reason": route.reason,
        "use_retrieval": route.use_retrieval,
    }


async def _run_historian_if_needed(
    state: dict[str, Any],
    route: TurnRoute,
) -> dict[str, Any]:
    if not route.use_historian:
        return state

    from app.agent.nodes.historian import historian_node

    updated = dict(state)
    updated.update(await historian_node(updated))
    return updated


async def _run_specialist_response(state: dict[str, Any]) -> dict[str, Any]:
    from app.agent.nodes.specialist import specialist_node

    updated = dict(state)
    updated.update(await specialist_node(updated))
    return updated


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
    prepared_message, prepared_history, route = _prepare_turn_inputs(
        user_message=user_message,
        conversation_history=conversation_history,
    )

    if not settings.gemini_api_key:
        text = await _stub_response_text(
            user_message=prepared_message,
            conversation_id=conversation_id,
            user_message_id=user_message_id,
        )
        return text, "gentle, warm tone", None

    final_text = await _agent_response_text(
        user_message=prepared_message,
        conversation_id=conversation_id,
        user_message_id=user_message_id,
        conversation_history=prepared_history,
        user_id=user_id,
        route=route,
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
    """Yield tokens in real time using the selected route for this turn.

    Low-risk turns stream directly from the Specialist. Higher-risk turns can
    still route through Historian and/or Anchor before the client sees text.
    The caller can pass a ``StreamResult`` to collect the final text and
    suggestions after the stream completes.
    """
    if result is None:
        result = StreamResult()

    prepared_message, prepared_history, route = _prepare_turn_inputs(
        user_message=user_message,
        conversation_history=conversation_history,
    )

    if not settings.gemini_api_key:
        text = await _stub_response_text(
            user_message=prepared_message,
            conversation_id=conversation_id,
            user_message_id=user_message_id,
        )
        result.full_text = text
        for word in text.split():
            yield word + " "
        return

    from app.agent.nodes.anchor import stream_anchor
    from app.agent.nodes.specialist import stream_specialist

    fallback = (
        "I hear you, and what you're feeling is completely valid. "
        "I'm having a brief difficulty, but I'm still here with you. "
        "Could you tell me a bit more about what's on your mind?"
    )

    try:
        initial_state = _build_initial_state(
            user_message=prepared_message,
            conversation_id=conversation_id,
            conversation_history=prepared_history,
            user_id=user_id,
            route=route,
        )
        route_state = await _run_historian_if_needed(initial_state, route)

        raw_chunks: list[str] = []
        if route.use_anchor:
            route_state = await _run_specialist_response(route_state)
            stream = stream_anchor(route_state)
        else:
            stream = stream_specialist(route_state)

        async for token in stream:
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
    route: TurnRoute,
) -> str:
    """Run the selected route and return full text."""
    initial_state = _build_initial_state(
        user_message=user_message,
        conversation_id=conversation_id,
        conversation_history=conversation_history,
        user_id=user_id,
        route=route,
    )

    try:
        state = await _run_historian_if_needed(initial_state, route)
        state = await _run_specialist_response(state)

        if route.use_anchor:
            from app.agent.nodes.anchor import anchor_node

            state.update(await anchor_node(state))
            final_text = str(state.get("final_response", ""))
        else:
            final_text = str(state.get("specialist_response", ""))
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
