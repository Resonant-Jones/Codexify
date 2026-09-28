"""Focused account-restore proof for ordinary-memory review revisions.

UMS-05C10A-P. Uses real disposable PostgreSQL for every load-bearing case.

Proves:

* clean v6 restore writes a coherent review-transition chain;
* stable review-revision IDs, exact typed states, actor, and timestamps
  survive;
* ``memory_records.review_state`` remains the canonical present value and
  history reconciles to it without overriding it;
* account isolation and actor containment hold;
* malformed parent, cross-account, actor mismatch, invalid token, no-op row,
  sequence gap, duplicate sequence, broken chain, final-state mismatch, and a
  specialized Personal Facts parent all fail closed;
* identical replay is idempotent;
* a semantic conflict, a sequence-occupancy conflict, and a late
  persistence failure each roll back the whole restore.

It does not implement any review mutation and asserts no legal-transition
policy: rows are seeded as canonical persistence.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any

import psycopg
import pytest
import sqlalchemy as sa

from guardian.services.account_export import REVIEW_REVISION_MANIFEST_SCHEMA_VERSION
from guardian.services.account_restore import (
    CanonicalMemoryRestoreExecutor,
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
NOW = "2026-09-28T10:00:00+00:00"
LATER = "2026-09-28T11:00:00+00:00"

EXACT_TEXT = "  Content with — em-dash, “quotes”, 日本語 and  spaces.  "

RR_1 = "cccccccc-1111-1111-1111-111111111111"
RR_2 = "cccccccc-2222-2222-2222-222222222222"
RR_3 = "cccccccc-3333-3333-3333-333333333333"
RR_B1 = "cccccccc-4444-4444-4444-444444444444"


def _memory_record(
    memory_id: str,
    *,
    review_state: str,
    species: str = "episodic_semantic_memory",
    text: str | None = EXACT_TEXT,
) -> dict[str, Any]:
    return {
        "memory_id": memory_id,
        "user_id": ACCOUNT_A,
        "project_id": PROJECT_A if species == "episodic_semantic_memory" else None,
        "semantic_species": species,
        "text_content": text,
        "fact_key": None if species == "episodic_semantic_memory" else "preferred_mode",
        "fact_value": None if species == "episodic_semantic_memory" else "local-first",
        "fact_confidence": (None if species == "episodic_semantic_memory" else 0.95),
        "reviewed_at": NOW,
        "activated_at": NOW,
        "pinned": False,
        "held": False,
        "review_state": review_state,
        "lifecycle_state": "active",
        "extensions": None,
        "created_at": NOW,
        "updated_at": LATER,
    }


def _review_revision(
    review_revision_id: str,
    memory_id: str,
    number: int,
    old: str,
    new: str,
    *,
    account: str = ACCOUNT_A,
    actor: str | None = None,
    created_at: str = NOW,
) -> dict[str, Any]:
    return {
        "review_revision_id": review_revision_id,
        "memory_id": memory_id,
        "user_id": account,
        "revision_number": number,
        "old_review_state": old,
        "new_review_state": new,
        "actor_account_id": actor or account,
        "created_at": created_at,
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
            _memory_record(MEMORY_A, review_state="rejected"),
            _memory_record(
                MEMORY_A_FACT,
                review_state="approved",
                species="verified_personal_fact",
                text=None,
            ),
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
        "memory_revisions": [],
        "memory_review_revisions": [
            _review_revision(RR_1, MEMORY_A, 1, "pending", "approved"),
            _review_revision(
                RR_2, MEMORY_A, 2, "approved", "disputed", created_at=LATER
            ),
            _review_revision(
                RR_3, MEMORY_A, 3, "disputed", "rejected", created_at=LATER
            ),
        ],
    }


def _preflight() -> UnifiedMemoryRestorePreflight:
    return UnifiedMemoryRestorePreflight(
        target_account_id=ACCOUNT_A,
        source_account_id=ACCOUNT_A,
        project_map={PROJECT_A: PROJECT_A_TARGET},
        thread_map={THREAD_A: THREAD_A_TARGET},
        message_map={MESSAGE_A: MESSAGE_A_TARGET},
        # The seven-family v6 canonical graph is opt-in; the preflight default
        # stays v4 so existing five-family callers keep their semantics.
        schema_version=REVIEW_REVISION_MANIFEST_SCHEMA_VERSION,
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


def _review_rows(connection, memory_id: str) -> list[tuple]:
    return connection.execute(
        sa.text(
            "SELECT review_revision_id, revision_number, old_review_state, "
            "new_review_state, actor_account_id, created_at "
            "FROM memory_review_revisions "
            "WHERE memory_id = :m AND user_id = :u "
            "ORDER BY revision_number ASC"
        ),
        {"m": memory_id, "u": ACCOUNT_A},
    ).fetchall()


# ---------------------------------------------------------------------------
# 1-11: clean restore, exactness, ordering, reconciliation.
# ---------------------------------------------------------------------------


def test_clean_v6_restore_persists_coherent_chain(temporary_postgres) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    plan = _plan(_valid_payload_rows())

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            _seed_sources(cur)
        conn.commit()
        result = CanonicalMemoryRestoreExecutor(plan).execute(conn)
        conn.commit()

    assert result.review_revision_created_count == 3
    assert result.review_revision_identical_count == 0

    with sa.create_engine(database_url, future=True).begin() as conn:
        rows = _review_rows(conn, MEMORY_A)
        # Stable IDs and order survive.
        assert [r[0] for r in rows] == [RR_1, RR_2, RR_3]
        assert [r[1] for r in rows] == [1, 2, 3]
        # Exact typed states.
        assert [(r[2], r[3]) for r in rows] == [
            ("pending", "approved"),
            ("approved", "disputed"),
            ("disputed", "rejected"),
        ]
        # Actor and timestamps preserved (TIMESTAMPTZ round-trips as an
        # instant; datetime equality is instant-based, so the UTC offset the
        # driver returns is equivalent).
        assert {r[4] for r in rows} == {ACCOUNT_A}
        assert rows[0][5] == datetime.fromisoformat(NOW)
        assert rows[-1][5] == datetime.fromisoformat(LATER)
        # Chain intact and reconciling with the parent's current state.
        for previous, following in zip(rows, rows[1:]):
            assert previous[3] == following[2]
        assert rows[-1][3] == "rejected"


def test_current_review_state_remains_canonical(temporary_postgres) -> None:
    """History reconciles to review_state; it never overrides it."""
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    plan = _plan(_valid_payload_rows())

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            _seed_sources(cur)
        conn.commit()
        CanonicalMemoryRestoreExecutor(plan).execute(conn)
        conn.commit()

    with sa.create_engine(database_url, future=True).begin() as conn:
        state = conn.execute(
            sa.text(
                "SELECT review_state, text_content FROM memory_records "
                "WHERE memory_id = :m"
            ),
            {"m": MEMORY_A},
        ).fetchone()
    assert state[0] == "rejected"
    # Review history did not disturb content authority or content.
    assert state[1] == EXACT_TEXT


def test_zero_review_history_restore(temporary_postgres) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    payload = _valid_payload_rows()
    payload["memory_review_revisions"] = []
    plan = _plan(payload)

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            _seed_sources(cur)
        conn.commit()
        result = CanonicalMemoryRestoreExecutor(plan).execute(conn)
        conn.commit()

    assert result.review_revision_created_count == 0
    with sa.create_engine(database_url, future=True).begin() as conn:
        total = conn.execute(
            sa.text("SELECT COUNT(*) FROM memory_review_revisions")
        ).scalar_one()
    # Absence of history is not fabricated during restore.
    assert total == 0


def test_multi_memory_review_restore(temporary_postgres) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    payload = _valid_payload_rows()
    payload["memory_records"].append(
        _memory_record("aaaaaaaa-1111-1111-1111-111111111111", review_state="approved")
    )
    payload["memory_provenance"].append(
        {
            "provenance_id": "bbbbbbbb-9999-9999-9999-999999999999",
            "memory_id": "aaaaaaaa-1111-1111-1111-111111111111",
            "user_id": ACCOUNT_A,
            "source_system": "codexify",
            "source_record_id": "second-memory",
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
    )
    payload["memory_review_revisions"].append(
        _review_revision(
            RR_B1, "aaaaaaaa-1111-1111-1111-111111111111", 1, "pending", "approved"
        )
    )
    plan = _plan(payload)

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            _seed_sources(cur)
        conn.commit()
        CanonicalMemoryRestoreExecutor(plan).execute(conn)
        conn.commit()

    with sa.create_engine(database_url, future=True).begin() as conn:
        assert len(_review_rows(conn, MEMORY_A)) == 3
        assert len(_review_rows(conn, "aaaaaaaa-1111-1111-1111-111111111111")) == 1


# ---------------------------------------------------------------------------
# 12-23: fail-closed preflight.
# ---------------------------------------------------------------------------


def test_missing_parent_fails_closed() -> None:
    payload = _valid_payload_rows()
    payload["memory_review_revisions"][0][
        "memory_id"
    ] = "99999999-9999-9999-9999-999999999999"
    with pytest.raises(UnifiedMemoryRestorePreflightError) as exc_info:
        _plan(payload)
    assert exc_info.value.code == "memory_review_revision_orphan"


def test_cross_account_review_revision_fails_closed() -> None:
    payload = _valid_payload_rows()
    payload["memory_review_revisions"][0]["user_id"] = ACCOUNT_B
    with pytest.raises(UnifiedMemoryRestorePreflightError) as exc_info:
        _plan(payload)
    assert exc_info.value.code == "memory_review_revision_account_mismatch"


def test_actor_account_mismatch_fails_closed() -> None:
    payload = _valid_payload_rows()
    payload["memory_review_revisions"][0]["actor_account_id"] = ACCOUNT_B
    with pytest.raises(UnifiedMemoryRestorePreflightError) as exc_info:
        _plan(payload)
    assert exc_info.value.code == "memory_review_revision_actor_mismatch"


def test_invalid_review_token_fails_closed() -> None:
    payload = _valid_payload_rows()
    payload["memory_review_revisions"][0]["new_review_state"] = "quarantined"
    with pytest.raises(UnifiedMemoryRestorePreflightError) as exc_info:
        _plan(payload)
    assert exc_info.value.code == "memory_review_revision_invalid_state"


def test_noop_review_transition_fails_closed() -> None:
    payload = _valid_payload_rows()
    payload["memory_review_revisions"][0]["new_review_state"] = "pending"
    with pytest.raises(UnifiedMemoryRestorePreflightError) as exc_info:
        _plan(payload)
    assert exc_info.value.code == "memory_review_revision_noop"


def test_sequence_gap_fails_closed() -> None:
    payload = _valid_payload_rows()
    payload["memory_review_revisions"] = [
        _review_revision(RR_1, MEMORY_A, 1, "pending", "approved"),
        _review_revision(RR_3, MEMORY_A, 3, "disputed", "rejected"),
    ]
    with pytest.raises(UnifiedMemoryRestorePreflightError) as exc_info:
        _plan(payload)
    assert exc_info.value.code == "memory_review_revision_sequence_gap"


def test_duplicate_sequence_fails_closed() -> None:
    payload = _valid_payload_rows()
    payload["memory_review_revisions"] = [
        _review_revision(RR_1, MEMORY_A, 1, "pending", "approved"),
        _review_revision(RR_2, MEMORY_A, 1, "approved", "disputed"),
    ]
    with pytest.raises(UnifiedMemoryRestorePreflightError) as exc_info:
        _plan(payload)
    assert exc_info.value.code == "memory_review_revision_number_conflict"


def test_duplicate_stable_id_fails_closed() -> None:
    payload = _valid_payload_rows()
    payload["memory_review_revisions"][1]["review_revision_id"] = RR_1
    with pytest.raises(UnifiedMemoryRestorePreflightError) as exc_info:
        _plan(payload)
    assert exc_info.value.code == "memory_review_revision_duplicate"


def test_invalid_review_number_fails_closed() -> None:
    payload = _valid_payload_rows()
    payload["memory_review_revisions"][0]["revision_number"] = 0
    with pytest.raises(UnifiedMemoryRestorePreflightError) as exc_info:
        _plan(payload)
    assert exc_info.value.code == "memory_review_revision_number_invalid"


def test_chain_mismatch_fails_closed() -> None:
    payload = _valid_payload_rows()
    payload["memory_review_revisions"][1]["old_review_state"] = "rejected"
    with pytest.raises(UnifiedMemoryRestorePreflightError) as exc_info:
        _plan(payload)
    assert exc_info.value.code == "memory_review_revision_chain_mismatch"


def test_final_state_mismatch_fails_closed() -> None:
    payload = _valid_payload_rows()
    payload["memory_records"][0]["review_state"] = "pending"
    with pytest.raises(UnifiedMemoryRestorePreflightError) as exc_info:
        _plan(payload)
    assert exc_info.value.code == "memory_review_revision_final_state_mismatch"


def test_personal_fact_parent_fails_closed() -> None:
    payload = _valid_payload_rows()
    payload["memory_review_revisions"][0]["memory_id"] = MEMORY_A_FACT
    with pytest.raises(UnifiedMemoryRestorePreflightError) as exc_info:
        _plan(payload)
    assert exc_info.value.code in {
        "memory_review_revision_final_state_mismatch",
        "memory_review_revision_unsupported_parent_species",
    }


def test_malformed_payload_fails_closed() -> None:
    payload = _valid_payload_rows()
    del payload["memory_review_revisions"][0]["actor_account_id"]
    with pytest.raises(UnifiedMemoryRestorePreflightError):
        _plan(payload)


def test_unadjudicated_transitions_restore_without_policy_enforcement() -> None:
    """Restore accepts pairs current architecture has not adjudicated.

    Persistence is not mutation authorization: a disputed -> approved or
    approved -> rejected history must restore without a policy check.
    """
    payload = _valid_payload_rows()
    payload["memory_records"][0]["review_state"] = "rejected"
    payload["memory_review_revisions"] = [
        _review_revision(RR_1, MEMORY_A, 1, "disputed", "approved"),
        _review_revision(RR_2, MEMORY_A, 2, "approved", "rejected"),
    ]
    plan = _plan(payload)
    assert len(plan.memory_review_revisions) == 2


# ---------------------------------------------------------------------------
# 24-28: replay and rollback.
# ---------------------------------------------------------------------------


def test_identical_replay_is_idempotent(temporary_postgres) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    plan = _plan(_valid_payload_rows())

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            _seed_sources(cur)
        conn.commit()
        first = CanonicalMemoryRestoreExecutor(plan).execute(conn)
        conn.commit()

    with psycopg.connect(database_url) as conn:
        second = CanonicalMemoryRestoreExecutor(plan).execute(conn)
        conn.commit()

    assert first.review_revision_created_count == 3
    assert second.review_revision_created_count == 0
    assert second.review_revision_identical_count == 3

    with sa.create_engine(database_url, future=True).begin() as conn:
        rows = _review_rows(conn, MEMORY_A)
        assert len(rows) == 3
        assert [r[0] for r in rows] == [RR_1, RR_2, RR_3]
        assert rows[-1][3] == "rejected"


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

    # Same stable IDs, a different but internally coherent chain, so preflight
    # passes and the executor's identity comparison is what fails.
    conflicting = deepcopy(_valid_payload_rows())
    conflicting["memory_review_revisions"] = [
        _review_revision(RR_1, MEMORY_A, 1, "pending", "disputed"),
        _review_revision(RR_2, MEMORY_A, 2, "disputed", "approved", created_at=LATER),
        _review_revision(RR_3, MEMORY_A, 3, "approved", "rejected", created_at=LATER),
    ]
    conflicting_plan = _plan(conflicting)

    with psycopg.connect(database_url) as conn:
        with pytest.raises(UnifiedMemoryRestoreConflictError):
            CanonicalMemoryRestoreExecutor(conflicting_plan).execute(conn)
        conn.rollback()

    with sa.create_engine(database_url, future=True).begin() as conn:
        rows = _review_rows(conn, MEMORY_A)
        assert len(rows) == 3
        # Original history retained; nothing overwritten.
        assert rows[0][3] == "approved"
        assert rows[-1][3] == "rejected"


def test_sequence_occupancy_conflict_fails_closed(temporary_postgres) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    plan = _plan(_valid_payload_rows())

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            _seed_sources(cur)
        conn.commit()
        CanonicalMemoryRestoreExecutor(plan).execute(conn)
        conn.commit()

    # A different stable ID tries to occupy (memory, 1).
    conflicting = deepcopy(_valid_payload_rows())
    conflicting["memory_review_revisions"][0][
        "review_revision_id"
    ] = "dddddddd-1111-1111-1111-111111111111"
    conflicting_plan = _plan(conflicting)

    with psycopg.connect(database_url) as conn:
        with pytest.raises(
            UnifiedMemoryRestoreConflictError,
            match="memory_review_revision_sequence_conflict",
        ):
            CanonicalMemoryRestoreExecutor(conflicting_plan).execute(conn)
        conn.rollback()


def test_semantic_preflight_failure_produces_zero_partial_restore(
    temporary_postgres,
) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    payload = _valid_payload_rows()
    payload["memory_review_revisions"][1]["old_review_state"] = "rejected"

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            _seed_sources(cur)
        conn.commit()
        with pytest.raises(UnifiedMemoryRestorePreflightError):
            _plan(payload)
        conn.rollback()

    with sa.create_engine(database_url, future=True).begin() as conn:
        memories = conn.execute(
            sa.text("SELECT COUNT(*) FROM memory_records")
        ).scalar_one()
        reviews = conn.execute(
            sa.text("SELECT COUNT(*) FROM memory_review_revisions")
        ).scalar_one()
    # Preflight runs before any persistence: zero partial canonical restore.
    assert memories == 0
    assert reviews == 0


def test_late_review_persistence_failure_rolls_back(temporary_postgres) -> None:
    """Force failure at the review-revision persistence stage only.

    Parent memory rows are already inserted; a review-revision INSERT failure
    must abort the whole transaction so no partial graph commits.
    """
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    plan = _plan(_valid_payload_rows())

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            _seed_sources(cur)
        conn.commit()

        executor = CanonicalMemoryRestoreExecutor(plan)

        def _boom(*args, **kwargs):
            raise RuntimeError("forced review revision persistence failure")

        executor._insert_review_revisions = _boom  # type: ignore[method-assign]
        with pytest.raises(
            RuntimeError, match="forced review revision persistence failure"
        ):
            executor.execute(conn)
        conn.rollback()

    with sa.create_engine(database_url, future=True).begin() as conn:
        memories = conn.execute(
            sa.text("SELECT COUNT(*) FROM memory_records")
        ).scalar_one()
        reviews = conn.execute(
            sa.text("SELECT COUNT(*) FROM memory_review_revisions")
        ).scalar_one()
    # Whole restore rolled back; no partial canonical graph committed.
    assert memories == 0
    assert reviews == 0
