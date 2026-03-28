"""Tests for auth endpoints and JWT-protected chat routes."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_returns_token(client: AsyncClient) -> None:
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": "alice@example.com", "password": "secret1234"},
    )
    assert r.status_code == 201
    data = r.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "dup@example.com", "password": "secret1234"},
    )
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": "dup@example.com", "password": "secret1234"},
    )
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_register_short_password(client: AsyncClient) -> None:
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": "short@example.com", "password": "123"},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "login@example.com", "password": "secret1234"},
    )
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "login@example.com", "password": "secret1234"},
    )
    assert r.status_code == 200
    assert "access_token" in r.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "wrong@example.com", "password": "secret1234"},
    )
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "wrong@example.com", "password": "badpassword"},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient) -> None:
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "secret1234"},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_get_me(client: AsyncClient) -> None:
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "me@example.com",
            "password": "secret1234",
            "display_name": "Test User",
        },
    )
    token = reg.json()["access_token"]

    r = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["email"] == "me@example.com"
    assert data["display_name"] == "Test User"


@pytest.mark.asyncio
async def test_get_me_no_token(client: AsyncClient) -> None:
    r = await client.get("/api/v1/auth/me")
    assert r.status_code == 401


# --- Chat routes now require JWT ---


async def _register_and_get_token(client: AsyncClient, email: str) -> str:
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "secret1234"},
    )
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_create_conversation_requires_auth(client: AsyncClient) -> None:
    r = await client.post("/api/v1/conversations", json={})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_create_and_list_conversations(client: AsyncClient) -> None:
    token = await _register_and_get_token(client, "chatlist@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Create two conversations
    r1 = await client.post(
        "/api/v1/conversations",
        json={"title": "First chat"},
        headers=headers,
    )
    assert r1.status_code == 201

    r2 = await client.post(
        "/api/v1/conversations",
        json={"title": "Second chat"},
        headers=headers,
    )
    assert r2.status_code == 201

    # List conversations
    r = await client.get("/api/v1/conversations", headers=headers)
    assert r.status_code == 200
    convos = r.json()
    assert len(convos) == 2
    # Most recently updated first
    titles = [c["title"] for c in convos]
    assert "First chat" in titles
    assert "Second chat" in titles


@pytest.mark.asyncio
async def test_conversation_isolation_between_users(client: AsyncClient) -> None:
    token_a = await _register_and_get_token(client, "usera@example.com")
    token_b = await _register_and_get_token(client, "userb@example.com")

    # User A creates a conversation
    r = await client.post(
        "/api/v1/conversations",
        json={"title": "A's chat"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    cid = r.json()["id"]

    # User B cannot see A's conversations
    r_list = await client.get(
        "/api/v1/conversations",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert len(r_list.json()) == 0

    # User B cannot access A's conversation messages
    r_msg = await client.get(
        f"/api/v1/conversations/{cid}/messages",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert r_msg.status_code == 404


@pytest.mark.asyncio
async def test_stream_with_auth(client: AsyncClient) -> None:
    token = await _register_and_get_token(client, "stream@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.post(
        "/api/v1/conversations",
        json={"title": "Stream test"},
        headers=headers,
    )
    cid = r.json()["id"]

    async with client.stream(
        "POST",
        f"/api/v1/conversations/{cid}/messages/stream",
        json={"content": "Hello from auth test"},
        headers=headers,
    ) as stream:
        assert stream.status_code == 200
        body = ""
        async for chunk in stream.aiter_text():
            body += chunk

    assert "event: meta" in body
    assert "event: done" in body
