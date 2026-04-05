"""Tests for Historian JSON extraction and vector retrieval edge cases."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock

from app.agent.nodes.historian import _extract_json_from_llm_response, retrieve_relevant_chunks


class TestExtractJsonFromLlmResponse:
    """Unit tests for _extract_json_from_llm_response."""

    def test_plain_json(self):
        raw = '{"date_insights": "today", "journal_insights": "none"}'
        result = _extract_json_from_llm_response(raw)
        assert result["date_insights"] == "today"
        assert result["journal_insights"] == "none"

    def test_json_in_markdown_fence(self):
        raw = 'Here is the analysis:\n```json\n{"date_insights": "today", "journal_insights": "sad"}\n```\nEnd.'
        result = _extract_json_from_llm_response(raw)
        assert result["date_insights"] == "today"
        assert result["journal_insights"] == "sad"

    def test_json_in_plain_code_fence(self):
        raw = 'Result:\n```\n{"date_insights": "a", "journal_insights": "b"}\n```'
        result = _extract_json_from_llm_response(raw)
        assert result["date_insights"] == "a"

    def test_multiple_code_blocks_extracts_first_json(self):
        raw = (
            "Here is the JSON:\n"
            '```json\n{"date_insights": "first", "journal_insights": "block"}\n```\n'
            "And here is more code:\n"
            "```python\nprint('hello')\n```"
        )
        result = _extract_json_from_llm_response(raw)
        assert result["date_insights"] == "first"

    def test_invalid_json_raises(self):
        raw = "This is not JSON at all"
        with pytest.raises(Exception):
            _extract_json_from_llm_response(raw)

    def test_empty_string_raises(self):
        with pytest.raises(Exception):
            _extract_json_from_llm_response("")

    def test_nested_json(self):
        raw = '```json\n{"date_insights": "today", "journal_insights": "entry", "extra": {"key": "val"}}\n```'
        result = _extract_json_from_llm_response(raw)
        assert result["extra"]["key"] == "val"


class TestRetrieveRelevantChunks:
    """Tests for retrieve_relevant_chunks with empty/failing DB retrieval."""

    @pytest.mark.asyncio
    async def test_empty_db_returns_empty(self, monkeypatch):
        """When retrieval returns no rows, return an empty list without crashing."""
        import app.agent.nodes.historian as historian_mod

        monkeypatch.setattr(historian_mod.Embedder, "embed", AsyncMock(return_value=[0.1, 0.2]))
        monkeypatch.setattr(
            historian_mod.VectorRetriever,
            "search",
            AsyncMock(return_value=[]),
        )

        result = await retrieve_relevant_chunks("test query")
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_chunk_contents(self, monkeypatch):
        import app.agent.nodes.historian as historian_mod

        monkeypatch.setattr(historian_mod.Embedder, "embed", AsyncMock(return_value=[0.1, 0.2]))
        monkeypatch.setattr(
            historian_mod.VectorRetriever,
            "search",
            AsyncMock(
                return_value=[
                    {"content": "first chunk", "score": 0.9},
                    {"content": "second chunk", "score": 0.8},
                ]
            ),
        )

        result = await retrieve_relevant_chunks("test query")
        assert result == ["first chunk", "second chunk"]
