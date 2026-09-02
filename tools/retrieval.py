"""pgvector similarity-search tool.

The rich docstring on :func:`knowledge_base_search` is what the LLM sees when
deciding whether to call this tool, so it is written for the model, not just
for developers.
"""

from __future__ import annotations

import re
from typing import Annotated, Any

from langchain_core.tools import tool
from pydantic import Field

from core.config import settings
from core.llm import get_embeddings
from core.logging import get_logger
from database.repository import similarity_search

logger = get_logger(__name__)

# Header emitted by :func:`_format_results` for each passage, e.g.
# ``[1] source=db.md similarity=0.913``. :func:`parse_formatted_results`
# reads it back, so the two must stay in sync — hence they live together.
#
# The score is cosine similarity (``1 - distance``), so it ranges over
# [-1, 1] and the sign must be accepted: an unmatched header would silently
# fold that passage's text into the previous one's snippet.
_RESULT_HEADER = re.compile(
    r"^\[(?P<rank>\d+)\] source=(?P<source>.*?) similarity=(?P<score>-?[0-9.]+)$",
    re.MULTILINE,
)


def _format_results(results: list[dict[str, Any]]) -> str:
    """Render retrieved passages into a compact, citeable block for the LLM."""
    if not results:
        return "No relevant documents were found in the knowledge base."

    blocks: list[str] = []
    for rank, result in enumerate(results, start=1):
        metadata = result.get("metadata") or {}
        source = metadata.get("source", "unknown")
        score = float(result.get("score", 0.0))
        content = str(result.get("content", "")).strip()
        blocks.append(f"[{rank}] source={source} similarity={score:.3f}\n{content}")
    return "\n\n".join(blocks)


def parse_formatted_results(text: str) -> list[dict[str, Any]]:
    """Recover structured passages from a :func:`_format_results` string.

    The tool must hand the LLM a single string, but the UI wants the passages
    back as data so it can show sources and similarity scores. Rather than
    threading a side-channel through ``ToolNode``, we parse the format we
    ourselves produced. Returns ``[]`` for the "nothing found" message or any
    text that doesn't match.
    """
    matches = list(_RESULT_HEADER.finditer(text))
    if not matches:
        return []

    passages: list[dict[str, Any]] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        passages.append(
            {
                "rank": int(match.group("rank")),
                "source": match.group("source"),
                "score": float(match.group("score")),
                "snippet": text[start:end].strip(),
            }
        )
    return passages


@tool("knowledge_base_search")
async def knowledge_base_search(
    query: Annotated[
        str,
        Field(description="A natural-language description of the information you need."),
    ],
    top_k: Annotated[
        int,
        Field(description="Maximum number of passages to return (1-10).", ge=1, le=10),
    ] = settings.retrieval_top_k,
) -> str:
    """Search the internal knowledge base for passages relevant to a query.

    Use this tool whenever the user asks about specific facts, documents,
    policies, or domain knowledge that may live in the organisation's private
    document collection. Prefer this tool over your own memory for such
    questions. It performs semantic (vector) search and returns the most
    similar passages, each with its source and a similarity score between 0 and
    1 (higher means more relevant). If nothing relevant is found, it says so.
    """
    try:
        embeddings = get_embeddings()
        query_vector = await embeddings.aembed_query(query)
        results = await similarity_search(query_vector, top_k=max(1, min(top_k, 10)))
        logger.info("knowledge_base_search: %d result(s) for %r", len(results), query)
        return _format_results(results)
    except Exception as exc:  # noqa: BLE001 - surface a safe message to the agent
        logger.exception("knowledge_base_search failed for query %r", query)
        return (
            "The knowledge base search failed due to an internal error "
            f"({type(exc).__name__}). Please answer using general knowledge and "
            "note that retrieval was unavailable."
        )
