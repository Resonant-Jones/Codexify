from __future__ import annotations

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from guardian.cognition.personas import store as persona_store
from guardian.core.event_graph import (
    _set_session_factory,
    get_event_writer,
    reset_event_writer,
)
from guardian.db.models import Base, EventGraphEvent, Persona


def _setup_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(
        bind=engine,
        tables=[EventGraphEvent.__table__, Persona.__table__],
    )
    Session = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True
    )
    _set_session_factory(Session)
    persona_store._set_session_factory(Session)
    reset_event_writer()
    return Session


def test_event_graph_emit_is_idempotent_by_key() -> None:
    Session = _setup_session()
    writer = get_event_writer()

    first_id = writer.emit_event(
        event_type="thread.update",
        actor_user_id="u1",
        project_id=1,
        thread_id=7,
        entity_type="thread",
        entity_id="7",
        payload={"thread_id": 7, "message_id": 2},
        parent_event_id=None,
        idempotency_key="thread.update:7:message:2",
    )
    second_id = writer.emit_event(
        event_type="thread.update",
        actor_user_id="u1",
        project_id=1,
        thread_id=7,
        entity_type="thread",
        entity_id="7",
        payload={"thread_id": 7, "message_id": 2, "ignored": True},
        parent_event_id=None,
        idempotency_key="thread.update:7:message:2",
    )

    assert first_id == second_id
    with Session() as session:
        rows = session.scalars(select(EventGraphEvent)).all()
        assert len(rows) == 1


def test_thread_update_events_queryable_by_thread() -> None:
    _setup_session()
    writer = get_event_writer()
    writer.emit_event(
        event_type="thread.update",
        actor_user_id="u1",
        project_id=1,
        thread_id=42,
        entity_type="thread",
        entity_id="42",
        payload={"thread_id": 42, "message_id": 100},
        parent_event_id=None,
        idempotency_key="thread.update:42:message:100",
    )
    writer.emit_event(
        event_type="thread.update",
        actor_user_id="u1",
        project_id=1,
        thread_id=99,
        entity_type="thread",
        entity_id="99",
        payload={"thread_id": 99, "message_id": 200},
        parent_event_id=None,
        idempotency_key="thread.update:99:message:200",
    )

    rows = writer.list_events_by_thread(42)
    assert len(rows) == 1
    assert rows[0].thread_id == 42
    assert rows[0].event_type == "thread.update"


def test_persona_activation_emits_persona_set_event() -> None:
    Session = _setup_session()
    writer = get_event_writer()

    persona = persona_store.create_persona(
        user_id="u1",
        project_id=9,
        name="user",
        content="persona text",
    )
    activated = persona_store.activate_persona("u1", 9, persona.id)

    with Session() as session:
        rows = session.scalars(
            select(EventGraphEvent)
            .where(EventGraphEvent.event_type == "persona.set")
            .where(EventGraphEvent.entity_id == str(activated.id))
        ).all()
        assert len(rows) == 1
        assert rows[0].project_id == 9
        assert rows[0].actor_user_id == "u1"
        assert rows[0].payload_json.get("persona_id") == activated.id
    assert writer.get_event_by_idempotency(rows[0].idempotency_key) is not None
