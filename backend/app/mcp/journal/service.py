class JournalService:
    def __init__(self, retriever, embedder):
        self.retriever = retriever
        self.embedder = embedder

    async def search(self, user_id: str, query: str):
        embedding = await self.embedder.embed(query)
        results = await self.retriever.search(embedding, user_id)
        return [
            {
                "content": r.content,
                "score": r.similarity
            }
            for r in results
        ]
