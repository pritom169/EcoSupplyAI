"""Document chunking strategies for the RAG pipeline."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from enum import Enum


class ChunkingStrategy(Enum):
    RECURSIVE = "recursive"
    MARKDOWN = "markdown"


@dataclass
class Chunk:
    text: str
    metadata: dict = field(default_factory=dict)
    chunk_id: str = ""

    def __post_init__(self) -> None:
        if not self.chunk_id:
            self.chunk_id = hashlib.sha256(self.text.encode()).hexdigest()[:16]


class RecursiveChunker:
    """Split text by paragraphs, then sentences, then characters with overlap."""

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = ["\n\n", "\n", ". ", " "]

    def chunk(self, text: str, source: str = "") -> list[Chunk]:
        pieces = self._split_recursive(text, self.separators)
        chunks: list[Chunk] = []
        current_text = ""
        char_start = 0

        for piece in pieces:
            if len(current_text) + len(piece) > self.chunk_size and current_text:
                chunks.append(
                    Chunk(
                        text=current_text.strip(),
                        metadata={
                            "source_file": source,
                            "chunk_index": len(chunks),
                            "char_start": char_start,
                            "char_end": char_start + len(current_text),
                        },
                    )
                )
                # Keep overlap
                overlap_text = current_text[-self.chunk_overlap :] if len(current_text) > self.chunk_overlap else ""
                char_start += len(current_text) - len(overlap_text)
                current_text = overlap_text

            current_text += piece

        if current_text.strip():
            chunks.append(
                Chunk(
                    text=current_text.strip(),
                    metadata={
                        "source_file": source,
                        "chunk_index": len(chunks),
                        "char_start": char_start,
                        "char_end": char_start + len(current_text),
                    },
                )
            )
        return chunks

    def _split_recursive(self, text: str, separators: list[str]) -> list[str]:
        if not separators:
            return [text]
        sep = separators[0]
        parts = text.split(sep)
        result: list[str] = []
        for i, part in enumerate(parts):
            if len(part) > self.chunk_size and len(separators) > 1:
                result.extend(self._split_recursive(part, separators[1:]))
            else:
                result.append(part + (sep if i < len(parts) - 1 else ""))
        return result


class MarkdownChunker:
    """Respect markdown headers as chunk boundaries."""

    def __init__(self, chunk_size: int = 512) -> None:
        self.chunk_size = chunk_size
        self._header_pattern = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

    def chunk(self, text: str, source: str = "") -> list[Chunk]:
        sections = self._split_by_headers(text)
        chunks: list[Chunk] = []

        for section_header, section_text in sections:
            if len(section_text) <= self.chunk_size:
                chunks.append(
                    Chunk(
                        text=section_text.strip(),
                        metadata={
                            "source_file": source,
                            "chunk_index": len(chunks),
                            "header": section_header,
                        },
                    )
                )
            else:
                # Fall back to recursive splitting within section
                sub_chunker = RecursiveChunker(chunk_size=self.chunk_size)
                for sub_chunk in sub_chunker.chunk(section_text, source):
                    sub_chunk.metadata["header"] = section_header
                    chunks.append(sub_chunk)
        return chunks

    def _split_by_headers(self, text: str) -> list[tuple[str, str]]:
        matches = list(self._header_pattern.finditer(text))
        if not matches:
            return [("", text)]
        sections: list[tuple[str, str]] = []
        if matches[0].start() > 0:
            sections.append(("", text[: matches[0].start()]))
        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            header = match.group(2).strip()
            sections.append((header, text[start:end]))
        return sections


def get_chunker(strategy: ChunkingStrategy, chunk_size: int = 512, chunk_overlap: int = 50) -> RecursiveChunker | MarkdownChunker:
    if strategy == ChunkingStrategy.MARKDOWN:
        return MarkdownChunker(chunk_size=chunk_size)
    return RecursiveChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)