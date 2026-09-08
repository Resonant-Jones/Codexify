from __future__ import annotations

import inspect
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker

from guardian.core.persona_subjects import (
    PERSONA_PROFILE_REF_KIND,
    PERSONA_REF_KIND,
    PersonaSubjectResolutionError,
    ensure_persona_subject,
)
from guardian.db.models import (
    Base,
    Persona,
    PersonaProfile,
    PersonaProfileBinding,
    PersonaSubject,
    PersonaSubjectBinding,
    User,
)
from guardian.protocol_tokens import PersonaSubjectLifecycle

NOW = datetime(2026, 9, 7, tzinfo=timezone.utc)


def _as_utc(value: datetime) -> datetime:
    """Normalize SQLite's timezone-naive round trip for timestamp assertions."""

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


@pytest.fixture
def session() -> Session:
    engine = sa.create_engine("sqlite+pysqlite:///:memory:", future=True)
    sa.event.listen(
        engine,
        "connect",
        lambda connection, _: connection.execute("PRAGMA foreign_keys=ON"),
    )
    tables = [
        User.__table__,
        Persona.__table__,
        PersonaProfile.__table__,
        PersonaProfileBinding.__table__,
        PersonaSubject.__table__,
        PersonaSubjectBinding.__table__,
    ]
    Base.metadata.create_all(engine, tables=tables)
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    with factory() as db_session:
        try:
            yield db_session
        finally:
            db_session.rollback()
    engine.dispose()


def _add_user(session: Session, account_id: str) -> None:
    session.add(
        User(
            id=account_id,
            username=account_id,
            password_hash="not-a-real-hash",
            role="guest",
        )
    )
    session.flush()


def _add_persona(
    session: Session,
    account_id: str,
    *,
    body: str = "persona body",
    project_id: int | None = None,
    is_active: bool = True,
) -> Persona:
    persona = Persona(
        user_id=account_id,
        project_id=project_id,
        body=body,
        source="user",
        is_active=is_active,
        created_at=NOW,
        updated_at=NOW,
    )
    session.add(persona)
    session.flush()
    return persona


def _add_profile(
    session: Session,
    account_id: str,
    *,
    profile_id: str = "profile-a",
    name: str = "Persona Profile",
) -> PersonaProfile:
    profile = PersonaProfile(
        id=profile_id,
        name=name,
        system_prompt="prompt",
        model_provider="local",
        model_id="model",
        temperature=0.5,
        current_revision=1,
        created_at=NOW,
        updated_at=NOW,
    )
    binding = PersonaProfileBinding(
        profile_id=profile_id,
        owner_account_id=account_id,
        created_at=NOW + timedelta(seconds=1),
        updated_at=NOW + timedelta(seconds=1),
    )
    session.add_all((profile, binding))
    session.flush()
    return profile


def _add_closed_persona_binding(
    session: Session,
    persona: Persona,
    account_id: str,
) -> None:
    subject = PersonaSubject(
        persona_subject_id=str(uuid.uuid4()),
        user_id=account_id,
        lifecycle=PersonaSubjectLifecycle.ACTIVE.value,
    )
    session.add(subject)
    session.flush()
    session.add(
        PersonaSubjectBinding(
            binding_id=str(uuid.uuid4()),
            persona_subject_id=subject.persona_subject_id,
            subject_user_id=account_id,
            source_account_id=account_id,
            ref_kind=PERSONA_REF_KIND,
            ref_id=str(persona.id),
            valid_from=NOW,
            valid_until=NOW + timedelta(seconds=1),
        )
    )
    session.flush()


def test_persona_source_resolves_using_personas_user_id(session: Session) -> None:
    _add_user(session, "account-a")
    persona = _add_persona(session, "account-a")

    subject = ensure_persona_subject(
        session,
        "account-a",
        PERSONA_REF_KIND,
        str(persona.id),
    )

    binding = session.scalar(
        sa.select(PersonaSubjectBinding).where(
            PersonaSubjectBinding.persona_subject_id == subject.persona_subject_id
        )
    )
    assert subject.user_id == "account-a"
    assert subject.display_name_snapshot is None
    assert subject.lifecycle == PersonaSubjectLifecycle.ACTIVE.value
    assert binding is not None
    assert binding.source_account_id == "account-a"
    assert binding.subject_user_id == "account-a"
    assert binding.ref_kind == PERSONA_REF_KIND
    assert binding.ref_id == str(persona.id)
    assert _as_utc(binding.valid_from) == NOW


