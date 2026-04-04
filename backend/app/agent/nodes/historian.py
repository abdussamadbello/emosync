"""Historian — gathers context from MCP servers + vector store (CBT PDF)."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.agent.prompts import HISTORIAN_SYSTEM
from app.agent.state import AgentState
from app.core.config import settings
from app.mcp.journal.embedding import Embedder
from app.ingestion.vector_retriever import VectorRetriever

logger = logging.getLogger(__name__)

LLM_TIMEOUT_SECONDS = 30.0
VECTOR_STORE_PATH = os.path.join("backend", "data", "vector_store.json")

_vector_store_warned = False


async def retrieve_relevant_chunks(query: str, top_k: int = 5) -> list[str]:
    """Return top-K semantically relevant chunks from the CBT vector store."""
    global _vector_store_warned

    if not os.path.exists(VECTOR_STORE_PATH):
        if not _vector_store_warned:
            logger.warning("Vector store not found at %s — CBT context unavailable.", VECTOR_STORE_PATH)
            _vector_store_warned = True
        return []

    try:
        retriever = VectorRetriever(path=VECTOR_STORE_PATH)
    except (FileNotFoundError, json.JSONDecodeError):
        logger.warning("Failed to load vector store at %s.", VECTOR_STORE_PATH)
        return []

    if not retriever.store:
        return []

    try:
        embedder = Embedder()
        query_embedding = await embedder.embed(query)
        results = retriever.search(query_embedding, top_k=top_k)
        return [item["content"] for item in results if item.get("content")]
    except Exception:
        logger.exception("Semantic retrieval failed; falling back to naive top-k.")
        key_name = "content" if "content" in retriever.store[0] else "chunk"
        return [item[key_name] for item in retriever.store[:top_k] if item.get(key_name)]


async def retrieve_journal_context(user_message: str) -> list[dict]:
    """Retrieve journal entries semantically relevant to the user's message."""
    try:
        embedder = Embedder()
        retriever = VectorRetriever()
        query_embedding = await embedder.embed(user_message)
        return retriever.search(query_embedding)
    except FileNotFoundError:
        logger.debug("Vector store not found for journal context.")
        return []
    except Exception:
        logger.exception("Journal context retrieval failed.")
        return []


def _build_historian_prompt(state: AgentState, query_chunks: list[str]) -> str:
    """Build the user-facing prompt for the Historian with available context."""
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
    calendar_context = state.get("calendar_context", [])
    journal_results = await retrieve_journal_context(state.get("user_message", ""))
    journal_context = [
        f"{item['content']} (score={round(item['score'], 3)})"
        for item in journal_results
    ]

    # Retrieve relevant CBT chunks via semantic search.
    query_chunks = await retrieve_relevant_chunks(state.get("user_message", ""), top_k=5)

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite",
        google_api_key=settings.gemini_api_key,
        temperature=0.3,
    )

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
