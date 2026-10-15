"""Focused account-export.v5 proof for ordinary-memory content revisions.

UMS-05C9. Proves that the six-family canonical Unified Memory graph
serializes ``memory_revisions`` with exact text fidelity, deterministic
ordering, exact manifest counts, and account isolation — and that
``account-export.v4`` is NOT silently redefined into v5.

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
    REVISION_MANIFEST_SCHEMA_VERSION,
    STAGED_MANIFEST_SCHEMA_VERSION,
    STAGED_PAYLOAD_FAMILIES,
    build_account_export_zip,
)

ACCOUNT_A = "account-a"
ACCOUNT_B = "account-b"
PROJECT_A = 101
NOW = "2026-09-27T12:00:00+00:00"
LATER = "2026-09-27T13:00:00+00:00"

MEMORY_A = "33333333-3333-3333-3333-333333333333"
MEMORY_B = "55555555-5555-5555-5555-555555555555"
SUBJECT_A = "11111111-1111-1111-1111-111111111111"
THREAD_A = 1001

#: Exact text fixtures exercising whitespace, newlines, Unicode, punctuation.
EXACT_ORIGINAL = "  Original.\n\tTabbed — em-dash, “quotes”, 日本語.  "
EXACT_CORRECTED = "Corrected!  \r\nNewline, emoji 🎯, and  double  spaces. "
EXACT_FINAL_MID = "Intermediate.  \nWith whitespace. "
EXACT_FINAL = "Final revision.  \nTrailing whitespace kept.   "

REV_1 = "bbbbbbbb-1111-1111-1111-111111111111"
REV_2 = "bbbbbbbb-2222-2222-2222-222222222222"
REV_3 = "bbbbbbbb-3333-3333-3333-333333333333"
REV_B1 = "cccccccc-1111-1111-1111-111111111111"


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
    }


def _memory(memory_id: str, text: str) -> dict[str, Any]:
    return {
        "memory_id": memory_id,
        "user_id": ACCOUNT_A,
        "project_id": None,
        "semantic_species": "episodic_semantic_memory",
        "text_content": text,
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


def _revision(
    revision_id: str,
    memory_id: str,
    number: int,
    old: str,
    new: str,
) -> dict[str, Any]:
    return {
        "revision_id": revision_id,
        "memory_id": memory_id,
        "user_id": ACCOUNT_A,
        "revision_number": number,
        "old_text_content": old,
        "new_text_content": new,
        "created_at": NOW,
    }


def _bundle_with_chain() -> dict[str, list[dict[str, Any]]]:
    bundle = _empty_bundle()
    bundle["memory_records"] = [_memory(MEMORY_A, EXACT_FINAL)]
    bundle["memory_provenance"] = [
        {
            "provenance_id": "99999999-9999-9999-9999-999999999999",
            "memory_id": MEMORY_A,
            "user_id": ACCOUNT_A,
            "source_system": "codexify",
            "source_record_id": "source-memory-1",
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
    ]
    # Deliberately out of order: the exporter must sort deterministically.
    bundle["memory_revisions"] = [
        _revision(REV_3, MEMORY_A, 3, EXACT_FINAL_MID, EXACT_FINAL),
        _revision(REV_1, MEMORY_A, 1, EXACT_ORIGINAL, EXACT_CORRECTED),
        _revision(REV_2, MEMORY_A, 2, EXACT_CORRECTED, EXACT_FINAL_MID),
    ]
    return bundle


class RevisionExportDB:
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


def _archive(
    db: RevisionExportDB,
    tmp_path: Path,
    *,
    schema_version: str,
) -> bytes:
    os_env = {
        "projects": "entities/projects.json",
        "chat_threads": "entities/chat_threads.json",
        "chat_messages": "entities/chat_messages.json",
    }
    _ = os_env
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


# ---------------------------------------------------------------------------
# 1-3: manifest identity, family enumeration, exact count.
# ---------------------------------------------------------------------------


def test_v5_manifest_identifies_schema_and_revision_family(tmp_path: Path) -> None:
    db = RevisionExportDB(_bundle_with_chain())
    manifest, payloads = _read(
        _archive(db, tmp_path, schema_version=REVISION_MANIFEST_SCHEMA_VERSION)
    )

    assert manifest["schema_version"] == "account-export.v5"
    assert "memory_revisions" in manifest["included_families"]
    assert "entities/memory_revisions.json" in manifest["integrity"]["payload_files"]
    # Six canonical families are present.
    canonical = {
        f
        for f in manifest["included_families"]
        if f.startswith(("persona_subject", "memory_"))
    }
    assert canonical == {
        "persona_subjects",
        "persona_subject_bindings",
        "memory_records",
        "memory_persona_links",
        "memory_provenance",
        "memory_revisions",
    }
    assert manifest["entity_counts"]["memory_revisions"] == 3
    assert len(payloads["memory_revisions"]) == 3


# ---------------------------------------------------------------------------
# 4-5: every field serializes; exact text survives.
# ---------------------------------------------------------------------------


def test_v5_serializes_every_revision_field_with_exact_text(
    tmp_path: Path,
) -> None:
    db = RevisionExportDB(_bundle_with_chain())
    _manifest, payloads = _read(
        _archive(db, tmp_path, schema_version=REVISION_MANIFEST_SCHEMA_VERSION)
    )
    rows = payloads["memory_revisions"]
    assert set(rows[0]) == {
        "revision_id",
        "memory_id",
        "user_id",
        "revision_number",
        "old_text_content",
        "new_text_content",
        "created_at",
    }
    by_number = {r["revision_number"]: r for r in rows}
    # Invariant 4: exact text, no trimming or normalization.
    assert by_number[1]["old_text_content"] == EXACT_ORIGINAL
    assert by_number[1]["new_text_content"] == EXACT_CORRECTED
    assert by_number[2]["new_text_content"] == EXACT_FINAL_MID
    assert by_number[3]["new_text_content"] == EXACT_FINAL
    # Invariant 11: the reconstruction chain survives serialization intact.
    assert by_number[1]["new_text_content"] == by_number[2]["old_text_content"]
    assert by_number[2]["new_text_content"] == by_number[3]["old_text_content"]


# ---------------------------------------------------------------------------
# 6: account isolation.
# ---------------------------------------------------------------------------


def test_v5_revisions_are_account_scoped(tmp_path: Path) -> None:
    """A foreign-account revision is never serialized into this account's
    archive. The production row source selects ``WHERE user_id = %s``; the
    fake models that by refusing to hand back another account's row.
    """

    class ScopedExportDB(RevisionExportDB):
        def fetch_account_export_bundle_for_user(
            self,
            user_id: str,
            *,
            include_unified_memory: bool = False,
        ) -> dict[str, list[dict[str, Any]]]:
            self.calls.append((user_id, include_unified_memory))
            scoped = deepcopy(self.bundle)
            for family in (
                "memory_records",
                "memory_provenance",
                "memory_persona_links",
                "memory_revisions",
            ):
                scoped[family] = [
                    row
                    for row in scoped.get(family, [])
                    if row.get("user_id") == user_id
                ]
            return scoped

    bundle = _bundle_with_chain()
    foreign = _revision(REV_B1, MEMORY_A, 4, EXACT_FINAL, "someone else")
    foreign["user_id"] = ACCOUNT_B
    bundle["memory_revisions"].append(foreign)

    db = ScopedExportDB(bundle)
    manifest, payloads = _read(
        _archive(db, tmp_path, schema_version=REVISION_MANIFEST_SCHEMA_VERSION)
    )
    assert manifest["entity_counts"]["memory_revisions"] == 3
    assert {r["user_id"] for r in payloads["memory_revisions"]} == {ACCOUNT_A}
    assert all(r["revision_id"] != REV_B1 for r in payloads["memory_revisions"])


def test_v5_rejects_revision_for_foreign_memory(tmp_path: Path) -> None:
    bundle = _bundle_with_chain()
    orphan = _revision(REV_B1, "99999999-9999-9999-9999-999999999999", 1, "a", "b")
    bundle["memory_revisions"].append(orphan)
    db = RevisionExportDB(bundle)
    with pytest.raises(RuntimeError, match="memory_revision_export_graph_mismatch"):
        _archive(db, tmp_path, schema_version=REVISION_MANIFEST_SCHEMA_VERSION)


# ---------------------------------------------------------------------------
# 7: deterministic ordering.
# ---------------------------------------------------------------------------


def test_v5_revision_ordering_is_deterministic(tmp_path: Path) -> None:
    db = RevisionExportDB(_bundle_with_chain())
    _manifest, payloads = _read(
        _archive(db, tmp_path, schema_version=REVISION_MANIFEST_SCHEMA_VERSION)
    )
    numbers = [r["revision_number"] for r in payloads["memory_revisions"]]
    assert numbers == sorted(numbers)
    assert numbers == [1, 2, 3]


# ---------------------------------------------------------------------------
# 8: a memory with zero revisions stays valid.
# ---------------------------------------------------------------------------


def test_v5_memory_with_zero_revisions_is_valid(tmp_path: Path) -> None:
    bundle = _bundle_with_chain()
    bundle["memory_records"].append(_memory(MEMORY_B, "no revisions here"))
    bundle["memory_provenance"].append(
        {
            "provenance_id": "dddddddd-9999-9999-9999-999999999999",
            "memory_id": MEMORY_B,
            "user_id": ACCOUNT_A,
            "source_system": "codexify",
            "source_record_id": "m2",
            "source_thread_id": None,
            "source_message_id": None,
            "source_import_job_id": None,
            "source_export_fingerprint": None,
            "source_subject_kind": "vault",
            "source_subject_id": None,
            "is_imported": False,
            "extensions": None,
            "created_at": NOW,
        }
    )
    db = RevisionExportDB(bundle)
    manifest, payloads = _read(
        _archive(db, tmp_path, schema_version=REVISION_MANIFEST_SCHEMA_VERSION)
    )
    assert manifest["entity_counts"]["memory_revisions"] == 3
    assert all(r["memory_id"] == MEMORY_A for r in payloads["memory_revisions"])
    assert any(m["memory_id"] == MEMORY_B for m in payloads["memory_records"])


# ---------------------------------------------------------------------------
# 9: v4 is NOT silently redefined into v5.
# ---------------------------------------------------------------------------


def test_explicit_v4_stays_five_family_and_unsupported(tmp_path: Path) -> None:
    db = RevisionExportDB(_bundle_with_chain())
    manifest, payloads = _read(
        _archive(db, tmp_path, schema_version=STAGED_MANIFEST_SCHEMA_VERSION)
    )

    assert manifest["schema_version"] == "account-export.v4"
    # v4 keeps exactly its five-family canonical graph.
    assert "memory_revisions" not in manifest["included_families"]
    assert (
        "entities/memory_revisions.json" not in manifest["integrity"]["payload_files"]
    )
    assert "memory_revisions" not in manifest["entity_counts"]
    assert "memory_revisions" not in STAGED_PAYLOAD_FAMILIES
    assert list(STAGED_PAYLOAD_FAMILIES)[-1] == "memory_provenance"
    # v4 keeps its historical restore posture unchanged.
    assert manifest["compatibility"]["restore_supported"] is False
    assert manifest["compatibility"]["restore_mode"] == "unsupported"
    assert manifest["compatibility"]["reader"] == "account_export.v4"
    _ = payloads
