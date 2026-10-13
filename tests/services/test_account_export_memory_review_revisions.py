"""Focused account-export.v6 proof for ordinary-memory review revisions.

UMS-05C10A-P. Proves that the seven-family canonical Unified Memory graph
serializes ``memory_review_revisions`` with exact field fidelity,
deterministic ordering, exact manifest counts, and account isolation — and
that ``account-export.v5`` is NOT silently redefined into v6.

Malformed canonical review history must fail closed at export rather than be
emitted or repaired. Provenance extensions are never consulted to repair it.

This suite is intentionally separate from the known-red
``test_account_export_unified_memory.py``.

It does not implement any review mutation: history rows are seeded directly
as canonical persistence, and no test asserts that any recorded transition is
a legal runtime mutation.
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
    REVIEW_REVISION_MANIFEST_SCHEMA_VERSION,
    REVISION_MANIFEST_SCHEMA_VERSION,
    build_account_export_zip,
)

ACCOUNT_A = "account-a"
NOW = "2026-09-28T12:00:00+00:00"
LATER = "2026-09-28T13:00:00+00:00"

MEMORY_A = "33333333-3333-3333-3333-333333333333"
MEMORY_B = "55555555-5555-5555-5555-555555555555"
SUBJECT_A = "11111111-1111-1111-1111-111111111111"

RR1 = "dddddddd-1111-1111-1111-111111111111"
RR2 = "dddddddd-2222-2222-2222-222222222222"
RR3 = "dddddddd-3333-3333-3333-333333333333"
RRB1 = "dddddddd-4444-4444-4444-444444444444"

V6_CANONICAL_FAMILIES = {
    "persona_subjects",
    "persona_subject_bindings",
    "memory_records",
    "memory_persona_links",
    "memory_provenance",
    "memory_revisions",
    "memory_review_revisions",
}

V5_CANONICAL_FAMILIES = V6_CANONICAL_FAMILIES - {"memory_review_revisions"}


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
    }


def _memory(
    memory_id: str,
    *,
    review_state: str = "approved",
    text: str = "content",
    species: str = "episodic_semantic_memory",
) -> dict[str, Any]:
    return {
        "memory_id": memory_id,
        "user_id": ACCOUNT_A,
        "project_id": None,
        "semantic_species": species,
        "text_content": text,
        "fact_key": None,
        "fact_value": None,
        "fact_confidence": None,
        "reviewed_at": NOW,
        "activated_at": NOW,
        "pinned": False,
        "held": False,
        "review_state": review_state,
        "lifecycle_state": "active",
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


def _review_revision(
    review_revision_id: str,
    memory_id: str,
    number: int,
    old: str,
    new: str,
    *,
    account: str = ACCOUNT_A,
    actor: str | None = None,
    created_at: str = NOW,
) -> dict[str, Any]:
    return {
        "review_revision_id": review_revision_id,
        "memory_id": memory_id,
        "user_id": account,
        "revision_number": number,
        "old_review_state": old,
        "new_review_state": new,
        "actor_account_id": actor or account,
        "created_at": created_at,
    }


def _bundle_with_history() -> dict[str, list[dict[str, Any]]]:
    bundle = _empty_bundle()
    bundle["memory_records"] = [_memory(MEMORY_A)]
    bundle["memory_provenance"] = [
        _provenance(MEMORY_A, "99999999-9999-9999-9999-999999999999")
    ]
    # Deliberately out of order: the exporter must sort deterministically.
    bundle["memory_review_revisions"] = [
        _review_revision(RR3, MEMORY_A, 3, "disputed", "approved", created_at=LATER),
        _review_revision(RR1, MEMORY_A, 1, "pending", "approved"),
        _review_revision(RR2, MEMORY_A, 2, "approved", "disputed"),
    ]
    return bundle


class ReviewExportDB:
    def __init__(self, bundle: dict[str, list[dict[str, Any]]]):
        self.bundle = bundle
        self.calls: list[tuple[str, bool]] = []

    def fetch_account_export_bundle_for_user(
        self,
        user_id: str,
        *,
        include_unified_memory: bool = False,
    ) -> dict[str, list[dict[str, Any]]]:
        self.calls.append((user_id, include_unified_memory))
        return deepcopy(self.bundle)

    def fetch_account_export_projects_for_user(self, user_id: str):
        return deepcopy(self.bundle["projects"])

    def fetch_account_export_chat_threads_for_user(self, user_id: str):
        return deepcopy(self.bundle["chat_threads"])

    def fetch_account_export_chat_messages_for_user(self, user_id: str):
        return deepcopy(self.bundle["chat_messages"])


def _archive(db: ReviewExportDB, *, schema_version: str) -> bytes:
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
# 1-3: v6 exists with seven families; v5 keeps exactly six.
# ---------------------------------------------------------------------------


def test_v6_manifest_identifies_schema_and_review_family() -> None:
    db = ReviewExportDB(_bundle_with_history())
    manifest, _ = _read(
        _archive(db, schema_version=REVIEW_REVISION_MANIFEST_SCHEMA_VERSION)
    )

    assert manifest["schema_version"] == "account-export.v6"
    assert "memory_review_revisions" in manifest["included_families"]
    assert (
        "entities/memory_review_revisions.json"
        in manifest["integrity"]["payload_files"]
    )
    assert _canonical_families(manifest) == V6_CANONICAL_FAMILIES
    assert len(V6_CANONICAL_FAMILIES) == 7


def test_v5_remains_exactly_six_families() -> None:
    db = ReviewExportDB(_bundle_with_history())
    manifest, payloads = _read(
        _archive(db, schema_version=REVISION_MANIFEST_SCHEMA_VERSION)
    )

    assert manifest["schema_version"] == "account-export.v5"
    assert _canonical_families(manifest) == V5_CANONICAL_FAMILIES
    # v5 is never widened to carry review history.
    assert "memory_review_revisions" not in manifest["included_families"]
    assert "memory_review_revisions" not in payloads


# ---------------------------------------------------------------------------
# 4-12: exact preservation, ordering, count, isolation.
# ---------------------------------------------------------------------------


def test_v6_exports_review_history_exactly() -> None:
    db = ReviewExportDB(_bundle_with_history())
    _, payloads = _read(
        _archive(db, schema_version=REVIEW_REVISION_MANIFEST_SCHEMA_VERSION)
    )

    rows = payloads["memory_review_revisions"]
    assert len(rows) == 3
    assert [r["review_revision_id"] for r in rows] == [RR1, RR2, RR3]
    assert [r["revision_number"] for r in rows] == [1, 2, 3]
    assert [(r["old_review_state"], r["new_review_state"]) for r in rows] == [
        ("pending", "approved"),
        ("approved", "disputed"),
        ("disputed", "approved"),
    ]
    assert rows[0]["actor_account_id"] == ACCOUNT_A
    assert rows[0]["user_id"] == ACCOUNT_A
    assert rows[0]["memory_id"] == MEMORY_A
    assert rows[0]["created_at"] == NOW
    assert rows[2]["created_at"] == LATER


def test_v6_orders_deterministically_by_memory_then_number() -> None:
    bundle = _bundle_with_history()
    bundle["memory_records"].append(_memory(MEMORY_B, review_state="approved"))
    bundle["memory_provenance"].append(
        _provenance(MEMORY_B, "88888888-8888-8888-8888-888888888888")
    )
    bundle["memory_review_revisions"].append(
        _review_revision(RRB1, MEMORY_B, 1, "pending", "approved")
    )

    db = ReviewExportDB(bundle)
    _, payloads = _read(
        _archive(db, schema_version=REVIEW_REVISION_MANIFEST_SCHEMA_VERSION)
    )
    rows = payloads["memory_review_revisions"]

    assert [(r["memory_id"], r["revision_number"]) for r in rows] == [
        (MEMORY_A, 1),
        (MEMORY_A, 2),
        (MEMORY_A, 3),
        (MEMORY_B, 1),
    ]


def test_v6_orders_ten_before_two_numerically() -> None:
    """Ordering is numeric, not lexicographic: 10 must follow 9, not 2."""
    bundle = _empty_bundle()
    bundle["memory_records"] = [_memory(MEMORY_A, review_state="pending")]
    bundle["memory_provenance"] = [
        _provenance(MEMORY_A, "99999999-9999-9999-9999-999999999999")
    ]
    # pending -> approved (1) ... alternating to reach an odd terminal state.
    states = ["approved", "disputed"] * 5
    rows = []
    previous = "pending"
    for number in range(1, 11):
        rows.append(
            _review_revision(
                f"eeeeeeee-{number:04d}-0000-0000-000000000000",
                MEMORY_A,
                number,
                previous,
                states[number - 1],
            )
        )
        previous = states[number - 1]
    bundle["memory_records"][0]["review_state"] = previous
    bundle["memory_review_revisions"] = rows

    db = ReviewExportDB(bundle)
    _, payloads = _read(
        _archive(db, schema_version=REVIEW_REVISION_MANIFEST_SCHEMA_VERSION)
    )
    assert [r["revision_number"] for r in payloads["memory_review_revisions"]] == list(
        range(1, 11)
    )


def test_v6_manifest_reports_exact_review_count() -> None:
    db = ReviewExportDB(_bundle_with_history())
    manifest, _ = _read(
        _archive(db, schema_version=REVIEW_REVISION_MANIFEST_SCHEMA_VERSION)
    )
    assert manifest["entity_counts"]["memory_review_revisions"] == 3


def test_zero_history_account_exports_validly() -> None:
    bundle = _empty_bundle()
    bundle["memory_records"] = [_memory(MEMORY_A, review_state="approved")]
    bundle["memory_provenance"] = [
        _provenance(MEMORY_A, "99999999-9999-9999-9999-999999999999")
    ]
    db = ReviewExportDB(bundle)
    manifest, payloads = _read(
        _archive(db, schema_version=REVIEW_REVISION_MANIFEST_SCHEMA_VERSION)
    )
    # A memory with zero review revisions is valid; absence is not fabricated.
    assert manifest["entity_counts"]["memory_review_revisions"] == 0
    assert payloads["memory_review_revisions"] == []


def test_v6_is_account_scoped() -> None:
    db = ReviewExportDB(_bundle_with_history())
    _, payloads = _read(
        _archive(db, schema_version=REVIEW_REVISION_MANIFEST_SCHEMA_VERSION)
    )
    assert {r["user_id"] for r in payloads["memory_review_revisions"]} == {ACCOUNT_A}


# ---------------------------------------------------------------------------
# 14-20: malformed history fails closed.
# ---------------------------------------------------------------------------


def _expect_export_failure(bundle) -> None:
    db = ReviewExportDB(bundle)
    with pytest.raises(RuntimeError):
        _archive(db, schema_version=REVIEW_REVISION_MANIFEST_SCHEMA_VERSION)


def test_export_rejects_personal_fact_parent() -> None:
    bundle = _bundle_with_history()
    bundle["memory_records"][0]["semantic_species"] = "verified_personal_fact"
    bundle["memory_records"][0]["text_content"] = None
    _expect_export_failure(bundle)


def test_export_rejects_invalid_review_token() -> None:
    bundle = _bundle_with_history()
    bundle["memory_review_revisions"][0]["new_review_state"] = "quarantined"
    _expect_export_failure(bundle)


def test_export_rejects_noop_transition() -> None:
    bundle = _bundle_with_history()
    bundle["memory_review_revisions"][0]["new_review_state"] = "pending"
    _expect_export_failure(bundle)


def test_export_rejects_sequence_gap() -> None:
    bundle = _bundle_with_history()
    bundle["memory_review_revisions"] = [
        _review_revision(RR1, MEMORY_A, 1, "pending", "approved"),
        _review_revision(RR3, MEMORY_A, 3, "disputed", "approved"),
    ]
    _expect_export_failure(bundle)


def test_export_rejects_chain_mismatch() -> None:
    bundle = _bundle_with_history()
    # Bundle order is RR3, RR1, RR2. Break the RR1 -> RR2 link: RR1 resolves to
    # "approved" but RR2 then claims it started from "rejected".
    bundle["memory_review_revisions"][2]["old_review_state"] = "rejected"
    _expect_export_failure(bundle)


def test_export_rejects_final_state_mismatch() -> None:
    bundle = _bundle_with_history()
    # Terminal historical state is "approved"; the parent claims "pending".
    bundle["memory_records"][0]["review_state"] = "pending"
    _expect_export_failure(bundle)


def test_export_rejects_actor_account_mismatch() -> None:
    bundle = _bundle_with_history()
    bundle["memory_review_revisions"][0]["actor_account_id"] = "someone-else"
    _expect_export_failure(bundle)


def test_export_rejects_orphan_review_revision() -> None:
    bundle = _bundle_with_history()
    bundle["memory_review_revisions"][0]["memory_id"] = "no-such-memory"
    _expect_export_failure(bundle)


def test_export_rejects_duplicate_sequence_occupancy() -> None:
    bundle = _bundle_with_history()
    # Two rows claiming revision 1 on the same memory.
    bundle["memory_review_revisions"] = [
        _review_revision(RR1, MEMORY_A, 1, "pending", "approved"),
        _review_revision(RR2, MEMORY_A, 1, "disputed", "approved"),
    ]
    _expect_export_failure(bundle)


def test_export_does_not_repair_using_provenance_extensions() -> None:
    """Malformed history is never repaired from non-authority metadata."""
    bundle = _bundle_with_history()
    bundle["memory_review_revisions"] = [
        _review_revision(RR1, MEMORY_A, 1, "pending", "approved"),
    ]
    bundle["memory_records"][0]["review_state"] = "disputed"
    # Provenance claims a different history; it must not be consulted.
    bundle["memory_provenance"][0]["extensions"] = {
        "review_state_history": ["pending", "approved", "disputed"]
    }
    _expect_export_failure(bundle)
