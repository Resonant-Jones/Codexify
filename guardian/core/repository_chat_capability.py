"""Fail-closed ordinary-chat eligibility for bound repository search.

This seam derives only the current thread's authoritative Project identity.
Repository roots and binding metadata remain inside the Stage 2K.1 resolver.
"""

from __future__ import annotations

from collections.abc import Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

from guardian.core.repository_authority import (
    RepositoryAuthorityError,
    resolve_project_repository_binding,
)


@dataclass(frozen=True)
class RepositoryChatCapabilityContext:
    """Private, in-memory authority needed to hydrate one search dispatch."""

    project_id: int

    def __post_init__(self) -> None:
        if (
            not isinstance(self.project_id, int)
            or isinstance(self.project_id, bool)
            or self.project_id <= 0
        ):
            raise ValueError("repository chat capability requires a positive project_id")


def _positive_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if not isinstance(value, int) or value <= 0:
        return None
    return value


def _read_only_session_factory(chatlog_db: Any) -> Any:
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


def resolve_repository_chat_capability(
    chatlog_db: Any,
    *,
    authenticated_account_id: str | None,
    thread_id: int,
) -> RepositoryChatCapabilityContext | None:
    """Resolve one thread-owned, binding-backed Project or fail closed.

    Eligibility is intentionally optional: expected authority or storage
    failures suppress repository search while leaving ordinary chat available.
    The resolver performs no writes and returns only the Project identity.
    """

    account_id = str(authenticated_account_id or "").strip()
    normalized_thread_id = _positive_int(thread_id)
    if not account_id or normalized_thread_id is None or chatlog_db is None:
        return None

    get_chat_thread = getattr(chatlog_db, "get_chat_thread", None)
    get_session = _read_only_session_factory(chatlog_db)
    if not callable(get_chat_thread) or not callable(get_session):
        return None

    try:
        thread = get_chat_thread(normalized_thread_id)
    except Exception:
        return None
    if not isinstance(thread, Mapping):
        return None
    if thread.get("user_id") != account_id:
        return None

    project_id = _positive_int(thread.get("project_id"))
    if project_id is None:
        return None

    try:
        with get_session() as session:
            resolve_project_repository_binding(
                session,
                authenticated_account_id=account_id,
                project_id=project_id,
            )
    except RepositoryAuthorityError:
        return None
    except Exception:
        return None

    return RepositoryChatCapabilityContext(project_id=project_id)
