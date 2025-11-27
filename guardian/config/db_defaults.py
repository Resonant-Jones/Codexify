"""Shared defaults for database configuration."""

from __future__ import annotations

import os
from typing import Final

_DEFAULT_COMPOSE_DSN: Final[
    str
] = "postgresql://guardian:guardian@db:5432/guardian"

# Compute the default DSN once, honoring any pre-existing environment overrides.
DEFAULT_PG_DSN: Final[str] = (
    os.getenv("GUARDIAN_DB_URL")
    or os.getenv("DATABASE_URL")
    or _DEFAULT_COMPOSE_DSN
)

__all__ = ["DEFAULT_PG_DSN"]
