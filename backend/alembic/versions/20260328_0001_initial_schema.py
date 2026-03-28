"""initial schema with pgvector

Revision ID: 0001_initial
Revises:
Create Date: 2026-03-28

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Adjust when you lock an embedding model (e.g. Gemini / OpenAI dimensions).
EMBEDDING_DIM = 1536


def upgrade() -> None:
    op.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector"))

    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "conversations",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"], unique=False)

    op.create_table(
        "messages",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"], unique=False)

    op.create_table(
        "embedding_chunks",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", UUID(as_uuid=True), nullable=True),
        sa.Column("source_uri", sa.String(length=2048), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=True),
        sa.Column(
            "extra_metadata",
            sa.JSON(),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_embedding_chunks_conversation_id", "embedding_chunks", ["conversation_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_embedding_chunks_conversation_id", table_name="embedding_chunks")
    op.drop_table("embedding_chunks")
    op.drop_index("ix_messages_conversation_id", table_name="messages")
    op.drop_table("messages")
    op.drop_index("ix_conversations_user_id", table_name="conversations")
    op.drop_table("conversations")
    op.drop_table("users")
    op.execute(sa.text("DROP EXTENSION IF EXISTS vector"))
