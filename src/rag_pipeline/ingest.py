"""Document ingestion pipeline: load → chunk → embed → store."""

from __future__ import annotations

import hashlib
from pathlib import Path

import structlog

from src.rag_pipeline.chunker import ChunkingStrategy, get_chunker
from src.rag_pipeline.config import get_rag_settings
from src.rag_pipeline.embedder import AzureOpenAIEmbedder
from src.rag_pipeline.vector_store import QdrantVectorStore

logger = structlog.get_logger(__name__)

SUPPORTED_EXTENSIONS = {".md", ".txt", ".json"}


class IngestPipeline:
    def __init__(
        self,
        embedder: AzureOpenAIEmbedder | None = None,
        vector_store: QdrantVectorStore | None = None,
    ) -> None:
        self.settings = get_rag_settings()
        self.embedder = embedder or AzureOpenAIEmbedder(self.settings)
        self.vector_store = vector_store or QdrantVectorStore(
            host=self.settings.QDRANT_HOST, port=self.settings.QDRANT_PORT
        )
        self._seen_hashes: set[str] = set()

    async def ingest_directory(self, directory: str | Path) -> dict:
        directory = Path(directory)
        if not directory.is_dir():
            raise FileNotFoundError(f"Directory not found: {directory}")

        files = [f for f in directory.rglob("*") if f.suffix in SUPPORTED_EXTENSIONS]
        logger.info("ingest.start", directory=str(directory), file_count=len(files))

        # Ensure collection exists (1536 dims for text-embedding-3-small)
        await self.vector_store.create_collection(self.settings.COLLECTION_NAME, dimension=1536)

        total_chunks = 0
        total_skipped = 0

        for file_path in files:
            result = await self.ingest_file(file_path)
            total_chunks += result["chunks_stored"]
            total_skipped += result["chunks_skipped"]

        summary = {
            "files_processed": len(files),
            "total_chunks": total_chunks,
            "duplicates_skipped": total_skipped,
            "embedding_cost_usd": self.embedder.estimated_cost,
        }
        logger.info("ingest.complete", **summary)
        return summary

    async def ingest_file(self, file_path: Path) -> dict:
        text = file_path.read_text(encoding="utf-8")

        # Choose chunking strategy based on file type
        strategy = ChunkingStrategy.MARKDOWN if file_path.suffix == ".md" else ChunkingStrategy.RECURSIVE
        chunker = get_chunker(strategy, self.settings.CHUNK_SIZE, self.settings.CHUNK_OVERLAP)
        chunks = chunker.chunk(text, source=file_path.name)

        # Deduplicate
        new_chunks = []
        for chunk in chunks:
            content_hash = hashlib.sha256(chunk.text.encode()).hexdigest()
            if content_hash not in self._seen_hashes:
                self._seen_hashes.add(content_hash)
                new_chunks.append(chunk)

        skipped = len(chunks) - len(new_chunks)

        if not new_chunks:
            return {"chunks_stored": 0, "chunks_skipped": skipped}

        # Embed
        texts = [c.text for c in new_chunks]
        embeddings = await self.embedder.embed_batch(texts)

        # Store
        ids = [c.chunk_id for c in new_chunks]
        metadatas = [c.metadata for c in new_chunks]
        await self.vector_store.upsert(self.settings.COLLECTION_NAME, ids, embeddings, texts, metadatas)

        logger.info("ingest.file_done", file=file_path.name, chunks=len(new_chunks), skipped=skipped)
        return {"chunks_stored": len(new_chunks), "chunks_skipped": skipped}


if __name__ == "__main__":
    import argparse
    import asyncio

    parser = argparse.ArgumentParser(description="Ingest documents into the RAG pipeline")
    parser.add_argument("--source", required=True, help="Path to documents directory")
    args = parser.parse_args()

    asyncio.run(IngestPipeline().ingest_directory(args.source))