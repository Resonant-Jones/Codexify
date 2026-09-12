from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest

from guardian.services.account_export import (
    MANIFEST_SCHEMA_VERSION,
    STAGED_MANIFEST_SCHEMA_VERSION,
)
from guardian.services.account_restore import (
    AccountRestoreService,
    AccountRestoreValidationError,
    CanonicalMemoryRestoreExecutor,
    CanonicalMemoryRestorePlan,
    UnifiedMemoryRestoreConflictError,
    UnifiedMemoryRestorePreflight,
    UnifiedMemoryRestorePreflightError,
)
from tests.migration.test_canonical_memory_persistence_migration import _upgrade
from tests.migration.test_canonical_memory_persistence_migration import (  # noqa: PLC0414
    temporary_postgres as temporary_postgres,
)

ACCOUNT_A = "account-a"
ACCOUNT_B = "account-b"

PROJECT_A = 101
PROJECT_B = 202
PROJECT_A_TARGET = 1101

THREAD_A = 1001
THREAD_A_TARGET = 11001
MESSAGE_A = 2001
MESSAGE_A_TARGET = 12001

# Preflight-only synthetic IDs (used by the UMS-04C-A preflight tests
# against the in-memory payload rows that the preflight tests construct).
SUBJECT_A = "11111111-1111-1111-1111-111111111111"
SUBJECT_B = "22222222-2222-2222-2222-222222222222"

BINDING_A = "44444444-4444-4444-4444-444444444444"
BINDING_B = "55555555-5555-5555-5555-555555555555"

MEMORY_A = "66666666-6666-6666-6666-666666666666"
MEMORY_B = "77777777-7777-7777-7777-777777777777"
MEMORY_C = "88888888-8888-8888-8888-888888888888"

LINK_A = "99999999-9999-9999-9999-999999999999"
LINK_B = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"

PROV_A = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
PROV_B = "cccccccc-cccc-cccc-cccc-cccccccccccc"
PROV_C = "dddddddd-dddd-dddd-dddd-dddddddddddd"

NOW = "2026-09-12T10:00:00+00:00"
LATER = "2026-09-12T11:00:00+00:00"


def _valid_persona_subjects() -> list[dict[str, Any]]:
    return [
        {
            "persona_subject_id": SUBJECT_A,
            "user_id": ACCOUNT_A,
            "display_name_snapshot": "Axis",
            "lifecycle": "active",
            "created_at": NOW,
            "updated_at": LATER,
        },
    ]


def _valid_persona_subject_bindings() -> list[dict[str, Any]]:
    return [
        {
            "binding_id": BINDING_A,
            "persona_subject_id": SUBJECT_A,
            "subject_user_id": ACCOUNT_A,
            "source_account_id": ACCOUNT_A,
            "ref_kind": "persona_profile",
            "ref_id": "axis-current",
            "valid_from": NOW,
            "valid_until": None,
            "created_at": NOW,
        },
    ]


def _valid_memory_records() -> list[dict[str, Any]]:
    return [
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
            "activated_at": LATER,
            "pinned": True,
            "held": False,
            "extensions": {"display_hint": "architecture"},
            "created_at": NOW,
            "updated_at": LATER,
        },
        {
            "memory_id": MEMORY_B,
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
    ]


def _valid_memory_persona_links() -> list[dict[str, Any]]:
    return [
        {
            "link_id": LINK_A,
            "memory_id": MEMORY_A,
            "user_id": ACCOUNT_A,
            "persona_subject_id": SUBJECT_A,
            "persona_user_id": ACCOUNT_A,
            "link_kind": "captured_under",
            "created_at": NOW,
        },
        {
            "link_id": LINK_B,
            "memory_id": MEMORY_B,
            "user_id": ACCOUNT_A,
            "persona_subject_id": SUBJECT_A,
            "persona_user_id": ACCOUNT_A,
            "link_kind": "associated_with",
            "created_at": LATER,
        },
    ]


