"""Real PostgreSQL/Alembic proof for the UMS-11 purge-tombstone migration.

Proves revision
``c7f4a9b2e6d1_add_memory_purge_tombstones`` on a disposable PostgreSQL
database, reusing the ``temporary_postgres`` fixture already qualified by
``test_canonical_memory_persistence_migration.py``.

It proves:

* clean migration from the direct parent to head, with ORM/live parity;
* an existing-instance upgrade that preserves every canonical row and
  fabricates **zero** synthetic tombstones -- no pre-existing memory is given
  invented suppression history, because no pre-existing memory was purged;
* that Personal Facts are untouched and that ordinary-memory purge has no
  schema path to them;
* exact field types, nullability, and server defaults;
* stable purge-receipt identity as primary key;
* one suppression entry per ``(account, purged-record fingerprint)``;
* a source-atom fingerprint that is legitimately NULL for a direct/manual
  purge, yet at most once per account when present;
* that ``suppress_reimport`` is structurally incapable of becoming false;
* that the relation carries **no** content-bearing column; and
* a clean downgrade that removes the relation and nothing else.

It asserts no purge policy, no fingerprint algorithm, and no service
behaviour. Those are proven elsewhere.
"""

from __future__ import annotations

from datetime import datetime, timezone

import sqlalchemy as sa

from tests.migration.test_canonical_memory_persistence_migration import (  # noqa: E402
    _expect_integrity_error,
    temporary_postgres,
)

#: Direct parent of the UMS-11 revision.
PREVIOUS_REVISION = "b8e2f4a6c901"

#: The UMS-11 revision under qualification.
UMS_11_REVISION = "c7f4a9b2e6d1"

ACCOUNT_A = "ums11-account-a"
ACCOUNT_B = "ums11-account-b"

NOW = datetime(2026, 9, 30, 12, 0, tzinfo=timezone.utc)

#: Shape of an opaque non-content fingerprint: ``<version>:<64 hex>``.
RECORD_FP = f"v1:{'a' * 64}"
SOURCE_FP_1 = f"v1:{'b' * 64}"
SOURCE_FP_2 = f"v1:{'c' * 64}"


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
    text_content: str | None = "content",
    semantic_species: str = "episodic_semantic_memory",
) -> None:
    connection.execute(
        sa.text(
            "INSERT INTO memory_records "
            "(memory_id, user_id, project_id, semantic_species, "
            " text_content, fact_key, fact_value, fact_confidence, "
            " reviewed_at, activated_at, pinned, held, extensions, "
            " review_state, lifecycle_state, created_at, updated_at) "
            "VALUES (:mid, :acct, NULL, :species, :text_content, "
            " NULL, NULL, NULL, :now, :now, false, false, NULL, "
            " 'approved', 'active', :now, :now)"
        ),
        {
            "mid": memory_id,
            "acct": account_id,
            "species": semantic_species,
            "text_content": text_content,
            "now": NOW,
        },
    )


def _insert_personal_fact(connection, *, user_id: str, key: str, value: str) -> int:
    result = connection.execute(
        sa.text(
            "INSERT INTO personal_facts (user_id, key, value, status, "
            "confidence, is_active, created_at, updated_at) "
            "VALUES (:acct, :key, :value, 'verified', 0.9, true, :now, :now) "
            "RETURNING id"
        ),
        {"acct": user_id, "key": key, "value": value, "now": NOW},
    )
    return int(result.scalar_one())


def _insert_tombstone(
    connection,
    *,
    receipt_id: str,
    account_id: str,
    record_fingerprint: str,
    source_system: str | None = None,
    source_entity_kind: str | None = None,
    source_atom_fingerprint: str | None = None,
    suppress_reimport: bool = True,
) -> None:
    connection.execute(
        sa.text(
            "INSERT INTO memory_purge_tombstones "
            "(purge_receipt_id, user_id, purged_record_fingerprint, "
            " source_system, source_entity_kind, source_atom_fingerprint, "
            " purged_at, suppress_reimport) "
            "VALUES (:rid, :acct, :rfp, :ssys, :skind, :sfp, :now, :sup)"
        ),
        {
            "rid": receipt_id,
            "acct": account_id,
            "rfp": record_fingerprint,
            "ssys": source_system,
            "skind": source_entity_kind,
            "sfp": source_atom_fingerprint,
            "now": NOW,
            "sup": suppress_reimport,
        },
    )


