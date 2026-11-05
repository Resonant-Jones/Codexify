"""Per-message source-origin classification for the history recall reader.

These tests exercise the pure classification decision in
:mod:`guardian.core.message_origin_classification` against the evidence shapes
that ADR-016 and the documentation-only provenance fixture describe. They are
deliberately free of database fixtures: the classifier reads persisted metadata
and nothing else, so its contract is fully observable without a store.

The reader-side behaviour (exclusion before model exposure, coverage counts,
and source-label assignment) is covered in
``tests/core/test_account_history_recall.py``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from guardian.core.db import RESERVED_MESSAGE_ORIGIN_KEY
from guardian.core.message_origin_classification import (
    LABEL_CONFLICTING,
    LABEL_IMPORTED,
    LABEL_NATIVE,
    LABEL_UNKNOWN,
    classify_message_origin,
)


PROVENANCE_FIXTURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "architecture"
    / "fixtures"
    / "history-message-provenance.v1.json"
)

#: The trusted native assertion shape the canonical writer produces.
NATIVE_ASSERTION = {
    RESERVED_MESSAGE_ORIGIN_KEY: {
        "version": 1,
        "origin_system": "codexify",
        "asserted_at": "2026-11-01T22:00:00+00:00",
    }
}

#: The canonical importer's message metadata shape.
IMPORTED_META = {
    "origin": "chatgpt_import",
    "canonical_filter_profile": "chatgpt_v1_canonical",
    "imported_at": "2026-10-31T12:00:00+00:00",
    "source_thread_id": "export-chat-1",
    "source_message_id": "export-message-1",
    "source_created_at": "2025-05-02T10:00:00+00:00",
    "turn_index": 0,
    "raw_role": "user",
    "raw_message": {"id": "export-message-1", "author": {"role": "user"}},
    "era": "legacy",
}


def _fixture_by_id(fixture_id: str) -> dict:
    payload = json.loads(PROVENANCE_FIXTURE_PATH.read_text(encoding="utf-8"))
    for entry in payload["fixtures"]:
        if entry["id"] == fixture_id:
            return entry
    raise AssertionError(f"provenance fixture {fixture_id!r} is missing")


# ---------------------------------------------------------------------------
# The documented fixture expectations
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("fixture_id", "expected_label"),
    [
        ("P01", LABEL_NATIVE),
        ("P02", LABEL_NATIVE),
        ("P03", LABEL_IMPORTED),
        ("P04", LABEL_IMPORTED),
        ("P05", LABEL_IMPORTED),
        ("P06", LABEL_NATIVE),
        ("P07", LABEL_NATIVE),
        ("P09", LABEL_NATIVE),
        ("N01", LABEL_UNKNOWN),
        ("N02", LABEL_UNKNOWN),
        ("N03", LABEL_CONFLICTING),
        ("N05", LABEL_IMPORTED),
        ("N06", LABEL_UNKNOWN),
        ("N07", LABEL_UNKNOWN),
        ("N08", LABEL_UNKNOWN),
        ("N10", LABEL_UNKNOWN),
        ("N11", LABEL_NATIVE),
        ("N12", LABEL_IMPORTED),
    ],
)
def test_the_documented_fixture_evidence_classifies_as_documented(
    fixture_id: str, expected_label: str
):
    """The classifier agrees with the documented provenance expectations.

    The fixture file is documentation-only, so this test proves the runtime
    decision the fixture describes rather than treating the fixture text as
    runtime proof.
    """

    fixture = _fixture_by_id(fixture_id)
    extra_meta = fixture["persisted_evidence"]["message"]["extra_meta"]

    origin = classify_message_origin(extra_meta)

    assert origin.label == expected_label, fixture["reason"]
    assert fixture["expected_origin_classification"] == expected_label


def test_the_write_side_custody_cases_are_not_read_time_distinguishable():
    """N04/N09 are decided by write-side custody, not by the stored bytes.

    N04 (a client-supplied native-looking claim) and N09 (an unverified
    uploaded archive claiming native origin) persist *byte-identical*
    ``extra_meta`` to P01 and P09. The distinguishing fact in each case is the
    custody of the write, not the shape of the stored JSON: ADR-016's custody
    boundary in ``guardian/core/db.py`` refuses the reserved member from
    untrusted payloads, and the restore path refuses an archive carrying it.

    A read-time classifier therefore cannot separate them from the stored
    bytes alone, and it must not invent a discriminator the contract forbids
    (no timestamp cutoff, no trusted flag). This test records that boundary
    rather than pretending the reader can decide it.
    """

    for unproven, proven in (("N04", "P01"), ("N09", "P09")):
        unproven_meta = _fixture_by_id(unproven)["persisted_evidence"]["message"][
            "extra_meta"
        ]
        proven_meta = _fixture_by_id(proven)["persisted_evidence"]["message"][
            "extra_meta"
        ]
        assert unproven_meta == proven_meta
        # Both therefore read the same way, and the write-side custody boundary
        # is what separates them.
        assert (
            classify_message_origin(unproven_meta).label
            == classify_message_origin(proven_meta).label
        )


def test_the_assistant_witness_supplies_the_native_proof_p08_describes():
    """P08's native verdict comes from the trusted witness, not from metadata."""

    fixture = _fixture_by_id("P08")
    extra_meta = fixture["persisted_evidence"]["message"]["extra_meta"]

    assert classify_message_origin(extra_meta).label == LABEL_UNKNOWN
    assert (
        classify_message_origin(extra_meta, trusted_native_witness=True).label
        == LABEL_NATIVE
    )
    assert fixture["expected_origin_classification"] == LABEL_NATIVE


