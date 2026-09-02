"""LangGraph agent state definition.

The state carries the running message history. ``add_messages`` is the reducer
that appends (and de-duplicates by id) new messages returned by each node,
which is what makes the ReAct loop accumulate context correctly.
"""

from __future__ import annotations

from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """Shared state passed between graph nodes."""

    messages: Annotated[list[AnyMessage], add_messages]
