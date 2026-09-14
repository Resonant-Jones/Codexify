from __future__ import annotations

import hashlib
import io
import json
import os
import zipfile
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import sqlalchemy as sa

from guardian.core import pgdb as pgdb_module
from guardian.services.account_export import (
    MANIFEST_SCHEMA_VERSION,
    PAYLOAD_FAMILIES,
    STAGED_MANIFEST_SCHEMA_VERSION,
    STAGED_PAYLOAD_FAMILIES,
    UNIFIED_MEMORY_PAYLOAD_FAMILIES,
    build_account_export_zip,
)
from guardian.services.account_restore import (
    AccountRestoreService,
    AccountRestoreValidationError,
)
from tests.migration.test_canonical_memory_persistence_migration import _upgrade
from tests.migration.test_canonical_memory_persistence_migration import (  # noqa: PLC0414
    temporary_postgres as temporary_postgres,
)

ACCOUNT_A = "account-a"
ACCOUNT_B = "account-b"
PROJECT_A = 101
PROJECT_B = 202
THREAD_A = 1001
MESSAGE_A = 2001
SUBJECT_A = "11111111-1111-1111-1111-111111111111"
SUBJECT_B = "22222222-2222-2222-2222-222222222222"
MEMORY_A = "33333333-3333-3333-3333-333333333333"
MEMORY_A_FACT = "44444444-4444-4444-4444-444444444444"
MEMORY_B = "55555555-5555-5555-5555-555555555555"
NOW = "2026-09-10T12:00:00+00:00"
LATER = "2026-09-10T13:00:00+00:00"

EXPECTED_UNIFIED_MEMORY_FIELDS = {
    "persona_subjects": {
        "persona_subject_id",
        "user_id",
        "display_name_snapshot",
        "lifecycle",
        "created_at",
        "updated_at",
    },
    "persona_subject_bindings": {
        "binding_id",
        "persona_subject_id",
        "subject_user_id",
        "source_account_id",
        "ref_kind",
        "ref_id",
        "valid_from",
        "valid_until",
        "created_at",
    },
    "memory_records": {
        "memory_id",
        "user_id",
        "project_id",
        "semantic_species",
        "text_content",
        "fact_key",
        "fact_value",
        "fact_confidence",
        "reviewed_at",
        "activated_at",
        "pinned",
        "held",
        "extensions",
        "created_at",
        "updated_at",
    },
    "memory_persona_links": {
        "link_id",
        "memory_id",
        "user_id",
        "persona_subject_id",
        "persona_user_id",
        "link_kind",
        "created_at",
    },
    "memory_provenance": {
        "provenance_id",
        "memory_id",
        "user_id",
        "source_system",
        "source_record_id",
        "source_thread_id",
        "source_message_id",
        "source_import_job_id",
        "source_export_fingerprint",
        "source_subject_kind",
        "source_subject_id",
        "is_imported",
        "extensions",
        "created_at",
    },
}


def _empty_bundle() -> dict[str, list[dict[str, Any]]]:
    return {family: [] for family in STAGED_PAYLOAD_FAMILIES}


