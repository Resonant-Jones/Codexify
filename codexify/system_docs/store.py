"""
System document storage helpers.

System docs are long-form, optionally scoped documents that can be attached
to a user's configuration and included in the system prompt.
"""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from guardian.core.dependencies import get_database_dsn
from guardian.db.models import SystemDoc, SystemDocLink

_SessionFactory: Optional[sessionmaker] = None


def _get_session_factory() -> sessionmaker:
    """Return a cached Session factory backed by the configured DSN."""
    global _SessionFactory
    if _SessionFactory is not None:
        return _SessionFactory
    dsn = get_database_dsn()
    if not dsn:
        raise RuntimeError("Database DSN not configured; cannot access system docs store.")
    engine = create_engine(dsn, future=True)
    _SessionFactory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    return _SessionFactory


def _set_session_factory(factory: sessionmaker) -> None:
    """Test hook to override the session factory."""
    global _SessionFactory
    _SessionFactory = factory


def get_docs_for(user_id: str, project_id: Optional[int]) -> List[SystemDoc]:
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
        unique_docs: List[SystemDoc] = []
        for d in docs:
            if d.id in seen:
                continue
            seen.add(d.id)
            unique_docs.append(d)
        return unique_docs


def estimate_token_cost_for_docs(docs: List[SystemDoc]) -> int:
    """Rough heuristic: 1 token ~= 4 chars."""
    return sum(len(d.content or "") for d in docs) // 4


__all__ = [
    "get_docs_for",
    "estimate_token_cost_for_docs",
    "_set_session_factory",
]
