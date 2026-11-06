"""Read-only session seam for repository authority resolution.

Guardian resolves repository authority against PostgreSQL. A caller that only
needs to *read* authority must not inherit the auto-commit behaviour of the
application's write session, so this seam exposes the existing read session
factory in one place instead of each consumer re-deriving it.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any

__all__ = ["read_only_session_factory"]


def read_only_session_factory(chatlog_db: Any) -> Any:
    """Return the existing session seam without inheriting PgDB auto-commit."""

    get_session = getattr(chatlog_db, "get_session", None)
    if callable(get_session):
        return get_session
    session_factory = getattr(chatlog_db, "_SessionLocal", None)
    if not callable(session_factory):
        return None

    @contextmanager
    def _open_session() -> Any:
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    return _open_session
