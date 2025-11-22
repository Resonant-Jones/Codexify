"""
Postgres-backed chat log repository.

This module provides a single Postgres-first ChatDB implementation for the
Guardian API surface. It is a thin alias around ``PgDB`` so downstream code
can depend on a stable name that is explicitly Postgres-only.
"""

from guardian.core.pgdb import PgDB


class PostgresChatLogDB(PgDB):
    """Postgres-only chat log + connector repository."""


__all__ = ["PostgresChatLogDB"]
