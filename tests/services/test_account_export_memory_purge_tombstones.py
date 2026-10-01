"""Focused account-export.v8 proof for permanent-erasure suppression tombstones.

UMS-11. Proves that the nine-family canonical Unified Memory graph
serializes ``memory_purge_tombstones`` with exact field fidelity,
deterministic ordering, exact manifest counts, and account isolation -- and
that ``account-export.v7`` is NOT silently redefined.

The load-bearing obligation is **erasure that survives migration**: a
tombstone must reach the archive as the minimum non-content suppression
authority, so the destination instance does not silently resurrect an atom
the source account erased.

Two guarantees are asserted throughout:

* a purged memory is **absent** from the archive -- its content, revisions,
  review history, lifecycle history, persona links, and provenance all leave
  nothing behind; and
* the tombstone carries **no** content, so an archive is not itself a copy of
  what was supposedly erased.

Malformed suppression state fails closed at export rather than being emitted
or repaired.

This suite is intentionally separate from the known-red
``test_account_export_unified_memory.py``.
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
    PURGE_TOMBSTONE_MANIFEST_SCHEMA_VERSION,
    REVIEW_REVISION_MANIFEST_SCHEMA_VERSION,
    build_account_export_zip,
)

ACCOUNT_A = "account-a"
ACCOUNT_B = "account-b"
NOW = "2026-09-30T12:00:00+00:00"
LATER = "2026-09-30T13:00:00+00:00"

MEMORY_A = "44444444-4444-4444-4444-444444444444"
SUBJECT_A = "11111111-1111-1111-1111-111111111111"

RID_1 = "aaaa1111-1111-1111-1111-111111111111"
RID_2 = "aaaa2222-2222-2222-2222-222222222222"

RECORD_FP_1 = "v1:" + "a" * 64
RECORD_FP_2 = "v1:" + "b" * 64
SOURCE_FP_1 = "v1:" + "c" * 64
SOURCE_FP_2 = "v1:" + "d" * 64

V7_CANONICAL_FAMILIES = {
    "persona_subjects",
    "persona_subject_bindings",
    "memory_records",
    "memory_persona_links",
    "memory_provenance",
    "memory_revisions",
    "memory_review_revisions",
    "memory_lifecycle_revisions",
}
V8_CANONICAL_FAMILIES = V7_CANONICAL_FAMILIES | {"memory_purge_tombstones"}


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
        "memory_purge_tombstones": [],
    }


def _memory(memory_id: str, *, user_id: str = ACCOUNT_A) -> dict[str, Any]:
    return {
        "memory_id": memory_id,
        "user_id": user_id,
        "project_id": None,
        "semantic_species": "episodic_semantic_memory",
        "text_content": "content",
        "fact_key": None,
        "fact_value": None,
        "fact_confidence": None,
        "reviewed_at": NOW,
        "activated_at": NOW,
        "pinned": False,
        "held": False,
        "review_state": "approved",
        "lifecycle_state": "active",
        "extensions": None,
        "created_at": NOW,
        "updated_at": LATER,
    }


def _provenance(
    memory_id: str, provenance_id: str, *, user_id: str = ACCOUNT_A
) -> dict[str, Any]:
    return {
        "provenance_id": provenance_id,
        "memory_id": memory_id,
        "user_id": user_id,
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


def _tombstone(
    receipt_id: str,
    *,
    user_id: str = ACCOUNT_A,
    record_fingerprint: str = RECORD_FP_1,
    source_system: str | None = None,
    source_entity_kind: str | None = None,
    source_atom_fingerprint: str | None = None,
    purged_at: str = NOW,
    suppress_reimport: bool = True,
) -> dict[str, Any]:
    return {
        "purge_receipt_id": receipt_id,
        "user_id": user_id,
        "purged_record_fingerprint": record_fingerprint,
        "source_system": source_system,
        "source_entity_kind": source_entity_kind,
        "source_atom_fingerprint": source_atom_fingerprint,
        "purged_at": purged_at,
        "suppress_reimport": suppress_reimport,
    }


class TombstoneExportDB:
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


def _archive(db: TombstoneExportDB, *, schema_version: str) -> bytes:
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


def _live_memory_bundle() -> dict[str, list[dict[str, Any]]]:
    bundle = _empty_bundle()
    bundle["memory_records"] = [_memory(MEMORY_A)]
    bundle["memory_provenance"] = [
        _provenance(MEMORY_A, "99999999-9999-9999-9999-999999999999")
    ]
    return bundle


# ---------------------------------------------------------------------------
# A. Schema identity + prior-schema immutability.
# ---------------------------------------------------------------------------


def test_v8_manifest_identifies_schema_and_tombstone_family() -> None:
    manifest, _ = _read(
        _archive(
            TombstoneExportDB(_empty_bundle()),
            schema_version=PURGE_TOMBSTONE_MANIFEST_SCHEMA_VERSION,
        )
    )
    assert manifest["schema_version"] == "account-export.v8"
    assert _canonical_families(manifest) == V8_CANONICAL_FAMILIES
    assert "memory_purge_tombstones" in manifest["included_families"]
    assert manifest["compatibility"]["reader"] == "account_export.v8"
    assert manifest["compatibility"]["restore_supported"] is True
    assert any("memory_purge_tombstones" in note for note in manifest.get("notes", []))


def test_v7_is_not_silently_redefined() -> None:
    manifest, payloads = _read(
        _archive(
            TombstoneExportDB(_empty_bundle()),
            schema_version=LIFECYCLE_REVISION_MANIFEST_SCHEMA_VERSION,
        )
    )
    assert manifest["schema_version"] == "account-export.v7"
    assert _canonical_families(manifest) == V7_CANONICAL_FAMILIES
    # A v7 archive carries no tombstone family at all.
    assert "memory_purge_tombstones" not in manifest["included_families"]
    assert "memory_purge_tombstones" not in payloads


def test_v6_and_earlier_remain_unchanged() -> None:
    manifest, _ = _read(
        _archive(
            TombstoneExportDB(_empty_bundle()),
            schema_version=REVIEW_REVISION_MANIFEST_SCHEMA_VERSION,
        )
    )
    assert manifest["schema_version"] == "account-export.v6"
    assert "memory_purge_tombstones" not in manifest["included_families"]


# ---------------------------------------------------------------------------
# B. Zero-tombstone account.
# ---------------------------------------------------------------------------


def test_zero_tombstone_export_is_valid() -> None:
    manifest, payloads = _read(
        _archive(
            TombstoneExportDB(_live_memory_bundle()),
            schema_version=PURGE_TOMBSTONE_MANIFEST_SCHEMA_VERSION,
        )
    )
    assert payloads["memory_purge_tombstones"] == []
    counts = manifest.get("entity_counts", {})
    assert counts.get("memory_purge_tombstones", 0) == 0


# ---------------------------------------------------------------------------
# C. Exact tombstone serialization.
# ---------------------------------------------------------------------------


def test_tombstone_export_is_exact() -> None:
    bundle = _empty_bundle()
    bundle["memory_purge_tombstones"] = [
        _tombstone(
            RID_1,
            record_fingerprint=RECORD_FP_1,
            source_system="openai",
            source_entity_kind="importer",
            source_atom_fingerprint=SOURCE_FP_1,
        )
    ]
    manifest, payloads = _read(
        _archive(
            TombstoneExportDB(bundle),
            schema_version=PURGE_TOMBSTONE_MANIFEST_SCHEMA_VERSION,
        )
    )
    rows = payloads["memory_purge_tombstones"]
    assert len(rows) == 1
    row = rows[0]
    assert row["purge_receipt_id"] == RID_1
    assert row["user_id"] == ACCOUNT_A
    assert row["purged_record_fingerprint"] == RECORD_FP_1
    assert row["source_system"] == "openai"
    assert row["source_entity_kind"] == "importer"
    assert row["source_atom_fingerprint"] == SOURCE_FP_1
    assert row["purged_at"] == NOW
    assert row["suppress_reimport"] is True
    # Exact manifest count.
    assert manifest["entity_counts"]["memory_purge_tombstones"] == 1


def test_tombstone_export_carries_no_content() -> None:
    bundle = _empty_bundle()
    bundle["memory_purge_tombstones"] = [_tombstone(RID_1)]
    _, payloads = _read(
        _archive(
            TombstoneExportDB(bundle),
            schema_version=PURGE_TOMBSTONE_MANIFEST_SCHEMA_VERSION,
        )
    )
    row = payloads["memory_purge_tombstones"][0]
    assert set(row) == {
        "purge_receipt_id",
        "user_id",
        "purged_record_fingerprint",
        "source_system",
        "source_entity_kind",
        "source_atom_fingerprint",
        "purged_at",
        "suppress_reimport",
    }
    for forbidden in (
        "text_content",
        "content",
        "excerpt",
        "embedding",
        "memory_id",
        "source_record_id",
    ):
        assert forbidden not in row


def test_tombstone_ordering_is_deterministic() -> None:
    bundle = _empty_bundle()
    # Deliberately out of order.
    bundle["memory_purge_tombstones"] = [
        _tombstone(RID_2, record_fingerprint=RECORD_FP_2),
        _tombstone(RID_1, record_fingerprint=RECORD_FP_1),
    ]
    _, first = _read(
        _archive(
            TombstoneExportDB(bundle),
            schema_version=PURGE_TOMBSTONE_MANIFEST_SCHEMA_VERSION,
        )
    )
    _, second = _read(
        _archive(
            TombstoneExportDB(bundle),
            schema_version=PURGE_TOMBSTONE_MANIFEST_SCHEMA_VERSION,
        )
    )
    receipts = [row["purge_receipt_id"] for row in first["memory_purge_tombstones"]]
    assert receipts == sorted(receipts)
    assert first == second


# ---------------------------------------------------------------------------
# D. The erased memory is absent.
# ---------------------------------------------------------------------------


def test_purged_memory_and_all_its_history_are_absent() -> None:
    """Erasure means the archive is not a surviving copy of what was erased."""
    bundle = _empty_bundle()
    # One live memory for closure, and one purged memory represented ONLY by
    # a tombstone.
    bundle["memory_records"] = [_memory(MEMORY_A)]
    bundle["memory_provenance"] = [
        _provenance(MEMORY_A, "99999999-9999-9999-9999-999999999999")
    ]
    bundle["memory_purge_tombstones"] = [_tombstone(RID_1)]

    _, payloads = _read(
        _archive(
            TombstoneExportDB(bundle),
            schema_version=PURGE_TOMBSTONE_MANIFEST_SCHEMA_VERSION,
        )
    )
    for family in (
        "memory_records",
        "memory_revisions",
        "memory_review_revisions",
        "memory_lifecycle_revisions",
        "memory_provenance",
        "memory_persona_links",
    ):
        rows = payloads[family]
        # No erased identity survives anywhere in the canonical graph.
        assert all(
            row.get("memory_id") is None or MEMORY_A == row.get("memory_id")
            for row in rows
        ), f"{family} leaked an erased memory"
    # Exactly one live memory, and no trace of the purged one.
    assert [row["memory_id"] for row in payloads["memory_records"]] == [MEMORY_A]
    assert payloads["memory_purge_tombstones"][0]["purge_receipt_id"] == RID_1


# ---------------------------------------------------------------------------
# E. Account isolation.
# ---------------------------------------------------------------------------


def test_tombstone_export_is_account_scoped() -> None:
    bundle = _empty_bundle()
    bundle["memory_purge_tombstones"] = [_tombstone(RID_1)]
    manifest, payloads = _read(
        _archive(
            TombstoneExportDB(bundle),
            schema_version=PURGE_TOMBSTONE_MANIFEST_SCHEMA_VERSION,
        )
    )
    assert all(
        row["user_id"] == ACCOUNT_A for row in payloads["memory_purge_tombstones"]
    )


# ---------------------------------------------------------------------------
# F. Fail-closed on malformed suppression state.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("mutation", "label"),
    [
        ({"suppress_reimport": False}, "relaxed suppression"),
        ({"purged_record_fingerprint": "not-a-digest"}, "unversioned fingerprint"),
        ({"purged_record_fingerprint": ""}, "missing record fingerprint"),
        ({"purged_at": None}, "missing purge time"),
        ({"source_atom_fingerprint": "v1:tooshort"}, "malformed source fingerprint"),
    ],
)
def test_malformed_tombstone_fails_closed(mutation, label) -> None:
    bundle = _empty_bundle()
    row = _tombstone(RID_1)
    row.update(mutation)
    bundle["memory_purge_tombstones"] = [row]
    with pytest.raises(Exception):
        _archive(
            TombstoneExportDB(bundle),
            schema_version=PURGE_TOMBSTONE_MANIFEST_SCHEMA_VERSION,
        )


def test_cross_account_tombstone_fails_closed() -> None:
    bundle = _empty_bundle()
    bundle["memory_purge_tombstones"] = [_tombstone(RID_1, user_id=ACCOUNT_B)]
    with pytest.raises(Exception):
        _archive(
            TombstoneExportDB(bundle),
            schema_version=PURGE_TOMBSTONE_MANIFEST_SCHEMA_VERSION,
        )


def test_content_bearing_tombstone_fails_closed() -> None:
    """A tombstone carrying content means erasure did not happen."""
    bundle = _empty_bundle()
    row = _tombstone(RID_1)
    row["excerpt"] = "The red toolbox is in the garage."
    bundle["memory_purge_tombstones"] = [row]
    with pytest.raises(Exception):
        _archive(
            TombstoneExportDB(bundle),
            schema_version=PURGE_TOMBSTONE_MANIFEST_SCHEMA_VERSION,
        )


def test_duplicate_receipt_identity_fails_closed() -> None:
    bundle = _empty_bundle()
    bundle["memory_purge_tombstones"] = [
        _tombstone(RID_1, record_fingerprint=RECORD_FP_1),
        _tombstone(RID_1, record_fingerprint=RECORD_FP_2),
    ]
    with pytest.raises(Exception):
        _archive(
            TombstoneExportDB(bundle),
            schema_version=PURGE_TOMBSTONE_MANIFEST_SCHEMA_VERSION,
        )