def _valid_memory_provenance() -> list[dict[str, Any]]:
    return [
        {
            "provenance_id": PROV_A,
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
            "provenance_id": PROV_B,
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
            "provenance_id": PROV_C,
            "memory_id": MEMORY_B,
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


def _valid_payload_rows() -> dict[str, list[dict[str, Any]]]:
    return {
        "persona_subjects": _valid_persona_subjects(),
        "persona_subject_bindings": _valid_persona_subject_bindings(),
        "memory_records": _valid_memory_records(),
        "memory_persona_links": _valid_memory_persona_links(),
        "memory_provenance": _valid_memory_provenance(),
    }


def _preflight() -> UnifiedMemoryRestorePreflight:
    return UnifiedMemoryRestorePreflight(
        target_account_id=ACCOUNT_A,
        source_account_id=ACCOUNT_A,
        project_map={PROJECT_A: PROJECT_A_TARGET},
        thread_map={THREAD_A: THREAD_A_TARGET},
        message_map={MESSAGE_A: MESSAGE_A_TARGET},
    )


# ---------------------------------------------------------------------------
# Valid plan
# ---------------------------------------------------------------------------


def test_valid_plan_is_complete_and_deterministic():
    preflight = _preflight()
    payload = _valid_payload_rows()

    plan = preflight.plan(payload)

    assert isinstance(plan, CanonicalMemoryRestorePlan)
    assert plan.target_account_id == ACCOUNT_A
    assert plan.source_account_id == ACCOUNT_A

    # All five families populated with deterministic ordering.
    assert [s.source_persona_subject_id for s in plan.persona_subjects] == [SUBJECT_A]
    assert [b.source_binding_id for b in plan.persona_subject_bindings] == [BINDING_A]
    assert [m.source_memory_id for m in plan.memory_records] == [MEMORY_A, MEMORY_B]
    assert [l.source_link_id for l in plan.memory_persona_links] == [LINK_A, LINK_B]
    assert [p.source_provenance_id for p in plan.memory_provenance] == [
        PROV_A,
        PROV_B,
        PROV_C,
    ]

    # Stable memory IDs preserved unchanged.
    assert {m.source_memory_id for m in plan.memory_records} == {
        m.target_memory_id for m in plan.memory_records
    }
    # Display name preserved as data, not used for identity.
    assert plan.persona_subjects[0].display_name_snapshot == "Axis"

    # Project mapping applied; account-owned memory kept as None.
    project_targets = {
        m.source_memory_id: m.target_project_id for m in plan.memory_records
    }
    assert project_targets[MEMORY_A] == PROJECT_A_TARGET
    assert project_targets[MEMORY_B] is None

    # Local provenance references remapped through explicit maps.
    thread_prov = next(
        p for p in plan.memory_provenance if p.source_provenance_id == PROV_B
    )
    assert thread_prov.target_source_thread_id == THREAD_A_TARGET
    assert thread_prov.target_source_message_id == MESSAGE_A_TARGET

    # Opaque external identifiers preserved verbatim.
    ext_prov = next(
        p for p in plan.memory_provenance if p.source_provenance_id == PROV_A
    )
    assert ext_prov.target_source_thread_id is None
    assert ext_prov.target_source_message_id is None
    assert ext_prov.source_record_id == "source-memory-1"


# ---------------------------------------------------------------------------
# Project mapping
# ---------------------------------------------------------------------------


def test_missing_project_mapping_fails_closed():
    payload = _valid_payload_rows()
    preflight = UnifiedMemoryRestorePreflight(
        target_account_id=ACCOUNT_A,
        source_account_id=ACCOUNT_A,
        project_map={},  # intentionally empty
        thread_map={THREAD_A: THREAD_A_TARGET},
        message_map={MESSAGE_A: MESSAGE_A_TARGET},
    )

    with pytest.raises(UnifiedMemoryRestorePreflightError) as exc_info:
        preflight.plan(payload)
    assert exc_info.value.code == "memory_project_mapping_missing"


def test_missing_project_mapping_never_becomes_null_for_project_scoped_memory():
    payload = _valid_payload_rows()
    preflight = UnifiedMemoryRestorePreflight(
        target_account_id=ACCOUNT_A,
        source_account_id=ACCOUNT_A,
        # Empty project_map: this MUST not silently widen the memory to
        # ``target_project_id == None`` (account-wide).
        project_map={},
        thread_map={THREAD_A: THREAD_A_TARGET},
        message_map={MESSAGE_A: MESSAGE_A_TARGET},
    )

    with pytest.raises(UnifiedMemoryRestorePreflightError) as exc_info:
        preflight.plan(payload)
    assert exc_info.value.code == "memory_project_mapping_missing"
    assert exc_info.value.details["project_id"] == PROJECT_A


def test_account_owned_memory_without_project_is_allowed():
    payload = _valid_payload_rows()
    # Remove the only Project-scoped memory to leave only account-owned.
    payload["memory_records"] = [
        row for row in payload["memory_records"] if row["memory_id"] != MEMORY_A
    ]
    payload["memory_persona_links"] = [
        row for row in payload["memory_persona_links"] if row["memory_id"] != MEMORY_A
    ]
    payload["memory_provenance"] = [
        row for row in payload["memory_provenance"] if row["memory_id"] != MEMORY_A
    ]
    preflight = UnifiedMemoryRestorePreflight(
        target_account_id=ACCOUNT_A,
        source_account_id=ACCOUNT_A,
        project_map={},
        thread_map={},
        message_map={},
    )

    plan = preflight.plan(payload)

    assert len(plan.memory_records) == 1
    assert plan.memory_records[0].source_memory_id == MEMORY_B
    assert plan.memory_records[0].target_project_id is None


# ---------------------------------------------------------------------------
# Persona identity
# ---------------------------------------------------------------------------


def test_stable_subject_id_retained_even_with_renamed_display():
    payload = _valid_payload_rows()
    payload["persona_subjects"][0]["display_name_snapshot"] = "Renamed"
    preflight = _preflight()

    plan = preflight.plan(payload)

    assert plan.persona_subjects[0].target_persona_subject_id == SUBJECT_A
    assert plan.persona_subjects[0].source_persona_subject_id == SUBJECT_A
    assert plan.persona_subjects[0].display_name_snapshot == "Renamed"


def test_binding_referencing_unknown_subject_fails():
    payload = _valid_payload_rows()
    payload["persona_subject_bindings"][0]["persona_subject_id"] = SUBJECT_B
    preflight = _preflight()

    with pytest.raises(UnifiedMemoryRestorePreflightError) as exc_info:
        preflight.plan(payload)
    assert exc_info.value.code == "persona_binding_orphan"


def test_binding_to_cross_account_subject_fails():
    payload = _valid_payload_rows()
    payload["persona_subject_bindings"][0]["subject_user_id"] = ACCOUNT_B
    preflight = _preflight()

    with pytest.raises(UnifiedMemoryRestorePreflightError) as exc_info:
        preflight.plan(payload)
    assert exc_info.value.code == "persona_binding_account_mismatch"


def test_binding_to_cross_account_source_account_fails():
    payload = _valid_payload_rows()
    payload["persona_subject_bindings"][0]["source_account_id"] = ACCOUNT_B
    preflight = _preflight()

    with pytest.raises(UnifiedMemoryRestorePreflightError) as exc_info:
        preflight.plan(payload)
    assert exc_info.value.code == "persona_binding_account_mismatch"


# ---------------------------------------------------------------------------
# Memory governance preservation
# ---------------------------------------------------------------------------


def test_memory_governance_state_preserved_without_inference():
    payload = _valid_payload_rows()
    preflight = _preflight()

    plan = preflight.plan(payload)

    by_id = {m.source_memory_id: m for m in plan.memory_records}
    assert by_id[MEMORY_A].reviewed_at == NOW
    assert by_id[MEMORY_A].activated_at == LATER
    assert by_id[MEMORY_A].pinned is True
    assert by_id[MEMORY_A].held is False
    assert by_id[MEMORY_A].semantic_species == "episodic_semantic_memory"

    assert by_id[MEMORY_B].reviewed_at == NOW
    assert by_id[MEMORY_B].activated_at == LATER
    assert by_id[MEMORY_B].pinned is False
    assert by_id[MEMORY_B].held is True
    assert by_id[MEMORY_B].semantic_species == "verified_personal_fact"


def test_memory_with_missing_review_state_is_allowed_no_inference():
    payload = _valid_payload_rows()
    payload["memory_records"][0]["reviewed_at"] = None
    payload["memory_records"][0]["activated_at"] = None
    preflight = _preflight()

    plan = preflight.plan(payload)

    memory_a = next(m for m in plan.memory_records if m.source_memory_id == MEMORY_A)
    assert memory_a.reviewed_at is None
    assert memory_a.activated_at is None


def test_invalid_pinned_state_fails():
    payload = _valid_payload_rows()
    payload["memory_records"][0]["pinned"] = "yes"
    preflight = _preflight()

    with pytest.raises(UnifiedMemoryRestorePreflightError) as exc_info:
        preflight.plan(payload)
    assert exc_info.value.code == "memory_governance_state_invalid"


def test_missing_semantic_species_fails():
    payload = _valid_payload_rows()
    payload["memory_records"][0]["semantic_species"] = ""
    preflight = _preflight()

    with pytest.raises(UnifiedMemoryRestorePreflightError) as exc_info:
        preflight.plan(payload)
    assert exc_info.value.code == "memory_species_missing"


# ---------------------------------------------------------------------------
# Persona link validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "link_kind",
    ["captured_under", "suggested_by", "associated_with"],
)
def test_canonical_link_kinds_accepted(link_kind: str):
    payload = _valid_payload_rows()
    payload["memory_persona_links"][0]["link_kind"] = link_kind
    preflight = _preflight()

    plan = preflight.plan(payload)

    assert plan.memory_persona_links[0].link_kind == link_kind


def test_unknown_link_kind_fails():
    payload = _valid_payload_rows()
    payload["memory_persona_links"][0]["link_kind"] = "synthesized_by"
    preflight = _preflight()

    with pytest.raises(UnifiedMemoryRestorePreflightError) as exc_info:
        preflight.plan(payload)
    assert exc_info.value.code == "memory_persona_link_invalid_kind"


def test_link_to_missing_memory_fails():
    payload = _valid_payload_rows()
    payload["memory_persona_links"][0]["memory_id"] = MEMORY_C
    preflight = _preflight()

    with pytest.raises(UnifiedMemoryRestorePreflightError) as exc_info:
        preflight.plan(payload)
    assert exc_info.value.code == "memory_persona_link_orphan"


def test_link_to_missing_subject_fails():
    payload = _valid_payload_rows()
    payload["memory_persona_links"][0]["persona_subject_id"] = SUBJECT_B
    preflight = _preflight()

    with pytest.raises(UnifiedMemoryRestorePreflightError) as exc_info:
        preflight.plan(payload)
    assert exc_info.value.code == "memory_persona_link_orphan"


def test_link_with_cross_account_user_fails():
    payload = _valid_payload_rows()
    payload["memory_persona_links"][0]["user_id"] = ACCOUNT_B
    preflight = _preflight()

    with pytest.raises(UnifiedMemoryRestorePreflightError) as exc_info:
        preflight.plan(payload)
    assert exc_info.value.code == "memory_persona_link_account_mismatch"


def test_link_with_cross_account_persona_user_fails():
    payload = _valid_payload_rows()
    payload["memory_persona_links"][0]["persona_user_id"] = ACCOUNT_B
    preflight = _preflight()

    with pytest.raises(UnifiedMemoryRestorePreflightError) as exc_info:
        preflight.plan(payload)
    assert exc_info.value.code == "memory_persona_link_account_mismatch"


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------


def test_multiple_provenance_rows_for_one_memory_preserved():
    payload = _valid_payload_rows()
    preflight = _preflight()

    plan = preflight.plan(payload)

    memory_a_provenance = [
        p for p in plan.memory_provenance if p.target_memory_id == MEMORY_A
    ]
    assert len(memory_a_provenance) == 2


def test_local_thread_remap_succeeds():
    payload = _valid_payload_rows()
    preflight = _preflight()

    plan = preflight.plan(payload)

    thread_prov = next(
        p for p in plan.memory_provenance if p.source_provenance_id == PROV_B
    )
    assert thread_prov.target_source_thread_id == THREAD_A_TARGET
    assert thread_prov.target_source_message_id == MESSAGE_A_TARGET


def test_missing_local_thread_mapping_fails():
    payload = _valid_payload_rows()
    preflight = UnifiedMemoryRestorePreflight(
        target_account_id=ACCOUNT_A,
        source_account_id=ACCOUNT_A,
        project_map={PROJECT_A: PROJECT_A_TARGET},
        # thread_map intentionally missing
        thread_map={},
        message_map={MESSAGE_A: MESSAGE_A_TARGET},
    )

    with pytest.raises(UnifiedMemoryRestorePreflightError) as exc_info:
        preflight.plan(payload)
    assert exc_info.value.code == "memory_provenance_thread_mapping_missing"


def test_missing_local_message_mapping_fails():
    payload = _valid_payload_rows()
    preflight = UnifiedMemoryRestorePreflight(
        target_account_id=ACCOUNT_A,
        source_account_id=ACCOUNT_A,
        project_map={PROJECT_A: PROJECT_A_TARGET},
        thread_map={THREAD_A: THREAD_A_TARGET},
        # message_map intentionally missing
        message_map={},
    )

    with pytest.raises(UnifiedMemoryRestorePreflightError) as exc_info:
        preflight.plan(payload)
    assert exc_info.value.code == "memory_provenance_message_mapping_missing"


def test_external_opaque_identifier_preserved_verbatim():
    payload = _valid_payload_rows()
    preflight = _preflight()

    plan = preflight.plan(payload)

    ext = next(p for p in plan.memory_provenance if p.source_provenance_id == PROV_A)
    assert ext.source_record_id == "source-memory-1"
    assert ext.source_import_job_id == "import-job-1"
    assert ext.source_export_fingerprint == "sha256:source-export"
    assert ext.target_source_thread_id is None
    assert ext.target_source_message_id is None


def test_orphan_provenance_fails():
    payload = _valid_payload_rows()
    payload["memory_provenance"][0]["memory_id"] = MEMORY_C
    preflight = _preflight()

    with pytest.raises(UnifiedMemoryRestorePreflightError) as exc_info:
        preflight.plan(payload)
    assert exc_info.value.code == "memory_provenance_orphan"


# ---------------------------------------------------------------------------
# Archive closure
# ---------------------------------------------------------------------------


def test_required_provenance_absence_fails():
    payload = _valid_payload_rows()
    # Drop the only provenance row for MEMORY_B (account-owned memory).
    payload["memory_provenance"] = [
        row for row in payload["memory_provenance"] if row["memory_id"] != MEMORY_B
    ]
    preflight = _preflight()

    with pytest.raises(UnifiedMemoryRestorePreflightError) as exc_info:
        preflight.plan(payload)
    assert exc_info.value.code == "memory_provenance_missing"
    assert MEMORY_B in exc_info.value.details["memory_ids"]


def test_memory_account_mismatch_fails():
    payload = _valid_payload_rows()
    payload["memory_records"][0]["user_id"] = ACCOUNT_B
    preflight = _preflight()

    with pytest.raises(UnifiedMemoryRestorePreflightError) as exc_info:
        preflight.plan(payload)
    assert exc_info.value.code == "memory_account_mismatch"


def test_duplicate_subject_id_fails():
    payload = _valid_payload_rows()
    payload["persona_subjects"].append(deepcopy(payload["persona_subjects"][0]))
    preflight = _preflight()

    with pytest.raises(UnifiedMemoryRestorePreflightError) as exc_info:
        preflight.plan(payload)
    assert exc_info.value.code == "persona_subject_duplicate"


def test_duplicate_memory_id_fails():
    payload = _valid_payload_rows()
    payload["memory_records"].append(deepcopy(payload["memory_records"][0]))
    preflight = _preflight()

    with pytest.raises(UnifiedMemoryRestorePreflightError) as exc_info:
        preflight.plan(payload)
    assert exc_info.value.code == "memory_record_duplicate"


def test_missing_required_field_fails():
    payload = _valid_payload_rows()
    payload["memory_records"][0].pop("semantic_species")
    preflight = _preflight()

    with pytest.raises(UnifiedMemoryRestorePreflightError) as exc_info:
        preflight.plan(payload)
    assert exc_info.value.code == "payload_invalid_required_field"


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_equivalent_input_rows_in_different_order_produce_equivalent_plans():
    preflight = _preflight()
    payload_a = _valid_payload_rows()
    payload_b = _valid_payload_rows()

    # Reverse every family.
    for family in payload_b:
        payload_b[family] = list(reversed(payload_b[family]))

    plan_a = preflight.plan(payload_a)
    plan_b = preflight.plan(payload_b)

    def _ids(plan: CanonicalMemoryRestorePlan) -> tuple[tuple[str, ...], ...]:
        return (
            tuple(s.source_persona_subject_id for s in plan.persona_subjects),
            tuple(b.source_binding_id for b in plan.persona_subject_bindings),
            tuple(m.source_memory_id for m in plan.memory_records),
            tuple(l.source_link_id for l in plan.memory_persona_links),
            tuple(p.source_provenance_id for p in plan.memory_provenance),
        )

    assert _ids(plan_a) == _ids(plan_b)


# ---------------------------------------------------------------------------
# Production dispatch remains fail-closed
# ---------------------------------------------------------------------------


def test_production_dispatch_rejects_v4_archive(tmp_path):
    from tests.services.test_account_export_unified_memory import (  # noqa: PLC0415
        StagedExportDB,
        _archive_bytes,
    )

    archive_bytes = _archive_bytes(
        StagedExportDB(),
        tmp_path,
        schema_version=STAGED_MANIFEST_SCHEMA_VERSION,
    )

    with pytest.raises(AccountRestoreValidationError) as exc_info:
        AccountRestoreService(db=None).restore_from_zip(
            archive_bytes, user_id=ACCOUNT_A
        )
    assert exc_info.value.code == "schema_version_unsupported"
    # v4 schema version is reported so operators know why it was rejected.
    assert exc_info.value.schema_version == STAGED_MANIFEST_SCHEMA_VERSION


def test_production_dispatch_still_accepts_v3_archive(tmp_path):
    from tests.services.test_account_export_unified_memory import (  # noqa: PLC0415
        StagedExportDB,
        _archive_bytes,
        _read_archive,
    )

    archive_bytes = _archive_bytes(
        StagedExportDB(),
        tmp_path,
        schema_version=MANIFEST_SCHEMA_VERSION,
    )

    # Parsing through the production dispatch must NOT raise the
    # ``schema_version_unsupported`` validation error that v4 produces. Any
    # other error (e.g., a missing restore helper for ``db=None``) is
    # acceptable here because it proves the schema_version gate let v3
    # through.
    try:
        AccountRestoreService(db=None).restore_from_zip(
            archive_bytes, user_id=ACCOUNT_A
        )
    except AccountRestoreValidationError as exc:
        assert exc.code != "schema_version_unsupported"
    except Exception as exc:  # noqa: BLE001 — restore helper may be missing for db=None
        # A non-validation exception (e.g., missing restore helper) is
        # acceptable here because it still proves v3 passed the schema
        # version gate and reached the restore stage.
        assert not isinstance(exc, AccountRestoreValidationError)
        assert getattr(exc, "code", None) != "schema_version_unsupported"

    manifest, _payloads, _archive_names = _read_archive(archive_bytes)
    assert manifest["schema_version"] == MANIFEST_SCHEMA_VERSION


# =============================================================================
# UMS-04C-B: PostgreSQL persistence tests
# =============================================================================
#
# These tests prove that CanonicalMemoryRestoreExecutor:
#   - classifies every planned entity before any canonical DML;
#   - inserts CREATE entities in dependency order inside one transaction;
#   - treats identical replay as an idempotent no-op;
#   - fails closed on canonical conflicts (no mutation);
#   - fails closed on late-family conflicts (zero mutation);
#   - rolls back partial mutation when a later family fails;
#   - preserves all authoritative fields exactly across restore.
#
# Authority: dedicated PostgreSQL 17 cluster through local Unix socket.
# Transport: postgresql://codexify_test_runner@/postgres?host=/tmp&port=55432


# =============================================================================
# UMS-04C-B: PostgreSQL persistence tests
# =============================================================================
#
# These tests prove that CanonicalMemoryRestoreExecutor:
#   - classifies every planned entity before any canonical DML;
#   - inserts CREATE entities in dependency order inside one transaction;
#   - treats identical replay as an idempotent no-op;
#   - fails closed on canonical conflicts (no mutation);
#   - fails closed on late-family conflicts (zero mutation);
#   - rolls back partial mutation when a later family fails;
#   - preserves all authoritative fields exactly across restore.
#
# Authority: dedicated PostgreSQL 17 cluster through local Unix socket.
# Transport: postgresql://codexify_test_runner@/postgres?host=/tmp&port=55432


def _build_plan_for_account_a(
    *,
    source_account_id: str = ACCOUNT_A,
    target_account_id: str = ACCOUNT_A,
    project_map: dict[int, int] | None = None,
    thread_map: dict[int, int] | None = None,
    message_map: dict[int, int] | None = None,
) -> tuple[UnifiedMemoryRestorePreflight, CanonicalMemoryRestorePlan]:
    """Build a preflight + plan from the canonical ``_unified_memory_bundle``.

    Returns ``(preflight, plan)`` so callers can mutate one or both before
    classification. Default maps cover the IDs the bundle uses.
    """
    from tests.services.test_account_export_unified_memory import (
        MESSAGE_A as BUNDLE_MESSAGE_A,
    )
    from tests.services.test_account_export_unified_memory import (
        PROJECT_A as BUNDLE_PROJECT_A,
    )
    from tests.services.test_account_export_unified_memory import (
        THREAD_A as BUNDLE_THREAD_A,
    )
    from tests.services.test_account_export_unified_memory import (  # noqa: PLC0415
        _unified_memory_bundle as _unified_memory_bundle,
    )

    bundle = _unified_memory_bundle()
    payload = {
        "persona_subjects": bundle["persona_subjects"],
        "persona_subject_bindings": bundle["persona_subject_bindings"],
        "memory_records": bundle["memory_records"],
        "memory_persona_links": bundle["memory_persona_links"],
        "memory_provenance": bundle["memory_provenance"],
    }
    preflight = UnifiedMemoryRestorePreflight(
        target_account_id=target_account_id,
        source_account_id=source_account_id,
        project_map=project_map or {BUNDLE_PROJECT_A: PROJECT_A_TARGET},
        thread_map=thread_map or {BUNDLE_THREAD_A: THREAD_A_TARGET},
        message_map=message_map or {BUNDLE_MESSAGE_A: MESSAGE_A_TARGET},
    )
    return preflight, preflight.plan(payload)


def _seed_account_a(database_url: str) -> None:
    """Seed ``users``, ``projects``, ``chat_threads``, ``chat_messages``
    for the ``ACCOUNT_A`` target so canonical restore FKs resolve.
    """
    import psycopg

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (id, username, password_hash, role) "
                "VALUES (%s, %s, 'test', 'guest')",
                (ACCOUNT_A, ACCOUNT_A),
            )
            cur.execute(
                "INSERT INTO projects (id, user_id, name) VALUES (%s, %s, %s)",
                (PROJECT_A_TARGET, ACCOUNT_A, "Account A Memory Project"),
            )
            cur.execute(
                "INSERT INTO chat_threads (id, user_id, title, project_id) "
                "VALUES (%s, %s, %s, %s)",
                (THREAD_A_TARGET, ACCOUNT_A, "Source thread", PROJECT_A_TARGET),
            )
            cur.execute(
                "INSERT INTO chat_messages (id, thread_id, user_id, role, content) "
                "VALUES (%s, %s, %s, 'user', %s)",
                (
                    MESSAGE_A_TARGET,
                    THREAD_A_TARGET,
                    ACCOUNT_A,
                    "Remember this exactly.",
                ),
            )
        conn.commit()


