"""Upload and knowledge-base management routes.

Endpoints:
    POST   /upload              — ingest one or more files into the vector store
    GET    /sources             — list all source files with chunk counts
    DELETE /sources/{name}      — remove all chunks for a given source file
"""

from __future__ import annotations

import urllib.parse

from fastapi import APIRouter, HTTPException, UploadFile, status

from api.schemas import (
    DeleteSourceResponse,
    SourceItem,
    SourcesResponse,
    UploadFileResult,
    UploadResponse,
)
from core.logging import get_logger
from database.ingest import ingest_bytes
from database.repository import delete_source, list_sources

logger = get_logger(__name__)
upload_router = APIRouter(tags=["knowledge"])

# 50 MB per file limit
_MAX_FILE_SIZE = 50 * 1024 * 1024

ALLOWED_EXTENSIONS = {
    ".txt",
    ".md",
    ".pdf",
    ".docx",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
}


@upload_router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload documents into the knowledge base",
)
async def upload_documents(files: list[UploadFile]) -> UploadResponse:
    """Accept one or more files and ingest them into the vector store.

    Supported formats: ``.txt``, ``.md``, ``.pdf``, ``.docx``,
    ``.png``, ``.jpg``, ``.jpeg``, ``.webp``.

    Each file is text-extracted, chunked, embedded, and inserted into
    the pgvector ``documents`` table. The response lists per-file
    outcomes so partial failures are visible.
    """
    if not files:
        raise HTTPException(status_code=422, detail="No files were provided.")

    results: list[UploadFileResult] = []

    for upload in files:
        filename = upload.filename or "unknown"
        import pathlib
        suffix = pathlib.Path(filename).suffix.lower()

        if suffix not in ALLOWED_EXTENSIONS:
            results.append(
                UploadFileResult(
                    filename=filename,
                    chunks_stored=0,
                    status="error",
                    detail=f"Unsupported file type '{suffix}'. "
                           f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
                )
            )
            continue

        try:
            raw = await upload.read()
            if len(raw) > _MAX_FILE_SIZE:
                results.append(
                    UploadFileResult(
                        filename=filename,
                        chunks_stored=0,
                        status="error",
                        detail=f"File exceeds the 50 MB limit ({len(raw) // 1024 // 1024} MB).",
                    )
                )
                continue

            mime = upload.content_type or ""
            chunks_stored = await ingest_bytes(filename, raw, mime)
            results.append(
                UploadFileResult(
                    filename=filename,
                    chunks_stored=chunks_stored,
                    status="ok",
                )
            )
            logger.info("Uploaded and ingested '%s': %d chunk(s).", filename, chunks_stored)

        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to ingest uploaded file '%s'.", filename)
            results.append(
                UploadFileResult(
                    filename=filename,
                    chunks_stored=0,
                    status="error",
                    detail=str(exc),
                )
            )

    return UploadResponse(uploaded=results)


@upload_router.get(
    "/sources",
    response_model=SourcesResponse,
    status_code=status.HTTP_200_OK,
    summary="List all sources in the knowledge base",
)
async def get_sources() -> SourcesResponse:
    """Return all distinct source files stored in the knowledge base."""
    rows = await list_sources()
    items = [SourceItem(**row) for row in rows]
    total = sum(item.chunk_count for item in items)
    return SourcesResponse(sources=items, total_chunks=total)


@upload_router.delete(
    "/sources/{name:path}",
    response_model=DeleteSourceResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete a source from the knowledge base",
)
async def remove_source(name: str) -> DeleteSourceResponse:
    """Delete all chunks belonging to ``name`` from the vector store."""
    decoded = urllib.parse.unquote(name)
    deleted = await delete_source(decoded)
    if deleted == 0:
        raise HTTPException(
            status_code=404,
            detail=f"Source '{decoded}' not found in the knowledge base.",
        )
    return DeleteSourceResponse(source=decoded, chunks_deleted=deleted)
