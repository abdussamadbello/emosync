from __future__ import annotations

import logging
import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select

from app.core.database import get_async_session
from app.models.conversation import Conversation
from app.models.embedding_chunk import EmbeddingChunk

logger = logging.getLogger(__name__)


class VectorRetriever:
    """Database-backed semantic search over stored embedding chunks.

    Uses pgvector's cosine distance operator (<=>) for efficient in-database
    similarity search instead of loading all rows into Python.
    """

    _empty_store_warned = False

    @staticmethod
    def cosine_similarity(a: list[float], b: list[float]) -> float:
        """Python fallback — kept for tests that mock search()."""
        import numpy as np

        arr_a = np.array(a)
        arr_b = np.array(b)
        norm_product = np.linalg.norm(arr_a) * np.linalg.norm(arr_b)
        if norm_product == 0:
            return 0.0
        return float(np.dot(arr_a, arr_b) / norm_product)

    async def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        *,
        sources: Sequence[str] | None = None,
        conversation_id: str | uuid.UUID | None = None,
        user_id: str | uuid.UUID | None = None,
    ) -> list[dict[str, Any]]:
        # pgvector cosine distance: 0 = identical, 2 = opposite.
        # Score = 1 - distance  →  1.0 = identical.
        cosine_distance = EmbeddingChunk.embedding.cosine_distance(query_embedding)

        stmt = (
            select(
                EmbeddingChunk,
                (1 - cosine_distance).label("score"),
            )
            .where(EmbeddingChunk.embedding.is_not(None))
            .order_by(cosine_distance)
            .limit(top_k)
        )

        if sources:
            stmt = stmt.where(EmbeddingChunk.extra_metadata["source"].astext.in_(list(sources)))

        if conversation_id is not None:
            stmt = stmt.where(EmbeddingChunk.conversation_id == self._coerce_uuid(conversation_id))

        if user_id is not None:
            stmt = stmt.join(Conversation, EmbeddingChunk.conversation_id == Conversation.id)
            stmt = stmt.where(Conversation.user_id == self._coerce_uuid(user_id))

        async with get_async_session() as session:
            try:
                result = await session.execute(stmt)
                rows = result.all()
            except Exception:
                logger.exception("Vector retrieval query failed.")
                return []

            if not rows:
                try:
                    await self._warn_if_store_empty(session)
                except Exception:
                    logger.exception("Failed to inspect embedding chunk availability.")
                return []

        return [
            {
                "id": str(item.id),
                "content": item.content,
                "metadata": item.extra_metadata or {},
                "score": float(score),
                "conversation_id": str(item.conversation_id) if item.conversation_id else None,
                "source_uri": item.source_uri,
            }
            for item, score in rows
        ]

    async def _warn_if_store_empty(self, session) -> None:
        if self.__class__._empty_store_warned:
            return

        count_stmt = select(func.count()).select_from(EmbeddingChunk).where(
            EmbeddingChunk.embedding.is_not(None)
        )
        count = await session.scalar(count_stmt)
        if count == 0:
            logger.warning("No embedding chunks found in database — retrieval will return empty results.")
            self.__class__._empty_store_warned = True

    @staticmethod
    def _coerce_uuid(value: str | uuid.UUID) -> uuid.UUID:
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))
