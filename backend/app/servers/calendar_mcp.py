"""EmoSync Calendar MCP Server.

Exposes calendar events as MCP tools for external AI clients.
Run with: python -m app.servers.calendar_mcp
Or via entry point: emosync-calendar-mcp

Tools:
  - get_upcoming_events: Get calendar events in the next N days
  - get_trigger_events: Get anniversary/trigger events within N days
  - get_events_by_date: Get all events on a specific date
"""

from __future__ import annotations

import json
from datetime import date

from fastmcp import FastMCP

mcp = FastMCP(
    name="EmoSync Calendar",
    instructions=(
        "Calendar MCP server for the EmoSync grief coaching platform. "
        "Provides access to user calendar events including anniversaries, "
        "therapy sessions, and emotional trigger dates."
    ),
)


@mcp.tool
async def get_upcoming_events(user_id: str, days: int = 7) -> str:
    """Get upcoming calendar events for a user within a date window.

    Only returns events where notify_agent is enabled. Useful for providing
    the AI agent with awareness of emotionally significant dates.

    Args:
        user_id: UUID of the user.
        days: Number of days to look ahead (default 7).

    Returns:
        JSON object with relevant_today and upcoming_events arrays.
    """
    from app.mcp.calendar.service import CalendarService

    service = CalendarService()
    ctx = await service.get_context(user_id)
    return json.dumps(
        {
            "relevant_today": [e.model_dump() for e in ctx.relevant_today],
            "upcoming_events": [e.model_dump() for e in ctx.upcoming_events],
        },
        default=str,
    )


@mcp.tool
async def get_trigger_events(user_id: str, days: int = 7) -> str:
    """Get anniversary and trigger-type events within N days.

    These are emotionally significant dates that the AI should handle
    with extra sensitivity (gentle tone, validation-first responses).

    Args:
        user_id: UUID of the user.
        days: Number of days to look ahead (default 7).

    Returns:
        JSON array of trigger events with id, title, date, event_type, notes.
    """
    from app.mcp.calendar.service import CalendarService

    service = CalendarService()
    results = await service.get_triggers(user_id, days)
    return json.dumps(results, default=str)


@mcp.tool
async def get_events_by_date(user_id: str, target_date: str) -> str:
    """Get all calendar events for a user on a specific date.

    Args:
        user_id: UUID of the user.
        target_date: ISO date string (YYYY-MM-DD).

    Returns:
        JSON array of events on that date.
    """
    from app.mcp.calendar.service import CalendarService

    service = CalendarService()
    parsed_date = date.fromisoformat(target_date)
    results = await service.get_by_date(user_id, parsed_date)
    return json.dumps(results, default=str)


if __name__ == "__main__":
    mcp.run()
