"""Focused account-export.v7 proof for ordinary-memory lifecycle revisions.

UMS-05C10B-P. Proves that the eight-family canonical Unified Memory graph
serializes ``memory_lifecycle_revisions`` with exact field fidelity,
deterministic numeric ordering, exact manifest counts, and account
isolation — and that ``account-export.v6`` is NOT silently redefined.

The load-bearing obligation is pre-retirement posture: a transition
``active -> retired`` and a transition ``dormant -> retired`` must remain
distinguishable in the archive, because that is the fact C10B-R proved the
restore contract needs and current storage could not preserve.

Malformed canonical lifecycle history must fail closed at export rather
than be emitted or repaired. Provenance extensions are never consulted to
repair it.

This suite is intentionally separate from the known-red
``test_account_export_unified_memory.py``.

It implements no retire/restore action: history rows are seeded directly
as canonical persistence, and no test asserts that any recorded transition
is a legal runtime mutation.
"""

from __future__ import annotations

import io
import json
import zipfile
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from guardian.services.account_export import (
    LIFECYCLE_REVISION_MANIFEST_SCHEMA_VERSION,
    REVIEW_REVISION_MANIFEST_SCHEMA_VERSION,
    build_account_export_zip,
)

ACCOUNT_A = "account-a"
NOW = "2026-09-29T12:00:00+00:00"
LATER = "2026-09-29T13:00:00+00:00"

MEMORY_A = "44444444-4444-4444-4444-444444444444"
MEMORY_B = "66666666-6666-6666-6666-666666666666"
SUBJECT_A = "11111111-1111-1111-1111-111111111111"

LCR1 = "eeeeeeee-1111-1111-1111-111111111111"
LCR2 = "eeeeeeee-2222-2222-2222-222222222222"
LCR_B1 = "eeeeeeee-3333-3333-3333-333333333333"

V6_CANONICAL_FAMILIES = {
    "persona_subjects",
    "persona_subject_bindings",
    "memory_records",
    "memory_persona_links",
    "memory_provenance",
    "memory_revisions",
    "memory_review_revisions",
}
V7_CANONICAL_FAMILIES = V6_CANONICAL_FAMILIES | {"memory_lifecycle_revisions"}


def _empty_bundle() -> dict[str, list[dict[str, Any]]]:
    return {
        "projects": [],
        "chat_threads": [],
        "chat_messages": [],
        "uploaded_documents": [],
        "generated_documents": [],
        "uploaded_images": [],
        "generated_images": [],
        "media_assets": [],
        "media_aliases": [],
        "persona_profiles": [],
        "persona_profile_revisions": [],
        "persona_profile_bindings": [],
        "persona_subjects": [
            {
                "persona_subject_id": SUBJECT_A,
                "user_id": ACCOUNT_A,
                "display_name_snapshot": "Subject A",
                "lifecycle": "active",
                "created_at": NOW,
                "updated_at": NOW,
            }
        ],
        "persona_subject_bindings": [],
        "memory_records": [],
        "memory_persona_links": [],
        "memory_provenance": [],
        "memory_revisions": [],
        "memory_review_revisions": [],
        "memory_lifecycle_revisions": [],
    }


def _memory(
    memory_id: str,
    *,
    lifecycle_state: str = "retired",
    species: str = "episodic_semantic_memory",
) -> dict[str, Any]:
    return {
        "memory_id": memory_id,
        "user_id": ACCOUNT_A,
        "project_id": None,
        "semantic_species": species,
        "text_content": None if species != "episodic_semantic_memory" else "content",
        "fact_key": None if species == "episodic_semantic_memory" else "preferred_mode",
        "fact_value": None if species == "episodic_semantic_memory" else "local-first",
        "fact_confidence": None if species == "episodic_semantic_memory" else 0.9,
        "reviewed_at": NOW,
        "activated_at": NOW,
        "pinned": False,
        "held": False,
        "review_state": "approved",
        "lifecycle_state": lifecycle_state,
        "extensions": None,
        "created_at": NOW,
        "updated_at": LATER,
    }


