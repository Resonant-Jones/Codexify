"""Canonical Beta release-boundary proof surface for ADR-069.

This test file proves the canonical Beta support boundary contract established
by ADR-069 without requiring any runtime behavior change. It uses the existing
Product Architecture Assertion JSON Schema, the existing ontology concept
vocabulary, ADR-069, the default supported profile, and the canonical
`00-current-state.md` text as their respective binding surfaces.

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
# 14-16. Release-boundary doctrine and current-state operational truth
# ---------------------------------------------------------------------------


def _section_between(text: str, start: str, end: str) -> str:
    pattern = re.compile(
        rf"^{re.escape(start)}\s*$\n(?P<body>[\s\S]+?)^{re.escape(end)}\s*$",
        re.MULTILINE,
    )
    match = pattern.search(text)
    assert match is not None, f"Missing canonical section between {start!r} and {end!r}"
    return match.group("body")


def _heading_pattern(heading: str) -> str:
    """Regex source for a Markdown heading that tolerates apostrophe variants.

    The canonical current-state document writes ``## This week's priorities``
    with a typographic apostrophe (U+2019). A typographic apostrophe and an
    ASCII apostrophe are the same semantic character in prose, so both name the
    same heading. Every other character is matched literally, which keeps the
    match anchored to this exact heading rather than to an arbitrary one.
    """
    parts = heading.replace("\u2019", "'").split("'")
    return r"['\u2019]".join(re.escape(part) for part in parts)


def _section_until(text: str, start: str, end_pattern: str) -> str:
    """Extract the body of the section that starts at ``start`` and ends at a
    heading matching ``end_pattern``.

    ``start`` is still matched literally; only the closing heading is allowed to
    carry a tolerant pattern. A missing start heading still fails the caller,
    so a removed or renamed section can never be read as an empty one.
    """
    pattern = re.compile(
        rf"^{re.escape(start)}\s*$\n(?P<body>[\s\S]+?){end_pattern}\s*$",
        re.MULTILINE,
    )
    match = pattern.search(text)
    assert match is not None, (
        f"Missing canonical section starting at {start!r} "
        f"and ending at {end_pattern!r}"
    )
    return match.group("body")


# ---------------------------------------------------------------------------
# 14b. Bounded release-proof helpers
# ---------------------------------------------------------------------------
#
# The release contract is expressed as bounded subject, predicate and status
# checks rather than as one fixed piece of prose, and rather than as a general
# natural-language parser. Anything ambiguous or contradictory fails closed.

# Ordinary Markdown list markers: "-", "*", "+", "1." and "1)".
_LIST_MARKER = re.compile(r"^(?:[-*+]|\d+[.)])\s+")

# The HOLD declaration must name the release gate or release posture. A gate
# of another kind (a model gate, say) does not prove the release gate.
_RELEASE_GATE_SUBJECT = re.compile(
    r"\brelease\s+gate\b|\brelease\s+posture\b",
    re.IGNORECASE,
)

# An affirmative declaration that a gate is on HOLD.
_ACTIVE_HOLD_DECLARATION = re.compile(
    r"\b(?:remains?|is|stays?|holds?|still)\b\s*`?HOLD`?(?![A-Za-z])",
    re.IGNORECASE,
)

# A release gate that is not on HOLD.
_RELEASE_GATE_NEGATIVE = re.compile(
    r"\b(?:not|never|no\s+longer|isn't|is\s+no\s+longer)\b[^\n.;]{0,30}?\bhold\b"
    r"|\bhold\b[^\n.;]{0,30}?\b(?:lifted|cleared|removed|dropped|waived|"
    r"rescinded|retired)\b"
    r"|\b(?:is|are)\s+(?:open|lifted|ready|released)\b"
    r"|\bno\s+longer\s+on\s+hold\b",
    re.IGNORECASE,
)

# A readiness claim. The negation must sit immediately before the phrase, so
# an unrelated negation earlier in the sentence cannot hide a promotion.
_RELEASE_READY_PHRASE = re.compile(
    r"\b(?:ready\s+to\s+ship|ready\s+for\s+release|release[-\s]ready|"
    r"generally\s+available)\b",
    re.IGNORECASE,
)
_RELEASE_READY_NEGATION = re.compile(
    r"(?:\bnot|\bnever|\bno\s+longer)\s+(?:yet\s+)?$",
    re.IGNORECASE,
)

# The canonical supported installation path.
_SUPPORTED_PROFILE_NAME = "v1-local-core-web-mcp"
_COMPOSE_INSTALL_PATH = "local Docker Compose"
_SUPPORTED_CLAIM = re.compile(
    r"\bsupported\s+install(?:ation)?\s+path\b"
    r"|\b(?:is|are|remains?)\s+(?:the\s+)?(?:named\s+)?supported\b"
    r"|\bsupports?\b",
    re.IGNORECASE,
)
_UNSUPPORTED_CLAIM = re.compile(
    r"\b(?:do\s+not|does\s+not|doesn't|don't|never)\s+support\b"
    r"|\bunsupported\b|\bnot\s+supported\b|\bno\s+longer\s+supported\b"
    r"|\bdeprecated\b",
    re.IGNORECASE,
)

# Ordinary, affirmative wording for an obligation that is still outstanding.
_UNRESOLVED_AFFIRMATIVE = re.compile(
    r"\b(?:missing|pending|outstanding|unresolved|incomplete)\b"
    r"|\b(?:is|are|remains?|stays?)\s+open\b",
    re.IGNORECASE,
)
# A negated completion ("has not been completed") states the opposite.
_NOT_COMPLETION = re.compile(
    r"\bnot\s+(?:yet\s+)?(?:been\s+)?"
    r"(?:complete|completed|done|proven|qualified|resolved)\b",
    re.IGNORECASE,
)
_COMPLETION_CLAIM = re.compile(
    r"\b(?:complete|completed|done|finished|proven|qualified|resolved|"
    r"closed|cleared)\b",
    re.IGNORECASE,
)
# A negation immediately before the matched word scopes that word.
_NEGATION_BEFORE = re.compile(
    r"(?:\bnot|\bnever|\bno\s+longer|\bisn't|\bcan't|\bcannot)\s+(?:yet\s+)?$",
    re.IGNORECASE,
)


def _claim_clauses(text: str) -> list[str]:
    """Split a passage into the statements that can stand on their own.

    Sentence ends and semicolons separate independent statements; commas are
    intra-statement detail and do not scope a claim's status.
    """
    parts = re.split(r";|(?<=[.!?])\s+|\n", text)
    return [part.strip() for part in parts if part.strip()]


def _has_unresolved_state(claim: str) -> bool:
    """True when the claim states its obligation is still outstanding.

    An affirmative marker must not be negated: "is not pending" states the
    opposite of outstanding. A negated completion ("has not been completed")
    is itself an outstanding state.
    """
    if _NOT_COMPLETION.search(claim):
        return True
    for match in _UNRESOLVED_AFFIRMATIVE.finditer(claim):
        if not _NEGATION_BEFORE.search(claim[: match.start()]):
            return True
    return False


def _has_completion_claim(claim: str) -> bool:
    """True when the claim asserts its obligation is finished."""
    negated = [match.span() for match in _NOT_COMPLETION.finditer(claim)]
    for match in _COMPLETION_CLAIM.finditer(claim):
        if any(start <= match.start() < end for start, end in negated):
            continue
        if _NEGATION_BEFORE.search(claim[: match.start()]):
            continue
        return True
    return False


def _release_gate_is_on_hold(section: str) -> bool:
    """True when the release gate itself is affirmatively declared on HOLD."""
    for clause in _claim_clauses(section):
        if not _RELEASE_GATE_SUBJECT.search(clause):
            continue
        if _ACTIVE_HOLD_DECLARATION.search(clause):
            return True
    return False


def _release_gate_contradicts_hold(section: str) -> bool:
    """True when a release-gate clause denies or lifts the HOLD gate.

    A contradictory clause fails the contract even when another clause
    declares HOLD.
    """
    for clause in _claim_clauses(section):
        if not _RELEASE_GATE_SUBJECT.search(clause):
            continue
        if _RELEASE_GATE_NEGATIVE.search(clause):
            return True
    return False


def _promotes_release_readiness(text: str) -> bool:
    """True when the text claims the release is ready.

    The negation must sit immediately before the readiness phrase, so an
    unrelated negation earlier in the sentence cannot hide a promotion.
    """
    for match in _RELEASE_READY_PHRASE.finditer(text):
        if _RELEASE_READY_NEGATION.search(text[: match.start()]):
            continue
        return True
    return False


def _supported_compose_profile_declared(section: str) -> bool:
    """True when the section positively declares the canonical Compose profile.

    The declaration must associate the local Docker Compose install path with
    the canonical profile. A clause declaring *that* profile unsupported or
    deprecated fails the contract; an unrelated legacy profile being
    unsupported does not.
    """
    clauses = _claim_clauses(section)
    for clause in clauses:
        if (
            _SUPPORTED_PROFILE_NAME in clause
            and _UNSUPPORTED_CLAIM.search(clause)
        ):
            return False
    for clause in clauses:
        if (
            _SUPPORTED_PROFILE_NAME in clause
            and _COMPOSE_INSTALL_PATH in clause
            and _SUPPORTED_CLAIM.search(clause)
        ):
            return True
    return False


def _require_unresolved_obligation(
    section: str, topic: re.Pattern[str], message: str
) -> None:
    """Require every matching obligation claim to state it is outstanding.

    All matching claims are inspected: an earlier unresolved claim cannot
    excuse a later contradictory one.
    """
    matching = [
        clause for clause in _claim_clauses(section) if topic.search(clause)
    ]
    assert matching, message
    for clause in matching:
        assert not _has_completion_claim(clause), message
        assert _has_unresolved_state(clause), message


def test_adr_069_contains_the_five_release_classes():
    text = _read(ADR_069_PATH)
    release_classes = _section_between(
        text,
        "## Release Classes",
        "## Evidence vs Support Doctrine",
    )
    for heading in RELEASE_CLASS_HEADINGS:
        assert f"**{heading}**" in release_classes, (
            f"ADR-069 must define the release class: {heading!r}"
        )


def test_adr_069_places_tts_voice_outside_beta():
    text = _read(ADR_069_PATH)
    out_of_beta = _section_between(
        text,
        "### Out of Beta",
        "## Promotion and Demotion Rules",
    )
    assert re.search(r"^\s*- TTS\s*/\s*voice execution\s*$", out_of_beta, re.MULTILINE), (
        "ADR-069 must explicitly place TTS / voice execution Out of Beta"
    )


def test_adr_069_places_federation_outside_beta():
    text = _read(ADR_069_PATH)
    out_of_beta = _section_between(
        text,
        "### Out of Beta",
        "## Promotion and Demotion Rules",
    )
    assert re.search(r"^\s*- federation\s*$", out_of_beta, re.MULTILINE), (
        "ADR-069 must explicitly place federation Out of Beta"
    )


def test_adr_069_names_coding_loop_and_hosted_rooms_qualification_pending():
    text = _read(ADR_069_PATH)
    section = _section_between(
        text,
        "## Qualification-Pending Doctrine",
        "### Out of Beta",
    )
    for surface in ("Coding Loop", "Hosted Rooms"):
        pattern = re.compile(
            rf"^\s*- \*\*{re.escape(surface)}\*\*\s+—\s+open gate:",
            re.MULTILINE,
        )
        assert pattern.search(section), (
            f"ADR-069 must keep {surface!r} Qualification Pending with a named open gate"
        )


def _assert_current_state_release_contract(text: str) -> None:
    """Assert the canonical release-truth contract against ``text``.

    ``docs/architecture/00-current-state.md`` is the authority. Every check is
    bounded to the section that owns the claim, so a phrase elsewhere in the
    document cannot satisfy a blocker requirement, and each requirement is
    stated semantically rather than as one fixed piece of prose.
    """
    current_phase = _section_between(
        text,
        "## Current phase",
        "## What changed recently",
    )
    supported_reality = _section_between(
        text,
        "## Current supported reality",
        "## Not yet true / do not assume",
    )
    active_blockers = _section_until(
        text,
        "## Active blockers",
        _heading_pattern("## This week's priorities"),
    )

    assert "local-first Beta hardening" in current_phase, (
        "Current phase must still describe local-first Beta hardening"
    )
    assert re.search(r"\bHOLD\b", current_phase), (
        "Current phase must still record the HOLD release gate"
    )
    assert _release_gate_is_on_hold(current_phase), (
        "Current phase must still record the HOLD release gate as an active "
        "declaration about the release gate or release posture"
    )
    assert not _release_gate_contradicts_hold(current_phase), (
        "Current phase must not negate, lift or open the HOLD release gate"
    )
    assert not _promotes_release_readiness(current_phase), (
        "Current phase must not promote the release gate to readiness"
    )
    assert "local Docker Compose" in supported_reality, (
        "Supported reality must still name the local Docker Compose install path"
    )
    assert "`v1-local-core-web-mcp`" in supported_reality, (
        "Supported reality must still name the supported Compose profile"
    )
    assert _supported_compose_profile_declared(supported_reality), (
        "Supported reality must positively declare the local Docker Compose "
        "install path for profile v1-local-core-web-mcp"
    )

    # A fresh current-tip supported-Compose qualification is still missing.
    # Every matching claim is inspected, so a later contradictory statement
    # cannot be excused by an earlier unresolved one.
    _require_unresolved_obligation(
        active_blockers,
        re.compile(r"supported-Compose\s+qualification", re.IGNORECASE),
        "Active blockers must state that a fresh current-tip supported-Compose "
        "qualification is still missing",
    )

    # The natural import-to-recall scope proof is still an open blocker.
    _require_unresolved_obligation(
        active_blockers,
        re.compile(r"import-to-recall", re.IGNORECASE),
        "Active blockers must still identify the open natural import-to-recall "
        "proof",
    )


def test_current_state_preserves_supported_path_hold_and_active_blockers():
    _assert_current_state_release_contract(_read(CURRENT_STATE_PATH))


def _without_lines_containing(text: str, needle: str) -> str:
    """Controlled substitution: drop every line that mentions ``needle``."""
    return "\n".join(line for line in text.splitlines() if needle not in line)


def test_release_contract_rejects_a_missing_active_blockers_section():
    """A missing Active blockers heading must still fail the contract."""
    text = _read(CURRENT_STATE_PATH)
    without_heading = text.replace("## Active blockers\n", "")
    assert without_heading != text, "controlled substitution must apply"

    with pytest.raises(AssertionError) as excinfo:
        _assert_current_state_release_contract(without_heading)
    assert "Missing canonical section" in str(excinfo.value)


def test_release_contract_rejects_a_missing_supported_compose_blocker():
    """A removed fresh-qualification blocker must still fail the contract."""
    text = _read(CURRENT_STATE_PATH)
    without_blocker = _without_lines_containing(
        text, "fresh current-tip supported-Compose qualification"
    )
    assert without_blocker != text, "controlled substitution must apply"

    with pytest.raises(AssertionError) as excinfo:
        _assert_current_state_release_contract(without_blocker)
    assert "fresh current-tip supported-Compose" in str(excinfo.value)


def test_release_contract_rejects_a_missing_import_to_recall_blocker():
    """A removed import-to-recall blocker must still fail the contract."""
    text = _read(CURRENT_STATE_PATH)
    without_blocker = _without_lines_containing(text, "natural import-to-recall")
    assert without_blocker != text, "controlled substitution must apply"

    with pytest.raises(AssertionError) as excinfo:
        _assert_current_state_release_contract(without_blocker)
    assert "natural import-to-recall" in str(excinfo.value)


def test_release_contract_rejects_a_missing_hold_release_posture():
    """A removed HOLD release posture must still fail the contract."""
    text = _read(CURRENT_STATE_PATH)
    without_hold = text.replace("`HOLD`", "released")
    assert without_hold != text, "controlled substitution must apply"

    with pytest.raises(AssertionError) as excinfo:
        _assert_current_state_release_contract(without_hold)
    assert "HOLD release gate" in str(excinfo.value)


# ---------------------------------------------------------------------------
# 16b. Release-proof invariants: bounded positive and negative proofs
# ---------------------------------------------------------------------------

_HOLD_CLAUSE = "the release gate remains `HOLD`."
_SUPPORTED_PROFILE_BULLET = (
    "- The named supported install path is local Docker Compose profile "
    "`v1-local-core-web-mcp` with `LLM_PROVIDER=local`, "
    "`CODEXIFY_LOCAL_ONLY_MODE=true`, and `ALLOW_CLOUD_PROVIDERS=false`."
)
_COMPOSE_BLOCKER_BULLET = (
    "- A fresh current-tip supported-Compose qualification is missing, "
    "including model rejection, browser/event/provenance coherence, restart "
    "recovery, and ordinary chat after restart."
)
_IMPORT_BLOCKER_BULLET = (
    "- The new-thread authored-message projection gap and natural "
    "import-to-recall scope proof remain open."
)


def _substitute(text: str, old: str, new: str) -> str:
    """Controlled substitution that must actually apply."""
    assert old in text, f"controlled substitution must apply: {old!r}"
    return text.replace(old, new)


def test_release_contract_rejects_a_readiness_promotion_hidden_by_negation():
    """An unrelated negation must not hide an affirmative readiness claim."""
    text = _read(CURRENT_STATE_PATH)
    promoted = _substitute(
        text,
        _HOLD_CLAUSE,
        "The release gate remains `HOLD`. The release is not blocked and ready "
        "to ship.",
    )
    with pytest.raises(AssertionError):
        _assert_current_state_release_contract(promoted)


def test_release_contract_accepts_a_negated_readiness_statement():
    """'Not release-ready' is truthful and must not be read as a promotion."""
    text = _read(CURRENT_STATE_PATH)
    truthful = _substitute(
        text,
        _HOLD_CLAUSE,
        "Not release-ready; the release gate remains `HOLD`.",
    )
    _assert_current_state_release_contract(truthful)


def test_release_contract_rejects_an_unrelated_gate_on_hold():
    """A model gate on HOLD does not prove the release gate is on HOLD."""
    text = _read(CURRENT_STATE_PATH)
    unrelated = _substitute(
        text,
        _HOLD_CLAUSE,
        "The model gate remains `HOLD`.",
    )
    with pytest.raises(AssertionError):
        _assert_current_state_release_contract(unrelated)


def test_release_contract_rejects_a_contradictory_release_gate_claim():
    """A contradictory release-gate clause fails even beside a valid HOLD."""
    text = _read(CURRENT_STATE_PATH)
    contradictory = _substitute(
        text,
        _HOLD_CLAUSE,
        "The release gate remains `HOLD`; the release gate is OPEN.",
    )
    with pytest.raises(AssertionError):
        _assert_current_state_release_contract(contradictory)


def test_release_contract_rejects_an_unsupported_canonical_compose_profile():
    """A profile declared unsupported cannot satisfy the supported-path rule."""
    text = _read(CURRENT_STATE_PATH)
    unsupported = _substitute(
        text,
        _SUPPORTED_PROFILE_BULLET,
        "- Do not support local Docker Compose profile "
        "`v1-local-core-web-mcp`.",
    )
    with pytest.raises(AssertionError):
        _assert_current_state_release_contract(unsupported)


def test_release_contract_rejects_a_deprecated_canonical_compose_profile():
    text = _read(CURRENT_STATE_PATH)
    deprecated = _substitute(
        text,
        _SUPPORTED_PROFILE_BULLET,
        "- The `v1-local-core-web-mcp` profile is unsupported.",
    )
    with pytest.raises(AssertionError):
        _assert_current_state_release_contract(deprecated)


def test_release_contract_allows_an_unsupported_legacy_profile():
    """An unrelated legacy profile being unsupported must not invalidate v1."""
    text = _read(CURRENT_STATE_PATH)
    legacy = _substitute(
        text,
        _SUPPORTED_PROFILE_BULLET,
        _SUPPORTED_PROFILE_BULLET
        + "\n- The legacy v0-local-core-web profile is unsupported.",
    )
    _assert_current_state_release_contract(legacy)


def test_release_contract_rejects_a_later_completed_obligation():
    """A later completed claim cannot be excused by an earlier pending one."""
    text = _read(CURRENT_STATE_PATH)
    contradictory = _substitute(
        text,
        _COMPOSE_BLOCKER_BULLET,
        _COMPOSE_BLOCKER_BULLET
        + "\n- Supported-Compose qualification is complete.",
    )
    with pytest.raises(AssertionError):
        _assert_current_state_release_contract(contradictory)


def test_release_contract_rejects_a_negated_unresolved_state():
    """'is not pending' states the opposite of outstanding.

    The reconciled contract accepts ordinary unresolved wording, so a negated
    marker must be rejected explicitly rather than by the absence of the word
    "missing".
    """
    text = _read(CURRENT_STATE_PATH)
    negated = _substitute(
        text,
        _COMPOSE_BLOCKER_BULLET,
        "- A fresh current-tip supported-Compose qualification is not pending.",
    )
    with pytest.raises(AssertionError):
        _assert_current_state_release_contract(negated)


@pytest.mark.parametrize("marker", ["-", "*", "+", "1.", "1)"])
def test_release_contract_recognises_standard_blocker_list_markers(marker: str):
    """Active blockers may use any standard Markdown list marker."""
    text = _read(CURRENT_STATE_PATH)
    restyled = _substitute(
        text,
        _COMPOSE_BLOCKER_BULLET,
        f"{marker} A fresh current-tip supported-Compose qualification is "
        f"missing, including model rejection and restart recovery.",
    )
    restyled = _substitute(
        restyled,
        _IMPORT_BLOCKER_BULLET,
        f"{marker} The new-thread authored-message projection gap and natural "
        f"import-to-recall scope proof remain open.",
    )
    _assert_current_state_release_contract(restyled)


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
