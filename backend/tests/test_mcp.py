import asyncio
from datetime import datetime
from app.mcp.calendar.service import CalendarService
from app.mcp.journal.embedding import Embedder

# Mock Journal Retriever if DB isn't ready
class MockJournalRetriever:
    async def search(self, query_embedding, user_id):
        return [
            {"content": "Today I felt happy.", "score": 0.9, "tags": ["mood"], "created_at": datetime.utcnow()},
            {"content": "I need to work on my focus.", "score": 0.85, "tags": ["productivity"], "created_at": datetime.utcnow()},
        ]

async def run_mcp_demo():
    print("=== Testing Calendar MCP ===")
    calendar_service = CalendarService()
    calendar_context = await calendar_service.get_context(user_id="test_user")
    print("Relevant today:", calendar_context.relevant_today)
    print("Upcoming events:", calendar_context.upcoming_events)

    print("\n=== Testing Journal MCP (Mock) ===")
    journal_retriever = MockJournalRetriever()
    journal_results = await journal_retriever.search(query_embedding=[0.0]*1536, user_id="test_user")
    for entry in journal_results:
        print(entry)

    print("\n=== Testing Embedder ===")
    embedder = Embedder()
    texts = ["Hello world!", "Testing embeddings with Gemini."]
    embeddings = await embedder.embed_batch(texts)
    for i, emb in enumerate(embeddings):
        print(f"Embedding {i+1} length:", len(emb))

if __name__ == "__main__":
    asyncio.run(run_mcp_demo())
