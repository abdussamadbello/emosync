"""Seed the database with demo users.

Usage (from repo root, with DATABASE_URL set and migrations applied):

    python -m scripts.seed_users

Credentials:
    alice@example.com   / password123
    bob@example.com     / password123
    carol@example.com   / password123
"""

from __future__ import annotations

import asyncio
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Ensure backend/ is importable when run from repo root
sys.path.insert(0, "backend")

from app.core.database import SessionLocal, engine  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models.user import User  # noqa: E402

SEED_USERS = [
    {
        "email": "alice@example.com",
        "password": "password123",
        "display_name": "Alice",
    },
    {
        "email": "bob@example.com",
        "password": "password123",
        "display_name": "Bob",
    },
    {
        "email": "carol@example.com",
        "password": "password123",
        "display_name": "Carol",
    },
]


async def seed(session: AsyncSession) -> None:
    for entry in SEED_USERS:
        result = await session.execute(
            select(User).where(User.email == entry["email"])
        )
        if result.scalar_one_or_none() is not None:
            print(f"  skip {entry['email']} (already exists)")
            continue

        user = User(
            email=entry["email"],
            password_hash=hash_password(entry["password"]),
            display_name=entry["display_name"],
        )
        session.add(user)
        print(f"  created {entry['email']} (display_name={entry['display_name']})")

    await session.commit()


async def main() -> None:
    print("Seeding users...")
    async with SessionLocal() as session:
        await seed(session)
    await engine.dispose()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
