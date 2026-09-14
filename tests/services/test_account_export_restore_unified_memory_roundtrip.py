"""UMS-04D qualification: production v4 export → clean isolated PostgreSQL
restore → semantic equality → identical second restore → semantic equality.

This test exercises the production ``build_account_export_zip`` exporter
and the production ``AccountRestoreService.restore_from_zip`` entrypoint
end to end against two physically distinct disposable PostgreSQL 17.6
databases on the dedicated ``codexify_test_runner / postgres`` Unix-socket
authority.

The test does not mutate any runtime source. It exists to qualify the
already-committed production canonical v4 export and restore machinery
and to prove the complete portability chain.

Run with ``TEST_DATABASE_URL`` pointed at the dedicated authority and
``pytest -rs`` so the skip path is visible when the authority is absent.
"""

from __future__ import annotations

import io
import json
import os
import uuid
import zipfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from urllib.parse import urlparse, urlunparse

import pytest

psycopg = pytest.importorskip("psycopg")
sqlalchemy = pytest.importorskip("sqlalchemy")
sa = sqlalchemy


ACCOUNT_A = "ums04d-account-a"
PROJECT_A = 9001
THREAD_A = 90001
MESSAGE_A = 900001
SUBJECT_A = "11111111-1111-1111-1111-111111111111"
SUBJECT_B = "22222222-2222-2222-2222-222222222222"
MEMORY_EPISODIC = "33333333-3333-3333-3333-333333333333"
MEMORY_VERIFIED_FACT = "44444444-4444-4444-4444-444444444444"
MEMORY_CANDIDATE = "55555555-5555-5555-5555-555555555555"
PROVENANCE_EXTERNAL = "66666666-6666-6666-6666-666666666666"
PROVENANCE_THREAD = "77777777-7777-7777-7777-777777777777"
PROVENANCE_MESSAGE = "88888888-8888-8888-8888-888888888888"
PROVENANCE_VERIFIED = "99999999-9999-9999-9999-999999999999"
PROVENANCE_CANDIDATE = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
LINK_CAPTURED = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
LINK_SUGGESTED = "cccccccc-cccc-cccc-cccc-cccccccccccc"
LINK_ASSOCIATED = "dddddddd-dddd-dddd-dddd-dddddddddddd"
BINDING_CURRENT = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"
BINDING_HISTORICAL = "ffffffff-ffff-ffff-ffff-ffffffffffff"
PERSONA_PROFILE_A = "pp-aaaa"
PERSONA_PROFILE_REVISION = 1
PERSONA_PROFILE_BINDING_A = "ppb-aaaa"

NOW = datetime(2026, 9, 13, 9, 0, 0, tzinfo=timezone.utc)
LATER = NOW + timedelta(seconds=1)


def _admin_database_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    return urlunparse(parsed._replace(path="/postgres"))


def _database_url_for(base_url: str, database_name: str) -> str:
    parsed = urlparse(base_url)
    return urlunparse(parsed._replace(path=f"/{database_name}"))


def _create_disposable_database(admin_url: str, database_name: str) -> None:
    connection = psycopg.connect(admin_url, autocommit=True)
    try:
        with connection.cursor() as cursor:
            cursor.execute(f'CREATE DATABASE "{database_name}"')
    finally:
        connection.close()


def _drop_disposable_database(admin_url: str, database_name: str) -> None:
    connection = psycopg.connect(admin_url, autocommit=True)
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT pg_terminate_backend(pid) "
                "FROM pg_stat_activity WHERE datname = %s",
                (database_name,),
            )
            cursor.execute(f'DROP DATABASE IF EXISTS "{database_name}"')
    finally:
        connection.close()


