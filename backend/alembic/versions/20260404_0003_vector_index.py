"""add pgvector HNSW cosine index on embedding_chunks

Revision ID: 0003_vector_index
Revises: 0002_user_auth
Create Date: 2026-04-04

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_vector_index"
down_revision: Union[str, None] = "0002_user_auth"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS ix_embedding_chunks_embedding_cosine "
        "ON embedding_chunks USING hnsw (embedding vector_cosine_ops)"
    ))


def downgrade() -> None:
    op.execute(sa.text("DROP INDEX IF EXISTS ix_embedding_chunks_embedding_cosine"))
