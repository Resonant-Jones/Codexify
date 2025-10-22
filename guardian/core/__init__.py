"""
guardian.core package

Exposes the active database adapter as ``guardian.core.db`` while keeping
other submodules importable (event_bus, chat_db, etc.). The adapter is
selected based on ``DATABASE_URL`` so that Postgres deployments don't
accidentally fall back to the SQLite helper module.
"""

from __future__ import annotations

import logging
import os
from importlib import import_module
from types import ModuleType
from typing import Optional

_logger = logging.getLogger(__name__)


def _detect_database_url() -> str:
    """
    Resolve the configured database URL, favouring DATABASE_URL but
    allowing explicit overrides via GUARDIAN_DATABASE_URL.
    """
    return (
        os.getenv("DATABASE_URL")
        or os.getenv("GUARDIAN_DATABASE_URL")
        or ""
    )


def _load_db_module() -> ModuleType:
    url = _detect_database_url().strip()
    lowered = url.lower()
    use_postgres = lowered.startswith("postgres://") or lowered.startswith("postgresql://")

    if use_postgres:
        try:
            module = import_module("guardian.core.pgdb")
            _logger.info("guardian.core: using PostgreSQL backend for DATABASE_URL")
            return module  # type: ignore[return-value]
        except Exception as exc:  # pragma: no cover - import failure fallback
            _logger.exception("guardian.core: failed to import Postgres backend, falling back to SQLite: %s", exc)

    if url:
        _logger.info("guardian.core: using SQLite fallback for DATABASE_URL=%s", url)
    else:
        _logger.info("guardian.core: DATABASE_URL not set, using SQLite fallback")
    return import_module("guardian.core.db")  # type: ignore[return-value]


db: ModuleType = _load_db_module()

__all__ = ["db"]
