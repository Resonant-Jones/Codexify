"""Real PostgreSQL/Alembic proof for the UMS-05C10B-P lifecycle-revision migration.

Proves revision
``b8e2f4a6c901_persist_ordinary_memory_lifecycle_revisions`` on a
disposable PostgreSQL database, reusing the ``temporary_postgres`` fixture
already qualified by
``test_canonical_memory_persistence_migration.py``.

It proves:

* clean migration from the direct parent to head, with ORM/live parity;
* an existing-instance upgrade that preserves every canonical row and
  fabricates **zero** synthetic lifecycle history;
* account-identity enforcement through the composite parent foreign key;
* typed lifecycle vocabulary acceptance and rejection;
* per-memory sequence constraints and no-op rejection;
* **transition-shape neutrality**: persistence representability is not
  runtime authorization, so unequal pairs whose legality is unresolved are
  still accepted;
* **pre-retirement posture preservation**: ``active -> retired`` and
  ``dormant -> retired`` each preserve their own old state, which is the
  fact C10B-R proved restore semantics require;
* cascade with parent erasure.

It does not modify, repair, or extend the migration itself, and it asserts
no lifecycle transition policy.
"""

from __future__ import annotations

from datetime import datetime, timezone

import sqlalchemy as sa

from tests.migration.test_canonical_memory_persistence_migration import (  # noqa: E402
    _expect_integrity_error,
    temporary_postgres,
)

#: Direct parent of the C10B-P revision.
PREVIOUS_REVISION = "a7c3e91d4b60"

#: The C10B-P revision under qualification.
UMS_05C10B_P_REVISION = "b8e2f4a6c901"

ACCOUNT_A = "ums05c10bp-account-a"
ACCOUNT_B = "ums05c10bp-account-b"

NOW = datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc)

LIFECYCLE_STATES = ("active", "dormant", "retired")


def _upgrade(config, revision: str) -> None:
    from alembic import command

    command.upgrade(config, revision)


def _engine(database_url: str):
    return sa.create_engine(database_url, future=True)


def _insert_account(connection, account_id: str) -> None:
    connection.execute(
        sa.text(
            "INSERT INTO users (id, username, password_hash, role) "
            "VALUES (:id, :username, 'not-a-real-hash', 'guest')"
        ),
        {"id": account_id, "username": account_id},
    )


def _insert_memory(
    connection,
    *,
    memory_id: str,
    account_id: str,
    lifecycle_state: str = "active",
    review_state: str = "approved",
    text_content: str | None = "content",
    semantic_species: str = "episodic_semantic_memory",
    pinned: bool = False,
    held: bool = False,
) -> None:
    connection.execute(
        sa.text(
            "INSERT INTO memory_records "
            "(memory_id, user_id, project_id, semantic_species, "
            " text_content, fact_key, fact_value, fact_confidence, "
            " reviewed_at, activated_at, pinned, held, extensions, "
            " review_state, lifecycle_state, created_at, updated_at) "
            "VALUES (:mid, :acct, NULL, :species, :text_content, "
            " NULL, NULL, NULL, :now, :now, :pinned, :held, NULL, "
            " :review_state, :lifecycle_state, :now, :now)"
        ),
        {
            "mid": memory_id,
            "acct": account_id,
            "species": semantic_species,
            "text_content": text_content,
            "pinned": pinned,
            "held": held,
            "review_state": review_state,
            "lifecycle_state": lifecycle_state,
            "now": NOW,
        },
    )


def _insert_lifecycle_revision(
    connection,
    *,
    lifecycle_revision_id: str,
    memory_id: str,
    account_id: str,
    revision_number: int,
    old_state: str,
    new_state: str,
) -> None:
    connection.execute(
        sa.text(
            "INSERT INTO memory_lifecycle_revisions "
            "(lifecycle_revision_id, memory_id, user_id, revision_number, "
            " old_lifecycle_state, new_lifecycle_state, created_at) "
            "VALUES (:lid, :mid, :acct, :num, :old, :new, :now)"
        ),
        {
            "lid": lifecycle_revision_id,
            "mid": memory_id,
            "acct": account_id,
            "num": revision_number,
            "old": old_state,
            "new": new_state,
            "now": NOW,
        },
    )


# ---------------------------------------------------------------------------
# A/D. Clean migration + ORM parity + constraints.
# ---------------------------------------------------------------------------


