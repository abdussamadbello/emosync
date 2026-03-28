from __future__ import annotations

from fastapi import HTTPException, Request, status

from app.core import config


async def require_api_key(request: Request) -> None:
    expected = config.settings.api_key
    if not expected:
        return

    auth = request.headers.get("Authorization")
    if (
        auth
        and auth.startswith("Bearer ")
        and auth.removeprefix("Bearer ").strip() == expected
    ):
        return

    if request.headers.get("X-API-Key") == expected:
        return

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing API key. Send Authorization: Bearer <key> or X-API-Key.",
    )
