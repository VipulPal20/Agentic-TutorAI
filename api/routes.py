"""API routes: streaming chat, synchronous chat, notes, and health."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, status
from fastapi.responses import StreamingResponse

from agent.graph import run_agent, stream_agent_events
from agent.learn import generate_learn_content
from agent.summarize import summarize_conversation
from api.schemas import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
    LearnRequest,
    LearnResponse,
    SummarizeRequest,
    SummarizeResponse,
)
from core.logging import get_logger
from database.repository import count_documents
from database.session import db

logger = get_logger(__name__)
router = APIRouter()


def _sse(payload: dict[str, object]) -> str:
    """Format a dict as a Server-Sent Events ``data:`` frame."""
    return f"data: {json.dumps(payload)}\n\n"


@router.get("/health", response_model=HealthResponse, tags=["system"])
async def health() -> HealthResponse:
    """Report service and database status (and document count if reachable)."""
    database_state = "connected" if db.is_connected else "disconnected"
    document_count: int | None = None
    if db.is_connected:
        try:
            document_count = await count_documents()
        except Exception:  # noqa: BLE001 - health must never raise
            database_state = "error"
    return HealthResponse(
        status="ok",
        database=database_state,
        document_count=document_count,
    )


@router.post("/chat", tags=["chat"])
async def chat(request: ChatRequest) -> StreamingResponse:
    """Stream the agent's reasoning and answer as Server-Sent Events.

    Each frame is a JSON object with a ``type``:

    - ``status`` — the agent changed phase (``thinking``, ``answering``)
    - ``step``   — a tool was called, or its results came back
    - ``sources``— retrieved passages with their source and similarity score
    - ``token``  — a piece of the answer text
    - ``done``   — the run finished
    - ``error``  — the run failed (sent instead of ``done``)
    """

    async def event_stream() -> AsyncIterator[str]:
        try:
            async for event in stream_agent_events(
                request.query,
                session_id=request.session_id,
                user_id=request.user_id,
            ):
                yield _sse(event)
        except Exception as exc:  # noqa: BLE001 - report error inside the stream
            logger.exception("Streaming chat failed.")
            yield _sse({"type": "error", "detail": str(exc)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post(
    "/chat/sync",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    tags=["chat"],
)
async def chat_sync(request: ChatRequest) -> ChatResponse:
    """Run the agent to completion and return the full answer in one response."""
    answer = await run_agent(
        request.query,
        session_id=request.session_id,
        user_id=request.user_id,
    )
    return ChatResponse(answer=answer, session_id=request.session_id)


@router.post(
    "/summarize",
    response_model=SummarizeResponse,
    status_code=status.HTTP_200_OK,
    tags=["chat"],
)
async def summarize(request: SummarizeRequest) -> SummarizeResponse:
    """Turn a conversation into revision-ready Markdown notes."""
    notes = await summarize_conversation([(t.role, t.content) for t in request.turns])
    return SummarizeResponse(notes=notes)


@router.post(
    "/learn",
    response_model=LearnResponse,
    status_code=status.HTTP_200_OK,
    tags=["learn"],
)
async def learn(request: LearnRequest) -> LearnResponse:
    """Generate grounded learning content (quizzes, flashcards, explanations, assessments)."""
    return await generate_learn_content(request)

