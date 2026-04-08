"""The Specialist — applies CBT, ACT, and Narrative Therapy frameworks.

Uses the Historian's contextual briefing + conversation history to craft
a therapeutically grounded response.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.context import (
    MAX_PROMPT_HISTORY_MESSAGES,
    trim_conversation_history,
    truncate_text,
)
from app.agent.llm import get_specialist_llm
from app.agent.prompts import SPECIALIST_SYSTEM
from app.agent.state import AgentState

logger = logging.getLogger(__name__)

LLM_TIMEOUT_SECONDS = 30.0


def _build_specialist_prompt(state: AgentState) -> str:
    """Assemble the prompt for the Specialist with historian briefing + history."""
    parts: list[str] = []

    # Historian briefing
    briefing = state.get("historian_briefing", {})
    parts.append("## Contextual briefing from The Historian")
    parts.append(f"**Date insights:** {briefing.get('date_insights', 'None available.')}")
    parts.append(f"**Journal insights:** {briefing.get('journal_insights', 'None available.')}")

    # Therapeutic context
    profile = state.get("user_profile", {})
    if profile:
        parts.append("\n## User profile")
        parts.append(f"Grief type: {truncate_text(profile.get('grief_type', 'unknown'), 80)}")
        parts.append(
            f"Support system: {truncate_text(profile.get('support_system', 'unknown'), 80)}"
        )
        approaches = profile.get('preferred_approaches', [])
        if approaches:
            parts.append(
                f"Preferred approaches: {truncate_text(', '.join(approaches[:3]), 120)}"
            )

    assessment = state.get("assessment_context", {})
    if assessment:
        parts.append("\n## Latest assessment")
        parts.append(f"{assessment.get('instrument', 'PHQ-9').upper()}: {assessment.get('total_score', '?')}/27 ({assessment.get('severity', 'unknown')})")

    plan = state.get("treatment_plan", {})
    if plan:
        parts.append(
            f"\n## Active treatment plan: {truncate_text(plan.get('title', 'Untitled'), 120)}"
        )
        for g in plan.get("goals", [])[:3]:
            parts.append(
                f"- [{g.get('status', '?')}] {truncate_text(g.get('description', ''), 140)}"
            )

    moods = state.get("recent_moods", [])
    if moods:
        scores = [m["score"] for m in moods if "score" in m]
        if scores:
            avg = sum(scores) / len(scores)
            parts.append(f"\n## Recent mood trend: avg {avg:.1f}/10 over {len(scores)} entries")

    # Conversation history (last 10 turns)
    history = trim_conversation_history(
        state.get("conversation_history", []),
        max_messages=MAX_PROMPT_HISTORY_MESSAGES,
    )
    if history:
        parts.append("\n## Recent conversation history")
        for turn in history:
            parts.append(f"**{turn['role'].title()}**: {turn['content']}")

    # Current message
    parts.append(f"\n## User's current message\n{truncate_text(state['user_message'], 900)}")
    route_mode = state.get("route_mode")
    if route_mode:
        parts.append(f"\n## Response mode\n{route_mode}")
    parts.append(
        "\nRespond to the user using the most appropriate therapeutic framework(s). "
        "Be warm, concise (2-4 paragraphs), and ground your response in the "
        "context provided above when relevant."
    )

    return "\n".join(parts)


async def specialist_node(state: AgentState) -> dict[str, Any]:
    """Run the Specialist agent to generate a therapy-informed response."""

    llm = get_specialist_llm()

    prompt = _build_specialist_prompt(state)
    messages = [SystemMessage(content=SPECIALIST_SYSTEM), HumanMessage(content=prompt)]

    fallback = (
        "I hear you, and I want you to know that what you're feeling is completely valid. "
        "I'm having a moment of difficulty on my end, but I'm still here with you. "
        "Would you like to tell me more about what's on your mind?"
    )
    try:
        response = await asyncio.wait_for(llm.ainvoke(messages), timeout=LLM_TIMEOUT_SECONDS)
        specialist_response = response.content
    except asyncio.TimeoutError:
        logger.error("Specialist LLM call timed out after %ss.", LLM_TIMEOUT_SECONDS)
        specialist_response = fallback
    except Exception:
        logger.exception("Specialist LLM call failed.")
        specialist_response = fallback

    return {"specialist_response": specialist_response}


async def stream_specialist(state: AgentState) -> AsyncIterator[str]:
    """Stream the Specialist response token-by-token for low-risk turns."""
    llm = get_specialist_llm()
    prompt = _build_specialist_prompt(state)
    messages = [SystemMessage(content=SPECIALIST_SYSTEM), HumanMessage(content=prompt)]

    fallback = state.get(
        "specialist_response",
        "I hear you, and what you're feeling matters. What feels most important right now?",
    )

    try:
        async for chunk in llm.astream(messages):
            token = chunk.content
            if token:
                yield token
    except Exception:
        logger.exception("Specialist streaming failed; yielding fallback response.")
        yield fallback
