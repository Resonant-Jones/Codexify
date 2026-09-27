"""Focused account-restore proof for ordinary-memory content revisions.

UMS-05C9. Uses real disposable PostgreSQL for every load-bearing case.

Proves:

* clean v5 restore writes a coherent revision chain;
* stable revision IDs, exact text, and chain order survive;
* the final revision reconciles with the parent canonical current content;
* account isolation holds;
* malformed parent, cross-account, duplicate sequence, broken chain,
  no-op row, and final-content mismatch all fail closed;
* a revision attached to a specialized Personal Facts parent fails closed;
* replay is idempotent;
* a semantic conflict, and a late persistence failure, roll back.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import psycopg
import pytest
import sqlalchemy as sa

from guardian.services.account_export import REVISION_MANIFEST_SCHEMA_VERSION
from guardian.services.account_restore import (
    CanonicalMemoryRestoreExecutor,
    CanonicalMemoryRestorePlan,
    UnifiedMemoryRestoreConflictError,
    UnifiedMemoryRestorePreflight,
    UnifiedMemoryRestorePreflightError,
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
MEMORY_A = "66666666-6666-6666-6666-666666666666"
MEMORY_A_FACT = "77777777-7777-7777-7777-777777777777"
SUBJECT_A = "88888888-8888-8888-8888-888888888888"
NOW = "2026-09-27T10:00:00+00:00"
LATER = "2026-09-27T11:00:00+00:00"

EXACT_ORIGINAL = "  Original.\n\tTabbed — em-dash, “quotes”, 日本語.  "
EXACT_CORRECTED = "Corrected!  \r\nNewline, emoji 🎯, and  double  spaces. "
EXACT_FINAL = "Final revision.  \nTrailing whitespace kept.   "

REV_1 = "bbbbbbbb-1111-1111-1111-111111111111"
REV_2 = "bbbbbbbb-2222-2222-2222-222222222222"


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
            {
                "memory_id": MEMORY_A,
                "user_id": ACCOUNT_A,
                "project_id": PROJECT_A,
                "semantic_species": "episodic_semantic_memory",
                "text_content": EXACT_FINAL,
                "fact_key": None,
                "fact_value": None,
                "fact_confidence": None,
                "reviewed_at": NOW,
                "activated_at": NOW,
                "pinned": False,
                "held": False,
                "review_state": "approved",
                "lifecycle_state": "active",
                "extensions": None,
                "created_at": NOW,
                "updated_at": LATER,
            },
            {
                "memory_id": MEMORY_A_FACT,
                "user_id": ACCOUNT_A,
                "project_id": None,
                "semantic_species": "verified_personal_fact",
                "text_content": None,
                "fact_key": "preferred_mode",
                "fact_value": "local-first",
                "fact_confidence": 0.95,
                "reviewed_at": NOW,
                "activated_at": LATER,
                "pinned": False,
                "held": True,
                "review_state": "approved",
                "lifecycle_state": "active",
                "extensions": None,
                "created_at": NOW,
                "updated_at": LATER,
            },
        ],
        "memory_persona_links": [],
        "memory_provenance": [
            {
                "provenance_id": "99999999-9999-9999-9999-999999999999",
                "memory_id": MEMORY_A,
                "user_id": ACCOUNT_A,
                "source_system": "codexify",
                "source_record_id": "chat-message:2001",
                "source_thread_id": THREAD_A,
                "source_message_id": MESSAGE_A,
                "source_import_job_id": None,
                "source_export_fingerprint": None,
                "source_subject_kind": "chat",
                "source_subject_id": str(THREAD_A),
                "is_imported": False,
                "extensions": None,
                "created_at": NOW,
            },
            {
                "provenance_id": "aaaaaaaa-9999-9999-9999-999999999999",
                "memory_id": MEMORY_A_FACT,
                "user_id": ACCOUNT_A,
                "source_system": "codexify",
                "source_record_id": "personal-fact:1",
                "source_thread_id": None,
                "source_message_id": None,
                "source_import_job_id": None,
                "source_export_fingerprint": None,
                "source_subject_kind": "vault",
                "source_subject_id": "fact-editor",
                "is_imported": False,
                "extensions": None,
                "created_at": NOW,
            },
        ],
        "memory_revisions": [
            {
                "revision_id": REV_1,
                "memory_id": MEMORY_A,
                "user_id": ACCOUNT_A,
                "revision_number": 1,
                "old_text_content": EXACT_ORIGINAL,
                "new_text_content": EXACT_CORRECTED,
                "created_at": NOW,
            },
            {
                "revision_id": REV_2,
                "memory_id": MEMORY_A,
                "user_id": ACCOUNT_A,
                "revision_number": 2,
                "old_text_content": EXACT_CORRECTED,
                "new_text_content": EXACT_FINAL,
                "created_at": LATER,
            },
        ],
    }


def _preflight() -> UnifiedMemoryRestorePreflight:
    return UnifiedMemoryRestorePreflight(
        target_account_id=ACCOUNT_A,
        source_account_id=ACCOUNT_A,
        project_map={PROJECT_A: PROJECT_A_TARGET},
        thread_map={THREAD_A: THREAD_A_TARGET},
        message_map={MESSAGE_A: MESSAGE_A_TARGET},
        # The six-family v5 canonical graph is opt-in; the preflight default
        # stays v4 so existing five-family callers keep their semantics.
        schema_version=REVISION_MANIFEST_SCHEMA_VERSION,
    )


def _plan(payload: dict[str, list[dict[str, Any]]]) -> CanonicalMemoryRestorePlan:
    return _preflight().plan(payload)


def _seed_sources(cur) -> None:
    """Seed the regular (non-canonical) parents the v5 archive references."""
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


def _revision_rows(connection, memory_id: str) -> list[tuple]:
    return connection.execute(
        sa.text(
            "SELECT revision_id, revision_number, old_text_content, "
            "new_text_content FROM memory_revisions "
            "WHERE memory_id = :m AND user_id = :u "
            "ORDER BY revision_number ASC"
        ),
        {"m": memory_id, "u": ACCOUNT_A},
    ).fetchall()


# ---------------------------------------------------------------------------
# 1-6: clean restore, counts, stable IDs, exact text, order, reconciliation.
# ---------------------------------------------------------------------------


def test_clean_v5_restore_persists_coherent_chain(temporary_postgres) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    plan = _plan(_valid_payload_rows())

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            _seed_sources(cur)
        conn.commit()
        result = CanonicalMemoryRestoreExecutor(plan).execute(conn)
        conn.commit()

    assert result.revision_created_count == 2
    assert result.revision_identical_count == 0

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT text_content FROM memory_records WHERE memory_id = %s",
                (MEMORY_A,),
            )
            assert cur.fetchone()[0] == EXACT_FINAL
    with sa.create_engine(database_url, future=True).begin() as conn:
        rows = _revision_rows(conn, MEMORY_A)
        assert [r[1] for r in rows] == [1, 2]
        assert rows[0][0] == REV_1
        assert rows[1][0] == REV_2
        # Exact text, no trimming.
        assert rows[0][2] == EXACT_ORIGINAL
        assert rows[1][3] == EXACT_FINAL
        # Chain intact; final reconciles with parent canonical text.
        assert rows[0][3] == rows[1][2]
        assert rows[-1][3] == EXACT_FINAL


def test_clean_v5_restore_creates_zero_rows_for_memory_without_revisions(
    temporary_postgres,
) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    payload = _valid_payload_rows()
    # Attach a revision to the episodic memory only; the fact memory has none.
    plan = _plan(payload)

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            _seed_sources(cur)
        conn.commit()
        result = CanonicalMemoryRestoreExecutor(plan).execute(conn)
        conn.commit()

    with sa.create_engine(database_url, future=True).begin() as conn:
        assert _revision_rows(conn, MEMORY_A_FACT) == []


# ---------------------------------------------------------------------------
# 8-13: fail-closed preflight.
# ---------------------------------------------------------------------------


def test_malformed_parent_fails_closed() -> None:
    payload = _valid_payload_rows()
    payload["memory_revisions"][0]["memory_id"] = "99999999-9999-9999-9999-999999999999"
    with pytest.raises(UnifiedMemoryRestorePreflightError) as exc_info:
        _plan(payload)
    assert exc_info.value.code == "memory_revision_orphan"


def test_cross_account_revision_fails_closed() -> None:
    payload = _valid_payload_rows()
    payload["memory_revisions"][0]["user_id"] = ACCOUNT_B
    with pytest.raises(UnifiedMemoryRestorePreflightError) as exc_info:
        _plan(payload)
    assert exc_info.value.code == "memory_revision_account_mismatch"


def test_duplicate_sequence_conflict_fails_closed() -> None:
    payload = _valid_payload_rows()
    payload["memory_revisions"][1]["revision_number"] = 1
    with pytest.raises(UnifiedMemoryRestorePreflightError) as exc_info:
        _plan(payload)
    assert exc_info.value.code == "memory_revision_sequence_conflict"


def test_broken_chain_fails_closed() -> None:
    payload = _valid_payload_rows()
    # Rev 2's old no longer equals rev 1's new.
    payload["memory_revisions"][1]["old_text_content"] = "unrelated prior text"
    with pytest.raises(UnifiedMemoryRestorePreflightError) as exc_info:
        _plan(payload)
    assert exc_info.value.code == "memory_revision_chain_broken"


def test_sequence_gap_fails_closed() -> None:
    payload = _valid_payload_rows()
    payload["memory_revisions"][1]["revision_number"] = 3
    with pytest.raises(UnifiedMemoryRestorePreflightError) as exc_info:
        _plan(payload)
    assert exc_info.value.code == "memory_revision_sequence_gap"


def test_noop_revision_fails_closed() -> None:
    payload = _valid_payload_rows()
    payload["memory_revisions"][0]["new_text_content"] = EXACT_ORIGINAL
    with pytest.raises(UnifiedMemoryRestorePreflightError) as exc_info:
        _plan(payload)
    assert exc_info.value.code == "memory_revision_noop"


def test_final_content_mismatch_fails_closed() -> None:
    payload = _valid_payload_rows()
    # Parent text drifts away from the final revision while the chain stays
    # internally consistent, so the reconciliation check is the one that fires.
    payload["memory_records"][0]["text_content"] = "something else entirely"
    with pytest.raises(UnifiedMemoryRestorePreflightError) as exc_info:
        _plan(payload)
    assert exc_info.value.code == "memory_revision_final_content_mismatch"


def test_personal_fact_parent_fails_closed() -> None:
    payload = _valid_payload_rows()
    payload["memory_revisions"][0]["memory_id"] = MEMORY_A_FACT
    with pytest.raises(UnifiedMemoryRestorePreflightError) as exc_info:
        _plan(payload)
    assert exc_info.value.code == "memory_revision_unsupported_parent_species"


def test_invalid_revision_number_fails_closed() -> None:
    payload = _valid_payload_rows()
    payload["memory_revisions"][0]["revision_number"] = 0
    with pytest.raises(UnifiedMemoryRestorePreflightError) as exc_info:
        _plan(payload)
    assert exc_info.value.code == "memory_revision_number_invalid"


def test_malformed_revision_payload_fails_closed() -> None:
    payload = _valid_payload_rows()
    payload["memory_revisions"][0]["old_text_content"] = 12345
    with pytest.raises(UnifiedMemoryRestorePreflightError) as exc_info:
        _plan(payload)
    assert exc_info.value.code == "memory_revision_payload_invalid"


# ---------------------------------------------------------------------------
# 14: replay idempotency.
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
    assert first.revision_created_count == 2

    with psycopg.connect(database_url) as conn:
        second = CanonicalMemoryRestoreExecutor(plan).execute(conn)
        conn.commit()
    assert second.revision_created_count == 0
    assert second.revision_identical_count == 2

    with sa.create_engine(database_url, future=True).begin() as conn:
        rows = _revision_rows(conn, MEMORY_A)
        assert len(rows) == 2
        assert rows[-1][3] == EXACT_FINAL


# ---------------------------------------------------------------------------
# 15: semantic conflict rolls back.
# ---------------------------------------------------------------------------


def test_semantic_conflict_rolls_back(temporary_postgres) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    plan = _plan(_valid_payload_rows())

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            _seed_sources(cur)
        conn.commit()
        CanonicalMemoryRestoreExecutor(plan).execute(conn)
        conn.commit()

    # Same revision_id, different semantic content, but the chain stays
    # internally coherent so preflight passes and the executor's identity
    # comparison is what fails.
    conflicting = deepcopy(_valid_payload_rows())
    conflicting["memory_revisions"][0]["new_text_content"] = "conflicting text"
    conflicting["memory_revisions"][1]["old_text_content"] = "conflicting text"
    conflicting["memory_revisions"][1]["new_text_content"] = EXACT_FINAL
    conflicting["memory_records"][0]["text_content"] = EXACT_FINAL
    conflicting_plan = _plan(conflicting)

    with psycopg.connect(database_url) as conn:
        with pytest.raises(UnifiedMemoryRestoreConflictError):
            CanonicalMemoryRestoreExecutor(conflicting_plan).execute(conn)
        conn.rollback()

    with sa.create_engine(database_url, future=True).begin() as conn:
        rows = _revision_rows(conn, MEMORY_A)
        assert len(rows) == 2
        assert rows[0][3] == EXACT_CORRECTED  # original value retained
        assert rows[-1][3] == EXACT_FINAL


def test_sequence_occupancy_conflict_fails_closed_at_executor(
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

    # A different revision_id tries to occupy (memory, 1).
    conflicting = deepcopy(_valid_payload_rows())
    conflicting["memory_revisions"][0][
        "revision_id"
    ] = "dddddddd-1111-1111-1111-111111111111"
    conflicting_plan = _plan(conflicting)

    with psycopg.connect(database_url) as conn:
        with pytest.raises(
            UnifiedMemoryRestoreConflictError,
            match="memory_revision_sequence_conflict",
        ):
            CanonicalMemoryRestoreExecutor(conflicting_plan).execute(conn)
        conn.rollback()


# ---------------------------------------------------------------------------
# 16: late persistence failure rolls back.
# ---------------------------------------------------------------------------


def test_late_revision_persistence_failure_rolls_back(temporary_postgres) -> None:
    """Force a failure at the revision persistence stage only.

    Parent memory rows are already inserted; a revision INSERT failure must
    abort the whole transaction so no partial canonical graph commits.
    """
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    plan = _plan(_valid_payload_rows())

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            _seed_sources(cur)
        conn.commit()

        executor = CanonicalMemoryRestoreExecutor(plan)
        original_insert_revisions = executor._insert_revisions

        def _boom(*args, **kwargs):
            raise RuntimeError("forced revision persistence failure")

        executor._insert_revisions = _boom  # type: ignore[method-assign]
        with pytest.raises(RuntimeError, match="forced revision persistence failure"):
            executor.execute(conn)
        conn.rollback()

    with sa.create_engine(database_url, future=True).begin() as conn:
        # Nothing from this restore attempt committed.
        memories = conn.execute(
            sa.text("SELECT COUNT(*) FROM memory_records")
        ).scalar_one()
        revisions = conn.execute(
            sa.text("SELECT COUNT(*) FROM memory_revisions")
        ).scalar_one()
    assert memories == 0
    assert revisions == 0
    assert original_insert_revisions is not None
