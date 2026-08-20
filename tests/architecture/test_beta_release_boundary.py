"""Canonical Beta release-boundary proof surface for ADR-069.

This test file proves the canonical Beta support boundary contract established
by ADR-069 without requiring any runtime behavior change. It uses the existing
Product Architecture Assertion JSON Schema, the existing ontology concept
vocabulary, the default supported profile, and the canonical
`00-current-state.md` text as its binding surfaces.

It must NOT assert entire Markdown file equals a static string. All
current-state assertions are structural: they look for required phrases in
the live document so the document can continue to evolve while the release
boundary contract holds.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

try:
    import jsonschema
except ImportError:  # pragma: no cover - pytest skip handled below
    pytest.skip("jsonschema not installed", allow_module_level=True)

try:
    import yaml
except ImportError:  # pragma: no cover
    pytest.skip("pyyaml not installed", allow_module_level=True)


REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO_ROOT / "schemas" / "knowledge" / "product-architecture-assertion.schema.json"
ONTOLOGY_PATH = REPO_ROOT / "docs" / "knowledge-graph" / "ontologies" / "product-architecture-ontology.v1.json"
CORPUS_PATH = REPO_ROOT / "docs" / "knowledge-graph" / "assertions" / "codexify-beta-support-posture.v1.json"
CURRENT_STATE_PATH = REPO_ROOT / "docs" / "architecture" / "00-current-state.md"
ADR_069_PATH = REPO_ROOT / "docs" / "architecture" / "adr" / "069-codexify-beta-runtime-support-boundary.md"
SUPPORTED_PROFILE_PATH = REPO_ROOT / "config" / "supported_profiles" / "v1-local-core-web-mcp.yaml"

# Audited pre-change full HEAD SHA recorded against the original 2026-08-14 corpus.
AUDITED_HEAD = "f4fece599e9e081154a7a7a96e1923f7f5c205b5"

# Pre-change full HEAD SHA recorded against the current temporal continuity
# assertion (beta-continuity-v2), the 2026-08-19 Anthropic conversation-import
# Beta-boundary reconciliation. Contains the successful R2 runtime proof.
CURRENT_HEAD = "0f494b398b79f73c077322ef82456027e51d38f1"

FULL_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")

# The one currently active (open-ended) generic continuity assertion. Historical
# records keep their own audited revisions and must never be selected by an
# active posture lookup.
ACTIVE_CONTINUITY_ASSERTION_ID = (
    "codexify:assertion:product-architecture:beta-continuity-v2"
)

# Five human-facing release classes per ADR-069 §5.
RELEASE_CLASS_HEADINGS = [
    "Beta Supported",
    "Beta Bounded / Conditional",
    "Internal",
    "Qualification Pending",
    "Out of Beta",
]

# Subjects required by the task brief.
REQUIRED_SUBJECTS = {
    "codexify:program:digital-cognitive-workspace",
    "codexify:program:node-runtime",
    "codexify:program:threadspace",
    "codexify:capability:identity",
    "codexify:capability:authorization-policy",
    "codexify:capability:context-retrieval-assembly",
    "codexify:capability:continuity",
    "codexify:capability:persistence",
    "codexify:capability:runtime-lifecycle",
    "codexify:capability:events-receipts-observability",
    "codexify:capability:provider-tool-adapter-interfaces",
    "codexify:client:web",
    "codexify:client:desktop",
    "codexify:client:browser-extension",
    "codexify:client:browser-host",
    "codexify:adapter:local-inference",
    "codexify:adapter:whooshd",
    "codexify:adapter:deepseek",
}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _load_json(path: Path) -> Any:
    assert path.exists(), f"Missing file: {path}"
    return json.loads(path.read_text(encoding="utf-8"))


def _load_yaml(path: Path) -> dict[str, Any]:
    assert path.exists(), f"Missing file: {path}"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _read(path: Path) -> str:
    assert path.exists(), f"Missing file: {path}"
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. Corpus exists and parses
# ---------------------------------------------------------------------------


def test_corpus_file_exists():
    assert CORPUS_PATH.exists(), f"Missing canonical Beta posture corpus: {CORPUS_PATH}"


def test_corpus_is_valid_json_array():
    corpus = _load_json(CORPUS_PATH)
    assert isinstance(corpus, list), "Canonical Beta posture corpus must be a JSON array of assertions"
    assert corpus, "Canonical Beta posture corpus must contain at least one record"


# ---------------------------------------------------------------------------
# 2. Every record validates against the existing Product Architecture Assertion schema
# ---------------------------------------------------------------------------


def test_every_record_validates_against_assertion_schema():
    schema = _load_json(SCHEMA_PATH)
    corpus = _load_json(CORPUS_PATH)
    for record in corpus:
        jsonschema.validate(record, schema)


# ---------------------------------------------------------------------------
# 3. Every record is a canonical assertion
# ---------------------------------------------------------------------------


def test_every_record_is_canonical_assertion():
    corpus = _load_json(CORPUS_PATH)
    for record in corpus:
        assert record.get("record_purpose") == "canonical_assertion", (
            f"Record {record.get('assertion_id')} must have record_purpose='canonical_assertion'"
        )


# ---------------------------------------------------------------------------
# 4. Assertion IDs are unique
# ---------------------------------------------------------------------------


def test_assertion_ids_are_unique():
    corpus = _load_json(CORPUS_PATH)
    ids = [record["assertion_id"] for record in corpus]
    assert len(ids) == len(set(ids)), f"Duplicate assertion IDs found: {[i for i in ids if ids.count(i) > 1]}"


# ---------------------------------------------------------------------------
# 5. Every subject_id exists in the accepted Product Architecture Ontology
# ---------------------------------------------------------------------------


def test_every_subject_id_exists_in_ontology():
    ontology = _load_json(ONTOLOGY_PATH)
    known_ids: set[str] = set()
    for bucket in ("programs", "capabilities", "client_surfaces", "adapter_families"):
        for entry in ontology.get(bucket, []):
            known_ids.add(entry["id"])
    corpus = _load_json(CORPUS_PATH)
    for record in corpus:
        subject_id = record["subject_id"]
        assert subject_id in known_ids, (
            f"Record {record['assertion_id']} subject {subject_id} is not in the ontology"
        )


# ---------------------------------------------------------------------------
# 6. Required authority/governing document IDs are structurally valid DLG identities
# ---------------------------------------------------------------------------


_DLG_DOC_PATTERN = re.compile(r"^codexify:doc:[a-z0-9][a-z0-9-]*:[a-z0-9][a-z0-9-]*$")
_GOV_ADR_PATTERN = re.compile(r"^codexify:doc:adr:[a-z0-9][a-z0-9-]*$")


def test_authority_and_governing_ids_are_structurally_valid():
    corpus = _load_json(CORPUS_PATH)
    for record in corpus:
        for doc_id in record.get("authority_document_ids", []):
            assert _DLG_DOC_PATTERN.match(doc_id), (
                f"Record {record['assertion_id']} has invalid authority_document_id {doc_id!r}"
            )
        for doc_id in record.get("evidence_document_ids", []):
            assert _DLG_DOC_PATTERN.match(doc_id), (
                f"Record {record['assertion_id']} has invalid evidence_document_id {doc_id!r}"
            )
        for doc_id in record.get("governing_adr_document_ids", []):
            assert _GOV_ADR_PATTERN.match(doc_id), (
                f"Record {record['assertion_id']} has invalid governing_adr_document_id {doc_id!r}"
            )


# ---------------------------------------------------------------------------
# 7-12. Required posture coverage
# ---------------------------------------------------------------------------


def _is_active(record: dict) -> bool:
    """Open-ended posture assertions are the currently active records.

    A record carrying ``effective_until`` is a closed historical record and is
    never selected as current truth.
    """
    return not bool(record.get("effective_until"))


def _posture_for(corpus: list, subject_id: str) -> dict | None:
    for record in corpus:
        if (
            record.get("assertion_kind") == "posture"
            and record.get("subject_id") == subject_id
            and _is_active(record)
        ):
            return record.get("posture", {})
    return None


def test_required_subjects_have_posture_assertions():
    corpus = _load_json(CORPUS_PATH)
    for subject_id in REQUIRED_SUBJECTS:
        assert _posture_for(corpus, subject_id) is not None, (
            f"No posture assertion recorded for required subject {subject_id}"
        )


def test_digital_cognitive_workspace_is_supported():
    corpus = _load_json(CORPUS_PATH)
    posture = _posture_for(corpus, "codexify:program:digital-cognitive-workspace")
    assert posture is not None
    assert posture.get("support_posture") == "supported", posture


def test_node_runtime_is_supported():
    corpus = _load_json(CORPUS_PATH)
    posture = _posture_for(corpus, "codexify:program:node-runtime")
    assert posture is not None
    assert posture.get("support_posture") == "supported", posture


def test_threadspace_is_not_marked_as_fully_supported():
    corpus = _load_json(CORPUS_PATH)
    posture = _posture_for(corpus, "codexify:program:threadspace")
    assert posture is not None
    # Must NOT carry support_posture='supported' for the program as a whole.
    assert posture.get("support_posture") != "supported", (
        f"ThreadSpace must not be marked supported as a whole; got {posture}"
    )
    assert posture.get("support_posture") in {"internal", "strategic", "experimental", "historical", "unknown"}, (
        f"ThreadSpace posture must be a non-full-support posture; got {posture.get('support_posture')!r}"
    )


def test_deepseek_is_not_marked_supported():
    corpus = _load_json(CORPUS_PATH)
    posture = _posture_for(corpus, "codexify:adapter:deepseek")
    assert posture is not None
    # DeepSeek must NOT be the default Beta-supported adapter.
    assert posture.get("support_posture") != "supported", (
        f"DeepSeek must not be marked supported; got {posture}"
    )


def test_web_client_is_supported():
    corpus = _load_json(CORPUS_PATH)
    posture = _posture_for(corpus, "codexify:client:web")
    assert posture is not None
    assert posture.get("support_posture") == "supported", posture


def test_local_inference_and_whooshd_are_supported():
    corpus = _load_json(CORPUS_PATH)
    for subject_id in ("codexify:adapter:local-inference", "codexify:adapter:whooshd"):
        posture = _posture_for(corpus, subject_id)
        assert posture is not None, f"Missing posture for {subject_id}"
        assert posture.get("support_posture") == "supported", (
            f"{subject_id} must be supported within the local runtime contract; got {posture}"
        )


# ---------------------------------------------------------------------------
# 13. Repository revisions are temporal: every SHA valid, historical records
#     keep their audited revisions, and active lookup never selects v1
# ---------------------------------------------------------------------------


def test_repository_revisions_are_full_shas():
    corpus = _load_json(CORPUS_PATH)
    for record in corpus:
        revision = record["repository_revision"]
        assert FULL_SHA_PATTERN.match(revision), (
            f"Record {record['assertion_id']} has invalid repository_revision "
            f"{revision!r}; every revision must remain a full 40-hex SHA"
        )


def test_historical_records_keep_the_original_audited_revision():
    corpus = _load_json(CORPUS_PATH)
    for record in corpus:
        if record["assertion_id"] == ACTIVE_CONTINUITY_ASSERTION_ID:
            continue
        assert record["repository_revision"] == AUDITED_HEAD, (
            f"Historical record {record['assertion_id']} must keep the original "
            f"audited revision {AUDITED_HEAD}; got {record['repository_revision']}"
        )


def test_every_required_subject_has_exactly_one_active_posture_assertion():
    corpus = _load_json(CORPUS_PATH)
    for subject_id in REQUIRED_SUBJECTS:
        active = [
            record
            for record in corpus
            if record.get("subject_id") == subject_id and _is_active(record)
        ]
        assert len(active) == 1, (
            f"Subject {subject_id} must have exactly one currently active "
            f"posture assertion; got {[r['assertion_id'] for r in active]}"
        )


def test_continuity_v1_is_a_closed_historical_record():
    corpus = _load_json(CORPUS_PATH)
    v1 = next(
        record
        for record in corpus
        if record["assertion_id"]
        == "codexify:assertion:product-architecture:beta-continuity-v1"
    )
    v2 = next(
        record
        for record in corpus
        if record["assertion_id"] == ACTIVE_CONTINUITY_ASSERTION_ID
    )
    # v1 is closed at the same timestamp v2 opens; both remain schema-valid.
    assert v1.get("effective_until") == v2.get("effective_from"), (
        "beta-continuity-v1 effective_until must equal "
        "beta-continuity-v2 effective_from"
    )
    assert not _is_active(v1), "beta-continuity-v1 must be historical after its effective_until"
    assert _is_active(v2), "beta-continuity-v2 must be the active continuity assertion"
    # The historical record is not bulk-rewritten: identity, scope, evidence
    # posture, and original repository revision are preserved.
    assert v1["repository_revision"] == AUDITED_HEAD
    assert v1["evidence_class"] == "documented-contract"
    assert "Bounded import, migration" in v1["assertion_scope"]


def test_active_continuity_lookup_selects_v2_not_v1():
    corpus = _load_json(CORPUS_PATH)
    posture = _posture_for(corpus, "codexify:capability:continuity")
    assert posture is not None, "Active continuity posture lookup must resolve"
    assert posture.get("support_posture") == "supported"
    assert posture.get("integration_state") == "partial"
    # Guard against accidentally selecting the expired v1 record: the active
    # lookup must return exactly v2's posture dimensions.
    v2 = next(
        record
        for record in corpus
        if record["assertion_id"] == ACTIVE_CONTINUITY_ASSERTION_ID
    )
    assert posture == v2["posture"], (
        "Active continuity posture lookup must select beta-continuity-v2, "
        "never the expired beta-continuity-v1 record"
    )


def test_active_continuity_assertion_includes_anthropic_conversation_import_boundary():
    corpus = _load_json(CORPUS_PATH)
    v2 = next(
        record
        for record in corpus
        if record["assertion_id"] == ACTIVE_CONTINUITY_ASSERTION_ID
    )
    scope_and_notes = f"{v2['assertion_scope']} {v2['notes']}".lower()
    # The active continuity assertion names the Anthropic conversation-import
    # boundary explicitly.
    assert "anthropic" in scope_and_notes
    assert "conversation import" in scope_and_notes
    assert "openai" in scope_and_notes, (
        "OpenAI / ChatGPT import must remain named in the active continuity scope"
    )
    # The boundary stays conservative: the Anthropic claim is bounded to the
    # proven conversation-import path and the generic evidence class is not
    # inflated to proven-live-runtime for the whole continuity scope.
    assert "proven conversation-import path" in scope_and_notes
    assert v2["evidence_class"] == "documented-contract"
    assert "proven-live-runtime" in v2["notes"], (
        "continuity-v2 notes must record the Anthropic conversation-import "
        "sub-scope's proven-live-runtime receipt separately"
    )
    assert v2["posture"]["support_posture"] == "supported"
    assert v2["posture"]["integration_state"] == "partial"
    assert v2["repository_revision"] == CURRENT_HEAD


# ---------------------------------------------------------------------------
# 14-16. 00-current-state.md structural assertions
# ---------------------------------------------------------------------------


def test_current_state_contains_the_five_release_classes():
    text = _read(CURRENT_STATE_PATH)
    for heading in RELEASE_CLASS_HEADINGS:
        assert heading in text, (
            f"00-current-state.md must contain the release class heading: {heading!r}"
        )


def test_current_state_places_tts_voice_outside_beta():
    text = _read(CURRENT_STATE_PATH)
    # Must explicitly call TTS / voice Out of Beta (not just absent, not just qualification-pending).
    pattern = re.compile(
        r"TTS\s*/\s*voice[\s\S]{0,200}Out of Beta",
        re.IGNORECASE,
    )
    assert pattern.search(text), (
        "00-current-state.md must explicitly place TTS / voice outside Beta"
    )


def test_current_state_places_federation_outside_beta():
    text = _read(CURRENT_STATE_PATH)
    pattern = re.compile(
        r"federation[\s\S]{0,200}Out of Beta",
        re.IGNORECASE,
    )
    assert pattern.search(text), (
        "00-current-state.md must explicitly place federation outside Beta"
    )


def test_current_state_names_coding_loop_and_hosted_rooms_qualification_pending():
    text = _read(CURRENT_STATE_PATH)
    # Coding Loop and Hosted Rooms must be recorded as qualification-pending,
    # not silently promoted to supported. The current-state document puts them
    # under a "Qualification Pending" section heading and gives each a named
    # remaining gate. We assert both: (a) the surface is listed inside the
    # Qualification Pending section, and (b) it carries a "remaining gate"
    # annotation. We do NOT require the literal phrase "Qualification Pending"
    # to appear within a fixed character window after the surface name.
    section = re.search(
        r"###\s+Qualification Pending[\s\S]+?(?=###\s|\Z)",
        text,
        re.IGNORECASE,
    )
    assert section is not None, (
        "00-current-state.md must contain a 'Qualification Pending' section"
    )
    section_text = section.group(0)
    for surface in ("Coding Loop", "Hosted Rooms"):
        assert surface in section_text, (
            f"00-current-state.md Qualification Pending section must list {surface!r}"
        )
        # Named-remaining-gate annotation requirement.
        assert "remaining gate" in section_text.lower(), (
            "Qualification Pending section must name the remaining gate for each entry"
        )


# ---------------------------------------------------------------------------
# 17. ADR-069 exists and is accepted by Resonant Jones
# ---------------------------------------------------------------------------


def test_adr_069_exists_and_is_accepted():
    assert ADR_069_PATH.exists(), f"Missing ADR-069 file at {ADR_069_PATH}"
    text = _read(ADR_069_PATH)
    assert text.startswith("# ADR-069: Codexify Beta Runtime Support Boundary")
    # ADR must be Accepted (not Proposed) and approved by Resonant Jones.
    assert re.search(r"^## Status\s*$", text, re.MULTILINE), "ADR-069 must declare its Status"
    # Find the Status block and verify it is Accepted.
    status_match = re.search(
        r"^## Status\s*\n+\s*Accepted\s*\.",
        text,
        re.MULTILINE,
    )
    assert status_match is not None, "ADR-069 Status must be 'Accepted.'"
    assert "Resonant Jones" in text, "ADR-069 must name Resonant Jones as human approver"
    assert "ADR-068 was intentionally reserved" in text
    assert "ADR-069 was explicitly allocated" in text


def test_beta_decision_is_not_allocated_to_adr_066_or_adr_068():
    assert not (REPO_ROOT / "docs" / "architecture" / "adr" / "066-codexify-beta-runtime-support-boundary.md").exists()
    assert not (REPO_ROOT / "docs" / "architecture" / "adr" / "068-codexify-beta-runtime-support-boundary.md").exists()


# ---------------------------------------------------------------------------
# 18-21. Default supported profile invariants
# ---------------------------------------------------------------------------


def test_default_supported_profile_remains_local_only():
    manifest = _load_yaml(SUPPORTED_PROFILE_PATH)
    contract = manifest["provider_contract"]
    assert contract["LLM_PROVIDER"] == "local"
    assert contract["ALLOW_CLOUD_PROVIDERS"] is False
    assert contract["CODEXIFY_LOCAL_ONLY_MODE"] is True


def test_default_supported_profile_quarantines_voice_and_federation():
    manifest = _load_yaml(SUPPORTED_PROFILE_PATH)
    quarantined = manifest["route_posture"]["quarantined"]
    assert "voice" in quarantined, "Default supported profile must quarantine voice"
    assert "federation" in quarantined, "Default supported profile must quarantine federation"


def test_default_supported_profile_keeps_command_bus_internal_only():
    manifest = _load_yaml(SUPPORTED_PROFILE_PATH)
    internal_only = manifest["route_posture"]["internal_only"]
    assert "command_bus" in internal_only, (
        "Default supported profile must keep command_bus internal-only"
    )


def test_default_supported_profile_quarantines_tools_and_api_tools():
    manifest = _load_yaml(SUPPORTED_PROFILE_PATH)
    quarantined = manifest["route_posture"]["quarantined"]
    assert "tools" in quarantined, "Default supported profile must quarantine tools"
    assert "api_tools" in quarantined, "Default supported profile must quarantine api_tools"


# ---------------------------------------------------------------------------
# 22. New canon does not require modifying runtime behavior to pass
# ---------------------------------------------------------------------------


def test_canon_does_not_require_runtime_changes_to_pass():
    """The canonical Beta boundary canon is satisfied by docs/assertions/profile
    alone; no runtime code, no schema, no migration, no Compose topology
    changes are required to make this test pass."""
    assert CORPUS_PATH.exists()
    assert ADR_069_PATH.exists()
    assert CURRENT_STATE_PATH.exists()
    assert SUPPORTED_PROFILE_PATH.exists()