def _unified_memory_bundle() -> dict[str, list[dict[str, Any]]]:
    bundle = _empty_bundle()
    bundle["projects"] = [
        {
            "id": PROJECT_A,
            "user_id": ACCOUNT_A,
            "name": "Account A Project",
            "description": "Canonical Project scope",
            "icon": None,
            "identity_depth": "light",
            "created_at": NOW,
            "updated_at": LATER,
        }
    ]
    bundle["chat_threads"] = [
        {
            "id": THREAD_A,
            "user_id": ACCOUNT_A,
            "title": "Source thread",
            "project_id": PROJECT_A,
            "created_at": NOW,
            "updated_at": LATER,
        }
    ]
    bundle["chat_messages"] = [
        {
            "id": MESSAGE_A,
            "thread_id": THREAD_A,
            "role": "user",
            "content": "Remember this exactly.",
            "created_at": NOW,
        }
    ]
    bundle["persona_subjects"] = [
        {
            "persona_subject_id": SUBJECT_A,
            "user_id": ACCOUNT_A,
            "display_name_snapshot": "Axis",
            "lifecycle": "active",
            "created_at": NOW,
            "updated_at": LATER,
        }
    ]
    bundle["persona_subject_bindings"] = [
        {
            "binding_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
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
            "binding_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "persona_subject_id": SUBJECT_A,
            "subject_user_id": ACCOUNT_A,
            "source_account_id": ACCOUNT_A,
            "ref_kind": "persona_profile",
            "ref_id": "axis-historical",
            "valid_from": NOW,
            "valid_until": LATER,
            "created_at": NOW,
        },
    ]
    bundle["memory_records"] = [
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
            "extensions": {"display_hint": "sovereignty"},
            "created_at": NOW,
            "updated_at": LATER,
        },
        {
            "memory_id": MEMORY_A,
            "user_id": ACCOUNT_A,
            "project_id": PROJECT_A,
            "semantic_species": "episodic_semantic_memory",
            "text_content": "The network should remain local-first.",
            "fact_key": None,
            "fact_value": None,
            "fact_confidence": None,
            "reviewed_at": NOW,
            "activated_at": NOW,
            "pinned": True,
            "held": False,
            "extensions": {"display_hint": "architecture"},
            "created_at": NOW,
            "updated_at": LATER,
        },
    ]
    bundle["memory_persona_links"] = [
        {
            "link_id": "77777777-7777-7777-7777-777777777777",
            "memory_id": MEMORY_A_FACT,
            "user_id": ACCOUNT_A,
            "persona_subject_id": SUBJECT_A,
            "persona_user_id": ACCOUNT_A,
            "link_kind": "associated_with",
            "created_at": LATER,
        },
        {
            "link_id": "66666666-6666-6666-6666-666666666666",
            "memory_id": MEMORY_A,
            "user_id": ACCOUNT_A,
            "persona_subject_id": SUBJECT_A,
            "persona_user_id": ACCOUNT_A,
            "link_kind": "captured_under",
            "created_at": NOW,
        },
    ]
    bundle["memory_provenance"] = [
        {
            "provenance_id": "99999999-9999-9999-9999-999999999999",
            "memory_id": MEMORY_A,
            "user_id": ACCOUNT_A,
            "source_system": "openai",
            "source_record_id": "source-memory-1",
            "source_thread_id": None,
            "source_message_id": None,
            "source_import_job_id": "import-job-1",
            "source_export_fingerprint": "sha256:source-export",
            "source_subject_kind": "importer",
            "source_subject_id": "importer-1",
            "is_imported": True,
            "extensions": {"adapter": "openai-v1"},
            "created_at": LATER,
        },
        {
            "provenance_id": "88888888-8888-8888-8888-888888888888",
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
            "extensions": {"capture": "explicit"},
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
            "extensions": {"reviewed": True},
            "created_at": NOW,
        },
    ]
    return bundle


class StagedExportDB:
    def __init__(self, bundle: dict[str, list[dict[str, Any]]] | None = None):
        self.bundle = bundle or _unified_memory_bundle()
        self.calls: list[tuple[str, bool]] = []

    def fetch_account_export_bundle_for_user(
        self,
        user_id: str,
        *,
        include_unified_memory: bool = False,
    ) -> dict[str, list[dict[str, Any]]]:
        self.calls.append((user_id, include_unified_memory))
        families = (
            STAGED_PAYLOAD_FAMILIES if include_unified_memory else PAYLOAD_FAMILIES
        )
        return {family: deepcopy(self.bundle.get(family, [])) for family in families}


def _archive_bytes(
    db: Any,
    tmp_path: Path,
    *,
    schema_version: str | None = None,
) -> bytes:
    os.environ.setdefault("STORAGE_BASE_PATH", str(tmp_path / "storage"))
    path = build_account_export_zip(
        db,
        SimpleNamespace(id=ACCOUNT_A),
        app_version="test-version",
        schema_version=schema_version,
    )
    try:
        return Path(path).read_bytes()
    finally:
        Path(path).unlink(missing_ok=True)


def _read_archive(
    archive_bytes: bytes,
) -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]], tuple[str, ...]]:
    with zipfile.ZipFile(io.BytesIO(archive_bytes), "r") as archive:
        manifest = json.loads(archive.read("manifest.json"))
        payloads = {
            family: json.loads(archive.read(f"entities/{family}.json"))
            for family in manifest["included_families"]
        }
        return manifest, payloads, tuple(archive.namelist())


