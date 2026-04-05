from __future__ import annotations

from typing import Any

from app.ingestion.vector_retriever import VectorRetriever


class JournalRetriever:
    """Database-backed retrieval for journal-like embedding chunks."""

    def __init__(self) -> None:
        self.retriever = VectorRetriever()

    async def search(
        self,
        query_embedding: list[float],
        user_id: str | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        return await self.retriever.search(
            query_embedding,
            top_k=limit,
            user_id=user_id,
            sources=("journal",),
        )