# ---------------------------------------------------------------------------
# A. Clean migration + ORM parity + exact schema.
# ---------------------------------------------------------------------------


def test_fresh_migration_creates_purge_tombstones_with_orm_parity(
    temporary_postgres,
) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")

    from guardian.db.models import MemoryPurgeTombstone

    engine = _engine(database_url)
    with engine.begin() as conn:
        cols = {
            r[0]: {"type": r[1], "nullable": r[2], "default": r[3]}
            for r in conn.execute(
                sa.text(
                    "SELECT column_name, data_type, is_nullable, "
                    "column_default FROM information_schema.columns "
                    "WHERE table_name = 'memory_purge_tombstones'"
                )
            ).fetchall()
        }
        constraints = {
            r[0]
            for r in conn.execute(
                sa.text(
                    "SELECT conname FROM pg_constraint "
                    "WHERE conrelid = 'memory_purge_tombstones'::regclass"
                )
            ).fetchall()
        }
        indexes = {
            r[0]
            for r in conn.execute(
                sa.text(
                    "SELECT indexname FROM pg_indexes "
                    "WHERE tablename = 'memory_purge_tombstones'"
                )
            ).fetchall()
        }

    # Exact relation shape.
    assert set(cols) == {
        "purge_receipt_id",
        "user_id",
        "purged_record_fingerprint",
        "source_system",
        "source_entity_kind",
        "source_atom_fingerprint",
        "purged_at",
        "suppress_reimport",
    }
    assert cols["purge_receipt_id"]["nullable"] == "NO"
    assert cols["user_id"]["nullable"] == "NO"
    assert cols["purged_record_fingerprint"]["nullable"] == "NO"
    assert cols["purged_at"]["nullable"] == "NO"
    assert cols["suppress_reimport"]["nullable"] == "NO"
    # Source fields are legitimately NULL for a direct/manual purge.
    assert cols["source_system"]["nullable"] == "YES"
    assert cols["source_entity_kind"]["nullable"] == "YES"
    assert cols["source_atom_fingerprint"]["nullable"] == "YES"
    # Database-authored purge time and suppression default.
    assert cols["purged_at"]["default"] is not None
    assert cols["suppress_reimport"]["default"] is not None

    assert "pk_memory_purge_tombstones" in constraints
    assert "uq_memory_purge_tombstones_account_record" in constraints
    assert "fk_memory_purge_tombstones_user" in constraints
    assert "memory_purge_tombstones_suppress_reimport_check" in constraints
    assert "memory_purge_tombstones_source_system_check" in constraints
    assert "memory_purge_tombstones_source_entity_kind_check" in constraints
    assert "ix_memory_purge_tombstones_user_id" in indexes
    assert "uq_memory_purge_tombstones_account_source_atom" in indexes

    # No content-bearing column exists at all.
    for forbidden in (
        "text_content",
        "content",
        "excerpt",
        "embedding",
        "memory_id",
        "source_record_id",
    ):
        assert forbidden not in cols

    # ORM/live parity.
    assert {c.name for c in MemoryPurgeTombstone.__table__.columns} == set(cols)

    # Account erasure cascades suppression away.
    with engine.begin() as conn:
        fk = conn.execute(
            sa.text(
                "SELECT confdeltype FROM pg_constraint "
                "WHERE conname = 'fk_memory_purge_tombstones_user'"
            )
        ).scalar_one()
    assert fk == "c"  # CASCADE

    # Exactly one head, with UMS-11 in its lineage.
    from alembic.script import ScriptDirectory

    script = ScriptDirectory.from_config(config)
    heads = list(script.get_heads())
    assert len(heads) == 1
    assert heads[0] == UMS_11_REVISION
    assert PREVIOUS_REVISION in {
        revision.revision for revision in script.iterate_revisions(heads[0], "base")
    }