def _provenance(memory_id: str, provenance_id: str) -> dict[str, Any]:
    return {
        "provenance_id": provenance_id,
        "memory_id": memory_id,
        "user_id": ACCOUNT_A,
        "source_system": "codexify",
        "source_record_id": f"source-{memory_id}",
        "source_thread_id": None,
        "source_message_id": None,
        "source_import_job_id": None,
        "source_export_fingerprint": None,
        "source_subject_kind": "vault",
        "source_subject_id": "vault-editor",
        "is_imported": False,
        "extensions": None,
        "created_at": NOW,
    }


def _lifecycle_revision(
    lifecycle_revision_id: str,
    memory_id: str,
    number: int,
    old: str,
    new: str,
    *,
    created_at: str = NOW,
) -> dict[str, Any]:
    return {
        "lifecycle_revision_id": lifecycle_revision_id,
        "memory_id": memory_id,
        "user_id": ACCOUNT_A,
        "revision_number": number,
        "old_lifecycle_state": old,
        "new_lifecycle_state": new,
        "created_at": created_at,
    }


def _retired_from_active_bundle() -> dict[str, list[dict[str, Any]]]:
    bundle = _empty_bundle()
    bundle["memory_records"] = [_memory(MEMORY_A, lifecycle_state="retired")]
    bundle["memory_provenance"] = [
        _provenance(MEMORY_A, "99999999-9999-9999-9999-999999999999")
    ]
    bundle["memory_lifecycle_revisions"] = [
        _lifecycle_revision(LCR1, MEMORY_A, 1, "active", "retired")
    ]
    return bundle


def _retired_from_dormant_bundle() -> dict[str, list[dict[str, Any]]]:
    bundle = _empty_bundle()
    bundle["memory_records"] = [_memory(MEMORY_A, lifecycle_state="retired")]
    bundle["memory_provenance"] = [
        _provenance(MEMORY_A, "99999999-9999-9999-9999-999999999999")
    ]
    bundle["memory_lifecycle_revisions"] = [
        _lifecycle_revision(LCR1, MEMORY_A, 1, "dormant", "retired")
    ]
    return bundle


class LifecycleExportDB:
    def __init__(self, bundle: dict[str, list[dict[str, Any]]]):
        self.bundle = bundle

    def fetch_account_export_bundle_for_user(
        self,
        user_id: str,
        *,
        include_unified_memory: bool = False,
    ) -> dict[str, list[dict[str, Any]]]:
        return deepcopy(self.bundle)

    def fetch_account_export_projects_for_user(self, user_id: str):
        return deepcopy(self.bundle["projects"])

    def fetch_account_export_chat_threads_for_user(self, user_id: str):
        return deepcopy(self.bundle["chat_threads"])

    def fetch_account_export_chat_messages_for_user(self, user_id: str):
        return deepcopy(self.bundle["chat_messages"])


def _archive(db: LifecycleExportDB, *, schema_version: str) -> bytes:
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


def _read(archive_bytes: bytes):
    with zipfile.ZipFile(io.BytesIO(archive_bytes), "r") as archive:
        manifest = json.loads(archive.read("manifest.json"))
        payloads = {
            family: json.loads(archive.read(f"entities/{family}.json"))
            for family in manifest["included_families"]
        }
    return manifest, payloads


def _canonical_families(manifest: dict[str, Any]) -> set[str]:
    return {
        family
        for family in manifest["included_families"]
        if family.startswith(("persona_subject", "memory_"))
    }


# ---------------------------------------------------------------------------
# 1-3: v7 exists with eight families; v6 keeps exactly seven.
# ---------------------------------------------------------------------------


