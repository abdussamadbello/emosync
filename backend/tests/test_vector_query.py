import asyncio

from app.ingestion.vector_retriever import VectorRetriever
from app.mcp.journal.embedding import Embedder


async def run_vector_query() -> None:
    embedder = Embedder()
    retriever = VectorRetriever()

    query = "I want to improve my focus"
    query_embedding = await embedder.embed(query)
    results = await retriever.search(query_embedding, top_k=3)

    print("Top chunks for query:", query)
    for index, result in enumerate(results, start=1):
        print(f"{index}. Score: {result['score']:.4f}, Content: {result['content'][:100]}...")


if __name__ == "__main__":
    asyncio.run(run_vector_query())
