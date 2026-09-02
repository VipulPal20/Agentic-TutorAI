"""Async data-access layer for the ``documents`` table.

All functions use the shared pool from :mod:`database.session`. Vectors are
passed as ``list[float]`` (encoded by the pgvector codec) and metadata as
``dict`` (encoded by the JSONB codec).

Extra helpers:
  list_sources()   — aggregated chunk counts per source file
  delete_source()  — remove all chunks for a given source
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import asyncpg

from core.exceptions import DatabaseError
from core.logging import get_logger
from database.session import db

logger = get_logger(__name__)

# Cosine distance (``<=>``); score is similarity in [0, 1] (higher = closer).
_SIMILARITY_QUERY = """
SELECT
    id,
    content,
    metadata,
    1 - (embedding <=> $1) AS score
FROM documents
ORDER BY embedding <=> $1
LIMIT $2;
"""

_INSERT_QUERY = """
INSERT INTO documents (content, metadata, embedding)
VALUES ($1, $2, $3);
"""


async def similarity_search(embedding: list[float], top_k: int = 4) -> list[dict[str, Any]]:
    """Return the ``top_k`` most similar documents to ``embedding``.

    Each result dict has ``id``, ``content``, ``metadata`` (dict), and
    ``score`` (cosine similarity in ``[0, 1]``).
    """
    try:
        async with db.acquire() as conn:
            rows = await conn.fetch(_SIMILARITY_QUERY, embedding, top_k)
    except (OSError, asyncpg.PostgresError) as exc:
        raise DatabaseError(f"Similarity search failed: {exc}") from exc

    return [
        {
            "id": row["id"],
            "content": row["content"],
            "metadata": row["metadata"] or {},
            "score": float(row["score"]),
        }
        for row in rows
    ]


async def upsert_documents(records: Sequence[dict[str, Any]]) -> int:
    """Bulk-insert document records.

    Each record must contain ``content`` (str), ``embedding`` (list[float]),
    and optionally ``metadata`` (dict). Returns the number of rows inserted.
    """
    if not records:
        return 0

    rows = [
        (record["content"], record.get("metadata", {}), record["embedding"])
        for record in records
    ]
    try:
        async with db.acquire() as conn:
            await conn.executemany(_INSERT_QUERY, rows)
    except (OSError, asyncpg.PostgresError) as exc:
        raise DatabaseError(f"Bulk insert failed: {exc}") from exc
    except (KeyError, TypeError) as exc:
        raise DatabaseError(f"Malformed document record: {exc}") from exc

    logger.info("Inserted %d document row(s).", len(rows))
    return len(rows)


async def count_documents() -> int:
    """Return the total number of rows in ``documents`` (used by /health)."""
    try:
        async with db.acquire() as conn:
            value = await conn.fetchval("SELECT count(*) FROM documents;")
    except (OSError, asyncpg.PostgresError) as exc:
        raise DatabaseError(f"Count query failed: {exc}") from exc
    return int(value or 0)


# ---------------------------------------------------------------------------
# Knowledge-base source management
# ---------------------------------------------------------------------------

_LIST_SOURCES_QUERY = """
SELECT
    metadata->>'source' AS source,
    count(*)            AS chunk_count,
    min(created_at)     AS uploaded_at
FROM documents
WHERE metadata->>'source' IS NOT NULL
GROUP BY metadata->>'source'
ORDER BY uploaded_at DESC;
"""

_DELETE_SOURCE_QUERY = """
DELETE FROM documents
WHERE metadata->>'source' = $1;
"""


async def list_sources() -> list[dict]:
    """Return one entry per distinct source filename with its chunk count.

    Each dict has: ``source`` (str), ``chunk_count`` (int), ``uploaded_at`` (datetime).
    """
    try:
        async with db.acquire() as conn:
            rows = await conn.fetch(_LIST_SOURCES_QUERY)
    except (OSError, asyncpg.PostgresError) as exc:
        raise DatabaseError(f"list_sources failed: {exc}") from exc

    return [
        {
            "source": row["source"],
            "chunk_count": int(row["chunk_count"]),
            "uploaded_at": row["uploaded_at"].isoformat() if row["uploaded_at"] else None,
        }
        for row in rows
    ]


async def delete_source(source: str) -> int:
    """Delete all chunks whose metadata source matches ``source``.

    Returns the number of rows deleted.
    """
    try:
        async with db.acquire() as conn:
            result = await conn.execute(_DELETE_SOURCE_QUERY, source)
    except (OSError, asyncpg.PostgresError) as exc:
        raise DatabaseError(f"delete_source failed: {exc}") from exc

    # asyncpg returns e.g. "DELETE 4"
    try:
        deleted = int(str(result).split()[-1])
    except (ValueError, IndexError):
        deleted = 0
    logger.info("Deleted %d chunk(s) for source '%s'.", deleted, source)
    return deleted


async def fetch_sample_chunks(limit: int = 10, topic: str | None = None) -> list[dict[str, Any]]:
    """Fetch sample chunks from the documents table for learning content generation.

    If topic is given, uses ILIKE matching on content or source metadata.
    Otherwise fetches a random sample.
    """
    if topic:
        query = """
        SELECT id, content, metadata
        FROM documents
        WHERE content ILIKE $1 OR metadata->>'source' ILIKE $1
        LIMIT $2;
        """
        params = [f"%{topic}%", limit]
    else:
        query = """
        SELECT id, content, metadata
        FROM documents
        ORDER BY random()
        LIMIT $1;
        """
        params = [limit]

    try:
        async with db.acquire() as conn:
            rows = await conn.fetch(query, *params)
    except (OSError, asyncpg.PostgresError) as exc:
        raise DatabaseError(f"fetch_sample_chunks failed: {exc}") from exc

    return [
        {
            "id": row["id"],
            "content": row["content"],
            "metadata": row["metadata"] or {},
        }
        for row in rows
    ]

