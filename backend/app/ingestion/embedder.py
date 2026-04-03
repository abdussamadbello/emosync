
from app.mcp.journal.embedding import Embedder as BaseEmbedder

class Embedder(BaseEmbedder):
    async def embed_batch(self, texts):
        embeddings = []
        for text in texts:
            emb = await self.embed(text)
            embeddings.append(emb)
        return embeddings