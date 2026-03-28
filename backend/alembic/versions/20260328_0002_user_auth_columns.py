"""add email, password_hash, display_name to users

Revision ID: 0002_user_auth
Revises: 0001_initial
Create Date: 2026-03-28

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_user_auth"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("email", sa.String(320), nullable=True))
    op.add_column("users", sa.Column("password_hash", sa.String(128), nullable=True))
    op.add_column("users", sa.Column("display_name", sa.String(256), nullable=True))
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # Backfill existing rows with a placeholder so we can set NOT NULL.
    op.execute(sa.text("UPDATE users SET email = 'legacy_' || id::text || '@placeholder' WHERE email IS NULL"))
    op.execute(sa.text("UPDATE users SET password_hash = 'nologin' WHERE password_hash IS NULL"))

    op.alter_column("users", "email", nullable=False)
    op.alter_column("users", "password_hash", nullable=False)


def downgrade() -> None:
    op.drop_index("ix_users_email", table_name="users")
    op.drop_column("users", "display_name")
    op.drop_column("users", "password_hash")
    op.drop_column("users", "email")
