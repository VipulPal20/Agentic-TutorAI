"""Langfuse observability wiring for the agent.

Returns LangChain callback handlers that trace the whole graph run (every LLM
call and tool invocation). If Langfuse is disabled or misconfigured, an empty
list is returned so the agent runs normally without tracing.

Uses the Langfuse v2 callback API: ``from langfuse.callback import CallbackHandler``.
"""

from __future__ import annotations

from typing import Any

from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)


def get_langfuse_callbacks(
    *,
    session_id: str | None = None,
    user_id: str | None = None,
) -> list[Any]:
    """Return a list of callback handlers (possibly empty) for the run config."""
    if not settings.langfuse_ready:
        return []
    try:
        from langfuse.callback import CallbackHandler

        handler = CallbackHandler(
            public_key=settings.langfuse_public_key.get_secret_value(),
            secret_key=settings.langfuse_secret_key.get_secret_value(),
            host=settings.langfuse_host,
            session_id=session_id,
            user_id=user_id,
        )
        return [handler]
    except Exception:  # noqa: BLE001 - tracing must never break the request path
        logger.exception("Failed to initialise Langfuse; continuing without tracing.")
        return []