def test_v7_manifest_identifies_schema_and_lifecycle_family() -> None:
    db = LifecycleExportDB(_retired_from_active_bundle())
    manifest, _ = _read(
        _archive(db, schema_version=LIFECYCLE_REVISION_MANIFEST_SCHEMA_VERSION)
    )

    assert manifest["schema_version"] == "account-export.v7"
    assert "memory_lifecycle_revisions" in manifest["included_families"]
    assert (
        "entities/memory_lifecycle_revisions.json"
        in manifest["integrity"]["payload_files"]
    )
    assert _canonical_families(manifest) == V7_CANONICAL_FAMILIES
    assert len(V7_CANONICAL_FAMILIES) == 8


def test_v6_remains_exactly_seven_families() -> None:
    db = LifecycleExportDB(_retired_from_active_bundle())
    manifest, payloads = _read(
        _archive(db, schema_version=REVIEW_REVISION_MANIFEST_SCHEMA_VERSION)
    )

    assert manifest["schema_version"] == "account-export.v6"
    assert _canonical_families(manifest) == V6_CANONICAL_FAMILIES
    assert len(V6_CANONICAL_FAMILIES) == 7
    # v6 is never widened to carry lifecycle history.
    assert "memory_lifecycle_revisions" not in manifest["included_families"]
    assert "memory_lifecycle_revisions" not in payloads


# ---------------------------------------------------------------------------
# 4-13: exact preservation, ordering, count, isolation.
# ---------------------------------------------------------------------------


def test_v7_exports_lifecycle_history_exactly() -> None:
    bundle = _retired_from_active_bundle()
    bundle["memory_lifecycle_revisions"].append(
        _lifecycle_revision(LCR2, MEMORY_A, 2, "retired", "active", created_at=LATER)
    )
    bundle["memory_records"][0]["lifecycle_state"] = "active"
    db = LifecycleExportDB(bundle)
    _, payloads = _read(
        _archive(db, schema_version=LIFECYCLE_REVISION_MANIFEST_SCHEMA_VERSION)
    )

    rows = payloads["memory_lifecycle_revisions"]
    assert len(rows) == 2
    assert [r["lifecycle_revision_id"] for r in rows] == [LCR1, LCR2]
    assert [r["revision_number"] for r in rows] == [1, 2]
    assert [(r["old_lifecycle_state"], r["new_lifecycle_state"]) for r in rows] == [
        ("active", "retired"),
        ("retired", "active"),
    ]
    assert rows[0]["user_id"] == ACCOUNT_A
    assert rows[0]["created_at"] == NOW
    assert rows[1]["created_at"] == LATER
    # Deliberately absent: intent/source/actor evidence is not revision data.
    assert "actor_account_id" not in rows[0]
    assert "reason" not in rows[0]


def test_v7_manifest_reports_exact_lifecycle_count() -> None:
    db = LifecycleExportDB(_retired_from_active_bundle())
    manifest, _ = _read(
        _archive(db, schema_version=LIFECYCLE_REVISION_MANIFEST_SCHEMA_VERSION)
    )
    assert manifest["entity_counts"]["memory_lifecycle_revisions"] == 1


def test_zero_history_account_exports_validly() -> None:
    bundle = _empty_bundle()
    bundle["memory_records"] = [_memory(MEMORY_A, lifecycle_state="retired")]
    bundle["memory_provenance"] = [
        _provenance(MEMORY_A, "99999999-9999-9999-9999-999999999999")
    ]
    db = LifecycleExportDB(bundle)
    manifest, payloads = _read(
        _archive(db, schema_version=LIFECYCLE_REVISION_MANIFEST_SCHEMA_VERSION)
    )
    # A currently-retired memory with no reconstructable pre-retirement
    # history stays exportable; absence is never filled in.
    assert manifest["entity_counts"]["memory_lifecycle_revisions"] == 0
    assert payloads["memory_lifecycle_revisions"] == []


