"""Tests for assessment endpoints."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, email: str | None = None) -> str:
    if email is None:
        email = f"assess_{uuid.uuid4().hex[:8]}@example.com"
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "secret1234"},
    )
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_submit_phq9(client: AsyncClient) -> None:
    token = await _register(client)
    responses = {f"q{i}": 1 for i in range(1, 10)}
    r = await client.post(
        "/api/v1/assessments",
        headers={"Authorization": f"Bearer {token}"},
        json={"instrument": "phq9", "responses": responses, "source": "onboarding"},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["instrument"] == "phq9"
    assert data["total_score"] == 9
    assert data["severity"] == "mild"
    assert data["source"] == "onboarding"


@pytest.mark.asyncio
async def test_submit_gad7(client: AsyncClient) -> None:
    token = await _register(client)
    responses = {f"q{i}": 2 for i in range(1, 8)}
    r = await client.post(
        "/api/v1/assessments",
        headers={"Authorization": f"Bearer {token}"},
        json={"instrument": "gad7", "responses": responses},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["total_score"] == 14
    assert data["severity"] == "moderate"


@pytest.mark.asyncio
async def test_submit_invalid_instrument(client: AsyncClient) -> None:
    token = await _register(client)
    r = await client.post(
        "/api/v1/assessments",
        headers={"Authorization": f"Bearer {token}"},
        json={"instrument": "invalid", "responses": {"q1": 0}},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_list_assessments(client: AsyncClient) -> None:
    token = await _register(client)
    responses = {f"q{i}": 0 for i in range(1, 10)}
    await client.post(
        "/api/v1/assessments",
        headers={"Authorization": f"Bearer {token}"},
        json={"instrument": "phq9", "responses": responses},
    )
    r = await client.get(
        "/api/v1/assessments",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["instrument"] == "phq9"


@pytest.mark.asyncio
async def test_get_latest_assessment(client: AsyncClient) -> None:
    token = await _register(client)
    for score_val in [0, 2]:
        responses = {f"q{i}": score_val for i in range(1, 10)}
        await client.post(
            "/api/v1/assessments",
            headers={"Authorization": f"Bearer {token}"},
            json={"instrument": "phq9", "responses": responses},
        )
    r = await client.get(
        "/api/v1/assessments/latest",
        headers={"Authorization": f"Bearer {token}"},
        params={"instrument": "phq9"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["total_score"] == 18


@pytest.mark.asyncio
async def test_get_latest_no_results(client: AsyncClient) -> None:
    token = await _register(client)
    r = await client.get(
        "/api/v1/assessments/latest",
        headers={"Authorization": f"Bearer {token}"},
        params={"instrument": "phq9"},
    )
    assert r.status_code == 404
