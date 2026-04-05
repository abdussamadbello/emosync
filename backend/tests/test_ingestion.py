import asyncio

from app.core.database import SessionLocal
from app.ingestion.chunker import Chunker
from app.ingestion.pipeline import IngestionPipeline
from app.ingestion.pdf_loader import PDFLoader
from app.ingestion.tagger import CBTTagger
from app.ingestion.writer import VectorWriter
from app.mcp.journal.embedding import Embedder


async def run_ingestion(pdf_path: str) -> None:
    loader = PDFLoader()
    chunker = Chunker(chunk_size=1500, overlap=200)
    embedder = Embedder()
    tagger = CBTTagger()

    async with SessionLocal() as db:
        writer = VectorWriter(db)
        pipeline = IngestionPipeline(loader, chunker, embedder, writer, tagger)
        await pipeline.ingest_pdf(pdf_path)
        await db.commit()

    print("✅ Ingestion complete. Data saved to embedding_chunks.")


if __name__ == "__main__":
    asyncio.run(run_ingestion("backend/data/cbt.pdf"))