def _row_count(database_url: str, table: str) -> int:
    """Count canonical restore rows owned by ``ACCOUNT_A`` for the given table.

    ``persona_subject_bindings`` carries the owner in ``subject_user_id``;
    all other canonical tables carry it in ``user_id``.
    """
    import sqlalchemy as sa

    owner_column = (
        "subject_user_id" if table == "persona_subject_bindings" else "user_id"
    )
    engine = sa.create_engine(database_url, future=True)
    with engine.connect() as conn:
        return conn.execute(
            sa.text(f"SELECT COUNT(*) FROM {table} WHERE {owner_column} = :u"),
            {"u": ACCOUNT_A},
        ).scalar_one()


def _table_count_all(database_url: str, table: str) -> int:
    import sqlalchemy as sa

    engine = sa.create_engine(database_url, future=True)
    with engine.connect() as conn:
        return conn.execute(sa.text(f"SELECT COUNT(*) FROM {table}")).scalar_one()


@pytest.mark.integration
def test_clean_persistence_creates_all_five_families(temporary_postgres, tmp_path):
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    _seed_account_a(database_url)

    _preflight, plan = _build_plan_for_account_a()
    assert len(plan.memory_records) == 2
    assert len(plan.memory_provenance) == 3

    import psycopg

    with psycopg.connect(database_url) as conn:
        result = CanonicalMemoryRestoreExecutor(plan).execute(conn)
        conn.commit()

    assert result.subject_created_count == 1
    assert result.binding_created_count == 2
    assert result.memory_created_count == 2
    assert result.link_created_count == 2
    assert result.provenance_created_count == 3
    assert result.subject_identical_count == 0
    assert result.binding_identical_count == 0
    assert result.memory_identical_count == 0
    assert result.link_identical_count == 0
    assert result.provenance_identical_count == 0

    assert _row_count(database_url, "persona_subjects") == 1
    assert _row_count(database_url, "persona_subject_bindings") == 2
    assert _row_count(database_url, "memory_records") == 2
    assert _row_count(database_url, "memory_persona_links") == 2
    assert _row_count(database_url, "memory_provenance") == 3

    # Verify ownership and identity preservation by reading the rows back.
    import sqlalchemy as sa

    engine = sa.create_engine(database_url, future=True)
    with engine.connect() as conn:
        # All memory_records carry the exact target account.
        distinct_owners = (
            conn.execute(sa.text("SELECT DISTINCT user_id FROM memory_records"))
            .scalars()
            .all()
        )
        assert distinct_owners == [ACCOUNT_A]

        # Project scope preserved (Project-scoped memory stays Project-scoped).
        episodic_memory_id = next(
            m.target_memory_id
            for m in plan.memory_records
            if m.semantic_species == "episodic_semantic_memory"
        )
        fact_memory_id = next(
            m.target_memory_id
            for m in plan.memory_records
            if m.semantic_species == "verified_personal_fact"
        )
        scope = {
            row["memory_id"]: {"project_id": row["project_id"]}
            for row in conn.execute(
                sa.text(
                    "SELECT memory_id, project_id FROM memory_records "
                    "WHERE memory_id = ANY(:ids)"
                ),
                {"ids": [episodic_memory_id, fact_memory_id]},
            )
            .mappings()
            .all()
        }
        assert scope[episodic_memory_id]["project_id"] == PROJECT_A_TARGET
        assert scope[fact_memory_id]["project_id"] is None

        # Pin/hold/species all preserved.
        governance = {
            row["memory_id"]: {
                "pinned": row["pinned"],
                "held": row["held"],
                "semantic_species": row["semantic_species"],
            }
            for row in conn.execute(
                sa.text(
                    "SELECT memory_id, pinned, held, semantic_species "
                    "FROM memory_records"
                )
            ).mappings()
        }
        assert governance[episodic_memory_id]["pinned"] is True
        assert governance[episodic_memory_id]["held"] is False
        assert governance[fact_memory_id]["pinned"] is False
        assert governance[fact_memory_id]["held"] is True

        # Multiplicity preserved: episodic memory has two provenance rows.
        episodic_provenance_count = conn.execute(
            sa.text("SELECT COUNT(*) FROM memory_provenance WHERE memory_id = :m"),
            {"m": episodic_memory_id},
        ).scalar_one()
        assert episodic_provenance_count == 2
        fact_provenance_count = conn.execute(
            sa.text("SELECT COUNT(*) FROM memory_provenance WHERE memory_id = :m"),
            {"m": fact_memory_id},
        ).scalar_one()
        assert fact_provenance_count == 1


