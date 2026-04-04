import json
import logging

import numpy as np

logger = logging.getLogger(__name__)


class VectorRetriever:
    def __init__(self, path="backend/data/vector_store.json"):
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.store = json.load(f)
        except FileNotFoundError:
            logger.warning("Vector store not found at %s — retrieval will return empty results.", path)
            self.store = []
        except json.JSONDecodeError:
            logger.warning("Vector store at %s is corrupted — retrieval will return empty results.", path)
            self.store = []

    def cosine_similarity(self, a, b):
        a = np.array(a)
        b = np.array(b)
        norm_product = np.linalg.norm(a) * np.linalg.norm(b)
        if norm_product == 0:
            return 0.0
        return float(np.dot(a, b) / norm_product)

    def search(self, query_embedding, top_k=5):
        results = []

        for item in self.store:
            emb = item.get("embedding")
            if not emb:
                continue

            score = self.cosine_similarity(query_embedding, emb)

            results.append({
                "content": item.get("content", ""),
                "metadata": item.get("metadata", {}),
                "score": score,
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]