def test_fresh_migration_creates_memory_lifecycle_revisions_with_orm_parity(
    temporary_postgres,
) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")

    from guardian.db.models import MemoryLifecycleRevision

    engine = _engine(database_url)
    with engine.begin() as conn:
        cols = {
            r[0]: {"type": r[1], "nullable": r[2], "default": r[3]}
            for r in conn.execute(
                sa.text(
                    "SELECT column_name, data_type, is_nullable, "
                    "column_default FROM information_schema.columns "
                    "WHERE table_name = 'memory_lifecycle_revisions'"
                )
            ).fetchall()
        }
        constraints = {
            r[0]
            for r in conn.execute(
                sa.text(
                    "SELECT conname FROM pg_constraint "
                    "WHERE conrelid = 'memory_lifecycle_revisions'::regclass"
                )
            ).fetchall()
        }
        indexes = {
            r[0]
            for r in conn.execute(
                sa.text(
                    "SELECT indexname FROM pg_indexes "
                    "WHERE tablename = 'memory_lifecycle_revisions'"
                )
            ).fetchall()
        }
        fk = conn.execute(
            sa.text(
                "SELECT confdeltype FROM pg_constraint "
                "WHERE conname = "
                "'fk_memory_lifecycle_revisions_memory_account'"
            )
        ).scalar_one()
    engine.dispose()

    assert set(cols) == {
        "lifecycle_revision_id",
        "memory_id",
        "user_id",
        "revision_number",
        "old_lifecycle_state",
        "new_lifecycle_state",
        "created_at",
    }
    for column in cols.values():
        assert column["nullable"] == "NO"
    # Identity and sequence are server/application supplied.
    assert cols["lifecycle_revision_id"]["default"] is None
    assert cols["revision_number"]["default"] is None
    assert cols["created_at"]["type"] == "timestamp with time zone"
    # Append-only historical rows: no mutable updated_at.
    assert "updated_at" not in cols
    # Deliberately absent: intent/source/actor evidence lives in the receipt
    # layer, not in revision authority.
    for absent in ("actor_account_id", "reason", "request_ref", "action"):
        assert absent not in cols

    orm_cols = {c.name: c for c in MemoryLifecycleRevision.__table__.columns}
    assert set(orm_cols) == set(cols)
    for column in orm_cols.values():
        assert column.nullable is False

    assert {
        "pk_memory_lifecycle_revisions",
        "uq_memory_lifecycle_revisions_memory_number",
        "fk_memory_lifecycle_revisions_memory_account",
        "memory_lifecycle_revisions_number_check",
        "memory_lifecycle_revisions_old_state_check",
        "memory_lifecycle_revisions_new_state_check",
        "memory_lifecycle_revisions_change_check",
    } <= constraints
    assert "ix_memory_lifecycle_revisions_memory_id" in indexes
    # "c" == CASCADE: history may not outlive parent erasure.
    assert fk == "c"

    from alembic.script import ScriptDirectory

    # UMS-11 adds a descendant migration, so the repository no longer
    # terminates at C10B-P. Assert the topology instead of a terminal value:
    # there is exactly one head, and C10B-P is in its intentional lineage.
    script = ScriptDirectory.from_config(config)
    heads = list(script.get_heads())
    assert len(heads) == 1
    assert UMS_05C10B_P_REVISION in {
        revision.revision for revision in script.iterate_revisions(heads[0], "base")
    }
    assert PREVIOUS_REVISION in {
        revision.revision for revision in script.iterate_revisions(heads[0], "base")
    }


# ---------------------------------------------------------------------------
# B/C. Populated upgrade: zero synthetic history, full preservation.
# ---------------------------------------------------------------------------


