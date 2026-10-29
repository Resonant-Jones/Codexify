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


# The canonical current-state heading is written with a typographic
# apostrophe ("This week’s priorities"). Current-state section extraction
# therefore normalizes apostrophes. ADR section extraction above is left
# untouched so no other parsing requirement is weakened.
_TYPOGRAPHIC_APOSTROPHES = str.maketrans({"’": "'", "‘": "'"})


def _current_state_section(text: str, start: str, end: str) -> str:
    """Extract a canonical current-state section.

    Apostrophes are normalized so a heading written with a typographic
    apostrophe still matches the ASCII form used by the contract.
    """
    return _section_between(text.translate(_TYPOGRAPHIC_APOSTROPHES), start, end)


# The two foundational proof obligations that must remain observable as
# unresolved inside the Active blockers section. They are matched by topic,
# not by an exact historical sentence, so current-state can keep evolving.
_COMPOSE_QUALIFICATION_OBLIGATION = re.compile(
    r"supported-compose\s+qualification",
    re.IGNORECASE,
)
_IMPORT_TO_RECALL_OBLIGATION = re.compile(r"import-to-recall", re.IGNORECASE)

# ── Release-gate contract ───────────────────────────────────────────────────
#
# The canonical current phase states the gate positively: "The current release
# gate remains `HOLD`." The contract therefore requires an *affirmative*,
# *unnegated* release-gate HOLD declaration. A HOLD that is negated or lifted
# is a contradiction, and a positive readiness claim is a promotion.
#
# A negated readiness statement ("not release-ready") is truthful and must not
# be mistaken for a promotion, so readiness is judged per clause and only
# unqualified claims count.

# A HOLD that is negated ("the release gate is not HOLD") or lifted
# ("HOLD has been lifted") no longer declares an active HOLD gate.
_HOLD_NEGATED = re.compile(
    r"\b(?:not|never|no\s+longer|isn't|is\s+no\s+longer)\b[^\n.;]{0,24}?\bHOLD\b"
    r"|\bHOLD\b[^\n.;]{0,24}?\b(?:lifted|cleared|released|removed|dropped|"
    r"waived|rescinded|retired)\b",
    re.IGNORECASE,
)

# An affirmative declaration that a gate is on HOLD.
_ACTIVE_HOLD_DECLARATION = re.compile(
    r"\b(?:remains?|is|stays?|holds?|still)\b\s*`?HOLD`?(?![A-Za-z])",
    re.IGNORECASE,
)

# The declaration must name the *release* gate or release posture. A gate of
# another kind (a model gate, say) does not prove the release gate.
_RELEASE_GATE_SUBJECT = re.compile(
    r"\brelease\s+gate\b|\brelease\s+posture\b",
    re.IGNORECASE,
)

# A release gate that is not on HOLD. Such a clause contradicts the HOLD
# contract even when another clause declares HOLD.
_RELEASE_GATE_NEGATIVE = re.compile(
    r"\b(?:not|never|no\s+longer|isn't|is\s+no\s+longer)\b[^\n.;]{0,30}?\bhold\b"
    r"|\bhold\b[^\n.;]{0,30}?\b(?:lifted|cleared|removed|dropped|waived|"
    r"rescinded|retired)\b"
    r"|\b(?:is|are)\s+(?:open|lifted|ready|released)\b"
    r"|\bno\s+longer\s+on\s+hold\b",
    re.IGNORECASE,
)

# A readiness claim. Only an unqualified claim promotes the release.
_READINESS_WORD = re.compile(
    r"\bready\b|\bgenerally\s+available\b",
    re.IGNORECASE,
)

# A negation anywhere before the matched word scopes that word.
_NEGATION = re.compile(
    r"\b(?:not|never|no\s+longer|isn't|is\s+no\s+longer|cannot|can't|"
    r"nor\s+is)\b",
    re.IGNORECASE,
)

# ── Obligation contract ─────────────────────────────────────────────────────
#
# The two obligations must be recorded as outstanding, and the unresolved
# state must belong to the *obligation's own* clause. A completion claim on
# the obligation rejects it even when the same bullet carries a pending word
# for something else.

# Ordinary, bounded wording for an obligation that is still outstanding.
# These markers are affirmative: a preceding negation ("is not pending") means
# the obligation is NOT outstanding and must not satisfy the contract.
_UNRESOLVED_AFFIRMATIVE = re.compile(
    r"\b(?:missing|pending|outstanding|unresolved|incomplete)\b"
    r"|\b(?:is|are|remains?|stays?)\s+open\b",
    re.IGNORECASE,
)

# A negated completion ("has not been completed") is itself a statement that
# the obligation is still outstanding.
_UNRESOLVED_NEGATED_COMPLETION = re.compile(
    r"\bnot\s+(?:yet\s+)?(?:been\s+)?"
    r"(?:complete|completed|done|proven|qualified|resolved)\b",
    re.IGNORECASE,
)

# Wording that claims an obligation is finished.
_COMPLETION_CLAIM = re.compile(
    r"\b(?:complete|completed|done|finished|proven|qualified|resolved|"
    r"closed|cleared)\b",
    re.IGNORECASE,
)


# The canonical supported installation path: the local Docker Compose profile
# `v1-local-core-web-mcp`. The contract requires a positive declaration that
# associates the two, so a statement declaring the profile unsupported cannot
# satisfy it.
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
    r"|\bunsupported\b|\bnot\s+supported\b|\bno\s+longer\s+supported\b",
    re.IGNORECASE,
)

# A Markdown list marker: "-", "*", "+", "1." or "1)".
_LIST_MARKER = re.compile(r"^(?:[-*+]|\d+[.)])\s+")


def _clauses(text: str) -> list[str]:
    """Split a passage into the statements that can stand on their own.

    Semicolons and sentence ends separate independent statements. Commas are
    intra-statement detail and do not scope an obligation's state, so
    "qualification is missing, including restart recovery" keeps its state.
    """
    parts = re.split(r";|(?<=[.!?])\s+|\n", text)
    return [part.strip() for part in parts if part.strip()]


def _has_affirmative(text: str, pattern: re.Pattern[str]) -> bool:
    """True when ``pattern`` matches somewhere without a preceding negation."""
    for match in pattern.finditer(text):
        if not _NEGATION.search(text[: match.start()]):
            return True
    return False


