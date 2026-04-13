"""Journal MCP service — search, recent, get_by_id."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select

from app.core.database import get_async_session
from app.models.journal_entry import JournalEntry


class JournalService:
    def __init__(self, retriever=None, embedder=None):
        self.retriever = retriever
        self.embedder = embedder

    async def search(self, user_id: str, query: str) -> list[dict[str, Any]]:
        """Semantic search over journal entries via pgvector."""
        if not self.embedder or not self.retriever:
            return []
        embedding = await self.embedder.embed(query)
        results = await self.retriever.search(embedding, user_id)
        return [
            {
                "content": r["content"],
                "score": r["score"],
                "metadata": r.get("metadata", {}),
            }
            for r in results
        ]

    async def recent(self, user_id: str, limit: int = 5) -> list[dict[str, Any]]:
        """Return the N most recent journal entries for a user."""
        uid = uuid.UUID(user_id)
        async with get_async_session() as db:
            result = await db.execute(
                select(JournalEntry)
                .where(JournalEntry.user_id == uid)
                .order_by(JournalEntry.created_at.desc())
                .limit(limit)
            )
            entries = result.scalars().all()
            return [
                {
                    "id": str(e.id),
                    "title": e.title,
                    "content": e.content,
                    "mood_score": e.mood_score,
                    "tags": e.tags,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                }
                for e in entries
            ]

    async def get_by_id(self, entry_id: str) -> dict[str, Any] | None:
        """Return a single journal entry by ID."""
        async with get_async_session() as db:
            entry = await db.get(JournalEntry, uuid.UUID(entry_id))
            if entry is None:
                return None
            return {
                "id": str(entry.id),
                "title": entry.title,
                "content": entry.content,
                "mood_score": entry.mood_score,
                "tags": entry.tags,
                "created_at": entry.created_at.isoformat() if entry.created_at else None,
            }
