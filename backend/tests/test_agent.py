"""Tests for the agent pipeline components.

These tests verify the agent module structure, state schema, and prompts
without requiring a Gemini API key (no LLM calls).
"""

from __future__ import annotations

import pytest

from app.agent.state import AgentState
from app.agent.prompts import HISTORIAN_SYSTEM, SPECIALIST_SYSTEM, ANCHOR_SYSTEM
from app.agent.nodes.historian import _build_historian_prompt
from app.agent.nodes.specialist import _build_specialist_prompt
from app.agent.nodes.anchor import _build_anchor_prompt
from app.services.chat_turn import _extract_suggestions


def _sample_state(**overrides: object) -> AgentState:
    base: AgentState = {
        "user_message": "I miss my mom. Her birthday is next week.",
        "conversation_id": "00000000-0000-0000-0000-000000000001",
        "conversation_history": [
            {"role": "user", "content": "Hi, I've been struggling lately."},
            {"role": "assistant", "content": "I'm here for you. Tell me more."},
        ],
        "calendar_context": [],
        "journal_context": [],
    }
    base.update(overrides)  # type: ignore[typeddict-item]
    return base


class TestAgentState:
    def test_state_accepts_minimal_keys(self) -> None:
        state: AgentState = {"user_message": "hello", "conversation_id": "abc"}
        assert state["user_message"] == "hello"

    def test_state_accepts_all_keys(self) -> None:
        state = _sample_state(
            historian_briefing={"date_insights": "x", "journal_insights": "y"},
            specialist_response="draft",
            final_response="final",
        )
        assert "final_response" in state


class TestPrompts:
    def test_system_prompts_are_non_empty(self) -> None:
        for prompt in (HISTORIAN_SYSTEM, SPECIALIST_SYSTEM, ANCHOR_SYSTEM):
            assert len(prompt) > 100

    def test_specialist_prompt_mentions_cbt(self) -> None:
        assert "CBT" in SPECIALIST_SYSTEM
        assert "ACT" in SPECIALIST_SYSTEM
        assert "Narrative Therapy" in SPECIALIST_SYSTEM

    def test_anchor_prompt_mentions_safety(self) -> None:
        assert "988" in ANCHOR_SYSTEM
        assert "Trauma-informed" in ANCHOR_SYSTEM


class TestHistorianPromptBuilder:
    def test_includes_user_message(self) -> None:
        prompt = _build_historian_prompt(_sample_state())
        assert "I miss my mom" in prompt

    def test_includes_conversation_history(self) -> None:
        prompt = _build_historian_prompt(_sample_state())
        assert "struggling lately" in prompt

    def test_notes_missing_mcp(self) -> None:
        prompt = _build_historian_prompt(_sample_state())
        assert "MCP not connected" in prompt

    def test_includes_calendar_when_present(self) -> None:
        prompt = _build_historian_prompt(
            _sample_state(calendar_context=["Mom's birthday — March 30"])
        )
        assert "Mom's birthday" in prompt


class TestSpecialistPromptBuilder:
    def test_includes_briefing(self) -> None:
        state = _sample_state(
            historian_briefing={
                "date_insights": "Birthday next week",
                "journal_insights": "Wrote about grief in January",
            }
        )
        prompt = _build_specialist_prompt(state)
        assert "Birthday next week" in prompt
        assert "Wrote about grief" in prompt

    def test_includes_user_message(self) -> None:
        prompt = _build_specialist_prompt(_sample_state())
        assert "I miss my mom" in prompt


class TestAnchorPromptBuilder:
    def test_includes_specialist_draft(self) -> None:
        state = _sample_state(specialist_response="Here is a thoughtful response.")
        prompt = _build_anchor_prompt(state)
        assert "thoughtful response" in prompt

    def test_includes_user_message(self) -> None:
        prompt = _build_anchor_prompt(_sample_state())
        assert "I miss my mom" in prompt


