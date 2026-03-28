import uuid

import pytest
from httpx import AsyncClient

from app.core import config


@pytest.fixture
def enforce_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        config,
        "settings",
        config.settings.model_copy(update={"api_key": "integration-test-key"}),
    )


@pytest.mark.asyncio
async def test_create_conversation_and_stream_persists_messages(
    client: AsyncClient,
) -> None:
    r = await client.post("/api/v1/conversations", json={})
    assert r.status_code == 201
    cid = r.json()["id"]

    async with client.stream(
        "POST",
        f"/api/v1/conversations/{cid}/messages/stream",
        json={"content": "Hello from the test suite"},
    ) as stream:
        assert stream.status_code == 200
        body = ""
        async for chunk in stream.aiter_text():
            body += chunk

    assert "event: meta" in body
    assert "event: token" in body
    assert "event: done" in body

    listed = await client.get(f"/api/v1/conversations/{cid}/messages")
    assert listed.status_code == 200
    messages = listed.json()
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Hello from the test suite"
    assert messages[1]["role"] == "assistant"
    # Without GEMINI_API_KEY the stub is used
    assert "[stub assistant]" in messages[1]["content"]


@pytest.mark.asyncio
async def test_chat_requires_api_key_when_configured(
    client: AsyncClient,
    enforce_api_key: None,
) -> None:
    r = await client.post("/api/v1/conversations", json={})
    assert r.status_code == 401
    assert r.json()["code"] == "unauthorized"

    r2 = await client.post(
        "/api/v1/conversations",
        json={},
        headers={"X-API-Key": "integration-test-key"},
    )
    assert r2.status_code == 201


@pytest.mark.asyncio
async def test_health_public_even_when_api_key_configured(
    client: AsyncClient,
    enforce_api_key: None,
) -> None:
    r = await client.get("/api/v1/health")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_stream_unknown_conversation(client: AsyncClient) -> None:
    bad = uuid.uuid4()
    async with client.stream(
        "POST",
        f"/api/v1/conversations/{bad}/messages/stream",
        json={"content": "x"},
    ) as stream:
        assert stream.status_code == 404
