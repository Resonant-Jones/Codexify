"""Focused account-restore proof for permanent-erasure suppression tombstones.

UMS-11. Uses real disposable PostgreSQL for every load-bearing case.

Proves:

* a clean v8 restore persists coherent, minimum non-content suppression
  state with stable receipt identity, stable record fingerprint, stable
  source-atom fingerprint, exact purge time, and ``suppress_reimport`` true;
* **suppression survives restore**, which is the whole point: a source atom
  purged on the source instance is still suppressed at the service boundary
  on the destination;
* restoring a tombstone never recreates the memory it describes;
* an archive carrying *both* a live canonical memory and a tombstone
  suppressing that same identity, or that same source atom, fails closed --
  neither side is silently preferred;
* account isolation, and fail-closed behavior for cross-account rows,
  relaxed suppression, malformed fingerprints, duplicate receipts, duplicate
  source-atom suppression, and content-bearing tombstones;
* replay is idempotent, and a semantic conflict rolls back; and
* whole-restore atomicity is intact.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any

import psycopg
import pytest
import sqlalchemy as sa

from guardian.db.models import MemoryRecord
from guardian.services.account_export import PURGE_TOMBSTONE_MANIFEST_SCHEMA_VERSION
from guardian.services.account_restore import (
    CanonicalMemoryRestoreExecutor,
    UnifiedMemoryRestoreConflictError,
    UnifiedMemoryRestorePreflight,
    UnifiedMemoryRestorePreflightError,
)
from guardian.services.memory_purge import (
    SUPPRESSION_OUTCOME_SUPPRESSED,
    MemoryPurgeService,
    source_atom_fingerprint,
)
from tests.migration.test_canonical_memory_persistence_migration import (  # noqa: E402
    _upgrade,
    temporary_postgres,
)

ACCOUNT_A = "account-a"
ACCOUNT_B = "account-b"
PROJECT_A = 101
PROJECT_A_TARGET = 1101
THREAD_A = 1001
THREAD_A_TARGET = 11001
MESSAGE_A = 2001
MESSAGE_A_TARGET = 12001

MEMORY_A = "55555555-5555-5555-5555-555555555555"
MEMORY_B = "66666666-6666-6666-6666-666666666666"

SUBJECT_A = "11111111-1111-1111-1111-111111111111"

RID_1 = "aaaa1111-1111-1111-1111-111111111111"
RID_2 = "aaaa2222-2222-2222-2222-222222222222"

NOW = "2026-09-30T12:00:00+00:00"
LATER = "2026-09-30T13:00:00+00:00"

RECORD_FP_1 = "v1:" + "a" * 64
RECORD_FP_2 = "v1:" + "b" * 64

#: The exact source atom whose digest the archive claims is suppressed. The
#: archive value is the real canonical digest, not a synthetic constant, so
#: the round trip proves the algorithm agrees end to end.
ATOM_SYSTEM = "openai"
ATOM_KIND = "importer"
ATOM_IDENTITY = "thread-purged-42"
SOURCE_FP_1 = source_atom_fingerprint(
    source_system=ATOM_SYSTEM,
    source_entity_kind=ATOM_KIND,
    source_atom_identity=ATOM_IDENTITY,
)


def _memory_row(
    memory_id: str,
    *,
    lifecycle_state: str = "active",
    species: str = "episodic_semantic_memory",
) -> dict[str, Any]:
    return {
        "memory_id": memory_id,
        "user_id": ACCOUNT_A,
        "project_id": None,
        "semantic_species": species,
        "text_content": "content" if species == "episodic_semantic_memory" else None,
        "fact_key": None if species == "episodic_semantic_memory" else "k",
        "fact_value": None if species == "episodic_semantic_memory" else "v",
        "fact_confidence": (None if species == "episodic_semantic_memory" else 0.9),
        "reviewed_at": NOW,
        "activated_at": NOW,
        "pinned": False,
        "held": False,
        "review_state": "approved",
        "lifecycle_state": lifecycle_state,
        "extensions": None,
        "created_at": NOW,
        "updated_at": LATER,
    }


def _provenance_row(memory_id: str, provenance_id: str) -> dict[str, Any]:
    return {
        "provenance_id": provenance_id,
        "memory_id": memory_id,
        "user_id": ACCOUNT_A,
        "source_system": "codexify",
        "source_record_id": f"source-{memory_id}",
        "source_thread_id": None,
        "source_message_id": None,
        "source_import_job_id": None,
        "source_export_fingerprint": None,
        "source_subject_kind": "vault",
        "source_subject_id": "vault-editor",
        "is_imported": False,
        "extensions": None,
        "created_at": NOW,
    }


def _tombstone_row(
    receipt_id: str = RID_1,
    *,
    user_id: str = ACCOUNT_A,
    record_fingerprint: str = RECORD_FP_1,
    source_system: str | None = ATOM_SYSTEM,
    source_entity_kind: str | None = ATOM_KIND,
    source_atom_fingerprint: str | None = SOURCE_FP_1,
    purged_at: str = NOW,
    suppress_reimport: bool = True,
) -> dict[str, Any]:
    return {
        "purge_receipt_id": receipt_id,
        "user_id": user_id,
        "purged_record_fingerprint": record_fingerprint,
        "source_system": source_system,
        "source_entity_kind": source_entity_kind,
        "source_atom_fingerprint": source_atom_fingerprint,
        "purged_at": purged_at,
        "suppress_reimport": suppress_reimport,
    }


def _valid_payload_rows() -> dict[str, list[dict[str, Any]]]:
    return {
        "persona_subjects": [
            {
                "persona_subject_id": SUBJECT_A,
                "user_id": ACCOUNT_A,
                "display_name_snapshot": "Subject A",
                "lifecycle": "active",
                "created_at": NOW,
                "updated_at": NOW,
            }
        ],
        "persona_subject_bindings": [],
        "memory_records": [
            _memory_row(MEMORY_A),
            _memory_row(MEMORY_B),
        ],
        "memory_persona_links": [],
        "memory_provenance": [
            _provenance_row(MEMORY_A, "99999999-9999-9999-9999-999999999999"),
            _provenance_row(MEMORY_B, "88888888-8888-8888-8888-888888888888"),
        ],
        "memory_revisions": [],
        "memory_review_revisions": [],
        "memory_lifecycle_revisions": [],
        "memory_purge_tombstones": [_tombstone_row()],
    }


def _preflight(
    *, source_account: str = ACCOUNT_A, target_account: str = ACCOUNT_A
) -> UnifiedMemoryRestorePreflight:
    return UnifiedMemoryRestorePreflight(
        target_account_id=target_account,
        source_account_id=source_account,
        project_map={PROJECT_A: PROJECT_A_TARGET},
        thread_map={THREAD_A: THREAD_A_TARGET},
        message_map={MESSAGE_A: MESSAGE_A_TARGET},
        # The nine-family v8 canonical graph is opt-in.
        schema_version=PURGE_TOMBSTONE_MANIFEST_SCHEMA_VERSION,
    )


def _plan(payload: dict[str, list[dict[str, Any]]]):
    return _preflight().plan(payload)


def _seed_sources(cur) -> None:
    cur.execute(
        "INSERT INTO users (id, username, password_hash, role) "
        "VALUES (%s, %s, 'not-a-real-hash', 'guest')",
        (ACCOUNT_A, ACCOUNT_A),
    )
    cur.execute(
        "INSERT INTO projects (id, user_id, name) VALUES (%s, %s, 'p')",
        (PROJECT_A_TARGET, ACCOUNT_A),
    )
    cur.execute(
        "INSERT INTO chat_threads (id, user_id, title, project_id) "
        "VALUES (%s, %s, 't', %s)",
        (THREAD_A_TARGET, ACCOUNT_A, PROJECT_A_TARGET),
    )
    cur.execute(
        "INSERT INTO chat_messages (id, thread_id, user_id, role, content) "
        "VALUES (%s, %s, %s, 'user', 'c')",
        (MESSAGE_A_TARGET, THREAD_A_TARGET, ACCOUNT_A),
    )


def _tombstone_rows(database_url: str) -> list[tuple]:
    with sa.create_engine(database_url, future=True).begin() as conn:
        return list(
            conn.execute(
                sa.text(
                    "SELECT purge_receipt_id, user_id, "
                    "purged_record_fingerprint, source_system, "
                    "source_entity_kind, source_atom_fingerprint, purged_at, "
                    "suppress_reimport FROM memory_purge_tombstones "
                    "ORDER BY purge_receipt_id ASC"
                )
            ).fetchall()
        )


# ---------------------------------------------------------------------------
# 1-6: clean restore, exactness, and surviving suppression.
# ---------------------------------------------------------------------------


def test_clean_v8_restore_persists_exact_tombstone(
    temporary_postgres,
) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    plan = _plan(_valid_payload_rows())

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            _seed_sources(cur)
        conn.commit()
        result = CanonicalMemoryRestoreExecutor(plan).execute(conn)
        conn.commit()

    assert result.purge_tombstone_created_count == 1
    assert result.purge_tombstone_identical_count == 0

    rows = _tombstone_rows(database_url)
    assert len(rows) == 1
    assert rows[0][0] == RID_1
    assert rows[0][1] == ACCOUNT_A
    assert rows[0][2] == RECORD_FP_1
    assert rows[0][3] == ATOM_SYSTEM
    assert rows[0][4] == ATOM_KIND
    assert rows[0][5] == SOURCE_FP_1
    assert rows[0][6] == datetime.fromisoformat(NOW)
    assert rows[0][7] is True


def test_restore_never_recreates_the_purged_memory(
    temporary_postgres,
) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    plan = _plan(_valid_payload_rows())

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            _seed_sources(cur)
        conn.commit()
        CanonicalMemoryRestoreExecutor(plan).execute(conn)
        conn.commit()

    # Exactly the two archive memories exist, and no memory_id was invented
    # for the erased atom.
    with sa.create_engine(database_url, future=True).begin() as conn:
        ids = {
            row[0]
            for row in conn.execute(
                sa.text("SELECT memory_id FROM memory_records")
            ).fetchall()
        }
    assert ids == {MEMORY_A, MEMORY_B}


def test_suppression_survives_restore_at_the_service_boundary(
    temporary_postgres,
) -> None:
    """The load-bearing obligation: erasure survives migration."""
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    plan = _plan(_valid_payload_rows())

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            _seed_sources(cur)
        conn.commit()
        CanonicalMemoryRestoreExecutor(plan).execute(conn)
        conn.commit()

    engine = sa.create_engine(database_url, future=True)
    from sqlalchemy.orm import sessionmaker

    with sessionmaker(bind=engine, expire_on_commit=False)() as session:
        service = MemoryPurgeService(session, authenticated_account_id=ACCOUNT_A)
        # The archive's fingerprint must be exactly what the canonical
        # algorithm produces for that atom, or suppression silently fails.
        status = service.source_atom_suppression_status(
            source_system=ATOM_SYSTEM,
            source_entity_kind=ATOM_KIND,
            source_atom_identity=ATOM_IDENTITY,
        )
        assert status.suppressed is True
        assert status.outcome == SUPPRESSION_OUTCOME_SUPPRESSED

        # An unrelated atom is still allowed.
        assert (
            service.source_atom_suppression_status(
                source_system=ATOM_SYSTEM,
                source_entity_kind=ATOM_KIND,
                source_atom_identity="thread-other",
            ).suppressed
            is False
        )
    engine.dispose()


def test_zero_tombstone_restore_is_valid(temporary_postgres) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    payload = _valid_payload_rows()
    payload["memory_purge_tombstones"] = []
    plan = _plan(payload)

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            _seed_sources(cur)
        conn.commit()
        result = CanonicalMemoryRestoreExecutor(plan).execute(conn)
        conn.commit()

    assert result.purge_tombstone_created_count == 0
    assert _tombstone_rows(database_url) == []


def test_direct_purge_null_source_fingerprint_round_trips(
    temporary_postgres,
) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    payload = _valid_payload_rows()
    payload["memory_purge_tombstones"] = [
        _tombstone_row(
            RID_2,
            record_fingerprint=RECORD_FP_2,
            source_system=None,
            source_entity_kind=None,
            source_atom_fingerprint=None,
        )
    ]
    plan = _plan(payload)

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            _seed_sources(cur)
        conn.commit()
        CanonicalMemoryRestoreExecutor(plan).execute(conn)
        conn.commit()

    rows = _tombstone_rows(database_url)
    assert len(rows) == 1
    assert rows[0][0] == RID_2
    assert rows[0][3] is None
    assert rows[0][4] is None
    assert rows[0][5] is None


# ---------------------------------------------------------------------------
# 7. The contradiction rule.
# ---------------------------------------------------------------------------


def test_live_memory_plus_matching_tombstone_fails_closed(
    temporary_postgres,
) -> None:
    """An archive cannot both restore a memory and claim it was purged."""
    from guardian.services.memory_purge import purged_record_fingerprint

    config, database_url = temporary_postgres
    _upgrade(config, "head")
    payload = _valid_payload_rows()
    payload["memory_purge_tombstones"] = [
        _tombstone_row(
            record_fingerprint=purged_record_fingerprint(MEMORY_A),
        )
    ]
    with pytest.raises(UnifiedMemoryRestorePreflightError):
        _plan(payload)


def test_live_imported_memory_plus_matching_source_atom_fails_closed(
    temporary_postgres,
) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    payload = _valid_payload_rows()
    # Make MEMORY_A import-origin from the very atom the tombstone suppresses.
    payload["memory_provenance"][0] = {
        **payload["memory_provenance"][0],
        "source_system": ATOM_SYSTEM,
        "source_record_id": ATOM_IDENTITY,
        "source_subject_kind": ATOM_KIND,
        "is_imported": True,
    }
    payload["memory_purge_tombstones"] = [
        _tombstone_row(source_atom_fingerprint=SOURCE_FP_1)
    ]
    with pytest.raises(UnifiedMemoryRestorePreflightError):
        _plan(payload)


def test_unrelated_tombstone_does_not_conflict(temporary_postgres) -> None:
    """A different erased record's tombstone is not a contradiction."""
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    plan = _plan(_valid_payload_rows())
    assert len(plan.memory_purge_tombstones) == 1


