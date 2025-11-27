"""
System document storage helpers.

System docs are long-form, optionally scoped documents that can be attached
to a user's configuration and included in the system prompt.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from guardian.core.dependencies import get_database_dsn
from guardian.db.models import SystemDoc, SystemDocLink

_SessionFactory: sessionmaker | None = None


def _get_session_factory() -> sessionmaker:
    """Return a cached Session factory backed by the configured DSN."""
    global _SessionFactory
    if _SessionFactory is not None:
        return _SessionFactory
    dsn = get_database_dsn()
    if not dsn:
        raise RuntimeError(
            "Database DSN not configured; cannot access system docs store."
        )
    engine = create_engine(dsn, future=True)
    _SessionFactory = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True
    )
    return _SessionFactory


def _set_session_factory(factory: sessionmaker) -> None:
    """Test hook to override the session factory."""
    global _SessionFactory
    _SessionFactory = factory


def get_docs_for(user_id: str, project_id: int | None) -> list[SystemDoc]:
    """
    Return enabled docs attached to (user_id, project_id).
    Includes:
      - Docs explicitly linked via system_doc_links where is_enabled=True and doc is_enabled=True
      - Global docs that are enabled (scope='global'), regardless of links
    """
    Session = _get_session_factory()
    with Session() as session:
        docs = []

        # Linked docs
        link_stmt = (
            select(SystemDoc)
            .join(SystemDocLink, SystemDoc.id == SystemDocLink.system_doc_id)
            .where(
                SystemDoc.is_enabled.is_(True),
                SystemDocLink.is_enabled.is_(True),
                SystemDocLink.user_id == user_id,
                SystemDocLink.project_id == project_id,
            )
        )
        docs.extend(session.scalars(link_stmt).all())

        # Global docs (enabled) included by default
        global_stmt = select(SystemDoc).where(
            SystemDoc.scope == "global",
            SystemDoc.is_enabled.is_(True),
        )
        docs.extend(session.scalars(global_stmt).all())

        # Deduplicate by id while preserving order (linked first)
        seen = set()
        unique_docs: list[SystemDoc] = []
        for d in docs:
            if d.id in seen:
                continue
            seen.add(d.id)
            unique_docs.append(d)
        return unique_docs


def list_docs_with_links(
    user_id: str, project_id: int | None
) -> list[tuple[SystemDoc, bool]]:
    """
    Return docs paired with an enabled flag for a given (user, project).
    - Global docs: enabled reflects SystemDoc.is_enabled.
    - Linked docs: enabled reflects link.is_enabled AND doc.is_enabled.
    """
    Session = _get_session_factory()
    with Session() as session:
        results: list[tuple[SystemDoc, bool]] = []

        # Linked docs for user/project
        link_stmt = (
            select(SystemDoc, SystemDocLink.is_enabled)
            .join(SystemDocLink, SystemDoc.id == SystemDocLink.system_doc_id)
            .where(
                SystemDocLink.user_id == user_id,
                SystemDocLink.project_id == project_id,
            )
        )
        for doc, enabled in session.execute(link_stmt):
            results.append((doc, bool(enabled and doc.is_enabled)))

        # Global docs (enabled) always included with enabled flag from doc
        global_stmt = select(SystemDoc).where(
            SystemDoc.scope == "global",
            SystemDoc.is_enabled.is_(True),
        )
        for doc in session.scalars(global_stmt):
            results.append((doc, bool(doc.is_enabled)))

        # Deduplicate by id (prefer linked setting over global)
        seen = set()
        unique: list[tuple[SystemDoc, bool]] = []
        for doc, enabled in results:
            if doc.id in seen:
                continue
            seen.add(doc.id)
            unique.append((doc, enabled))
        return unique


def set_doc_link(
    user_id: str, project_id: int | None, doc_id: int, enabled: bool
) -> None:
    """
    Create or update a SystemDocLink for (user, project, doc).
    Note: global docs cannot be disabled globally; this only affects the link.
    """
    Session = _get_session_factory()
    with Session() as session:
        # Ensure doc exists
        doc = session.get(SystemDoc, doc_id)
        if not doc:
            raise ValueError("System doc not found")

        link = (
            session.query(SystemDocLink)
            .filter(
                SystemDocLink.user_id == user_id,
                SystemDocLink.project_id == project_id,
                SystemDocLink.system_doc_id == doc_id,
            )
            .first()
        )
        if link:
            link.is_enabled = enabled
        else:
            link = SystemDocLink(
                user_id=user_id,
                project_id=project_id,
                system_doc_id=doc_id,
                is_enabled=enabled,
            )
            session.add(link)
        session.commit()


def estimate_token_cost_for_docs(docs: list[SystemDoc]) -> int:
    """Rough heuristic: 1 token ~= 4 chars."""
    return sum(len(d.content or "") for d in docs) // 4


__all__ = [
    "get_docs_for",
    "estimate_token_cost_for_docs",
    "list_docs_with_links",
    "set_doc_link",
    "_set_session_factory",
]
