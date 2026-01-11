"""
Imprint storage helpers.

Provides minimal CRUD helpers for Imprint_Zero data with the invariant that
only one imprint may be active for a given (user_id, project_id) pair.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import sessionmaker

from guardian.core.dependencies import get_database_dsn
from guardian.db.models import Imprint

_SessionFactory: sessionmaker | None = None


def _get_session_factory() -> sessionmaker:
    """Return a cached Session factory backed by the configured DSN."""
    global _SessionFactory
    if _SessionFactory is not None:
        return _SessionFactory
    dsn = get_database_dsn()
    if not dsn:
        raise RuntimeError(
            "Database DSN not configured; cannot access imprints store."
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


def get_active_imprint(user_id: str, project_id: int | None) -> Imprint | None:
    """Return the active imprint for (user_id, project_id), if any."""
    Session = _get_session_factory()
    with Session() as session:
        stmt = select(Imprint).where(
            Imprint.user_id == user_id,
            Imprint.project_id == project_id,
            Imprint.status == "active",
        )
        return session.scalars(stmt).first()


def get_imprint_by_id(imprint_id: int) -> Imprint | None:
    """Fetch an imprint by primary key."""
    Session = _get_session_factory()
    with Session() as session:
        return session.get(Imprint, imprint_id)


def save_imprint(
    user_id: str,
    project_id: int | None,
    **fields: Any,
) -> Imprint:
    """
    Create an imprint row (defaults to status='draft' unless provided).
    Does not activate it; call activate_imprint after creation to set it active.
    """
    Session = _get_session_factory()
    with Session() as session:
        imprint = Imprint(
            user_id=user_id,
            project_id=project_id,
            status=fields.get("status", "draft"),
            guardian_name=fields.get("guardian_name"),
            preferred_name=fields.get("preferred_name"),
            style=fields.get("style"),
            grammar_prefs=fields.get("grammar_prefs") or {},
            metrics=fields.get("metrics") or {},
            heat_score=fields.get("heat_score"),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(imprint)
        session.commit()
        session.refresh(imprint)
        return imprint


def activate_imprint(imprint_id: int) -> Imprint:
    """
    Mark the given imprint as active and supersede any prior actives for the same (user, project).
    """
    Session = _get_session_factory()
    with Session() as session:
        imprint = session.get(Imprint, imprint_id)
        if not imprint:
            raise ValueError(f"Imprint {imprint_id} not found")

        # Supersede existing actives for this (user, project)
        session.execute(
            update(Imprint)
            .where(
                Imprint.user_id == imprint.user_id,
                Imprint.project_id == imprint.project_id,
                Imprint.status == "active",
                Imprint.id != imprint.id,
            )
            .values(status="superseded", updated_at=datetime.utcnow())
        )

        imprint.status = "active"
        imprint.updated_at = datetime.utcnow()
        session.add(imprint)
        session.commit()
        session.refresh(imprint)
        return imprint


def supersede_imprint(imprint_id: int) -> Imprint | None:
    """Mark an imprint as superseded."""
    Session = _get_session_factory()
    with Session() as session:
        imprint = session.get(Imprint, imprint_id)
        if not imprint:
            return None
        imprint.status = "superseded"
        imprint.updated_at = datetime.utcnow()
        session.add(imprint)
        session.commit()
        session.refresh(imprint)
        return imprint


__all__ = [
    "get_active_imprint",
    "save_imprint",
    "activate_imprint",
    "get_imprint_by_id",
    "supersede_imprint",
    "_set_session_factory",
]
