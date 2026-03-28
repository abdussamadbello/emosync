import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_ok(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_ready_when_db_available(client: AsyncClient) -> None:
    response = await client.get("/api/v1/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
