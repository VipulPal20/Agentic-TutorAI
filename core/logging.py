"""Structured-ish stdout logging configuration.

Call :func:`configure_logging` once at application startup. Logs go to stdout
so Docker / CI capture them without extra config.
"""

from __future__ import annotations

import logging
import sys

from core.config import settings

_CONFIGURED = False


def configure_logging() -> None:
    """Configure the root logger. Idempotent — safe to call more than once."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(settings.log_level.upper())

    # Quiet the noisy uvicorn access log; keep our application logs.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a named logger (configures logging lazily on first use)."""
    configure_logging()
    return logging.getLogger(name)