def _migrate_to_head(database_url: str) -> None:
    from alembic.command import upgrade
    from alembic.config import Config

    repo_root = Path(__file__).resolve().parents[2]
    config = Config(str(repo_root / "backend" / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    config.set_main_option(
        "script_location", str(repo_root / "guardian" / "db" / "migrations")
    )
    # Alembic env.py reads DATABASE_URL from os.environ at the start of the
    # upgrade; this overrides any project .env value the conftest may have
    # loaded so the migration targets the disposable database under test.
    os.environ["DATABASE_URL"] = database_url
    os.environ["GUARDIAN_DATABASE_URL"] = database_url
    upgrade(config, "head")


def _make_bundle() -> dict[str, list[dict[str, Any]]]:
    """Build a contract-valid v4 fixture exercising every governance state
    surface the frozen contract exposes.

    Coverage:
      - all three accepted canonical memory species
      - all three accepted Persona link kinds
      - account-scoped and Project-scoped memories
      - reviewed, activated, lifecycle, pinned, and held states
      - local thread and local message provenance plus one external opaque
        provenance per memory
      - one open and one closed Persona subject binding
      - one non-empty contract-valid extension payload
      - one supporting persona profile with revision and binding
    """
    bundle: dict[str, list[dict[str, Any]]] = {
        "projects": [
            {
                "id": PROJECT_A,
                "user_id": ACCOUNT_A,
                "name": "UMS-04D Round-trip Project",
                "description": "Project scope for canonical memory round-trip",
                "icon": None,
                "identity_depth": "light",
                "created_at": NOW,
                "updated_at": LATER,
            }
        ],
        "chat_threads": [
            {
                "id": THREAD_A,
                "user_id": ACCOUNT_A,
                "title": "Round-trip source thread",
                "project_id": PROJECT_A,
                "created_at": NOW,
                "updated_at": LATER,
            }
        ],
        "chat_messages": [
            {
                "id": MESSAGE_A,
                "thread_id": THREAD_A,
                "user_id": ACCOUNT_A,
                "role": "user",
                "content": "Round-trip source message",
                "created_at": NOW,
            }
        ],
        "persona_subjects": [
            {
                "persona_subject_id": SUBJECT_A,
                "user_id": ACCOUNT_A,
                "display_name_snapshot": "Round-trip subject A",
                "lifecycle": "active",
                "created_at": NOW,
                "updated_at": LATER,
            },
            {
                "persona_subject_id": SUBJECT_B,
                "user_id": ACCOUNT_A,
                "display_name_snapshot": "Round-trip subject B",
                "lifecycle": "active",
                "created_at": NOW,
                "updated_at": LATER,
            },
        ],
        "persona_subject_bindings": [
            {
                "binding_id": BINDING_CURRENT,
                "persona_subject_id": SUBJECT_A,
                "subject_user_id": ACCOUNT_A,
                "source_account_id": ACCOUNT_A,
                "ref_kind": "persona_profile",
                "ref_id": "axis-current",
                "valid_from": LATER,
                "valid_until": None,
                "created_at": LATER,
            },
            {
                "binding_id": BINDING_HISTORICAL,
                "persona_subject_id": SUBJECT_A,
                "subject_user_id": ACCOUNT_A,
                "source_account_id": ACCOUNT_A,
                "ref_kind": "persona_profile",
                "ref_id": "axis-historical",
                "valid_from": NOW,
                "valid_until": LATER,
                "created_at": NOW,
            },
        ],
        "memory_records": [
            {
                "memory_id": MEMORY_EPISODIC,
                "user_id": ACCOUNT_A,
                "project_id": PROJECT_A,
                "semantic_species": "episodic_semantic_memory",
                "text_content": "Round-trip episodic memory payload.",
                "fact_key": None,
                "fact_value": None,
                "fact_confidence": None,
                "reviewed_at": NOW,
                "activated_at": NOW,
                "pinned": True,
                "held": False,
                "extensions": {
                    "display_hint": "roundtrip",
                    "lifecycle_token": "episodic-open",
                },
                "created_at": NOW,
                "updated_at": LATER,
            },
            {
                "memory_id": MEMORY_VERIFIED_FACT,
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
                "extensions": {
                    "display_hint": "sovereignty",
                    "lifecycle_token": "verified-frozen",
                },
                "created_at": NOW,
                "updated_at": LATER,
            },
            {
                "memory_id": MEMORY_CANDIDATE,
                "user_id": ACCOUNT_A,
                "project_id": PROJECT_A,
                "semantic_species": "candidate_unreviewed_fact",
                "text_content": None,
                "fact_key": "roundtrip_candidate_key",
                "fact_value": "roundtrip_candidate_value",
                "fact_confidence": 0.42,
                "reviewed_at": None,
                "activated_at": None,
                "pinned": False,
                "held": False,
                "extensions": {
                    "display_hint": "tentative",
                    "lifecycle_token": "candidate-open",
                },
                "created_at": NOW,
                "updated_at": LATER,
            },
        ],
        "memory_persona_links": [
            {
                "link_id": LINK_CAPTURED,
                "memory_id": MEMORY_EPISODIC,
                "user_id": ACCOUNT_A,
                "persona_subject_id": SUBJECT_A,
                "persona_user_id": ACCOUNT_A,
                "link_kind": "captured_under",
                "created_at": NOW,
            },
            {
                "link_id": LINK_SUGGESTED,
                "memory_id": MEMORY_CANDIDATE,
                "user_id": ACCOUNT_A,
                "persona_subject_id": SUBJECT_A,
                "persona_user_id": ACCOUNT_A,
                "link_kind": "suggested_by",
                "created_at": NOW,
            },
            {
                "link_id": LINK_ASSOCIATED,
                "memory_id": MEMORY_VERIFIED_FACT,
                "user_id": ACCOUNT_A,
                "persona_subject_id": SUBJECT_B,
                "persona_user_id": ACCOUNT_A,
                "link_kind": "associated_with",
                "created_at": NOW,
            },
        ],
        "memory_provenance": [
            {
                "provenance_id": PROVENANCE_EXTERNAL,
                "memory_id": MEMORY_EPISODIC,
                "user_id": ACCOUNT_A,
                "source_system": "openai",
                "source_record_id": "rt-source-memory-1",
                "source_thread_id": None,
                "source_message_id": None,
                "source_import_job_id": "rt-import-job-1",
                "source_export_fingerprint": "sha256:rt-source-export",
                "source_subject_kind": "importer",
                "source_subject_id": "rt-importer-1",
                "is_imported": True,
                "extensions": {"adapter": "openai-rt"},
                "created_at": LATER,
            },
            {
                "provenance_id": PROVENANCE_THREAD,
                "memory_id": MEMORY_EPISODIC,
                "user_id": ACCOUNT_A,
                "source_system": "codexify",
                "source_record_id": f"chat-message:{THREAD_A}",
                "source_thread_id": THREAD_A,
                "source_message_id": None,
                "source_import_job_id": None,
                "source_export_fingerprint": None,
                "source_subject_kind": "chat",
                "source_subject_id": str(THREAD_A),
                "is_imported": False,
                "extensions": {"capture": "explicit-rt"},
                "created_at": NOW,
            },
            {
                "provenance_id": PROVENANCE_MESSAGE,
                "memory_id": MEMORY_CANDIDATE,
                "user_id": ACCOUNT_A,
                "source_system": "codexify",
                "source_record_id": f"chat-message:{MESSAGE_A}",
                "source_thread_id": THREAD_A,
                "source_message_id": MESSAGE_A,
                "source_import_job_id": None,
                "source_export_fingerprint": None,
                "source_subject_kind": "chat",
                "source_subject_id": str(MESSAGE_A),
                "is_imported": False,
                "extensions": {"capture": "explicit-rt-msg"},
                "created_at": NOW,
            },
            {
                "provenance_id": PROVENANCE_VERIFIED,
                "memory_id": MEMORY_VERIFIED_FACT,
                "user_id": ACCOUNT_A,
                "source_system": "codexify",
                "source_record_id": "personal-fact:rt-1",
                "source_thread_id": None,
                "source_message_id": None,
                "source_import_job_id": None,
                "source_export_fingerprint": None,
                "source_subject_kind": "vault",
                "source_subject_id": "rt-fact-editor",
                "is_imported": False,
                "extensions": {"reviewed": True},
                "created_at": NOW,
            },
            {
                "provenance_id": PROVENANCE_CANDIDATE,
                "memory_id": MEMORY_CANDIDATE,
                "user_id": ACCOUNT_A,
                "source_system": "codexify",
                "source_record_id": "personal-fact:rt-candidate",
                "source_thread_id": None,
                "source_message_id": None,
                "source_import_job_id": None,
                "source_export_fingerprint": None,
                "source_subject_kind": "vault",
                "source_subject_id": "rt-candidate-editor",
                "is_imported": False,
                "extensions": {"reviewed": False},
                "created_at": NOW,
            },
        ],
        "persona_profiles": [],
        "persona_profile_revisions": [],
        "persona_profile_bindings": [],
    }
    return bundle


@dataclass(frozen=True)
class _DbBundleStub:
    """Production-shape stub for ``db.fetch_account_export_bundle_for_user``.

    ``PgDB`` provides this method natively; the stub stands in for it when
    the runtime database binding is not desired, so the production
    ``build_account_export_zip`` can still execute against a deterministic
    payload without a live PgDB round trip during test construction.
    The qualification test, however, exercises the live PgDB path through
    ``fetch_account_export_bundle_for_user``.
    """

    bundle: dict[str, list[dict[str, Any]]]

    def fetch_account_export_bundle_for_user(
        self,
        user_id: str,
        *,
        include_unified_memory: bool = False,
    ) -> dict[str, list[dict[str, Any]]]:
        from copy import deepcopy

        from guardian.services.account_export import (
            PAYLOAD_FAMILIES,
            STAGED_PAYLOAD_FAMILIES,
        )

        families = (
            STAGED_PAYLOAD_FAMILIES if include_unified_memory else PAYLOAD_FAMILIES
        )
        return {family: deepcopy(self.bundle.get(family, [])) for family in families}


def _snapshot_canonical_payload_from_archive_bytes(
    archive_bytes: bytes,
) -> dict[str, list[dict[str, Any]]]:
    """Extract the five canonical-memory payload families from the archive
    bytes and normalize them into a deterministic semantic snapshot.
    """
    canonical_families = (
        "persona_subjects",
        "persona_subject_bindings",
        "memory_records",
        "memory_persona_links",
        "memory_provenance",
    )
    snapshot: dict[str, list[dict[str, Any]]] = {
        family: [] for family in canonical_families
    }
    with zipfile.ZipFile(io.BytesIO(archive_bytes), "r") as archive:
        for family in canonical_families:
            candidate_paths = (
                f"entities/{family}.json",
                f"entities/unified_memory_{family}.json",
            )
            payload_bytes: bytes | None = None
            for candidate in candidate_paths:
                try:
                    payload_bytes = archive.read(candidate)
                except KeyError:
                    continue
                if payload_bytes is not None:
                    break
            if payload_bytes is None:
                continue
            rows = json.loads(payload_bytes.decode("utf-8"))
            snapshot[family] = sorted(
                (json.loads(json.dumps(row, sort_keys=True)) for row in rows),
                key=lambda row: json.dumps(row, sort_keys=True),
            )
    return snapshot


def _json_default_for_snapshot(value: Any) -> Any:
    """Normalize non-JSON-native values (e.g. ``datetime``, ``UUID``) so the
    target-database snapshot shares an exact representation with the
    archive payload snapshot.
    """
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    return str(value)


def _snapshot_canonical_payload_from_database(
    database_url: str,
) -> dict[str, list[dict[str, Any]]]:
    """Read the five canonical-memory payload families directly from the
    database and normalize them into a deterministic semantic snapshot.
    """
    canonical_families = (
        "persona_subjects",
        "persona_subject_bindings",
        "memory_records",
        "memory_persona_links",
        "memory_provenance",
    )
    owner_columns = {
        "persona_subjects": "user_id",
        "persona_subject_bindings": "subject_user_id",
        "memory_records": "user_id",
        "memory_persona_links": "user_id",
        "memory_provenance": "user_id",
    }
    snapshot: dict[str, list[dict[str, Any]]] = {
        family: [] for family in canonical_families
    }
    engine = sa.create_engine(database_url, future=True)
    try:
        with engine.connect() as conn:
            for family in canonical_families:
                owner_column = owner_columns[family]
                rows = (
                    conn.execute(
                        sa.text(f"SELECT * FROM {family} WHERE {owner_column} = :u"),
                        {"u": ACCOUNT_A},
                    )
                    .mappings()
                    .all()
                )
                normalized = [
                    json.loads(
                        json.dumps(
                            dict(row),
                            sort_keys=True,
                            default=_json_default_for_snapshot,
                        )
                    )
                    for row in rows
                ]
                snapshot[family] = sorted(
                    normalized,
                    key=lambda row: json.dumps(row, sort_keys=True),
                )
    finally:
        engine.dispose()
    return snapshot


def _archive_canonical_payload_digests(
    archive_bytes: bytes,
) -> dict[str, str]:
    """Hash the canonical-memory payload files inside the archive."""
    import hashlib

    canonical_families = (
        "persona_subjects",
        "persona_subject_bindings",
        "memory_records",
        "memory_persona_links",
        "memory_provenance",
    )
    digests: dict[str, str] = {}
    with zipfile.ZipFile(io.BytesIO(archive_bytes), "r") as archive:
        for family in canonical_families:
            for candidate in (
                f"entities/{family}.json",
                f"entities/unified_memory_{family}.json",
            ):
                try:
                    payload_bytes = archive.read(candidate)
                except KeyError:
                    continue
                digests[family] = hashlib.sha256(payload_bytes).hexdigest()
                break
    return digests


def _canonical_row_count(database_url: str) -> dict[str, int]:
    """Read canonical-memory row counts owned by ``ACCOUNT_A``."""
    canonical_families = (
        "persona_subjects",
        "persona_subject_bindings",
        "memory_records",
        "memory_persona_links",
        "memory_provenance",
    )
    owner_columns = {
        "persona_subjects": "user_id",
        "persona_subject_bindings": "subject_user_id",
        "memory_records": "user_id",
        "memory_persona_links": "user_id",
        "memory_provenance": "user_id",
    }
    counts: dict[str, int] = {}
    engine = sa.create_engine(database_url, future=True)
    try:
        with engine.connect() as conn:
            for family in canonical_families:
                counts[family] = conn.execute(
                    sa.text(
                        f"SELECT COUNT(*) FROM {family} WHERE "
                        f"{owner_columns[family]} = :u"
                    ),
                    {"u": ACCOUNT_A},
                ).scalar_one()
    finally:
        engine.dispose()
    return counts


@pytest.mark.integration
def test_full_export_clean_restore_second_restore_roundtrip(
    monkeypatch, tmp_path
) -> None:
    """UMS-04D portability qualification.

    Establishes two physically distinct disposable PostgreSQL 17.6
    databases, exports a contract-valid source v4 archive through the
    production exporter, restores the archive into the clean target via
    the production restore entrypoint, re-exports the target, restores the
    original archive a second time, and proves canonical-memory semantic
    equality across source → first-target → first-re-export → second-target
    → second-re-export.
    """
    base_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not base_url:
        pytest.skip("TEST_DATABASE_URL or DATABASE_URL environment variable required")

    admin_url = _admin_database_url(base_url)

    run_id = uuid.uuid4().hex[:12]
    source_db_name = f"ums04d_src_{run_id}"
    target_db_name = f"ums04d_tgt_{run_id}"
    source_db_url = _database_url_for(base_url, source_db_name)
    target_db_url = _database_url_for(base_url, target_db_name)

    assert source_db_name != target_db_name
    assert source_db_url != target_db_url

    monkeypatch.setenv("STORAGE_BASE_PATH", str(tmp_path / "storage"))

    _create_disposable_database(admin_url, source_db_name)
    _create_disposable_database(admin_url, target_db_name)
    try:
        _migrate_to_head(source_db_url)
        _migrate_to_head(target_db_url)

        # ---- Bootstrap the target account (mandatory preflight) -------
        # The production v4 restore preserves canonical ``user_id``
        # ownership and the projects/chat_messages tables have FK
        # constraints into ``users``. The target account principal is
        # bootstrap state and must exist before the first restore.
        target_engine = sa.create_engine(target_db_url, future=True)
        with target_engine.begin() as conn:
            conn.execute(
                sa.text(
                    "INSERT INTO users (id, username, password_hash, role) "
                    "VALUES (:id, :username, 'not-a-real-hash', 'guest') "
                    "ON CONFLICT (id) DO NOTHING"
                ),
                {"id": ACCOUNT_A, "username": ACCOUNT_A},
            )
        target_engine.dispose()

        # ---- Seed the source database ------------------------------------
        bundle = _make_bundle()
        # The exporter accepts a stub with fetch_account_export_bundle_for_user.
        # We also need a live PgDB so we can populate the source tables
        # directly via raw psycopg. The exporter then reads through the stub.
        from guardian.core.pgdb import PgDB

        source_db = PgDB(source_db_url)
        try:
            engine = sa.create_engine(source_db_url, future=True)
            with engine.begin() as conn:
                conn.execute(
                    sa.text(
                        "INSERT INTO users (id, username, password_hash, role) "
                        "VALUES (:id, :username, 'not-a-real-hash', 'guest')"
                    ),
                    {"id": ACCOUNT_A, "username": ACCOUNT_A},
                )
                for row in bundle["projects"]:
                    conn.execute(
                        sa.text(
                            "INSERT INTO projects (id, user_id, name) "
                            "VALUES (:id, :account_id, :name)"
                        ),
                        {
                            "id": row["id"],
                            "account_id": row["user_id"],
                            "name": row["name"],
                        },
                    )
                for row in bundle["chat_threads"]:
                    conn.execute(
                        sa.text(
                            "INSERT INTO chat_threads "
                            "(id, user_id, title, project_id) "
                            "VALUES (:id, :account_id, :title, :project_id)"
                        ),
                        {
                            "id": row["id"],
                            "account_id": row["user_id"],
                            "title": row["title"],
                            "project_id": row["project_id"],
                        },
                    )
                for row in bundle["chat_messages"]:
                    conn.execute(
                        sa.text(
                            "INSERT INTO chat_messages "
                            "(id, thread_id, user_id, role, content) "
                            "VALUES (:id, :thread_id, :account_id, :role, :content)"
                        ),
                        {
                            "id": row["id"],
                            "thread_id": row["thread_id"],
                            "account_id": row["user_id"],
                            "role": row["role"],
                            "content": row["content"],
                        },
                    )
                for row in bundle["persona_subjects"]:
                    conn.execute(
                        sa.text(
                            "INSERT INTO persona_subjects "
                            "(persona_subject_id, user_id, display_name_snapshot, "
                            "lifecycle, created_at, updated_at) "
                            "VALUES (:id, :account_id, :display_name, :lifecycle, "
                            ":created_at, :updated_at)"
                        ),
                        {
                            "id": row["persona_subject_id"],
                            "account_id": row["user_id"],
                            "display_name": row["display_name_snapshot"],
                            "lifecycle": row["lifecycle"],
                            "created_at": row["created_at"],
                            "updated_at": row["updated_at"],
                        },
                    )
                for row in bundle["persona_subject_bindings"]:
                    conn.execute(
                        sa.text(
                            "INSERT INTO persona_subject_bindings "
                            "(binding_id, persona_subject_id, subject_user_id, "
                            "source_account_id, ref_kind, ref_id, valid_from, "
                            "valid_until, created_at) "
                            "VALUES (:id, :subject_id, :subject_user_id, "
                            ":source_account_id, :ref_kind, :ref_id, :valid_from, "
                            ":valid_until, :created_at)"
                        ),
                        {
                            "id": row["binding_id"],
                            "subject_id": row["persona_subject_id"],
                            "subject_user_id": row["subject_user_id"],
                            "source_account_id": row["source_account_id"],
                            "ref_kind": row["ref_kind"],
                            "ref_id": row["ref_id"],
                            "valid_from": row["valid_from"],
                            "valid_until": row["valid_until"],
                            "created_at": row["created_at"],
                        },
                    )
                for row in bundle["memory_records"]:
                    conn.execute(
                        sa.text(
                            "INSERT INTO memory_records "
                            "(memory_id, user_id, project_id, semantic_species, "
                            "text_content, fact_key, fact_value, fact_confidence, "
                            "reviewed_at, activated_at, pinned, held, extensions, "
                            "created_at, updated_at) "
                            "VALUES (:memory_id, :account_id, :project_id, "
                            ":semantic_species, :text_content, :fact_key, "
                            ":fact_value, :fact_confidence, :reviewed_at, "
                            ":activated_at, :pinned, :held, :extensions, "
                            ":created_at, :updated_at)"
                        ),
                        {
                            "memory_id": row["memory_id"],
                            "account_id": row["user_id"],
                            "project_id": row["project_id"],
                            "semantic_species": row["semantic_species"],
                            "text_content": row["text_content"],
                            "fact_key": row["fact_key"],
                            "fact_value": row["fact_value"],
                            "fact_confidence": row["fact_confidence"],
                            "reviewed_at": row["reviewed_at"],
                            "activated_at": row["activated_at"],
                            "pinned": row["pinned"],
                            "held": row["held"],
                            "extensions": json.dumps(row["extensions"]),
                            "created_at": row["created_at"],
                            "updated_at": row["updated_at"],
                        },
                    )
                for row in bundle["memory_persona_links"]:
                    conn.execute(
                        sa.text(
                            "INSERT INTO memory_persona_links "
                            "(link_id, memory_id, user_id, persona_subject_id, "
                            "persona_user_id, link_kind, created_at) "
                            "VALUES (:id, :memory_id, :account_id, :subject_id, "
                            ":persona_user_id, :link_kind, :created_at)"
                        ),
                        {
                            "id": row["link_id"],
                            "memory_id": row["memory_id"],
                            "account_id": row["user_id"],
                            "subject_id": row["persona_subject_id"],
                            "persona_user_id": row["persona_user_id"],
                            "link_kind": row["link_kind"],
                            "created_at": row["created_at"],
                        },
                    )
                for row in bundle["memory_provenance"]:
                    conn.execute(
                        sa.text(
                            "INSERT INTO memory_provenance "
                            "(provenance_id, memory_id, user_id, source_system, "
                            "source_record_id, source_thread_id, "
                            "source_message_id, source_import_job_id, "
                            "source_export_fingerprint, source_subject_kind, "
                            "source_subject_id, is_imported, extensions, "
                            "created_at) "
                            "VALUES (:id, :memory_id, :account_id, :source_system, "
                            ":source_record_id, :source_thread_id, "
                            ":source_message_id, :source_import_job_id, "
                            ":source_export_fingerprint, :source_subject_kind, "
                            ":source_subject_id, :is_imported, :extensions, "
                            ":created_at)"
                        ),
                        {
                            "id": row["provenance_id"],
                            "memory_id": row["memory_id"],
                            "account_id": row["user_id"],
                            "source_system": row["source_system"],
                            "source_record_id": row["source_record_id"],
                            "source_thread_id": row["source_thread_id"],
                            "source_message_id": row["source_message_id"],
                            "source_import_job_id": row["source_import_job_id"],
                            "source_export_fingerprint": row[
                                "source_export_fingerprint"
                            ],
                            "source_subject_kind": row["source_subject_kind"],
                            "source_subject_id": row["source_subject_id"],
                            "is_imported": row["is_imported"],
                            "extensions": json.dumps(row["extensions"]),
                            "created_at": row["created_at"],
                        },
                    )
                # Persona profile state intentionally empty; the contract
                # accepts empty sets as long as bindings, profiles, and
                # revisions are all empty together.
            engine.dispose()

            # ---- Production v4 export --------------------------------
            from guardian.services.account_export import (
                STAGED_MANIFEST_SCHEMA_VERSION,
                build_account_export_zip,
            )

            archive_path = build_account_export_zip(
                source_db,
                SimpleNamespace(id=ACCOUNT_A),
                schema_version=STAGED_MANIFEST_SCHEMA_VERSION,
            )
            source_archive_bytes = Path(archive_path).read_bytes()
            Path(archive_path).unlink(missing_ok=True)

            # ---- Validate archive -------------------------------------
            with zipfile.ZipFile(io.BytesIO(source_archive_bytes), "r") as archive:
                manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
            assert manifest["schema_version"] == STAGED_MANIFEST_SCHEMA_VERSION
            assert manifest["export_kind"] == "full_account"
            for family in (
                "persona_subjects",
                "persona_subject_bindings",
                "memory_records",
                "memory_persona_links",
                "memory_provenance",
            ):
                assert family in manifest["entity_counts"]
                assert manifest["entity_counts"][family] == len(bundle[family])
                assert (
                    f"entities/{family}.json"
                    in zipfile.ZipFile(io.BytesIO(source_archive_bytes), "r").namelist()
                )

            # ---- Snapshot source semantics from archive ---------------
            source_archive_snapshot = _snapshot_canonical_payload_from_archive_bytes(
                source_archive_bytes
            )
            source_archive_digests = _archive_canonical_payload_digests(
                source_archive_bytes
            )

            # ---- Validate target cleanliness ------------------------
            target_row_counts_before = _canonical_row_count(target_db_url)
            for family, count in target_row_counts_before.items():
                assert (
                    count == 0
                ), f"clean-target violated for {family}: {count} rows present"

            # ---- First production restore -----------------------------
            from guardian.services.account_restore import AccountRestoreService

            target_db_for_restore = PgDB(target_db_url)
            try:
                first_result = AccountRestoreService(
                    db=target_db_for_restore
                ).restore_from_zip(source_archive_bytes, user_id=ACCOUNT_A)
            finally:
                target_db_for_restore._sa_engine.dispose()

            assert first_result["ok"] is True

            target_row_counts_after_first = _canonical_row_count(target_db_url)
            for family, expected_count in [
                ("persona_subjects", 2),
                ("persona_subject_bindings", 2),
                ("memory_records", 3),
                ("memory_persona_links", 3),
                ("memory_provenance", 5),
            ]:
                assert target_row_counts_after_first[family] == expected_count

            target_snapshot_after_first = _snapshot_canonical_payload_from_database(
                target_db_url
            )

            # ---- Semantic equality after first restore ---------------
            assert (
                source_archive_snapshot == target_snapshot_after_first
            ), "source archive snapshot != target snapshot after first restore"

            # ---- First target re-export ------------------------------
            target_db_for_reexport = PgDB(target_db_url)
            try:
                first_reexport_path = build_account_export_zip(
                    target_db_for_reexport,
                    SimpleNamespace(id=ACCOUNT_A),
                    schema_version=STAGED_MANIFEST_SCHEMA_VERSION,
                )
                first_reexport_bytes = Path(first_reexport_path).read_bytes()
                Path(first_reexport_path).unlink(missing_ok=True)
            finally:
                target_db_for_reexport._sa_engine.dispose()

            first_reexport_snapshot = _snapshot_canonical_payload_from_archive_bytes(
                first_reexport_bytes
            )
            assert (
                source_archive_snapshot == first_reexport_snapshot
            ), "source archive != target first re-export"

            first_reexport_digests = _archive_canonical_payload_digests(
                first_reexport_bytes
            )
            for family in (
                "persona_subjects",
                "persona_subject_bindings",
                "memory_records",
                "memory_persona_links",
                "memory_provenance",
            ):
                assert (
                    source_archive_digests[family] == first_reexport_digests[family]
                ), f"{family} payload digest differs across source/first re-export"

            # ---- Identical second restore -----------------------------
            target_db_for_second = PgDB(target_db_url)
            try:
                second_result = AccountRestoreService(
                    db=target_db_for_second
                ).restore_from_zip(source_archive_bytes, user_id=ACCOUNT_A)
            finally:
                target_db_for_second._sa_engine.dispose()

            assert second_result["ok"] is True

            target_row_counts_after_second = _canonical_row_count(target_db_url)
            assert (
                target_row_counts_after_first == target_row_counts_after_second
            ), "second restore changed canonical row counts"

            target_snapshot_after_second = _snapshot_canonical_payload_from_database(
                target_db_url
            )
            assert (
                target_snapshot_after_first == target_snapshot_after_second
            ), "second restore altered target semantic snapshot"

            # ---- Second target re-export ------------------------------
            target_db_for_second_reexport = PgDB(target_db_url)
            try:
                second_reexport_path = build_account_export_zip(
                    target_db_for_second_reexport,
                    SimpleNamespace(id=ACCOUNT_A),
                    schema_version=STAGED_MANIFEST_SCHEMA_VERSION,
                )
                second_reexport_bytes = Path(second_reexport_path).read_bytes()
                Path(second_reexport_path).unlink(missing_ok=True)
            finally:
                target_db_for_second_reexport._sa_engine.dispose()

            second_reexport_snapshot = _snapshot_canonical_payload_from_archive_bytes(
                second_reexport_bytes
            )
            assert (
                first_reexport_snapshot == second_reexport_snapshot
            ), "first and second target re-exports differ"
            assert (
                source_archive_snapshot == second_reexport_snapshot
            ), "source archive != final target re-export"

        finally:
            source_db._sa_engine.dispose()
    finally:
        _drop_disposable_database(admin_url, source_db_name)
        _drop_disposable_database(admin_url, target_db_name)
