"""Tests for auth endpoint rate limiting."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_login_rate_limit(client: AsyncClient) -> None:
    """After 5 login attempts per minute, the 6th should be rate-limited (429)."""
    # Register a user first.
    await client.post(
        "/api/v1/auth/register",
        json={"email": "ratelimit@example.com", "password": "secret1234"},
    )

    # Send 5 login attempts (these should all get 200 or 401, not 429).
    for i in range(5):
        r = await client.post(
            "/api/v1/auth/login",
            json={"email": "ratelimit@example.com", "password": "secret1234"},
        )
        assert r.status_code in (200, 401), f"Attempt {i+1} got unexpected {r.status_code}"

    # The 6th should be rate-limited.
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "ratelimit@example.com", "password": "secret1234"},
    )
    assert r.status_code == 429, f"Expected 429 but got {r.status_code}"


@pytest.mark.asyncio
async def test_register_rate_limit(client: AsyncClient) -> None:
    """After 3 register attempts per minute, the 4th should be rate-limited (429)."""
    for i in range(3):
        r = await client.post(
            "/api/v1/auth/register",
            json={"email": f"regrl{i}@example.com", "password": "secret1234"},
        )
        assert r.status_code in (201, 409), f"Attempt {i+1} got unexpected {r.status_code}"

    r = await client.post(
        "/api/v1/auth/register",
        json={"email": "regrl_extra@example.com", "password": "secret1234"},
    )
    assert r.status_code == 429, f"Expected 429 but got {r.status_code}"
