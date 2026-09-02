"""Web-search tool.

This ships as a safe **stub** so the agent has a second tool to reason about
(demonstrating source selection in the ReAct loop) without requiring an extra
API key. To enable real web search, install a provider and replace the stub
body — a Tavily implementation is included, commented out, below.
"""

from __future__ import annotations

from typing import Annotated

from langchain_core.tools import tool
from pydantic import Field

from core.logging import get_logger

logger = get_logger(__name__)


@tool("web_search")
async def web_search(
    query: Annotated[
        str,
        Field(description="The search query to run against the public web."),
    ],
) -> str:
    """Search the public web for current or general information.

    Use this tool only when the internal knowledge base is unlikely to contain
    the answer — for example, questions about current events, breaking news, or
    general facts that fall outside the private document collection. For
    anything that could be in the organisation's documents, use
    ``knowledge_base_search`` instead.
    """
    try:
        logger.info("web_search (stub) invoked for query %r", query)
        # --- STUB IMPLEMENTATION -------------------------------------------
        return (
            "Web search is not configured in this deployment, so no live "
            f"results are available for: '{query}'. Answer using the internal "
            "knowledge base or your general knowledge, and clearly note that "
            "live web data was unavailable."
        )
        # --- REAL IMPLEMENTATION (uncomment + `pip install langchain-tavily`)
        # from langchain_tavily import TavilySearch
        # from core.config import settings
        #
        # client = TavilySearch(
        #     max_results=5,
        #     tavily_api_key=settings.tavily_api_key.get_secret_value(),
        # )
        # results = await client.ainvoke({"query": query})
        # return str(results)
    except Exception as exc:  # noqa: BLE001 - surface a safe message to the agent
        logger.exception("web_search failed for query %r", query)
        return f"Web search failed due to an internal error ({type(exc).__name__})."
