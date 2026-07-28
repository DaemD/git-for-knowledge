"""Pytest bootstrap: auth-disabled settings before app imports."""

from __future__ import annotations

import os

os.environ.setdefault("AUTH_DISABLED", "true")
os.environ.setdefault("MEMORY_API_KEY", "test-nams-key")
os.environ.setdefault("MEMORY_WORKSPACE_ID", "ws-shared-test")
os.environ.setdefault("PUBLIC_BASE_URL", "http://test.local")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://unused:unused@localhost:5432/unused",
)

from app.config import get_settings

get_settings.cache_clear()