def test_profile_source_resolves_using_canonical_profile_binding(
    session: Session,
) -> None:
    _add_user(session, "account-a")
    profile = _add_profile(session, "account-a", name="Trusted profile name")

    subject = ensure_persona_subject(
        session,
        "account-a",
        PERSONA_PROFILE_REF_KIND,
        profile.id,
    )

    binding = session.scalar(
        sa.select(PersonaSubjectBinding).where(
            PersonaSubjectBinding.persona_subject_id == subject.persona_subject_id
        )
    )
    assert subject.user_id == "account-a"
    assert subject.display_name_snapshot == "Trusted profile name"
    assert binding is not None
    assert binding.ref_kind == PERSONA_PROFILE_REF_KIND
    assert binding.ref_id == profile.id
    assert _as_utc(binding.valid_from) == NOW + timedelta(seconds=1)


def test_authenticated_account_mismatch_fails_before_subject_creation(
    session: Session,
) -> None:
    _add_user(session, "account-a")
    _add_user(session, "account-b")
    persona = _add_persona(session, "account-a")

    with pytest.raises(PersonaSubjectResolutionError, match="does not own source"):
        ensure_persona_subject(
            session,
            "account-b",
            PERSONA_REF_KIND,
            str(persona.id),
        )

    assert session.scalar(sa.select(sa.func.count()).select_from(PersonaSubject)) == 0


def test_resolver_signature_does_not_accept_caller_owned_identity_fields() -> None:
    assert tuple(inspect.signature(ensure_persona_subject).parameters) == (
        "session",
        "authenticated_account_id",
        "ref_kind",
        "ref_id",
    )


def test_existing_active_binding_returns_same_subject_idempotently(
    session: Session,
) -> None:
    _add_user(session, "account-a")
    persona = _add_persona(session, "account-a")

    first = ensure_persona_subject(
        session, "account-a", PERSONA_REF_KIND, str(persona.id)
    )
    second = ensure_persona_subject(
        session, "account-a", PERSONA_REF_KIND, str(persona.id)
    )

    assert first.persona_subject_id == second.persona_subject_id
    assert session.scalar(sa.select(sa.func.count()).select_from(PersonaSubject)) == 1
    assert (
        session.scalar(sa.select(sa.func.count()).select_from(PersonaSubjectBinding))
        == 1
    )


def test_owned_source_without_subject_binding_receives_one_active_subject(
    session: Session,
) -> None:
    _add_user(session, "account-a")
    profile = _add_profile(session, "account-a")

    subject = ensure_persona_subject(
        session,
        "account-a",
        PERSONA_PROFILE_REF_KIND,
        profile.id,
    )

    assert subject.lifecycle == PersonaSubjectLifecycle.ACTIVE.value
    assert session.scalar(sa.select(sa.func.count()).select_from(PersonaSubject)) == 1


def test_closed_binding_without_continuity_evidence_fails_closed(
    session: Session,
) -> None:
    _add_user(session, "account-a")
    persona = _add_persona(session, "account-a")
    _add_closed_persona_binding(session, persona, "account-a")

    with pytest.raises(PersonaSubjectResolutionError, match="closed binding history"):
        ensure_persona_subject(
            session,
            "account-a",
            PERSONA_REF_KIND,
            str(persona.id),
        )


def test_invalid_ref_kind_fails_closed(session: Session) -> None:
    _add_user(session, "account-a")

    with pytest.raises(PersonaSubjectResolutionError, match="ref_kind"):
        ensure_persona_subject(session, "account-a", "thread_profile", "profile-a")


def test_project_scope_is_not_consulted_for_persona_identity(session: Session) -> None:
    _add_user(session, "account-a")
    persona = _add_persona(session, "account-a", project_id=987)

    subject = ensure_persona_subject(
        session,
        "account-a",
        PERSONA_REF_KIND,
        str(persona.id),
    )

    assert subject.user_id == "account-a"


def test_similar_persona_and_profile_content_never_coalesce(session: Session) -> None:
    _add_user(session, "account-a")
    persona = _add_persona(session, "account-a", body="same descriptive content")
    profile = _add_profile(
        session,
        "account-a",
        name="same descriptive content",
    )

    persona_subject = ensure_persona_subject(
        session,
        "account-a",
        PERSONA_REF_KIND,
        str(persona.id),
    )
    profile_subject = ensure_persona_subject(
        session,
        "account-a",
        PERSONA_PROFILE_REF_KIND,
        profile.id,
    )

    assert persona_subject.persona_subject_id != profile_subject.persona_subject_id
    assert session.scalar(sa.select(sa.func.count()).select_from(PersonaSubject)) == 2


def test_resolution_does_not_require_or_create_memory_tables(session: Session) -> None:
    _add_user(session, "account-a")
    persona = _add_persona(session, "account-a")

    ensure_persona_subject(session, "account-a", PERSONA_REF_KIND, str(persona.id))

    table_names = set(sa.inspect(session.get_bind()).get_table_names())
    assert "memory_entries" not in table_names
    assert "memory_persona_links" not in table_names
