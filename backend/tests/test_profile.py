"""Tests for user profile endpoints."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, suffix: str = "") -> str:
    email = f"profile_{suffix or uuid.uuid4().hex}@example.com"
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "secret1234"},
    )
    assert r.status_code == 201, f"Registration failed: {r.text}"
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_get_profile_after_register(client: AsyncClient) -> None:
    token = await _register(client)
    r = await client.get(
        "/api/v1/profile/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["onboarding_completed"] is False
    assert data["grief_type"] is None


@pytest.mark.asyncio
async def test_update_profile(client: AsyncClient) -> None:
    token = await _register(client)
    r = await client.put(
        "/api/v1/profile/me",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "grief_type": "loss",
            "grief_subject": "my grandmother",
            "grief_duration_months": 6,
            "support_system": "some",
            "prior_therapy": True,
            "preferred_approaches": ["cbt", "journaling"],
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["grief_type"] == "loss"
    assert data["grief_subject"] == "my grandmother"
    assert data["grief_duration_months"] == 6
    assert data["support_system"] == "some"
    assert data["prior_therapy"] is True
    assert data["preferred_approaches"] == ["cbt", "journaling"]
    assert data["onboarding_completed"] is False


@pytest.mark.asyncio
async def test_complete_onboarding(client: AsyncClient) -> None:
    token = await _register(client)
    r = await client.post(
        "/api/v1/profile/complete-onboarding",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["onboarding_completed"] is True


@pytest.mark.asyncio
async def test_get_profile_unauthenticated(client: AsyncClient) -> None:
    r = await client.get("/api/v1/profile/me")
    assert r.status_code == 401
