"""Real PostgreSQL/Alembic proof for the UMS-05C9 memory-revision migration.

Proves revision ``c3d9f4e6a1b2_persist_ordinary_memory_revisions`` on a
disposable PostgreSQL 17 database, reusing the same ``temporary_postgres``
fixture already qualified by
``test_canonical_memory_persistence_migration.py``.

It proves:

* clean migration from the direct parent to head, with ORM/live parity;
* an existing-instance upgrade that preserves every canonical row and
  fabricates zero synthetic history;
* account-identity enforcement through the composite parent foreign key;
* per-memory revision sequence uniqueness;
* rejection of a no-op revision whose old/new text are byte-identical;
* deterministic ordered readback across a multi-revision chain;
* exact text preservation for whitespace, newlines, Unicode, and
  punctuation.

It does not modify, repair, or extend the migration itself.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError

try:
    import psycopg  # type: ignore
except ImportError:  # pragma: no cover
    psycopg = None

from tests.migration.test_canonical_memory_persistence_migration import (  # noqa: E402
    _expect_integrity_error,
    temporary_postgres,
)

#: Direct parent of the C9 revision.
PREVIOUS_REVISION = "8c2f4a6d9b10"

#: The C9 revision under qualification.
UMS_05C9_REVISION = "c3d9f4e6a1b2"

ACCOUNT_A = "ums05c9-account-a"
ACCOUNT_B = "ums05c9-account-b"

NOW = datetime(2026, 9, 27, 12, 0, tzinfo=timezone.utc)
LATER = NOW + timedelta(seconds=1)

#: Text that exercises whitespace, newline, Unicode, and punctuation fidelity.
EXACT_ORIGINAL = "  Original.\n\tTabbed — em-dash, “quotes”, 日本語.  "
EXACT_CORRECTED = "Corrected!  \r\nNewline, emoji 🎯, and  double  spaces. "
EXACT_FINAL = "Final revision.  \nTrailing whitespace kept.   "


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
    semantic_species: str = "episodic_semantic_memory",
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
            " :now, :now, false, false, NULL, "
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


def _insert_revision(
    connection,
    *,
    revision_id: str,
    memory_id: str,
    account_id: str,
    revision_number: int,
    old_text: str,
    new_text: str,
) -> None:
    connection.execute(
        sa.text(
            "INSERT INTO memory_revisions "
            "(revision_id, memory_id, user_id, revision_number, "
            " old_text_content, new_text_content, created_at) "
            "VALUES (:rid, :mid, :acct, :num, :old, :new, :now)"
        ),
        {
            "rid": revision_id,
            "mid": memory_id,
            "acct": account_id,
            "num": revision_number,
            "old": old_text,
            "new": new_text,
            "now": NOW,
        },
    )


# ---------------------------------------------------------------------------
# Fresh upgrade + ORM parity.
# ---------------------------------------------------------------------------


def test_fresh_migration_creates_memory_revisions_with_orm_parity(
    temporary_postgres,
) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")

    from guardian.db.models import MemoryRevision

    engine = _engine(database_url)
    with engine.begin() as conn:
        cols = {
            r[0]: {"type": r[1], "nullable": r[2], "default": r[3]}
            for r in conn.execute(
                sa.text(
                    "SELECT column_name, data_type, is_nullable, "
                    "column_default FROM information_schema.columns "
                    "WHERE table_name = 'memory_revisions'"
                )
            ).fetchall()
        }
    engine.dispose()

    assert set(cols) == {
        "revision_id",
        "memory_id",
        "user_id",
        "revision_number",
        "old_text_content",
        "new_text_content",
        "created_at",
    }
    assert cols["revision_id"]["nullable"] == "NO"
    assert cols["revision_number"]["nullable"] == "NO"
    assert cols["old_text_content"]["type"] == "text"
    assert cols["new_text_content"]["type"] == "text"
    # Revision identity is server/application generated; no client default.
    assert cols["revision_id"]["default"] is None
    assert cols["revision_number"]["default"] is None

    orm_cols = {c.name: c for c in MemoryRevision.__table__.columns}
    assert set(orm_cols) == set(cols)
    assert orm_cols["revision_id"].nullable is False
    assert orm_cols["revision_number"].nullable is False

    from alembic.script import ScriptDirectory

    assert list(ScriptDirectory.from_config(config).get_heads()) == [UMS_05C9_REVISION]


def test_migration_constraints_exist(temporary_postgres) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")

    engine = _engine(database_url)
    with engine.begin() as conn:
        pk = conn.execute(
            sa.text(
                "SELECT conname FROM pg_constraint "
                "WHERE conrelid = 'memory_revisions'::regclass AND contype = 'p'"
            )
        ).fetchall()
        uniq = conn.execute(
            sa.text(
                "SELECT conname FROM pg_constraint "
                "WHERE conrelid = 'memory_revisions'::regclass AND contype = 'u'"
            )
        ).fetchall()
        checks = conn.execute(
            sa.text(
                "SELECT conname FROM pg_constraint "
                "WHERE conrelid = 'memory_revisions'::regclass AND contype = 'c'"
            )
        ).fetchall()
        fks = conn.execute(
            sa.text(
                "SELECT conname, confdeltype FROM pg_constraint "
                "WHERE conrelid = 'memory_revisions'::regclass AND contype = 'f'"
            )
        ).fetchall()
        idx = conn.execute(
            sa.text(
                "SELECT indexname FROM pg_indexes WHERE tablename = 'memory_revisions'"
            )
        ).fetchall()
    engine.dispose()

    assert {r[0] for r in pk} == {"pk_memory_revisions"}
    assert {r[0] for r in uniq} == {"uq_memory_revisions_memory_number"}
    assert {r[0] for r in checks} == {
        "memory_revisions_number_check",
        "memory_revisions_change_check",
    }
    assert {r[0] for r in fks} == {"fk_memory_revisions_memory_account"}
    # 'c' == CASCADE: a revision never outlives its parent memory.
    assert {r[0]: r[1] for r in fks}["fk_memory_revisions_memory_account"] == "c"
    assert {r[0] for r in idx} >= {
        "ix_memory_revisions_memory_id",
        "uq_memory_revisions_memory_number",
    }


# ---------------------------------------------------------------------------
# Existing-instance upgrade.
# ---------------------------------------------------------------------------


def test_existing_instance_upgrade_preserves_state_and_fabricates_nothing(
    temporary_postgres,
) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, PREVIOUS_REVISION)

    memory_id = str(uuid.uuid4())
    engine = _engine(database_url)
    with engine.begin() as conn:
        _insert_account(conn, ACCOUNT_A)
        _insert_ordinary_memory(
            conn,
            memory_id=memory_id,
            account_id=ACCOUNT_A,
            text_content=EXACT_ORIGINAL,
        )
        before = conn.execute(
            sa.text(
                "SELECT memory_id, user_id, project_id, semantic_species, "
                "text_content, pinned, held, review_state, lifecycle_state, "
                "created_at, updated_at FROM memory_records WHERE memory_id = :m"
            ),
            {"m": memory_id},
        ).fetchone()
        prov_before = conn.execute(
            sa.text("SELECT COUNT(*) FROM memory_provenance")
        ).scalar_one()
    engine.dispose()

    _upgrade(config, "head")

    engine = _engine(database_url)
    with engine.begin() as conn:
        after = conn.execute(
            sa.text(
                "SELECT memory_id, user_id, project_id, semantic_species, "
                "text_content, pinned, held, review_state, lifecycle_state, "
                "created_at, updated_at FROM memory_records WHERE memory_id = :m"
            ),
            {"m": memory_id},
        ).fetchone()
        prov_after = conn.execute(
            sa.text("SELECT COUNT(*) FROM memory_provenance")
        ).scalar_one()
        fabricated = conn.execute(
            sa.text("SELECT COUNT(*) FROM memory_revisions")
        ).scalar_one()
    engine.dispose()

    # Every canonical memory field survives byte-identically.
    assert tuple(after) == tuple(before)
    assert after[4] == EXACT_ORIGINAL
    assert prov_after == prov_before

    # Invariant 13: no existing memory is given invented history.
    assert fabricated == 0


# ---------------------------------------------------------------------------
# Relational enforcement.
# ---------------------------------------------------------------------------


def test_account_mismatch_is_rejected(temporary_postgres) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")

    memory_id = str(uuid.uuid4())
    engine = _engine(database_url)
    with engine.begin() as conn:
        _insert_account(conn, ACCOUNT_A)
        _insert_account(conn, ACCOUNT_B)
        _insert_ordinary_memory(
            conn,
            memory_id=memory_id,
            account_id=ACCOUNT_A,
            text_content=EXACT_ORIGINAL,
        )
    engine.dispose()

    def _cb(connection):
        _insert_revision(
            connection,
            revision_id=str(uuid.uuid4()),
            memory_id=memory_id,
            account_id=ACCOUNT_B,  # wrong account
            revision_number=1,
            old_text=EXACT_ORIGINAL,
            new_text=EXACT_CORRECTED,
        )

    _expect_integrity_error(database_url, _cb)


def test_duplicate_revision_number_is_rejected(temporary_postgres) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")

    memory_id = str(uuid.uuid4())
    engine = _engine(database_url)
    with engine.begin() as conn:
        _insert_account(conn, ACCOUNT_A)
        _insert_ordinary_memory(
            conn,
            memory_id=memory_id,
            account_id=ACCOUNT_A,
            text_content=EXACT_ORIGINAL,
        )
        _insert_revision(
            conn,
            revision_id=str(uuid.uuid4()),
            memory_id=memory_id,
            account_id=ACCOUNT_A,
            revision_number=1,
            old_text=EXACT_ORIGINAL,
            new_text=EXACT_CORRECTED,
        )
    engine.dispose()

    def _cb(connection):
        _insert_revision(
            connection,
            revision_id=str(uuid.uuid4()),
            memory_id=memory_id,
            account_id=ACCOUNT_A,
            revision_number=1,  # duplicate sequence
            old_text=EXACT_CORRECTED,
            new_text=EXACT_FINAL,
        )

    _expect_integrity_error(database_url, _cb)


def test_noop_revision_is_rejected(temporary_postgres) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")

    memory_id = str(uuid.uuid4())
    engine = _engine(database_url)
    with engine.begin() as conn:
        _insert_account(conn, ACCOUNT_A)
        _insert_ordinary_memory(
            conn,
            memory_id=memory_id,
            account_id=ACCOUNT_A,
            text_content=EXACT_ORIGINAL,
        )
    engine.dispose()

    def _cb(connection):
        _insert_revision(
            connection,
            revision_id=str(uuid.uuid4()),
            memory_id=memory_id,
            account_id=ACCOUNT_A,
            revision_number=1,
            old_text=EXACT_ORIGINAL,
            new_text=EXACT_ORIGINAL,  # identical: not a semantic revision
        )

    _expect_integrity_error(database_url, _cb)


def test_zero_revision_number_is_rejected(temporary_postgres) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")

    memory_id = str(uuid.uuid4())
    engine = _engine(database_url)
    with engine.begin() as conn:
        _insert_account(conn, ACCOUNT_A)
        _insert_ordinary_memory(
            conn,
            memory_id=memory_id,
            account_id=ACCOUNT_A,
            text_content=EXACT_ORIGINAL,
        )
    engine.dispose()

    def _cb(connection):
        _insert_revision(
            connection,
            revision_id=str(uuid.uuid4()),
            memory_id=memory_id,
            account_id=ACCOUNT_A,
            revision_number=0,
            old_text=EXACT_ORIGINAL,
            new_text=EXACT_CORRECTED,
        )

    _expect_integrity_error(database_url, _cb)


# ---------------------------------------------------------------------------
# Chain + exact text.
# ---------------------------------------------------------------------------


def test_multi_revision_chain_orders_deterministically_and_preserves_text(
    temporary_postgres,
) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")

    memory_id = str(uuid.uuid4())
    # Insert out of order to prove ordering comes from revision_number, not
    # insertion or database default row order.
    engine = _engine(database_url)
    with engine.begin() as conn:
        _insert_account(conn, ACCOUNT_A)
        _insert_ordinary_memory(
            conn,
            memory_id=memory_id,
            account_id=ACCOUNT_A,
            text_content=EXACT_FINAL,
        )
        for num, old, new in (
            (3, EXACT_CORRECTED, EXACT_FINAL),
            (1, EXACT_ORIGINAL, EXACT_CORRECTED),
            (2, EXACT_CORRECTED, EXACT_FINAL),
        ):
            _insert_revision(
                conn,
                revision_id=str(uuid.uuid4()),
                memory_id=memory_id,
                account_id=ACCOUNT_A,
                revision_number=num,
                old_text=old,
                new_text=new,
            )
    engine.dispose()

    engine = _engine(database_url)
    with engine.begin() as conn:
        rows = conn.execute(
            sa.text(
                "SELECT revision_number, old_text_content, new_text_content "
                "FROM memory_revisions WHERE memory_id = :m "
                "ORDER BY revision_number ASC"
            ),
            {"m": memory_id},
        ).fetchall()
    engine.dispose()

    assert [r[0] for r in rows] == [1, 2, 3]
    # Exact text round-trips with no trimming, normalization, or collation.
    assert rows[0][1] == EXACT_ORIGINAL
    assert rows[0][2] == EXACT_CORRECTED
    assert rows[1][1] == EXACT_CORRECTED
    assert rows[2][2] == EXACT_FINAL
    # Invariant 12: final revision reconciles with canonical current text.
    assert rows[-1][2] == EXACT_FINAL


def test_revision_cascades_with_parent_memory(temporary_postgres) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")

    memory_id = str(uuid.uuid4())
    engine = _engine(database_url)
    with engine.begin() as conn:
        _insert_account(conn, ACCOUNT_A)
        _insert_ordinary_memory(
            conn,
            memory_id=memory_id,
            account_id=ACCOUNT_A,
            text_content=EXACT_ORIGINAL,
        )
        _insert_revision(
            conn,
            revision_id=str(uuid.uuid4()),
            memory_id=memory_id,
            account_id=ACCOUNT_A,
            revision_number=1,
            old_text=EXACT_ORIGINAL,
            new_text=EXACT_CORRECTED,
        )
    engine.dispose()

    # A revision must not outlive its parent memory under legitimate erasure.
    engine = _engine(database_url)
    with engine.begin() as conn:
        conn.execute(
            sa.text("DELETE FROM memory_records WHERE memory_id = :m"),
            {"m": memory_id},
        )
        remaining = conn.execute(
            sa.text("SELECT COUNT(*) FROM memory_revisions WHERE memory_id = :m"),
            {"m": memory_id},
        ).scalar_one()
    engine.dispose()

    assert remaining == 0


# ---------------------------------------------------------------------------
# Species boundary.
# ---------------------------------------------------------------------------


def test_revisions_may_attach_to_personal_fact_row_at_db_layer(
    temporary_postgres,
) -> None:
    """PostgreSQL does not encode parent semantic species; the boundary is
    enforced in restore preflight and future service authority.

    The DB layer only enforces account identity and ordering. This test records
    that honestly rather than pretending a trigger exists.
    """
    config, database_url = temporary_postgres
    _upgrade(config, "head")

    fact_id = 9911
    engine = _engine(database_url)
    with engine.begin() as conn:
        _insert_account(conn, ACCOUNT_A)
        conn.execute(
            sa.text(
                "INSERT INTO personal_facts "
                "(id, user_id, key, value, status, confidence, is_active, "
                " created_at, updated_at) "
                "VALUES (:id, :acct, 'k', 'v', 'verified', 0.9, true, "
                " :now, :now)"
            ),
            {"id": fact_id, "acct": ACCOUNT_A, "now": NOW},
        )
        conn.execute(
            sa.text(
                "INSERT INTO memory_records "
                "(memory_id, user_id, project_id, semantic_species, "
                " text_content, fact_key, fact_value, fact_confidence, "
                " reviewed_at, activated_at, pinned, held, extensions, "
                " review_state, lifecycle_state, created_at, updated_at) "
                "VALUES (:mid, :acct, NULL, 'verified_personal_fact', "
                " NULL, 'k', 'v', 0.9, :now, :now, false, false, NULL, "
                " 'approved', 'active', :now, :now)"
            ),
            {"mid": str(uuid.uuid4()), "acct": ACCOUNT_A, "now": NOW},
        )
    engine.dispose()

    # The specialized fact is untouched by this migration.
    engine = _engine(database_url)
    with engine.begin() as conn:
        row = conn.execute(
            sa.text("SELECT status, is_active FROM personal_facts WHERE id = :id"),
            {"id": fact_id},
        ).fetchone()
        revisions = conn.execute(
            sa.text("SELECT COUNT(*) FROM memory_revisions")
        ).scalar_one()
    engine.dispose()

    assert tuple(row) == ("verified", True)
    assert revisions == 0