def _promotes_release_readiness(text: str) -> bool:
    """True when the text claims the release is ready.

    A negated readiness statement ("not release-ready") is truthful and is
    not a promotion, so only unqualified readiness claims count.
    """
    for clause in _clauses(text):
        if _has_affirmative(clause, _READINESS_WORD):
            return True
    return False


def _active_release_gate_is_hold(text: str) -> bool:
    """True when the release gate itself is affirmatively declared on HOLD.

    The clause must name the release gate or release posture: a gate of some
    other kind (a model gate, say) does not prove the release gate.
    """
    for clause in _clauses(text):
        if not _RELEASE_GATE_SUBJECT.search(clause):
            continue
        if _ACTIVE_HOLD_DECLARATION.search(clause):
            return True
    return False


def _contradicts_release_hold(text: str) -> bool:
    """True when a release-gate clause denies or lifts the HOLD gate.

    A contradictory clause fails the contract even when another clause
    declares HOLD.
    """
    for clause in _clauses(text):
        if not _RELEASE_GATE_SUBJECT.search(clause):
            continue
        if _RELEASE_GATE_NEGATIVE.search(clause):
            return True
    return False


def _has_unresolved_state(clause: str) -> bool:
    """True when the clause states the obligation is still outstanding.

    An affirmative marker must not be negated: "is not pending" states the
    opposite of outstanding and must not satisfy the contract. A negated
    completion ("has not been completed") is itself an outstanding state.
    """
    if _UNRESOLVED_NEGATED_COMPLETION.search(clause):
        return True
    for match in _UNRESOLVED_AFFIRMATIVE.finditer(clause):
        if not _NEGATION.search(clause[: match.start()]):
            return True
    return False


