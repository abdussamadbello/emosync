import json
import asyncio

class VectorWriter:
    def __init__(self, db):
        self.db = db

    async def write(self, chunks, embeddings, metadata_list=None):
        for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            metadata = metadata_list[i] if metadata_list else {"source": "cbt_pdf"}
            await self.db.execute("""
                INSERT INTO embedding_chunks (id, content, embedding, extra_metadata)
                VALUES (gen_random_uuid(), :content, :embedding, :meta::jsonb)
            """, {
                "content": chunk,
                "embedding": emb,
                "meta": json.dumps(metadata)
            })
        await self.db.commit()
