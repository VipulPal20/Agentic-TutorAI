"""Async PostgreSQL connection pool management (asyncpg + pgvector).

Exposes a single :data:`db` instance. Its pool must be started with
:meth:`Database.connect` at application startup and closed with
:meth:`Database.disconnect` on shutdown.

Startup ordering note
---------------------
Each pooled connection registers the pgvector codec, which requires the
``vector`` type to already exist in the database. Therefore
:func:`database.schema.init_db` (which runs ``CREATE EXTENSION vector``) must be
called **before** :meth:`Database.connect`. Both the FastAPI lifespan and the
Docker entrypoint follow this ordering.
"""

from __future__ import annotations

import json

import asyncpg
from pgvector.asyncpg import register_vector

from core.config import settings
from core.exceptions import DatabaseError
from core.logging import get_logger

logger = get_logger(__name__)


class Database:
    """Thin wrapper around an :class:`asyncpg.Pool` with pgvector support."""

    def __init__(self) -> None:
        self._pool: asyncpg.Pool | None = None

    @property
    def pool(self) -> asyncpg.Pool:
        """Return the live pool or raise if it has not been started."""
        if self._pool is None:
            raise DatabaseError("Database pool is not initialised; call connect() first.")
        return self._pool

    @property
    def is_connected(self) -> bool:
        return self._pool is not None

    async def connect(self) -> None:
        """Create the connection pool. Idempotent."""
        if self._pool is not None:
            return
        try:
            self._pool = await asyncpg.create_pool(
                dsn=settings.async_dsn,
                min_size=settings.db_pool_min_size,
                max_size=settings.db_pool_max_size,
                init=self._init_connection,
                command_timeout=60,
            )
            logger.info("PostgreSQL connection pool established.")
        except (OSError, asyncpg.PostgresError) as exc:
            raise DatabaseError(f"Failed to create database pool: {exc}") from exc

    async def disconnect(self) -> None:
        """Close the pool if it is open. Idempotent."""
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
            logger.info("PostgreSQL connection pool closed.")

    def acquire(self) -> asyncpg.pool.PoolAcquireContext:
        """Acquire a pooled connection as an async context manager."""
        return self.pool.acquire()

    @staticmethod
    async def _init_connection(conn: asyncpg.Connection) -> None:
        """Per-connection setup: pgvector codec + JSONB <-> dict codec."""
        await register_vector(conn)
        await conn.set_type_codec(
            "jsonb",
            encoder=json.dumps,
            decoder=json.loads,
            schema="pg_catalog",
        )


# Application-wide singleton.
db = Database()
