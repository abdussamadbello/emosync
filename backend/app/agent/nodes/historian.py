"""Historian — gathers context from MCP servers + vector store (CBT PDF)."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.llm import get_historian_llm
from app.agent.prompts import HISTORIAN_SYSTEM
from app.agent.state import AgentState
from app.core.config import settings
from app.mcp.calendar.service import CalendarService
from app.mcp.journal.embedding import Embedder
from app.ingestion.vector_retriever import VectorRetriever

logger = logging.getLogger(__name__)

LLM_TIMEOUT_SECONDS = 30.0


async def _embed_user_message(user_message: str) -> list[float] | None:
    """Embed the user message once for reuse across retrievals."""
    if not user_message.strip():
        return None
    try:
        embedder = Embedder()
        return await embedder.embed(user_message)
    except Exception:
        logger.exception("Failed to embed user message.")
        return None


async def retrieve_relevant_chunks(
    query: str, top_k: int = 5, *, query_embedding: list[float] | None = None,
) -> list[str]:
    """Return top-K semantically relevant CBT chunks stored in the database."""
    retriever = VectorRetriever()

    if not query.strip():
        return []

    try:
        if query_embedding is None:
            query_embedding = await _embed_user_message(query)
        if query_embedding is None:
            return []
        results = await retriever.search(
            query_embedding,
            top_k=top_k,
            sources=("cbt_pdf",),
        )
        return [item["content"] for item in results if item.get("content")]
    except Exception:
        logger.exception("Semantic CBT retrieval failed.")
        return []


async def retrieve_journal_context(
    user_message: str, *, query_embedding: list[float] | None = None,
) -> list[dict]:
    """Retrieve journal entries semantically relevant to the user's message."""
    if not user_message.strip():
        return []

    try:
        if query_embedding is None:
            query_embedding = await _embed_user_message(user_message)
        if query_embedding is None:
            return []
        retriever = VectorRetriever()
        return await retriever.search(
            query_embedding,
            top_k=5,
            sources=("journal",),
        )
    except ValueError:
        logger.warning("Journal retrieval received an invalid embedding query.")
        return []
    except Exception:
        logger.exception("Journal context retrieval failed.")
        return []


async def _load_calendar_context(
    calendar_service: CalendarService, state: AgentState,
) -> list[str]:
    """Load upcoming calendar events for the user, if user context available."""
    try:
        user_id = state.get("user_id", "")
        if not user_id:
            return []
        ctx = await calendar_service.get_context(user_id)
        return [
            f"{e.title} on {e.date} ({e.type})"
            for e in ctx.upcoming_events
        ]
    except Exception:
        logger.exception("Failed to load calendar context.")
        return []


def _build_historian_prompt(state: AgentState, query_chunks: list[str] | None = None) -> str:
    """Build the user-facing prompt for the Historian with available context."""
    query_chunks = query_chunks or []
    parts: list[str] = []

    # Conversation history (last 10 turns)
    history = state.get("conversation_history", [])
    if history:
        recent = history[-10:]
        parts.append("## Recent conversation")
        for turn in recent:
            parts.append(f"**{turn['role'].title()}**: {turn['content']}")

    # MCP Calendar context
    calendar = state.get("calendar_context", [])
    if calendar:
        parts.append("\n## Calendar events")
        for event in calendar:
            parts.append(f"- {event}")
    else:
        parts.append("\n## Calendar events\nNo calendar data available yet (MCP not connected).")

    # MCP Journal context
    journal = state.get("journal_context", [])
    if journal:
        parts.append("\n## Journal & CBT snippets")
        for snippet in journal:
            parts.append(f"- {snippet}")
    else:
        parts.append("\n## Journal & CBT snippets\nNo journal data available yet (MCP not connected).")

    # CBT PDF context from ingestion pipeline
    if query_chunks:
        parts.append("\n## CBT content chunks")
        for chunk in query_chunks:
            parts.append(f"- {chunk}")

    # Current user message
    parts.append(f"\n## Current user message\n{state.get('user_message', '')}")
    parts.append(
        "\nProvide your contextual briefing as JSON with keys "
        '"date_insights" and "journal_insights".'
    )
    parts.append(
        "\nAlso identify if the user's patterns align with CBT concepts such as "
        "cognitive distortions, emotional patterns, or behavioral habits."
    )

    return "\n".join(parts)


def _extract_json_from_llm_response(content: str) -> dict:
    """Extract JSON from an LLM response that may be wrapped in markdown fences."""
    if "```json" in content:
        json_str = content.split("```json", 1)[1].split("```", 1)[0].strip()
        return json.loads(json_str)
    if "```" in content:
        json_str = content.split("```", 1)[1].split("```", 1)[0].strip()
        return json.loads(json_str)
    return json.loads(content.strip())


async def historian_node(state: AgentState) -> dict[str, Any]:
    """Run the Historian agent to gather contextual briefing."""
    user_message = state.get("user_message", "")

    # Embed once, then run all retrievals in parallel.
    query_embedding = await _embed_user_message(user_message)

    calendar_service = CalendarService()

    journal_results, query_chunks, calendar_ctx = await asyncio.gather(
        retrieve_journal_context(user_message, query_embedding=query_embedding),
        retrieve_relevant_chunks(user_message, top_k=5, query_embedding=query_embedding),
        _load_calendar_context(calendar_service, state),
    )

    # Use DB-loaded calendar context, falling back to state
    calendar_context = calendar_ctx if calendar_ctx else state.get("calendar_context", [])

    journal_context = [
        f"{item['content']} (score={round(item['score'], 3)})"
        for item in journal_results
    ]

    llm = get_historian_llm()

    prompt = _build_historian_prompt(state, query_chunks)
    messages = [SystemMessage(content=HISTORIAN_SYSTEM), HumanMessage(content=prompt)]

    response_content: str | None = None
    try:
        response = await asyncio.wait_for(llm.ainvoke(messages), timeout=LLM_TIMEOUT_SECONDS)
        content = response.content
        response_content = content if isinstance(content, str) else str(content)

        if isinstance(content, str):
            briefing = _extract_json_from_llm_response(content)
        elif isinstance(content, list) and content and isinstance(content[0], str):
            briefing = _extract_json_from_llm_response(content[0])
        else:
            briefing = {
                "date_insights": "No specific date context identified.",
                "journal_insights": str(content),
            }
    except asyncio.TimeoutError:
        logger.error("Historian LLM call timed out after %ss.", LLM_TIMEOUT_SECONDS)
        briefing = {
            "date_insights": "Context unavailable (timeout).",
            "journal_insights": "Context unavailable (timeout).",
        }
    except (json.JSONDecodeError, IndexError, ValueError):
        logger.warning("Historian returned non-JSON; using raw text as insights.")
        briefing = {
            "date_insights": "No specific date context identified.",
            "journal_insights": response_content or "No journal context available.",
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
        "cbt_chunks": query_chunks,
        "historian_briefing": briefing,
    }
