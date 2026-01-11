"""
Persona storage helpers.

Maintains user-editable persona prompts with an active flag per (user, project).
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import sessionmaker

from guardian.core.dependencies import get_database_dsn
from guardian.db.models import Persona

_SessionFactory: sessionmaker | None = None


def _get_session_factory() -> sessionmaker:
    """Return a cached Session factory backed by the configured DSN."""
    global _SessionFactory
    if _SessionFactory is not None:
        return _SessionFactory
    dsn = get_database_dsn()
    if not dsn:
        raise RuntimeError(
            "Database DSN not configured; cannot access personas store."
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


def get_active_persona(user_id: str, project_id: int | None) -> Persona | None:
    """Return the active persona for (user_id, project_id), if any."""
    Session = _get_session_factory()
    with Session() as session:
        stmt = (
            select(Persona)
            .where(
                Persona.user_id == user_id,
                Persona.project_id == project_id,
                Persona.is_active.is_(True),
            )
            .order_by(Persona.created_at.desc())
        )
        return session.scalars(stmt).first()


def set_persona(
    user_id: str, project_id: int | None, body: str, source: str = "user"
) -> Persona:
    """
    Create and activate a persona. Any existing active persona for the pair
    will be deactivated.
    """
    Session = _get_session_factory()
    with Session() as session:
        session.execute(
            update(Persona)
            .where(
                Persona.user_id == user_id,
                Persona.project_id == project_id,
                Persona.is_active.is_(True),
            )
            .values(is_active=False, updated_at=datetime.utcnow())
        )

        persona = Persona(
            user_id=user_id,
            project_id=project_id,
            body=body,
            source=source,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(persona)
        session.commit()
        session.refresh(persona)
        return persona


__all__ = [
    "get_active_persona",
    "set_persona",
    "_set_session_factory",
]
