"""EmoSync Journal MCP Server.

Exposes journal entries as MCP tools for external AI clients.
Run with: python -m app.servers.journal_mcp
Or via entry point: emosync-journal-mcp

Tools:
  - search_journal: Semantic search over journal entries via pgvector
  - recent_journal_entries: Get the N most recent journal entries
  - get_journal_entry: Get a single journal entry by ID
"""

from __future__ import annotations

import json

from fastmcp import FastMCP

mcp = FastMCP(
    name="EmoSync Journal",
    instructions=(
        "Journal MCP server for the EmoSync grief coaching platform. "
        "Provides semantic search and retrieval of user journal entries."
    ),
)


@mcp.tool
async def search_journal(user_id: str, query: str, top_k: int = 5) -> str:
    """Semantic search over a user's journal entries using pgvector cosine similarity.

    Args:
        user_id: UUID of the user whose journals to search.
        query: Natural language search query to match against journal content.
        top_k: Maximum number of results to return (default 5).

    Returns:
        JSON array of matching entries with content, score, and metadata.
    """
    from app.mcp.journal.embedding import Embedder
    from app.mcp.journal.retriever import JournalRetriever
    from app.mcp.journal.service import JournalService

    service = JournalService(retriever=JournalRetriever(), embedder=Embedder())
    results = await service.search(user_id, query)
    return json.dumps(results, default=str)


@mcp.tool
async def recent_journal_entries(user_id: str, limit: int = 5) -> str:
    """Get the most recent journal entries for a user, ordered by creation date.

    Args:
        user_id: UUID of the user.
        limit: Maximum number of entries to return (default 5).

    Returns:
        JSON array of journal entries with id, title, content, mood_score, tags, created_at.
    """
    from app.mcp.journal.service import JournalService

    service = JournalService()
    results = await service.recent(user_id, limit)
    return json.dumps(results, default=str)


@mcp.tool
async def get_journal_entry(entry_id: str) -> str:
    """Get a single journal entry by its ID.

    Args:
        entry_id: UUID of the journal entry.

    Returns:
        JSON object with entry details, or "null" if not found.
    """
    from app.mcp.journal.service import JournalService

    service = JournalService()
    result = await service.get_by_id(entry_id)
    return json.dumps(result, default=str)


if __name__ == "__main__":
    mcp.run()
