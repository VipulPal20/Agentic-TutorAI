"""Document chunking using LangChain's recursive character splitter."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from langchain_text_splitters import RecursiveCharacterTextSplitter

from core.config import settings


@dataclass(slots=True)
class Chunk:
    """A single chunk of text with its associated metadata."""

    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


def _build_splitter(chunk_size: int, chunk_overlap: int) -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )


def chunk_text(
    text: str,
    metadata: dict[str, Any] | None = None,
    *,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[Chunk]:
    """Split ``text`` into overlapping chunks, propagating ``metadata``.

    Each chunk's metadata is augmented with ``chunk_index`` and ``chunk_count``.
    """
    metadata = metadata or {}
    splitter = _build_splitter(
        chunk_size or settings.chunk_size,
        chunk_overlap if chunk_overlap is not None else settings.chunk_overlap,
    )
    pieces = [piece for piece in splitter.split_text(text) if piece.strip()]
    total = len(pieces)
    return [
        Chunk(
            content=piece,
            metadata={**metadata, "chunk_index": index, "chunk_count": total},
        )
        for index, piece in enumerate(pieces)
    ]


def chunk_documents(documents: list[dict[str, Any]]) -> list[Chunk]:
    """Chunk a list of ``{"content": str, "metadata": dict}`` documents."""
    chunks: list[Chunk] = []
    for document in documents:
        chunks.extend(chunk_text(document["content"], document.get("metadata", {})))
    return chunks
