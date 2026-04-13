
class IngestionPipeline:
    def __init__(self, loader, chunker, embedder, writer, tagger):
        self.loader = loader
        self.chunker = chunker
        self.embedder = embedder
        self.writer = writer
        self.tagger = tagger

    async def ingest_pdf(self, file_path: str):
        text = self.loader.load(file_path)
        chunks = self.chunker.chunk(text)
        chunks = chunks[:5]  # only first 5 chunks for testing

        # Create metadata for each chunk
        metadata_list = []

        for i, chunk in enumerate(chunks):
            base_meta = {
                "source": "cbt_pdf",
                "filename": file_path,
                "index": i
            }

            tag_meta = self.tagger.tag(chunk)

            # merge dictionaries
            combined_meta = {**base_meta, **tag_meta}

            metadata_list.append(combined_meta)

        embeddings = await self.embedder.embed_batch(chunks)
        await self.writer.write(chunks, embeddings, metadata_list)
        print(f"✅ PDF '{file_path}' ingested: {len(chunks)} chunks.")