@pytest.mark.integration
def test_identical_replay_creates_zero_rows(temporary_postgres, tmp_path):
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    _seed_account_a(database_url)

    _preflight, plan = _build_plan_for_account_a()

    import psycopg

    with psycopg.connect(database_url) as conn:
        first = CanonicalMemoryRestoreExecutor(plan).execute(conn)
        conn.commit()
    assert first.subject_created_count == 1
    assert first.memory_created_count == 2

    first_counts = {
        "persona_subjects": _row_count(database_url, "persona_subjects"),
        "persona_subject_bindings": _row_count(
            database_url, "persona_subject_bindings"
        ),
        "memory_records": _row_count(database_url, "memory_records"),
        "memory_persona_links": _row_count(database_url, "memory_persona_links"),
        "memory_provenance": _row_count(database_url, "memory_provenance"),
    }

    with psycopg.connect(database_url) as conn:
        second = CanonicalMemoryRestoreExecutor(plan).execute(conn)
        conn.commit()

    assert second.subject_created_count == 0
    assert second.binding_created_count == 0
    assert second.memory_created_count == 0
    assert second.link_created_count == 0
    assert second.provenance_created_count == 0
    assert second.subject_identical_count == 1
    assert second.binding_identical_count == 2
    assert second.memory_identical_count == 2
    assert second.link_identical_count == 2
    assert second.provenance_identical_count == 3

    second_counts = {
        "persona_subjects": _row_count(database_url, "persona_subjects"),
        "persona_subject_bindings": _row_count(
            database_url, "persona_subject_bindings"
        ),
        "memory_records": _row_count(database_url, "memory_records"),
        "memory_persona_links": _row_count(database_url, "memory_persona_links"),
        "memory_provenance": _row_count(database_url, "memory_provenance"),
    }
    assert first_counts == second_counts


