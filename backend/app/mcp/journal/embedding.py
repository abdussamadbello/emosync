from __future__ import annotations

from typing import List
import asyncio

import google.generativeai as genai
from app.core.config import settings

# Must match EMBEDDING_DIM in models/embedding_chunk.py
_OUTPUT_DIMENSIONALITY = 1536


class Embedder:
    """Gemini-based embedding service."""
    def __init__(self):
        genai.configure(api_key=settings.gemini_api_key)
        self.model = "models/gemini-embedding-001"

    async def embed(self, text: str) -> List[float]:
        loop = asyncio.get_running_loop()

        def _embed():
            return genai.embed_content(
                model=self.model,
                content=text,
                task_type="retrieval_document",
                output_dimensionality=_OUTPUT_DIMENSIONALITY,
            )["embedding"]

        return await loop.run_in_executor(None, _embed)

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        embeddings = []
        for text in texts:
            emb = await self.embed(text)
            embeddings.append(emb)
        return embeddings