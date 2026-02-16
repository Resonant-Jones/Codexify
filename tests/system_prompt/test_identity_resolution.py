from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from guardian.cognition.identity_resolution import (
    resolve_imprint,
    resolve_persona,
)
from guardian.cognition.imprints import store as imprint_store
from guardian.cognition.personas import store as persona_store
from guardian.db.models import Base, Imprint, Persona


def _setup_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(
        bind=engine,
        tables=[Imprint.__table__, Persona.__table__],
    )
    return sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True
    )


def test_imprint_activation_keeps_one_active_per_scope() -> None:
    Session = _setup_session()
    imprint_store._set_session_factory(Session)

    first = imprint_store.create_imprint("u1", 1, "G1", "content1")
    second = imprint_store.create_imprint("u1", 1, "G2", "content2")
    imprint_store.activate_imprint("u1", 1, first.id)
    imprint_store.activate_imprint("u1", 1, second.id)

    rows = imprint_store.list_imprints("u1", 1)
    active = [row for row in rows if row.status == "active"]
    assert len(active) == 1
    assert active[0].id == second.id


def test_persona_activation_keeps_one_active_per_scope() -> None:
    Session = _setup_session()
    persona_store._set_session_factory(Session)

    first = persona_store.create_persona("u1", 1, "seed", "persona first")
    second = persona_store.create_persona("u1", 1, "seed", "persona second")
    persona_store.activate_persona("u1", 1, first.id)
    persona_store.activate_persona("u1", 1, second.id)

    rows = persona_store.list_personas("u1", 1)
    active = [row for row in rows if row.is_active]
    assert len(active) == 1
    assert active[0].id == second.id


def test_activation_is_project_scoped_no_cross_bleed() -> None:
    Session = _setup_session()
    imprint_store._set_session_factory(Session)
    persona_store._set_session_factory(Session)

    i1 = imprint_store.create_imprint("u1", 1, "P1", "imprint one")
    i2 = imprint_store.create_imprint("u1", 2, "P2", "imprint two")
    imprint_store.activate_imprint("u1", 1, i1.id)
    imprint_store.activate_imprint("u1", 2, i2.id)

    p1 = persona_store.create_persona("u1", 1, "user", "persona one")
    p2 = persona_store.create_persona("u1", 2, "user", "persona two")
    persona_store.activate_persona("u1", 1, p1.id)
    persona_store.activate_persona("u1", 2, p2.id)

    assert imprint_store.get_active_imprint("u1", 1).id == i1.id
    assert imprint_store.get_active_imprint("u1", 2).id == i2.id
    assert persona_store.get_active_persona("u1", 1).id == p1.id
    assert persona_store.get_active_persona("u1", 2).id == p2.id


def test_resolve_persona_precedence() -> None:
    Session = _setup_session()
    persona_store._set_session_factory(Session)

    candidate = persona_store.create_persona("u1", 3, "user", "active persona")
    persona_store.activate_persona("u1", 3, candidate.id)

    explicit = resolve_persona("u1", 3, requested_persona_id_or_name="override")
    assert explicit.source == "request_override"
    assert explicit.body == "override"

    active = resolve_persona("u1", 3, requested_persona_id_or_name=None)
    assert active.source == "active_scope"
    assert active.body == "active persona"

    fallback = resolve_persona(
        "u2",
        3,
        requested_persona_id_or_name=None,
        system_default_persona="system default persona",
    )
    assert fallback.source == "system_default"
    assert fallback.body == "system default persona"


def test_resolve_imprint_precedence_and_scope() -> None:
    Session = _setup_session()
    imprint_store._set_session_factory(Session)

    user_default = imprint_store.create_imprint("u1", None, "Default", "x")
    project_specific = imprint_store.create_imprint("u1", 9, "Project", "y")
    imprint_store.activate_imprint("u1", None, user_default.id)
    imprint_store.activate_imprint("u1", 9, project_specific.id)

    scoped = resolve_imprint("u1", 9)
    assert scoped.source == "active_scope"
    assert scoped.imprint_id == project_specific.id

    fallback_user = resolve_imprint("u1", 10)
    assert fallback_user.source == "user_default"
    assert fallback_user.imprint_id == user_default.id

    fallback_system = resolve_imprint(
        "u2",
        10,
        system_default_imprint={"guardian_name": "System"},
    )
    assert fallback_system.source == "system_default"
    assert fallback_system.guardian_name == "System"
