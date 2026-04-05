"""The Anchor — trauma-informed safety and validation layer.

Reviews the Specialist's draft response and ensures it meets safety,
validation, and emotional-pacing criteria before reaching the user.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.llm import get_anchor_llm
from app.agent.prompts import ANCHOR_SYSTEM
from app.agent.state import AgentState

logger = logging.getLogger(__name__)

LLM_TIMEOUT_SECONDS = 30.0


def _build_anchor_prompt(state: AgentState) -> str:
    """Build the review prompt for the Anchor with all relevant context."""
    parts: list[str] = []

    # Original user message
    parts.append(f"## User's message\n{state['user_message']}")

    # Historian briefing (so Anchor can verify no hallucinated context)
    briefing = state.get("historian_briefing", {})
    parts.append("\n## Historian's contextual briefing")
    parts.append(f"**Date insights:** {briefing.get('date_insights', 'None available.')}")
    parts.append(f"**Journal insights:** {briefing.get('journal_insights', 'None available.')}")

    # Specialist draft
    parts.append(f"\n## Specialist's draft response\n{state.get('specialist_response', '')}")

    # Assessment context for escalation
    assessment = state.get("assessment_context", {})
    if assessment:
        parts.append(f"\n## Assessment context")
        parts.append(f"{assessment.get('instrument', 'PHQ-9').upper()}: score {assessment.get('total_score', '?')}, severity: {assessment.get('severity', 'unknown')}")

    # Calendar triggers
    calendar = state.get("calendar_context", [])
    if calendar:
        parts.append(f"\n## Upcoming events")
        for event in calendar:
            parts.append(f"- {event}")

    parts.append(
        "\nReview the draft against all safety criteria. Output the final "
        "polished response for the user (with prosody hint at the end in brackets)."
    )

    return "\n".join(parts)


async def anchor_node(state: AgentState) -> dict[str, Any]:
    """Run the Anchor agent to validate and finalize the response."""

    llm = get_anchor_llm()

    prompt = _build_anchor_prompt(state)
    messages = [SystemMessage(content=ANCHOR_SYSTEM), HumanMessage(content=prompt)]

    passthrough = state.get(
        "specialist_response",
        "I'm here with you. What you're feeling matters. "
        "Would you like to share more about what's going on?",
    )
    try:
        response = await asyncio.wait_for(llm.ainvoke(messages), timeout=LLM_TIMEOUT_SECONDS)
        final_response = response.content
    except asyncio.TimeoutError:
        logger.error("Anchor LLM call timed out after %ss; passing through Specialist response.", LLM_TIMEOUT_SECONDS)
        final_response = passthrough
    except Exception:
        logger.exception("Anchor LLM call failed; passing through Specialist response.")
        final_response = passthrough

    return {"final_response": final_response}
