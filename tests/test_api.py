"""Tests for the FastAPI layer using TestClient with mocked agent + DB.

The lifespan's real dependencies (DB pool, graph compilation) are patched out so
the app starts without Postgres or a live Gemini key.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from api import main as main_mod
from api import routes as routes_mod
from core.exceptions import AgentError


async def _anoop(*args, **kwargs) -> None:
    return None


async def _fake_events(query, *, session_id=None, user_id=None):
    """Mimic stream_agent_events: status -> step -> sources -> tokens -> done."""
    yield {"type": "status", "stage": "thinking", "label": "Thinking"}
    yield {
        "type": "step",
        "stage": "tool",
        "tool": "knowledge_base_search",
        "label": "Searching the knowledge base",
        "query": "pgvector",
    }
    yield {
        "type": "sources",
        "items": [{"rank": 1, "source": "db.md", "score": 0.91, "snippet": "pgvector..."}],
    }
    yield {"type": "token", "content": "Hello"}
    yield {"type": "token", "content": " world"}
    yield {"type": "done"}


async def _fake_run(query, *, session_id=None, user_id=None) -> str:
    return "sync answer"


async def _fake_notes(turns) -> str:
    return "# Notes\nA summary."


@pytest.fixture()
def client(monkeypatch):
    # Neutralise startup/shutdown side effects.
    monkeypatch.setattr(main_mod, "init_db", _anoop)
    monkeypatch.setattr(main_mod.db, "connect", _anoop)
    monkeypatch.setattr(main_mod.db, "disconnect", _anoop)
    monkeypatch.setattr(main_mod, "get_compiled_graph", lambda: None)

    # Replace the agent entry points used by the routes.
    monkeypatch.setattr(routes_mod, "stream_agent_events", _fake_events)
    monkeypatch.setattr(routes_mod, "run_agent", _fake_run)
    monkeypatch.setattr(routes_mod, "summarize_conversation", _fake_notes)

    with TestClient(main_mod.app) as test_client:
        yield test_client


def test_health_ok(client) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    # DB was never really connected in tests.
    assert body["database"] == "disconnected"


def test_chat_streams_all_event_types(client) -> None:
    resp = client.post("/chat", json={"query": "hello"})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")

    text = resp.text
    assert '"type": "status"' in text
    assert '"type": "step"' in text
    assert '"type": "sources"' in text
    assert '"type": "token"' in text
    assert "Hello" in text
    assert "world" in text
    assert '"type": "done"' in text


def test_chat_frames_are_valid_sse_json(client) -> None:
    resp = client.post("/chat", json={"query": "hello"})
    frames = [
        json.loads(line.removeprefix("data: "))
        for line in resp.text.splitlines()
        if line.startswith("data: ")
    ]
    assert frames[0]["type"] == "status"
    assert frames[-1]["type"] == "done"
    tokens = "".join(f["content"] for f in frames if f["type"] == "token")
    assert tokens == "Hello world"


def test_chat_validation_rejects_empty_query(client) -> None:
    resp = client.post("/chat", json={"query": ""})
    assert resp.status_code == 422


def test_chat_sync_returns_answer(client) -> None:
    resp = client.post("/chat/sync", json={"query": "hi", "session_id": "s1"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["answer"] == "sync answer"
    assert body["session_id"] == "s1"


def test_summarize_returns_notes(client) -> None:
    resp = client.post(
        "/summarize",
        json={"turns": [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"}]},
    )
    assert resp.status_code == 200
    assert resp.json()["notes"].startswith("# Notes")


def test_summarize_rejects_empty_transcript(client) -> None:
    resp = client.post("/summarize", json={"turns": []})
    assert resp.status_code == 422


def test_summarize_rejects_unknown_role(client) -> None:
    resp = client.post("/summarize", json={"turns": [{"role": "robot", "content": "x"}]})
    assert resp.status_code == 422


def test_app_error_maps_to_status(client, monkeypatch) -> None:
    async def _boom(query, *, session_id=None, user_id=None):
        raise AgentError("agent exploded")

    monkeypatch.setattr(routes_mod, "run_agent", _boom)

    resp = client.post("/chat/sync", json={"query": "hi"})
    assert resp.status_code == 502
    body = resp.json()
    assert body["error"] == "AgentError"
    assert "agent exploded" in body["detail"]


def test_learn_endpoint(client, monkeypatch) -> None:
    async def _fake_learn(req):
        from api.schemas import LearnResponse
        return LearnResponse(mode="quiz", topic="Test", sources_used=[])

    monkeypatch.setattr(routes_mod, "generate_learn_content", _fake_learn)

    resp = client.post("/learn", json={"topic": "Test", "mode": "quiz"})
    assert resp.status_code == 200
    assert resp.json()["mode"] == "quiz"

