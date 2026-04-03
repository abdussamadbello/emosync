

import asyncio

from app.ingestion.pdf_loader import PDFLoader
from app.ingestion.chunker import Chunker
from app.ingestion.pipeline import IngestionPipeline
from app.ingestion.writer import VectorWriter
from app.ingestion.tagger import CBTTagger
from app.mcp.journal.embedding import Embedder
from app.core.database import SessionLocal


async def main():
    loader = PDFLoader()
    chunker = Chunker(chunk_size=1500, overlap=200)  # quota-safe
    embedder = Embedder()
    tagger = CBTTagger()

    async with SessionLocal() as db:
        writer = VectorWriter(db)

        pipeline = IngestionPipeline(
            loader=loader,
            chunker=chunker,
            embedder=embedder,
            writer=writer,
            tagger=tagger   
        )

        #  Use correct path (match your project structure)
        pdf_path = "backend/data/cbt.pdf"

        await pipeline.ingest_pdf(pdf_path)

        await db.commit()  # ✅ ensure persistence

        print(f"✅ Successfully ingested: {pdf_path}")


if __name__ == "__main__":
    asyncio.run(main())