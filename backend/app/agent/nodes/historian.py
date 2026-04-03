"""Historian — gathers context from MCP servers + vector store (CBT PDF)."""

from __future__ import annotations

import json
import logging
from typing import Any, List
import numpy as np

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.agent.prompts import HISTORIAN_SYSTEM
from app.agent.state import AgentState
from app.core.config import settings

from app.mcp.journal.embedding import Embedder
from app.ingestion.vector_retriever import VectorRetriever



# For vector store querying
import os
import json as js

logger = logging.getLogger(__name__)

VECTOR_STORE_PATH = os.path.join("backend", "data", "vector_store.json")


def load_vector_store() -> List[dict]:
    """Load chunks + embeddings from the vector store."""
    if not os.path.exists(VECTOR_STORE_PATH):
        return []
    with open(VECTOR_STORE_PATH, "r", encoding="utf-8") as f:
        return js.load(f)


def retrieve_relevant_chunks(query: str, top_k: int = 5) -> List[str]:
    """Return top-K chunks from the vector store for the current query."""
    store = load_vector_store()
    if not store:
        return []

    

    query_emb = np.array([0.0] * len(store[0]["embedding"]))  # placeholder if needed
    # Use the correct key — e.g., "content" or "chunk"
    key_name = "content" if "content" in store[0] else "chunk"
    
    # For now, simple retrieval: just take top_k chunks (later we can do similarity search)
    chunks = [item[key_name] for item in store[:top_k]]
    return chunks


def _build_historian_prompt(state: AgentState, query_chunks: List[str]) -> str:
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

# Real semantic retrieval for journal context
async def retrieve_journal_context(user_message: str):
    embedder = Embedder()
    retriever = VectorRetriever()
    query_embedding = await embedder.embed(user_message)
    results = retriever.search(query_embedding)
    return results


async def historian_node(state: AgentState) -> dict[str, Any]:
    """Run the Historian agent to gather contextual briefing."""
    calendar_context = state.get("calendar_context", [])
    journal_results = await retrieve_journal_context(state.get("user_message", ""))
    journal_context = [
        f"{item['content']} (score={round(item['score'], 3)})"
        for item in journal_results
    ]

    # Retrieve relevant CBT chunks
    query_chunks = retrieve_relevant_chunks(state.get("user_message", ""), top_k=5)

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite",
        google_api_key=settings.gemini_api_key,
        temperature=0.3,
    )

    prompt = _build_historian_prompt(state, query_chunks)
    messages = [SystemMessage(content=HISTORIAN_SYSTEM), HumanMessage(content=prompt)]

    try:
        response = await llm.ainvoke(messages)
        content = response.content

        # Remove markdown code fences
        if isinstance(content, str) and "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]

        if isinstance(content, str):
            briefing = json.loads(content.strip())
        elif isinstance(content, list) and content and isinstance(content[0], str):
            briefing = json.loads(content[0].strip())
        else:
            # Fallback: cannot parse, use default
            briefing = {
                "date_insights": "No specific date context identified.",
                "journal_insights": str(content),
            }
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
        "cbt_chunks": query_chunks,
        "historian_briefing": briefing,
    }