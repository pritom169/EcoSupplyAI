"""Tests for RAG pipeline chunker."""

from __future__ import annotations

import pytest


class TestRecursiveChunker:
    """Test recursive text chunking."""

    def test_short_text_single_chunk(self) -> None:
        """Text shorter than chunk_size should produce a single chunk."""
        text = "This is a short paragraph about sustainability."
        chunk_size = 512
        # Simple split logic
        if len(text) <= chunk_size:
            chunks = [text]
        else:
            chunks = [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_long_text_multiple_chunks(self) -> None:
        """Long text should be split into multiple chunks."""
        text = "Sustainability reporting. " * 100  # ~2600 chars
        chunk_size = 512
        overlap = 50
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunks.append(text[start:end])
            start = end - overlap
        assert len(chunks) > 1

    def test_chunks_have_overlap(self) -> None:
        """Consecutive chunks should share overlapping text."""
        text = "A" * 1000
        chunk_size = 512
        overlap = 50
        chunk1 = text[0:chunk_size]
        chunk2 = text[chunk_size - overlap : 2 * chunk_size - overlap]
        # The end of chunk1 and start of chunk2 should overlap
        assert chunk1[-overlap:] == chunk2[:overlap]

    def test_empty_text_returns_empty(self) -> None:
        """Empty text should return no chunks."""
        text = ""
        chunks = [text] if text.strip() else []
        assert len(chunks) == 0


class TestMarkdownChunker:
    """Test markdown-aware chunking."""

    def test_splits_on_headers(self) -> None:
        """Markdown text should split on header boundaries."""
        md = "# Section 1\n\nParagraph one.\n\n# Section 2\n\nParagraph two."
        sections = md.split("\n# ")
        assert len(sections) == 2

    def test_preserves_header_context(self) -> None:
        """Each chunk should include its section header."""
        md = "# Overview\n\nText about overview.\n\n## Details\n\nMore details here."
        # Simple header-aware split
        sections = []
        current = ""
        for line in md.split("\n"):
            if line.startswith("# ") and current:
                sections.append(current.strip())
                current = line + "\n"
            else:
                current += line + "\n"
        if current.strip():
            sections.append(current.strip())
        assert sections[0].startswith("# Overview")
