

import asyncio
import json
import uuid

from app.ingestion.pdf_loader import PDFLoader
from app.ingestion.chunker import Chunker
from app.mcp.journal.embedding import Embedder
from app.ingestion.pipeline import IngestionPipeline
from app.ingestion.tagger import CBTTagger



class JSONWriter:
    def __init__(self, path):
        self.path = path

    async def write(self, chunks, embeddings, metadata_list):
        data = []

        for chunk, emb, meta in zip(chunks, embeddings, metadata_list):
            data.append({
                "id": str(uuid.uuid4()),
                "content": chunk,              
                "embedding": emb,
                "metadata": meta               
            })

        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"✅ Saved {len(data)} chunks to vector_store.json")


async def test_ingestion(pdf_path: str):
    loader = PDFLoader()
    chunker = Chunker(chunk_size=1500, overlap=200)  # fewer chunks (quota-safe)
    embedder = Embedder()
    writer = JSONWriter("backend/data/vector_store.json")
    tagger = CBTTagger()

    pipeline = IngestionPipeline(
        loader,
        chunker,
        embedder,
        writer,
        tagger   
    )

    await pipeline.ingest_pdf(pdf_path)

    print("✅ Ingestion complete. Data saved to vector_store.json")


if __name__ == "__main__":
    pdf_path = "backend/data/cbt.pdf"
    asyncio.run(test_ingestion(pdf_path))