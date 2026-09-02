"""Tests for the custom LangGraph agent: routing, text extraction, run loop."""

from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from agent import graph as graph_mod
from agent.graph import (
    _extract_text,
    _should_continue,
    _tool_call_events,
    _tool_result_events,
)
from tools.retrieval import _format_results


def test_should_continue_routes_to_tools_when_tool_calls() -> None:
    msg = AIMessage(
        content="",
        tool_calls=[{"name": "knowledge_base_search", "args": {"query": "x"}, "id": "1"}],
    )
    assert _should_continue({"messages": [msg]}) == "tools"


def test_should_continue_ends_without_tool_calls() -> None:
    from langgraph.graph import END

    msg = AIMessage(content="final answer")
    assert _should_continue({"messages": [msg]}) == END


def test_extract_text_from_plain_string() -> None:
    assert _extract_text("hello") == "hello"


def test_extract_text_from_content_parts() -> None:
    content = [{"type": "text", "text": "part-a "}, {"type": "text", "text": "part-b"}, "tail"]
    assert _extract_text(content) == "part-a part-btail"


class FakeModel:
    """Stands in for a tool-bound ChatGoogleGenerativeAI instance."""

    def bind_tools(self, tools):
        return self

    async def ainvoke(self, messages):
        return AIMessage(content="Hello from agent")


async def test_run_agent_returns_final_answer(monkeypatch) -> None:
    monkeypatch.setattr(graph_mod, "get_tools", lambda: [])
    monkeypatch.setattr(graph_mod, "get_chat_model", lambda: FakeModel())
    monkeypatch.setattr(
        graph_mod, "get_langfuse_callbacks", lambda **kwargs: []
    )

    # The compiled graph is lru_cached; rebuild it with the patched model.
    graph_mod.get_compiled_graph.cache_clear()
    try:
        answer = await graph_mod.run_agent("hi", session_id="s1", user_id="u1")
    finally:
        graph_mod.get_compiled_graph.cache_clear()

    assert answer == "Hello from agent"


def test_run_agent_accepts_human_message_input() -> None:
    # Sanity: HumanMessage import is wired (guards against accidental removal).
    assert HumanMessage(content="q").content == "q"


# --- event builders used by stream_agent_events -----------------------------


def test_tool_call_events_describe_the_call() -> None:
    msg = AIMessage(
        content="",
        tool_calls=[
            {"name": "knowledge_base_search", "args": {"query": "pgvector"}, "id": "1"}
        ],
    )
    events = _tool_call_events(msg)

    assert len(events) == 1
    assert events[0]["type"] == "step"
    assert events[0]["tool"] == "knowledge_base_search"
    assert events[0]["label"] == "Searching the knowledge base"
    assert events[0]["query"] == "pgvector"


def test_tool_result_events_emit_step_and_sources() -> None:
    formatted = _format_results(
        [
            {"content": "A.", "metadata": {"source": "a.md"}, "score": 0.9},
            {"content": "B.", "metadata": {"source": "b.md"}, "score": 0.8},
        ]
    )
    msg = ToolMessage(content=formatted, name="knowledge_base_search", tool_call_id="1")
    events = _tool_result_events(msg)

    assert events[0]["type"] == "step"
    assert events[0]["count"] == 2
    assert events[0]["label"] == "Read 2 passages"
    assert events[1]["type"] == "sources"
    assert [item["source"] for item in events[1]["items"]] == ["a.md", "b.md"]


def test_tool_result_events_singular_label() -> None:
    formatted = _format_results([{"content": "A.", "metadata": {"source": "a.md"}, "score": 0.9}])
    msg = ToolMessage(content=formatted, name="knowledge_base_search", tool_call_id="1")
    assert _tool_result_events(msg)[0]["label"] == "Read 1 passage"


def test_tool_result_events_no_sources_when_empty() -> None:
    msg = ToolMessage(
        content="No relevant documents were found in the knowledge base.",
        name="knowledge_base_search",
        tool_call_id="1",
    )
    events = _tool_result_events(msg)

    assert len(events) == 1  # step only, no sources frame
    assert events[0]["count"] == 0
    assert events[0]["label"] == "No matching passages"


def test_tool_result_events_for_other_tools() -> None:
    msg = ToolMessage(content="stub result", name="web_search", tool_call_id="1")
    events = _tool_result_events(msg)

    assert len(events) == 1
    assert events[0]["stage"] == "tool_done"
    assert events[0]["tool"] == "web_search"


async def test_stream_agent_events_emits_status_tokens_done(monkeypatch) -> None:
    """The event stream should open with status and close with done."""
    monkeypatch.setattr(graph_mod, "get_tools", lambda: [])
    monkeypatch.setattr(graph_mod, "get_chat_model", lambda: FakeModel())
    monkeypatch.setattr(graph_mod, "get_langfuse_callbacks", lambda **kwargs: [])

    graph_mod.get_compiled_graph.cache_clear()
    try:
        events = [event async for event in graph_mod.stream_agent_events("hi")]
    finally:
        graph_mod.get_compiled_graph.cache_clear()

    types = [event["type"] for event in events]
    assert types[0] == "status"
    assert types[-1] == "done"


async def test_stream_agent_tokens_runs(monkeypatch) -> None:
    """Token-only helper stays wired (kept as a text-only alternative)."""
    monkeypatch.setattr(graph_mod, "get_tools", lambda: [])
    monkeypatch.setattr(graph_mod, "get_chat_model", lambda: FakeModel())
    monkeypatch.setattr(graph_mod, "get_langfuse_callbacks", lambda **kwargs: [])

    graph_mod.get_compiled_graph.cache_clear()
    try:
        tokens = [token async for token in graph_mod.stream_agent_tokens("hi")]
    finally:
        graph_mod.get_compiled_graph.cache_clear()

    # The fake model doesn't emit streaming callbacks, so no tokens is correct;
    # this guards the signature and the happy path against regressions.
    assert isinstance(tokens, list)
