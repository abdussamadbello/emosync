"""The Anchor — trauma-informed safety and validation layer.

Reviews the Specialist's draft response and ensures it meets safety,
validation, and emotional-pacing criteria before reaching the user.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.agent.prompts import ANCHOR_SYSTEM
from app.agent.state import AgentState
from app.core.config import settings

logger = logging.getLogger(__name__)


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

    parts.append(
        "\nReview the draft against all safety criteria. Output the final "
        "polished response for the user (with prosody hint at the end in brackets)."
    )

    return "\n".join(parts)


async def anchor_node(state: AgentState) -> dict[str, Any]:
    """Run the Anchor agent to validate and finalize the response."""

    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-pro",
        google_api_key=settings.gemini_api_key,
        temperature=0.3,
    )

    prompt = _build_anchor_prompt(state)
    messages = [SystemMessage(content=ANCHOR_SYSTEM), HumanMessage(content=prompt)]

    try:
        response = await llm.ainvoke(messages)
        final_response = response.content
    except Exception:
        logger.exception("Anchor LLM call failed; passing through Specialist response.")
        final_response = state.get(
            "specialist_response",
            "I'm here with you. What you're feeling matters. "
            "Would you like to share more about what's going on?",
        )

    return {"final_response": final_response}