def _supported_compose_profile_declared(section: str) -> bool:
    """True when the section positively declares the supported Compose profile.

    The declaration must associate the local Docker Compose install path with
    the ``v1-local-core-web-mcp`` profile and must assert support. A clause
    declaring the profile unsupported fails the contract outright.
    """
    clauses = _clauses(section)
    for clause in clauses:
        if _COMPOSE_INSTALL_PATH in clause and _UNSUPPORTED_CLAIM.search(clause):
            return False
        if (
            _SUPPORTED_PROFILE_NAME in clause
            and _COMPOSE_INSTALL_PATH in clause
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


def _blocker_bullets(section: str) -> list[str]:
    """Return the list items of a section, for any standard Markdown marker.

    The marker is not part of the statement, so it is removed: a statement is
    read as the words the bullet actually asserts.
    """
    bullets = []
    for line in section.splitlines():
        stripped = line.strip()
        marker = _LIST_MARKER.match(stripped)
        if marker:
            bullets.append(stripped[marker.end() :].strip())
    return bullets


# ── Obligation status interpretation ────────────────────────────────────────
#
# An obligation's status is stated in one of two ways. It can be stated
# directly, on the obligation itself: "import-to-recall is complete". Or it
# can be stated by a predicate shared with the obligations coordinated beside
# it: "New-thread authored-message projection, natural import-to-recall, and
# complete scope-isolation proof remain open".
#
# The second form is why a clause-wide word scan is wrong. The word "complete"
# there describes the neighbouring "scope-isolation proof"; it says nothing
# about import-to-recall, and the shared "remain open" is what leaves both
# obligations outstanding. Reading the clause as one undifferentiated string
# therefore reports an unfinished obligation as finished.
#
# The interpretation below stays deliberately small. It reads the statement
# around the matched obligation rather than parsing the sentence:
#
# * a completion word belongs either to the noun phrase it modifies, or to the
#   subject its copula governs, and only one of those is the obligation;
# * a statement that names no subject of its own continues the subject of the
#   statement before it, so an elided or anaphoric completion stays in scope;
# * a predicate shared across coordinated obligations is honoured only when
#   the obligation carries no predicate of its own.

_OBLIGATION_COMPLETED = "completed"
_OBLIGATION_UNRESOLVED = "unresolved"
_OBLIGATION_UNKNOWN = "unknown"

# A boundary that introduces a different subject. Material beyond it belongs
# to that subject, so it can neither complete nor keep open the obligation
# named before it.
_STATUS_SCOPE_SEPARATOR = re.compile(
    r"(,|\band\b|\bor\b|\bbut\b|\byet\b|\bhowever\b|\bwhile\b|\bwhereas\b|"
    r"\balthough\b|\bthough\b)",
    re.IGNORECASE,
)

# The boundary token itself, recognised on its own.
_SEPARATOR_TOKEN = re.compile(
    r"^(?:,|and|or|but|yet|however|while|whereas|although|though)$",
    re.IGNORECASE,
)

# A boundary that joins two subjects into one coordinated list. Only across
# such a boundary may an obligation inherit a predicate that names it
# nowhere of its own. A contrastive boundary ("but", "while") introduces a
# different subject, whose predicate proves nothing about this one.
_COORDINATION_BOUNDARY = re.compile(r"^(?:,|and|or)$", re.IGNORECASE)

# A copula or auxiliary that puts a following completion word in predicate
# position ("is complete", "has been completed").
_COMPLETION_COPULA = re.compile(
    r"\b(?:is|are|was|were|remains?|stays?|became|becomes|got|been)\b",
    re.IGNORECASE,
)

# A plural predicate governs every obligation coordinated in its clause. A
# singular predicate binds to its own subject and proves nothing about a
# neighbouring obligation.
_SHARED_PREDICATE = re.compile(
    r"\b(?:remain|stay|are|were)\b",
    re.IGNORECASE,
)

# Words that cannot begin a noun phrase. A statement built only from these
# names no subject of its own, so it continues the subject of the statement
# before it and its predicate belongs to that subject.
_FUNCTION_ONLY_WORD = re.compile(
    r"^(?:it|they|them|this|that|these|those|"
    r"is|are|was|were|be|been|being|has|have|had|do|does|did|"
    r"will|would|shall|should|can|could|may|might|must|"
    r"remains?|stays?|became|becomes|gets?|got|"
    r"now|already|still|also|just|only|merely|simply|fully|partly|"
    r"largely|recently|currently|finally|here|there|"
    r"nevertheless|nonetheless|instead|again|furthermore|moreover|"
    r"yesterday|today|tomorrow|tonight|earlier|later|previously|"
    r"not|never|no|yet|"
    r"complete|completed|done|finished|proven|qualified|resolved|"
    r"closed|cleared)$",
    re.IGNORECASE,
)

# The noun phrase a completion word modifies ends at the first word that
# cannot continue it. A word inside a hyphenated compound is part of that
# compound and never ends the phrase, so the boundary must not match there:
# "import-to-recall" is one name, not a phrase ending before "to".
_NOUN_PHRASE_BREAK = re.compile(
    r"(?<![\w-])(?:of|for|with|without|in|on|at|to|from|by|as|into|onto|per|"
    r"and|or|but|while|whereas|although|though|yet|however|"
    r"is|are|was|were|be|been|being|has|have|had|remains?|stays?|"
    r"will|would|can|could|shall|should|may|might|must)(?![\w-])",
    re.IGNORECASE,
)

# A negation immediately before a completion word scopes that word. A
# negation that belongs to another predicate does not.
_NEGATION_IMMEDIATELY_BEFORE = re.compile(
    r"(?:\bnot|\bnever|\bno\s+longer|\bisn't|\bcan't|\bcannot)\s+"
    r"(?:yet\s+|now\s+|just\s+|ever\s+|been\s+|being\s+)*$",
    re.IGNORECASE,
)


def _status_scopes(clause: str) -> list[tuple[str, str]]:
    """Split a clause into the statements whose subjects it coordinates.

    Each entry is the statement and the boundary that introduced it.
    """
    scopes: list[tuple[str, str]] = []
    separator = ""
    for part in _STATUS_SCOPE_SEPARATOR.split(clause):
        text = part.strip()
        if not text:
            continue
        if _SEPARATOR_TOKEN.fullmatch(text):
            separator = text
            continue
        scopes.append((text, separator))
        separator = ""
    return scopes


def _words(text: str) -> list[str]:
    """Return the words of a statement, ignoring punctuation and markers."""
    return re.findall(r"[A-Za-z][A-Za-z'-]*", text)


def _names_a_subject(text: str) -> bool:
    """True when a statement names a subject of its own.

    A statement of pronouns, auxiliaries, adverbs, negations and completion
    words alone names no subject: it continues the subject before it.
    """
    return any(not _FUNCTION_ONLY_WORD.match(word) for word in _words(text))


def _scope_subject(scope: str) -> str:
    """Return the subject of a statement: the text before its predicate."""
    copulas = list(_COMPLETION_COPULA.finditer(scope))
    if copulas:
        return scope[: copulas[0].start()]
    return scope


def _completion_noun_phrase(text: str, match: re.Match[str]) -> str:
    """Return the noun phrase a completion word modifies, if any."""
    after = text[match.end() :]
    boundary = _NOUN_PHRASE_BREAK.search(after)
    if boundary:
        after = after[: boundary.start()]
    return after.strip()


def _completion_object_phrase(
    text: str, match: re.Match[str], topic: re.Pattern[str]
) -> str:
    """Return the phrase a completion word governs, including its complement.

    A completion word can govern a phrase that names the obligation through a
    prepositional complement ("We completed the proof of natural
    import-to-recall"), so the complement belongs to the governed phrase when it
    names the obligation.
    """
    after = text[match.end() :]
    boundary = _NOUN_PHRASE_BREAK.search(after)
    head = after[: boundary.start()] if boundary else after
    if not topic.search(head):
        complement = after[len(head) :]
        if topic.search(complement):
            return (head + complement).strip()
    return head.strip()


def _negates_completion(text: str, position: int) -> bool:
    """True when a negation immediately governs the completion word."""
    return bool(_NEGATION_IMMEDIATELY_BEFORE.search(text[:position]))


def _scope_completes(scope: str, subject: str, topic: re.Pattern[str]) -> bool:
    """True when the statement claims the matched obligation is finished.

    A completion word either modifies the noun phrase that follows it, or is
    governed by a copula. In the first case the claim is about that noun
    phrase; in the second it is about the subject of the copula. Only a claim
    about the matched obligation itself counts, so an adjective on a
    neighbouring proof says nothing about this obligation.
    """
    for match in _COMPLETION_CLAIM.finditer(scope):
        if _negates_completion(scope, match.start()):
            continue
        noun_phrase = _completion_object_phrase(scope, match, topic)
        if noun_phrase and _names_a_subject(noun_phrase):
            if topic.search(noun_phrase):
                return True
            continue
        if topic.search(subject):
            return True
    return False


def _predicative_completion(text: str) -> bool:
    """True when ``text`` claims a completion in predicate position.

    A completion word is predicative when it does not modify a noun phrase and
    a copula or auxiliary governs it ("is complete", "has been completed"). An
    attributive adjective ("complete scope-isolation proof") describes the
    noun phrase it precedes and states no status, so it is not counted here.
    """
    stripped = text.rstrip()
    for match in _COMPLETION_CLAIM.finditer(text):
        if _negates_completion(text, match.start()):
            continue
        noun_phrase = _completion_noun_phrase(text, match)
        if noun_phrase and _names_a_subject(noun_phrase):
            continue
        if _COMPLETION_COPULA.search(text[: match.start()]):
            return True
        if match.end() == len(stripped):
            return True
    return False


def _scope_has_own_predicate(scope: str) -> bool:
    """True when a statement carries a predicate of its own."""
    return bool(
        _COMPLETION_COPULA.search(scope)
        or _UNRESOLVED_AFFIRMATIVE.search(scope)
        or _COMPLETION_CLAIM.search(scope)
    )


def _trailing_status(scope: str) -> str:
    """Return the status the trailing predicate of a statement declares."""
    if _has_unresolved_state(scope):
        return _OBLIGATION_UNRESOLVED
    if _predicative_completion(scope):
        return _OBLIGATION_COMPLETED
    return _OBLIGATION_UNKNOWN


def _shared_predicate_scope(
    index: int, scopes: list[tuple[str, str]]
) -> str | None:
    """Return the scope that carries the predicate shared with this obligation.

    A coordination list may name several obligations before the predicate that
    governs all of them, so the shared predicate is not always in the
    immediately following scope. Only coordination boundaries may be crossed:
    a contrastive boundary introduces a different subject, whose predicate
    proves nothing about this obligation.
    """
    for next_index in range(index + 1, len(scopes)):
        next_scope, next_separator = scopes[next_index]
        if not _COORDINATION_BOUNDARY.fullmatch(next_separator):
            return None
        if _SHARED_PREDICATE.search(next_scope):
            return next_scope
    return None


def _inherits_coordinated_predicate(index: int, scopes: list[tuple[str, str]]) -> bool:
    """True when the statement may take a later statement's predicate.

    The obligation must carry no predicate of its own, and the statements that
    follow it must be joined to it by coordination boundaries only. A
    contrastive boundary introduces a different subject, so that subject's
    pending state cannot be borrowed to satisfy this obligation.
    """
    scope = scopes[index][0]
    if _scope_has_own_predicate(scope):
        return False
    return _shared_predicate_scope(index, scopes) is not None


def _clause_obligation_status(
    clause: str, topic: re.Pattern[str], prior_subject: str = ""
) -> tuple[str, str]:
    """Return the status the clause states for the matched obligation.

    The clause's own statement of the obligation wins. A statement that names
    no subject of its own continues the subject before it, so an elided or
    anaphoric completion stays inside the obligation's scope. When the
    obligation is only named, with its status left to a predicate shared with
    the obligations coordinated beside it, that shared predicate is consulted
    -- but only when the obligation carries no predicate of its own.

    The second value is the subject the statement leaves behind, so that an
    anaphoric continuation in the next sentence of the same bullet can be
    read against it.
    """
    scopes = _status_scopes(clause)
    status = _OBLIGATION_UNKNOWN
    carried = prior_subject
    for index, (scope, _separator) in enumerate(scopes):
        if _names_a_subject(scope):
            subject = _scope_subject(scope)
            carried = subject
        else:
            subject = carried
        if not (topic.search(scope) or topic.search(subject)):
            continue
        if _scope_completes(scope, subject, topic):
            return _OBLIGATION_COMPLETED, carried
        if _has_unresolved_state(scope):
            status = _OBLIGATION_UNRESOLVED
        elif not _scope_has_own_predicate(scope):
            shared = _shared_predicate_scope(index, scopes)
            if shared is not None:
                status = _trailing_status(shared)
    return status, carried


def _require_unresolved_obligation(
    section: str, topic: re.Pattern[str], label: str
) -> None:
    """Require ``topic`` to be recorded as an unresolved blocker.

    The obligation must appear inside the Active blockers section. Its
    unresolved state must belong to the obligation itself: a pending word
    attached to a different statement in the same bullet does not prove the
    gap, and a completion claim about the obligation is rejected outright.

    Every statement that names the obligation is read, so an earlier valid
    declaration cannot hide a later contradictory one. A statement that names
    no subject of its own continues the subject of the statement before it, so
    a contradictory continuation inside the same bullet is read too.
    """
    mentioned = False
    completed = False
    unresolved = False
    for bullet in _blocker_bullets(section):
        carried = ""
        for clause in _clauses(bullet):
            status, carried = _clause_obligation_status(clause, topic, carried)
            if topic.search(clause):
                mentioned = True
            if status == _OBLIGATION_COMPLETED:
                completed = True
            elif status == _OBLIGATION_UNRESOLVED:
                unresolved = True
    assert not completed, (
        f"Active blockers must not record the {label} obligation as complete"
    )
    assert mentioned, (
        f"Active blockers must record the {label} obligation"
    )
    assert unresolved, (
        f"Active blockers must record the {label} obligation as unresolved"
    )


def _assert_beta_release_current_state_contract(text: str) -> None:
    """Assert the canonical current-state Beta release contract.

    The contract is structural and semantic rather than a transcription of
    historical prose: the current phase declares local-first Beta hardening
    behind a HOLD gate, the supported-reality section names the local Docker
    Compose profile ``v1-local-core-web-mcp``, and the Active blockers
    section still records both foundational proof obligations — the
    current-tip supported-Compose qualification and the natural
    import-to-recall proof — as unresolved.
    """
    current_phase = _current_state_section(
        text, "## Current phase", "## What changed recently"
    )
    supported_reality = _current_state_section(
        text, "## Current supported reality", "## Not yet true / do not assume"
    )
    active_blockers = _current_state_section(
        text, "## Active blockers", "## This week's priorities"
    )

    assert "local-first Beta hardening" in current_phase, (
        "Current phase must record local-first Beta hardening"
    )
    assert _active_release_gate_is_hold(current_phase), (
        "Current phase must declare the release gate itself on HOLD"
    )
    assert not _contradicts_release_hold(current_phase), (
        "Current phase must not negate, lift or open the release gate"
    )
    assert not _HOLD_NEGATED.search(current_phase), (
        "Current phase must not negate or lift the HOLD release gate"
    )
    assert not _promotes_release_readiness(current_phase), (
        "Current phase must not promote the release gate to readiness"
    )
    assert _supported_compose_profile_declared(supported_reality), (
        "Supported reality must positively declare the local Docker Compose "
        "install path for profile v1-local-core-web-mcp"
    )
    _require_unresolved_obligation(
        active_blockers,
        _COMPOSE_QUALIFICATION_OBLIGATION,
        "current-tip supported-Compose qualification",
    )
    _require_unresolved_obligation(
        active_blockers,
        _IMPORT_TO_RECALL_OBLIGATION,
        "natural import-to-recall proof",
    )


def test_current_state_preserves_supported_path_hold_and_active_blockers():
    _assert_beta_release_current_state_contract(_read(CURRENT_STATE_PATH))


# ---------------------------------------------------------------------------
# 16b. Negative proof: the release contract must fail closed
# ---------------------------------------------------------------------------

# Table-driven release-gate cases. Each entry is (current phase text,
# accepted). The first four rows are the Codex review findings; the rest
# cover the equivalent truthful wordings the contract must keep accepting.
_HOLD_GATE_CASES = [
    # Finding 1: a negated or lifted HOLD must not pass.
    (
        "`main` remains in local-first Beta hardening. The current release "
        "gate is not HOLD.",
        False,
    ),
    (
        "`main` remains in local-first Beta hardening. HOLD has been lifted.",
        False,
    ),
    (
        "`main` remains in local-first Beta hardening. The release gate is no "
        "longer on HOLD.",
        False,
    ),
    (
        "`main` remains in local-first Beta hardening. The release is ready to "
        "ship.",
        False,
    ),
    # Equivalent truthful wordings must pass.
    (
        "`main` remains in local-first Beta hardening. The current release "
        "gate remains `HOLD`.",
        True,
    ),
    (
        "`main` remains in local-first Beta hardening. The release gate is "
        "HOLD.",
        True,
    ),
    (
        "`main` remains in local-first Beta hardening. Not release-ready; the "
        "release gate remains HOLD.",
        True,
    ),
    (
        "`main` remains in local-first Beta hardening. The Beta release "
        "posture is still HOLD.",
        True,
    ),
]

# Table-driven obligation cases. Each entry is (active-blocker bullet,
# accepted) for the current-tip supported-Compose obligation.
_COMPOSE_OBLIGATION_CASES = [
    # Finding 2: a completed obligation must not borrow another clause's
    # pending marker.
    (
        "- The current-tip supported-Compose qualification is complete; "
        "documentation remains pending.",
        False,
    ),
    (
        "- The current-tip supported-Compose qualification is complete; "
        "import-to-recall proof remains open.",
        False,
    ),
    # Finding 4: ordinary unresolved wording must be accepted.
    ("- The current-tip supported-Compose qualification is missing.", True),
    ("- The current-tip supported-Compose qualification is pending.", True),
    ("- The current-tip supported-Compose qualification is open.", True),
    ("- The current-tip supported-Compose qualification is outstanding.", True),
    ("- The current-tip supported-Compose qualification remains open.", True),
    (
        "- The current-tip supported-Compose qualification has not been "
        "completed.",
        True,
    ),
]


def _synthetic_current_state(
    *,
    phase: str = (
        "`main` remains in local-first Beta hardening. The current release "
        "gate remains `HOLD`."
    ),
    supported: str = (
        "- The named supported install path is local Docker Compose profile "
        "`v1-local-core-web-mcp` with `LLM_PROVIDER=local`."
    ),
    blockers: tuple[str, ...] = (
        "- A fresh current-tip supported-Compose qualification is missing.",
        "- The natural import-to-recall scope proof remain open.",
    ),
    recent: tuple[str, ...] = ("- Nothing yet.",),
    priorities_heading: str = "## This week's priorities",
) -> str:
    """Build a minimal synthetic canonical current-state document."""
    return "\n".join(
        [
            "## Current phase",
            "",
            phase,
            "",
            "## What changed recently",
            "",
            *recent,
            "",
            "## Current supported reality",
            "",
            supported,
            "",
            "## Not yet true / do not assume",
            "",
            "- Do not assume unsupported capabilities.",
            "",
            "## Active blockers",
            "",
            *blockers,
            "",
            priorities_heading,
            "",
            "1. Do the thing.",
            "",
        ]
    )


# Table-driven cases for the PFP-01C3R2 review findings: the release gate
# must be bound to the release subject, the unresolved state must be
# affirmative, the supported profile must be positively declared, and
# standard Markdown list markers must be recognised.
_RELEASE_GATE_SUBJECT_CASES = [
    # P1-1: an unrelated gate on HOLD cannot prove the release HOLD.
    (
        "`main` remains in local-first Beta hardening. The model gate remains "
        "HOLD; the release gate is OPEN.",
        False,
    ),
    # Requirement 5: a contradictory release-gate claim fails even when
    # another clause declares HOLD.
    (
        "`main` remains in local-first Beta hardening. The current release "
        "gate remains `HOLD`; the release gate is OPEN.",
        False,
    ),
    # The release subject must be named explicitly.
    (
        "`main` remains in local-first Beta hardening. The model gate remains "
        "HOLD.",
        False,
    ),
    # Truthful release-gate declarations pass.
    (
        "`main` remains in local-first Beta hardening. The current release "
        "gate remains `HOLD`.",
        True,
    ),
    (
        "`main` remains in local-first Beta hardening. The release gate is "
        "HOLD.",
        True,
    ),
]

_NEGATED_UNRESOLVED_CASES = [
    "- The current-tip supported-Compose qualification is not pending.",
    "- The current-tip supported-Compose qualification is not missing.",
    "- The current-tip supported-Compose qualification is no longer unresolved.",
    "- The current-tip supported-Compose qualification is not outstanding.",
]

_SUPPORTED_PROFILE_CASES = [
    # P1-3: an explicitly unsupported profile cannot satisfy the requirement.
    (
        "- Do not support local Docker Compose profile v1-local-core-web-mcp.",
        False,
    ),
    (
        "- The v1-local-core-web-mcp profile is unsupported.",
        False,
    ),
    (
        "- local Docker Compose profile v1-local-core-web-mcp is not "
        "supported.",
        False,
    ),
    # A positive declaration passes.
    (
        "- The named supported install path is local Docker Compose profile "
        "`v1-local-core-web-mcp` with `LLM_PROVIDER=local`.",
        True,
    ),
]

_LIST_MARKER_CASES = ["-", "*", "+", "1.", "1)"]


def test_beta_release_contract_accepts_typographic_apostrophe_heading() -> None:
    """Canonical current-state writes the weekly heading with U+2019."""
    text = _synthetic_current_state(
        priorities_heading="## This week’s priorities"
    )
    _assert_beta_release_current_state_contract(text)


@pytest.mark.parametrize("phase,accepted", _RELEASE_GATE_SUBJECT_CASES)
def test_beta_release_contract_release_gate_subject_cases(
    phase: str, accepted: bool
) -> None:
    """The HOLD assertion must be bound to the release gate subject."""
    text = _synthetic_current_state(phase=phase)
    if accepted:
        _assert_beta_release_current_state_contract(text)
    else:
        with pytest.raises(AssertionError):
            _assert_beta_release_current_state_contract(text)


@pytest.mark.parametrize("bullet", _NEGATED_UNRESOLVED_CASES)
def test_beta_release_contract_rejects_a_negated_unresolved_state(
    bullet: str,
) -> None:
    """A negated unresolved marker states the opposite of outstanding."""
    text = _synthetic_current_state(
        blockers=(
            bullet,
            "- The natural import-to-recall scope proof remain open.",
        )
    )
    with pytest.raises(AssertionError):
        _assert_beta_release_current_state_contract(text)


@pytest.mark.parametrize("supported,accepted", _SUPPORTED_PROFILE_CASES)
def test_beta_release_contract_supported_profile_cases(
    supported: str, accepted: bool
) -> None:
    """The supported install path must be positively declared."""
    text = _synthetic_current_state(supported=supported)
    if accepted:
        _assert_beta_release_current_state_contract(text)
    else:
        with pytest.raises(AssertionError):
            _assert_beta_release_current_state_contract(text)


@pytest.mark.parametrize("marker", _LIST_MARKER_CASES)
def test_beta_release_contract_recognises_standard_list_markers(
    marker: str,
) -> None:
    """Active blockers may use any standard Markdown list marker."""
    text = _synthetic_current_state(
        blockers=(
            f"{marker} A fresh current-tip supported-Compose qualification is "
            f"missing.",
            f"{marker} The natural import-to-recall scope proof remain open.",
        )
    )
    _assert_beta_release_current_state_contract(text)


def test_beta_release_contract_ignores_blockers_outside_the_section() -> None:
    """A blocker outside Active blockers does not satisfy the contract."""
    text = _synthetic_current_state(
        blockers=("- Nothing relevant is recorded here.",),
        recent=(
            "* A fresh current-tip supported-Compose qualification is missing.",
            "* The natural import-to-recall scope proof remain open.",
        ),
    )
    with pytest.raises(AssertionError):
        _assert_beta_release_current_state_contract(text)


@pytest.mark.parametrize("phase,accepted", _HOLD_GATE_CASES)
def test_beta_release_contract_release_gate_cases(
    phase: str, accepted: bool
) -> None:
    """The release gate must be an active, unnegated HOLD."""
    text = _synthetic_current_state(phase=phase)
    if accepted:
        _assert_beta_release_current_state_contract(text)
    else:
        with pytest.raises(AssertionError):
            _assert_beta_release_current_state_contract(text)


@pytest.mark.parametrize("bullet,accepted", _COMPOSE_OBLIGATION_CASES)
def test_beta_release_contract_obligation_cases(
    bullet: str, accepted: bool
) -> None:
    """Each obligation independently requires its own unresolved state."""
    text = _synthetic_current_state(
        blockers=(
            bullet,
            "- The natural import-to-recall scope proof remain open.",
        )
    )
    if accepted:
        _assert_beta_release_current_state_contract(text)
    else:
        with pytest.raises(AssertionError):
            _assert_beta_release_current_state_contract(text)


# Table-driven obligation-status cases for the natural import-to-recall
# obligation. Each entry is (active-blocker bullet, accepted).
_IMPORT_OBLIGATION_STATUS_CASES = [
    # The canonical coordinated wording: the trailing "remain open" governs
    # every coordinated obligation, and the attributive "complete" describes
    # the neighbouring scope-isolation proof rather than import-to-recall.
    (
        "- New-thread authored-message projection, natural import-to-recall, "
        "and complete scope-isolation proof remain open.",
        True,
    ),
    # Ordinary unresolved wording for the obligation itself.
    ("- The natural import-to-recall proof remains open.", True),
    ("- The natural import-to-recall proof is pending.", True),
    ("- The natural import-to-recall proof has not been completed.", True),
    # An attributive "complete" describing a neighbouring obligation.
    (
        "- The natural import-to-recall proof and complete scope-isolation "
        "proof remain open.",
        True,
    ),
    # The same attributive "complete" when both obligations share one
    # statement, where the neighbouring adjective must still not read as a
    # completion of import-to-recall.
    (
        "- The natural import-to-recall proof plus complete scope-isolation "
        "proof remain open.",
        True,
    ),
    # Several coordinated obligations sharing one unresolved predicate.
    (
        "- Scope-isolation proof, natural import-to-recall, and export proof "
        "remain open.",
        True,
    ),
    # A neighbouring obligation's own completion claim disqualifies nothing.
    (
        "- The natural import-to-recall proof remains open while the "
        "scope-isolation proof is complete.",
        True,
    ),
    (
        "- The scope-isolation proof is complete; the natural import-to-recall "
        "proof remains open.",
        True,
    ),
]


@pytest.mark.parametrize("bullet,accepted", _IMPORT_OBLIGATION_STATUS_CASES)
def test_beta_release_contract_import_obligation_status_cases(
    bullet: str, accepted: bool
) -> None:
    """The obligation's status is read from the statement that names it."""
    text = _synthetic_current_state(
        blockers=(
            "- A fresh current-tip supported-Compose qualification is missing.",
            bullet,
        )
    )
    if accepted:
        _assert_beta_release_current_state_contract(text)
    else:
        with pytest.raises(AssertionError):
            _assert_beta_release_current_state_contract(text)


# Table-driven rejection cases for the obligation-status interpretation. Each
# entry is (active-blocker bullets, expected reason). The reason is asserted
# and anchored, so a case cannot pass because of an unrelated failure.
_OBLIGATION_STATUS_REJECTIONS = [
    # The import-to-recall obligation is explicitly completed.
    (
        (
            "- A fresh current-tip supported-Compose qualification is missing.",
            "- The natural import-to-recall proof is complete.",
        ),
        r"(?m)must not record the natural import-to-recall proof obligation "
        r"as complete$",
    ),
    # The supported-Compose obligation is explicitly completed.
    (
        (
            "- A fresh current-tip supported-Compose qualification is complete.",
            "- The natural import-to-recall proof remains open.",
        ),
        r"(?m)must not record the current-tip supported-Compose qualification "
        r"obligation as complete$",
    ),
    # A completion claim followed by another obligation's pending status.
    (
        (
            "- A fresh current-tip supported-Compose qualification is missing.",
            "- The natural import-to-recall proof is complete; the "
            "scope-isolation proof remains pending.",
        ),
        r"(?m)must not record the natural import-to-recall proof obligation "
        r"as complete$",
    ),
    # An unrelated pending clause cannot disguise a completion claim.
    (
        (
            "- A fresh current-tip supported-Compose qualification is missing.",
            "- The natural import-to-recall proof is complete, but the export "
            "proof remains pending.",
        ),
        r"(?m)must not record the natural import-to-recall proof obligation "
        r"as complete$",
    ),
    # A negated unresolved marker states the opposite of outstanding.
    (
        (
            "- A fresh current-tip supported-Compose qualification is missing.",
            "- The natural import-to-recall proof is not pending.",
        ),
        r"(?m)must record the natural import-to-recall proof obligation "
        r"as unresolved$",
    ),
    # The obligation is not recorded at all.
    (
        (
            "- A fresh current-tip supported-Compose qualification is missing.",
        ),
        r"(?m)must record the natural import-to-recall proof obligation$",
    ),
]


@pytest.mark.parametrize(
    "blockers,reason",
    _OBLIGATION_STATUS_REJECTIONS,
    ids=[
        "import-completed",
        "compose-completed",
        "completion-then-pending",
        "pending-disguises-completion",
        "negated-unresolved",
        "obligation-missing",
    ],
)
def test_beta_release_contract_obligation_status_rejections(
    blockers: tuple[str, ...], reason: str
) -> None:
    """A completion claim fails for the obligation's own reason."""
    text = _synthetic_current_state(blockers=blockers)
    with pytest.raises(AssertionError, match=reason):
        _assert_beta_release_current_state_contract(text)


# Table-driven cases for the obligation-attribution seam. Each entry is (active-
# blocker bullet, expected reason). The reason is asserted, so a case cannot
# pass because of an unrelated failure: a rejection that names the wrong
# obligation status is itself a defect.
_OBLIGATION_ATTRIBUTION_REJECTIONS = [
    # The obligation is contradicted inside its own statement: the completion
    # predicate continues the obligation's subject.
    (
        "- The natural import-to-recall proof remains open but is complete.",
        r"(?m)must not record the natural import-to-recall proof obligation "
        r"as complete$",
    ),
    (
        "- The natural import-to-recall proof remains open but has been "
        "completed.",
        r"(?m)must not record the natural import-to-recall proof obligation "
        r"as complete$",
    ),
    (
        "- The natural import-to-recall proof remains open but is now complete.",
        r"(?m)must not record the natural import-to-recall proof obligation "
        r"as complete$",
    ),
    (
        "- The natural import-to-recall proof remains open but complete.",
        r"(?m)must not record the natural import-to-recall proof obligation "
        r"as complete$",
    ),
    (
        "- The natural import-to-recall proof remains open, but it is complete.",
        r"(?m)must not record the natural import-to-recall proof obligation "
        r"as complete$",
    ),
    (
        "- The natural import-to-recall proof remains open. It is complete.",
        r"(?m)must not record the natural import-to-recall proof obligation "
        r"as complete$",
    ),
    (
        "- We completed the natural import-to-recall proof.",
        r"(?m)must not record the natural import-to-recall proof obligation "
        r"as complete$",
    ),
    (
        "- The completed natural import-to-recall proof remains open.",
        r"(?m)must not record the natural import-to-recall proof obligation "
        r"as complete$",
    ),
    # A connective adverb between the subject and its predicate does not start
    # a new subject, so the completion still belongs to the obligation.
    (
        "- The natural import-to-recall proof remains open but nevertheless "
        "is complete.",
        r"(?m)must not record the natural import-to-recall proof obligation "
        r"as complete$",
    ),
    # The completion can govern the obligation through a prepositional
    # complement ("the proof of natural import-to-recall").
    (
        "- We completed the proof of natural import-to-recall.",
        r"(?m)must not record the natural import-to-recall proof obligation "
        r"as complete$",
    ),
    # A temporal complement does not turn the completion into a description of
    # some other noun phrase.
    (
        "- The natural import-to-recall proof was completed yesterday.",
        r"(?m)must not record the natural import-to-recall proof obligation "
        r"as complete$",
    ),
    # A negation that belongs to another predicate cannot suppress a
    # completion declaration.
    (
        "- Natural import-to-recall is not merely pending: the proof is "
        "complete.",
        r"(?m)must not record the natural import-to-recall proof obligation "
        r"as complete$",
    ),
    # Another subject's pending state cannot satisfy the obligation.
    (
        "- Natural import-to-recall is discussed, while export proofs are "
        "complete and smoke tests are pending.",
        r"(?m)must record the natural import-to-recall proof obligation "
        r"as unresolved$",
    ),
    (
        "- The natural import-to-recall proof is tracked, but export proofs "
        "remain open.",
        r"(?m)must record the natural import-to-recall proof obligation "
        r"as unresolved$",
    ),
    (
        "- The natural import-to-recall proof is tracked, and export proofs "
        "remain open.",
        r"(?m)must record the natural import-to-recall proof obligation "
        r"as unresolved$",
    ),
]

_OBLIGATION_ATTRIBUTION_REJECTION_IDS = [
    "open-but-complete",
    "open-but-has-been-completed",
    "open-but-now-complete",
    "open-but-complete-without-copula",
    "open-but-nevertheless-complete",
    "completed-proof-object",
    "completed-with-temporal-complement",
    "pronoun-continuation",
    "anaphoric-next-sentence",
    "active-voice-completion",
    "attributive-completion-on-the-obligation",
    "unrelated-negation-suppresses-completion",
    "unrelated-pending-subject",
    "unrelated-plural-after-contrast",
    "unrelated-plural-after-coordination",
]

# The same attribution seam, applied to the current-tip supported-Compose
# obligation.
_COMPOSE_ATTRIBUTION_REJECTIONS = [
    (
        "- A fresh current-tip supported-Compose qualification is missing but "
        "is complete.",
        r"(?m)must not record the current-tip supported-Compose qualification "
        r"obligation as complete$",
    ),
    (
        "- We completed the current-tip supported-Compose qualification.",
        r"(?m)must not record the current-tip supported-Compose qualification "
        r"obligation as complete$",
    ),
]

_COMPOSE_ATTRIBUTION_REJECTION_IDS = [
    "compose-open-but-complete",
    "compose-active-voice-completion",
]

# Truthful wordings the contract must keep accepting. Each entry is the full
# Active blockers list. A completion that belongs to a neighbouring
# obligation, and a separate completed obligation, must not alter the target
# obligation's status.
_OBLIGATION_ATTRIBUTION_ACCEPTED = [
    # The canonical coordinated wording.
    (
        "- A fresh current-tip supported-Compose qualification is missing.",
        "- New-thread authored-message projection, natural import-to-recall, "
        "and complete scope-isolation proof remain open.",
    ),
    # An attributive completion on the neighbouring proof, in one statement.
    (
        "- A fresh current-tip supported-Compose qualification is missing.",
        "- The natural import-to-recall proof remains open alongside complete "
        "scope-isolation proof.",
    ),
    # A separate completed obligation in the same bullet.
    (
        "- A fresh current-tip supported-Compose qualification is missing.",
        "- The natural import-to-recall proof remains open; the export proof "
        "is complete.",
    ),
    # An explicit unresolved declaration for the other obligation.
    (
        "- A fresh current-tip supported-Compose qualification remains missing.",
        "- The natural import-to-recall proof remains open.",
    ),
]

_OBLIGATION_ATTRIBUTION_ACCEPTED_IDS = [
    "canonical-coordinated",
    "attributive-completion-on-neighbour",
    "separate-completed-obligation",
    "explicit-unresolved-declaration",
]


@pytest.mark.parametrize(
    "bullet,reason",
    _OBLIGATION_ATTRIBUTION_REJECTIONS,
    ids=_OBLIGATION_ATTRIBUTION_REJECTION_IDS,
)
def test_beta_release_contract_rejects_misattributed_obligation_status(
    bullet: str, reason: str
) -> None:
    """A completion or pending state must belong to its own obligation."""
    text = _synthetic_current_state(
        blockers=(
            "- A fresh current-tip supported-Compose qualification is missing.",
            bullet,
        )
    )
    with pytest.raises(AssertionError, match=reason):
        _assert_beta_release_current_state_contract(text)


@pytest.mark.parametrize(
    "bullet,reason",
    _COMPOSE_ATTRIBUTION_REJECTIONS,
    ids=_COMPOSE_ATTRIBUTION_REJECTION_IDS,
)
def test_beta_release_contract_rejects_misattributed_compose_status(
    bullet: str, reason: str
) -> None:
    """The Compose obligation owns its completion state as well."""
    text = _synthetic_current_state(
        blockers=(
            bullet,
            "- The natural import-to-recall proof remains open.",
        )
    )
    with pytest.raises(AssertionError, match=reason):
        _assert_beta_release_current_state_contract(text)


@pytest.mark.parametrize(
    "blockers",
    _OBLIGATION_ATTRIBUTION_ACCEPTED,
    ids=_OBLIGATION_ATTRIBUTION_ACCEPTED_IDS,
)
def test_beta_release_contract_accepts_truthful_obligation_attribution(
    blockers: tuple[str, ...],
) -> None:
    """A neighbouring obligation's status must not alter this one."""
    text = _synthetic_current_state(blockers=blockers)
    _assert_beta_release_current_state_contract(text)


@pytest.mark.parametrize(
    "blockers",
    [
        (
            "- A fresh current-tip supported-Compose qualification is missing.",
            "- The natural import-to-recall proof remains open.",
            "- The natural import-to-recall proof is complete.",
        ),
        (
            "- A fresh current-tip supported-Compose qualification is missing.",
            "- The natural import-to-recall proof is complete.",
            "- The natural import-to-recall proof remains open.",
        ),
    ],
    ids=["open-then-complete", "complete-then-open"],
)
def test_beta_release_contract_rejects_contradictory_obligation_status(
    blockers: tuple[str, ...],
) -> None:
    """An open declaration must not hide a completed declaration."""
    text = _synthetic_current_state(blockers=blockers)
    with pytest.raises(
        AssertionError,
        match=r"(?m)must not record the natural import-to-recall proof "
        r"obligation as complete$",
    ):
        _assert_beta_release_current_state_contract(text)


@pytest.mark.parametrize(
    "bullet",
    [
        "- The current-tip supported-Compose qualification is complete.",
        "- The current-tip supported-Compose qualification is done.",
        "- The current-tip supported-Compose qualification has been qualified.",
    ],
)
def test_beta_release_contract_rejects_a_completed_obligation(bullet: str) -> None:
    text = _synthetic_current_state(
        blockers=(
            bullet,
            "- The natural import-to-recall scope proof remain open.",
        )
    )
    with pytest.raises(AssertionError):
        _assert_beta_release_current_state_contract(text)


@pytest.mark.parametrize(
    "bullet",
    [
        "- The natural import-to-recall scope proof is complete; "
        "supported-Compose qualification remains pending.",
        "- The natural import-to-recall scope proof is done; "
        "supported-Compose qualification remains open.",
    ],
)
def test_beta_release_contract_rejects_a_completed_import_obligation(
    bullet: str,
) -> None:
    text = _synthetic_current_state(
        blockers=(
            "- A fresh current-tip supported-Compose qualification is missing.",
            bullet,
        )
    )
    with pytest.raises(AssertionError):
        _assert_beta_release_current_state_contract(text)


def test_beta_release_contract_fails_when_hold_is_removed() -> None:
    text = _synthetic_current_state(
        phase="`main` remains in local-first Beta hardening."
    )
    with pytest.raises(AssertionError):
        _assert_beta_release_current_state_contract(text)


def test_beta_release_contract_fails_when_hold_is_promoted_to_readiness() -> None:
    text = _synthetic_current_state(
        phase=(
            "`main` remains in local-first Beta hardening. The current release "
            "gate is READY and is no longer on HOLD."
        )
    )
    with pytest.raises(AssertionError):
        _assert_beta_release_current_state_contract(text)


def test_beta_release_contract_fails_without_the_supported_compose_profile() -> None:
    text = _synthetic_current_state(
        supported="- The supported install path is a local native install."
    )
    with pytest.raises(AssertionError):
        _assert_beta_release_current_state_contract(text)


def test_beta_release_contract_fails_when_the_compose_blocker_is_omitted() -> None:
    text = _synthetic_current_state(
        blockers=("- The natural import-to-recall scope proof remain open.",)
    )
    with pytest.raises(AssertionError):
        _assert_beta_release_current_state_contract(text)


def test_beta_release_contract_fails_when_the_import_blocker_is_omitted() -> None:
    text = _synthetic_current_state(
        blockers=(
            "- A fresh current-tip supported-Compose qualification is missing.",
        )
    )
    with pytest.raises(AssertionError):
        _assert_beta_release_current_state_contract(text)


def test_beta_release_contract_fails_when_a_blocker_claims_completion() -> None:
    text = _synthetic_current_state(
        blockers=(
            "- The current-tip supported-Compose qualification is complete.",
            "- The natural import-to-recall scope proof remain open.",
        )
    )
    with pytest.raises(AssertionError):
        _assert_beta_release_current_state_contract(text)


def test_beta_release_contract_fails_when_blocker_language_is_outside_the_section() -> None:
    text = _synthetic_current_state(
        blockers=("- Something else entirely is unresolved.",),
        recent=(
            "- A fresh current-tip supported-Compose qualification is missing.",
            "- The natural import-to-recall scope proof remain open.",
        ),
    )
    with pytest.raises(AssertionError):
        _assert_beta_release_current_state_contract(text)


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
