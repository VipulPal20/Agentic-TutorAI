"""Custom LangChain tools exposed to the agent.

``get_tools`` is the single registry the agent binds to the LLM; add new tools
here and they become available to the ReAct loop.
"""

from __future__ import annotations

from langchain_core.tools import BaseTool

from tools.retrieval import knowledge_base_search
from tools.web_search import web_search


def get_tools() -> list[BaseTool]:
    """Return the ordered list of tools available to the agent."""
    return [knowledge_base_search, web_search]


__all__ = ["get_tools", "knowledge_base_search", "web_search"]
