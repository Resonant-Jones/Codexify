"""Event graph persistence with idempotent write keys and causal references."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from guardian.core.dependencies import get_database_dsn
from guardian.db.models import EventGraphEvent

_SessionFactory: sessionmaker | None = None
_SENSITIVE_PAYLOAD_KEYS = {
    "content",
    "body",
    "text",
    "raw_content",
    "message_content",
}


def _get_session_factory() -> sessionmaker:
    global _SessionFactory
    if _SessionFactory is not None:
        return _SessionFactory
    dsn = get_database_dsn()
    if not dsn:
        raise RuntimeError(
            "Database DSN not configured; cannot access event graph store."
        )
    engine = create_engine(dsn, future=True)
    _SessionFactory = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True
    )
    return _SessionFactory


def _set_session_factory(factory: sessionmaker) -> None:
    global _SessionFactory
    _SessionFactory = factory


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _sanitize_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not payload:
        return {}
    sanitized: dict[str, Any] = {}
    for key, value in payload.items():
        if key.lower() in _SENSITIVE_PAYLOAD_KEYS:
            continue
        sanitized[key] = value
    return sanitized


class EventWriter:
    """Persist idempotent event graph entries."""

    def __init__(self, session_factory: sessionmaker | None = None) -> None:
        self._session_factory = session_factory

    @property
    def session_factory(self) -> sessionmaker:
        return self._session_factory or _get_session_factory()

    def emit_event(
        self,
        *,
        event_type: str,
        actor_user_id: str | None,
        project_id: int | None,
        thread_id: int | None,
        entity_type: str | None,
        entity_id: str | None,
        payload: dict[str, Any] | None,
        parent_event_id: int | None,
        idempotency_key: str,
    ) -> int:
        Session = self.session_factory
        with Session() as session:
            existing = session.scalars(
                select(EventGraphEvent).where(
                    EventGraphEvent.idempotency_key == idempotency_key
                )
            ).first()
            if existing is not None:
                return int(existing.event_id)

            row = EventGraphEvent(
                event_type=event_type,
                occurred_at=_utcnow(),
                actor_user_id=actor_user_id,
                project_id=project_id,
                thread_id=thread_id,
                entity_type=entity_type,
                entity_id=entity_id,
                idempotency_key=idempotency_key,
                parent_event_id=parent_event_id,
                payload_json=_sanitize_payload(payload),
            )
            session.add(row)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                existing = session.scalars(
                    select(EventGraphEvent).where(
                        EventGraphEvent.idempotency_key == idempotency_key
                    )
                ).first()
                if existing is None:
                    raise
                return int(existing.event_id)
            session.refresh(row)
            return int(row.event_id)

    def list_events_by_thread(self, thread_id: int) -> list[EventGraphEvent]:
        Session = self.session_factory
        with Session() as session:
            rows = (
                session.query(EventGraphEvent)
                .filter(EventGraphEvent.thread_id == thread_id)
                .order_by(
                    EventGraphEvent.occurred_at.asc(),
                    EventGraphEvent.event_id.asc(),
                )
                .all()
            )
            return list(rows)

    def get_event_by_idempotency(
        self, idempotency_key: str
    ) -> EventGraphEvent | None:
        Session = self.session_factory
        with Session() as session:
            return session.scalars(
                select(EventGraphEvent).where(
                    EventGraphEvent.idempotency_key == idempotency_key
                )
            ).first()

    def get_latest_event_id(
        self, *, thread_id: int | None, event_type: str | None = None
    ) -> int | None:
        Session = self.session_factory
        with Session() as session:
            query = session.query(EventGraphEvent)
            if thread_id is not None:
                query = query.filter(EventGraphEvent.thread_id == thread_id)
            if event_type:
                query = query.filter(EventGraphEvent.event_type == event_type)
            row = query.order_by(
                EventGraphEvent.occurred_at.desc(),
                EventGraphEvent.event_id.desc(),
            ).first()
            return int(row.event_id) if row is not None else None


_event_writer: EventWriter | None = None


def get_event_writer() -> EventWriter:
    global _event_writer
    if _event_writer is None:
        _event_writer = EventWriter()
    return _event_writer


def reset_event_writer() -> None:
    global _event_writer
    _event_writer = None


__all__ = [
    "EventWriter",
    "get_event_writer",
    "reset_event_writer",
    "_set_session_factory",
]