# ---------------------------------------------------------------------------
# 8. Fail-closed shapes.
# ---------------------------------------------------------------------------


def test_cross_account_tombstone_fails_closed(temporary_postgres) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    payload = _valid_payload_rows()
    payload["memory_purge_tombstones"] = [_tombstone_row(user_id=ACCOUNT_B)]
    with pytest.raises(UnifiedMemoryRestorePreflightError):
        _plan(payload)


def test_relaxed_suppression_fails_closed(temporary_postgres) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    payload = _valid_payload_rows()
    payload["memory_purge_tombstones"] = [_tombstone_row(suppress_reimport=False)]
    with pytest.raises(UnifiedMemoryRestorePreflightError):
        _plan(payload)


@pytest.mark.parametrize(
    "fingerprint",
    ["not-a-digest", "v1:tooshort", "", "nope:" + "a" * 64],
)
def test_malformed_record_fingerprint_fails_closed(
    temporary_postgres, fingerprint
) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    payload = _valid_payload_rows()
    payload["memory_purge_tombstones"] = [
        _tombstone_row(record_fingerprint=fingerprint)
    ]
    with pytest.raises(UnifiedMemoryRestorePreflightError):
        _plan(payload)


def test_malformed_source_fingerprint_fails_closed(temporary_postgres) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    payload = _valid_payload_rows()
    payload["memory_purge_tombstones"] = [
        _tombstone_row(source_atom_fingerprint="v1:zzzz")
    ]
    with pytest.raises(UnifiedMemoryRestorePreflightError):
        _plan(payload)