@pytest.mark.integration
def test_subject_conflict_fails_closed(temporary_postgres, tmp_path):
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    _seed_account_a(database_url)

    _preflight, plan = _build_plan_for_account_a()
    subject_id = plan.persona_subjects[0].target_persona_subject_id

    # Seed same subject identity but different lifecycle.
    import psycopg

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO persona_subjects "
                "(persona_subject_id, user_id, display_name_snapshot, lifecycle, "
                "created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s)",
                (subject_id, ACCOUNT_A, "Axis", "retired", NOW, NOW),
            )
        conn.commit()

    with psycopg.connect(database_url) as conn:
        with pytest.raises(UnifiedMemoryRestoreConflictError) as exc_info:
            CanonicalMemoryRestoreExecutor(plan).execute(conn)
        conn.rollback()

    assert exc_info.value.code == "persona_subject_conflict"


@pytest.mark.integration
def test_memory_conflict_fails_closed(temporary_postgres, tmp_path):
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    _seed_account_a(database_url)

    _preflight, plan = _build_plan_for_account_a()
    target_memory_id = plan.memory_records[0].target_memory_id

    # Seed subject IDENTICALLY to plan so subject classifies as IDENTICAL.
    # Then seed a conflicting memory with the same memory_id.
    import psycopg

    planned_subject = plan.persona_subjects[0]
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO persona_subjects "
                "(persona_subject_id, user_id, display_name_snapshot, lifecycle, "
                "created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s)",
                (
                    planned_subject.target_persona_subject_id,
                    planned_subject.target_account_id,
                    planned_subject.display_name_snapshot,
                    planned_subject.lifecycle,
                    planned_subject.created_at,
                    planned_subject.updated_at,
                ),
            )
            cur.execute(
                "INSERT INTO memory_records "
                "(memory_id, user_id, project_id, semantic_species, "
                "text_content, fact_key, fact_value, fact_confidence, "
                "reviewed_at, activated_at, pinned, held, extensions, "
                "created_at, updated_at) VALUES "
                "(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)",
                (
                    target_memory_id,
                    ACCOUNT_A,
                    PROJECT_A_TARGET,
                    "verified_personal_fact",  # different from plan
                    None,
                    "k",
                    "v",
                    0.5,
                    NOW,
                    NOW,
                    False,
                    False,
                    "{}",
                    NOW,
                    NOW,
                ),
            )
        conn.commit()

    with psycopg.connect(database_url) as conn:
        with pytest.raises(UnifiedMemoryRestoreConflictError) as exc_info:
            CanonicalMemoryRestoreExecutor(plan).execute(conn)
        conn.rollback()

    assert exc_info.value.code == "memory_record_conflict"


