"""Tests for the LangGraph tools with mocked embeddings + retrieval.

Uses string-target monkeypatching (e.g. ``"tools.retrieval.get_embeddings"``)
so the names are patched in the exact namespace the tool looks them up in.
"""

from __future__ import annotations

from tools import get_tools
from tools.retrieval import _format_results, knowledge_base_search, parse_formatted_results
from tools.web_search import web_search


class FakeEmbeddings:
    async def aembed_query(self, text: str) -> list[float]:
        return [0.1] * 768


async def test_knowledge_base_search_returns_context(monkeypatch) -> None:
    monkeypatch.setattr("tools.retrieval.get_embeddings", lambda: FakeEmbeddings())

    async def fake_search(embedding, top_k):
        return [
            {
                "content": "pgvector stores embeddings.",
                "metadata": {"source": "db.md"},
                "score": 0.91,
            },
        ]

    monkeypatch.setattr("tools.retrieval.similarity_search", fake_search)

    result = await knowledge_base_search.ainvoke({"query": "what is pgvector", "top_k": 2})

    assert "pgvector stores embeddings." in result
    assert "db.md" in result


async def test_knowledge_base_search_handles_no_results(monkeypatch) -> None:
    monkeypatch.setattr("tools.retrieval.get_embeddings", lambda: FakeEmbeddings())

    async def empty_search(embedding, top_k):
        return []

    monkeypatch.setattr("tools.retrieval.similarity_search", empty_search)

    result = await knowledge_base_search.ainvoke({"query": "nothing"})
    assert "no relevant" in result.lower()


async def test_knowledge_base_search_swallows_errors(monkeypatch) -> None:
    monkeypatch.setattr("tools.retrieval.get_embeddings", lambda: FakeEmbeddings())

    async def boom(embedding, top_k):
        raise RuntimeError("db down")

    monkeypatch.setattr("tools.retrieval.similarity_search", boom)

    result = await knowledge_base_search.ainvoke({"query": "x"})
    # A tool must never raise into the agent loop; it returns a safe string.
    assert isinstance(result, str)
    assert "error" in result.lower()


async def test_web_search_stub_is_safe() -> None:
    result = await web_search.ainvoke({"query": "latest news"})
    assert isinstance(result, str)
    assert result  # non-empty


def test_get_tools_registry() -> None:
    names = {t.name for t in get_tools()}
    assert names == {"knowledge_base_search", "web_search"}


# --- format <-> parse round trip -------------------------------------------
# parse_formatted_results reads the exact string _format_results writes, so the
# most valuable test is that the pair stays consistent.


def test_format_parse_round_trip() -> None:
    results = [
        {"content": "First passage.", "metadata": {"source": "a.md"}, "score": 0.912},
        {"content": "Second passage.", "metadata": {"source": "b.md"}, "score": 0.844},
    ]
    parsed = parse_formatted_results(_format_results(results))

    assert [p["rank"] for p in parsed] == [1, 2]
    assert [p["source"] for p in parsed] == ["a.md", "b.md"]
    assert parsed[0]["score"] == 0.912
    assert parsed[0]["snippet"] == "First passage."
    assert parsed[1]["snippet"] == "Second passage."


def test_parse_handles_multiline_snippets() -> None:
    results = [
        {"content": "Line one.\nLine two.", "metadata": {"source": "m.md"}, "score": 0.5},
    ]
    parsed = parse_formatted_results(_format_results(results))
    assert parsed[0]["snippet"] == "Line one.\nLine two."


def test_parse_handles_negative_similarity() -> None:
    # Cosine similarity is ``1 - distance``, so it spans [-1, 1]. A header the
    # parser fails to match would fold that passage's text into the previous
    # snippet instead of erroring, so assert on the boundaries explicitly.
    results = [
        {"content": "Close.", "metadata": {"source": "a.md"}, "score": 0.5},
        {"content": "Opposite.", "metadata": {"source": "b.md"}, "score": -0.271},
    ]
    parsed = parse_formatted_results(_format_results(results))

    assert len(parsed) == 2
    assert parsed[1]["score"] == -0.271
    assert parsed[0]["snippet"] == "Close."
    assert parsed[1]["snippet"] == "Opposite."


def test_parse_returns_empty_for_no_results_message() -> None:
    assert parse_formatted_results(_format_results([])) == []


def test_parse_returns_empty_for_unrelated_text() -> None:
    assert parse_formatted_results("the tool failed for some reason") == []
