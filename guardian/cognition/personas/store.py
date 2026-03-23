"""
Persona storage helpers.

Maintains user-editable persona prompts with an active flag per (user, project).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import sessionmaker

from guardian.core.dependencies import get_database_dsn
from guardian.core.event_graph import get_event_writer
from guardian.db.models import Persona

logger = logging.getLogger(__name__)

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


def get_persona_by_id(persona_id: int) -> Persona | None:
    """Fetch a persona by primary key."""
    Session = _get_session_factory()
    with Session() as session:
        return session.get(Persona, persona_id)


def list_personas(user_id: str, project_id: int | None) -> list[Persona]:
    """List personas scoped to (user_id, project_id), newest first."""
    Session = _get_session_factory()
    with Session() as session:
        stmt = (
            select(Persona)
            .where(
                Persona.user_id == user_id,
                Persona.project_id == project_id,
            )
            .order_by(Persona.created_at.desc(), Persona.id.desc())
        )
        return list(session.scalars(stmt))


def create_persona(
    user_id: str,
    project_id: int | None,
    name: str,
    content: str,
) -> Persona:
    """Create a non-active persona using the canonical task API shape."""
    Session = _get_session_factory()
    with Session() as session:
        logger.info(
            "[persona_prompt_versions] inserting version row %s",
            {"userId": user_id, "personaId": None},
        )
        persona = Persona(
            user_id=user_id,
            project_id=project_id,
            body=content,
            source=name or "user",
            is_active=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.add(persona)
        session.commit()
        session.refresh(persona)
        return persona


def _activate_persona_with_scope(
    *,
    user_id: str,
    project_id: int | None,
    persona_id: int,
) -> Persona:
    Session = _get_session_factory()
    with Session() as session:
        persona = session.get(Persona, persona_id)
        if not persona:
            raise ValueError(f"Persona {persona_id} not found")
        if persona.user_id != user_id or persona.project_id != project_id:
            raise ValueError("persona scope mismatch")

        session.execute(
            update(Persona)
            .where(
                Persona.user_id == user_id,
                Persona.project_id == project_id,
                Persona.is_active.is_(True),
                Persona.id != persona.id,
            )
            .values(is_active=False, updated_at=datetime.now(timezone.utc))
        )

        persona.is_active = True
        persona.updated_at = datetime.now(timezone.utc)
        session.add(persona)
        session.commit()
        session.refresh(persona)
        try:
            activated_at = (
                persona.updated_at
                or persona.created_at
                or datetime.now(timezone.utc)
            )
            idempotency_key = "persona.set:{user_id}:{project_id}:{persona_id}:{activated_at}".format(
                user_id=persona.user_id,
                project_id=persona.project_id,
                persona_id=persona.id,
                activated_at=activated_at.isoformat(),
            )
            get_event_writer().emit_event(
                event_type="persona.set",
                actor_user_id=persona.user_id,
                project_id=persona.project_id,
                thread_id=None,
                entity_type="persona",
                entity_id=str(persona.id),
                payload={
                    "persona_id": persona.id,
                    "source": persona.source,
                },
                parent_event_id=None,
                idempotency_key=idempotency_key,
            )
        except Exception:
            # Event emission is best-effort and must not block activation.
            pass
        return persona


def activate_persona(*args) -> Persona:
    """
    Activate persona in scope.

    Supported call shapes:
    - activate_persona(persona_id)
    - activate_persona(user_id, project_id, persona_id)
    """
    if len(args) == 1:
        persona_id = int(args[0])
        persona = get_persona_by_id(persona_id)
        if not persona:
            raise ValueError(f"Persona {persona_id} not found")
        return _activate_persona_with_scope(
            user_id=persona.user_id,
            project_id=persona.project_id,
            persona_id=persona_id,
        )

    if len(args) == 3:
        user_id = str(args[0])
        project_id = args[1]
        persona_id = int(args[2])
        return _activate_persona_with_scope(
            user_id=user_id,
            project_id=project_id,
            persona_id=persona_id,
        )

    raise TypeError(
        "activate_persona expects (persona_id) or (user_id, project_id, persona_id)"
    )


def set_persona(
    user_id: str, project_id: int | None, body: str, source: str = "user"
) -> Persona:
    """
    Create and activate a persona. Any existing active persona for the pair
    will be deactivated.
    """
    persona = create_persona(
        user_id=user_id,
        project_id=project_id,
        name=source,
        content=body,
    )
    return activate_persona(persona.id)


__all__ = [
    "activate_persona",
    "create_persona",
    "get_active_persona",
    "get_persona_by_id",
    "list_personas",
    "set_persona",
    "_set_session_factory",
]
