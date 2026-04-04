import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.api.v1.auth import limiter
from app.core.database import engine
from app.main import app


@pytest_asyncio.fixture(autouse=True)
async def _dispose_async_engine_after_test() -> None:
    """Reset the connection pool so the next test's event loop does not inherit asyncpg futures from a closed loop."""
    yield
    await engine.dispose()


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Reset in-memory rate limiter storage before and after each test to prevent cross-test interference."""
    limiter._limiter.storage.reset()
    yield
    limiter._limiter.storage.reset()


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