@pytest.mark.integration
def test_binding_conflict_fails_closed(temporary_postgres, tmp_path):
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    _seed_account_a(database_url)

    _preflight, plan = _build_plan_for_account_a()
    planned_subject = plan.persona_subjects[0]
    target_binding_id = plan.persona_subject_bindings[0].target_binding_id

    import psycopg

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO persona_subjects "
                "(persona_subject_id, user_id, display_name_snapshot, lifecycle, "
                "created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s) "
                "ON CONFLICT (persona_subject_id) DO NOTHING",
                (
                    plan.persona_subjects[0].target_persona_subject_id,
                    ACCOUNT_A,
                    planned_subject.display_name_snapshot,
                    planned_subject.lifecycle,
                    planned_subject.created_at,
                    planned_subject.updated_at,
                ),
            )
            cur.execute(
                "INSERT INTO persona_subject_bindings "
                "(binding_id, persona_subject_id, subject_user_id, "
                "source_account_id, ref_kind, ref_id, valid_from, valid_until, "
                "created_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    target_binding_id,
                    plan.persona_subjects[0].target_persona_subject_id,
                    ACCOUNT_A,
                    ACCOUNT_A,
                    "persona_profile",
                    "different-ref-id",  # different from plan
                    NOW,
                    None,
                    NOW,
                ),
            )
        conn.commit()

    with psycopg.connect(database_url) as conn:
        with pytest.raises(UnifiedMemoryRestoreConflictError) as exc_info:
            CanonicalMemoryRestoreExecutor(plan).execute(conn)
        conn.rollback()

    assert exc_info.value.code == "persona_binding_conflict"


