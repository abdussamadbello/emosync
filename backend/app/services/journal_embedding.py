"""Auto-embed journal entries into embedding_chunks for pgvector search."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.embedding_chunk import EmbeddingChunk

logger = logging.getLogger(__name__)


async def embed_journal_entry(
    db: AsyncSession,
    entry_id: uuid.UUID,
    user_id: uuid.UUID,
    content: str,
) -> None:
    """Embed journal content and upsert into embedding_chunks.

    If GEMINI_API_KEY is not set, silently skips (stub mode).
    """
    if not settings.gemini_api_key:
        logger.debug("No GEMINI_API_KEY; skipping journal embedding.")
        return

    try:
        from app.mcp.journal.embedding import Embedder

        embedder = Embedder()
        embedding = await embedder.embed(content)

        source_uri = f"journal:{entry_id}"

        # Delete existing embedding for this journal entry
        await db.execute(
            delete(EmbeddingChunk).where(EmbeddingChunk.source_uri == source_uri)
        )

        chunk = EmbeddingChunk(
            id=uuid.uuid4(),
            content=content,
            embedding=embedding,
            source_uri=source_uri,
            extra_metadata={"source": "journal", "journal_entry_id": str(entry_id)},
        )

        db.add(chunk)
        await db.flush()
    except Exception:
        logger.exception("Failed to embed journal entry %s", entry_id)


async def delete_journal_embedding(db: AsyncSession, entry_id: uuid.UUID) -> None:
    """Remove embedding_chunks for a deleted journal entry."""
    source_uri = f"journal:{entry_id}"
    await db.execute(
        delete(EmbeddingChunk).where(EmbeddingChunk.source_uri == source_uri)
    )
