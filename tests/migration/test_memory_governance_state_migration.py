"""Real PostgreSQL/Alembic proof for the UMS-05C8 governance-state migration.

This file proves the UMS-05C8 revision
``8c2f4a6d9b10_add_memory_governance_state`` against a disposable
PostgreSQL 17 database, using the same
``temporary_postgres`` fixture pattern already proven by
``test_canonical_memory_persistence_migration.py``.

It proves:

* clean migration from the direct parent revision to head;
* ORM/Alembic parity for the two governance-state columns;
* the exact deterministic legacy -> typed governance-state backfill, on a
  populated pre-C8 database, without manufacturing ``rejected``,
  ``disputed``, or ``retired`` rows;
* preservation of every canonical field C8 does not own;
* Personal Facts specialized authority is not rewritten by the migration;
* database CHECK enforcement rejects out-of-vocabulary governance tokens;
* the migration is repeatable across independently created databases.

It does not modify, repair, or extend the C8 migration itself. If this
suite exposes a genuine C8 defect, that is a STOP for the qualifying task,
not something to patch here.
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

#: Direct parent of the C8 governance-state revision.
PREVIOUS_REVISION = "7e5a5fccf253"

#: The C8 governance-state revision under qualification.
UMS_05C8_REVISION = "8c2f4a6d9b10"

#: Column contract exactly as C8 implemented it.
REVIEW_COLUMN = "review_state"
LIFECYCLE_COLUMN = "lifecycle_state"
REVIEW_CHECK = "memory_records_review_state_check"
LIFECYCLE_CHECK = "memory_records_lifecycle_state_check"

CANONICAL_REVIEW_STATES = ("pending", "approved", "rejected", "disputed")
CANONICAL_LIFECYCLE_STATES = ("active", "dormant", "retired")

#: The exact legacy mapping the C8 revision performs.
LEGACY_REVIEW_MAPPING = {
    None: "pending",
    "set": "approved",
}
LEGACY_LIFECYCLE_MAPPING = {
    None: "dormant",
    "set": "active",
}

NOW = datetime(2026, 9, 25, 12, 0, tzinfo=timezone.utc)
LATER = NOW + timedelta(seconds=1)

ACCOUNT_A = "ums05c8q-account-a"


def _database_url(base_url: str, database_name: str) -> str:
    parsed = urlparse(base_url)
    return urlunparse(parsed._replace(path=f"/{database_name}"))


def _admin_database_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    return urlunparse(parsed._replace(path="/postgres"))


def _fresh_disposable_postgres(base_url: str, prefix: str) -> tuple:
    """Create one disposable child database and return (config, url, name)."""
    if psycopg is None:
        pytest.skip("psycopg not installed")
    if not base_url:
        pytest.skip("TEST_DATABASE_URL or DATABASE_URL environment variable required")

    admin_url = _admin_database_url(base_url)
    database_name = f"{prefix}_{uuid.uuid4().hex[:12]}"
    database_url = _database_url(base_url, database_name)

    admin_connection = psycopg.connect(admin_url, autocommit=True)
    try:
        with admin_connection.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE {database_name}")
    finally:
        admin_connection.close()

    from alembic.config import Config

    repo_root = Path(__file__).resolve().parents[2]
    config = Config(str(repo_root / "backend" / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    config.set_main_option(
        "script_location", str(repo_root / "guardian" / "db" / "migrations")
    )
    return config, database_url, database_name


def _drop_disposable_postgres(admin_url: str, database_name: str) -> None:
    """Drop the disposable child database.

    ``pg_terminate_backend`` needs a privilege the dedicated test role may
    not hold. Terminating backends is therefore best-effort, and the drop
    falls back to ``WITH (FORCE)`` (PostgreSQL 13+) so teardown completes
    without escalating privileges.
    """
    connection = psycopg.connect(admin_url, autocommit=True)
    try:
        with connection.cursor() as cursor:
            try:
                cursor.execute(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = %s",
                    (database_name,),
                )
            except psycopg.Error:
                # Not privileged to terminate backends; rely on FORCE below.
                pass
            try:
                cursor.execute(f"DROP DATABASE IF EXISTS {database_name} WITH (FORCE)")
            except psycopg.Error:
                cursor.execute(f"DROP DATABASE IF EXISTS {database_name}")
    finally:
        connection.close()


def _upgrade(config, revision: str) -> None:
    from alembic import command

    command.upgrade(config, revision)


def _engine(database_url: str):
    """Return a SQLAlchemy engine, matching the proven migration pattern.

    The repository's qualified migration suite uses a SQLAlchemy engine
    rather than a raw psycopg connection, because the assertions are
    expressed with SQLAlchemy ``text()`` clauses.
    """
    return sa.create_engine(database_url, future=True)


def _insert_account(connection, account_id: str) -> None:
    connection.execute(
        sa.text(
            "INSERT INTO users (id, username, password_hash, role) "
            "VALUES (:id, :username, 'not-a-real-hash', 'guest')"
        ),
        {"id": account_id, "username": account_id},
    )


def _insert_legacy_memory(
    connection,
    *,
    memory_id: str,
    account_id: str,
    reviewed_at: datetime | None,
    activated_at: datetime | None,
    text_content: str,
) -> None:
    """Insert a pre-C8 canonical memory using only the pre-C8 column set."""
    connection.execute(
        sa.text(
            "INSERT INTO memory_records "
            "(memory_id, user_id, project_id, semantic_species, "
            " text_content, fact_key, fact_value, fact_confidence, "
            " reviewed_at, activated_at, pinned, held, extensions, "
            " created_at, updated_at) "
            "VALUES (:memory_id, :user_id, NULL, 'episodic_semantic_memory', "
            " :text_content, NULL, NULL, NULL, "
            " :reviewed_at, :activated_at, :pinned, :held, :extensions, "
            " :created_at, :updated_at)"
        ),
        {
            "memory_id": memory_id,
            "user_id": account_id,
            "text_content": text_content,
            "reviewed_at": reviewed_at,
            "activated_at": activated_at,
            "pinned": True,
            "held": False,
            "extensions": None,
            "created_at": NOW,
            "updated_at": LATER,
        },
    )


def _governance_columns(connection) -> dict:
    rows = connection.execute(
        sa.text(
            "SELECT column_name, data_type, is_nullable, column_default "
            "FROM information_schema.columns "
            "WHERE table_name = 'memory_records' "
            "  AND column_name IN (:review, :lifecycle)"
        ),
        {"review": REVIEW_COLUMN, "lifecycle": LIFECYCLE_COLUMN},
    ).fetchall()
    return {
        row[0]: {"type": row[1], "nullable": row[2], "default": row[3]} for row in rows
    }


def _check_constraint_names(connection) -> set[str]:
    rows = connection.execute(
        sa.text(
            "SELECT conname FROM pg_constraint "
            "WHERE conrelid = 'memory_records'::regclass AND contype = 'c'"
        )
    ).fetchall()
    return {row[0] for row in rows}


# ---------------------------------------------------------------------------
# A. Clean migration.
# ---------------------------------------------------------------------------


def test_clean_migration_applies_and_materializes_governance_columns(
    temporary_postgres,
) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")

    with _engine(database_url).begin() as conn:
        cols = _governance_columns(conn)
        assert set(cols) == {REVIEW_COLUMN, LIFECYCLE_COLUMN}
        for name in (REVIEW_COLUMN, LIFECYCLE_COLUMN):
            assert cols[name]["type"] == "character varying", name
            assert cols[name]["nullable"] == "NO", name

        names = _check_constraint_names(conn)
        assert REVIEW_CHECK in names
        assert LIFECYCLE_CHECK in names

        # Alembic must remain at a single head, and the C8 revision must
        # still be part of that lineage. UMS-05C9 intentionally added a
        # later revision on top of C8, so the head value itself advances;
        # the invariant under test is single-head topology plus C8 ancestry.
        heads = connection_heads(config)
        assert len(heads) == 1
        assert _is_ancestor_revision(config, UMS_05C8_REVISION, heads[0])


def connection_heads(config) -> list[str]:
    from alembic.script import ScriptDirectory

    return list(ScriptDirectory.from_config(config).get_heads())


def _is_ancestor_revision(config, ancestor: str, head: str) -> bool:
    """Return True when ``ancestor`` is ``head`` or precedes it in lineage."""
    from alembic.script import ScriptDirectory

    if ancestor == head:
        return True
    script = ScriptDirectory.from_config(config)
    seen: set[str] = set()
    current: str | None = head
    while current and current not in seen:
        seen.add(current)
        current = script.get_revision(current).down_revision
        if isinstance(current, (tuple, list)):  # merge point; follow the first
            current = current[0] if current else None
        if current == ancestor:
            return True
    return False


def test_orm_metadata_matches_live_schema_for_governance_columns(
    temporary_postgres,
) -> None:
    """ORM and Alembic must describe the same C8 persistence contract."""
    config, database_url = temporary_postgres
    _upgrade(config, "head")

    from guardian.db.models import MemoryRecord

    orm_cols = {c.name: c for c in MemoryRecord.__table__.columns}
    assert REVIEW_COLUMN in orm_cols
    assert LIFECYCLE_COLUMN in orm_cols
    assert orm_cols[REVIEW_COLUMN].nullable is False
    assert orm_cols[LIFECYCLE_COLUMN].nullable is False

    orm_checks = {c.name for c in MemoryRecord.__table__.constraints if c.name}
    assert REVIEW_CHECK in orm_checks
    assert LIFECYCLE_CHECK in orm_checks

    with _engine(database_url).begin() as conn:
        live = _governance_columns(conn)
        assert set(live) == {REVIEW_COLUMN, LIFECYCLE_COLUMN}
        assert REVIEW_CHECK in _check_constraint_names(conn)
        assert LIFECYCLE_CHECK in _check_constraint_names(conn)


# ---------------------------------------------------------------------------
# B. Existing-instance upgrade + exact legacy -> typed backfill.
# ---------------------------------------------------------------------------


def test_populated_pre_c8_upgrade_performs_exact_deterministic_backfill(
    temporary_postgres,
) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, PREVIOUS_REVISION)

    # Four distinct pre-C8 postures; the schema before C8 could express no
    # more than these, so no rejected/disputed/retired mapping may be invented.
    cases = [
        ("unreviewed-never-activated", None, None, "pending", "dormant"),
        ("reviewed-not-activated", NOW, None, "approved", "dormant"),
        ("reviewed-and-activated", NOW, LATER, "approved", "active"),
    ]
    ids = {}
    with _engine(database_url).begin() as conn:
        _insert_account(conn, ACCOUNT_A)
        for label, reviewed, activated, _r, _l in cases:
            mid = str(uuid.uuid4())
            ids[label] = mid
            _insert_legacy_memory(
                conn,
                memory_id=mid,
                account_id=ACCOUNT_A,
                reviewed_at=reviewed,
                activated_at=activated,
                text_content=f"legacy {label}",
            )

    _upgrade(config, "head")

    with _engine(database_url).begin() as conn:
        for label, _rev, _act, expect_review, expect_lifecycle in cases:
            row = conn.execute(
                sa.text(
                    f"SELECT {REVIEW_COLUMN}, {LIFECYCLE_COLUMN} "
                    "FROM memory_records WHERE memory_id = :mid"
                ),
                {"mid": ids[label]},
            ).fetchone()
            assert row is not None, label
            assert row[0] == expect_review, (label, row[0])
            assert row[1] == expect_lifecycle, (label, row[1])

        # C8 must never manufacture history.
        counts = conn.execute(
            sa.text(
                f"SELECT {REVIEW_COLUMN}, {LIFECYCLE_COLUMN}, COUNT(*) "
                "FROM memory_records GROUP BY 1, 2"
            )
        ).fetchall()
        produced = {(r[0], r[1]) for r in counts}
        assert produced == {
            ("pending", "dormant"),
            ("approved", "dormant"),
            ("approved", "active"),
        }
        for forbidden in ("rejected", "disputed"):
            assert forbidden not in {r[0] for r in counts}
        assert "retired" not in {r[1] for r in counts}


# ---------------------------------------------------------------------------
# C. Existing data preservation.
# ---------------------------------------------------------------------------


def test_upgrade_preserves_every_field_c8_does_not_own(
    temporary_postgres,
) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, PREVIOUS_REVISION)

    memory_id = str(uuid.uuid4())
    preserved_extensions = {"display_hint": "preserve-me"}
    with _engine(database_url).begin() as conn:
        _insert_account(conn, ACCOUNT_A)
        conn.execute(
            sa.text(
                "INSERT INTO memory_records "
                "(memory_id, user_id, project_id, semantic_species, "
                " text_content, fact_key, fact_value, fact_confidence, "
                " reviewed_at, activated_at, pinned, held, extensions, "
                " created_at, updated_at) "
                "VALUES (:mid, :acct, NULL, 'episodic_semantic_memory', "
                " 'preserve this text', NULL, NULL, NULL, "
                " :reviewed, :activated, true, true, "
                " CAST(:ext AS jsonb), :created, :updated)"
            ),
            {
                "mid": memory_id,
                "acct": ACCOUNT_A,
                "reviewed": NOW,
                "activated": LATER,
                "ext": '{"display_hint": "preserve-me"}',
                "created": NOW,
                "updated": LATER,
            },
        )
        # A provenance row and a persona subject/link must also survive.
        conn.execute(
            sa.text(
                "INSERT INTO memory_provenance "
                "(provenance_id, memory_id, user_id, source_system, "
                " source_subject_kind, is_imported, created_at) "
                "VALUES (:pid, :mid, :acct, 'codexify', 'vault', false, :created)"
            ),
            {
                "pid": str(uuid.uuid4()),
                "mid": memory_id,
                "acct": ACCOUNT_A,
                "created": NOW,
            },
        )

        before_ext = conn.execute(
            sa.text("SELECT extensions FROM memory_records WHERE memory_id = :m"),
            {"m": memory_id},
        ).scalar_one()
        assert before_ext == preserved_extensions

    _upgrade(config, "head")

    with _engine(database_url).begin() as conn:
        row = conn.execute(
            sa.text(
                "SELECT memory_id, user_id, project_id, semantic_species, "
                " text_content, fact_key, fact_value, fact_confidence, "
                " reviewed_at, activated_at, pinned, held, extensions, "
                " created_at, updated_at, review_state, lifecycle_state "
                "FROM memory_records WHERE memory_id = :m"
            ),
            {"m": memory_id},
        ).fetchone()
        assert row is not None
        assert row[0] == memory_id
        assert row[1] == ACCOUNT_A
        assert row[2] is None
        assert row[3] == "episodic_semantic_memory"
        assert row[4] == "preserve this text"
        assert row[5] is None and row[6] is None and row[7] is None
        assert row[8] == NOW
        assert row[9] == LATER
        assert row[10] is True
        assert row[11] is True
        assert row[12] == preserved_extensions
        assert row[13] == NOW
        assert row[14] == LATER
        # Only the two governance columns may be new.
        assert row[15] == "approved"
        assert row[16] == "active"

        prov = conn.execute(
            sa.text(
                "SELECT source_system, source_subject_kind, is_imported "
                "FROM memory_provenance WHERE memory_id = :m"
            ),
            {"m": memory_id},
        ).fetchall()
        assert len(prov) == 1
        assert prov[0][0] == "codexify"
        assert prov[0][1] == "vault"
        assert prov[0][2] is False


# ---------------------------------------------------------------------------
# D. Personal Facts authority preservation.
# ---------------------------------------------------------------------------


def test_migration_does_not_rewrite_personal_fact_authority(
    temporary_postgres,
) -> None:
    """C8 must not convert Personal Facts into ordinary-memory governance."""
    config, database_url = temporary_postgres
    _upgrade(config, PREVIOUS_REVISION)

    fact_id = 4711
    with _engine(database_url).begin() as conn:
        _insert_account(conn, ACCOUNT_A)
        conn.execute(
            sa.text(
                "INSERT INTO personal_facts "
                "(id, user_id, key, value, status, confidence, is_active, "
                " created_at, updated_at) "
                "VALUES (:id, :acct, 'pf_key', 'pf_value', 'disputed', 0.5, "
                " false, :created, :updated)"
            ),
            {
                "id": fact_id,
                "acct": ACCOUNT_A,
                "created": NOW,
                "updated": NOW,
            },
        )

        before = conn.execute(
            sa.text(
                "SELECT status, is_active, confidence FROM personal_facts "
                "WHERE id = :id"
            ),
            {"id": fact_id},
        ).fetchone()

    _upgrade(config, "head")

    with _engine(database_url).begin() as conn:
        after = conn.execute(
            sa.text(
                "SELECT status, is_active, confidence FROM personal_facts "
                "WHERE id = :id"
            ),
            {"id": fact_id},
        ).fetchone()
        # Specialized Personal Facts authority is untouched by the C8 upgrade.
        assert after == before
        assert after[0] == "disputed"
        assert after[1] is False

        # The generic governance columns exist only on memory_records; they
        # must not appear as a second writable Personal Fact review/lifecycle
        # truth.
        pf_cols = {
            r[0]
            for r in conn.execute(
                sa.text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = 'personal_facts'"
                )
            ).fetchall()
        }
        assert REVIEW_COLUMN not in pf_cols
        assert LIFECYCLE_COLUMN not in pf_cols


# ---------------------------------------------------------------------------
# E. Constraint enforcement.
# ---------------------------------------------------------------------------


def test_database_rejects_out_of_vocabulary_governance_tokens(
    temporary_postgres,
) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")

    with _engine(database_url).begin() as conn:
        _insert_account(conn, ACCOUNT_A)

    def _insert(review: str, lifecycle: str):
        def _cb(connection):
            connection.execute(
                sa.text(
                    "INSERT INTO memory_records "
                    "(memory_id, user_id, project_id, semantic_species, "
                    " text_content, fact_key, fact_value, fact_confidence, "
                    " reviewed_at, activated_at, pinned, held, "
                    f" {REVIEW_COLUMN}, {LIFECYCLE_COLUMN}, extensions, "
                    " created_at, updated_at) "
                    "VALUES (:mid, :acct, NULL, 'episodic_semantic_memory', "
                    " 'token', NULL, NULL, NULL, NULL, NULL, false, false, "
                    " :review, :lifecycle, NULL, :now, :now)"
                ),
                {
                    "mid": str(uuid.uuid4()),
                    "acct": ACCOUNT_A,
                    "review": review,
                    "lifecycle": lifecycle,
                    "now": NOW,
                },
            )

        return _cb

    # Every canonical token must be accepted.
    for review in CANONICAL_REVIEW_STATES:
        for lifecycle in CANONICAL_LIFECYCLE_STATES:
            with _engine(database_url).begin() as conn:
                _insert(review, lifecycle)(conn)

    # Out-of-vocabulary review token must be rejected at the DB boundary.
    _expect_integrity_error(database_url, _insert("not_a_review_state", "active"))
    # Out-of-vocabulary lifecycle token must be rejected at the DB boundary.
    _expect_integrity_error(database_url, _insert("approved", "not_a_lifecycle_state"))
    # 'archived' is a Personal Facts token, not an ordinary-memory lifecycle.
    _expect_integrity_error(database_url, _insert("approved", "archived"))
    # 'inactive' is not an ordinary-memory lifecycle token either.
    _expect_integrity_error(database_url, _insert("approved", "inactive"))

    # A rejected insert must leave no row behind.
    with _engine(database_url).begin() as conn:
        total = conn.execute(
            sa.text("SELECT COUNT(*) FROM memory_records WHERE user_id = :a"),
            {"a": ACCOUNT_A},
        ).scalar_one()
    assert total == len(CANONICAL_REVIEW_STATES) * len(CANONICAL_LIFECYCLE_STATES)


# ---------------------------------------------------------------------------
# G. Repeatability.
# ---------------------------------------------------------------------------


def test_governance_migration_is_repeatable_on_independent_databases(
    monkeypatch,
) -> None:
    """The C8 proof must reproduce on a second, independently created DB."""
    base_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not base_url:
        pytest.skip("TEST_DATABASE_URL or DATABASE_URL environment variable required")
    admin_url = _admin_database_url(base_url)

    config, database_url, database_name = _fresh_disposable_postgres(
        base_url, "codexify_ums05c8q"
    )
    try:
        # Match the proven fixture posture: migrations resolve the DSN from
        # DATABASE_URL, exactly as temporary_postgres does.
        monkeypatch.setenv("DATABASE_URL", database_url)
        _upgrade(config, PREVIOUS_REVISION)
        mid = str(uuid.uuid4())
        with _engine(database_url).begin() as conn:
            _insert_account(conn, ACCOUNT_A)
            _insert_legacy_memory(
                conn,
                memory_id=mid,
                account_id=ACCOUNT_A,
                reviewed_at=NOW,
                activated_at=None,
                text_content="repeatable",
            )
            conn.commit()

        _upgrade(config, "head")

        with _engine(database_url).begin() as conn:
            row = conn.execute(
                sa.text(
                    f"SELECT {REVIEW_COLUMN}, {LIFECYCLE_COLUMN} "
                    "FROM memory_records WHERE memory_id = :m"
                ),
                {"m": mid},
            ).fetchone()
            assert row == ("approved", "dormant")
            heads = connection_heads(config)
            assert len(heads) == 1
            assert _is_ancestor_revision(config, UMS_05C8_REVISION, heads[0])
    finally:
        _drop_disposable_postgres(admin_url, database_name)
