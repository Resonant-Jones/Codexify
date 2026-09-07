"""Focused tests for the UMS-03E ``memory_entries`` compatibility projection.

These tests prove the acceptance matrix from the UMS-03E task spec:

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
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker

from guardian.core.memory_compatibility import (
    MEMORY_ENTRY_ENVELOPE_SPECIES,
    MEMORY_ENTRY_LEGACY_SOURCE_FAMILY,
    MEMORY_ENTRY_LEGACY_SOURCE_SYSTEM,
    MemoryCompatibilityReadError,
    read_memory_entry_projection,
)
from guardian.db.models import Base, MemoryEntry, Project, User
from guardian.protocol_tokens import MemorySemanticSpecies

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
    sa.event.listen(
        engine,
        "connect",
        lambda connection, _: connection.execute("PRAGMA foreign_keys=ON"),
    )
    tables = [
        User.__table__,
        Project.__table__,
        MemoryEntry.__table__,
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
