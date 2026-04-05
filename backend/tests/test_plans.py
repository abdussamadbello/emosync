"""Tests for treatment plan and goal endpoints."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient) -> str:
    email = f"plan_{uuid.uuid4().hex[:8]}@example.com"
    r = await client.post("/api/v1/auth/register", json={"email": email, "password": "secret1234"})
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_create_plan(client: AsyncClient) -> None:
    token = await _register(client)
    r = await client.post("/api/v1/plans", headers={"Authorization": f"Bearer {token}"}, json={"title": "Grief recovery plan"})
    assert r.status_code == 201
    data = r.json()
    assert data["title"] == "Grief recovery plan"
    assert data["status"] == "active"
    assert data["goals"] == []


@pytest.mark.asyncio
async def test_list_plans(client: AsyncClient) -> None:
    token = await _register(client)
    await client.post("/api/v1/plans", headers={"Authorization": f"Bearer {token}"}, json={"title": "Plan 1"})
    await client.post("/api/v1/plans", headers={"Authorization": f"Bearer {token}"}, json={"title": "Plan 2"})
    r = await client.get("/api/v1/plans", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert len(r.json()) == 2


@pytest.mark.asyncio
async def test_get_plan_with_goals(client: AsyncClient) -> None:
    token = await _register(client)
    plan_r = await client.post("/api/v1/plans", headers={"Authorization": f"Bearer {token}"}, json={"title": "Test plan"})
    plan_id = plan_r.json()["id"]
    await client.post(f"/api/v1/plans/{plan_id}/goals", headers={"Authorization": f"Bearer {token}"}, json={"description": "Practice mindfulness daily"})
    r = await client.get(f"/api/v1/plans/{plan_id}", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert len(data["goals"]) == 1
    assert data["goals"][0]["description"] == "Practice mindfulness daily"
    assert data["goals"][0]["status"] == "not_started"


@pytest.mark.asyncio
async def test_update_plan(client: AsyncClient) -> None:
    token = await _register(client)
    plan_r = await client.post("/api/v1/plans", headers={"Authorization": f"Bearer {token}"}, json={"title": "Old"})
    plan_id = plan_r.json()["id"]
    r = await client.patch(f"/api/v1/plans/{plan_id}", headers={"Authorization": f"Bearer {token}"}, json={"title": "New", "status": "paused"})
    assert r.status_code == 200
    assert r.json()["title"] == "New"
    assert r.json()["status"] == "paused"


@pytest.mark.asyncio
async def test_add_goal(client: AsyncClient) -> None:
    token = await _register(client)
    plan_r = await client.post("/api/v1/plans", headers={"Authorization": f"Bearer {token}"}, json={"title": "Plan"})
    plan_id = plan_r.json()["id"]
    r = await client.post(f"/api/v1/plans/{plan_id}/goals", headers={"Authorization": f"Bearer {token}"}, json={"description": "Write in journal 3x/week", "target_date": "2026-05-01"})
    assert r.status_code == 201
    assert r.json()["description"] == "Write in journal 3x/week"
    assert r.json()["target_date"] == "2026-05-01"


@pytest.mark.asyncio
async def test_update_goal_with_progress_note(client: AsyncClient) -> None:
    token = await _register(client)
    plan_r = await client.post("/api/v1/plans", headers={"Authorization": f"Bearer {token}"}, json={"title": "Plan"})
    plan_id = plan_r.json()["id"]
    goal_r = await client.post(f"/api/v1/plans/{plan_id}/goals", headers={"Authorization": f"Bearer {token}"}, json={"description": "Goal"})
    goal_id = goal_r.json()["id"]
    r = await client.patch(f"/api/v1/goals/{goal_id}", headers={"Authorization": f"Bearer {token}"}, json={"status": "in_progress", "progress_note": "Started this week"})
    assert r.status_code == 200
    assert r.json()["status"] == "in_progress"
    assert len(r.json()["progress_notes"]) == 1
    assert r.json()["progress_notes"][0]["note"] == "Started this week"


@pytest.mark.asyncio
async def test_delete_goal(client: AsyncClient) -> None:
    token = await _register(client)
    plan_r = await client.post("/api/v1/plans", headers={"Authorization": f"Bearer {token}"}, json={"title": "Plan"})
    plan_id = plan_r.json()["id"]
    goal_r = await client.post(f"/api/v1/plans/{plan_id}/goals", headers={"Authorization": f"Bearer {token}"}, json={"description": "Goal to delete"})
    goal_id = goal_r.json()["id"]
    r = await client.delete(f"/api/v1/goals/{goal_id}", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 204