def test_v7_orders_deterministically_by_memory_then_number() -> None:
    bundle = _retired_from_active_bundle()
    bundle["memory_records"].append(_memory(MEMORY_B, lifecycle_state="dormant"))
    bundle["memory_provenance"].append(
        _provenance(MEMORY_B, "88888888-8888-8888-8888-888888888888")
    )
    bundle["memory_lifecycle_revisions"].append(
        _lifecycle_revision(LCR_B1, MEMORY_B, 1, "active", "dormant")
    )
    db = LifecycleExportDB(bundle)
    _, payloads = _read(
        _archive(db, schema_version=LIFECYCLE_REVISION_MANIFEST_SCHEMA_VERSION)
    )
    rows = payloads["memory_lifecycle_revisions"]

    assert [(r["memory_id"], r["revision_number"]) for r in rows] == [
        (MEMORY_A, 1),
        (MEMORY_B, 1),
    ]


def test_v7_orders_ten_before_two_numerically() -> None:
    """Ordering is numeric, not lexicographic: 10 follows 9, not 2."""
    bundle = _empty_bundle()
    bundle["memory_records"] = [_memory(MEMORY_A, lifecycle_state="dormant")]
    bundle["memory_provenance"] = [
        _provenance(MEMORY_A, "99999999-9999-9999-9999-999999999999")
    ]
    rows = []
    previous = "active"
    for number in range(1, 11):
        new_state = "dormant" if number % 2 == 1 else "active"
        rows.append(
            _lifecycle_revision(
                f"eeeeeeee-{number:04d}-0000-0000-000000000000",
                MEMORY_A,
                number,
                previous,
                new_state,
            )
        )
        previous = new_state
    bundle["memory_records"][0]["lifecycle_state"] = previous
    bundle["memory_lifecycle_revisions"] = rows

    db = LifecycleExportDB(bundle)
    _, payloads = _read(
        _archive(db, schema_version=LIFECYCLE_REVISION_MANIFEST_SCHEMA_VERSION)
    )
    assert [
        r["revision_number"] for r in payloads["memory_lifecycle_revisions"]
    ] == list(range(1, 11))


def test_v7_is_account_scoped() -> None:
    db = LifecycleExportDB(_retired_from_active_bundle())
    _, payloads = _read(
        _archive(db, schema_version=LIFECYCLE_REVISION_MANIFEST_SCHEMA_VERSION)
    )
    assert {r["user_id"] for r in payloads["memory_lifecycle_revisions"]} == {ACCOUNT_A}


# ---------------------------------------------------------------------------
# 22-23: the load-bearing pre-retirement posture obligation.
# ---------------------------------------------------------------------------


def test_active_to_retired_preserves_old_state() -> None:
    db = LifecycleExportDB(_retired_from_active_bundle())
    _, payloads = _read(
        _archive(db, schema_version=LIFECYCLE_REVISION_MANIFEST_SCHEMA_VERSION)
    )
    row = payloads["memory_lifecycle_revisions"][0]
    assert row["old_lifecycle_state"] == "active"
    assert row["new_lifecycle_state"] == "retired"


def test_dormant_to_retired_preserves_old_state() -> None:
    db = LifecycleExportDB(_retired_from_dormant_bundle())
    _, payloads = _read(
        _archive(db, schema_version=LIFECYCLE_REVISION_MANIFEST_SCHEMA_VERSION)
    )
    row = payloads["memory_lifecycle_revisions"][0]
    assert row["old_lifecycle_state"] == "dormant"
    assert row["new_lifecycle_state"] == "retired"


def test_two_retirement_postures_remain_distinguishable() -> None:
    """The core C10B-R finding: active-retired != dormant-retired."""
    from_active = _read(
        _archive(
            LifecycleExportDB(_retired_from_active_bundle()),
            schema_version=LIFECYCLE_REVISION_MANIFEST_SCHEMA_VERSION,
        )
    )[1]["memory_lifecycle_revisions"][0]
    from_dormant = _read(
        _archive(
            LifecycleExportDB(_retired_from_dormant_bundle()),
            schema_version=LIFECYCLE_REVISION_MANIFEST_SCHEMA_VERSION,
        )
    )[1]["memory_lifecycle_revisions"][0]

    assert from_active["old_lifecycle_state"] != from_dormant["old_lifecycle_state"]
    assert from_active["new_lifecycle_state"] == from_dormant["new_lifecycle_state"]


