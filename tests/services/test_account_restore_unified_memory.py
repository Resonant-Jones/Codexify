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
    CanonicalMemoryRestorePlan,
    UnifiedMemoryRestorePreflight,
    UnifiedMemoryRestorePreflightError,
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

SUBJECT_A = "11111111-1111-1111-1111-111111111111"
SUBJECT_B = "22222222-2222-2222-2222-222222222222"
SUBJECT_A_TARGET = "33333333-3333-3333-3333-333333333333"

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
