"""Tests for calendar event CRUD endpoints."""

from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient) -> str:
    email = f"cal_{uuid.uuid4().hex[:8]}@example.com"
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "secret1234"},
    )
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_create_calendar_event(client: AsyncClient) -> None:
    token = await _register(client)
    r = await client.post(
        "/api/v1/calendar",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Mom's anniversary",
            "date": "2026-05-15",
            "event_type": "anniversary",
            "recurrence": "yearly",
            "notes": "First year",
            "notify_agent": True,
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["title"] == "Mom's anniversary"
    assert data["date"] == "2026-05-15"
    assert data["event_type"] == "anniversary"
    assert data["recurrence"] == "yearly"


@pytest.mark.asyncio
async def test_list_calendar_events(client: AsyncClient) -> None:
    token = await _register(client)
    today = date.today()
    for i in range(3):
        await client.post(
            "/api/v1/calendar",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": f"Event {i}",
                "date": str(today + timedelta(days=i)),
                "event_type": "personal",
            },
        )
    r = await client.get(
        "/api/v1/calendar",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert len(r.json()) == 3


@pytest.mark.asyncio
async def test_list_filter_by_date_range(client: AsyncClient) -> None:
    token = await _register(client)
    today = date.today()
    await client.post(
        "/api/v1/calendar",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Soon", "date": str(today + timedelta(days=2)), "event_type": "personal"},
    )
    await client.post(
        "/api/v1/calendar",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Far", "date": str(today + timedelta(days=30)), "event_type": "personal"},
    )
    r = await client.get(
        "/api/v1/calendar",
        headers={"Authorization": f"Bearer {token}"},
        params={"from_date": str(today), "to_date": str(today + timedelta(days=7))},
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["title"] == "Soon"


@pytest.mark.asyncio
async def test_list_filter_by_type(client: AsyncClient) -> None:
    token = await _register(client)
    today = date.today()
    await client.post(
        "/api/v1/calendar",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Ann", "date": str(today), "event_type": "anniversary"},
    )
    await client.post(
        "/api/v1/calendar",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Therapy", "date": str(today), "event_type": "therapy"},
    )
    r = await client.get(
        "/api/v1/calendar",
        headers={"Authorization": f"Bearer {token}"},
        params={"event_type": "anniversary"},
    )
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["title"] == "Ann"


@pytest.mark.asyncio
async def test_get_calendar_event(client: AsyncClient) -> None:
    token = await _register(client)
    create_r = await client.post(
        "/api/v1/calendar",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Test", "date": "2026-06-01", "event_type": "personal"},
    )
    event_id = create_r.json()["id"]
    r = await client.get(
        f"/api/v1/calendar/{event_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["title"] == "Test"


@pytest.mark.asyncio
async def test_update_calendar_event(client: AsyncClient) -> None:
    token = await _register(client)
    create_r = await client.post(
        "/api/v1/calendar",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Original", "date": "2026-06-01", "event_type": "personal"},
    )
    event_id = create_r.json()["id"]
    r = await client.patch(
        f"/api/v1/calendar/{event_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Updated", "notes": "Added notes"},
    )
    assert r.status_code == 200
    assert r.json()["title"] == "Updated"
    assert r.json()["notes"] == "Added notes"


@pytest.mark.asyncio
async def test_delete_calendar_event(client: AsyncClient) -> None:
    token = await _register(client)
    create_r = await client.post(
        "/api/v1/calendar",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Delete me", "date": "2026-06-01", "event_type": "personal"},
    )
    event_id = create_r.json()["id"]
    r = await client.delete(
        f"/api/v1/calendar/{event_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 204


@pytest.mark.asyncio
async def test_calendar_isolation(client: AsyncClient) -> None:
    token_a = await _register(client)
    token_b = await _register(client)
    create_r = await client.post(
        "/api/v1/calendar",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"title": "Private", "date": "2026-06-01", "event_type": "personal"},
    )
    event_id = create_r.json()["id"]
    r = await client.get(
        f"/api/v1/calendar/{event_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert r.status_code == 404
