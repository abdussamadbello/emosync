import pytest

from app.agent.nodes.historian import historian_node
from app.agent.state import AgentState


@pytest.mark.asyncio
async def test_historian(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeLLM:
        async def ainvoke(self, _messages):  # noqa: ANN001
            class _R:
                content = '{"date_insights": "Test dates", "journal_insights": "Test journal"}'

            return _R()

    monkeypatch.setattr(
        "app.agent.nodes.historian.get_historian_llm",
        lambda: _FakeLLM(),
    )

    # Mocked agent state with Calendar + Journal + user message
    state = AgentState({
        "user_message": "I want to improve my focus",
        "conversation_history": [
            {"role": "user", "content": "Hello!"},
            {"role": "assistant", "content": "Hi! How can I help today?"}
        ],
        # Mocked Calendar MCP events
        "calendar_context": [
            "Meeting with mentor at 3 PM",
            "Project deadline on Friday"
        ],
        # Mocked Journal MCP snippets
        "journal_context": [
            "Today I felt anxious but managed my tasks.",
            "I need to focus more on deep work sessions."
        ]
    })

    result = await historian_node(state)

    assert result["calendar_context"] == [
        "Meeting with mentor at 3 PM",
        "Project deadline on Friday",
    ]
    assert result["historian_briefing"]["date_insights"] == "Test dates"
    assert result["historian_briefing"]["journal_insights"] == "Test journal"