"""Document ingestion pipeline: load -> chunk -> embed -> upsert.

Supports:
  - .txt / .md  — plain text (original)
  - .pdf        — extracted via pypdf
  - .docx       — extracted via python-docx
  - .png / .jpg / .jpeg / .webp — OCR via Gemini Vision

Usage (CLI):
    python -m database.ingest --path data/sample_docs
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import io
import pathlib
from typing import Any

from core.logging import get_logger
from database.chunking import Chunk, chunk_documents
from database.repository import upsert_documents
from database.schema import init_db
from database.session import db

logger = get_logger(__name__)

SUPPORTED_SUFFIXES = {".txt", ".md", ".pdf", ".docx", ".png", ".jpg", ".jpeg", ".webp"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
TEXT_SUFFIXES = {".txt", ".md"}
PDF_SUFFIX = ".pdf"
DOCX_SUFFIX = ".docx"


# ---------------------------------------------------------------------------
# Text extraction per file type
# ---------------------------------------------------------------------------

def _extract_text_from_pdf(raw: bytes) -> str:
    """Extract text from a PDF using pypdf."""
    import pypdf  # lazy import – only needed when processing PDFs

    reader = pypdf.PdfReader(io.BytesIO(raw))
    parts: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            parts.append(text)
    return "\n\n".join(parts)


def _extract_text_from_docx(raw: bytes) -> str:
    """Extract text from a DOCX using python-docx."""
    import docx  # lazy import – only needed when processing DOCX

    doc = docx.Document(io.BytesIO(raw))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)


async def _extract_text_from_image(raw: bytes, mime_type: str) -> str:
    """OCR an image using the Gemini Vision API."""
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.messages import HumanMessage
    from core.config import settings

    b64 = base64.b64encode(raw).decode("utf-8")
    model = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=settings.google_api_key.get_secret_value(),
        temperature=0.0,
    )
    message = HumanMessage(
        content=[
            {
                "type": "text",
                "text": (
                    "Extract all text visible in this image. "
                    "Return only the extracted text, preserving structure. "
                    "If there is no readable text, return an empty string."
                ),
            },
            {
                "type": "image_url",
                "image_url": {"url": f"data:{mime_type};base64,{b64}"},
            },
        ]
    )
    response = await model.ainvoke([message])
    content = response.content
    if isinstance(content, list):
        return " ".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in content
        )
    return str(content)


def _suffix_to_mime(suffix: str) -> str:
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }.get(suffix.lower(), "image/png")


# ---------------------------------------------------------------------------
# Core ingest helpers
# ---------------------------------------------------------------------------

async def extract_text(filename: str, raw: bytes) -> str:
    """Dispatch to the right extractor based on file extension."""
    suffix = pathlib.Path(filename).suffix.lower()
    if suffix in TEXT_SUFFIXES:
        return raw.decode("utf-8", errors="replace")
    elif suffix == PDF_SUFFIX:
        return _extract_text_from_pdf(raw)
    elif suffix == DOCX_SUFFIX:
        return _extract_text_from_docx(raw)
    elif suffix in IMAGE_SUFFIXES:
        return await _extract_text_from_image(raw, _suffix_to_mime(suffix))
    else:
        # Attempt UTF-8 decode as a fallback
        return raw.decode("utf-8", errors="replace")


async def embed_chunks(chunks: list[Chunk]) -> list[dict[str, Any]]:
    """Embed chunk contents and pair vectors back to chunks."""
    from core.llm import get_embeddings
    
    embeddings = get_embeddings()
    texts = [chunk.content for chunk in chunks]
    
    # OpenAIEmbeddings handles its own batching and retries natively
    vectors = await embeddings.aembed_documents(texts)

    return [
        {"content": chunk.content, "metadata": chunk.metadata, "embedding": vector}
        for chunk, vector in zip(chunks, vectors, strict=True)
    ]


# ---------------------------------------------------------------------------
# Public API used by the upload route
# ---------------------------------------------------------------------------

async def ingest_bytes(filename: str, raw: bytes, mime_type: str = "") -> int:
    """Ingest a single file provided as raw bytes.

    Called by the upload API route. The database connection pool must already
    be open (i.e., this runs inside the FastAPI lifespan).

    Returns the number of chunks stored.
    """
    text = await extract_text(filename, raw)
    if not text.strip():
        logger.warning("No text extracted from %s — skipping.", filename)
        return 0

    documents = [
        {
            "content": text,
            "metadata": {"source": filename, "original_filename": filename},
        }
    ]
    chunks = chunk_documents(documents)
    logger.info("File %s -> %d chunk(s).", filename, len(chunks))

    records = await embed_chunks(chunks)
    stored = await upsert_documents(records)
    logger.info("Ingested %s: %d chunk(s) stored.", filename, stored)
    return stored


# ---------------------------------------------------------------------------
# CLI entry point (unchanged behaviour)
# ---------------------------------------------------------------------------

def load_documents(path: pathlib.Path) -> list[dict[str, Any]]:
    """Load supported text files from a file or directory into doc dicts."""
    candidates = [path] if path.is_file() else sorted(path.rglob("*"))
    documents: list[dict[str, Any]] = []
    for candidate in candidates:
        if candidate.is_file() and candidate.suffix.lower() in SUPPORTED_SUFFIXES:
            documents.append(
                {
                    "content": candidate.read_text(encoding="utf-8"),
                    "metadata": {"source": candidate.name, "path": str(candidate)},
                }
            )
    return documents


async def ingest_path(path: pathlib.Path) -> int:
    """Full ingestion for a path. Returns the number of chunks stored."""
    documents = load_documents(path)
    if not documents:
        logger.warning("No ingestible documents found at %s", path)
        return 0

    chunks = chunk_documents(documents)
    logger.info("Loaded %d document(s) -> %d chunk(s).", len(documents), len(chunks))

    records = await embed_chunks(chunks)

    await init_db()
    await db.connect()
    try:
        stored = await upsert_documents(records)
    finally:
        await db.disconnect()

    logger.info("Ingestion complete: %d chunk(s) stored.", stored)
    return stored


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest documents into pgvector.")
    parser.add_argument(
        "--path",
        type=pathlib.Path,
        default=pathlib.Path("data/sample_docs"),
        help="File or directory of documents to ingest.",
    )
    args = parser.parse_args()
    asyncio.run(ingest_path(args.path))


if __name__ == "__main__":
    main()
