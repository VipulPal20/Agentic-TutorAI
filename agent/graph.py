"""Custom LangGraph ReAct agent.

Graph topology::

        START -> agent -> (tool calls?) --yes--> tools -> agent
                             |
                             no
                             v
                            END

The ``agent`` node calls the tool-bound Gemini model; ``_should_continue``
routes to the prebuilt ``ToolNode`` when the model requested tools, otherwise
ends. This is a hand-built StateGraph (not the deprecated ``AgentExecutor``).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from functools import lru_cache
from typing import TYPE_CHECKING, Any

from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    AnyMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from agent.observability import get_langfuse_callbacks
from agent.prompts import SYSTEM_PROMPT
from agent.state import AgentState
from core.exceptions import AgentError
from core.llm import get_chat_model
from core.logging import get_logger
from tools import get_tools
from tools.retrieval import parse_formatted_results

if TYPE_CHECKING:  # pragma: no cover - typing only, avoids a hard runtime import
    from langgraph.graph.state import CompiledStateGraph

logger = get_logger(__name__)


def _extract_text(content: str | list[Any]) -> str:
    """Normalise message content (str or content-parts list) to plain text."""
    if isinstance(content, str):
        return content
    parts: list[str] = []
    for item in content:
        if isinstance(item, str):
            parts.append(item)
        elif isinstance(item, dict):
            parts.append(str(item.get("text", "")))
    return "".join(parts)


def _should_continue(state: AgentState) -> str:
    """Route to the tools node if the last AI message requested tool calls."""
    last_message = state["messages"][-1]
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"
    return END


@lru_cache
def get_compiled_graph() -> CompiledStateGraph:
    """Build and cache the compiled agent graph.

    Cached so tools are bound and the graph is compiled once per process.
    """
    bound_tools = get_tools()
    model = get_chat_model().bind_tools(bound_tools)

    async def call_model(state: AgentState) -> dict[str, list[AnyMessage]]:
        messages = list(state["messages"])
        # Ensure the system prompt is present exactly once, at the front.
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=SYSTEM_PROMPT), *messages]
        response = await model.ainvoke(messages)
        return {"messages": [response]}

    builder = StateGraph(AgentState)
    builder.add_node("agent", call_model)
    builder.add_node("tools", ToolNode(bound_tools))
    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", _should_continue, {"tools": "tools", END: END})
    builder.add_edge("tools", "agent")

    graph = builder.compile()
    logger.info("Agent graph compiled with %d tool(s).", len(bound_tools))
    return graph


def _run_config(session_id: str | None, user_id: str | None) -> dict[str, Any]:
    return {
        "callbacks": get_langfuse_callbacks(session_id=session_id, user_id=user_id),
        "run_name": "agentic-rag-chat",
    }


async def stream_agent_tokens(
    query: str,
    *,
    session_id: str | None = None,
    user_id: str | None = None,
) -> AsyncIterator[str]:
    """Yield assistant answer tokens as they are generated.

    Only tokens emitted by the ``agent`` node are yielded (tool outputs are
    excluded), giving the client a clean, streaming final answer.
    """
    graph = get_compiled_graph()
    inputs = {"messages": [HumanMessage(content=query)]}
    try:
        async for chunk, metadata in graph.astream(
            inputs,
            config=_run_config(session_id, user_id),
            stream_mode="messages",
        ):
            if metadata.get("langgraph_node") != "agent":
                continue
            if not isinstance(chunk, AIMessageChunk):
                continue
            text = _extract_text(chunk.content)
            if text:
                yield text
    except Exception as exc:  # noqa: BLE001 - re-raised as a domain error
        logger.exception("Agent streaming failed for query %r", query)
        raise AgentError(str(exc)) from exc


async def run_agent(
    query: str,
    *,
    session_id: str | None = None,
    user_id: str | None = None,
) -> str:
    """Run the agent to completion and return the final answer as a string."""
    graph = get_compiled_graph()
    try:
        result = await graph.ainvoke(
            {"messages": [HumanMessage(content=query)]},
            config=_run_config(session_id, user_id),
        )
    except Exception as exc:  # noqa: BLE001 - re-raised as a domain error
        logger.exception("Agent invocation failed for query %r", query)
        raise AgentError(str(exc)) from exc

    final_message = result["messages"][-1]
    return _extract_text(final_message.content)


# ---------------------------------------------------------------------------
# Rich event stream (used by the UI to show the agent reasoning live)
# ---------------------------------------------------------------------------

# Human-readable labels for the tools the agent can call.
_TOOL_LABELS = {
    "knowledge_base_search": "Searching the knowledge base",
    "web_search": "Searching the web",
}


def _tool_call_events(message: AIMessage) -> list[dict[str, Any]]:
    """Turn an AI message's tool calls into ``step`` events."""
    events: list[dict[str, Any]] = []
    for call in message.tool_calls:
        name = call.get("name", "tool")
        args = call.get("args") or {}
        events.append(
            {
                "type": "step",
                "stage": "tool",
                "tool": name,
                "label": _TOOL_LABELS.get(name, f"Running {name}"),
                "query": args.get("query"),
            }
        )
    return events


