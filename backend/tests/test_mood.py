"""Tests for mood log endpoints."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, email: str | None = None) -> str:
    if email is None:
        email = f"mood_{uuid.uuid4().hex[:8]}@example.com"
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "secret1234"},
    )
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_log_mood(client: AsyncClient) -> None:
    token = await _register(client)
    r = await client.post(
        "/api/v1/mood",
        headers={"Authorization": f"Bearer {token}"},
        json={"score": 7, "label": "hopeful", "source": "onboarding"},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["score"] == 7
    assert data["label"] == "hopeful"
    assert data["source"] == "onboarding"


@pytest.mark.asyncio
async def test_log_mood_minimal(client: AsyncClient) -> None:
    token = await _register(client)
    r = await client.post(
        "/api/v1/mood",
        headers={"Authorization": f"Bearer {token}"},
        json={"score": 3},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["score"] == 3
    assert data["label"] is None
    assert data["source"] == "check_in"


@pytest.mark.asyncio
async def test_log_mood_invalid_score(client: AsyncClient) -> None:
    token = await _register(client)
    r = await client.post(
        "/api/v1/mood",
        headers={"Authorization": f"Bearer {token}"},
        json={"score": 11},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_list_moods(client: AsyncClient) -> None:
    token = await _register(client)
    for score in [3, 5, 7]:
        await client.post(
            "/api/v1/mood",
            headers={"Authorization": f"Bearer {token}"},
            json={"score": score},
        )
    r = await client.get(
        "/api/v1/mood",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 3
    assert data[0]["score"] == 7
    assert data[2]["score"] == 3
