"""Tests for MCP server tool registration."""

from __future__ import annotations

import asyncio

import pytest


@pytest.mark.asyncio
async def test_journal_mcp_tools_registered() -> None:
    from app.servers.journal_mcp import mcp

    tools = await mcp.list_tools()
    tool_names = {t.name for t in tools}
    assert "search_journal" in tool_names
    assert "recent_journal_entries" in tool_names
    assert "get_journal_entry" in tool_names
    assert len(tool_names) == 3


@pytest.mark.asyncio
async def test_calendar_mcp_tools_registered() -> None:
    from app.servers.calendar_mcp import mcp

    tools = await mcp.list_tools()
    tool_names = {t.name for t in tools}
    assert "get_upcoming_events" in tool_names
    assert "get_trigger_events" in tool_names
    assert "get_events_by_date" in tool_names
    assert len(tool_names) == 3


@pytest.mark.asyncio
async def test_journal_tools_have_descriptions() -> None:
    from app.servers.journal_mcp import mcp

    tools = await mcp.list_tools()
    for tool in tools:
        assert tool.description, f"Tool {tool.name} missing description"


@pytest.mark.asyncio
async def test_calendar_tools_have_descriptions() -> None:
    from app.servers.calendar_mcp import mcp

    tools = await mcp.list_tools()
    for tool in tools:
        assert tool.description, f"Tool {tool.name} missing description"
