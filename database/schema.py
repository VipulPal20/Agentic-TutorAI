"""Schema bootstrap: pgvector extension, ``documents`` table, and indexes.

Run once at startup (before the pool is created) via :func:`init_db`. All
statements are idempotent (``IF NOT EXISTS``), so repeated calls are safe.
"""

from __future__ import annotations

import asyncpg

from core.config import settings
from core.exceptions import DatabaseError
from core.logging import get_logger

logger = get_logger(__name__)

_CREATE_EXTENSION = "CREATE EXTENSION IF NOT EXISTS vector;"

# ``{dim}`` is filled from settings (an int we control — never user input).
_CREATE_DOCUMENTS_TABLE = """
CREATE TABLE IF NOT EXISTS documents (
    id          BIGSERIAL PRIMARY KEY,
    content     TEXT NOT NULL,
    metadata    JSONB NOT NULL DEFAULT '{{}}'::jsonb,
    embedding   VECTOR({dim}) NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""

# HNSW index with cosine ops — matches the ``<=>`` operator used at query time.
_CREATE_HNSW_INDEX = """
CREATE INDEX IF NOT EXISTS documents_embedding_hnsw_idx
ON documents USING hnsw (embedding vector_cosine_ops);
"""

# GIN index to support optional metadata filtering.
_CREATE_METADATA_INDEX = """
CREATE INDEX IF NOT EXISTS documents_metadata_gin_idx
ON documents USING gin (metadata);
"""


async def init_db(dim: int | None = None) -> None:
    """Create the extension, table, and indexes on a standalone connection.

    A dedicated connection (not the pool) is used because the pool's
    per-connection initializer registers the pgvector codec, which needs the
    ``vector`` type to already exist.
    """
    dim = dim or settings.embedding_dim
    conn: asyncpg.Connection | None = None
    try:
        conn = await asyncpg.connect(dsn=settings.async_dsn)
        await conn.execute(_CREATE_EXTENSION)
        await conn.execute(_CREATE_DOCUMENTS_TABLE.format(dim=dim))
        if dim <= 2000:
            await conn.execute(_CREATE_HNSW_INDEX)
            logger.info(
                "Embedding dim (%d) > 2000; using exact vector search without HNSW index.",
                dim,
            )
        await conn.execute(_CREATE_METADATA_INDEX)
        logger.info("Database schema ready (embedding dim=%d).", dim)
    except (OSError, asyncpg.PostgresError) as exc:
        raise DatabaseError(f"Schema initialisation failed: {exc}") from exc
    finally:
        if conn is not None:
            await conn.close()
