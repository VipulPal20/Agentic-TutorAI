"""Application exception hierarchy.

Every custom error carries an HTTP ``status_code`` and a client-safe
``message``. The FastAPI layer maps :class:`AppError` to a JSON response
centrally, so business/data code can raise these without knowing about HTTP.
"""

from __future__ import annotations


class AppError(Exception):
    """Base class for all expected application errors."""

    status_code: int = 500
    default_message: str = "Internal server error."

    def __init__(
        self,
        message: str | None = None,
        *,
        status_code: int | None = None,
    ) -> None:
        self.message = message or self.default_message
        if status_code is not None:
            self.status_code = status_code
        super().__init__(self.message)


class ConfigurationError(AppError):
    """Raised when required configuration (keys, DSN, ...) is missing/invalid."""

    status_code = 500
    default_message = "Service is misconfigured."


class DatabaseError(AppError):
    """Raised when a database connection or query fails."""

    status_code = 503
    default_message = "Database operation failed."


class RetrievalError(AppError):
    """Raised when vector retrieval fails (embedding or search)."""

    status_code = 502
    default_message = "Document retrieval failed."


class AgentError(AppError):
    """Raised when the agent graph fails to produce a response."""

    status_code = 502
    default_message = "The agent failed to produce a response."