@pytest.mark.integration
def test_link_conflict_fails_closed(temporary_postgres, tmp_path):
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    _seed_account_a(database_url)

    _preflight, plan = _build_plan_for_account_a()
    planned_subject = plan.persona_subjects[0]
    planned_memory = plan.memory_records[0]
    target_link_id = plan.memory_persona_links[0].target_link_id
    target_memory_id = plan.memory_persona_links[0].target_memory_id

    import psycopg

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO persona_subjects "
                "(persona_subject_id, user_id, display_name_snapshot, lifecycle, "
                "created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s) "
                "ON CONFLICT (persona_subject_id) DO NOTHING",
                (
                    plan.persona_subjects[0].target_persona_subject_id,
                    ACCOUNT_A,
                    planned_subject.display_name_snapshot,
                    planned_subject.lifecycle,
                    planned_subject.created_at,
                    planned_subject.updated_at,
                ),
            )
            cur.execute(
                "INSERT INTO memory_records "
                "(memory_id, user_id, project_id, semantic_species, "
                "text_content, fact_key, fact_value, fact_confidence, "
                "reviewed_at, activated_at, pinned, held, extensions, "
                "created_at, updated_at) VALUES "
                "(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s) "
                "ON CONFLICT (memory_id) DO NOTHING",
                (
                    target_memory_id,
                    planned_memory.target_account_id,
                    planned_memory.target_project_id,
                    planned_memory.semantic_species,
                    planned_memory.text_content,
                    planned_memory.fact_key,
                    planned_memory.fact_value,
                    planned_memory.fact_confidence,
                    planned_memory.reviewed_at,
                    planned_memory.activated_at,
                    planned_memory.pinned,
                    planned_memory.held,
                    __import__("json").dumps(planned_memory.extensions),
                    planned_memory.created_at,
                    planned_memory.updated_at,
                ),
            )
            cur.execute(
                "INSERT INTO memory_persona_links "
                "(link_id, memory_id, user_id, persona_subject_id, "
                "persona_user_id, link_kind, created_at) VALUES "
                "(%s, %s, %s, %s, %s, %s, %s)",
                (
                    target_link_id,
                    target_memory_id,
                    ACCOUNT_A,
                    plan.persona_subjects[0].target_persona_subject_id,
                    ACCOUNT_A,
                    "suggested_by",  # different from plan
                    NOW,
                ),
            )
        conn.commit()

    with psycopg.connect(database_url) as conn:
        with pytest.raises(UnifiedMemoryRestoreConflictError) as exc_info:
            CanonicalMemoryRestoreExecutor(plan).execute(conn)
        conn.rollback()

    assert exc_info.value.code == "memory_persona_link_conflict"


@pytest.mark.integration
def test_provenance_conflict_fails_closed(temporary_postgres, tmp_path):
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    _seed_account_a(database_url)

    _preflight, plan = _build_plan_for_account_a()
    planned_subject = plan.persona_subjects[0]
    planned_memory = plan.memory_records[0]
    target_provenance_id = plan.memory_provenance[0].target_provenance_id
    target_memory_id = plan.memory_provenance[0].target_memory_id

    import psycopg

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO persona_subjects "
                "(persona_subject_id, user_id, display_name_snapshot, lifecycle, "
                "created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s) "
                "ON CONFLICT (persona_subject_id) DO NOTHING",
                (
                    plan.persona_subjects[0].target_persona_subject_id,
                    ACCOUNT_A,
                    planned_subject.display_name_snapshot,
                    planned_subject.lifecycle,
                    planned_subject.created_at,
                    planned_subject.updated_at,
                ),
            )
            cur.execute(
                "INSERT INTO memory_records "
                "(memory_id, user_id, project_id, semantic_species, "
                "text_content, fact_key, fact_value, fact_confidence, "
                "reviewed_at, activated_at, pinned, held, extensions, "
                "created_at, updated_at) VALUES "
                "(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s) "
                "ON CONFLICT (memory_id) DO NOTHING",
                (
                    target_memory_id,
                    planned_memory.target_account_id,
                    planned_memory.target_project_id,
                    planned_memory.semantic_species,
                    planned_memory.text_content,
                    planned_memory.fact_key,
                    planned_memory.fact_value,
                    planned_memory.fact_confidence,
                    planned_memory.reviewed_at,
                    planned_memory.activated_at,
                    planned_memory.pinned,
                    planned_memory.held,
                    __import__("json").dumps(planned_memory.extensions),
                    planned_memory.created_at,
                    planned_memory.updated_at,
                ),
            )
            cur.execute(
                "INSERT INTO memory_provenance "
                "(provenance_id, memory_id, user_id, source_system, "
                "source_record_id, source_thread_id, source_message_id, "
                "source_import_job_id, source_export_fingerprint, "
                "source_subject_kind, source_subject_id, is_imported, "
                "extensions, created_at) VALUES "
                "(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s)",
                (
                    target_provenance_id,
                    target_memory_id,
                    ACCOUNT_A,
                    "openai",
                    "different-source-record-id",  # different from plan
                    None,
                    None,
                    "import-job-1",
                    "sha256:source-export",
                    "importer",
                    "importer-1",
                    True,
                    "{}",
                    NOW,
                ),
            )
        conn.commit()

    with psycopg.connect(database_url) as conn:
        with pytest.raises(UnifiedMemoryRestoreConflictError) as exc_info:
            CanonicalMemoryRestoreExecutor(plan).execute(conn)
        conn.rollback()

    assert exc_info.value.code == "memory_provenance_conflict"


