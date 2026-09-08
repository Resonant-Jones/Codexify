"""Focused tests for the UMS-03E ``memory_entries`` and UMS-03F verified
``personal_facts`` compatibility projections.

UMS-03E proved:

* owned legacy memory-entry projects successfully;
* cross-account read fails closed (concealed like "not found");
* missing source row fails closed;
* semantic species is exactly the canonical ``episodic_semantic_memory``;
* legacy source family and source identifier survive projection;
* Project scope is never invented;
* Persona attribution is never invented (always zero links);
* governance posture is the frozen ambient-eligible default;
* provenance is preserved and does not confer ownership;
* the projection performs no canonical-table write;
* the projection performs no legacy-row mutation;
* the projection type is not an ORM model.

UMS-03F adds:

* verified + active fact projects successfully;
* exact canonical ``verified_personal_fact`` semantic species;
* candidate / disputed / archived / inactive rows do not project;
* cross-account reads fail closed;
* empty account id fails closed;
* primary (latest) evidence ``source_type`` / ``source_message_id``
  carried in provenance;
* multiple evidence rows remain distinct;
* revision rows preserved as historical lineage;
* no canonical-table write;
* no personal-fact / evidence / revision mutation;
* unknown evidence ``source_type`` fails closed;
* self-referential ``evidence_meta`` fails closed.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker

from guardian.core.memory_compatibility import (
    MEMORY_ENTRY_ENVELOPE_SPECIES,
    MEMORY_ENTRY_LEGACY_SOURCE_FAMILY,
    MEMORY_ENTRY_LEGACY_SOURCE_SYSTEM,
    PERSONAL_FACT_CANDIDATE_ENVELOPE_SPECIES,
    PERSONAL_FACT_LEGACY_SOURCE_FAMILY,
    PERSONAL_FACT_LEGACY_SOURCE_SYSTEM,
    PERSONAL_FACT_VERIFIED_ENVELOPE_SPECIES,
    MemoryCompatibilityReadError,
    MemoryCompatibilitySourceKind,
    MemoryCompatibilitySourceRef,
    read_candidate_personal_fact_projection,
    read_memory_compatibility_projection,
    read_memory_entry_projection,
    read_verified_personal_fact_projection,
)
from guardian.db.models import (
    Base,
    ChatMessage,
    MemoryEntry,
    PersonalFact,
    PersonalFactEvidence,
    PersonalFactRevision,
    Project,
    User,
)
from guardian.protocol_tokens import MemorySemanticSpecies, PersonalFactStatus


# Make JSONB renderable on SQLite so the legacy personal-fact
# tables (which declare ``guardrail_metadata`` and ``evidence_meta``
# as JSONB on PostgreSQL) can be materialized in the in-memory
# test database. On the real PostgreSQL runtime this hook is a
# no-op.
@compiles(JSONB, "sqlite")
def _compile_jsonb_for_sqlite(_type, _compiler, **_kwargs):
    return "JSON"


NOW = datetime(2026, 9, 7, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Fixtures.
# ---------------------------------------------------------------------------


@pytest.fixture
def session() -> Session:
    """In-memory SQLite session wired with only the tables this test needs.

    Includes the legacy ``memory_entries`` table (the projection source
    of truth) and the three canonical ``memory_records``,
    ``memory_persona_links``, ``memory_provenance`` tables so the
    no-canonical-write assertion can compare before/after row counts.
    Also includes ``users`` and ``projects`` because the canonical
    memory tables reference them. ``Base.metadata.create_all`` is run
    with exactly this subset; the compatibility projection type
    itself is intentionally NOT included in ``Base.metadata``.
    """

    engine = sa.create_engine("sqlite+pysqlite:///:memory:", future=True)
    # Foreign keys are intentionally NOT enforced in this test
    # because the compatibility projection's correctness is
    # independent of the ``personal_fact_evidence.source_message_id``
    # FK to ``chat_messages``. Enforcing FKs here would require
    # materializing a chain of upstream tables (chat_threads,
    # hosted_room_participants, ...) that are themselves outside
    # the projection's concern. The reader never relies on FK
    # enforcement; it preserves the legacy source identity
    # regardless.
    tables = [
        User.__table__,
        Project.__table__,
        MemoryEntry.__table__,
        PersonalFact.__table__,
        PersonalFactEvidence.__table__,
        PersonalFactRevision.__table__,
        ChatMessage.__table__,
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


def _add_memory_entry(
    session: Session,
    *,
    user_id: str,
    silo: str = "longterm",
    content: str | None = "remember this",
    tags: str | None = None,
    pinned: bool = False,
) -> MemoryEntry:
    # The MemoryEntry.id column is BigInteger autoincrement, which SQLite
    # cannot auto-populate without an INTEGER PRIMARY KEY declaration. The
    # legacy schema uses BigInteger globally for cross-DB stability, so
    # assign an explicit id to keep the test SQLite-portable without
    # altering the ORM model.
    next_id = (
        session.query(sa.func.coalesce(sa.func.max(MemoryEntry.id), 0)).scalar() or 0
    ) + 1
    entry = MemoryEntry(
        id=next_id,
        user_id=user_id,
        silo=silo,
        content=content,
        tags=tags,
        pinned=pinned,
        created_at=NOW,
        updated_at=NOW,
    )
    session.add(entry)
    session.flush()
    return entry


# ---------------------------------------------------------------------------
# UMS-03F personal-fact helpers.
# ---------------------------------------------------------------------------


def _add_personal_fact(
    session: Session,
    *,
    user_id: str,
    key: str = "favorite_color",
    value: str = "blue",
    status: str = PersonalFactStatus.VERIFIED.value,
    is_active: bool = True,
    confidence: float = 0.9,
    last_confirmed_at: datetime | None = NOW,
    guardrail_metadata: dict | None = None,
) -> PersonalFact:
    """Insert a legacy ``personal_facts`` row with an explicit id.

    Mirrors the SQLite-portable pattern used by ``_add_memory_entry``.
    """

    next_id = (
        session.query(sa.func.coalesce(sa.func.max(PersonalFact.id), 0)).scalar() or 0
    ) + 1
    fact = PersonalFact(
        id=next_id,
        user_id=user_id,
        key=key,
        value=value,
        status=status,
        confidence=confidence,
        is_active=is_active,
        last_confirmed_at=last_confirmed_at,
        guardrail_metadata=guardrail_metadata,
        created_at=NOW,
        updated_at=NOW,
    )
    session.add(fact)
    session.flush()
    return fact


def _add_evidence(
    session: Session,
    *,
    fact_id: int,
    source_type: str = "runtime_extraction",
    source_message_id: int | None = None,
    modality: str = "text",
    excerpt: str | None = None,
    evidence_meta: dict | None = None,
    created_at: datetime | None = None,
) -> PersonalFactEvidence:
    """Insert a ``personal_fact_evidence`` row for an existing fact."""

    next_id = (
        session.query(
            sa.func.coalesce(sa.func.max(PersonalFactEvidence.id), 0)
        ).scalar()
        or 0
    ) + 1
    row = PersonalFactEvidence(
        id=next_id,
        fact_id=fact_id,
        source_message_id=source_message_id,
        excerpt=excerpt,
        modality=modality,
        confidence=0.8,
        source_type=source_type,
        evidence_meta=evidence_meta if evidence_meta is not None else {},
        created_at=created_at or NOW,
    )
    session.add(row)
    session.flush()
    return row


def _add_revision(
    session: Session,
    *,
    fact_id: int,
    actor: str = "personal_facts_service",
    action: str = "verify",
    field_changed: str | None = "status",
    old_value: str | None = "candidate",
    new_value: str | None = "verified",
    reason: str | None = "user_approved",
    created_at: datetime | None = None,
) -> PersonalFactRevision:
    """Insert a ``personal_fact_revisions`` row for an existing fact."""

    next_id = (
        session.query(
            sa.func.coalesce(sa.func.max(PersonalFactRevision.id), 0)
        ).scalar()
        or 0
    ) + 1
    row = PersonalFactRevision(
        id=next_id,
        fact_id=fact_id,
        actor=actor,
        action=action,
        field_changed=field_changed,
        old_value=old_value,
        new_value=new_value,
        reason=reason,
        created_at=created_at or NOW,
    )
    session.add(row)
    session.flush()
    return row


def _add_chat_message(session: Session, *, message_id: int) -> None:
    """Insert a minimal ``chat_messages`` row at a fixed id.

    ``personal_fact_evidence.source_message_id`` is a foreign key to
    ``chat_messages.id``. To prove that the compatibility reader
    preserves a non-null ``source_message_id``, the test must
    materialize the referenced chat-message row. This helper builds
    a minimal row with only the required NOT NULL fields populated;
    other fields take the table defaults.
    """

    session.execute(
        sa.insert(ChatMessage).values(
            id=message_id,
            thread_id=1,
            user_id="account-A",
            role="user",
            content="test",
            extra_meta={},
            event_at=NOW,
            kind="text",
        )
    )
    session.flush()


# ---------------------------------------------------------------------------
# 1. Owned legacy memory-entry projects successfully.
# ---------------------------------------------------------------------------


def test_owned_memory_entry_projects_successfully(session: Session) -> None:
    _add_user(session, "account-A")
    entry = _add_memory_entry(
        session,
        user_id="account-A",
        silo="longterm",
        content="remember the trip to Lisbon",
        tags="travel,2026",
        pinned=True,
    )

    projection = read_memory_entry_projection(
        session,
        authenticated_account_id="account-A",
        memory_entry_id=entry.id,
    )

    assert projection is not None

    # Compatibility lineage is preserved.
    assert projection.legacy_source_family == MEMORY_ENTRY_LEGACY_SOURCE_FAMILY
    assert (
        projection.legacy_source_record_id
        == f"{MEMORY_ENTRY_LEGACY_SOURCE_FAMILY}:{entry.id}"
    )

    # Ownership.
    assert projection.account_user_id == "account-A"

    # Species and content.
    assert projection.semantic_species == MEMORY_ENTRY_ENVELOPE_SPECIES
    assert (
        projection.semantic_species
        == MemorySemanticSpecies.EPISODIC_SEMANTIC_MEMORY.value
    )
    assert projection.content == "remember the trip to Lisbon"

    # Retention class and priority / decay control.
    assert projection.retention_class == "longterm"
    assert projection.tags == "travel,2026"
    assert projection.pinned is True

    # Lifecycle.
    assert projection.created_at == NOW
    assert projection.updated_at == NOW

    # Project scope is absent (account scope only).
    assert projection.project_id is None

    # Persona attribution is zero links.
    assert projection.persona_links == []

    # Governance posture matches the frozen mapping.
    assert projection.ambient_eligible is True

    # Provenance is preserved and does not confer ownership.
    assert projection.provenance is not None
    assert projection.provenance.source_system == MEMORY_ENTRY_LEGACY_SOURCE_SYSTEM
    assert (
        projection.provenance.source_record_id
        == f"{MEMORY_ENTRY_LEGACY_SOURCE_FAMILY}:{entry.id}"
    )
    assert projection.provenance.source_thread_id is None
    assert projection.provenance.source_message_id is None


# ---------------------------------------------------------------------------
# 2. Cross-account read fails closed (concealed like "not found").
# ---------------------------------------------------------------------------


def test_cross_account_read_returns_none(session: Session) -> None:
    _add_user(session, "account-A")
    _add_user(session, "account-B")
    entry = _add_memory_entry(session, user_id="account-A", content="private memory")

    projection = read_memory_entry_projection(
        session,
        authenticated_account_id="account-B",
        memory_entry_id=entry.id,
    )

    assert projection is None


# ---------------------------------------------------------------------------
# 3. Missing source row returns None (not a fail-closed exception).
# ---------------------------------------------------------------------------


def test_missing_source_returns_none(session: Session) -> None:
    _add_user(session, "account-A")

    projection = read_memory_entry_projection(
        session,
        authenticated_account_id="account-A",
        memory_entry_id=999_999,
    )

    assert projection is None


# ---------------------------------------------------------------------------
# 4. Account-id is required; empty account fails closed.
# ---------------------------------------------------------------------------


def test_empty_authenticated_account_fails_closed(session: Session) -> None:
    _add_user(session, "account-A")
    entry = _add_memory_entry(session, user_id="account-A")

    with pytest.raises(MemoryCompatibilityReadError):
        read_memory_entry_projection(
            session,
            authenticated_account_id="",
            memory_entry_id=entry.id,
        )


# ---------------------------------------------------------------------------
# 5. The projection does not invent Project scope.
# ---------------------------------------------------------------------------


def test_projection_does_not_invent_project_scope(session: Session) -> None:
    _add_user(session, "account-A")
    entry = _add_memory_entry(session, user_id="account-A")

    projection = read_memory_entry_projection(
        session,
        authenticated_account_id="account-A",
        memory_entry_id=entry.id,
    )

    assert projection is not None
    assert projection.project_id is None


# ---------------------------------------------------------------------------
# 6. The projection does not invent Persona attribution.
# ---------------------------------------------------------------------------


def test_projection_has_zero_persona_links(session: Session) -> None:
    _add_user(session, "account-A")
    entry = _add_memory_entry(session, user_id="account-A")

    projection = read_memory_entry_projection(
        session,
        authenticated_account_id="account-A",
        memory_entry_id=entry.id,
    )

    assert projection is not None
    assert projection.persona_links == []


# ---------------------------------------------------------------------------
# 7. The projection does not fabricate a canonical memory_id.
# ---------------------------------------------------------------------------


def test_projection_has_no_canonical_memory_id(session: Session) -> None:
    _add_user(session, "account-A")
    entry = _add_memory_entry(session, user_id="account-A")

    projection = read_memory_entry_projection(
        session,
        authenticated_account_id="account-A",
        memory_entry_id=entry.id,
    )

    assert projection is not None
    # The projection type deliberately exposes no ``memory_id`` field;
    # the legacy source identity is the lineage. Verify by name.
    assert "memory_id" not in projection.__dataclass_fields__
    assert "canonical_memory_id" not in projection.__dataclass_fields__


# ---------------------------------------------------------------------------
# 8. No canonical-table write occurs.
# ---------------------------------------------------------------------------


_CANONICAL_TABLES: tuple[str, ...] = (
    "memory_records",
    "memory_persona_links",
    "memory_provenance",
)


def test_compatibility_read_writes_no_canonical_rows(
    session: Session,
) -> None:
    """The compatibility reader must not INSERT/UPDATE/DELETE canonical rows.

    The canonical tables are PostgreSQL-typed (JSONB, UUID, etc.) and
    cannot be materialized in this SQLite-backed test. The no-write
    contract is therefore proven at the SQL-event layer: every
    statement the session executes during a read is captured, and we
    assert no DML was issued against any canonical-memory table.
    """

    _add_user(session, "account-A")
    entry = _add_memory_entry(session, user_id="account-A")

    bind = session.get_bind()
    engine = bind.engine if hasattr(bind, "engine") else bind
    statements: list[str] = []

    def _capture(_conn, _cursor, statement, _params, _context, _executemany):
        statements.append(statement)

    sa.event.listen(engine, "before_cursor_execute", _capture)
    try:
        projection = read_memory_entry_projection(
            session,
            authenticated_account_id="account-A",
            memory_entry_id=entry.id,
        )
    finally:
        sa.event.remove(engine, "before_cursor_execute", _capture)

    assert projection is not None

    write_keywords = ("INSERT", "UPDATE", "DELETE", "TRUNCATE", "MERGE")
    canonical_violations = [
        s
        for s in statements
        if any(kw in s.upper() for kw in write_keywords)
        and any(table in s for table in _CANONICAL_TABLES)
    ]
    assert canonical_violations == [], (
        "compatibility read must not write to canonical tables; saw: "
        f"{canonical_violations}"
    )


# ---------------------------------------------------------------------------
# 9. No legacy-row mutation occurs.
# ---------------------------------------------------------------------------


def test_compatibility_read_does_not_mutate_legacy_row(session: Session) -> None:
    _add_user(session, "account-A")
    entry = _add_memory_entry(
        session,
        user_id="account-A",
        content="before read",
        tags="tag-1",
        pinned=False,
    )
    before = {
        "id": entry.id,
        "user_id": entry.user_id,
        "silo": entry.silo,
        "content": entry.content,
        "tags": entry.tags,
        "pinned": entry.pinned,
    }

    read_memory_entry_projection(
        session,
        authenticated_account_id="account-A",
        memory_entry_id=entry.id,
    )

    session.expire_all()
    fresh = session.get(MemoryEntry, entry.id)
    assert fresh is not None
    after = {
        "id": fresh.id,
        "user_id": fresh.user_id,
        "silo": fresh.silo,
        "content": fresh.content,
        "tags": fresh.tags,
        "pinned": fresh.pinned,
    }
    assert before == after


# ---------------------------------------------------------------------------
# 10. The projection type is not an ORM model.
# ---------------------------------------------------------------------------


def test_projection_type_is_not_registered_in_orm_metadata() -> None:
    table_names = {table.name for table in Base.metadata.tables.values()}
    assert "memory_compatibility_projection" not in table_names
    assert "memory_compatibility_provenance" not in table_names
    assert "memory_compatibility_persona_links" not in table_names
    assert "memory_entries_projection" not in table_names


# ---------------------------------------------------------------------------
# 11. All three retention silos project successfully.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("silo", ["ephemeral", "midterm", "longterm"])
def test_all_valid_silos_project(session: Session, silo: str) -> None:
    _add_user(session, "account-A")
    entry = _add_memory_entry(
        session, user_id="account-A", silo=silo, content=f"silo={silo}"
    )

    projection = read_memory_entry_projection(
        session,
        authenticated_account_id="account-A",
        memory_entry_id=entry.id,
    )

    assert projection is not None
    assert projection.retention_class == silo


# ---------------------------------------------------------------------------
# 12. Null content is representable (the source can have null content).
# ---------------------------------------------------------------------------


def test_null_content_projects_as_none(session: Session) -> None:
    _add_user(session, "account-A")
    entry = _add_memory_entry(session, user_id="account-A", content=None)

    projection = read_memory_entry_projection(
        session,
        authenticated_account_id="account-A",
        memory_entry_id=entry.id,
    )

    assert projection is not None
    assert projection.content is None


# ---------------------------------------------------------------------------
# 13. Provenance does not confer ownership.
# ---------------------------------------------------------------------------


def test_provenance_carries_source_identity_only(session: Session) -> None:
    _add_user(session, "account-A")
    entry = _add_memory_entry(session, user_id="account-A")

    projection = read_memory_entry_projection(
        session,
        authenticated_account_id="account-A",
        memory_entry_id=entry.id,
    )

    assert projection is not None
    assert projection.provenance is not None
    # Provenance is a read projection, not a memory_provenance row.
    assert "memory_provenance" not in projection.provenance.__dataclass_fields__
    # account_user_id remains the only ownership field; provenance
    # carries no user/Persona/Project information.
    assert projection.provenance.source_system == "codexify"
    assert projection.provenance.source_record_id == (
        f"{MEMORY_ENTRY_LEGACY_SOURCE_FAMILY}:{entry.id}"
    )
    # Confirm the projection still does not carry a Project or Persona
    # identity in the provenance payload.
    assert projection.provenance.source_thread_id is None
    assert projection.provenance.source_message_id is None
    assert projection.project_id is None
    assert projection.persona_links == []


# ===========================================================================
# UMS-03F — Verified personal-fact compatibility projection.
# ===========================================================================


# ---------------------------------------------------------------------------
# 16. Verified + active personal fact projects successfully.
# ---------------------------------------------------------------------------


def test_verified_active_fact_projects_successfully(session: Session) -> None:
    _add_user(session, "account-A")
    _add_chat_message(session, message_id=101)
    fact = _add_personal_fact(
        session,
        user_id="account-A",
        key="favorite_color",
        value="blue",
        status=PersonalFactStatus.VERIFIED.value,
        is_active=True,
        confidence=0.92,
        last_confirmed_at=NOW,
        guardrail_metadata={"source": "user_stated", "review": "approved"},
    )
    _add_evidence(
        session,
        fact_id=fact.id,
        source_type="user_stated",
        source_message_id=None,
        modality="text",
        excerpt="the user said their favorite color is blue",
        evidence_meta={"channel": "explicit", "excerpt_ref": "msg-1"},
    )

    projection = read_verified_personal_fact_projection(
        session,
        authenticated_account_id="account-A",
        personal_fact_id=fact.id,
    )

    assert projection is not None

    # Compatibility lineage.
    assert projection.legacy_source_family == PERSONAL_FACT_LEGACY_SOURCE_FAMILY
    assert (
        projection.legacy_source_record_id
        == f"{PERSONAL_FACT_LEGACY_SOURCE_FAMILY}:{fact.id}"
    )

    # Ownership.
    assert projection.account_user_id == "account-A"

    # Semantic species is exact.
    assert projection.semantic_species == PERSONAL_FACT_VERIFIED_ENVELOPE_SPECIES
    assert (
        projection.semantic_species
        == MemorySemanticSpecies.VERIFIED_PERSONAL_FACT.value
    )

    # Fact payload.
    assert projection.fact_key == "favorite_color"
    assert projection.fact_value == "blue"
    assert projection.confidence == pytest.approx(0.92)
    assert projection.last_confirmed_at == NOW
    assert projection.guardrail_metadata == {
        "source": "user_stated",
        "review": "approved",
    }

    # Memory-entries shape is None.
    assert projection.content is None
    assert projection.retention_class is None
    assert projection.tags is None
    assert projection.pinned is False

    # Lifecycle.
    assert projection.created_at == NOW
    assert projection.updated_at == NOW

    # Project + Persona posture.
    assert projection.project_id is None
    assert projection.persona_links == []

    # Provenance carries primary evidence.
    assert projection.provenance is not None
    assert projection.provenance.source_system == PERSONAL_FACT_LEGACY_SOURCE_SYSTEM
    assert (
        projection.provenance.source_record_id
        == f"{PERSONAL_FACT_LEGACY_SOURCE_FAMILY}:{fact.id}"
    )
    assert projection.provenance.source_type == "user_stated"
    assert projection.provenance.modality == "text"
    assert projection.provenance.excerpt == (
        "the user said their favorite color is blue"
    )
    assert projection.provenance.evidence_meta == {
        "channel": "explicit",
        "excerpt_ref": "msg-1",
    }
    assert projection.provenance.source_message_id is None
    assert projection.provenance.source_thread_id is None

    # Evidence list is preserved (one row here).
    assert len(projection.evidence) == 1
    only_evidence = projection.evidence[0]
    assert only_evidence.source_type == "user_stated"
    assert only_evidence.modality == "text"
    assert only_evidence.evidence_id is not None
    # SQLite drops tzinfo on round-trip; normalize for the assertion.
    assert only_evidence.created_at == NOW.replace(tzinfo=None) or (
        only_evidence.created_at.replace(tzinfo=timezone.utc) == NOW
    )

    # Governance posture is the approved/active default.
    assert projection.ambient_eligible is True


# ---------------------------------------------------------------------------
# 17. Cross-account read returns None.
# ---------------------------------------------------------------------------


def test_verified_fact_cross_account_returns_none(session: Session) -> None:
    _add_user(session, "account-A")
    _add_user(session, "account-B")
    fact = _add_personal_fact(session, user_id="account-A")

    projection = read_verified_personal_fact_projection(
        session,
        authenticated_account_id="account-B",
        personal_fact_id=fact.id,
    )

    assert projection is None


# ---------------------------------------------------------------------------
# 18. Missing fact returns None.
# ---------------------------------------------------------------------------


def test_verified_fact_missing_returns_none(session: Session) -> None:
    _add_user(session, "account-A")

    projection = read_verified_personal_fact_projection(
        session,
        authenticated_account_id="account-A",
        personal_fact_id=999_999,
    )

    assert projection is None


# ---------------------------------------------------------------------------
# 19. Empty account id fails closed.
# ---------------------------------------------------------------------------


def test_verified_fact_empty_account_fails_closed(session: Session) -> None:
    _add_user(session, "account-A")
    fact = _add_personal_fact(session, user_id="account-A")

    with pytest.raises(MemoryCompatibilityReadError):
        read_verified_personal_fact_projection(
            session,
            authenticated_account_id="",
            personal_fact_id=fact.id,
        )


# ---------------------------------------------------------------------------
# 20. Candidate fact does not project as verified.
# ---------------------------------------------------------------------------


def test_candidate_fact_does_not_project(session: Session) -> None:
    _add_user(session, "account-A")
    fact = _add_personal_fact(
        session,
        user_id="account-A",
        status=PersonalFactStatus.CANDIDATE.value,
        is_active=True,
    )

    projection = read_verified_personal_fact_projection(
        session,
        authenticated_account_id="account-A",
        personal_fact_id=fact.id,
    )

    assert projection is None


# ---------------------------------------------------------------------------
# 21. Disputed fact does not project.
# ---------------------------------------------------------------------------


def test_disputed_fact_does_not_project(session: Session) -> None:
    _add_user(session, "account-A")
    fact = _add_personal_fact(
        session,
        user_id="account-A",
        status=PersonalFactStatus.DISPUTED.value,
        is_active=True,
    )

    projection = read_verified_personal_fact_projection(
        session,
        authenticated_account_id="account-A",
        personal_fact_id=fact.id,
    )

    assert projection is None


# ---------------------------------------------------------------------------
# 22. Archived (superseded) fact does not project.
# ---------------------------------------------------------------------------


def test_archived_fact_does_not_project(session: Session) -> None:
    _add_user(session, "account-A")
    fact = _add_personal_fact(
        session,
        user_id="account-A",
        status=PersonalFactStatus.ARCHIVED.value,
        is_active=True,
    )

    projection = read_verified_personal_fact_projection(
        session,
        authenticated_account_id="account-A",
        personal_fact_id=fact.id,
    )

    assert projection is None


# ---------------------------------------------------------------------------
# 23. Inactive verified fact does not project.
# ---------------------------------------------------------------------------


def test_inactive_verified_fact_does_not_project(session: Session) -> None:
    _add_user(session, "account-A")
    fact = _add_personal_fact(
        session,
        user_id="account-A",
        status=PersonalFactStatus.VERIFIED.value,
        is_active=False,
    )

    projection = read_verified_personal_fact_projection(
        session,
        authenticated_account_id="account-A",
        personal_fact_id=fact.id,
    )

    assert projection is None


# ---------------------------------------------------------------------------
# 24. Multiple evidence rows remain distinct; primary is the latest.
# ---------------------------------------------------------------------------


def test_multiple_evidence_rows_remain_distinct(session: Session) -> None:
    _add_user(session, "account-A")
    fact = _add_personal_fact(session, user_id="account-A")
    _add_evidence(
        session,
        fact_id=fact.id,
        source_type="runtime_extraction",
        excerpt="first",
        created_at=NOW - timedelta(days=2),
    )
    _add_evidence(
        session,
        fact_id=fact.id,
        source_type="user_corrected",
        excerpt="second",
        created_at=NOW - timedelta(days=1),
    )
    _add_evidence(
        session,
        fact_id=fact.id,
        source_type="user_stated",
        excerpt="third (latest)",
        created_at=NOW,
    )

    projection = read_verified_personal_fact_projection(
        session,
        authenticated_account_id="account-A",
        personal_fact_id=fact.id,
    )

    assert projection is not None
    assert len(projection.evidence) == 3
    # All rows are distinct; no deduplication by source_type.
    source_types = [ev.source_type for ev in projection.evidence]
    assert sorted(source_types) == sorted(
        {"runtime_extraction", "user_corrected", "user_stated"}
    )
    # Primary evidence is the latest, by created_at DESC.
    assert projection.provenance is not None
    assert projection.provenance.source_type == "user_stated"
    assert projection.provenance.excerpt == "third (latest)"


# ---------------------------------------------------------------------------
# 25. Revisions are preserved as historical lineage.
# ---------------------------------------------------------------------------


def test_revisions_preserved_as_historical_lineage(session: Session) -> None:
    _add_user(session, "account-A")
    fact = _add_personal_fact(session, user_id="account-A")
    _add_revision(
        session,
        fact_id=fact.id,
        action="create",
        field_changed=None,
        old_value=None,
        new_value="candidate",
        created_at=NOW - timedelta(days=3),
    )
    _add_revision(
        session,
        fact_id=fact.id,
        action="verify",
        field_changed="status",
        old_value="candidate",
        new_value="verified",
        created_at=NOW,
    )

    projection = read_verified_personal_fact_projection(
        session,
        authenticated_account_id="account-A",
        personal_fact_id=fact.id,
    )

    assert projection is not None
    # Two revisions preserved; the current fact remains the authority.
    assert len(projection.revisions) == 2
    actions = [r.action for r in projection.revisions]
    assert actions == ["create", "verify"]
    # The current fact payload is unchanged by revision history.
    assert projection.fact_key == "favorite_color"
    assert projection.fact_value == "blue"


# ---------------------------------------------------------------------------
# 26. Unknown evidence source_type fails closed.
# ---------------------------------------------------------------------------


def test_unknown_evidence_source_type_fails_closed(session: Session) -> None:
    _add_user(session, "account-A")
    fact = _add_personal_fact(session, user_id="account-A")
    _add_evidence(session, fact_id=fact.id, source_type="not_in_vocabulary")

    with pytest.raises(MemoryCompatibilityReadError):
        read_verified_personal_fact_projection(
            session,
            authenticated_account_id="account-A",
            personal_fact_id=fact.id,
        )


# ---------------------------------------------------------------------------
# 27. Self-referential evidence_meta fails closed.
# ---------------------------------------------------------------------------


def test_self_referential_evidence_meta_fails_closed(session: Session) -> None:
    _add_user(session, "account-A")
    fact = _add_personal_fact(session, user_id="account-A")
    _add_evidence(
        session,
        fact_id=fact.id,
        evidence_meta={"references_fact": fact.id},
    )

    with pytest.raises(MemoryCompatibilityReadError):
        read_verified_personal_fact_projection(
            session,
            authenticated_account_id="account-A",
            personal_fact_id=fact.id,
        )


# ---------------------------------------------------------------------------
# 28. Verified + active fact with no evidence still projects.
# ---------------------------------------------------------------------------


def test_verified_fact_without_evidence_still_projects(session: Session) -> None:
    _add_user(session, "account-A")
    fact = _add_personal_fact(session, user_id="account-A")

    projection = read_verified_personal_fact_projection(
        session,
        authenticated_account_id="account-A",
        personal_fact_id=fact.id,
    )

    assert projection is not None
    assert projection.evidence == []
    assert projection.provenance is not None
    assert projection.provenance.source_type is None
    assert projection.provenance.evidence_meta is None
    # Source lineage still preserved.
    assert (
        projection.provenance.source_record_id
        == f"{PERSONAL_FACT_LEGACY_SOURCE_FAMILY}:{fact.id}"
    )


# ---------------------------------------------------------------------------
# 29. No canonical-table write occurs.
# ---------------------------------------------------------------------------


_CANONICAL_TABLES_F: tuple[str, ...] = (
    "memory_records",
    "memory_persona_links",
    "memory_provenance",
)

_PERSONAL_FACT_TABLES_F: tuple[str, ...] = (
    "personal_facts",
    "personal_fact_evidence",
    "personal_fact_revisions",
)


def test_verified_fact_read_writes_nothing(session: Session) -> None:
    """A compatibility read must not write to canonical or personal-fact tables.

    The canonical tables are PostgreSQL-typed (JSONB, UUID, etc.) and
    cannot be materialized in this SQLite-backed test. The no-write
    contract is proven at the SQL-event layer: every statement the
    session executes during a read is captured, and we assert no DML
    was issued against any canonical-memory or personal-fact table.
    """

    _add_user(session, "account-A")
    _add_chat_message(session, message_id=102)
    fact = _add_personal_fact(session, user_id="account-A")
    _add_evidence(session, fact_id=fact.id, source_type="user_stated")
    _add_revision(session, fact_id=fact.id)

    bind = session.get_bind()
    engine = bind.engine if hasattr(bind, "engine") else bind
    statements: list[str] = []

    def _capture(_conn, _cursor, statement, _params, _context, _executemany):
        statements.append(statement)

    sa.event.listen(engine, "before_cursor_execute", _capture)
    try:
        projection = read_verified_personal_fact_projection(
            session,
            authenticated_account_id="account-A",
            personal_fact_id=fact.id,
        )
    finally:
        sa.event.remove(engine, "before_cursor_execute", _capture)

    assert projection is not None

    import re

    # Match write keywords only at statement start, not as
    # substrings of column names like ``updated_at``.
    write_pattern = re.compile(
        r"^\s*(INSERT|UPDATE|DELETE|TRUNCATE|MERGE)\b",
        re.IGNORECASE,
    )
    protected = _CANONICAL_TABLES_F + _PERSONAL_FACT_TABLES_F
    violations = [
        s
        for s in statements
        if write_pattern.match(s) and any(table in s for table in protected)
    ]
    assert violations == [], (
        "compatibility read must not write to canonical or "
        f"personal-fact tables; saw: {violations}"
    )


# ---------------------------------------------------------------------------
# 30. No legacy mutation occurs on personal_facts / evidence / revisions.
# ---------------------------------------------------------------------------


def test_verified_fact_read_does_not_mutate_legacy_rows(session: Session) -> None:
    _add_user(session, "account-A")
    fact = _add_personal_fact(
        session,
        user_id="account-A",
        key="favorite_color",
        value="blue",
        guardrail_metadata={"source": "user_stated"},
    )
    evidence = _add_evidence(
        session, fact_id=fact.id, source_type="user_stated", excerpt="blue"
    )
    revision = _add_revision(session, fact_id=fact.id)

    def _snapshot_fact(fid: int) -> dict:
        f = session.get(PersonalFact, fid)
        return {
            "id": f.id,
            "user_id": f.user_id,
            "key": f.key,
            "value": f.value,
            "status": f.status,
            "is_active": f.is_active,
            "confidence": f.confidence,
            "guardrail_metadata": (
                dict(f.guardrail_metadata) if f.guardrail_metadata is not None else None
            ),
        }

    def _snapshot_evidence(eid: int) -> dict:
        e = session.get(PersonalFactEvidence, eid)
        return {
            "id": e.id,
            "source_type": e.source_type,
            "excerpt": e.excerpt,
            "evidence_meta": dict(e.evidence_meta),
        }

    def _snapshot_revision(rid: int) -> dict:
        r = session.get(PersonalFactRevision, rid)
        return {
            "id": r.id,
            "actor": r.actor,
            "action": r.action,
            "old_value": r.old_value,
            "new_value": r.new_value,
        }

    before_fact = _snapshot_fact(fact.id)
    before_evidence = _snapshot_evidence(evidence.id)
    before_revision = _snapshot_revision(revision.id)

    read_verified_personal_fact_projection(
        session,
        authenticated_account_id="account-A",
        personal_fact_id=fact.id,
    )

    session.expire_all()
    after_fact = _snapshot_fact(fact.id)
    after_evidence = _snapshot_evidence(evidence.id)
    after_revision = _snapshot_revision(revision.id)

    assert before_fact == after_fact
    assert before_evidence == after_evidence
    assert before_revision == after_revision


# ---------------------------------------------------------------------------
# 31. No fabricated canonical memory_id on a verified fact.
# ---------------------------------------------------------------------------


def test_verified_fact_has_no_canonical_memory_id(session: Session) -> None:
    _add_user(session, "account-A")
    fact = _add_personal_fact(session, user_id="account-A")

    projection = read_verified_personal_fact_projection(
        session,
        authenticated_account_id="account-A",
        personal_fact_id=fact.id,
    )

    assert projection is not None
    assert "memory_id" not in projection.__dataclass_fields__
    assert "canonical_memory_id" not in projection.__dataclass_fields__


# ---------------------------------------------------------------------------
# 32. Verified + active fact with source_message_id preserves it.
# ---------------------------------------------------------------------------


def test_primary_evidence_source_message_id_preserved(session: Session) -> None:
    _add_user(session, "account-A")
    _add_chat_message(session, message_id=42)
    fact = _add_personal_fact(session, user_id="account-A")
    _add_evidence(
        session,
        fact_id=fact.id,
        source_type="runtime_extraction",
        source_message_id=42,
        excerpt="from chat",
        created_at=NOW,
    )

    projection = read_verified_personal_fact_projection(
        session,
        authenticated_account_id="account-A",
        personal_fact_id=fact.id,
    )

    assert projection is not None
    assert projection.provenance is not None
    assert projection.provenance.source_type == "runtime_extraction"
    assert projection.provenance.source_message_id == "42"
    assert projection.evidence[0].source_message_id == 42


# ---------------------------------------------------------------------------
# 33. Verified + active fact does not invent Project or Persona.
# ---------------------------------------------------------------------------


def test_verified_fact_does_not_invent_project_or_persona(session: Session) -> None:
    _add_user(session, "account-A")
    fact = _add_personal_fact(session, user_id="account-A")

    projection = read_verified_personal_fact_projection(
        session,
        authenticated_account_id="account-A",
        personal_fact_id=fact.id,
    )

    assert projection is not None
    assert projection.project_id is None
    assert projection.persona_links == []


# ---------------------------------------------------------------------------
# 34. Exact semantic species is verified_personal_fact.
# ---------------------------------------------------------------------------


def test_verified_fact_species_is_exact_token(session: Session) -> None:
    _add_user(session, "account-A")
    fact = _add_personal_fact(session, user_id="account-A")

    projection = read_verified_personal_fact_projection(
        session,
        authenticated_account_id="account-A",
        personal_fact_id=fact.id,
    )

    assert projection is not None
    assert projection.semantic_species == "verified_personal_fact"
    assert projection.semantic_species == PERSONAL_FACT_VERIFIED_ENVELOPE_SPECIES
    # The species must NOT be the memory_entries species.
    assert projection.semantic_species != MEMORY_ENTRY_ENVELOPE_SPECIES


# ===========================================================================
# UMS-03G — Candidate / unreviewed personal-fact compatibility projection.
# ===========================================================================


# ---------------------------------------------------------------------------
# 35. Owned candidate fact projects successfully.
# ---------------------------------------------------------------------------


def test_candidate_active_fact_projects_successfully(session: Session) -> None:
    _add_user(session, "account-A")
    fact = _add_personal_fact(
        session,
        user_id="account-A",
        key="favorite_food",
        value="ramen",
        status=PersonalFactStatus.CANDIDATE.value,
        is_active=True,
        confidence=0.6,
    )
    _add_evidence(
        session,
        fact_id=fact.id,
        source_type="runtime_extraction",
        excerpt="user mentioned ramen",
    )

    projection = read_candidate_personal_fact_projection(
        session,
        authenticated_account_id="account-A",
        personal_fact_id=fact.id,
    )

    assert projection is not None

    # Lineage.
    assert projection.legacy_source_family == PERSONAL_FACT_LEGACY_SOURCE_FAMILY
    assert (
        projection.legacy_source_record_id
        == f"{PERSONAL_FACT_LEGACY_SOURCE_FAMILY}:{fact.id}"
    )

    # Ownership.
    assert projection.account_user_id == "account-A"

    # Species is exact and is the candidate species (not verified, not memory).
    assert projection.semantic_species == PERSONAL_FACT_CANDIDATE_ENVELOPE_SPECIES
    assert projection.semantic_species == "candidate_unreviewed_fact"
    assert projection.semantic_species != PERSONAL_FACT_VERIFIED_ENVELOPE_SPECIES
    assert projection.semantic_species != MEMORY_ENTRY_ENVELOPE_SPECIES

    # Review posture is pending / unapproved; species carries this.
    # Active candidate remains unapproved even though is_active=true.
    assert projection.ambient_eligible is False

    # Fact payload preserved exactly.
    assert projection.fact_key == "favorite_food"
    assert projection.fact_value == "ramen"
    assert projection.confidence == pytest.approx(0.6)

    # Project + Persona posture: never inferred.
    assert projection.project_id is None
    assert projection.persona_links == []

    # Evidence preserved.
    assert len(projection.evidence) == 1
    assert projection.evidence[0].source_type == "runtime_extraction"

    # Memory-entries shape remains None.
    assert projection.content is None
    assert projection.retention_class is None
    assert projection.tags is None
    assert projection.pinned is False


# ---------------------------------------------------------------------------
# 36. Candidate + inactive is also a valid candidate-state combination.
# ---------------------------------------------------------------------------


def test_candidate_inactive_fact_projects(session: Session) -> None:
    _add_user(session, "account-A")
    fact = _add_personal_fact(
        session,
        user_id="account-A",
        key="favorite_food",
        value="ramen",
        status=PersonalFactStatus.CANDIDATE.value,
        is_active=False,
    )

    projection = read_candidate_personal_fact_projection(
        session,
        authenticated_account_id="account-A",
        personal_fact_id=fact.id,
    )

    assert projection is not None
    assert projection.semantic_species == "candidate_unreviewed_fact"
    # Inactive candidate is still not approved / not ambient-eligible.
    assert projection.ambient_eligible is False


# ---------------------------------------------------------------------------
# 37. Active candidate does NOT become approved.
# ---------------------------------------------------------------------------


def test_active_candidate_does_not_become_approved(session: Session) -> None:
    _add_user(session, "account-A")
    fact = _add_personal_fact(
        session,
        user_id="account-A",
        status=PersonalFactStatus.CANDIDATE.value,
        is_active=True,
    )

    projection = read_candidate_personal_fact_projection(
        session,
        authenticated_account_id="account-A",
        personal_fact_id=fact.id,
    )

    assert projection is not None
    # Ambient eligibility is the canonical "is approved" surface; the
    # species is the canonical "what is the review posture" surface.
    # An active candidate must report neither.
    assert projection.ambient_eligible is False
    assert projection.semantic_species == "candidate_unreviewed_fact"
    # And it must NOT be the verified species.
    assert projection.semantic_species != "verified_personal_fact"


# ---------------------------------------------------------------------------
# 38. Verified + active fact does NOT pass the candidate reader.
# ---------------------------------------------------------------------------


def test_verified_active_fact_excluded_from_candidate_reader(
    session: Session,
) -> None:
    _add_user(session, "account-A")
    fact = _add_personal_fact(
        session,
        user_id="account-A",
        status=PersonalFactStatus.VERIFIED.value,
        is_active=True,
    )

    projection = read_candidate_personal_fact_projection(
        session,
        authenticated_account_id="account-A",
        personal_fact_id=fact.id,
    )

    # UMS-03F owns verified + active projection; candidate reader
    # returns None for those rows.
    assert projection is None


# ---------------------------------------------------------------------------
# 39. Verified + inactive is part of the candidate species (per §4.13).
# ---------------------------------------------------------------------------


def test_verified_inactive_fact_projects_as_candidate(
    session: Session,
) -> None:
    _add_user(session, "account-A")
    fact = _add_personal_fact(
        session,
        user_id="account-A",
        status=PersonalFactStatus.VERIFIED.value,
        is_active=False,
    )

    projection = read_candidate_personal_fact_projection(
        session,
        authenticated_account_id="account-A",
        personal_fact_id=fact.id,
    )

    # Verified + inactive is not UMS-03F (UMS-03F requires is_active=true)
    # and is candidate / unreviewed per §4.13 ("OR is_active=false").
    assert projection is not None
    assert projection.semantic_species == "candidate_unreviewed_fact"
    assert projection.ambient_eligible is False


# ---------------------------------------------------------------------------
# 40. Disputed fact projects as candidate (per §4.13).
# ---------------------------------------------------------------------------


def test_disputed_fact_projects_as_candidate(session: Session) -> None:
    _add_user(session, "account-A")
    fact = _add_personal_fact(
        session,
        user_id="account-A",
        status=PersonalFactStatus.DISPUTED.value,
        is_active=True,
    )

    projection = read_candidate_personal_fact_projection(
        session,
        authenticated_account_id="account-A",
        personal_fact_id=fact.id,
    )

    assert projection is not None
    assert projection.semantic_species == "candidate_unreviewed_fact"
    assert projection.ambient_eligible is False


# ---------------------------------------------------------------------------
# 41. Archived fact projects as candidate (per §4.13).
# ---------------------------------------------------------------------------


def test_archived_fact_projects_as_candidate(session: Session) -> None:
    _add_user(session, "account-A")
    fact = _add_personal_fact(
        session,
        user_id="account-A",
        status=PersonalFactStatus.ARCHIVED.value,
        is_active=True,
    )

    projection = read_candidate_personal_fact_projection(
        session,
        authenticated_account_id="account-A",
        personal_fact_id=fact.id,
    )

    assert projection is not None
    assert projection.semantic_species == "candidate_unreviewed_fact"
    assert projection.ambient_eligible is False


# ---------------------------------------------------------------------------
# 42. Cross-account read returns None.
# ---------------------------------------------------------------------------


def test_candidate_fact_cross_account_returns_none(session: Session) -> None:
    _add_user(session, "account-A")
    _add_user(session, "account-B")
    fact = _add_personal_fact(
        session,
        user_id="account-A",
        status=PersonalFactStatus.CANDIDATE.value,
    )

    projection = read_candidate_personal_fact_projection(
        session,
        authenticated_account_id="account-B",
        personal_fact_id=fact.id,
    )

    assert projection is None


# ---------------------------------------------------------------------------
# 43. Missing fact returns None.
# ---------------------------------------------------------------------------


def test_candidate_fact_missing_returns_none(session: Session) -> None:
    _add_user(session, "account-A")

    projection = read_candidate_personal_fact_projection(
        session,
        authenticated_account_id="account-A",
        personal_fact_id=999_999,
    )

    assert projection is None


# ---------------------------------------------------------------------------
# 44. Empty account id fails closed.
# ---------------------------------------------------------------------------


def test_candidate_fact_empty_account_fails_closed(session: Session) -> None:
    _add_user(session, "account-A")
    fact = _add_personal_fact(
        session,
        user_id="account-A",
        status=PersonalFactStatus.CANDIDATE.value,
    )

    with pytest.raises(MemoryCompatibilityReadError):
        read_candidate_personal_fact_projection(
            session,
            authenticated_account_id="",
            personal_fact_id=fact.id,
        )


# ---------------------------------------------------------------------------
# 45. No canonical-table write occurs.
# ---------------------------------------------------------------------------


def test_candidate_fact_read_writes_nothing(session: Session) -> None:
    """Candidate compatibility read must not write to canonical or personal-fact tables."""

    _add_user(session, "account-A")
    fact = _add_personal_fact(
        session,
        user_id="account-A",
        status=PersonalFactStatus.CANDIDATE.value,
        is_active=True,
    )
    _add_evidence(session, fact_id=fact.id, source_type="runtime_extraction")
    _add_revision(session, fact_id=fact.id)

    bind = session.get_bind()
    engine = bind.engine if hasattr(bind, "engine") else bind
    statements: list[str] = []

    def _capture(_conn, _cursor, statement, _params, _context, _executemany):
        statements.append(statement)

    sa.event.listen(engine, "before_cursor_execute", _capture)
    try:
        projection = read_candidate_personal_fact_projection(
            session,
            authenticated_account_id="account-A",
            personal_fact_id=fact.id,
        )
    finally:
        sa.event.remove(engine, "before_cursor_execute", _capture)

    assert projection is not None

    import re

    write_pattern = re.compile(
        r"^\s*(INSERT|UPDATE|DELETE|TRUNCATE|MERGE)\b",
        re.IGNORECASE,
    )
    protected = _CANONICAL_TABLES_F + _PERSONAL_FACT_TABLES_F
    violations = [
        s
        for s in statements
        if write_pattern.match(s) and any(table in s for table in protected)
    ]
    assert violations == [], (
        "candidate compatibility read must not write to canonical or "
        f"personal-fact tables; saw: {violations}"
    )


# ---------------------------------------------------------------------------
# 46. No legacy mutation occurs on personal_facts / evidence / revisions.
# ---------------------------------------------------------------------------


def test_candidate_fact_read_does_not_mutate_legacy_rows(
    session: Session,
) -> None:
    _add_user(session, "account-A")
    fact = _add_personal_fact(
        session,
        user_id="account-A",
        key="favorite_food",
        value="ramen",
        status=PersonalFactStatus.CANDIDATE.value,
        is_active=True,
        guardrail_metadata={"source": "runtime_extraction"},
    )
    evidence = _add_evidence(
        session, fact_id=fact.id, source_type="runtime_extraction", excerpt="ramen"
    )
    revision = _add_revision(
        session,
        fact_id=fact.id,
        action="create",
        field_changed=None,
        old_value=None,
        new_value="candidate",
    )

    def _snapshot_fact(fid: int) -> dict:
        f = session.get(PersonalFact, fid)
        return {
            "id": f.id,
            "user_id": f.user_id,
            "key": f.key,
            "value": f.value,
            "status": f.status,
            "is_active": f.is_active,
            "confidence": f.confidence,
            "guardrail_metadata": (
                dict(f.guardrail_metadata) if f.guardrail_metadata is not None else None
            ),
        }

    before_fact = _snapshot_fact(fact.id)
    before_evidence = {
        "id": evidence.id,
        "source_type": evidence.source_type,
        "excerpt": evidence.excerpt,
    }
    before_revision = {
        "id": revision.id,
        "actor": revision.actor,
        "action": revision.action,
        "old_value": revision.old_value,
        "new_value": revision.new_value,
    }

    read_candidate_personal_fact_projection(
        session,
        authenticated_account_id="account-A",
        personal_fact_id=fact.id,
    )

    session.expire_all()
    after_fact = _snapshot_fact(fact.id)
    after_evidence = {
        "id": evidence.id,
        "source_type": evidence.source_type,
        "excerpt": evidence.excerpt,
    }
    after_revision = {
        "id": revision.id,
        "actor": revision.actor,
        "action": revision.action,
        "old_value": revision.old_value,
        "new_value": revision.new_value,
    }

    assert before_fact == after_fact
    assert before_evidence == after_evidence
    assert before_revision == after_revision


# ---------------------------------------------------------------------------
# 47. Candidate projection has no canonical memory_id.
# ---------------------------------------------------------------------------


def test_candidate_fact_has_no_canonical_memory_id(session: Session) -> None:
    _add_user(session, "account-A")
    fact = _add_personal_fact(
        session,
        user_id="account-A",
        status=PersonalFactStatus.CANDIDATE.value,
    )

    projection = read_candidate_personal_fact_projection(
        session,
        authenticated_account_id="account-A",
        personal_fact_id=fact.id,
    )

    assert projection is not None
    assert "memory_id" not in projection.__dataclass_fields__
    assert "canonical_memory_id" not in projection.__dataclass_fields__


# ---------------------------------------------------------------------------
# 48. Candidate projection does not invent Project or Persona.
# ---------------------------------------------------------------------------


def test_candidate_fact_does_not_invent_project_or_persona(
    session: Session,
) -> None:
    _add_user(session, "account-A")
    fact = _add_personal_fact(
        session,
        user_id="account-A",
        status=PersonalFactStatus.CANDIDATE.value,
    )

    projection = read_candidate_personal_fact_projection(
        session,
        authenticated_account_id="account-A",
        personal_fact_id=fact.id,
    )

    assert projection is not None
    assert projection.project_id is None
    assert projection.persona_links == []


# ---------------------------------------------------------------------------
# 49. Evidence with multiple rows remains distinct on candidate projection.
# ---------------------------------------------------------------------------


def test_candidate_fact_multiple_evidence_remain_distinct(
    session: Session,
) -> None:
    _add_user(session, "account-A")
    fact = _add_personal_fact(
        session,
        user_id="account-A",
        status=PersonalFactStatus.CANDIDATE.value,
    )
    _add_evidence(
        session,
        fact_id=fact.id,
        source_type="runtime_extraction",
        excerpt="first",
        created_at=NOW - timedelta(days=2),
    )
    _add_evidence(
        session,
        fact_id=fact.id,
        source_type="user_stated",
        excerpt="second (latest)",
        created_at=NOW,
    )

    projection = read_candidate_personal_fact_projection(
        session,
        authenticated_account_id="account-A",
        personal_fact_id=fact.id,
    )

    assert projection is not None
    assert len(projection.evidence) == 2
    # Both source types preserved; no deduplication.
    assert sorted(ev.source_type for ev in projection.evidence) == sorted(
        {"runtime_extraction", "user_stated"}
    )
    # Primary (latest) is the user_stated row.
    assert projection.provenance is not None
    assert projection.provenance.source_type == "user_stated"


# ---------------------------------------------------------------------------
# 50. Unknown evidence source_type still fails closed on candidate reader.
# ---------------------------------------------------------------------------


def test_candidate_fact_unknown_evidence_source_type_fails_closed(
    session: Session,
) -> None:
    _add_user(session, "account-A")
    fact = _add_personal_fact(
        session,
        user_id="account-A",
        status=PersonalFactStatus.CANDIDATE.value,
    )
    _add_evidence(session, fact_id=fact.id, source_type="not_in_vocabulary")

    with pytest.raises(MemoryCompatibilityReadError):
        read_candidate_personal_fact_projection(
            session,
            authenticated_account_id="account-A",
            personal_fact_id=fact.id,
        )


# ---------------------------------------------------------------------------
# 51. Candidate fact with no evidence still projects.
# ---------------------------------------------------------------------------


def test_candidate_fact_without_evidence_still_projects(
    session: Session,
) -> None:
    _add_user(session, "account-A")
    fact = _add_personal_fact(
        session,
        user_id="account-A",
        status=PersonalFactStatus.CANDIDATE.value,
    )

    projection = read_candidate_personal_fact_projection(
        session,
        authenticated_account_id="account-A",
        personal_fact_id=fact.id,
    )

    assert projection is not None
    assert projection.evidence == []
    assert projection.provenance is not None
    assert projection.provenance.source_type is None
    assert (
        projection.provenance.source_record_id
        == f"{PERSONAL_FACT_LEGACY_SOURCE_FAMILY}:{fact.id}"
    )


# ---------------------------------------------------------------------------
# 52. Candidate projection has no canonical memory_id field on the dataclass.
# ---------------------------------------------------------------------------


def test_candidate_fact_species_is_exact_token(session: Session) -> None:
    _add_user(session, "account-A")
    fact = _add_personal_fact(
        session,
        user_id="account-A",
        status=PersonalFactStatus.CANDIDATE.value,
    )

    projection = read_candidate_personal_fact_projection(
        session,
        authenticated_account_id="account-A",
        personal_fact_id=fact.id,
    )

    assert projection is not None
    assert projection.semantic_species == "candidate_unreviewed_fact"
    assert projection.semantic_species == PERSONAL_FACT_CANDIDATE_ENVELOPE_SPECIES
    assert projection.semantic_species != "verified_personal_fact"
    assert projection.semantic_species != "episodic_semantic_memory"


# ===========================================================================
# UMS-03I — Unified memory compatibility read surface.
# ===========================================================================


def _memory_entry_source(source_id: int) -> MemoryCompatibilitySourceRef:
    return MemoryCompatibilitySourceRef(
        source_kind=MemoryCompatibilitySourceKind.MEMORY_ENTRY,
        source_id=source_id,
    )


def _personal_fact_source(source_id: int) -> MemoryCompatibilitySourceRef:
    return MemoryCompatibilitySourceRef(
        source_kind=MemoryCompatibilitySourceKind.PERSONAL_FACT,
        source_id=source_id,
    )


# ---------------------------------------------------------------------------
# 53. Memory entry: unified output equals direct adapter output.
# ---------------------------------------------------------------------------


def test_unified_memory_entry_equals_direct(session: Session) -> None:
    _add_user(session, "account-A")
    entry = _add_memory_entry(
        session,
        user_id="account-A",
        silo="longterm",
        content="remember the trip to Lisbon",
        tags="travel,2026",
        pinned=True,
    )

    direct = read_memory_entry_projection(
        session,
        authenticated_account_id="account-A",
        memory_entry_id=entry.id,
    )
    unified = read_memory_compatibility_projection(
        session,
        authenticated_account_id="account-A",
        source=_memory_entry_source(entry.id),
    )

    assert direct is not None
    assert unified is not None
    assert unified == direct
    assert unified.legacy_source_family == MEMORY_ENTRY_LEGACY_SOURCE_FAMILY
    assert unified.semantic_species == MEMORY_ENTRY_ENVELOPE_SPECIES


# ---------------------------------------------------------------------------
# 54. Verified Personal Fact: unified output equals direct adapter output.
# ---------------------------------------------------------------------------


def test_unified_verified_personal_fact_equals_direct(
    session: Session,
) -> None:
    _add_user(session, "account-A")
    fact = _add_personal_fact(
        session,
        user_id="account-A",
        status=PersonalFactStatus.VERIFIED.value,
        is_active=True,
    )

    direct = read_verified_personal_fact_projection(
        session,
        authenticated_account_id="account-A",
        personal_fact_id=fact.id,
    )
    unified = read_memory_compatibility_projection(
        session,
        authenticated_account_id="account-A",
        source=_personal_fact_source(fact.id),
    )

    assert direct is not None
    assert unified is not None
    assert unified == direct
    assert unified.semantic_species == PERSONAL_FACT_VERIFIED_ENVELOPE_SPECIES


# ---------------------------------------------------------------------------
# 55. Candidate Personal Fact: unified output equals direct adapter output.
# ---------------------------------------------------------------------------


def test_unified_candidate_personal_fact_equals_direct(
    session: Session,
) -> None:
    _add_user(session, "account-A")
    fact = _add_personal_fact(
        session,
        user_id="account-A",
        status=PersonalFactStatus.CANDIDATE.value,
        is_active=True,
    )

    direct = read_candidate_personal_fact_projection(
        session,
        authenticated_account_id="account-A",
        personal_fact_id=fact.id,
    )
    unified = read_memory_compatibility_projection(
        session,
        authenticated_account_id="account-A",
        source=_personal_fact_source(fact.id),
    )

    assert direct is not None
    assert unified is not None
    assert unified == direct
    assert unified.semantic_species == PERSONAL_FACT_CANDIDATE_ENVELOPE_SPECIES


# ---------------------------------------------------------------------------
# 56. Disputed + archived + inactive Personal Facts dispatch to candidate
#     adapter and produce the same projection as the direct candidate reader.
# ---------------------------------------------------------------------------


def test_unified_dispatches_disputed_to_candidate(
    session: Session,
) -> None:
    _add_user(session, "account-A")
    fact = _add_personal_fact(
        session,
        user_id="account-A",
        status=PersonalFactStatus.DISPUTED.value,
        is_active=True,
    )

    direct = read_candidate_personal_fact_projection(
        session,
        authenticated_account_id="account-A",
        personal_fact_id=fact.id,
    )
    unified = read_memory_compatibility_projection(
        session,
        authenticated_account_id="account-A",
        source=_personal_fact_source(fact.id),
    )

    assert direct is not None
    assert unified is not None
    assert unified == direct
    assert unified.semantic_species == PERSONAL_FACT_CANDIDATE_ENVELOPE_SPECIES


def test_unified_dispatches_archived_to_candidate(
    session: Session,
) -> None:
    _add_user(session, "account-A")
    fact = _add_personal_fact(
        session,
        user_id="account-A",
        status=PersonalFactStatus.ARCHIVED.value,
        is_active=True,
    )

    direct = read_candidate_personal_fact_projection(
        session,
        authenticated_account_id="account-A",
        personal_fact_id=fact.id,
    )
    unified = read_memory_compatibility_projection(
        session,
        authenticated_account_id="account-A",
        source=_personal_fact_source(fact.id),
    )

    assert direct is not None
    assert unified is not None
    assert unified == direct
    assert unified.semantic_species == PERSONAL_FACT_CANDIDATE_ENVELOPE_SPECIES


def test_unified_dispatches_inactive_verified_to_candidate(
    session: Session,
) -> None:
    _add_user(session, "account-A")
    fact = _add_personal_fact(
        session,
        user_id="account-A",
        status=PersonalFactStatus.VERIFIED.value,
        is_active=False,
    )

    direct = read_candidate_personal_fact_projection(
        session,
        authenticated_account_id="account-A",
        personal_fact_id=fact.id,
    )
    unified = read_memory_compatibility_projection(
        session,
        authenticated_account_id="account-A",
        source=_personal_fact_source(fact.id),
    )

    assert direct is not None
    assert unified is not None
    assert unified == direct
    assert unified.semantic_species == PERSONAL_FACT_CANDIDATE_ENVELOPE_SPECIES


# ---------------------------------------------------------------------------
# 57. Cross-account reads fail closed.
# ---------------------------------------------------------------------------


def test_unified_cross_account_memory_entry_returns_none(
    session: Session,
) -> None:
    _add_user(session, "account-A")
    _add_user(session, "account-B")
    entry = _add_memory_entry(session, user_id="account-A")

    projection = read_memory_compatibility_projection(
        session,
        authenticated_account_id="account-B",
        source=_memory_entry_source(entry.id),
    )

    assert projection is None


def test_unified_cross_account_personal_fact_returns_none(
    session: Session,
) -> None:
    _add_user(session, "account-A")
    _add_user(session, "account-B")
    fact = _add_personal_fact(
        session,
        user_id="account-A",
        status=PersonalFactStatus.VERIFIED.value,
    )

    projection = read_memory_compatibility_projection(
        session,
        authenticated_account_id="account-B",
        source=_personal_fact_source(fact.id),
    )

    assert projection is None


# ---------------------------------------------------------------------------
# 58. Missing sources return None (not a fail-closed exception).
# ---------------------------------------------------------------------------


def test_unified_missing_memory_entry_returns_none(
    session: Session,
) -> None:
    _add_user(session, "account-A")
    projection = read_memory_compatibility_projection(
        session,
        authenticated_account_id="account-A",
        source=_memory_entry_source(999_999),
    )
    assert projection is None


def test_unified_missing_personal_fact_returns_none(
    session: Session,
) -> None:
    _add_user(session, "account-A")
    projection = read_memory_compatibility_projection(
        session,
        authenticated_account_id="account-A",
        source=_personal_fact_source(999_999),
    )
    assert projection is None


# ---------------------------------------------------------------------------
# 59. Empty account id fails closed.
# ---------------------------------------------------------------------------


def test_unified_empty_account_fails_closed(session: Session) -> None:
    _add_user(session, "account-A")
    entry = _add_memory_entry(session, user_id="account-A")

    with pytest.raises(MemoryCompatibilityReadError):
        read_memory_compatibility_projection(
            session,
            authenticated_account_id="",
            source=_memory_entry_source(entry.id),
        )


# ---------------------------------------------------------------------------
# 60. Unsupported source kinds are rejected deterministically.
# ---------------------------------------------------------------------------


def test_unified_unsupported_source_kind_rejected(
    session: Session,
) -> None:
    _add_user(session, "account-A")

    class _FakeKind:
        # Stringly coerce to look like a valid kind for repr, but it
        # is not in SUPPORTED_COMPATIBILITY_SOURCE_KINDS.
        value = "personal_fact_evidence"

    bad = MemoryCompatibilitySourceRef(
        source_kind=_FakeKind(),  # type: ignore[arg-type]
        source_id=1,
    )

    with pytest.raises(MemoryCompatibilityReadError):
        read_memory_compatibility_projection(
            session,
            authenticated_account_id="account-A",
            source=bad,
        )


def test_unified_chat_message_source_kind_rejected(
    session: Session,
) -> None:
    _add_user(session, "account-A")

    class _ChatMsgKind:
        value = "chat_message"

    bad = MemoryCompatibilitySourceRef(
        source_kind=_ChatMsgKind(),  # type: ignore[arg-type]
        source_id=1,
    )

    with pytest.raises(MemoryCompatibilityReadError):
        read_memory_compatibility_projection(
            session,
            authenticated_account_id="account-A",
            source=bad,
        )


def test_unified_memoryos_source_kind_rejected(
    session: Session,
) -> None:
    _add_user(session, "account-A")

    class _MemoryosKind:
        value = "memoryos"

    bad = MemoryCompatibilitySourceRef(
        source_kind=_MemoryosKind(),  # type: ignore[arg-type]
        source_id=1,
    )

    with pytest.raises(MemoryCompatibilityReadError):
        read_memory_compatibility_projection(
            session,
            authenticated_account_id="account-A",
            source=bad,
        )


# ---------------------------------------------------------------------------
# 61. No canonical write or legacy mutation across unified dispatch.
# ---------------------------------------------------------------------------


def test_unified_dispatch_writes_nothing(session: Session) -> None:
    _add_user(session, "account-A")
    entry = _add_memory_entry(
        session,
        user_id="account-A",
        content="before unified",
    )
    fact = _add_personal_fact(
        session,
        user_id="account-A",
        status=PersonalFactStatus.VERIFIED.value,
        is_active=True,
    )
    _add_evidence(session, fact_id=fact.id, source_type="user_stated")
    _add_revision(session, fact_id=fact.id)

    bind = session.get_bind()
    engine = bind.engine if hasattr(bind, "engine") else bind
    statements: list[str] = []

    def _capture(_conn, _cursor, statement, _params, _context, _executemany):
        statements.append(statement)

    sa.event.listen(engine, "before_cursor_execute", _capture)
    try:
        read_memory_compatibility_projection(
            session,
            authenticated_account_id="account-A",
            source=_memory_entry_source(entry.id),
        )
        read_memory_compatibility_projection(
            session,
            authenticated_account_id="account-A",
            source=_personal_fact_source(fact.id),
        )
    finally:
        sa.event.remove(engine, "before_cursor_execute", _capture)

    import re

    write_pattern = re.compile(
        r"^\s*(INSERT|UPDATE|DELETE|TRUNCATE|MERGE)\b",
        re.IGNORECASE,
    )
    protected = _CANONICAL_TABLES_F + _PERSONAL_FACT_TABLES_F
    violations = [
        s
        for s in statements
        if write_pattern.match(s) and any(table in s for table in protected)
    ]
    assert violations == [], (
        "unified dispatch must not write to canonical or personal-fact "
        f"tables; saw: {violations}"
    )


# ---------------------------------------------------------------------------
# 62. No fabricated canonical memory_id.
# ---------------------------------------------------------------------------


def test_unified_has_no_canonical_memory_id(session: Session) -> None:
    _add_user(session, "account-A")
    entry = _add_memory_entry(session, user_id="account-A")
    fact = _add_personal_fact(
        session,
        user_id="account-A",
        status=PersonalFactStatus.VERIFIED.value,
    )

    for source in (_memory_entry_source(entry.id), _personal_fact_source(fact.id)):
        projection = read_memory_compatibility_projection(
            session,
            authenticated_account_id="account-A",
            source=source,
        )
        assert projection is not None
        assert "memory_id" not in projection.__dataclass_fields__
        assert "canonical_memory_id" not in projection.__dataclass_fields__


# ---------------------------------------------------------------------------
# 63. Caller cannot forge species (no species argument exists).
# ---------------------------------------------------------------------------


def test_unified_dispatcher_takes_no_species_argument(
    session: Session,
) -> None:
    """The unified surface has no species argument; it is determined server-side."""
    import inspect

    sig = inspect.signature(read_memory_compatibility_projection)
    assert "semantic_species" not in sig.parameters
    assert "species" not in sig.parameters
    assert "status" not in sig.parameters
    assert "is_active" not in sig.parameters


# ---------------------------------------------------------------------------
# 64. Memory entry source identity is preserved exactly.
# ---------------------------------------------------------------------------


def test_unified_memory_entry_preserves_source_identity(
    session: Session,
) -> None:
    _add_user(session, "account-A")
    entry = _add_memory_entry(session, user_id="account-A")

    projection = read_memory_compatibility_projection(
        session,
        authenticated_account_id="account-A",
        source=_memory_entry_source(entry.id),
    )

    assert projection is not None
    assert projection.legacy_source_family == MEMORY_ENTRY_LEGACY_SOURCE_FAMILY
    assert (
        projection.legacy_source_record_id
        == f"{MEMORY_ENTRY_LEGACY_SOURCE_FAMILY}:{entry.id}"
    )
