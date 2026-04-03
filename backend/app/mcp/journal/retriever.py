from __future__ import annotations

from typing import Any, List

from app.core.vector_store import LocalVectorStore


class JournalRetriever:
    """Local vector search (no DB)."""

    def __init__(self):
        self.store = LocalVectorStore()

    async def search(
        self,
        query_embedding: list[float],
        user_id: str | None = None,
        limit: int = 5,
    ) -> List[dict[str, Any]]:

        results = self.store.search(query_embedding, limit=limit)

        filtered = [
            r for r in results
            if r["metadata"].get("source") in ("journal", "cbt_pdf")
        ]

        return filtered
