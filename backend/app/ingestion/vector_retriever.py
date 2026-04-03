import json
import numpy as np

class VectorRetriever:
    def __init__(self, path="backend/data/vector_store.json"):
        with open(path, "r", encoding="utf-8") as f:
            self.store = json.load(f)

    def cosine_similarity(self, a, b):
        a = np.array(a)
        b = np.array(b)
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

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
                "score": float(score)
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]