class TestRunTurnStubFallback:
    @pytest.mark.asyncio
    async def test_stub_returns_tokens_without_api_key(self) -> None:
        """When GEMINI_API_KEY is unset, run_turn yields the stub response."""
        from app.services.chat_turn import run_turn

        tokens: list[str] = []
        async for token in run_turn(
            user_message="Hello",
            conversation_id="00000000-0000-0000-0000-000000000001",
            user_message_id="00000000-0000-0000-0000-000000000002",
        ):
            tokens.append(token)

        full = "".join(tokens)
        assert "[stub assistant]" in full
        assert "Hello" in full

    @pytest.mark.asyncio
    async def test_stub_accepts_conversation_history(self) -> None:
        from app.services.chat_turn import run_turn

        tokens: list[str] = []
        async for token in run_turn(
            user_message="test",
            conversation_id="00000000-0000-0000-0000-000000000001",
            user_message_id="00000000-0000-0000-0000-000000000002",
            conversation_history=[{"role": "user", "content": "prior"}],
        ):
            tokens.append(token)

        assert len(tokens) > 0


class TestGraphStructure:
    def test_graph_compiles_and_has_expected_nodes(self) -> None:
        from app.agent.graph import grief_coach_graph

        node_names = set(grief_coach_graph.nodes.keys())
        assert "historian" in node_names
        assert "specialist" in node_names
        assert "anchor" in node_names


class TestExtractSuggestions:
    def test_extracts_valid_suggestions_block(self) -> None:
        text = (
            "I hear you. That sounds really difficult.\n\n"
            '```suggestions\n'
            '{"micro_suggestion": {"title": "Box Breathing", "framework": "act", '
            '"description": "Breathe in for 4, hold for 4, out for 4.", '
            '"rationale": "You mentioned feeling anxious."}, '
            '"plan_generation": null}\n'
            '```'
        )
        clean, suggestions = _extract_suggestions(text)
        assert "Box Breathing" not in clean
        assert "I hear you" in clean
        assert suggestions is not None
        assert suggestions["micro_suggestion"]["title"] == "Box Breathing"
        assert suggestions["plan_generation"] is None

    def test_returns_none_for_no_block(self) -> None:
        text = "I understand what you're going through."
        clean, suggestions = _extract_suggestions(text)
        assert clean == text
        assert suggestions is None

    def test_returns_none_for_malformed_json(self) -> None:
        text = "Hello.\n\n```suggestions\n{invalid json}\n```"
        clean, suggestions = _extract_suggestions(text)
        assert "Hello." in clean
        assert suggestions is None

    def test_extracts_plan_generation(self) -> None:
        text = (
            "Based on your assessment, here's what I'd suggest.\n\n"
            '```suggestions\n'
            '{"micro_suggestion": null, "plan_generation": {"title": "Healing Path", '
            '"goals": [{"description": "Practice grounding", "target_date": "2026-05-08", '
            '"framework": "act"}]}}\n'
            '```'
        )
        clean, suggestions = _extract_suggestions(text)
        assert suggestions is not None
        assert suggestions["plan_generation"]["title"] == "Healing Path"
        assert len(suggestions["plan_generation"]["goals"]) == 1

    def test_preserves_text_before_block(self) -> None:
        text = (
            "First paragraph.\n\nSecond paragraph.\n\n"
            '```suggestions\n{"micro_suggestion": null, "plan_generation": null}\n```'
        )
        clean, suggestions = _extract_suggestions(text)
        assert "First paragraph." in clean
        assert "Second paragraph." in clean
        assert suggestions is not None


class TestPromptIncludesSuggestions:
    def test_specialist_prompt_mentions_suggestions(self) -> None:
        assert "suggestions" in SPECIALIST_SYSTEM
        assert "micro_suggestion" in SPECIALIST_SYSTEM
        assert "plan_generation" in SPECIALIST_SYSTEM

    def test_anchor_prompt_mentions_suggestions_validation(self) -> None:
        assert "Suggestions validation" in ANCHOR_SYSTEM
