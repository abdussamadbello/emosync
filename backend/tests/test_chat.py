"""Chat endpoint tests (with JWT auth)."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


async def _register_and_get_token(client: AsyncClient, email: str) -> str:
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "secret1234"},
    )
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_create_conversation_and_stream_persists_messages(
    client: AsyncClient,
) -> None:
    token = await _register_and_get_token(client, "chat_test@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.post("/api/v1/conversations", json={}, headers=headers)
    assert r.status_code == 201
    cid = r.json()["id"]

    async with client.stream(
        "POST",
        f"/api/v1/conversations/{cid}/messages/stream",
        json={"content": "Hello from the test suite"},
        headers=headers,
    ) as stream:
        assert stream.status_code == 200
        body = ""
        async for chunk in stream.aiter_text():
            body += chunk

    assert "event: meta" in body
    assert "event: token" in body
    assert "event: done" in body

    listed = await client.get(
        f"/api/v1/conversations/{cid}/messages", headers=headers
    )
    assert listed.status_code == 200
    messages = listed.json()
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Hello from the test suite"
    assert messages[1]["role"] == "assistant"
    # Without GEMINI_API_KEY the stub is used
    assert "[stub assistant]" in messages[1]["content"]


@pytest.mark.asyncio
async def test_chat_routes_require_auth(client: AsyncClient) -> None:
    r = await client.post("/api/v1/conversations", json={})
    assert r.status_code == 401

    r2 = await client.get("/api/v1/conversations")
    assert r2.status_code == 401


@pytest.mark.asyncio
async def test_stream_unknown_conversation(client: AsyncClient) -> None:
    token = await _register_and_get_token(client, "unknown_conv@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    bad = uuid.uuid4()
    async with client.stream(
        "POST",
        f"/api/v1/conversations/{bad}/messages/stream",
        json={"content": "x"},
        headers=headers,
    ) as stream:
        assert stream.status_code == 404