def test_duplicate_receipt_fails_closed(temporary_postgres) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    payload = _valid_payload_rows()
    payload["memory_purge_tombstones"] = [
        _tombstone_row(RID_1, record_fingerprint=RECORD_FP_1),
        _tombstone_row(RID_1, record_fingerprint=RECORD_FP_2),
    ]
    with pytest.raises(UnifiedMemoryRestorePreflightError):
        _plan(payload)


def test_duplicate_source_suppression_fails_closed(temporary_postgres) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    payload = _valid_payload_rows()
    payload["memory_purge_tombstones"] = [
        _tombstone_row(RID_1, record_fingerprint=RECORD_FP_1),
        _tombstone_row(RID_2, record_fingerprint=RECORD_FP_2),
    ]
    with pytest.raises(UnifiedMemoryRestorePreflightError):
        _plan(payload)


def test_content_bearing_tombstone_fails_closed(temporary_postgres) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    payload = _valid_payload_rows()
    payload["memory_purge_tombstones"] = [
        {**_tombstone_row(), "excerpt": "The red toolbox is in the garage."}
    ]
    with pytest.raises(UnifiedMemoryRestorePreflightError):
        _plan(payload)


# ---------------------------------------------------------------------------
# 9-10. Replay idempotency and conflict rollback.
# ---------------------------------------------------------------------------