@pytest.mark.integration
def test_late_family_conflict_proves_classify_before_mutate(
    temporary_postgres, tmp_path
):
    """Subjects/bindings/memories/links classify as CREATE; provenance CONFLICTs.

    Executor must raise on Phase 1 classification, before any INSERT runs.
    Read-back must show zero rows in any of the five families.
    """
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    _seed_account_a(database_url)

    _preflight, plan = _build_plan_for_account_a()
    planned_subject = plan.persona_subjects[0]
    planned_memory = plan.memory_records[0]
    target_provenance_id = plan.memory_provenance[0].target_provenance_id
    target_memory_id = plan.memory_provenance[0].target_memory_id

    import psycopg

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO persona_subjects "
                "(persona_subject_id, user_id, display_name_snapshot, lifecycle, "
                "created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s) "
                "ON CONFLICT (persona_subject_id) DO NOTHING",
                (
                    plan.persona_subjects[0].target_persona_subject_id,
                    ACCOUNT_A,
                    planned_subject.display_name_snapshot,
                    planned_subject.lifecycle,
                    planned_subject.created_at,
                    planned_subject.updated_at,
                ),
            )
            cur.execute(
                "INSERT INTO memory_records "
                "(memory_id, user_id, project_id, semantic_species, "
                "text_content, fact_key, fact_value, fact_confidence, "
                "reviewed_at, activated_at, pinned, held, extensions, "
                "created_at, updated_at) VALUES "
                "(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s) "
                "ON CONFLICT (memory_id) DO NOTHING",
                (
                    target_memory_id,
                    planned_memory.target_account_id,
                    planned_memory.target_project_id,
                    planned_memory.semantic_species,
                    planned_memory.text_content,
                    planned_memory.fact_key,
                    planned_memory.fact_value,
                    planned_memory.fact_confidence,
                    planned_memory.reviewed_at,
                    planned_memory.activated_at,
                    planned_memory.pinned,
                    planned_memory.held,
                    __import__("json").dumps(planned_memory.extensions),
                    planned_memory.created_at,
                    planned_memory.updated_at,
                ),
            )
            cur.execute(
                "INSERT INTO memory_provenance "
                "(provenance_id, memory_id, user_id, source_system, "
                "source_record_id, source_thread_id, source_message_id, "
                "source_import_job_id, source_export_fingerprint, "
                "source_subject_kind, source_subject_id, is_imported, "
                "extensions, created_at) VALUES "
                "(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s)",
                (
                    target_provenance_id,
                    target_memory_id,
                    ACCOUNT_A,
                    "openai",
                    "different-source-record-id",
                    None,
                    None,
                    "import-job-1",
                    "sha256:source-export",
                    "importer",
                    "importer-1",
                    True,
                    "{}",
                    NOW,
                ),
            )
        conn.commit()

    with psycopg.connect(database_url) as conn:
        with pytest.raises(UnifiedMemoryRestoreConflictError) as exc_info:
            CanonicalMemoryRestoreExecutor(plan).execute(conn)
        conn.rollback()

    assert exc_info.value.code == "memory_provenance_conflict"

    # Row counts must equal the seeded set exactly. The executor's
    # Phase 2 never started because Phase 1 raised CONFLICT on provenance,
    # so no executor-side INSERTs occurred.
    # Seeded: 1 subject, 0 bindings, 1 memory, 0 links, 1 provenance.
    expected_counts = {
        "persona_subjects": 1,
        "persona_subject_bindings": 0,
        "memory_records": 1,
        "memory_persona_links": 0,
        "memory_provenance": 1,
    }
    for table, expected in expected_counts.items():
        actual = _row_count(database_url, table)
        assert actual == expected, (
            f"expected {expected} seeded rows in {table}, got {actual}; "
            f"any difference proves Phase 2 mutated before the CONFLICT raised."
        )


@pytest.mark.integration
def test_late_dml_failure_rolls_back_partial_canonical_inserts(
    temporary_postgres, tmp_path, monkeypatch
):
    """Subjects/bindings succeed; memory insert FAILS via monkeypatched primitive.

    Phase 1 classification succeeds (subjects/bindings/memories/links/
    provenance all CREATE). Phase 2 begins mutation. We narrowly
    monkeypatch ``CanonicalMemoryRestoreExecutor._insert_memories`` to
    raise after subjects and bindings have already been INSERTed. The
    caller rolls back the open transaction; zero canonical rows persist.
    """
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    _seed_account_a(database_url)

    _preflight, plan = _build_plan_for_account_a()

    def _raise_after_subject_binding_insert(
        self,
        conn,
        plan,
        classification,
    ) -> None:  # pragma: no cover - monkeypatched
        raise RuntimeError("simulated late-family persistence failure")

    monkeypatch.setattr(
        CanonicalMemoryRestoreExecutor,
        "_insert_memories",
        _raise_after_subject_binding_insert,
    )

    import psycopg

    with psycopg.connect(database_url) as conn:
        with pytest.raises(RuntimeError):
            CanonicalMemoryRestoreExecutor(plan).execute(conn)
        conn.rollback()

    for table in (
        "persona_subjects",
        "persona_subject_bindings",
        "memory_records",
        "memory_persona_links",
        "memory_provenance",
    ):
        assert _row_count(database_url, table) == 0, (
            f"expected rollback to zero rows in {table}, got "
            f"{_row_count(database_url, table)}"
        )


@pytest.mark.integration
def test_provenance_multiplicity_preserved_across_replays(temporary_postgres, tmp_path):
    """Two distinct provenance entities for one memory remain distinct after
    first + second identical restore.
    """
    config, database_url = temporary_postgres
    _upgrade(config, "head")
    _seed_account_a(database_url)

    _preflight, plan = _build_plan_for_account_a()

    import psycopg
    import sqlalchemy as sa

    with psycopg.connect(database_url) as conn:
        CanonicalMemoryRestoreExecutor(plan).execute(conn)
        conn.commit()

    engine = sa.create_engine(database_url, future=True)

    def _provenance_count_for_memory(memory_id: str) -> int:
        with engine.connect() as conn:
            return conn.execute(
                sa.text("SELECT COUNT(*) FROM memory_provenance WHERE memory_id = :m"),
                {"m": memory_id},
            ).scalar_one()

    episodic_memory_id = next(
        m.target_memory_id
        for m in plan.memory_records
        if m.semantic_species == "episodic_semantic_memory"
    )
    first_count = _provenance_count_for_memory(episodic_memory_id)
    assert first_count == 2

    with psycopg.connect(database_url) as conn:
        CanonicalMemoryRestoreExecutor(plan).execute(conn)
        conn.commit()

    second_count = _provenance_count_for_memory(episodic_memory_id)
    assert second_count == 2