@pytest.mark.parametrize("schema_version", [None, MANIFEST_SCHEMA_VERSION])
def test_default_and_explicit_v3_remain_v3(tmp_path: Path, schema_version: str | None):
    db = StagedExportDB()
    manifest, _payloads, archive_names = _read_archive(
        _archive_bytes(db, tmp_path, schema_version=schema_version)
    )

    assert manifest["schema_version"] == MANIFEST_SCHEMA_VERSION
    assert manifest["included_families"] == list(PAYLOAD_FAMILIES)
    assert manifest["compatibility"]["restore_mode"] == "metadata_only"
    assert db.calls == [(ACCOUNT_A, False)]
    for family in UNIFIED_MEMORY_PAYLOAD_FAMILIES:
        assert f"entities/{family}.json" not in archive_names
        assert family not in manifest["entity_counts"]


def test_unsupported_export_schema_fails_closed(tmp_path: Path):
    with pytest.raises(
        RuntimeError,
        match="unsupported_account_export_schema_version:account-export.v5",
    ):
        _archive_bytes(
            StagedExportDB(),
            tmp_path,
            schema_version="account-export.v5",
        )


def test_explicit_v4_serializes_exact_canonical_graph_and_manifest(tmp_path: Path):
    db = StagedExportDB()
    manifest, payloads, archive_names = _read_archive(
        _archive_bytes(
            db,
            tmp_path,
            schema_version=STAGED_MANIFEST_SCHEMA_VERSION,
        )
    )

    assert db.calls == [(ACCOUNT_A, True)]
    assert manifest["schema_version"] == STAGED_MANIFEST_SCHEMA_VERSION
    assert manifest["included_families"] == list(STAGED_PAYLOAD_FAMILIES)
    assert tuple(manifest["included_families"][-5:]) == (
        UNIFIED_MEMORY_PAYLOAD_FAMILIES
    )
    assert manifest["compatibility"]["restore_mode"] == "unsupported"
    assert manifest["compatibility"]["restore_supported"] is False
    assert [name for name in archive_names if name.startswith("entities/")][-5:] == [
        f"entities/{family}.json" for family in UNIFIED_MEMORY_PAYLOAD_FAMILIES
    ]

    for family, expected_fields in EXPECTED_UNIFIED_MEMORY_FIELDS.items():
        assert payloads[family]
        assert all(set(row) == expected_fields for row in payloads[family])
        path = f"entities/{family}.json"
        assert manifest["entity_counts"][family] == len(payloads[family])
        assert path in manifest["integrity"]["payload_files"]
        assert path in manifest["integrity"]["files"]

    assert [row["persona_subject_id"] for row in payloads["persona_subjects"]] == [
        SUBJECT_A
    ]
    assert [row["binding_id"] for row in payloads["persona_subject_bindings"]] == [
        "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
    ]
    assert payloads["persona_subject_bindings"][0]["valid_until"] == LATER
    assert payloads["persona_subject_bindings"][1]["valid_until"] is None
    assert [row["memory_id"] for row in payloads["memory_records"]] == [
        MEMORY_A,
        MEMORY_A_FACT,
    ]

    episodic = payloads["memory_records"][0]
    assert episodic == {
        "memory_id": MEMORY_A,
        "user_id": ACCOUNT_A,
        "project_id": PROJECT_A,
        "semantic_species": "episodic_semantic_memory",
        "text_content": "The network should remain local-first.",
        "fact_key": None,
        "fact_value": None,
        "fact_confidence": None,
        "reviewed_at": NOW,
        "activated_at": NOW,
        "pinned": True,
        "held": False,
        "extensions": {"display_hint": "architecture"},
        "created_at": NOW,
        "updated_at": LATER,
    }
    fact = payloads["memory_records"][1]
    assert fact["semantic_species"] == "verified_personal_fact"
    assert fact["fact_key"] == "preferred_mode"
    assert fact["fact_value"] == "local-first"
    assert fact["fact_confidence"] == 0.95
    assert fact["held"] is True
    assert fact["extensions"] == {"display_hint": "sovereignty"}

    assert [row["memory_id"] for row in payloads["memory_persona_links"]] == [
        MEMORY_A,
        MEMORY_A_FACT,
    ]
    assert all(
        row["persona_subject_id"] == SUBJECT_A
        for row in payloads["memory_persona_links"]
    )
    memory_a_provenance = [
        row for row in payloads["memory_provenance"] if row["memory_id"] == MEMORY_A
    ]
    assert [row["provenance_id"] for row in memory_a_provenance] == [
        "88888888-8888-8888-8888-888888888888",
        "99999999-9999-9999-9999-999999999999",
    ]
    assert {row["source_system"] for row in memory_a_provenance} == {
        "codexify",
        "openai",
    }
    assert not any("compatibility" in family for family in payloads)