def test_replay_is_idempotent(temporary_postgres) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    plan = _plan(_valid_payload_rows())

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            _seed_sources(cur)
        conn.commit()
        first = CanonicalMemoryRestoreExecutor(plan).execute(conn)
        conn.commit()
        second = CanonicalMemoryRestoreExecutor(plan).execute(conn)
        conn.commit()

    assert first.purge_tombstone_created_count == 1
    # Replay creates nothing and reports the row as identical.
    assert second.purge_tombstone_created_count == 0
    assert second.purge_tombstone_identical_count == 1
    assert len(_tombstone_rows(database_url)) == 1


def test_semantic_tombstone_conflict_rolls_back(temporary_postgres) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    plan = _plan(_valid_payload_rows())

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            _seed_sources(cur)
        conn.commit()
        CanonicalMemoryRestoreExecutor(plan).execute(conn)
        conn.commit()

    conflicting = _plan(
        {
            **_valid_payload_rows(),
            "memory_purge_tombstones": [
                # Same stable receipt identity, different semantics.
                _tombstone_row(record_fingerprint=RECORD_FP_2)
            ],
        }
    )
    with psycopg.connect(database_url) as conn:
        with pytest.raises(UnifiedMemoryRestoreConflictError):
            CanonicalMemoryRestoreExecutor(conflicting).execute(conn)
        conn.rollback()

    # The original tombstone is untouched.
    rows = _tombstone_rows(database_url)
    assert len(rows) == 1
    assert rows[0][2] == RECORD_FP_1