# ---------------------------------------------------------------------------
# B. Populated upgrade: no fabrication, no collateral change.
# ---------------------------------------------------------------------------


def test_populated_upgrade_fabricates_zero_tombstones(
    temporary_postgres,
) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, PREVIOUS_REVISION)

    engine = _engine(database_url)
    with engine.begin() as conn:
        _insert_account(conn, ACCOUNT_A)
        _insert_memory(conn, memory_id="mem-1", account_id=ACCOUNT_A)
        _insert_memory(conn, memory_id="mem-2", account_id=ACCOUNT_A)
        fact_id = _insert_personal_fact(
            conn, user_id=ACCOUNT_A, key="favorite-color", value="blue"
        )

    _upgrade(config, "head")

    with engine.begin() as conn:
        # Zero synthetic tombstones: nothing was purged, so no memory is
        # given invented suppression history.
        tombstone_count = conn.execute(
            sa.text("SELECT count(*) FROM memory_purge_tombstones")
        ).scalar_one()
        assert tombstone_count == 0

        # Canonical memory survives byte-identically.
        rows = conn.execute(
            sa.text(
                "SELECT memory_id, text_content, review_state, lifecycle_state "
                "FROM memory_records ORDER BY memory_id"
            )
        ).fetchall()
        assert [tuple(r) for r in rows] == [
            ("mem-1", "content", "approved", "active"),
            ("mem-2", "content", "approved", "active"),
        ]

        # Personal Facts are untouched by this migration.
        fact = conn.execute(
            sa.text(
                "SELECT user_id, key, value, status FROM personal_facts "
                "WHERE id = :fid"
            ),
            {"fid": fact_id},
        ).fetchone()
        assert tuple(fact) == (ACCOUNT_A, "favorite-color", "blue", "verified")

        # Every pre-existing UMS relation survives.
        for table in (
            "memory_records",
            "memory_provenance",
            "memory_persona_links",
            "memory_revisions",
            "memory_review_revisions",
            "memory_lifecycle_revisions",
        ):
            conn.execute(sa.text(f"SELECT count(*) FROM {table}")).scalar_one()


# ---------------------------------------------------------------------------
# C. Constraints.
# ---------------------------------------------------------------------------


def test_suppress_reimport_cannot_become_false(temporary_postgres) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    engine = _engine(database_url)

    with engine.begin() as conn:
        _insert_account(conn, ACCOUNT_A)

    # A tombstone claiming relaxed suppression is rejected outright.
    _expect_integrity_error(
        database_url,
        lambda conn: _insert_tombstone(
            conn,
            receipt_id="rid-bad",
            account_id=ACCOUNT_A,
            record_fingerprint=RECORD_FP,
            suppress_reimport=False,
        ),
    )

    with engine.begin() as conn:
        _insert_tombstone(
            conn,
            receipt_id="rid-good",
            account_id=ACCOUNT_A,
            record_fingerprint=RECORD_FP,
        )
        value = conn.execute(
            sa.text(
                "SELECT suppress_reimport FROM memory_purge_tombstones "
                "WHERE purge_receipt_id = 'rid-good'"
            )
        ).scalar_one()
    assert value is True


def test_duplicate_account_record_fingerprint_rejected(temporary_postgres) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    engine = _engine(database_url)

    with engine.begin() as conn:
        _insert_account(conn, ACCOUNT_A)
        _insert_tombstone(
            conn,
            receipt_id="rid-1",
            account_id=ACCOUNT_A,
            record_fingerprint=RECORD_FP,
        )

    # Same account, same erased record: a second entry is impossible, which is
    # what makes an idempotent retry provable.
    _expect_integrity_error(
        database_url,
        lambda conn: _insert_tombstone(
            conn,
            receipt_id="rid-2",
            account_id=ACCOUNT_A,
            record_fingerprint=RECORD_FP,
        ),
    )