# ---------------------------------------------------------------------------
# 15-21, 25: malformed history fails closed.
# ---------------------------------------------------------------------------


def _expect_export_failure(bundle) -> None:
    db = LifecycleExportDB(bundle)
    with pytest.raises(RuntimeError):
        _archive(db, schema_version=LIFECYCLE_REVISION_MANIFEST_SCHEMA_VERSION)


def test_export_rejects_unsupported_parent_species() -> None:
    bundle = _retired_from_active_bundle()
    bundle["memory_records"][0]["semantic_species"] = "verified_personal_fact"
    bundle["memory_records"][0]["text_content"] = None
    _expect_export_failure(bundle)


def test_export_rejects_invalid_lifecycle_token() -> None:
    bundle = _retired_from_active_bundle()
    bundle["memory_lifecycle_revisions"][0]["new_lifecycle_state"] = "archived"
    _expect_export_failure(bundle)


def test_export_rejects_noop_transition() -> None:
    bundle = _retired_from_active_bundle()
    bundle["memory_lifecycle_revisions"][0]["new_lifecycle_state"] = "active"
    _expect_export_failure(bundle)


def test_export_rejects_sequence_gap() -> None:
    bundle = _retired_from_active_bundle()
    bundle["memory_lifecycle_revisions"] = [
        _lifecycle_revision(LCR1, MEMORY_A, 1, "active", "dormant"),
        _lifecycle_revision(LCR2, MEMORY_A, 3, "dormant", "retired"),
    ]
    bundle["memory_records"][0]["lifecycle_state"] = "retired"
    _expect_export_failure(bundle)


def test_export_rejects_duplicate_sequence() -> None:
    bundle = _retired_from_active_bundle()
    bundle["memory_lifecycle_revisions"] = [
        _lifecycle_revision(LCR1, MEMORY_A, 1, "active", "retired"),
        _lifecycle_revision(LCR2, MEMORY_A, 1, "dormant", "retired"),
    ]
    _expect_export_failure(bundle)


def test_export_rejects_chain_mismatch() -> None:
    bundle = _retired_from_active_bundle()
    bundle["memory_lifecycle_revisions"] = [
        _lifecycle_revision(LCR1, MEMORY_A, 1, "active", "retired"),
        _lifecycle_revision(LCR2, MEMORY_A, 2, "active", "dormant"),
    ]
    bundle["memory_records"][0]["lifecycle_state"] = "dormant"
    _expect_export_failure(bundle)


def test_export_rejects_final_state_mismatch() -> None:
    bundle = _retired_from_active_bundle()
    bundle["memory_records"][0]["lifecycle_state"] = "active"
    _expect_export_failure(bundle)


def test_export_rejects_orphan_lifecycle_revision() -> None:
    bundle = _retired_from_active_bundle()
    bundle["memory_lifecycle_revisions"][0]["memory_id"] = "no-such-memory"
    _expect_export_failure(bundle)


def test_export_does_not_repair_using_provenance_extensions() -> None:
    """Malformed history is never repaired from non-authority metadata."""
    bundle = _retired_from_active_bundle()
    bundle["memory_lifecycle_revisions"] = []
    bundle["memory_records"][0]["lifecycle_state"] = "dormant"
    # Provenance claims a lifecycle history; it must not be consulted.
    bundle["memory_provenance"][0]["extensions"] = {
        "lifecycle_history": ["active", "retired"]
    }
    db = LifecycleExportDB(bundle)
    _, payloads = _read(
        _archive(db, schema_version=LIFECYCLE_REVISION_MANIFEST_SCHEMA_VERSION)
    )
    # Zero history stays zero; the claimed history is not adopted.
    assert payloads["memory_lifecycle_revisions"] == []
