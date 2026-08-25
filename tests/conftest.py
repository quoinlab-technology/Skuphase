"""Global pytest configuration for deterministic test imports."""

import os


# Required settings used at import time by app modules.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/skuphase_test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-with-minimum-32-chars!")
os.environ.setdefault("GROK_API_KEY", "test-grok-key")
