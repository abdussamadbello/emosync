"""Shared state schema for the EmoSync agent graph."""

from __future__ import annotations

from typing import TypedDict


class AgentState(TypedDict, total=False):
    """State that flows through the Historian → Specialist → Anchor pipeline.

    Keys are additive — each node reads what it needs and writes its outputs.
    """

    # --- Inputs (set before the graph runs) ---
    user_message: str
    conversation_id: str
    # Prior turns for context: list of {"role": "user"|"assistant", "content": str}
    conversation_history: list[dict[str, str]]
    route_mode: str
    route_reason: str
    use_retrieval: bool

    # --- Historian outputs ---
    # Calendar events near today (stub until MCP is wired)
    calendar_context: list[str]
    # Journal snippets relevant to the user's message (stub until MCP is wired)
    journal_context: list[str]
    # Structured briefing: {"date_insights": str, "journal_insights": str}
    historian_briefing: dict[str, str]

    # --- Therapeutic context (loaded by Historian) ---
    user_id: str
    user_profile: dict
    assessment_context: dict
    treatment_plan: dict
    recent_moods: list[dict]

    # --- Specialist output ---
    specialist_response: str

    # --- Anchor (final) output ---
    final_response: str