def test_whole_restore_remains_atomic(temporary_postgres) -> None:
    """A tombstone insert failure must not leave canonical memory behind."""
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    plan = _plan(_valid_payload_rows())

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            _seed_sources(cur)
        conn.commit()

        # Inject a bounded failure at the tombstone persistence stage using the
        # established stable-service-seam strategy: no production code is
        # edited to create the hook.
        import guardian.services.account_restore as restore_module

        def _boom(*_args, **_kwargs):
            raise RuntimeError("injected tombstone insert failure")

        original = (
            restore_module.CanonicalMemoryRestoreExecutor._insert_purge_tombstones
        )
        restore_module.CanonicalMemoryRestoreExecutor._insert_purge_tombstones = _boom
        try:
            with pytest.raises(Exception):
                CanonicalMemoryRestoreExecutor(plan).execute(conn)
        finally:
            restore_module.CanonicalMemoryRestoreExecutor._insert_purge_tombstones = (
                original
            )
        conn.rollback()

    with sa.create_engine(database_url, future=True).begin() as conn:
        memory_count = conn.execute(
            sa.text("SELECT count(*) FROM memory_records")
        ).scalar_one()
        tombstone_count = conn.execute(
            sa.text("SELECT count(*) FROM memory_purge_tombstones")
        ).scalar_one()
    # Nothing committed: no orphan memory, no orphan tombstone.
    assert memory_count == 0
    assert tombstone_count == 0
