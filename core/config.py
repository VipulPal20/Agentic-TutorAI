"""Application settings, loaded from environment variables / `.env`.

Uses pydantic-settings (Pydantic v2). All configuration flows through the
singleton returned by :func:`get_settings`, so nothing in the codebase reads
``os.environ`` directly.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed application configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---- App ----
    app_name: str = "agentic-rag"
    environment: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])

    # ---- API Keys and Models ----
    google_api_key: SecretStr = SecretStr("")
    groq_api_key: SecretStr = SecretStr("")
    nvidia_api_key: SecretStr = SecretStr("")
    chat_model: str = "gemini-2.0-flash"
    embedding_model: str = "models/text-embedding-004"
    # text-embedding-004 -> 768. This value defines the pgvector column width;
    # changing the embedding model requires re-creating the documents table.
    embedding_dim: int = 768
    llm_temperature: float = 0.0

    # ---- PostgreSQL / pgvector ----
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "postgres"
    postgres_password: SecretStr = SecretStr("postgres")
    postgres_db: str = "ragdb"
    db_pool_min_size: int = 1
    db_pool_max_size: int = 10
    database_url: str | None = None  # optional full DSN override

    # ---- Retrieval / chunking ----
    retrieval_top_k: int = 4
    chunk_size: int = 1000
    chunk_overlap: int = 150

    # ---- Langfuse (observability) ----
    langfuse_enabled: bool = False
    langfuse_public_key: SecretStr = SecretStr("")
    langfuse_secret_key: SecretStr = SecretStr("")
    langfuse_host: str = "https://cloud.langfuse.com"

    # ---- Optional tool providers ----
    tavily_api_key: SecretStr = SecretStr("")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def async_dsn(self) -> str:
        """Return an asyncpg-compatible DSN.

        asyncpg wants a plain ``postgresql://`` DSN (no SQLAlchemy-style
        ``+asyncpg`` driver suffix). A full ``DATABASE_URL`` override wins if set.
        """
        if self.database_url:
            return self.database_url
        password = self.postgres_password.get_secret_value()
        return (
            f"postgresql://{self.postgres_user}:{password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def langfuse_ready(self) -> bool:
        """True only when tracing is enabled *and* both keys are present."""
        return (
            self.langfuse_enabled
            and bool(self.langfuse_public_key.get_secret_value())
            and bool(self.langfuse_secret_key.get_secret_value())
        )


@lru_cache
def get_settings() -> Settings:
    """Return the cached settings singleton."""
    return Settings()


# Module-level convenience handle. Safe to import anywhere.
settings = get_settings()
