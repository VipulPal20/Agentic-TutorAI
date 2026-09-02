"""Shared pytest configuration.

Ensures a dummy Gemini key exists so importing settings never fails during
collection. All real Gemini/DB calls are mocked in the individual tests.
"""

from __future__ import annotations

import os

os.environ.setdefault("GOOGLE_API_KEY", "test-key")
os.environ.setdefault("LANGFUSE_ENABLED", "false")
