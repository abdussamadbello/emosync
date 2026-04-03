import re

class Chunker:
    def __init__(self, chunk_size=1000, overlap=100, max_chunks=None):
        """
        chunk_size: number of characters per chunk
        overlap: number of overlapping characters between chunks
        max_chunks: optional limit for number of chunks returned
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.max_chunks = max_chunks
        
    def clean_text(self, text: str) -> str:
        # Remove id/cid patterns
        text = re.sub(r'id:\d+\)\(cid:\d+\)', '', text)
        # Replace multiple newlines and whitespace with a single space
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def chunk(self, text: str):
        # Clean up text
        text = self.clean_text(text)
        chunks = []
        start = 0

        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            start += self.chunk_size - self.overlap

            # Stop if we've reached max_chunks
            if self.max_chunks and len(chunks) >= self.max_chunks:
                break

        return chunks