from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.conversation import Conversation

EMBEDDING_DIM = 1536


class EmbeddingChunk(Base):
    __tablename__ = "embedding_chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True
    )
    source_uri: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    content: Mapped[str] = mapped_column(Text(), nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column("extra_metadata", JSON(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    conversation: Mapped[Conversation | None] = relationship("Conversation", back_populates="embedding_chunks")
