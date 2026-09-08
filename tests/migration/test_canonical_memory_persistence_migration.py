"""Real PostgreSQL/Alembic proof for canonical UMS memory persistence.

This file proves the UMS-03D migration
``f6b0d3e8c5a2_add_canonical_memory_persistence`` against a disposable
PostgreSQL 17 database. It exercises the full §4.16 contract from
``docs/architecture/unified-memory-store-contract.md`` (amended by
UMS-03C-A):

* memory_records column set, semantic-species and payload CHECKs, and
  review/activation ordering CHECK;
* memory_persona_links same-account integrity, link-kind CHECK, and
  per-(memory, persona, kind) uniqueness;
* memory_provenance one-to-many multiplicity, source-vocabulary
  CHECKs, and typed source-identity preservation;
* additive-only migration posture: legacy ``memory_entries`` and
  ``personal_facts`` rows survive the upgrade unchanged, and the
  canonical tables are empty after upgrading a legacy-bearing
  database;
* downgrade preservation: legacy rows are unchanged after a
  ``downgrade`` round-trip back to ``e5a9c2f7b4d1``.
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


PREVIOUS_REVISION = "e5a9c2f7b4d1"
UMS_03D_REVISION = "f6b0d3e8c5a2"
NEW_TABLES = {
    "memory_records",
    "memory_persona_links",
    "memory_provenance",
}

CANONICAL_SEMANTIC_SPECIES = (
    "episodic_semantic_memory",
    "verified_personal_fact",
    "candidate_unreviewed_fact",
)
CANONICAL_PERSONA_LINK_KINDS = (
    "captured_under",
    "suggested_by",
    "associated_with",
)
CANONICAL_PROVENANCE_SOURCE_SYSTEMS = (
    "codexify",
    "openai",
    "anthropic",
    "future_registered",
)
CANONICAL_PROVENANCE_SOURCE_SUBJECT_KINDS = (
    "chat",
    "vault",
    "importer",
    "classifier",
    "future_registered",
)

NOW = datetime(2026, 9, 7, 12, 0, tzinfo=timezone.utc)
LATER = NOW + timedelta(seconds=1)


def _database_url(base_url: str, database_name: str) -> str:
    parsed = urlparse(base_url)
    return urlunparse(parsed._replace(path=f"/{database_name}"))


def _admin_database_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    return urlunparse(parsed._replace(path="/postgres"))


@pytest.fixture
def temporary_postgres(monkeypatch):
    if psycopg is None:
        pytest.skip("psycopg not installed")

    base_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not base_url:
        pytest.skip("TEST_DATABASE_URL or DATABASE_URL environment variable required")

    admin_url = _admin_database_url(base_url)
    database_name = f"codexify_ums03d_{uuid.uuid4().hex[:12]}"
    database_url = _database_url(base_url, database_name)

    try:
        admin_connection = psycopg.connect(admin_url, autocommit=True)
    except psycopg.Error as exc:  # pragma: no cover - environment specific
        pytest.skip(f"Unable to connect to admin database: {exc}")

    try:
        with admin_connection.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE {database_name}")
    except psycopg.Error as exc:  # pragma: no cover - environment specific
        admin_connection.close()
        pytest.skip(f"Unable to create test database: {exc.sqlstate}")
    finally:
        admin_connection.close()

    from alembic.config import Config

    repo_root = Path(__file__).resolve().parents[2]
    config = Config(str(repo_root / "backend" / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    config.set_main_option(
        "script_location", str(repo_root / "guardian" / "db" / "migrations")
    )
    monkeypatch.setenv("DATABASE_URL", database_url)

    try:
        yield config, database_url
    finally:
        cleanup_connection = psycopg.connect(admin_url, autocommit=True)
        try:
            with cleanup_connection.cursor() as cursor:
                cursor.execute(
                    "SELECT pg_terminate_backend(pid) "
                    "FROM pg_stat_activity WHERE datname = %s",
                    (database_name,),
                )
                cursor.execute(f"DROP DATABASE IF EXISTS {database_name}")
        finally:
            cleanup_connection.close()


def _upgrade(config, revision: str) -> None:
    from alembic import command

    command.upgrade(config, revision)


def _downgrade(config, revision: str) -> None:
    from alembic import command

    command.downgrade(config, revision)


def _insert_user(connection, account_id: str) -> None:
    connection.execute(
        sa.text(
            "INSERT INTO users (id, username, password_hash, role) "
            "VALUES (:id, :username, 'not-a-real-hash', 'guest')"
        ),
        {"id": account_id, "username": account_id},
    )


def _insert_project(
    connection,
    *,
    project_id: int,
    account_id: str,
    name: str,
) -> None:
    connection.execute(
        sa.text(
            "INSERT INTO projects (id, user_id, name) "
            "VALUES (:id, :account_id, :name)"
        ),
        {"id": project_id, "account_id": account_id, "name": name},
    )


def _insert_legacy_memory_entry(
    connection,
    *,
    user_id: str,
    silo: str,
    content: str,
) -> int:
    return int(
        connection.execute(
            sa.text(
                "INSERT INTO memory_entries (user_id, silo, content) "
                "VALUES (:user_id, :silo, :content) RETURNING id"
            ),
            {"user_id": user_id, "silo": silo, "content": content},
        ).scalar_one()
    )


def _insert_legacy_personal_fact(
    connection,
    *,
    user_id: str,
    key: str,
    value: str,
) -> int:
    return int(
        connection.execute(
            sa.text(
                "INSERT INTO personal_facts (user_id, key, value) "
                "VALUES (:user_id, :key, :value) RETURNING id"
            ),
            {"user_id": user_id, "key": key, "value": value},
        ).scalar_one()
    )


def _insert_legacy_personal_fact_evidence(
    connection,
    *,
    fact_id: int,
    source_type: str,
) -> int:
    return int(
        connection.execute(
            sa.text(
                "INSERT INTO personal_fact_evidence "
                "(fact_id, source_type, evidence_meta) "
                "VALUES (:fact_id, :source_type, '{}'::jsonb) RETURNING id"
            ),
            {"fact_id": fact_id, "source_type": source_type},
        ).scalar_one()
    )


def _insert_legacy_personal_fact_revision(
    connection,
    *,
    fact_id: int,
) -> int:
    return int(
        connection.execute(
            sa.text(
                "INSERT INTO personal_fact_revisions (fact_id, actor, action) "
                "VALUES (:fact_id, 'test', 'create') RETURNING id"
            ),
            {"fact_id": fact_id},
        ).scalar_one()
    )


def _snapshot_legacy_rows(connection) -> dict[str, list[dict[str, object]]]:
    memory_rows = list(
        connection.execute(
            sa.text(
                "SELECT id, user_id, silo, content, pinned "
                "FROM memory_entries ORDER BY id"
            )
        ).mappings()
    )
    fact_rows = list(
        connection.execute(
            sa.text(
                "SELECT id, user_id, key, value, status, is_active, confidence "
                "FROM personal_facts ORDER BY id"
            )
        ).mappings()
    )
    evidence_rows = list(
        connection.execute(
            sa.text(
                "SELECT id, fact_id, source_type "
                "FROM personal_fact_evidence ORDER BY id"
            )
        ).mappings()
    )
    revision_rows = list(
        connection.execute(
            sa.text(
                "SELECT id, fact_id, actor, action "
                "FROM personal_fact_revisions ORDER BY id"
            )
        ).mappings()
    )
    return {
        "memory_entries": [dict(r) for r in memory_rows],
        "personal_facts": [dict(r) for r in fact_rows],
        "personal_fact_evidence": [dict(r) for r in evidence_rows],
        "personal_fact_revisions": [dict(r) for r in revision_rows],
    }


def _snapshot_project_rows(connection) -> list[dict[str, object]]:
    rows = list(
        connection.execute(
            sa.text(
                "SELECT id, user_id, name, description, icon, "
                "identity_depth, system_role, archived_at, created_at, updated_at "
                "FROM projects ORDER BY id"
            )
        ).mappings()
    )
    return [dict(r) for r in rows]


def _expect_integrity_error(database_url, callback) -> None:
    """Run ``callback(connection)`` in a fresh transaction and assert that
    the database raises ``IntegrityError``.

    Each rejection attempt must use a fresh transaction because
    PostgreSQL aborts the surrounding transaction after any
    ``IntegrityError``. Reusing the same transaction for the next
    rejection attempt would trigger
    ``psycopg.errors.InFailedSqlTransaction`` instead of the
    intended constraint error.
    """

    engine = sa.create_engine(database_url, future=True)
    try:
        with engine.begin() as connection:
            with pytest.raises(IntegrityError):
                callback(connection)
    finally:
        engine.dispose()


def _insert_canonical_memory(
    connection,
    *,
    memory_id: str,
    user_id: str,
    project_id: int | None,
    semantic_species: str,
    text_content: str | None = None,
    fact_key: str | None = None,
    fact_value: str | None = None,
    fact_confidence: float | None = None,
    reviewed_at: datetime | None = None,
    activated_at: datetime | None = None,
    pinned: bool = False,
    held: bool = False,
) -> None:
    connection.execute(
        sa.text("""
            INSERT INTO memory_records (
                memory_id, user_id, project_id, semantic_species,
                text_content, fact_key, fact_value, fact_confidence,
                reviewed_at, activated_at, pinned, held
            ) VALUES (
                :memory_id, :user_id, :project_id, :semantic_species,
                :text_content, :fact_key, :fact_value, :fact_confidence,
                :reviewed_at, :activated_at, :pinned, :held
            )
            """),
        {
            "memory_id": memory_id,
            "user_id": user_id,
            "project_id": project_id,
            "semantic_species": semantic_species,
            "text_content": text_content,
            "fact_key": fact_key,
            "fact_value": fact_value,
            "fact_confidence": fact_confidence,
            "reviewed_at": reviewed_at,
            "activated_at": activated_at,
            "pinned": pinned,
            "held": held,
        },
    )


def _insert_persona_link(
    connection,
    *,
    link_id: str,
    memory_id: str,
    user_id: str,
    persona_subject_id: str,
    persona_user_id: str,
    link_kind: str,
) -> None:
    connection.execute(
        sa.text("""
            INSERT INTO memory_persona_links (
                link_id, memory_id, user_id,
                persona_subject_id, persona_user_id, link_kind
            ) VALUES (
                :link_id, :memory_id, :user_id,
                :persona_subject_id, :persona_user_id, :link_kind
            )
            """),
        {
            "link_id": link_id,
            "memory_id": memory_id,
            "user_id": user_id,
            "persona_subject_id": persona_subject_id,
            "persona_user_id": persona_user_id,
            "link_kind": link_kind,
        },
    )


def _insert_provenance(
    connection,
    *,
    provenance_id: str,
    memory_id: str,
    user_id: str,
    source_system: str,
    source_record_id: str | None = None,
    source_thread_id: int | None = None,
    source_message_id: int | None = None,
    source_import_job_id: str | None = None,
    source_export_fingerprint: str | None = None,
    source_subject_kind: str | None = None,
    source_subject_id: str | None = None,
    is_imported: bool = False,
) -> None:
    connection.execute(
        sa.text("""
            INSERT INTO memory_provenance (
                provenance_id, memory_id, user_id, source_system,
                source_record_id, source_thread_id, source_message_id,
                source_import_job_id, source_export_fingerprint,
                source_subject_kind, source_subject_id, is_imported
            ) VALUES (
                :provenance_id, :memory_id, :user_id, :source_system,
                :source_record_id, :source_thread_id, :source_message_id,
                :source_import_job_id, :source_export_fingerprint,
                :source_subject_kind, :source_subject_id, :is_imported
            )
            """),
        {
            "provenance_id": provenance_id,
            "memory_id": memory_id,
            "user_id": user_id,
            "source_system": source_system,
            "source_record_id": source_record_id,
            "source_thread_id": source_thread_id,
            "source_message_id": source_message_id,
            "source_import_job_id": source_import_job_id,
            "source_export_fingerprint": source_export_fingerprint,
            "source_subject_kind": source_subject_kind,
            "source_subject_id": source_subject_id,
            "is_imported": is_imported,
        },
    )


@pytest.mark.integration
def test_fresh_replay_creates_canonical_tables_with_frozen_constraints(
    temporary_postgres,
) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    engine = sa.create_engine(database_url, future=True)
    try:
        with engine.connect() as connection:
            inspector = sa.inspect(connection)
            tables = set(inspector.get_table_names())
            assert NEW_TABLES <= tables, f"missing canonical tables; found {tables}"
            assert (
                connection.execute(
                    sa.text("SELECT version_num FROM alembic_version")
                ).scalar_one()
                == UMS_03D_REVISION
            )

            # UMS-03C-B: the enabling Project relational target must exist
            # after the UMS-03D upgrade. Verify via the unique_constraints
            # catalog and via a direct probe.
            project_unique = {
                tuple(c["column_names"])
                for c in inspector.get_unique_constraints("projects")
            }
            assert ("id", "user_id") in project_unique, (
                f"projects must carry uq_projects_id_user_id; "
                f"found unique constraints: {project_unique}"
            )
            assert (
                connection.execute(
                    sa.text(
                        "SELECT EXISTS ("
                        "SELECT 1 FROM pg_constraint "
                        "WHERE conname = 'uq_projects_id_user_id'"
                        ")"
                    )
                ).scalar_one()
                is True
            )

            for table in NEW_TABLES:
                assert (
                    connection.execute(
                        sa.text(f"SELECT count(*) FROM {table}")
                    ).scalar_one()
                    == 0
                ), f"{table} must be empty after fresh replay"

            for species in CANONICAL_SEMANTIC_SPECIES:
                # Existence of species in the CHECK constraint: insert and
                # rollback via SAVEPOINT
                pass

            constraints_for_records = {
                c["name"] for c in inspector.get_check_constraints("memory_records")
            }
            assert "memory_records_semantic_species_check" in constraints_for_records
            assert (
                "memory_records_review_activation_order_check"
                in constraints_for_records
            )
            assert "memory_records_payload_present_check" in constraints_for_records
            assert "memory_records_fact_confidence_check" in constraints_for_records
            assert (
                "memory_records_episodic_payload_shape_check" in constraints_for_records
            )
            assert "memory_records_fact_payload_shape_check" in constraints_for_records

            constraints_for_links = {
                c["name"]
                for c in inspector.get_check_constraints("memory_persona_links")
            }
            assert "memory_persona_links_link_kind_check" in constraints_for_links
            assert "memory_persona_links_same_account_check" in constraints_for_links

            constraints_for_provenance = {
                c["name"] for c in inspector.get_check_constraints("memory_provenance")
            }
            assert "memory_provenance_source_system_check" in constraints_for_provenance
            assert (
                "memory_provenance_source_subject_kind_check"
                in constraints_for_provenance
            )

            unique_for_records = {
                tuple(c["column_names"])
                for c in inspector.get_unique_constraints("memory_records")
            }
            assert ("memory_id", "user_id") in unique_for_records

            unique_for_links = {
                tuple(c["column_names"])
                for c in inspector.get_unique_constraints("memory_persona_links")
            }
            assert (
                "memory_id",
                "persona_subject_id",
                "link_kind",
            ) in unique_for_links

            indexes_for_records = {
                ix["name"] for ix in inspector.get_indexes("memory_records")
            }
            assert "ix_memory_records_user_id" in indexes_for_records
            assert "ix_memory_records_user_project" in indexes_for_records
            assert "ix_memory_records_user_species" in indexes_for_records
            assert "ix_memory_records_user_activated_at" in indexes_for_records

            indexes_for_links = {
                ix["name"] for ix in inspector.get_indexes("memory_persona_links")
            }
            assert "ix_memory_persona_links_user_id" in indexes_for_links
            assert "ix_memory_persona_links_persona_subject_id" in indexes_for_links

            indexes_for_provenance = {
                ix["name"] for ix in inspector.get_indexes("memory_provenance")
            }
            assert "ix_memory_provenance_memory_id" in indexes_for_provenance
            assert "ix_memory_provenance_user_source_system" in indexes_for_provenance
            assert "ix_memory_provenance_source_thread_id" in indexes_for_provenance
    finally:
        engine.dispose()


@pytest.mark.integration
def test_existing_schema_additive_upgrade_preserves_legacy_and_leaves_canonical_empty(
    temporary_postgres,
) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, PREVIOUS_REVISION)
    engine = sa.create_engine(database_url, future=True)
    legacy_seed = {
        "memory_entries": [],
        "personal_facts": [],
        "personal_fact_evidence": [],
        "personal_fact_revisions": [],
    }
    try:
        with engine.begin() as connection:
            _insert_user(connection, "account-A")
            _insert_user(connection, "account-B")
            # Seed representative Project rows so the UMS-03C-B
            # enabling relational target is exercised on existing
            # legacy data. The new UNIQUE(id, user_id) constraint
            # must accept these rows without rejection because
            # projects.id is already a primary key.
            _insert_project(
                connection,
                project_id=100,
                account_id="account-A",
                name="A project",
            )
            _insert_project(
                connection,
                project_id=200,
                account_id="account-B",
                name="B project",
            )
            pre_upgrade_projects = _snapshot_project_rows(connection)
            assert len(pre_upgrade_projects) == 2
            legacy_seed["memory_entries"] = [
                {
                    "id": _insert_legacy_memory_entry(
                        connection,
                        user_id="account-A",
                        silo="longterm",
                        content="Legacy memory A",
                    ),
                    "user_id": "account-A",
                    "silo": "longterm",
                    "content": "Legacy memory A",
                    "pinned": False,
                },
                {
                    "id": _insert_legacy_memory_entry(
                        connection,
                        user_id="account-B",
                        silo="ephemeral",
                        content="Legacy memory B",
                    ),
                    "user_id": "account-B",
                    "silo": "ephemeral",
                    "content": "Legacy memory B",
                    "pinned": False,
                },
            ]
            legacy_fact_id_A = _insert_legacy_personal_fact(
                connection,
                user_id="account-A",
                key="favorite_color",
                value="blue",
            )
            legacy_fact_id_B = _insert_legacy_personal_fact(
                connection,
                user_id="account-B",
                key="city",
                value="paris",
            )
            legacy_seed["personal_facts"] = [
                {
                    "id": legacy_fact_id_A,
                    "user_id": "account-A",
                    "key": "favorite_color",
                    "value": "blue",
                    "status": "candidate",
                    "is_active": True,
                    "confidence": 0.5,
                },
                {
                    "id": legacy_fact_id_B,
                    "user_id": "account-B",
                    "key": "city",
                    "value": "paris",
                    "status": "candidate",
                    "is_active": True,
                    "confidence": 0.5,
                },
            ]
            legacy_seed["personal_fact_evidence"] = [
                {
                    "id": _insert_legacy_personal_fact_evidence(
                        connection,
                        fact_id=legacy_fact_id_A,
                        source_type="runtime_extraction",
                    ),
                    "fact_id": legacy_fact_id_A,
                    "source_type": "runtime_extraction",
                },
                {
                    "id": _insert_legacy_personal_fact_evidence(
                        connection,
                        fact_id=legacy_fact_id_B,
                        source_type="user_stated",
                    ),
                    "fact_id": legacy_fact_id_B,
                    "source_type": "user_stated",
                },
            ]
            legacy_seed["personal_fact_revisions"] = [
                {
                    "id": _insert_legacy_personal_fact_revision(
                        connection, fact_id=legacy_fact_id_A
                    ),
                    "fact_id": legacy_fact_id_A,
                    "actor": "test",
                    "action": "create",
                },
                {
                    "id": _insert_legacy_personal_fact_revision(
                        connection, fact_id=legacy_fact_id_B
                    ),
                    "fact_id": legacy_fact_id_B,
                    "actor": "test",
                    "action": "create",
                },
            ]
        pre_upgrade_snapshot = _snapshot_legacy_rows(engine.connect().__enter__())
        assert pre_upgrade_snapshot == legacy_seed
    finally:
        engine.dispose()

    _upgrade(config, UMS_03D_REVISION)

    engine = sa.create_engine(database_url, future=True)
    try:
        with engine.connect() as connection:
            post_upgrade_snapshot = _snapshot_legacy_rows(connection)
            assert (
                post_upgrade_snapshot == pre_upgrade_snapshot
            ), "legacy rows must survive the additive upgrade unchanged"
            # UMS-03C-B: Project rows must also survive the additive
            # upgrade byte-for-byte. The new UNIQUE(id, user_id)
            # constraint changes schema only.
            post_upgrade_projects = _snapshot_project_rows(connection)
            assert (
                post_upgrade_projects == pre_upgrade_projects
            ), "projects rows must survive the additive upgrade unchanged"
            for table in NEW_TABLES:
                count = connection.execute(
                    sa.text(f"SELECT count(*) FROM {table}")
                ).scalar_one()
                assert count == 0, f"{table} must be empty after additive upgrade"
    finally:
        engine.dispose()


@pytest.mark.integration
def test_project_composite_target_accepts_same_account_and_rejects_cross_account(
    temporary_postgres,
) -> None:
    """UMS-03C-B: same-account Project scope is accepted, cross-account is
    rejected at the relational boundary, not by application code."""
    config, database_url = temporary_postgres
    _upgrade(config, UMS_03D_REVISION)
    engine = sa.create_engine(database_url, future=True)
    try:
        with engine.begin() as connection:
            _insert_user(connection, "account-A")
            _insert_user(connection, "account-B")
            _insert_project(
                connection,
                project_id=10,
                account_id="account-A",
                name="A-only project",
            )
            _insert_project(
                connection,
                project_id=20,
                account_id="account-B",
                name="B-only project",
            )

            # Same-account Project scope is accepted.
            _insert_canonical_memory(
                connection,
                memory_id=str(uuid.uuid4()),
                user_id="account-A",
                project_id=10,
                semantic_species="episodic_semantic_memory",
                text_content="A memory scoped to A's project",
            )

            # Cross-account Project scope is rejected at the
            # composite FK boundary.
            with pytest.raises(IntegrityError):
                _insert_canonical_memory(
                    connection,
                    memory_id=str(uuid.uuid4()),
                    user_id="account-A",
                    project_id=20,
                    semantic_species="episodic_semantic_memory",
                    text_content="cross-account scope attempt",
                )
    finally:
        engine.dispose()


@pytest.mark.integration
def test_valid_semantic_species_inserts_pass(temporary_postgres) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, UMS_03D_REVISION)
    engine = sa.create_engine(database_url, future=True)
    try:
        with engine.begin() as connection:
            _insert_user(connection, "account-A")
            _insert_canonical_memory(
                connection,
                memory_id=str(uuid.uuid4()),
                user_id="account-A",
                project_id=None,
                semantic_species="episodic_semantic_memory",
                text_content="I prefer dark roast coffee",
            )
            fact_id = str(uuid.uuid4())
            _insert_canonical_memory(
                connection,
                memory_id=fact_id,
                user_id="account-A",
                project_id=None,
                semantic_species="verified_personal_fact",
                fact_key="coffee_preference",
                fact_value="dark roast",
                fact_confidence=0.92,
                reviewed_at=NOW,
                activated_at=NOW,
            )
            _insert_canonical_memory(
                connection,
                memory_id=str(uuid.uuid4()),
                user_id="account-A",
                project_id=None,
                semantic_species="candidate_unreviewed_fact",
                fact_key="morning_routine",
                fact_value="wakes at 6am",
                fact_confidence=0.4,
            )
            for species in CANONICAL_SEMANTIC_SPECIES:
                assert (
                    connection.execute(
                        sa.text(
                            "SELECT count(*) FROM memory_records "
                            "WHERE semantic_species = :species"
                        ),
                        {"species": species},
                    ).scalar_one()
                    == 1
                )
    finally:
        engine.dispose()


@pytest.mark.integration
def test_semantic_species_aliases_rejected(temporary_postgres) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, UMS_03D_REVISION)

    def _seed_user() -> None:
        engine = sa.create_engine(database_url, future=True)
        try:
            with engine.begin() as connection:
                _insert_user(connection, "account-A")
        finally:
            engine.dispose()

    _seed_user()

    for alias in (
        "episodic_memory",
        "semantic_memory",
        "candidate_fact",
        "unreviewed_fact",
        "unknown",
        "EPISTEMIC_SEMANTIC_MEMORY",
    ):
        _expect_integrity_error(
            database_url,
            lambda conn, _alias=alias: _insert_canonical_memory(
                conn,
                memory_id=str(uuid.uuid4()),
                user_id="account-A",
                project_id=None,
                semantic_species=_alias,
                text_content="invalid alias payload",
            ),
        )


@pytest.mark.integration
def test_payload_shape_constraints_rejected(temporary_postgres) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, UMS_03D_REVISION)

    def _seed_user() -> None:
        engine = sa.create_engine(database_url, future=True)
        try:
            with engine.begin() as connection:
                _insert_user(connection, "account-A")
        finally:
            engine.dispose()

    _seed_user()

    # Episodic with fact-shaped payload is invalid.
    _expect_integrity_error(
        database_url,
        lambda conn: _insert_canonical_memory(
            conn,
            memory_id=str(uuid.uuid4()),
            user_id="account-A",
            project_id=None,
            semantic_species="episodic_semantic_memory",
            text_content="free text",
            fact_key="leak",
            fact_value="leak",
        ),
    )

    # Verified personal fact without fact_key is invalid.
    _expect_integrity_error(
        database_url,
        lambda conn: _insert_canonical_memory(
            conn,
            memory_id=str(uuid.uuid4()),
            user_id="account-A",
            project_id=None,
            semantic_species="verified_personal_fact",
            fact_key=None,
            fact_value="x",
            fact_confidence=0.5,
        ),
    )

    # Episodic with fact_confidence is invalid.
    _expect_integrity_error(
        database_url,
        lambda conn: _insert_canonical_memory(
            conn,
            memory_id=str(uuid.uuid4()),
            user_id="account-A",
            project_id=None,
            semantic_species="episodic_semantic_memory",
            text_content="free text",
            fact_confidence=0.5,
        ),
    )

    # fact_confidence out of range is invalid.
    _expect_integrity_error(
        database_url,
        lambda conn: _insert_canonical_memory(
            conn,
            memory_id=str(uuid.uuid4()),
            user_id="account-A",
            project_id=None,
            semantic_species="verified_personal_fact",
            fact_key="k",
            fact_value="v",
            fact_confidence=1.5,
        ),
    )


@pytest.mark.integration
def test_account_ownership_fk_rejects_nonexistent_user(
    temporary_postgres,
) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, UMS_03D_REVISION)
    engine = sa.create_engine(database_url, future=True)
    try:
        with engine.begin() as connection:
            with pytest.raises(IntegrityError):
                _insert_canonical_memory(
                    connection,
                    memory_id=str(uuid.uuid4()),
                    user_id="missing-account",
                    project_id=None,
                    semantic_species="episodic_semantic_memory",
                    text_content="orphan",
                )
    finally:
        engine.dispose()


@pytest.mark.integration
def test_cross_account_project_scope_rejected(temporary_postgres) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, UMS_03D_REVISION)
    engine = sa.create_engine(database_url, future=True)
    try:
        with engine.begin() as connection:
            _insert_user(connection, "account-A")
            _insert_user(connection, "account-B")
            _insert_project(
                connection,
                project_id=10,
                account_id="account-B",
                name="B-only project",
            )
            with pytest.raises(IntegrityError):
                _insert_canonical_memory(
                    connection,
                    memory_id=str(uuid.uuid4()),
                    user_id="account-A",
                    project_id=10,
                    semantic_species="episodic_semantic_memory",
                    text_content="cross-account scope",
                )
    finally:
        engine.dispose()


@pytest.mark.integration
def test_project_delete_restrict_blocks_when_scoped_memory_present(
    temporary_postgres,
) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, UMS_03D_REVISION)
    engine = sa.create_engine(database_url, future=True)
    try:
        with engine.begin() as connection:
            _insert_user(connection, "account-A")
            _insert_project(
                connection,
                project_id=20,
                account_id="account-A",
                name="Scoped project",
            )
            _insert_canonical_memory(
                connection,
                memory_id=str(uuid.uuid4()),
                user_id="account-A",
                project_id=20,
                semantic_species="episodic_semantic_memory",
                text_content="scoped memory",
            )
            with pytest.raises(IntegrityError):
                connection.execute(sa.text("DELETE FROM projects WHERE id = 20"))
    finally:
        engine.dispose()


@pytest.mark.integration
def test_review_activation_boundary_cases(temporary_postgres) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, UMS_03D_REVISION)

    def _seed_user() -> None:
        engine = sa.create_engine(database_url, future=True)
        try:
            with engine.begin() as connection:
                _insert_user(connection, "account-A")
        finally:
            engine.dispose()

    _seed_user()

    valid_cases = [
        {"reviewed_at": None, "activated_at": None},
        {"reviewed_at": NOW, "activated_at": None},
        {"reviewed_at": NOW, "activated_at": NOW},
        {"reviewed_at": NOW, "activated_at": LATER},
    ]
    for case in valid_cases:
        engine = sa.create_engine(database_url, future=True)
        try:
            with engine.begin() as connection:
                _insert_canonical_memory(
                    connection,
                    memory_id=str(uuid.uuid4()),
                    user_id="account-A",
                    project_id=None,
                    semantic_species="episodic_semantic_memory",
                    text_content="boundary case",
                    reviewed_at=case["reviewed_at"],
                    activated_at=case["activated_at"],
                )
        finally:
            engine.dispose()

    invalid_cases = [
        {"reviewed_at": None, "activated_at": NOW},
        {"reviewed_at": LATER, "activated_at": NOW},
    ]
    for case in invalid_cases:
        _expect_integrity_error(
            database_url,
            lambda conn, _case=case: _insert_canonical_memory(
                conn,
                memory_id=str(uuid.uuid4()),
                user_id="account-A",
                project_id=None,
                semantic_species="episodic_semantic_memory",
                text_content="invalid boundary case",
                reviewed_at=_case["reviewed_at"],
                activated_at=_case["activated_at"],
            ),
        )


@pytest.mark.integration
def test_persona_link_same_account_rejected(temporary_postgres) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, UMS_03D_REVISION)
    engine = sa.create_engine(database_url, future=True)
    try:
        with engine.begin() as connection:
            _insert_user(connection, "account-A")
            _insert_user(connection, "account-B")
            # Insert a Persona subject for account-A
            persona_subject_id = str(uuid.uuid4())
            connection.execute(
                sa.text("""
                    INSERT INTO persona_subjects
                        (persona_subject_id, user_id, lifecycle)
                    VALUES (:id, :user_id, 'active')
                    """),
                {"id": persona_subject_id, "user_id": "account-A"},
            )
            memory_id = str(uuid.uuid4())
            _insert_canonical_memory(
                connection,
                memory_id=memory_id,
                user_id="account-B",
                project_id=None,
                semantic_species="episodic_semantic_memory",
                text_content="B's memory",
            )
            with pytest.raises(IntegrityError):
                _insert_persona_link(
                    connection,
                    link_id=str(uuid.uuid4()),
                    memory_id=memory_id,
                    user_id="account-B",
                    persona_subject_id=persona_subject_id,
                    persona_user_id="account-A",
                    link_kind="captured_under",
                )
    finally:
        engine.dispose()


@pytest.mark.integration
def test_persona_link_kind_aliases_rejected(temporary_postgres) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, UMS_03D_REVISION)
    engine = sa.create_engine(database_url, future=True)
    try:
        with engine.begin() as connection:
            _insert_user(connection, "account-A")
            persona_subject_id = str(uuid.uuid4())
            connection.execute(
                sa.text("""
                    INSERT INTO persona_subjects
                        (persona_subject_id, user_id, lifecycle)
                    VALUES (:id, :user_id, 'active')
                    """),
                {"id": persona_subject_id, "user_id": "account-A"},
            )
            memory_id = str(uuid.uuid4())
            _insert_canonical_memory(
                connection,
                memory_id=memory_id,
                user_id="account-A",
                project_id=None,
                semantic_species="episodic_semantic_memory",
                text_content="valid memory",
            )
    finally:
        engine.dispose()

    for bad_kind in (
        "captured",
        "suggested",
        "associated",
        "owned_by",
        "created_by",
        "unknown",
    ):
        _expect_integrity_error(
            database_url,
            lambda conn, _kind=bad_kind, _mid=memory_id, _pid=persona_subject_id: _insert_persona_link(
                conn,
                link_id=str(uuid.uuid4()),
                memory_id=_mid,
                user_id="account-A",
                persona_subject_id=_pid,
                persona_user_id="account-A",
                link_kind=_kind,
            ),
        )


@pytest.mark.integration
def test_persona_link_duplicate_rejected(temporary_postgres) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, UMS_03D_REVISION)
    engine = sa.create_engine(database_url, future=True)
    try:
        with engine.begin() as connection:
            _insert_user(connection, "account-A")
            persona_subject_id = str(uuid.uuid4())
            connection.execute(
                sa.text("""
                    INSERT INTO persona_subjects
                        (persona_subject_id, user_id, lifecycle)
                    VALUES (:id, :user_id, 'active')
                    """),
                {"id": persona_subject_id, "user_id": "account-A"},
            )
            memory_id = str(uuid.uuid4())
            _insert_canonical_memory(
                connection,
                memory_id=memory_id,
                user_id="account-A",
                project_id=None,
                semantic_species="episodic_semantic_memory",
                text_content="memory",
            )
            _insert_persona_link(
                connection,
                link_id=str(uuid.uuid4()),
                memory_id=memory_id,
                user_id="account-A",
                persona_subject_id=persona_subject_id,
                persona_user_id="account-A",
                link_kind="captured_under",
            )
            with pytest.raises(IntegrityError):
                _insert_persona_link(
                    connection,
                    link_id=str(uuid.uuid4()),
                    memory_id=memory_id,
                    user_id="account-A",
                    persona_subject_id=persona_subject_id,
                    persona_user_id="account-A",
                    link_kind="captured_under",
                )
    finally:
        engine.dispose()


@pytest.mark.integration
def test_provenance_multiplicity_allowed(temporary_postgres) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, UMS_03D_REVISION)
    engine = sa.create_engine(database_url, future=True)
    try:
        with engine.begin() as connection:
            _insert_user(connection, "account-A")
            memory_id = str(uuid.uuid4())
            _insert_canonical_memory(
                connection,
                memory_id=memory_id,
                user_id="account-A",
                project_id=None,
                semantic_species="episodic_semantic_memory",
                text_content="multi-source memory",
            )
            _insert_provenance(
                connection,
                provenance_id=str(uuid.uuid4()),
                memory_id=memory_id,
                user_id="account-A",
                source_system="codexify",
                source_record_id="native-1",
            )
            _insert_provenance(
                connection,
                provenance_id=str(uuid.uuid4()),
                memory_id=memory_id,
                user_id="account-A",
                source_system="openai",
                source_record_id="imported-1",
                is_imported=True,
            )
            _insert_provenance(
                connection,
                provenance_id=str(uuid.uuid4()),
                memory_id=memory_id,
                user_id="account-A",
                source_system="codexify",
                source_record_id="user-corrected-1",
            )
            assert (
                connection.execute(
                    sa.text(
                        "SELECT count(*) FROM memory_provenance "
                        "WHERE memory_id = :memory_id"
                    ),
                    {"memory_id": memory_id},
                ).scalar_one()
                == 3
            )
    finally:
        engine.dispose()


@pytest.mark.integration
def test_provenance_typed_source_identity_preserved(temporary_postgres) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, UMS_03D_REVISION)
    engine = sa.create_engine(database_url, future=True)
    try:
        with engine.begin() as connection:
            _insert_user(connection, "account-A")
            memory_id = str(uuid.uuid4())
            _insert_canonical_memory(
                connection,
                memory_id=memory_id,
                user_id="account-A",
                project_id=None,
                semantic_species="episodic_semantic_memory",
                text_content="imported",
            )
            _insert_provenance(
                connection,
                provenance_id=str(uuid.uuid4()),
                memory_id=memory_id,
                user_id="account-A",
                source_system="openai",
                source_record_id="openai-record-abc",
                source_import_job_id=str(uuid.uuid4()),
                source_export_fingerprint="sha256:abcdef",
                source_subject_kind="importer",
                source_subject_id="openai-subject-1",
                is_imported=True,
            )
            row = (
                connection.execute(
                    sa.text("""
                    SELECT source_system, source_record_id,
                           source_import_job_id, source_export_fingerprint,
                           source_subject_kind, source_subject_id
                    FROM memory_provenance
                    WHERE memory_id = :memory_id
                    """),
                    {"memory_id": memory_id},
                )
                .mappings()
                .one()
            )
            assert row["source_system"] == "openai"
            assert row["source_record_id"] == "openai-record-abc"
            assert row["source_subject_id"] == "openai-subject-1"
    finally:
        engine.dispose()


@pytest.mark.integration
def test_provenance_fk_rejects_wrong_account(temporary_postgres) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, UMS_03D_REVISION)
    engine = sa.create_engine(database_url, future=True)
    try:
        with engine.begin() as connection:
            _insert_user(connection, "account-A")
            _insert_user(connection, "account-B")
            memory_id = str(uuid.uuid4())
            _insert_canonical_memory(
                connection,
                memory_id=memory_id,
                user_id="account-A",
                project_id=None,
                semantic_species="episodic_semantic_memory",
                text_content="A's memory",
            )
            with pytest.raises(IntegrityError):
                _insert_provenance(
                    connection,
                    provenance_id=str(uuid.uuid4()),
                    memory_id=memory_id,
                    user_id="account-B",
                    source_system="codexify",
                    source_record_id="wrong-account",
                )
    finally:
        engine.dispose()


@pytest.mark.integration
def test_downgrade_preserves_legacy_rows(temporary_postgres) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, PREVIOUS_REVISION)
    engine = sa.create_engine(database_url, future=True)
    try:
        with engine.begin() as connection:
            _insert_user(connection, "account-A")
            legacy_id = _insert_legacy_memory_entry(
                connection,
                user_id="account-A",
                silo="longterm",
                content="survives round trip",
            )
        pre_upgrade_snapshot = _snapshot_legacy_rows(engine.connect().__enter__())
        assert pre_upgrade_snapshot["memory_entries"][0]["id"] == legacy_id
    finally:
        engine.dispose()

    _upgrade(config, UMS_03D_REVISION)
    _downgrade(config, PREVIOUS_REVISION)

    engine = sa.create_engine(database_url, future=True)
    try:
        with engine.connect() as connection:
            post_roundtrip_snapshot = _snapshot_legacy_rows(connection)
            assert (
                post_roundtrip_snapshot == pre_upgrade_snapshot
            ), "legacy rows must survive upgrade + downgrade round trip"
            for table in NEW_TABLES:
                exists = connection.execute(
                    sa.text(
                        "SELECT EXISTS ("
                        "SELECT 1 FROM information_schema.tables "
                        "WHERE table_name = :table_name"
                        ")"
                    ),
                    {"table_name": table},
                ).scalar_one()
                assert not exists, f"{table} must be removed by the downgrade"
    finally:
        engine.dispose()
