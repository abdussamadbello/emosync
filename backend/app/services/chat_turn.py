from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

"""Agent integration boundary (M3).

`run_turn` is the single hook the Lead Agent replaces with LangGraph streaming.
HTTP layer should not import LangGraph directly — only this module.
"""


async def run_turn(
    *,
    user_message: str,
    conversation_id: str,
    user_message_id: str,
) -> AsyncIterator[str]:
    """Yield text fragments for the assistant reply (stub until LangGraph is wired)."""
    preview = user_message.strip().replace("\n", " ")
    if len(preview) > 120:
        preview = preview[:117] + "..."
    stub = (
        f"[stub assistant] Thanks for sharing. (conversation={conversation_id[:8]}…, "
        f"msg={user_message_id[:8]}…) You said: {preview}"
    )
    for part in stub.split():
        yield part + " "
        await asyncio.sleep(0.02)