def test_populated_upgrade_creates_zero_synthetic_history(
    temporary_postgres,
) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, PREVIOUS_REVISION)

    engine = _engine(database_url)
    with engine.begin() as conn:
        _insert_account(conn, ACCOUNT_A)
        _insert_memory(
            conn,
            memory_id="lifecycle-active",
            account_id=ACCOUNT_A,
            lifecycle_state="active",
        )
        _insert_memory(
            conn,
            memory_id="lifecycle-dormant",
            account_id=ACCOUNT_A,
            lifecycle_state="dormant",
        )
        _insert_memory(
            conn,
            memory_id="lifecycle-retired",
            account_id=ACCOUNT_A,
            lifecycle_state="retired",
        )
        # A memory carrying content and review history before the upgrade.
        _insert_memory(
            conn,
            memory_id="lifecycle-with-history",
            account_id=ACCOUNT_A,
            lifecycle_state="active",
            text_content="  spaced text  ",
            pinned=True,
            held=True,
        )
        conn.execute(
            sa.text(
                "INSERT INTO memory_revisions "
                "(revision_id, memory_id, user_id, revision_number, "
                " old_text_content, new_text_content, created_at) "
                "VALUES ('cr-1', 'lifecycle-with-history', :acct, 1, "
                " 'a', 'b', :now)"
            ),
            {"acct": ACCOUNT_A, "now": NOW},
        )
        conn.execute(
            sa.text(
                "INSERT INTO memory_review_revisions "
                "(review_revision_id, memory_id, user_id, revision_number, "
                " old_review_state, new_review_state, actor_account_id, "
                " created_at) "
                "VALUES ('rr-1', 'lifecycle-with-history', :acct, 1, "
                " 'pending', 'approved', :acct, :now)"
            ),
            {"acct": ACCOUNT_A, "now": NOW},
        )
        conn.execute(
            sa.text(
                "INSERT INTO memory_provenance "
                "(provenance_id, memory_id, user_id, source_system, "
                " source_thread_id, source_message_id, source_import_job_id, "
                " source_export_fingerprint, source_subject_kind, "
                " source_subject_id, is_imported, created_at) "
                "VALUES ('prov-1', 'lifecycle-with-history', :acct, "
                " 'codexify', NULL, NULL, NULL, NULL, 'vault', NULL, "
                " false, :now)"
            ),
            {"acct": ACCOUNT_A, "now": NOW},
        )
        before = {
            r[0]: r[1:]
            for r in conn.execute(
                sa.text(
                    "SELECT memory_id, user_id, project_id, semantic_species, "
                    " text_content, review_state, lifecycle_state, pinned, "
                    " held, created_at, updated_at FROM memory_records"
                )
            ).fetchall()
        }

    _upgrade(config, "head")

    with engine.begin() as conn:
        total = conn.execute(
            sa.text("SELECT COUNT(*) FROM memory_lifecycle_revisions")
        ).scalar_one()
        after = {
            r[0]: r[1:]
            for r in conn.execute(
                sa.text(
                    "SELECT memory_id, user_id, project_id, semantic_species, "
                    " text_content, review_state, lifecycle_state, pinned, "
                    " held, created_at, updated_at FROM memory_records"
                )
            ).fetchall()
        }
        content_revisions = conn.execute(
            sa.text("SELECT COUNT(*) FROM memory_revisions")
        ).scalar_one()
        review_revisions = conn.execute(
            sa.text("SELECT COUNT(*) FROM memory_review_revisions")
        ).scalar_one()
        provenance = conn.execute(
            sa.text("SELECT COUNT(*) FROM memory_provenance")
        ).scalar_one()
    engine.dispose()

    # No lifecycle history is manufactured, including for the legacy retired
    # record whose pre-retirement posture was never canonically recorded.
    assert total == 0
    assert after == before
    # Row layout after the memory_id key: user_id, project_id,
    # semantic_species, text_content, review_state, lifecycle_state, ...
    assert after["lifecycle-retired"][5] == "retired"
    assert after["lifecycle-with-history"][3] == "  spaced text  "
    assert content_revisions == 1
    assert review_revisions == 1
    assert provenance == 1


# ---------------------------------------------------------------------------
# E. Account integrity.
# ---------------------------------------------------------------------------


def test_lifecycle_revision_requires_matching_parent_account(
    temporary_postgres,
) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    engine = _engine(database_url)
    with engine.begin() as conn:
        _insert_account(conn, ACCOUNT_A)
        _insert_account(conn, ACCOUNT_B)
        _insert_memory(conn, memory_id="acct-a-memory", account_id=ACCOUNT_A)

    def _cb(connection):
        _insert_lifecycle_revision(
            connection,
            lifecycle_revision_id="cross-account",
            memory_id="acct-a-memory",
            account_id=ACCOUNT_B,
            revision_number=1,
            old_state="active",
            new_state="retired",
        )

    _expect_integrity_error(database_url, _cb)
    engine.dispose()


def test_lifecycle_revision_requires_existing_parent(temporary_postgres) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    engine = _engine(database_url)
    with engine.begin() as conn:
        _insert_account(conn, ACCOUNT_A)

    def _cb(connection):
        _insert_lifecycle_revision(
            connection,
            lifecycle_revision_id="orphan",
            memory_id="no-such-memory",
            account_id=ACCOUNT_A,
            revision_number=1,
            old_state="active",
            new_state="retired",
        )

    _expect_integrity_error(database_url, _cb)
    engine.dispose()