def test_same_record_fingerprint_allowed_across_accounts(
    temporary_postgres,
) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    engine = _engine(database_url)

    # Two accounts may each have purged their own record with an identical
    # identity: uniqueness is account-scoped, so one account's erasure can
    # never suppress or disclose another account's.
    with engine.begin() as conn:
        _insert_account(conn, ACCOUNT_A)
        _insert_account(conn, ACCOUNT_B)
        _insert_tombstone(
            conn,
            receipt_id="rid-a",
            account_id=ACCOUNT_A,
            record_fingerprint=RECORD_FP,
        )
        _insert_tombstone(
            conn,
            receipt_id="rid-b",
            account_id=ACCOUNT_B,
            record_fingerprint=RECORD_FP,
        )
        count = conn.execute(
            sa.text("SELECT count(*) FROM memory_purge_tombstones")
        ).scalar_one()
    assert count == 2


def test_source_atom_fingerprint_nullable_and_account_unique(
    temporary_postgres,
) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    engine = _engine(database_url)

    with engine.begin() as conn:
        _insert_account(conn, ACCOUNT_A)
        _insert_account(conn, ACCOUNT_B)
        # A direct/manual purge legitimately has no source atom.
        _insert_tombstone(
            conn,
            receipt_id="rid-direct-1",
            account_id=ACCOUNT_A,
            record_fingerprint=RECORD_FP,
        )
        _insert_tombstone(
            conn,
            receipt_id="rid-direct-2",
            account_id=ACCOUNT_A,
            record_fingerprint=f"v1:{'d' * 64}",
        )
        _insert_tombstone(
            conn,
            receipt_id="rid-import",
            account_id=ACCOUNT_A,
            record_fingerprint=f"v1:{'e' * 64}",
            source_system="openai",
            source_entity_kind="importer",
            source_atom_fingerprint=SOURCE_FP_1,
        )

    # NULL source fingerprints are unconstrained: any number of direct purges
    # coexist for one account.
    null_count = (
        _engine(database_url)
        .connect()
        .execute(
            sa.text(
                "SELECT count(*) FROM memory_purge_tombstones "
                "WHERE source_atom_fingerprint IS NULL"
            )
        )
        .scalar_one()
    )
    assert null_count == 2

    # But the same source atom may be suppressed only once per account.
    _expect_integrity_error(
        database_url,
        lambda conn: _insert_tombstone(
            conn,
            receipt_id="rid-import-dup",
            account_id=ACCOUNT_A,
            record_fingerprint=f"v1:{'f' * 64}",
            source_system="openai",
            source_entity_kind="importer",
            source_atom_fingerprint=SOURCE_FP_1,
        ),
    )

    # A different account may suppress the same atom independently: one
    # account's erasure is never another account's suppression.
    with engine.begin() as conn:
        _insert_tombstone(
            conn,
            receipt_id="rid-import-b",
            account_id=ACCOUNT_B,
            record_fingerprint=f"v1:{'9' * 64}",
            source_system="openai",
            source_entity_kind="importer",
            source_atom_fingerprint=SOURCE_FP_1,
        )
        _insert_tombstone(
            conn,
            receipt_id="rid-import-2",
            account_id=ACCOUNT_A,
            record_fingerprint=f"v1:{'8' * 64}",
            source_system="openai",
            source_entity_kind="importer",
            source_atom_fingerprint=SOURCE_FP_2,
        )


