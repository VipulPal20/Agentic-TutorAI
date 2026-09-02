"""Factories for the Google Gemini chat model and embeddings client.

Kept in ``core`` (not ``agent`` or ``tools``) because both the database layer
(for ingestion) and the tools layer (for query embedding) need the embeddings
client, and centralising construction here avoids circular imports.
"""

from __future__ import annotations

from functools import lru_cache

from langchain_groq import ChatGroq
from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings

from core.config import settings


@lru_cache
def get_chat_model() -> ChatGroq:
    """Return a cached Groq chat model configured from settings."""
    return ChatGroq(
        model=settings.chat_model,
        api_key=settings.groq_api_key.get_secret_value(),
        temperature=settings.llm_temperature,
    )


@lru_cache
def get_embeddings() -> NVIDIAEmbeddings:
    """Return a cached NVIDIA embeddings client configured from settings."""
    return NVIDIAEmbeddings(
        model=settings.embedding_model,
        api_key=settings.nvidia_api_key.get_secret_value(),
    )