def _tool_result_events(message: ToolMessage) -> list[dict[str, Any]]:
    """Turn a tool result into ``sources`` and/or ``step`` events."""
    text = _extract_text(message.content)
    events: list[dict[str, Any]] = []

    if message.name == "knowledge_base_search":
        passages = parse_formatted_results(text)
        count = len(passages)
        events.append(
            {
                "type": "step",
                "stage": "retrieved",
                "tool": message.name,
                "label": (
                    f"Read {count} passage{'s' if count != 1 else ''}"
                    if count
                    else "No matching passages"
                ),
                "count": count,
            }
        )
        if passages:
            events.append({"type": "sources", "items": passages})
    else:
        events.append(
            {
                "type": "step",
                "stage": "tool_done",
                "tool": message.name,
                "label": f"Finished {message.name}",
            }
        )
    return events


async def stream_agent_events(
    query: str,
    *,
    session_id: str | None = None,
    user_id: str | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """Stream the agent's work as structured events.

    Yields dicts the transport layer can serialise directly:

    - ``{"type": "status", "stage": "thinking"}`` — run started
    - ``{"type": "step", "stage": "tool", "tool": ..., "label": ..., "query": ...}``
    - ``{"type": "step", "stage": "retrieved", "count": n, "label": ...}``
    - ``{"type": "sources", "items": [{rank, source, score, snippet}, ...]}``
    - ``{"type": "token", "content": "..."}`` — answer text, as generated
    - ``{"type": "done"}``

    Uses multi-mode streaming: ``updates`` reveals what each node produced (tool
    calls and tool results), while ``messages`` carries the answer tokens.
    """
    graph = get_compiled_graph()
    inputs = {"messages": [HumanMessage(content=query)]}

    yield {"type": "status", "stage": "thinking", "label": "Thinking"}
    answer_started = False

    try:
        async for stream_mode, payload in graph.astream(
            inputs,
            config=_run_config(session_id, user_id),
            stream_mode=["updates", "messages"],
        ):
            if stream_mode == "updates":
                for node_name, node_state in (payload or {}).items():
                    for message in (node_state or {}).get("messages", []) or []:
                        if node_name == "agent" and isinstance(message, AIMessage):
                            for event in _tool_call_events(message):
                                yield event
                        elif isinstance(message, ToolMessage):
                            for event in _tool_result_events(message):
                                yield event
                continue

            # stream_mode == "messages": (chunk, metadata)
            chunk, metadata = payload
            if metadata.get("langgraph_node") != "agent":
                continue
            if not isinstance(chunk, AIMessageChunk):
                continue
            text = _extract_text(chunk.content)
            if not text:
                continue
            if not answer_started:
                answer_started = True
                yield {"type": "status", "stage": "answering", "label": "Writing the answer"}
            yield {"type": "token", "content": text}

        yield {"type": "done"}
    except Exception as exc:  # noqa: BLE001 - re-raised as a domain error
        logger.exception("Agent event stream failed for query %r", query)
        raise AgentError(str(exc)) from exc
