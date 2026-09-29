"""Real PostgreSQL/Alembic proof for the UMS-05C10A-P review-revision migration.

Proves revision
``a7c3e91d4b60_persist_ordinary_memory_review_revisions`` on a disposable
PostgreSQL database, reusing the ``temporary_postgres`` fixture already
qualified by ``test_canonical_memory_persistence_migration.py``.

It proves:

* clean migration from the direct parent to head, with ORM/live parity;
* an existing-instance upgrade that preserves every canonical row and
  fabricates **zero** synthetic review history;
* account-identity enforcement through the composite parent foreign key;
* actor-account containment inside the owning account;
* typed review vocabulary rejection and acceptance;
* per-memory sequence uniqueness, contiguity floors, and no-op rejection;
* deterministic ordered readback across a multi-transition chain;
* the absence of any legal-transition graph: unequal pairs that current
  architecture has *not* adjudicated are still accepted.

It does not modify, repair, or extend the migration itself, and it does not
assert that any transition in the fixture is a legal runtime mutation.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import sqlalchemy as sa

from tests.migration.test_canonical_memory_persistence_migration import (  # noqa: E402
    _expect_integrity_error,
    temporary_postgres,
)

#: Direct parent of the C10A-P revision.
PREVIOUS_REVISION = "c3d9f4e6a1b2"

#: The C10A-P revision under qualification.
UMS_05C10A_P_REVISION = "a7c3e91d4b60"

ACCOUNT_A = "ums05c10ap-account-a"
ACCOUNT_B = "ums05c10ap-account-b"

NOW = datetime(2026, 9, 28, 12, 0, tzinfo=timezone.utc)
LATER = NOW + timedelta(seconds=1)


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


def _insert_ordinary_memory(
    connection,
    *,
    memory_id: str,
    account_id: str,
    text_content: str | None,
    review_state: str = "approved",
    lifecycle_state: str = "active",
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
            "VALUES (:mid, :acct, NULL, :species, "
            " :text_content, NULL, NULL, NULL, "
            " :now, :now, :pinned, :held, NULL, "
            " :review_state, :lifecycle_state, :now, :now)"
        ),
        {
            "mid": memory_id,
            "acct": account_id,
            "species": semantic_species,
            "text_content": text_content,
            "review_state": review_state,
            "lifecycle_state": lifecycle_state,
            "pinned": pinned,
            "held": held,
            "now": NOW,
        },
    )


def _insert_review_revision(
    connection,
    *,
    review_revision_id: str,
    memory_id: str,
    account_id: str,
    revision_number: int,
    old_state: str,
    new_state: str,
    actor_account_id: str | None = None,
    created_at: datetime = NOW,
) -> None:
    connection.execute(
        sa.text(
            "INSERT INTO memory_review_revisions "
            "(review_revision_id, memory_id, user_id, revision_number, "
            " old_review_state, new_review_state, actor_account_id, "
            " created_at) "
            "VALUES (:rid, :mid, :acct, :num, :old, :new, :actor, :now)"
        ),
        {
            "rid": review_revision_id,
            "mid": memory_id,
            "acct": account_id,
            "num": revision_number,
            "old": old_state,
            "new": new_state,
            "actor": actor_account_id or account_id,
            "now": created_at,
        },
    )


def _seed_one_memory(connection, *, memory_id: str, account_id: str) -> None:
    _insert_ordinary_memory(
        connection,
        memory_id=memory_id,
        account_id=account_id,
        text_content="  Existing content.  ",
        review_state="rejected",
    )


# ---------------------------------------------------------------------------
# A. Clean migration + ORM parity.
# ---------------------------------------------------------------------------


def test_fresh_migration_creates_memory_review_revisions_with_orm_parity(
    temporary_postgres,
) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")

    from guardian.db.models import MemoryReviewRevision

    engine = _engine(database_url)
    with engine.begin() as conn:
        cols = {
            r[0]: {"type": r[1], "nullable": r[2], "default": r[3]}
            for r in conn.execute(
                sa.text(
                    "SELECT column_name, data_type, is_nullable, "
                    "column_default FROM information_schema.columns "
                    "WHERE table_name = 'memory_review_revisions'"
                )
            ).fetchall()
        }
    engine.dispose()

    assert set(cols) == {
        "review_revision_id",
        "memory_id",
        "user_id",
        "revision_number",
        "old_review_state",
        "new_review_state",
        "actor_account_id",
        "created_at",
    }
    for column in cols.values():
        assert column["nullable"] == "NO"
    # Identity, numbering, and actor are server/application supplied.
    assert cols["review_revision_id"]["default"] is None
    assert cols["revision_number"]["default"] is None
    assert cols["actor_account_id"]["default"] is None
    # Immutable creation timestamp, no mutable updated_at.
    assert cols["created_at"]["type"] == "timestamp with time zone"
    assert "updated_at" not in cols

    orm_cols = {c.name: c for c in MemoryReviewRevision.__table__.columns}
    assert set(orm_cols) == set(cols)
    for column in orm_cols.values():
        assert column.nullable is False

    from alembic.script import ScriptDirectory

    # UMS-05C10B-P adds a descendant migration, so the repository no longer
    # terminates at C10A-P. Assert the topology instead of a terminal value:
    # there is exactly one head, and C10A-P is in its intentional lineage.
    script = ScriptDirectory.from_config(config)
    heads = list(script.get_heads())
    assert len(heads) == 1
    assert UMS_05C10A_P_REVISION in {
        revision.revision for revision in script.iterate_revisions(heads[0], "base")
    }


def test_migration_constraints_exist(temporary_postgres) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")

    engine = _engine(database_url)
    with engine.connect() as conn:
        constraints = {
            r[0]
            for r in conn.execute(
                sa.text(
                    "SELECT conname FROM pg_constraint "
                    "WHERE conrelid = 'memory_review_revisions'::regclass"
                )
            ).fetchall()
        }
        indexes = {
            r[0]
            for r in conn.execute(
                sa.text(
                    "SELECT indexname FROM pg_indexes "
                    "WHERE tablename = 'memory_review_revisions'"
                )
            ).fetchall()
        }
        fk = conn.execute(
            sa.text(
                "SELECT confdeltype FROM pg_constraint "
                "WHERE conname = "
                "'fk_memory_review_revisions_memory_account'"
            )
        ).scalar_one()
    engine.dispose()

    assert {
        "pk_memory_review_revisions",
        "uq_memory_review_revisions_memory_number",
        "fk_memory_review_revisions_memory_account",
        "memory_review_revisions_number_check",
        "memory_review_revisions_old_state_check",
        "memory_review_revisions_new_state_check",
        "memory_review_revisions_change_check",
        "memory_review_revisions_actor_account_check",
    } <= constraints
    assert "ix_memory_review_revisions_memory_id" in indexes
    # "c" == CASCADE: history may not outlive legitimate erasure of its parent.
    assert fk == "c"


# ---------------------------------------------------------------------------
# B/C. Populated parent upgrade: zero synthetic history, full preservation.
# ---------------------------------------------------------------------------


def test_populated_upgrade_creates_zero_synthetic_history(temporary_postgres) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, PREVIOUS_REVISION)

    memory_id = "ums05c10ap-zero-history-memory"
    engine = _engine(database_url)
    with engine.begin() as conn:
        _insert_account(conn, ACCOUNT_A)
        _seed_one_memory(conn, memory_id=memory_id, account_id=ACCOUNT_A)

    _upgrade(config, "head")

    with engine.begin() as conn:
        # No history is manufactured from the current review_state.
        total = conn.execute(
            sa.text("SELECT COUNT(*) FROM memory_review_revisions")
        ).scalar_one()
        assert total == 0

        row = conn.execute(
            sa.text(
                "SELECT review_state, lifecycle_state, text_content, pinned, "
                "held, updated_at FROM memory_records WHERE memory_id = :mid"
            ),
            {"mid": memory_id},
        ).fetchone()
    engine.dispose()

    # Parent canonical state is untouched by the migration.
    assert row[0] == "rejected"
    assert row[1] == "active"
    assert row[2] == "  Existing content.  "
    assert row[3] is False
    assert row[4] is False
    assert row[5] is not None


def test_existing_content_revision_and_provenance_are_untouched(
    temporary_postgres,
) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, PREVIOUS_REVISION)

    memory_id = "ums05c10ap-preserve-memory"
    engine = _engine(database_url)
    with engine.begin() as conn:
        _insert_account(conn, ACCOUNT_A)
        _seed_one_memory(conn, memory_id=memory_id, account_id=ACCOUNT_A)
        conn.execute(
            sa.text(
                "INSERT INTO memory_revisions "
                "(revision_id, memory_id, user_id, revision_number, "
                " old_text_content, new_text_content, created_at) "
                "VALUES ('rr-1', :mid, :acct, 1, 'before', 'after', :now)"
            ),
            {"mid": memory_id, "acct": ACCOUNT_A, "now": NOW},
        )
        conn.execute(
            sa.text(
                "INSERT INTO memory_provenance "
                "(provenance_id, memory_id, user_id, source_system, "
                " source_record_id, source_thread_id, source_message_id, "
                " source_import_job_id, source_export_fingerprint, "
                " source_subject_kind, source_subject_id, is_imported, "
                " extensions, created_at) "
                "VALUES ('prov-1', :mid, :acct, 'codexify', 'src-1', "
                " NULL, NULL, NULL, NULL, NULL, NULL, false, NULL, :now)"
            ),
            {"mid": memory_id, "acct": ACCOUNT_A, "now": NOW},
        )

    _upgrade(config, "head")

    with engine.begin() as conn:
        content_revision = conn.execute(
            sa.text(
                "SELECT old_text_content, new_text_content FROM "
                "memory_revisions WHERE revision_id = 'rr-1'"
            )
        ).fetchone()
        provenance = conn.execute(
            sa.text(
                "SELECT source_system, source_record_id FROM "
                "memory_provenance WHERE provenance_id = 'prov-1'"
            )
        ).fetchone()
        review_rows = conn.execute(
            sa.text("SELECT COUNT(*) FROM memory_review_revisions")
        ).scalar_one()
    engine.dispose()

    assert content_revision == ("before", "after")
    assert provenance == ("codexify", "src-1")
    assert review_rows == 0


# ---------------------------------------------------------------------------
# E. Account integrity.
# ---------------------------------------------------------------------------


def test_review_revision_requires_matching_parent_account(
    temporary_postgres,
) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    engine = _engine(database_url)
    with engine.begin() as conn:
        _insert_account(conn, ACCOUNT_A)
        _insert_account(conn, ACCOUNT_B)
        _seed_one_memory(conn, memory_id="acct-a-memory", account_id=ACCOUNT_A)

    def _cb(connection):
        _insert_review_revision(
            connection,
            review_revision_id="cross-account",
            memory_id="acct-a-memory",
            account_id=ACCOUNT_B,
            revision_number=1,
            old_state="pending",
            new_state="approved",
            actor_account_id=ACCOUNT_B,
        )

    _expect_integrity_error(database_url, _cb)
    engine.dispose()


def test_review_revision_requires_existing_parent(temporary_postgres) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    engine = _engine(database_url)
    with engine.begin() as conn:
        _insert_account(conn, ACCOUNT_A)

    def _cb(connection):
        _insert_review_revision(
            connection,
            review_revision_id="orphan",
            memory_id="no-such-memory",
            account_id=ACCOUNT_A,
            revision_number=1,
            old_state="pending",
            new_state="approved",
        )

    _expect_integrity_error(database_url, _cb)
    engine.dispose()


def test_actor_account_cannot_escape_owning_account(
    temporary_postgres,
) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    engine = _engine(database_url)
    with engine.begin() as conn:
        _insert_account(conn, ACCOUNT_A)
        _insert_account(conn, ACCOUNT_B)
        _seed_one_memory(conn, memory_id="actor-memory", account_id=ACCOUNT_A)

    def _cb(connection):
        _insert_review_revision(
            connection,
            review_revision_id="foreign-actor",
            memory_id="actor-memory",
            account_id=ACCOUNT_A,
            revision_number=1,
            old_state="pending",
            new_state="approved",
            actor_account_id=ACCOUNT_B,
        )

    _expect_integrity_error(database_url, _cb)
    engine.dispose()


# ---------------------------------------------------------------------------
# F. Review vocabulary.
# ---------------------------------------------------------------------------


def test_valid_review_tokens_are_accepted(temporary_postgres) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    engine = _engine(database_url)
    with engine.begin() as conn:
        _insert_account(conn, ACCOUNT_A)
        _seed_one_memory(conn, memory_id="vocab-memory", account_id=ACCOUNT_A)
        for index, (old_state, new_state) in enumerate(
            [
                ("pending", "approved"),
                ("approved", "disputed"),
                ("disputed", "rejected"),
                ("rejected", "pending"),
            ],
            start=1,
        ):
            _insert_review_revision(
                conn,
                review_revision_id=f"vocab-{index}",
                memory_id="vocab-memory",
                account_id=ACCOUNT_A,
                revision_number=index,
                old_state=old_state,
                new_state=new_state,
            )
    engine.dispose()


def test_invalid_review_token_is_rejected(temporary_postgres) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    engine = _engine(database_url)
    with engine.begin() as conn:
        _insert_account(conn, ACCOUNT_A)
        _seed_one_memory(conn, memory_id="bad-token-memory", account_id=ACCOUNT_A)

    def _cb(connection):
        _insert_review_revision(
            connection,
            review_revision_id="bad-token",
            memory_id="bad-token-memory",
            account_id=ACCOUNT_A,
            revision_number=1,
            old_state="pending",
            new_state="quarantined",
        )

    _expect_integrity_error(database_url, _cb)
    engine.dispose()


# ---------------------------------------------------------------------------
# No legal transition graph is encoded.
# ---------------------------------------------------------------------------


def test_unadjudicated_transition_pairs_are_accepted(temporary_postgres) -> None:
    """The database must not encode a legal-transition policy.

    Current architecture has NOT settled which review transitions are legal.
    Persistence therefore accepts these specific pairs rather than guessing:
    they are exactly the pairs a premature policy would have forbidden.
    """
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    engine = _engine(database_url)
    with engine.begin() as conn:
        _insert_account(conn, ACCOUNT_A)
        _insert_account(conn, ACCOUNT_B)
        # Unadjudicated: disputed -> approved, approved -> rejected,
        # rejected -> pending.
        _seed_one_memory(conn, memory_id="unadjudicated-a", account_id=ACCOUNT_A)
        _seed_one_memory(conn, memory_id="unadjudicated-b", account_id=ACCOUNT_B)
        _insert_review_revision(
            conn,
            review_revision_id="ua-1",
            memory_id="unadjudicated-a",
            account_id=ACCOUNT_A,
            revision_number=1,
            old_state="disputed",
            new_state="approved",
        )
        _insert_review_revision(
            conn,
            review_revision_id="ua-2",
            memory_id="unadjudicated-b",
            account_id=ACCOUNT_B,
            revision_number=1,
            old_state="approved",
            new_state="rejected",
        )
        # rejected -> pending is likewise not forbidden by persistence.
        _insert_review_revision(
            conn,
            review_revision_id="ua-3",
            memory_id="unadjudicated-a",
            account_id=ACCOUNT_A,
            revision_number=2,
            old_state="approved",
            new_state="disputed",
        )
    engine.dispose()


# ---------------------------------------------------------------------------
# G. Sequence constraints.
# ---------------------------------------------------------------------------


def test_duplicate_review_revision_number_is_rejected(
    temporary_postgres,
) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    engine = _engine(database_url)
    with engine.begin() as conn:
        _insert_account(conn, ACCOUNT_A)
        _seed_one_memory(conn, memory_id="dup-memory", account_id=ACCOUNT_A)
        _insert_review_revision(
            conn,
            review_revision_id="dup-1",
            memory_id="dup-memory",
            account_id=ACCOUNT_A,
            revision_number=1,
            old_state="pending",
            new_state="approved",
        )

    def _cb(connection):
        _insert_review_revision(
            connection,
            review_revision_id="dup-2",
            memory_id="dup-memory",
            account_id=ACCOUNT_A,
            revision_number=1,
            old_state="approved",
            new_state="rejected",
        )

    _expect_integrity_error(database_url, _cb)
    engine.dispose()


def test_non_positive_review_revision_number_is_rejected(
    temporary_postgres,
) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    engine = _engine(database_url)
    with engine.begin() as conn:
        _insert_account(conn, ACCOUNT_A)
        _seed_one_memory(conn, memory_id="num-memory", account_id=ACCOUNT_A)

    for number in (0, -1):

        def _cb(connection, number=number):
            _insert_review_revision(
                connection,
                review_revision_id=f"num-{number}",
                memory_id="num-memory",
                account_id=ACCOUNT_A,
                revision_number=number,
                old_state="pending",
                new_state="approved",
            )

        _expect_integrity_error(database_url, _cb)
    engine.dispose()


# ---------------------------------------------------------------------------
# H. No-op history.
# ---------------------------------------------------------------------------


def test_noop_review_transition_is_rejected(temporary_postgres) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    engine = _engine(database_url)
    with engine.begin() as conn:
        _insert_account(conn, ACCOUNT_A)
        _seed_one_memory(conn, memory_id="noop-memory", account_id=ACCOUNT_A)

    def _cb(connection):
        _insert_review_revision(
            connection,
            review_revision_id="noop",
            memory_id="noop-memory",
            account_id=ACCOUNT_A,
            revision_number=1,
            old_state="approved",
            new_state="approved",
        )

    _expect_integrity_error(database_url, _cb)
    engine.dispose()


# ---------------------------------------------------------------------------
# I. Multiple revisions + deterministic ordered readback.
# ---------------------------------------------------------------------------


def test_multi_transition_chain_reads_back_in_order(temporary_postgres) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    memory_id = "chain-memory"
    engine = _engine(database_url)
    with engine.begin() as conn:
        _insert_account(conn, ACCOUNT_A)
        _insert_ordinary_memory(
            conn,
            memory_id=memory_id,
            account_id=ACCOUNT_A,
            text_content="chain content",
            review_state="rejected",
        )
        for index, (old_state, new_state) in enumerate(
            [
                ("pending", "approved"),
                ("approved", "disputed"),
                ("disputed", "approved"),
                ("approved", "rejected"),
            ],
            start=1,
        ):
            _insert_review_revision(
                conn,
                review_revision_id=f"chain-{index}",
                memory_id=memory_id,
                account_id=ACCOUNT_A,
                revision_number=index,
                old_state=old_state,
                new_state=new_state,
                created_at=NOW + timedelta(seconds=index),
            )

    with engine.begin() as conn:
        rows = conn.execute(
            sa.text(
                "SELECT revision_number, old_review_state, new_review_state, "
                "actor_account_id FROM memory_review_revisions "
                "WHERE memory_id = :mid "
                "ORDER BY revision_number ASC, review_revision_id ASC"
            ),
            {"mid": memory_id},
        ).fetchall()
    engine.dispose()

    # Persistence-shape only: this does NOT declare the future writer may
    # perform every transition in this fixture.
    assert [r[0] for r in rows] == [1, 2, 3, 4]
    assert [(r[1], r[2]) for r in rows] == [
        ("pending", "approved"),
        ("approved", "disputed"),
        ("disputed", "approved"),
        ("approved", "rejected"),
    ]
    # Terminal historical state reconciles with the parent's current state.
    assert rows[-1][2] == "rejected"
    assert {r[3] for r in rows} == {ACCOUNT_A}


def test_review_history_is_account_isolated(temporary_postgres) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    engine = _engine(database_url)
    with engine.begin() as conn:
        _insert_account(conn, ACCOUNT_A)
        _insert_account(conn, ACCOUNT_B)
        _seed_one_memory(conn, memory_id="iso-a", account_id=ACCOUNT_A)
        _seed_one_memory(conn, memory_id="iso-b", account_id=ACCOUNT_B)
        _insert_review_revision(
            conn,
            review_revision_id="iso-1",
            memory_id="iso-a",
            account_id=ACCOUNT_A,
            revision_number=1,
            old_state="pending",
            new_state="approved",
        )
        _insert_review_revision(
            conn,
            review_revision_id="iso-2",
            memory_id="iso-b",
            account_id=ACCOUNT_B,
            revision_number=1,
            old_state="pending",
            new_state="rejected",
        )

    with engine.begin() as conn:
        by_account = dict(
            conn.execute(
                sa.text(
                    "SELECT user_id, COUNT(*) FROM memory_review_revisions "
                    "GROUP BY user_id"
                )
            ).fetchall()
        )
    engine.dispose()

    assert by_account == {ACCOUNT_A: 1, ACCOUNT_B: 1}


def test_review_history_cascades_with_parent_erasure(temporary_postgres) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    engine = _engine(database_url)
    with engine.begin() as conn:
        _insert_account(conn, ACCOUNT_A)
        _seed_one_memory(conn, memory_id="cascade-memory", account_id=ACCOUNT_A)
        _insert_review_revision(
            conn,
            review_revision_id="cascade-1",
            memory_id="cascade-memory",
            account_id=ACCOUNT_A,
            revision_number=1,
            old_state="pending",
            new_state="approved",
        )
        conn.execute(
            sa.text("DELETE FROM memory_records WHERE memory_id = :mid"),
            {"mid": "cascade-memory"},
        )
        remaining = conn.execute(
            sa.text("SELECT COUNT(*) FROM memory_review_revisions")
        ).scalar_one()
    engine.dispose()

    # History may not outlive legitimate permanent erasure of its parent.
    assert remaining == 0
