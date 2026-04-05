from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.embedding_chunk import EmbeddingChunk


class VectorWriter:
    def __init__(
        self,
        db: AsyncSession,
        *,
        conversation_id: str | uuid.UUID | None = None,
    ) -> None:
        self.db = db
        self.conversation_id = self._coerce_uuid(conversation_id)

    async def write(
        self,
        chunks: list[str],
        embeddings: list[list[float]],
        metadata_list: list[dict] | None = None,
    ) -> None:
        rows: list[EmbeddingChunk] = []

        for index, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            metadata = metadata_list[index] if metadata_list else {"source": "cbt_pdf"}
            rows.append(
                EmbeddingChunk(
                    conversation_id=self.conversation_id,
                    source_uri=metadata.get("source_uri") or metadata.get("filename"),
                    content=chunk,
                    embedding=embedding,
                    extra_metadata=metadata,
                )
            )

        self.db.add_all(rows)
        await self.db.flush()

    @staticmethod
    def _coerce_uuid(value: str | uuid.UUID | None) -> uuid.UUID | None:
        if value is None or isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))