# ---------------------------------------------------------------------------
# F. Token validity.
# ---------------------------------------------------------------------------


def test_valid_lifecycle_tokens_are_accepted(temporary_postgres) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    engine = _engine(database_url)
    with engine.begin() as conn:
        _insert_account(conn, ACCOUNT_A)
        _insert_memory(conn, memory_id="vocab-memory", account_id=ACCOUNT_A)
        for index, (old_state, new_state) in enumerate(
            [
                ("active", "dormant"),
                ("dormant", "active"),
                ("active", "retired"),
                ("dormant", "retired"),
                ("retired", "active"),
                ("retired", "dormant"),
            ],
            start=1,
        ):
            _insert_lifecycle_revision(
                conn,
                lifecycle_revision_id=f"vocab-{index}",
                memory_id="vocab-memory",
                account_id=ACCOUNT_A,
                revision_number=index,
                old_state=old_state,
                new_state=new_state,
            )
    engine.dispose()


def test_invalid_lifecycle_token_is_rejected(temporary_postgres) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    engine = _engine(database_url)
    with engine.begin() as conn:
        _insert_account(conn, ACCOUNT_A)
        _insert_memory(conn, memory_id="bad-token-memory", account_id=ACCOUNT_A)

    def _cb(connection):
        _insert_lifecycle_revision(
            connection,
            lifecycle_revision_id="bad-token",
            memory_id="bad-token-memory",
            account_id=ACCOUNT_A,
            revision_number=1,
            old_state="archived",
            new_state="active",
        )

    _expect_integrity_error(database_url, _cb)
    engine.dispose()


# ---------------------------------------------------------------------------
# G. Sequence constraints.
# ---------------------------------------------------------------------------


def test_duplicate_lifecycle_revision_number_is_rejected(
    temporary_postgres,
) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    engine = _engine(database_url)
    with engine.begin() as conn:
        _insert_account(conn, ACCOUNT_A)
        _insert_memory(conn, memory_id="dup-memory", account_id=ACCOUNT_A)
        _insert_lifecycle_revision(
            conn,
            lifecycle_revision_id="dup-1",
            memory_id="dup-memory",
            account_id=ACCOUNT_A,
            revision_number=1,
            old_state="active",
            new_state="retired",
        )

    def _cb(connection):
        _insert_lifecycle_revision(
            connection,
            lifecycle_revision_id="dup-2",
            memory_id="dup-memory",
            account_id=ACCOUNT_A,
            revision_number=1,
            old_state="dormant",
            new_state="retired",
        )

    _expect_integrity_error(database_url, _cb)
    engine.dispose()


def test_non_positive_lifecycle_revision_number_is_rejected(
    temporary_postgres,
) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    engine = _engine(database_url)
    with engine.begin() as conn:
        _insert_account(conn, ACCOUNT_A)
        _insert_memory(conn, memory_id="num-memory", account_id=ACCOUNT_A)

    for number in (0, -1):

        def _cb(connection, number=number):
            _insert_lifecycle_revision(
                connection,
                lifecycle_revision_id=f"num-{number}",
                memory_id="num-memory",
                account_id=ACCOUNT_A,
                revision_number=number,
                old_state="active",
                new_state="retired",
            )

        _expect_integrity_error(database_url, _cb)
    engine.dispose()


# ---------------------------------------------------------------------------
# H. No-op history.
# ---------------------------------------------------------------------------


def test_noop_lifecycle_transition_is_rejected(temporary_postgres) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    engine = _engine(database_url)
    with engine.begin() as conn:
        _insert_account(conn, ACCOUNT_A)
        _insert_memory(conn, memory_id="noop-memory", account_id=ACCOUNT_A)

    def _cb(connection):
        _insert_lifecycle_revision(
            connection,
            lifecycle_revision_id="noop",
            memory_id="noop-memory",
            account_id=ACCOUNT_A,
            revision_number=1,
            old_state="active",
            new_state="active",
        )

    _expect_integrity_error(database_url, _cb)
    engine.dispose()


# ---------------------------------------------------------------------------
# I. Transition-shape neutrality.
# ---------------------------------------------------------------------------


