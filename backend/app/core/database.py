from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings


# -------------------------
# Engine + Session factory
# -------------------------

engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
)

SessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# -------------------------
# FastAPI Dependency (CORRECT)
# -------------------------

async def get_db() -> AsyncIterator[AsyncSession]:
    """Used with FastAPI Depends()."""
    async with SessionLocal() as session:
        yield session


# -------------------------
# Manual usage (IMPORTANT)
# -------------------------

@asynccontextmanager
async def get_async_session() -> AsyncIterator[AsyncSession]:
    """Use this in services (e.g., MCP, Historian)."""
    async with SessionLocal() as session:
        yield session