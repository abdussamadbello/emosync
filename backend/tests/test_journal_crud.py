"""Tests for journal entry CRUD endpoints."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient) -> str:
    email = f"journal_{uuid.uuid4().hex[:8]}@example.com"
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "secret1234"},
    )
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_create_journal_entry(client: AsyncClient) -> None:
    token = await _register(client)
    r = await client.post(
        "/api/v1/journal",
        headers={"Authorization": f"Bearer {token}"},
        json={"content": "Today I felt hopeful.", "title": "A good day", "mood_score": 7, "tags": ["hopeful"]},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["content"] == "Today I felt hopeful."
    assert data["title"] == "A good day"
    assert data["mood_score"] == 7
    assert data["tags"] == ["hopeful"]
    assert data["source"] == "manual"


@pytest.mark.asyncio
async def test_list_journal_entries(client: AsyncClient) -> None:
    token = await _register(client)
    for i in range(3):
        await client.post(
            "/api/v1/journal",
            headers={"Authorization": f"Bearer {token}"},
            json={"content": f"Entry {i}"},
        )
    r = await client.get(
        "/api/v1/journal",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 3
    assert data[0]["content"] == "Entry 2"


@pytest.mark.asyncio
async def test_get_journal_entry(client: AsyncClient) -> None:
    token = await _register(client)
    create_r = await client.post(
        "/api/v1/journal",
        headers={"Authorization": f"Bearer {token}"},
        json={"content": "Test entry"},
    )
    entry_id = create_r.json()["id"]
    r = await client.get(
        f"/api/v1/journal/{entry_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["content"] == "Test entry"


@pytest.mark.asyncio
async def test_update_journal_entry(client: AsyncClient) -> None:
    token = await _register(client)
    create_r = await client.post(
        "/api/v1/journal",
        headers={"Authorization": f"Bearer {token}"},
        json={"content": "Original"},
    )
    entry_id = create_r.json()["id"]
    r = await client.patch(
        f"/api/v1/journal/{entry_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"content": "Updated", "mood_score": 8},
    )
    assert r.status_code == 200
    assert r.json()["content"] == "Updated"
    assert r.json()["mood_score"] == 8


@pytest.mark.asyncio
async def test_delete_journal_entry(client: AsyncClient) -> None:
    token = await _register(client)
    create_r = await client.post(
        "/api/v1/journal",
        headers={"Authorization": f"Bearer {token}"},
        json={"content": "To delete"},
    )
    entry_id = create_r.json()["id"]
    r = await client.delete(
        f"/api/v1/journal/{entry_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 204
    r2 = await client.get(
        f"/api/v1/journal/{entry_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 404


@pytest.mark.asyncio
async def test_journal_isolation(client: AsyncClient) -> None:
    token_a = await _register(client)
    token_b = await _register(client)
    create_r = await client.post(
        "/api/v1/journal",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"content": "Private to A"},
    )
    entry_id = create_r.json()["id"]
    r = await client.get(
        f"/api/v1/journal/{entry_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_list_filter_by_tags(client: AsyncClient) -> None:
    token = await _register(client)
    await client.post(
        "/api/v1/journal",
        headers={"Authorization": f"Bearer {token}"},
        json={"content": "tagged", "tags": ["grief"]},
    )
    await client.post(
        "/api/v1/journal",
        headers={"Authorization": f"Bearer {token}"},
        json={"content": "untagged", "tags": []},
    )
    r = await client.get(
        "/api/v1/journal",
        headers={"Authorization": f"Bearer {token}"},
        params={"tag": "grief"},
    )
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["content"] == "tagged"