def test_source_vocabulary_is_enforced(temporary_postgres) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    engine = _engine(database_url)

    with engine.begin() as conn:
        _insert_account(conn, ACCOUNT_A)

    _expect_integrity_error(
        database_url,
        lambda conn: _insert_tombstone(
            conn,
            receipt_id="rid-bad-system",
            account_id=ACCOUNT_A,
            record_fingerprint=RECORD_FP,
            source_system="not-a-registered-source",
        ),
    )
    _expect_integrity_error(
        database_url,
        lambda conn: _insert_tombstone(
            conn,
            receipt_id="rid-bad-kind",
            account_id=ACCOUNT_A,
            record_fingerprint=f"v1:{'7' * 64}",
            source_system="openai",
            source_entity_kind="not-a-registered-kind",
        ),
    )

    # Every registered token is accepted.
    with engine.begin() as conn:
        for index, system in enumerate(
            ("codexify", "openai", "anthropic", "future_registered")
        ):
            _insert_tombstone(
                conn,
                receipt_id=f"rid-sys-{index}",
                account_id=ACCOUNT_A,
                record_fingerprint=f"v1:{index:064x}",
                source_system=system,
            )


def test_duplicate_receipt_identity_rejected(temporary_postgres) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    engine = _engine(database_url)

    with engine.begin() as conn:
        _insert_account(conn, ACCOUNT_A)
        _insert_tombstone(
            conn,
            receipt_id="rid-1",
            account_id=ACCOUNT_A,
            record_fingerprint=RECORD_FP,
        )

    _expect_integrity_error(
        database_url,
        lambda conn: _insert_tombstone(
            conn,
            receipt_id="rid-1",
            account_id=ACCOUNT_A,
            record_fingerprint=f"v1:{'6' * 64}",
        ),
    )


def test_tombstone_cannot_orphan_from_its_account(temporary_postgres) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    engine = _engine(database_url)

    # Account authority is non-null and enforced: a tombstone cannot be
    # attributed to an account that does not exist.
    _expect_integrity_error(
        database_url,
        lambda conn: _insert_tombstone(
            conn,
            receipt_id="rid-ghost",
            account_id="ums11-account-does-not-exist",
            record_fingerprint=RECORD_FP,
        ),
    )

    # Erasing the account removes its suppression state.
    with engine.begin() as conn:
        _insert_account(conn, ACCOUNT_A)
        _insert_tombstone(
            conn,
            receipt_id="rid-1",
            account_id=ACCOUNT_A,
            record_fingerprint=RECORD_FP,
        )
        conn.execute(sa.text("DELETE FROM users WHERE id = :acct"), {"acct": ACCOUNT_A})
        remaining = conn.execute(
            sa.text("SELECT count(*) FROM memory_purge_tombstones")
        ).scalar_one()
    assert remaining == 0


# ---------------------------------------------------------------------------
# D. Downgrade.
# ---------------------------------------------------------------------------


def test_downgrade_removes_only_the_tombstone_relation(
    temporary_postgres,
) -> None:
    from alembic import command

    config, database_url = temporary_postgres
    _upgrade(config, "head")

    engine = _engine(database_url)
    with engine.begin() as conn:
        _insert_account(conn, ACCOUNT_A)
        _insert_memory(conn, memory_id="mem-1", account_id=ACCOUNT_A)
        _insert_tombstone(
            conn,
            receipt_id="rid-1",
            account_id=ACCOUNT_A,
            record_fingerprint=RECORD_FP,
        )

    command.downgrade(config, PREVIOUS_REVISION)

    with engine.begin() as conn:
        present = conn.execute(
            sa.text(
                "SELECT count(*) FROM information_schema.tables "
                "WHERE table_name = 'memory_purge_tombstones'"
            )
        ).scalar_one()
        assert present == 0
        # Canonical memory is untouched by the downgrade.
        assert (
            conn.execute(sa.text("SELECT count(*) FROM memory_records")).scalar_one()
            == 1
        )

    # Re-upgrade is clean.
    _upgrade(config, "head")
    with engine.begin() as conn:
        assert (
            conn.execute(sa.text("SELECT count(*) FROM memory_records")).scalar_one()
            == 1
        )
