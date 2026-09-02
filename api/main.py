"""FastAPI application factory, lifespan, and central error handling."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from agent.graph import get_compiled_graph
from api.routes import router
from api.upload import upload_router
from core.config import settings
from core.exceptions import AppError
from core.logging import configure_logging, get_logger
from database.schema import init_db
from database.session import db

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Manage startup/shutdown resources.

    Ordering matters: :func:`init_db` creates the pgvector extension before the
    pool is opened, because the pool's connection initializer registers the
    pgvector codec (which needs the ``vector`` type to exist).
    """
    logger.info("Starting %s (env=%s)...", settings.app_name, settings.environment)
    try:
        await init_db()
        await db.connect()
        get_compiled_graph()  # compile/warm the agent graph up front
    except Exception:
        logger.exception("Startup failed.")
        raise
    logger.info("Startup complete; ready to serve.")
    yield
    await db.disconnect()
    logger.info("Shutdown complete.")


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    app = FastAPI(
        title="Agentic RAG API",
        description="Agentic RAG backend (LangGraph + pgvector + Gemini).",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)
    app.include_router(upload_router)

    @app.exception_handler(AppError)
    async def handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
        """Map known application errors to their HTTP status + safe message."""
        logger.warning("AppError (%s): %s", exc.status_code, exc.message)
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": type(exc).__name__, "detail": exc.message},
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(_request: Request, _exc: Exception) -> JSONResponse:
        """Catch-all so clients never receive an unstructured 500."""
        logger.exception("Unhandled exception.")
        return JSONResponse(
            status_code=500,
            content={"error": "InternalServerError", "detail": "An unexpected error occurred."},
        )

    return app


app = create_app()
