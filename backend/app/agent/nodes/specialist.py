"""The Specialist — applies CBT, ACT, and Narrative Therapy frameworks.

Uses the Historian's contextual briefing + conversation history to craft
a therapeutically grounded response.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.agent.prompts import SPECIALIST_SYSTEM
from app.agent.state import AgentState
from app.core.config import settings

logger = logging.getLogger(__name__)


def _build_specialist_prompt(state: AgentState) -> str:
    """Assemble the prompt for the Specialist with historian briefing + history."""
    parts: list[str] = []

    # Historian briefing
    briefing = state.get("historian_briefing", {})
    parts.append("## Contextual briefing from The Historian")
    parts.append(f"**Date insights:** {briefing.get('date_insights', 'None available.')}")
    parts.append(f"**Journal insights:** {briefing.get('journal_insights', 'None available.')}")

    # Conversation history (last 10 turns)
    history = state.get("conversation_history", [])
    if history:
        parts.append("\n## Recent conversation history")
        for turn in history[-10:]:
            parts.append(f"**{turn['role'].title()}**: {turn['content']}")

    # Current message
    parts.append(f"\n## User's current message\n{state['user_message']}")
    parts.append(
        "\nRespond to the user using the most appropriate therapeutic framework(s). "
        "Be warm, concise (2-4 paragraphs), and ground your response in the "
        "context provided above when relevant."
    )

    return "\n".join(parts)


async def specialist_node(state: AgentState) -> dict[str, Any]:
    """Run the Specialist agent to generate a therapy-informed response."""

    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-pro",
        google_api_key=settings.gemini_api_key,
        temperature=0.7,
    )

    prompt = _build_specialist_prompt(state)
    messages = [SystemMessage(content=SPECIALIST_SYSTEM), HumanMessage(content=prompt)]

    try:
        response = await llm.ainvoke(messages)
        specialist_response = response.content
    except Exception:
        logger.exception("Specialist LLM call failed.")
        specialist_response = (
            "I hear you, and I want you to know that what you're feeling is completely valid. "
            "I'm having a moment of difficulty on my end, but I'm still here with you. "
            "Would you like to tell me more about what's on your mind?"
        )

    return {"specialist_response": specialist_response}