def test_repeated_v4_serialization_preserves_identity_and_row_order(tmp_path: Path):
    first_manifest, first_payloads, _ = _read_archive(
        _archive_bytes(
            StagedExportDB(),
            tmp_path,
            schema_version=STAGED_MANIFEST_SCHEMA_VERSION,
        )
    )
    second_manifest, second_payloads, _ = _read_archive(
        _archive_bytes(
            StagedExportDB(),
            tmp_path,
            schema_version=STAGED_MANIFEST_SCHEMA_VERSION,
        )
    )

    assert first_payloads == second_payloads
    assert first_manifest["entity_counts"] == second_manifest["entity_counts"]
    assert (
        first_manifest["integrity"]["payload_files"]
        == second_manifest["integrity"]["payload_files"]
    )


def _malformed_bundle(case: str) -> dict[str, list[dict[str, Any]]]:
    bundle = _unified_memory_bundle()
    if case == "missing_memory_link":
        bundle["memory_persona_links"][0]["memory_id"] = "absent-memory"
    elif case == "missing_persona_link":
        bundle["memory_persona_links"][0]["persona_subject_id"] = "absent-persona"
    elif case == "missing_binding_subject":
        bundle["persona_subject_bindings"][0]["persona_subject_id"] = "absent-persona"
    elif case == "missing_provenance_memory":
        bundle["memory_provenance"][0]["memory_id"] = "absent-memory"
    elif case == "cross_account_memory":
        bundle["memory_records"][0]["user_id"] = ACCOUNT_B
    elif case == "cross_account_link":
        bundle["memory_persona_links"][0]["persona_user_id"] = ACCOUNT_B
    elif case == "missing_project":
        bundle["projects"] = []
    elif case == "cross_account_project":
        bundle["projects"][0]["user_id"] = ACCOUNT_B
    elif case == "cross_account_binding":
        bundle["persona_subject_bindings"][0]["source_account_id"] = ACCOUNT_B
    elif case == "missing_source_thread":
        bundle["memory_provenance"][1]["source_thread_id"] = 999999
    elif case == "missing_source_message":
        bundle["memory_provenance"][1]["source_message_id"] = 999999
    elif case == "missing_provenance":
        bundle["memory_provenance"] = [
            row
            for row in bundle["memory_provenance"]
            if row["memory_id"] != MEMORY_A_FACT
        ]
    elif case == "field_omitted":
        bundle["memory_records"][0].pop("held")
    else:  # pragma: no cover - guards the test table itself
        raise AssertionError(f"unknown malformed case: {case}")
    return bundle


@pytest.mark.parametrize(
    "case,error",
    [
        ("missing_memory_link", "memory_persona_link_export_graph_mismatch"),
        ("missing_persona_link", "memory_persona_link_export_graph_mismatch"),
        ("missing_binding_subject", "persona_subject_binding_export_graph_mismatch"),
        ("missing_provenance_memory", "memory_provenance_export_graph_mismatch"),
        ("cross_account_memory", "memory_record_export_account_mismatch"),
        ("cross_account_link", "memory_persona_link_export_graph_mismatch"),
        ("missing_project", "memory_export_project_scope_mismatch"),
        ("cross_account_project", "memory_export_project_scope_mismatch"),
        ("cross_account_binding", "persona_subject_binding_export_graph_mismatch"),
        ("missing_source_thread", "memory_provenance_export_source_mismatch"),
        ("missing_source_message", "memory_provenance_export_source_mismatch"),
        ("missing_provenance", "memory_provenance_export_missing"),
        ("field_omitted", "memory_records_export_field_set_incomplete"),
    ],
)
def test_malformed_v4_graph_fails_closed(
    tmp_path: Path,
    case: str,
    error: str,
):
    with pytest.raises(RuntimeError, match=error):
        _archive_bytes(
            StagedExportDB(_malformed_bundle(case)),
            tmp_path,
            schema_version=STAGED_MANIFEST_SCHEMA_VERSION,
        )


