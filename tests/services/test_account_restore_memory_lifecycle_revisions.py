"""Focused account-restore proof for ordinary-memory lifecycle revisions.

UMS-05C10B-P. Uses real disposable PostgreSQL for every load-bearing case.

Proves:

* clean v7 restore writes a coherent lifecycle chain;
* stable revision IDs, exact typed old/new states, sequence, and timestamps
  survive;
* the parent ``lifecycle_state`` remains present-state authority and history
  reconciles to it without overriding it;
* **pre-retirement posture survives the round trip**: ``active -> retired``
  and ``dormant -> retired`` remain distinguishable after restore, which is
  the obligation C10B-R identified;
* a currently-retired memory with no history stays zero-history — restore
  fabricates nothing, including a prior posture;
* account isolation, and fail-closed behavior for orphan parent, cross
  account, invalid token, no-op history, sequence gap, duplicate sequence,
  duplicate stable ID, chain mismatch, final-state mismatch, specialized
  Personal Fact parent, and malformed payload;
* replay is idempotent, and semantic plus sequence-occupancy conflicts and a
  late persistence failure roll back.

It implements no retire/restore action and asserts no lifecycle transition
policy.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any

import psycopg
import pytest
import sqlalchemy as sa

from guardian.services.account_export import LIFECYCLE_REVISION_MANIFEST_SCHEMA_VERSION
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
MEMORY_A = "55555555-5555-5555-5555-555555555555"
MEMORY_B = "66666666-6666-6666-6666-666666666666"
MEMORY_A_FACT = "77777777-7777-7777-7777-777777777777"
SUBJECT_A = "88888888-8888-8888-8888-888888888888"
NOW = "2026-09-29T10:00:00+00:00"
LATER = "2026-09-29T11:00:00+00:00"

LCR_1 = "eeeeeeee-1111-1111-1111-111111111111"
LCR_2 = "eeeeeeee-2222-2222-2222-222222222222"
LCR_B1 = "eeeeeeee-3333-3333-3333-333333333333"


def _memory_row(
    memory_id: str,
    *,
    lifecycle_state: str,
    species: str = "episodic_semantic_memory",
) -> dict[str, Any]:
    return {
        "memory_id": memory_id,
        "user_id": ACCOUNT_A,
        "project_id": PROJECT_A if species == "episodic_semantic_memory" else None,
        "semantic_species": species,
        "text_content": ("content" if species == "episodic_semantic_memory" else None),
        "fact_key": None if species == "episodic_semantic_memory" else "preferred_mode",
        "fact_value": (
            None if species == "episodic_semantic_memory" else "local-first"
        ),
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


def _lifecycle_row(
    lifecycle_revision_id: str,
    memory_id: str,
    number: int,
    old: str,
    new: str,
    *,
    account: str = ACCOUNT_A,
    created_at: str = NOW,
) -> dict[str, Any]:
    return {
        "lifecycle_revision_id": lifecycle_revision_id,
        "memory_id": memory_id,
        "user_id": account,
        "revision_number": number,
        "old_lifecycle_state": old,
        "new_lifecycle_state": new,
        "created_at": created_at,
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
            _memory_row(MEMORY_A, lifecycle_state="retired"),
            _memory_row(MEMORY_B, lifecycle_state="dormant"),
            _memory_row(
                MEMORY_A_FACT,
                lifecycle_state="active",
                species="verified_personal_fact",
            ),
        ],
        "memory_persona_links": [],
        "memory_provenance": [
            _provenance_row(MEMORY_A, "99999999-9999-9999-9999-999999999999"),
            _provenance_row(MEMORY_B, "88888888-8888-8888-8888-888888888888"),
            _provenance_row(MEMORY_A_FACT, "aaaaaaaa-9999-9999-9999-999999999999"),
        ],
        "memory_revisions": [],
        "memory_review_revisions": [],
        "memory_lifecycle_revisions": [
            _lifecycle_row(LCR_1, MEMORY_A, 1, "active", "retired"),
        ],
    }


def _preflight() -> UnifiedMemoryRestorePreflight:
    return UnifiedMemoryRestorePreflight(
        target_account_id=ACCOUNT_A,
        source_account_id=ACCOUNT_A,
        project_map={PROJECT_A: PROJECT_A_TARGET},
        thread_map={THREAD_A: THREAD_A_TARGET},
        message_map={MESSAGE_A: MESSAGE_A_TARGET},
        # The eight-family v7 canonical graph is opt-in.
        schema_version=LIFECYCLE_REVISION_MANIFEST_SCHEMA_VERSION,
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


def _lifecycle_rows(database_url: str, memory_id: str) -> list[tuple]:
    with sa.create_engine(database_url, future=True).begin() as conn:
        return list(
            conn.execute(
                sa.text(
                    "SELECT lifecycle_revision_id, revision_number, "
                    "old_lifecycle_state, new_lifecycle_state, created_at "
                    "FROM memory_lifecycle_revisions "
                    "WHERE memory_id = :m AND user_id = :u "
                    "ORDER BY revision_number ASC"
                ),
                {"m": memory_id, "u": ACCOUNT_A},
            ).fetchall()
        )


# ---------------------------------------------------------------------------
# 1-11: clean restore, exactness, ordering, reconciliation.
# ---------------------------------------------------------------------------


def test_clean_v7_restore_persists_coherent_chain(temporary_postgres) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    plan = _plan(_valid_payload_rows())

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            _seed_sources(cur)
        conn.commit()
        result = CanonicalMemoryRestoreExecutor(plan).execute(conn)
        conn.commit()

    assert result.lifecycle_revision_created_count == 1
    assert result.lifecycle_revision_identical_count == 0

    rows = _lifecycle_rows(database_url, MEMORY_A)
    assert len(rows) == 1
    assert rows[0][0] == LCR_1
    assert rows[0][1] == 1
    assert rows[0][2] == "active"
    assert rows[0][3] == "retired"
    # TIMESTAMPTZ round-trips as an instant; datetime equality is
    # instant-based, so the driver's session offset is equivalent.
    assert rows[0][4] == datetime.fromisoformat(NOW)

    with sa.create_engine(database_url, future=True).begin() as conn:
        state = conn.execute(
            sa.text(
                "SELECT lifecycle_state FROM memory_records " "WHERE memory_id = :m"
            ),
            {"m": MEMORY_A},
        ).scalar_one()
    # Parent lifecycle_state remains present-state authority.
    assert state == "retired"


def test_current_lifecycle_state_remains_canonical(temporary_postgres) -> None:
    """History reconciles to the parent state; it never overrides it."""
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
        row = conn.execute(
            sa.text(
                "SELECT lifecycle_state, review_state, text_content "
                "FROM memory_records WHERE memory_id = :m"
            ),
            {"m": MEMORY_A},
        ).fetchone()
    # Lifecycle history did not disturb review authority or content.
    assert row == ("retired", "approved", "content")


def test_zero_history_restore_fabricates_nothing(temporary_postgres) -> None:
    """A retired memory with no history stays retired and stays zero-history."""
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    payload = _valid_payload_rows()
    payload["memory_lifecycle_revisions"] = []
    plan = _plan(payload)

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            _seed_sources(cur)
        conn.commit()
        result = CanonicalMemoryRestoreExecutor(plan).execute(conn)
        conn.commit()

    assert result.lifecycle_revision_created_count == 0
    with sa.create_engine(database_url, future=True).begin() as conn:
        total = conn.execute(
            sa.text("SELECT COUNT(*) FROM memory_lifecycle_revisions")
        ).scalar_one()
        state = conn.execute(
            sa.text(
                "SELECT lifecycle_state FROM memory_records " "WHERE memory_id = :m"
            ),
            {"m": MEMORY_A},
        ).scalar_one()
    # No synthetic retirement, import, decay, or pre-retirement posture.
    assert total == 0
    assert state == "retired"


def test_multi_memory_lifecycle_restore(temporary_postgres) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    payload = _valid_payload_rows()
    payload["memory_lifecycle_revisions"].append(
        _lifecycle_row(LCR_B1, MEMORY_B, 1, "active", "dormant")
    )
    plan = _plan(payload)

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            _seed_sources(cur)
        conn.commit()
        CanonicalMemoryRestoreExecutor(plan).execute(conn)
        conn.commit()

    assert len(_lifecycle_rows(database_url, MEMORY_A)) == 1
    assert len(_lifecycle_rows(database_url, MEMORY_B)) == 1


# ---------------------------------------------------------------------------
# 28-30: the load-bearing pre-retirement posture round-trip.
# ---------------------------------------------------------------------------


def test_active_to_retired_survives_round_trip(temporary_postgres) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    plan = _plan(_valid_payload_rows())

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            _seed_sources(cur)
        conn.commit()
        CanonicalMemoryRestoreExecutor(plan).execute(conn)
        conn.commit()

    rows = _lifecycle_rows(database_url, MEMORY_A)
    assert rows[0][2] == "active"
    assert rows[0][3] == "retired"


def test_dormant_to_retired_survives_round_trip(temporary_postgres) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    payload = _valid_payload_rows()
    payload["memory_lifecycle_revisions"] = [
        _lifecycle_row(LCR_1, MEMORY_A, 1, "dormant", "retired")
    ]
    plan = _plan(payload)

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            _seed_sources(cur)
        conn.commit()
        CanonicalMemoryRestoreExecutor(plan).execute(conn)
        conn.commit()

    rows = _lifecycle_rows(database_url, MEMORY_A)
    assert rows[0][2] == "dormant"
    assert rows[0][3] == "retired"


def test_two_retirement_postures_remain_distinguishable_after_restore(
    temporary_postgres,
) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    payload = _valid_payload_rows()
    # MEMORY_A retired from active; MEMORY_B retired from dormant.
    payload["memory_records"][1]["lifecycle_state"] = "retired"
    payload["memory_lifecycle_revisions"] = [
        _lifecycle_row(LCR_1, MEMORY_A, 1, "active", "retired"),
        _lifecycle_row(LCR_B1, MEMORY_B, 1, "dormant", "retired"),
    ]
    plan = _plan(payload)

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            _seed_sources(cur)
        conn.commit()
        CanonicalMemoryRestoreExecutor(plan).execute(conn)
        conn.commit()

    from_active = _lifecycle_rows(database_url, MEMORY_A)[0][2]
    from_dormant = _lifecycle_rows(database_url, MEMORY_B)[0][2]
    # The two retirement postures the contract must restore differently
    # remain distinct after a full round trip.
    assert from_active == "active"
    assert from_dormant == "dormant"


# ---------------------------------------------------------------------------
# 12-22: fail-closed preflight.
# ---------------------------------------------------------------------------


def test_missing_parent_fails_closed() -> None:
    payload = _valid_payload_rows()
    payload["memory_lifecycle_revisions"][0][
        "memory_id"
    ] = "99999999-9999-9999-9999-999999999999"
    with pytest.raises(UnifiedMemoryRestorePreflightError) as exc_info:
        _plan(payload)
    assert exc_info.value.code == "memory_lifecycle_revision_orphan"


def test_cross_account_lifecycle_revision_fails_closed() -> None:
    payload = _valid_payload_rows()
    payload["memory_lifecycle_revisions"][0]["user_id"] = ACCOUNT_B
    with pytest.raises(UnifiedMemoryRestorePreflightError) as exc_info:
        _plan(payload)
    assert exc_info.value.code == "memory_lifecycle_revision_account_mismatch"


def test_invalid_lifecycle_token_fails_closed() -> None:
    payload = _valid_payload_rows()
    payload["memory_lifecycle_revisions"][0]["new_lifecycle_state"] = "archived"
    with pytest.raises(UnifiedMemoryRestorePreflightError) as exc_info:
        _plan(payload)
    assert exc_info.value.code == "memory_lifecycle_revision_invalid_state"


def test_noop_lifecycle_history_fails_closed() -> None:
    payload = _valid_payload_rows()
    payload["memory_lifecycle_revisions"][0]["new_lifecycle_state"] = "active"
    payload["memory_records"][0]["lifecycle_state"] = "active"
    with pytest.raises(UnifiedMemoryRestorePreflightError) as exc_info:
        _plan(payload)
    assert exc_info.value.code == "memory_lifecycle_revision_noop"


def test_sequence_gap_fails_closed() -> None:
    payload = _valid_payload_rows()
    payload["memory_lifecycle_revisions"] = [
        _lifecycle_row(LCR_1, MEMORY_A, 1, "active", "dormant"),
        _lifecycle_row(LCR_2, MEMORY_A, 3, "dormant", "retired"),
    ]
    payload["memory_records"][0]["lifecycle_state"] = "retired"
    with pytest.raises(UnifiedMemoryRestorePreflightError) as exc_info:
        _plan(payload)
    assert exc_info.value.code == "memory_lifecycle_revision_sequence_gap"


def test_duplicate_sequence_fails_closed() -> None:
    payload = _valid_payload_rows()
    payload["memory_lifecycle_revisions"] = [
        _lifecycle_row(LCR_1, MEMORY_A, 1, "active", "retired"),
        _lifecycle_row(LCR_2, MEMORY_A, 1, "dormant", "retired"),
    ]
    with pytest.raises(UnifiedMemoryRestorePreflightError) as exc_info:
        _plan(payload)
    assert exc_info.value.code == "memory_lifecycle_revision_number_conflict"


def test_duplicate_stable_id_fails_closed() -> None:
    payload = _valid_payload_rows()
    payload["memory_lifecycle_revisions"] = [
        _lifecycle_row(LCR_1, MEMORY_A, 1, "active", "retired"),
        _lifecycle_row(LCR_1, MEMORY_B, 1, "active", "dormant"),
    ]
    with pytest.raises(UnifiedMemoryRestorePreflightError) as exc_info:
        _plan(payload)
    assert exc_info.value.code == "memory_lifecycle_revision_duplicate"


def test_chain_mismatch_fails_closed() -> None:
    payload = _valid_payload_rows()
    payload["memory_lifecycle_revisions"] = [
        _lifecycle_row(LCR_1, MEMORY_A, 1, "active", "retired"),
        _lifecycle_row(LCR_2, MEMORY_A, 2, "active", "dormant"),
    ]
    payload["memory_records"][0]["lifecycle_state"] = "dormant"
    with pytest.raises(UnifiedMemoryRestorePreflightError) as exc_info:
        _plan(payload)
    assert exc_info.value.code == "memory_lifecycle_revision_chain_mismatch"


def test_final_state_mismatch_fails_closed() -> None:
    payload = _valid_payload_rows()
    payload["memory_records"][0]["lifecycle_state"] = "active"
    with pytest.raises(UnifiedMemoryRestorePreflightError) as exc_info:
        _plan(payload)
    assert exc_info.value.code == "memory_lifecycle_revision_final_state_mismatch"


def test_personal_fact_parent_fails_closed() -> None:
    payload = _valid_payload_rows()
    payload["memory_lifecycle_revisions"][0]["memory_id"] = MEMORY_A_FACT
    payload["memory_records"][2]["lifecycle_state"] = "retired"
    with pytest.raises(UnifiedMemoryRestorePreflightError) as exc_info:
        _plan(payload)
    assert exc_info.value.code == "memory_lifecycle_revision_unsupported_parent_species"


def test_malformed_lifecycle_payload_fails_closed() -> None:
    payload = _valid_payload_rows()
    del payload["memory_lifecycle_revisions"][0]["old_lifecycle_state"]
    with pytest.raises(UnifiedMemoryRestorePreflightError):
        _plan(payload)


def test_unadjudicated_transitions_plan_without_policy_enforcement() -> None:
    """Unequal pairs whose legality is unresolved must still plan.

    Persistence is not mutation authorization: C10B-C owns the legal
    lifecycle graph, so preflight must not enforce it.
    """
    payload = _valid_payload_rows()
    payload["memory_records"][0]["lifecycle_state"] = "retired"
    payload["memory_lifecycle_revisions"] = [
        _lifecycle_row(LCR_1, MEMORY_A, 1, "dormant", "retired"),
    ]
    plan = _plan(payload)
    assert len(plan.memory_lifecycle_revisions) == 1


# ---------------------------------------------------------------------------
# 23-27: replay, conflict, rollback.
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

    assert first.lifecycle_revision_created_count == 1
    assert second.lifecycle_revision_created_count == 0
    assert second.lifecycle_revision_identical_count == 1
    assert len(_lifecycle_rows(database_url, MEMORY_A)) == 1


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

    # Same stable ID, different semantic content, chain still coherent.
    conflicting = deepcopy(_valid_payload_rows())
    conflicting["memory_lifecycle_revisions"] = [
        _lifecycle_row(LCR_1, MEMORY_A, 1, "dormant", "retired")
    ]
    conflicting_plan = _plan(conflicting)

    with psycopg.connect(database_url) as conn:
        with pytest.raises(UnifiedMemoryRestoreConflictError):
            CanonicalMemoryRestoreExecutor(conflicting_plan).execute(conn)
        conn.rollback()

    rows = _lifecycle_rows(database_url, MEMORY_A)
    # Original history retained; nothing overwritten.
    assert len(rows) == 1
    assert rows[0][2] == "active"


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
    conflicting["memory_lifecycle_revisions"] = [
        _lifecycle_row(LCR_B1, MEMORY_A, 1, "active", "retired")
    ]
    conflicting_plan = _plan(conflicting)

    with psycopg.connect(database_url) as conn:
        with pytest.raises(
            UnifiedMemoryRestoreConflictError,
            match="memory_lifecycle_revision_sequence_conflict",
        ):
            CanonicalMemoryRestoreExecutor(conflicting_plan).execute(conn)
        conn.rollback()


def test_semantic_preflight_failure_produces_zero_partial_restore(
    temporary_postgres,
) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    payload = _valid_payload_rows()
    payload["memory_lifecycle_revisions"] = [
        _lifecycle_row(LCR_1, MEMORY_A, 1, "active", "dormant"),
        _lifecycle_row(LCR_2, MEMORY_A, 2, "active", "retired"),
    ]
    payload["memory_records"][0]["lifecycle_state"] = "retired"

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
        lifecycle = conn.execute(
            sa.text("SELECT COUNT(*) FROM memory_lifecycle_revisions")
        ).scalar_one()
    # Preflight runs before any persistence: zero partial canonical restore.
    assert memories == 0
    assert lifecycle == 0


def test_late_lifecycle_persistence_failure_rolls_back(
    temporary_postgres,
) -> None:
    """Force failure at the lifecycle-history persistence stage only."""
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    plan = _plan(_valid_payload_rows())

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            _seed_sources(cur)
        conn.commit()

        executor = CanonicalMemoryRestoreExecutor(plan)

        def _boom(*args, **kwargs):
            raise RuntimeError("forced lifecycle persistence failure")

        executor._insert_lifecycle_revisions = _boom  # type: ignore[method-assign]
        with pytest.raises(RuntimeError, match="forced lifecycle persistence failure"):
            executor.execute(conn)
        conn.rollback()

    with sa.create_engine(database_url, future=True).begin() as conn:
        memories = conn.execute(
            sa.text("SELECT COUNT(*) FROM memory_records")
        ).scalar_one()
        lifecycle = conn.execute(
            sa.text("SELECT COUNT(*) FROM memory_lifecycle_revisions")
        ).scalar_one()
    # Whole restore rolled back; no partial canonical graph committed.
    assert memories == 0
    assert lifecycle == 0