def test_n07_does_not_transfer_an_assistant_attempt_to_another_message():
    """An attempt bound to message 108 does not prove message 207."""

    fixture = _fixture_by_id("N07")
    extra_meta = fixture["persisted_evidence"]["message"]["extra_meta"]

    origin = classify_message_origin(extra_meta)

    assert origin.label == LABEL_UNKNOWN
    assert fixture["expected_origin_classification"] == LABEL_UNKNOWN


# ---------------------------------------------------------------------------
# Native evidence
# ---------------------------------------------------------------------------


def test_a_trusted_native_assertion_is_native():
    origin = classify_message_origin(dict(NATIVE_ASSERTION))

    assert origin.label == LABEL_NATIVE
    assert origin.is_native is True
    assert origin.origin_system == "codexify"


def test_an_unmarked_legacy_row_is_unknown_and_never_native():
    origin = classify_message_origin({})

    assert origin.label == LABEL_UNKNOWN
    assert origin.is_native is False
    assert origin.origin_system is None


def test_generic_metadata_without_proof_is_unknown():
    origin = classify_message_origin({"attachments": []})

    assert origin.label == LABEL_UNKNOWN


def test_an_unsupported_assertion_version_is_unknown():
    origin = classify_message_origin(
        {
            RESERVED_MESSAGE_ORIGIN_KEY: {
                "version": 99,
                "origin_system": "codexify",
            }
        }
    )

    assert origin.label == LABEL_UNKNOWN


def test_a_non_mapping_assertion_is_unknown():
    origin = classify_message_origin({RESERVED_MESSAGE_ORIGIN_KEY: "codexify"})

    assert origin.label == LABEL_UNKNOWN


def test_a_non_native_origin_system_is_unknown():
    origin = classify_message_origin(
        {
            RESERVED_MESSAGE_ORIGIN_KEY: {
                "version": 1,
                "origin_system": "openai",
                "asserted_at": "2026-11-01T22:00:00+00:00",
            }
        }
    )

    assert origin.label == LABEL_UNKNOWN


def test_a_missing_asserted_at_is_unknown():
    origin = classify_message_origin(
        {RESERVED_MESSAGE_ORIGIN_KEY: {"version": 1, "origin_system": "codexify"}}
    )

    assert origin.label == LABEL_UNKNOWN


def test_a_non_mapping_extra_meta_is_unknown():
    origin = classify_message_origin(None)

    assert origin.label == LABEL_UNKNOWN


# ---------------------------------------------------------------------------
# Imported evidence
# ---------------------------------------------------------------------------


def test_a_canonical_import_record_is_imported():
    origin = classify_message_origin(dict(IMPORTED_META))

    assert origin.label == LABEL_IMPORTED
    assert origin.is_native is False
    assert origin.origin_system is None


def test_a_claude_import_record_is_imported():
    origin = classify_message_origin({"origin": "claude_import"})

    assert origin.label == LABEL_IMPORTED


# ---------------------------------------------------------------------------
# Conflicting evidence
# ---------------------------------------------------------------------------


def test_a_native_assertion_with_import_markers_is_conflicting():
    origin = classify_message_origin(
        {**NATIVE_ASSERTION, **IMPORTED_META}
    )

    assert origin.label == LABEL_CONFLICTING
    assert origin.is_native is False
    assert origin.origin_system is None


def test_a_native_assertion_with_partial_import_lineage_is_conflicting():
    origin = classify_message_origin(
        {**NATIVE_ASSERTION, "source_message_id": "export-message-3"}
    )

    assert origin.label == LABEL_CONFLICTING


# ---------------------------------------------------------------------------
# The exact-message trusted assistant witness
# ---------------------------------------------------------------------------


def test_the_trusted_assistant_witness_proves_an_unmarked_assistant_row():
    origin = classify_message_origin({}, trusted_native_witness=True)

    assert origin.label == LABEL_NATIVE
    assert origin.origin_system == "codexify"


def test_the_trusted_assistant_witness_conflicts_with_import_evidence():
    origin = classify_message_origin(
        dict(IMPORTED_META), trusted_native_witness=True
    )

    assert origin.label == LABEL_CONFLICTING


def test_the_trusted_assistant_witness_does_not_rescue_a_malformed_claim():
    origin = classify_message_origin(
        {RESERVED_MESSAGE_ORIGIN_KEY: {"version": 99}},
        trusted_native_witness=True,
    )

    assert origin.label == LABEL_UNKNOWN


# ---------------------------------------------------------------------------
# Importer metadata is read, never rewritten
# ---------------------------------------------------------------------------


def test_classification_does_not_mutate_the_imported_metadata():
    extra_meta = dict(IMPORTED_META)
    before = json.dumps(extra_meta, sort_keys=True)

    classify_message_origin(extra_meta)

    assert json.dumps(extra_meta, sort_keys=True) == before
