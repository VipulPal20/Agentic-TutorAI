"""Tests for application settings."""

from __future__ import annotations

from core.config import Settings, settings


def test_gemini_defaults() -> None:
    assert settings.chat_model == "gemini-2.0-flash"
    assert settings.embedding_model == "models/text-embedding-004"
    assert settings.embedding_dim == 768


def test_async_dsn_built_from_parts(monkeypatch) -> None:
    monkeypatch.setenv("POSTGRES_USER", "u")
    monkeypatch.setenv("POSTGRES_PASSWORD", "p")
    monkeypatch.setenv("POSTGRES_HOST", "h")
    monkeypatch.setenv("POSTGRES_PORT", "6543")
    monkeypatch.setenv("POSTGRES_DB", "d")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    built = Settings(_env_file=None)
    assert built.async_dsn == "postgresql://u:p@h:6543/d"


def test_database_url_overrides_parts(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://x:y@host:5432/z")
    built = Settings(_env_file=None)
    assert built.async_dsn == "postgresql://x:y@host:5432/z"


def test_langfuse_ready_requires_keys(monkeypatch) -> None:
    monkeypatch.setenv("LANGFUSE_ENABLED", "true")
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    built = Settings(_env_file=None)
    # Enabled but no keys -> not ready.
    assert built.langfuse_ready is False

    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk")
    assert Settings(_env_file=None).langfuse_ready is True
