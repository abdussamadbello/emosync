import asyncio

from app.agent.nodes.historian import historian_node
from app.agent.state import AgentState





async def test_historian():
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
    
    print("=== Historian Node Output ===")
    print("Calendar Context:", result["calendar_context"])
    print("Journal Context:", result["journal_context"])
    print("Historian Briefing:", result["historian_briefing"])
    
    
    

if __name__ == "__main__":
    asyncio.run(test_historian())