def test_v4_restore_remains_unsupported(tmp_path: Path):
    archive_bytes = _archive_bytes(
        StagedExportDB(),
        tmp_path,
        schema_version=STAGED_MANIFEST_SCHEMA_VERSION,
    )

    with pytest.raises(AccountRestoreValidationError) as exc_info:
        AccountRestoreService(SimpleNamespace()).restore_from_zip(
            archive_bytes,
            user_id=ACCOUNT_A,
        )

    assert exc_info.value.code == "schema_version_unsupported"


@pytest.mark.integration
def test_postgres_v4_reader_enforces_account_isolation(
    temporary_postgres,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    engine = sa.create_engine(database_url, future=True)
    plain_dsn = database_url.replace("postgresql+psycopg://", "postgresql://")
    monkeypatch.setattr(pgdb_module, "_resolve_dsn", lambda: plain_dsn)
    monkeypatch.setenv("STORAGE_BASE_PATH", str(tmp_path / "storage"))

    try:
        with engine.begin() as connection:
            connection.execute(
                sa.text(
                    "INSERT INTO users (id, username, password_hash, role) VALUES "
                    "(:a, :a, 'test', 'guest'), (:b, :b, 'test', 'guest')"
                ),
                {"a": ACCOUNT_A, "b": ACCOUNT_B},
            )
            connection.execute(
                sa.text(
                    "INSERT INTO projects (id, user_id, name) VALUES "
                    "(:pa, :a, 'Account A Memory Project'), "
                    "(:pb, :b, 'Account B Memory Project')"
                ),
                {"pa": PROJECT_A, "pb": PROJECT_B, "a": ACCOUNT_A, "b": ACCOUNT_B},
            )
            connection.execute(
                sa.text(
                    "INSERT INTO persona_subjects "
                    "(persona_subject_id, user_id, display_name_snapshot, lifecycle) "
                    "VALUES (:sa, :a, 'Persona A', 'active'), "
                    "(:sb, :b, 'Persona B', 'active')"
                ),
                {"sa": SUBJECT_A, "sb": SUBJECT_B, "a": ACCOUNT_A, "b": ACCOUNT_B},
            )
            connection.execute(
                sa.text(
                    "INSERT INTO persona_subject_bindings "
                    "(binding_id, persona_subject_id, subject_user_id, "
                    " source_account_id, ref_kind, ref_id, valid_from) VALUES "
                    "('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', :sa, :a, :a, "
                    " 'persona', 'persona-a', :now), "
                    "('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', :sb, :b, :b, "
                    " 'persona', 'persona-b', :now)"
                ),
                {
                    "sa": SUBJECT_A,
                    "sb": SUBJECT_B,
                    "a": ACCOUNT_A,
                    "b": ACCOUNT_B,
                    "now": NOW,
                },
            )
            connection.execute(
                sa.text(
                    "INSERT INTO memory_records "
                    "(memory_id, user_id, project_id, semantic_species, "
                    " text_content, reviewed_at, activated_at, pinned, held, extensions) "
                    "VALUES (:ma, :a, :pa, 'episodic_semantic_memory', "
                    " 'Account A memory', :now, :now, true, false, "
                    " CAST(:ext_a AS jsonb)), "
                    "(:mb, :b, :pb, 'episodic_semantic_memory', "
                    " 'Account B memory', :now, :now, false, true, "
                    " CAST(:ext_b AS jsonb))"
                ),
                {
                    "ma": MEMORY_A,
                    "mb": MEMORY_B,
                    "a": ACCOUNT_A,
                    "b": ACCOUNT_B,
                    "pa": PROJECT_A,
                    "pb": PROJECT_B,
                    "now": NOW,
                    "ext_a": json.dumps({"account": "A"}),
                    "ext_b": json.dumps({"account": "B"}),
                },
            )
            connection.execute(
                sa.text(
                    "INSERT INTO memory_persona_links "
                    "(link_id, memory_id, user_id, persona_subject_id, "
                    " persona_user_id, link_kind) VALUES "
                    "('66666666-6666-6666-6666-666666666666', :ma, :a, :sa, :a, "
                    " 'captured_under'), "
                    "('77777777-7777-7777-7777-777777777777', :mb, :b, :sb, :b, "
                    " 'captured_under')"
                ),
                {
                    "ma": MEMORY_A,
                    "mb": MEMORY_B,
                    "sa": SUBJECT_A,
                    "sb": SUBJECT_B,
                    "a": ACCOUNT_A,
                    "b": ACCOUNT_B,
                },
            )
            connection.execute(
                sa.text(
                    "INSERT INTO memory_provenance "
                    "(provenance_id, memory_id, user_id, source_system, "
                    " source_record_id, source_subject_kind, source_subject_id, "
                    " is_imported, extensions) VALUES "
                    "('88888888-8888-8888-8888-888888888888', :ma, :a, "
                    " 'codexify', 'a-native', 'vault', 'vault-a', false, "
                    " CAST(:ext_native AS jsonb)), "
                    "('99999999-9999-9999-9999-999999999999', :ma, :a, "
                    " 'openai', 'a-import', 'importer', 'import-a', true, "
                    " CAST(:ext_import AS jsonb)), "
                    "('aaaaaaaa-9999-9999-9999-999999999999', :mb, :b, "
                    " 'anthropic', 'b-import', 'importer', 'import-b', true, "
                    " CAST(:ext_b AS jsonb))"
                ),
                {
                    "ma": MEMORY_A,
                    "mb": MEMORY_B,
                    "a": ACCOUNT_A,
                    "b": ACCOUNT_B,
                    "ext_native": json.dumps({"ordinal": 1}),
                    "ext_import": json.dumps({"ordinal": 2}),
                    "ext_b": json.dumps({"ordinal": 3}),
                },
            )

        archive_bytes = _archive_bytes(
            pgdb_module,
            tmp_path,
            schema_version=STAGED_MANIFEST_SCHEMA_VERSION,
        )
        manifest, payloads, _ = _read_archive(archive_bytes)

        assert manifest["schema_version"] == STAGED_MANIFEST_SCHEMA_VERSION
        assert [row["memory_id"] for row in payloads["memory_records"]] == [MEMORY_A]
        assert payloads["memory_records"][0]["project_id"] == PROJECT_A
        assert [row["persona_subject_id"] for row in payloads["persona_subjects"]] == [
            SUBJECT_A
        ]
        assert [
            row["persona_subject_id"] for row in payloads["persona_subject_bindings"]
        ] == [SUBJECT_A]
        assert [
            row["persona_subject_id"] for row in payloads["memory_persona_links"]
        ] == [SUBJECT_A]
        assert len(payloads["memory_provenance"]) == 2
        assert {row["provenance_id"] for row in payloads["memory_provenance"]} == {
            "88888888-8888-8888-8888-888888888888",
            "99999999-9999-9999-9999-999999999999",
        }
        project_ids = {row["id"] for row in payloads["projects"]}
        assert PROJECT_A in project_ids
        assert PROJECT_B not in project_ids
        serialized = json.dumps(payloads, sort_keys=True)
        assert ACCOUNT_B not in serialized
        assert SUBJECT_B not in serialized
        assert MEMORY_B not in serialized
    finally:
        engine.dispose()


def test_v4_payload_checksums_cover_exact_emitted_bytes(tmp_path: Path):
    archive_bytes = _archive_bytes(
        StagedExportDB(),
        tmp_path,
        schema_version=STAGED_MANIFEST_SCHEMA_VERSION,
    )
    with zipfile.ZipFile(io.BytesIO(archive_bytes), "r") as archive:
        manifest = json.loads(archive.read("manifest.json"))
        for family in UNIFIED_MEMORY_PAYLOAD_FAMILIES:
            path = f"entities/{family}.json"
            body = archive.read(path)
            assert manifest["integrity"]["files"][path] == {
                "sha256": hashlib.sha256(body).hexdigest(),
                "size_bytes": len(body),
            }
