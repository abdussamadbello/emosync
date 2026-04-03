import asyncio
import json
from app.mcp.journal.embedding import Embedder
from scipy.spatial.distance import cosine

VECTOR_STORE_PATH = "backend/data/vector_store.json"

async def main():
    # Load ingested data
    with open(VECTOR_STORE_PATH, "r", encoding="utf-8") as f:
        vector_data = json.load(f)

    # Initialize embedder
    embedder = Embedder()

    # Sample query
    query = "I want to improve my focus"
    query_embedding = await embedder.embed(query)

    # Compute similarity with each chunk
    results = []
    for item in vector_data:
        chunk_emb = item["embedding"]
        score = 1 - cosine(query_embedding, chunk_emb)  # cosine similarity
        results.append({"content": item.get("content", item.get("chunk", "")), "score": score})

    # Sort by similarity
    results.sort(key=lambda x: x["score"], reverse=True)

    # Print top 3 results
    print("Top chunks for query:", query)
    for i, r in enumerate(results[:3], start=1):
        print(f"{i}. Score: {r['score']:.4f}, Content: {r['content'][:100]}...")

if __name__ == "__main__":
    asyncio.run(main())