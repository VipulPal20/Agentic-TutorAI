"""Tests for the async repository using a fake asyncpg pool/connection."""

from __future__ import annotations

import pytest

from database import repository


class FakeConn:
    def __init__(self, rows: list[dict] | None = None) -> None:
        self._rows = rows or []
        self.executed: list[tuple] = []
        self.last_fetch: tuple | None = None

    async def fetch(self, query: str, *args):
        self.last_fetch = (query, args)
        return self._rows

    async def executemany(self, query: str, rows) -> None:
        self.executed.append((query, list(rows)))

    async def fetchval(self, query: str):
        return len(self._rows)


class FakeAcquire:
    def __init__(self, conn: FakeConn) -> None:
        self._conn = conn

    async def __aenter__(self) -> FakeConn:
        return self._conn

    async def __aexit__(self, *exc) -> bool:
        return False


class FakeDB:
    def __init__(self, conn: FakeConn) -> None:
        self._conn = conn

    def acquire(self) -> FakeAcquire:
        return FakeAcquire(self._conn)


async def test_similarity_search_maps_rows(monkeypatch) -> None:
    rows = [{"id": 1, "content": "hello", "metadata": {"source": "s"}, "score": 0.9}]
    monkeypatch.setattr(repository, "db", FakeDB(FakeConn(rows)))

    results = await repository.similarity_search([0.1] * 768, top_k=3)

    assert results[0]["content"] == "hello"
    assert results[0]["metadata"] == {"source": "s"}
    assert results[0]["score"] == pytest.approx(0.9)


async def test_similarity_search_passes_top_k(monkeypatch) -> None:
    conn = FakeConn([])
    monkeypatch.setattr(repository, "db", FakeDB(conn))

    await repository.similarity_search([0.0] * 768, top_k=7)

    # Query args are (embedding, top_k).
    assert conn.last_fetch is not None
    assert conn.last_fetch[1][1] == 7


async def test_upsert_documents_inserts(monkeypatch) -> None:
    conn = FakeConn()
    monkeypatch.setattr(repository, "db", FakeDB(conn))

    count = await repository.upsert_documents(
        [{"content": "c", "metadata": {"a": 1}, "embedding": [0.0] * 768}]
    )

    assert count == 1
    assert len(conn.executed) == 1
    assert len(conn.executed[0][1]) == 1


async def test_upsert_documents_empty_is_noop(monkeypatch) -> None:
    conn = FakeConn()
    monkeypatch.setattr(repository, "db", FakeDB(conn))

    assert await repository.upsert_documents([]) == 0
    assert conn.executed == []
