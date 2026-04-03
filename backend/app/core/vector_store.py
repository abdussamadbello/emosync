from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, List


class LocalVectorStore:
    """
    Lightweight JSON-based vector store.

    Temporary replacement for pgvector.
    Designed to be easily swappable with DB-backed implementation.
    """

    def __init__(self, path: str = "data/vector_store.json"):
        self.path = Path(path)
        self.data: List[dict[str, Any]] = []

        if self.path.exists():
            self._load()
        else:
            self._initialize_store()

    
    # Internal helpers
    

    def _initialize_store(self):
        """Create empty store file."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data = []
        self._save()

    def _load(self):
        """Load data from disk."""
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        except Exception:
            # Corrupted file fallback
            self.data = []

    def _save(self):
        """Persist data to disk."""
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    # Public API
    

    def add(
        self,
        content: str,
        embedding: list[float],
        metadata: dict | None = None,
    ):
        """Add a new vector entry."""
        self.data.append(
            {
                "content": content,
                "embedding": embedding,
                "metadata": metadata or {},
            }
        )
        self._save()

    def add_many(
        self,
        items: List[dict[str, Any]],
    ):
        """Bulk insert."""
        for item in items:
            self.data.append(
                {
                    "content": item["content"],
                    "embedding": item["embedding"],
                    "metadata": item.get("metadata", {}),
                }
            )
        self._save()

    def search(
        self,
        query_embedding: list[float],
        limit: int = 5,
    ) -> List[dict[str, Any]]:
        """Return top-k most similar items using cosine similarity."""

        results = []

        for item in self.data:
            emb = item.get("embedding")

            if not emb:
                continue

            score = self._cosine_similarity(query_embedding, emb)

            results.append(
                {
                    "content": item["content"],
                    "score": score,
                    "metadata": item.get("metadata", {}),
                }
            )

        # Sort descending by similarity
        results.sort(key=lambda x: x["score"], reverse=True)

        return results[:limit]

    
    # Math
    

    def _cosine_similarity(
        self,
        a: list[float],
        b: list[float],
    ) -> float:
        """Compute cosine similarity between two vectors."""

        if not a or not b:
            return 0.0

        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot / (norm_a * norm_b)