def test_persistence_representability_is_not_runtime_authorization(
    temporary_postgres,
) -> None:
    """Unequal pairs whose legality is unresolved are still representable.

    UMS-05C10B-C owns the legal lifecycle transition graph. The schema must
    not smuggle that undecided policy in, so every unequal pair of valid
    tokens is accepted here, including pairs a premature policy would likely
    have forbidden. This is a persistence-shape test, not a statement that
    any pair is a legal runtime mutation.
    """
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    engine = _engine(database_url)
    accepted = 0
    with engine.begin() as conn:
        _insert_account(conn, ACCOUNT_A)
        for index, (old_state, new_state) in enumerate(
            [
                ("active", "dormant"),
                ("active", "retired"),
                ("dormant", "active"),
                ("dormant", "retired"),
                ("retired", "active"),
                ("retired", "dormant"),
            ],
            start=1,
        ):
            memory_id = f"shape-{index}"
            _insert_memory(
                conn,
                memory_id=memory_id,
                account_id=ACCOUNT_A,
                lifecycle_state=new_state,
            )
            _insert_lifecycle_revision(
                conn,
                lifecycle_revision_id=f"shape-{index}",
                memory_id=memory_id,
                account_id=ACCOUNT_A,
                revision_number=1,
                old_state=old_state,
                new_state=new_state,
            )
            accepted += 1
    engine.dispose()

    assert accepted == 6


# ---------------------------------------------------------------------------
# J. Pre-retirement posture preservation.
# ---------------------------------------------------------------------------


def test_active_retired_preserves_pre_retirement_posture(
    temporary_postgres,
) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    engine = _engine(database_url)
    with engine.begin() as conn:
        _insert_account(conn, ACCOUNT_A)
        _insert_memory(
            conn,
            memory_id="retired-from-active",
            account_id=ACCOUNT_A,
            lifecycle_state="retired",
        )
        _insert_lifecycle_revision(
            conn,
            lifecycle_revision_id="posture-active",
            memory_id="retired-from-active",
            account_id=ACCOUNT_A,
            revision_number=1,
            old_state="active",
            new_state="retired",
        )
        old_state = conn.execute(
            sa.text(
                "SELECT old_lifecycle_state FROM memory_lifecycle_revisions "
                "WHERE lifecycle_revision_id = 'posture-active'"
            )
        ).scalar_one()
    engine.dispose()

    assert old_state == "active"


def test_dormant_retired_preserves_pre_retirement_posture(
    temporary_postgres,
) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    engine = _engine(database_url)
    with engine.begin() as conn:
        _insert_account(conn, ACCOUNT_A)
        _insert_memory(
            conn,
            memory_id="retired-from-dormant",
            account_id=ACCOUNT_A,
            lifecycle_state="retired",
        )
        _insert_lifecycle_revision(
            conn,
            lifecycle_revision_id="posture-dormant",
            memory_id="retired-from-dormant",
            account_id=ACCOUNT_A,
            revision_number=1,
            old_state="dormant",
            new_state="retired",
        )
        old_state = conn.execute(
            sa.text(
                "SELECT old_lifecycle_state FROM memory_lifecycle_revisions "
                "WHERE lifecycle_revision_id = 'posture-dormant'"
            )
        ).scalar_one()
    engine.dispose()

    # The two retirement postures remain distinguishable, which is exactly
    # the fact C10B-R proved the restore contract needs.
    assert old_state == "dormant"


# ---------------------------------------------------------------------------
# Cascade.
# ---------------------------------------------------------------------------


def test_lifecycle_history_cascades_with_parent_erasure(
    temporary_postgres,
) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    engine = _engine(database_url)
    with engine.begin() as conn:
        _insert_account(conn, ACCOUNT_A)
        _insert_memory(conn, memory_id="cascade-memory", account_id=ACCOUNT_A)
        _insert_lifecycle_revision(
            conn,
            lifecycle_revision_id="cascade-1",
            memory_id="cascade-memory",
            account_id=ACCOUNT_A,
            revision_number=1,
            old_state="active",
            new_state="retired",
        )
        conn.execute(
            sa.text("DELETE FROM memory_records WHERE memory_id = :mid"),
            {"mid": "cascade-memory"},
        )
        remaining = conn.execute(
            sa.text("SELECT COUNT(*) FROM memory_lifecycle_revisions")
        ).scalar_one()
    engine.dispose()

    # History may not outlive legitimate permanent erasure of its parent.
    assert remaining == 0
