"""The Historian — gathers context from MCP servers (Calendar + Journal).

Until MCP servers are wired (M5), this node stubs the context retrieval
and passes through empty/placeholder context so the downstream nodes
can still function.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.agent.prompts import HISTORIAN_SYSTEM
from app.agent.state import AgentState
from app.core.config import settings

logger = logging.getLogger(__name__)


def _build_historian_prompt(state: AgentState) -> str:
    """Build the user-facing prompt for the Historian with available context."""
    parts: list[str] = []

    # Conversation history (last 10 turns for context window efficiency)
    history = state.get("conversation_history", [])
    if history:
        recent = history[-10:]
        parts.append("## Recent conversation")
        for turn in recent:
            parts.append(f"**{turn['role'].title()}**: {turn['content']}")

    # MCP Calendar context (stub — will be replaced when MCP is wired)
    calendar = state.get("calendar_context", [])
    if calendar:
        parts.append("\n## Calendar events")
        for event in calendar:
            parts.append(f"- {event}")
    else:
        parts.append("\n## Calendar events\nNo calendar data available yet (MCP not connected).")

    # MCP Journal context (stub — will be replaced when MCP is wired)
    journal = state.get("journal_context", [])
    if journal:
        parts.append("\n## Journal snippets")
        for snippet in journal:
            parts.append(f"- {snippet}")
    else:
        parts.append("\n## Journal snippets\nNo journal data available yet (MCP not connected).")

    parts.append(f"\n## Current user message\n{state['user_message']}")
    parts.append(
        "\nProvide your contextual briefing as JSON with keys "
        '"date_insights" and "journal_insights".'
    )

    return "\n".join(parts)


async def historian_node(state: AgentState) -> dict[str, Any]:
    """Run the Historian agent to gather contextual briefing."""

    # --- MCP stub: In M5 these will call real MCP servers ---
    # For now, pass through whatever was seeded (empty lists by default).
    calendar_context = state.get("calendar_context", [])
    journal_context = state.get("journal_context", [])

    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-pro",
        google_api_key=settings.gemini_api_key,
        temperature=0.3,
    )

    prompt = _build_historian_prompt(state)
    messages = [SystemMessage(content=HISTORIAN_SYSTEM), HumanMessage(content=prompt)]

    try:
        response = await llm.ainvoke(messages)
        # Try to parse JSON from the response
        content = response.content
        # Strip markdown code fences if present
        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        briefing = json.loads(content.strip())
    except (json.JSONDecodeError, IndexError):
        logger.warning("Historian returned non-JSON; using raw text as insights.")
        briefing = {
            "date_insights": "No specific date context identified.",
            "journal_insights": response.content if "response" in dir() else "No journal context available.",
        }
    except Exception:
        logger.exception("Historian LLM call failed; continuing with empty context.")
        briefing = {
            "date_insights": "Context unavailable.",
            "journal_insights": "Context unavailable.",
        }

    return {
        "calendar_context": calendar_context,
        "journal_context": journal_context,
        "historian_briefing": briefing,
    }
