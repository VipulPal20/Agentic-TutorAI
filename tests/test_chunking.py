"""Tests for document chunking (uses the real recursive splitter)."""

from __future__ import annotations

from database.chunking import Chunk, chunk_documents, chunk_text


def test_chunk_text_splits_and_tags_metadata() -> None:
    text = "Intro paragraph.\n\n" + ("lorem ipsum " * 400)
    chunks = chunk_text(text, {"source": "doc.md"}, chunk_size=200, chunk_overlap=20)

    assert len(chunks) > 1
    assert all(isinstance(c, Chunk) for c in chunks)
    # Original metadata is preserved and augmented.
    assert all(c.metadata["source"] == "doc.md" for c in chunks)
    assert chunks[0].metadata["chunk_index"] == 0
    assert chunks[0].metadata["chunk_count"] == len(chunks)


def test_chunk_text_short_input_single_chunk() -> None:
    chunks = chunk_text("just a little text", {"source": "s"})
    assert len(chunks) == 1
    assert chunks[0].content == "just a little text"


def test_chunk_documents_aggregates() -> None:
    docs = [
        {"content": "alpha " * 300, "metadata": {"source": "a"}},
        {"content": "beta " * 300, "metadata": {"source": "b"}},
    ]
    chunks = chunk_documents(docs)
    sources = {c.metadata["source"] for c in chunks}
    assert sources == {"a", "b"}
    assert len(chunks) >= 2
