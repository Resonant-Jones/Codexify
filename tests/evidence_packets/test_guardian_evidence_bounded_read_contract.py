import json
import re
import subprocess
from pathlib import Path

import pytest

from tests.evidence_packets.release_truth_contract import (
    REASON_BOUNDED_EVIDENCE,
    REASON_NON_PROMOTION_CLAIM,
    REASON_NON_PROMOTION_RULE,
    REASON_RELEASE_AUTHORITY,
    REASON_RELEASE_CONTRADICTION,
    REASON_RELEASE_HOLD,
    REASON_SEPARATE_QUALIFICATION,
    REASON_UNMET_CRITERIA,
    assert_current_release_truth,
)


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "docs/architecture/guardian-evidence-bounded-read-contract.md"
CURRENT_STATE = ROOT / "docs/architecture/00-current-state.md"

SECTIONS = (
    "Purpose", "Status", "Scope", "Current Truth", "Why This Exists",
    "Bounded Read Is Not Authority", "Bounded Read Is Not Execution",
    "Bounded Read Is Not Evidence Ingestion", "Bounded Read Is Not Packet Generation",
    "Allowed Read Sources", "Disallowed Read Sources", "Source Reference Resolution Rules",
    "Local Path Boundary", "Network Boundary", "Secret and Sensitive Content Boundary",
    "Size and Truncation Rules", "Content Hash and Provenance Rules", "Read Artifact Shape",
    "Read Result Semantics", "Error and Warning Semantics", "Relationship to ReducerInputBundle",
    "Relationship to Dry-Run Loader", "Relationship to Packet Generator",
    "Relationship to Static Packet Validation", "Relationship to Execution Ledger and WorkOrder",
    "Relationship to UI and CI", "Forbidden Interpretations", "Future Allowed Slices",
    "Bottom Line",
)


def test_bounded_read_contract_exists_and_has_required_sections() -> None:
    assert CONTRACT.is_file()
    text = CONTRACT.read_text()
    for index, section in enumerate(SECTIONS, start=1):
        assert f"## {index}. {section}" in text


def test_bounded_read_contract_preserves_docs_only_boundaries() -> None:
    text = CONTRACT.read_text()
    for phrase in (
        "This is a docs-only contract",
        "does not implement a bounded evidence reader",
        "does not read source references",
        "does not modify scripts",
        "does not modify Makefile",
        "does not read source_ref targets",
        "does not generate a `GuardianEvidencePacket` output",
        "does not add a runtime or operator read surface",
        "does not alter existing packet fixtures",
        "does not implement runtime reducer behavior",
        "does not implement evidence ingestion",
        "does not add persistence",
        "does not add UI",
        "does not add CI/default release gating",
        "does not authorize execution",
        "does not authorize source mutation",
        "does not authorize Pi Loop invocation",
        "does not authorize provider execution",
        "does not authorize Codexify ingestion",
        "may read only explicitly allowed local source references",
        "must not follow network URLs",
        "must not read secrets",
        "must not call command bus",
        "must not call Codex Runner",
        "must not mutate WorkOrders",
        "must not write Execution Ledger entries",
    ):
        assert phrase in text


def test_allowed_and_disallowed_sources_are_documented() -> None:
    text = CONTRACT.read_text()
    for phrase in (
        "docs/architecture",
        "docs/architecture/fixtures",
        "docs/architecture/templates",
        "explicitly referenced by validated input bundles",
        "Test result summary files explicitly produced by local validation tasks",
        "Static proof index files explicitly named by a later implementation",
        "Absolute paths outside the repository",
        "Network URLs and network-backed references",
        "Secrets files and environment files such as `.env`",
        "Private key files and Git credentials",
        "Database files and Docker volumes",
        "Runtime logs unless a separate contract explicitly permits them",
        "User home directories outside the repository",
        "`/Volumes/Dev_SSD/Codex-Runner` unless a separate read contract explicitly",
        "Any file not explicitly referenced by a validated input bundle",
    ):
        assert phrase in text


def test_read_result_shape_statuses_and_diagnostics_are_documented() -> None:
    text = CONTRACT.read_text()
    for phrase in (
        "GuardianEvidenceBoundedReadResult",
        "schema_version", "read_contract_version", "input_bundle_ref", "source_ref",
        "resolved_repo_relative_path", "read_status", "content_hash", "content_excerpt",
        "excerpt_truncated", "omitted_content_reason", "warnings", "errors", "provenance",
        "limits", "`read`", "`skipped`", "`blocked`", "`missing`", "`too_large`",
        "`unsupported`", "source_ref_outside_repo", "source_ref_network_url_blocked",
        "source_ref_secret_risk_blocked", "source_ref_missing", "source_ref_too_large",
        "source_ref_unsupported_type", "source_ref_not_allowlisted", "content_truncated",
        "content_hash_unavailable", "Validated ReducerInputBundle",
        "future bounded evidence reader", "GuardianEvidencePacket", "static packet validator",
        "human/operator review", "not release approval",
    ):
        assert phrase in text


def test_cross_links_and_existing_tools_remain_green() -> None:
    generator = (ROOT / "docs/architecture/guardian-evidence-packet-generator-contract.md").read_text()
    reducer = (ROOT / "docs/architecture/guardian-evidence-packet-reducer-contract.md").read_text()
    runtime = (ROOT / "docs/architecture/guardian-evidence-packet-runtime-reducer-design-contract.md").read_text()
    loader = (ROOT / "docs/architecture/guardian-evidence-reducer-input-bundle-dry-run-loader-contract.md").read_text()
    validator = (ROOT / "docs/architecture/guardian-evidence-reducer-input-bundle-static-validator-contract.md").read_text()
    readme = (ROOT / "docs/architecture/README.md").read_text()
    current = (ROOT / "docs/architecture/00-current-state.md").read_text()

    assert "guardian-evidence-bounded-read-contract.md" in generator
    assert "guardian-evidence-bounded-read-contract.md" in reducer
    assert "guardian-evidence-bounded-read-contract.md" in runtime
    assert "loader success is not bounded reading" in loader
    assert "validator success is not read approval" in validator
    assert "guardian-evidence-bounded-read-contract.md" in readme
    assert_current_release_truth(current)

    for target in (
        "guardian-evidence-packets-validate",
        "guardian-evidence-reducer-dry-run",
        "guardian-evidence-reducer-input-bundles-validate",
        "guardian-evidence-reducer-input-bundle-dry-run",
    ):
        proc = subprocess.run(["make", target], cwd=ROOT, capture_output=True, text=True, check=False)
        assert proc.returncode == 0, proc.stderr

    packet = subprocess.run(
        ["python3", "scripts/guardian/validate_evidence_packets.py", "--json"],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    bundles = subprocess.run(
        ["python3", "scripts/guardian/validate_reducer_input_bundles.py", "--json"],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    assert packet.returncode == 0
    assert json.loads(packet.stdout)["matched_count"] == 3
    assert bundles.returncode == 0
    assert json.loads(bundles.stdout)["matched_count"] >= 2


def test_task_scope_does_not_add_reader_or_tooling_files() -> None:
    assert not (ROOT / "scripts/guardian/bounded_evidence_reader.py").exists()
    assert not (ROOT / "scripts/guardian/read_evidence.py").exists()


# ── Release-boundary controls ──────────────────────────────────────────
#
# The shared helper asserts that the canonical document *states* the release
# boundary. These controls mutate a synthetic copy of the document and require
# the helper to refuse each mutation for the *intended* boundary, identified by
# its stable reason token. Expecting only "an assertion failed" cannot tell the
# intended invariant apart from an unrelated missing phrase.
#
# Positive controls prove the helper tolerates presentation differences
# (heading casing, source-line wrapping) and preserves valid negated
# statements. Negative controls prove each boundary can fail on its own.
#
# The canonical document is never modified.


HOLD_PHRASE = "the release gate remains `HOLD`"
BOUNDED_EVIDENCE_PHRASE = "bounded evidence"
QUALIFICATION_PHRASE = "qualification is a separate gate"
NON_PROMOTION_PHRASE = "default Beta support remain unqualified"
NON_PROMOTION_RULE_PHRASE = "without current-main qualification"
RELEASE_READINESS_PHRASE = "release readiness"
COMPLETION_CLAIM = " The release gate is `COMPLETE` and the release is ready."
PERFECT_COMPLETION_CLAIM = " The release gate has passed."
PERFECT_CLOSED_CLAIM = " The release gate has closed."
PERFECT_MARKED_CLAIM = " The release gate has been marked as complete."
LIFTED_HOLD_CLAIM = " The release gate is no longer `HOLD`."
NEGATED_POSTURE = " The release is not ready. The release gate is not `COMPLETE`."
NEGATED_PERFECT_POSTURE = " The release gate has not passed."
SUBJECT_NEGATED_POSTURE = " No supported path is release-ready."
SUBJECT_NEGATED_EITHER = " Neither main nor Preview is release-ready."
ARTIFACT_READINESS_CLAIM = " The migration guide is release-ready."
RELEASE_ARTIFACT_READINESS_CLAIM = " The release checklist is release-ready."
UNRELATED_COMPLETION = (
    " The saved-widget storage foundation is complete and the retrieval lane is ready."
)


def _canonical_current_state() -> str:
    return CURRENT_STATE.read_text()


def _find_phrase(text: str, phrase: str) -> tuple[int, int]:
    """Locate a phrase case-insensitively.

    The canonical document rewrites its sentences from week to week, and a
    phrase can move from mid-sentence to sentence-initial position. Matching
    case-insensitively keeps presentation changes from deciding a boundary
    assertion.
    """
    index = text.casefold().find(phrase.casefold())
    assert index != -1, f"canonical phrase missing: {phrase!r}"
    return index, index + len(phrase)


def _contains(text: str, phrase: str) -> bool:
    """Case-insensitive containment check for a canonical phrase."""
    return phrase.casefold() in text.casefold()


def _drop(text: str, phrase: str) -> str:
    """Remove every occurrence of a phrase, leaving the rest of the document intact."""
    return re.compile(re.escape(phrase), re.IGNORECASE).sub("", text)


def _swap(text: str, old: str, new: str) -> str:
    """Replace every occurrence of a phrase, leaving the rest of the document intact."""
    return re.compile(re.escape(old), re.IGNORECASE).sub(new, text)


def _move_to_section(text: str, phrase: str, *, source: str, target: str) -> str:
    """Relocate a phrase out of one section and into an unrelated section."""
    moved: list[str] = []
    current: str | None = None
    for line in text.splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            moved.append(line)
            if current == target:
                moved.append(phrase)
            continue
        if current == source and _contains(line, phrase):
            start, end = _find_phrase(line, phrase)
            moved.append(line[:start] + line[end:])
            continue
        moved.append(line)
    result = "\n".join(moved) + "\n"
    assert _contains(result, phrase), "the phrase must survive the move"
    return result


def _append_to_section(text: str, *, section: str, addition: str) -> str:
    """Add a sentence inside one section, leaving every other line untouched."""
    marker = f"## {section}"
    lines = text.splitlines()
    assert marker in lines, f"section heading missing: {marker!r}"
    lines.insert(lines.index(marker) + 1, addition)
    return "\n".join(lines) + "\n"


def _indent_headings(text: str, spaces: int = 2) -> str:
    """Indent every section heading, which valid Markdown permits."""
    indented: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            indented.append(" " * spaces + line)
        else:
            indented.append(line)
    result = "\n".join(indented) + "\n"
    assert result != text, "the heading indentation must change the document"
    return result


def _recase_headings(text: str) -> str:
    """Recase and respace every section heading without touching body text."""
    recased: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            recased.append(f"##   {line[3:].strip().swapcase()}  ")
        else:
            recased.append(line)
    result = "\n".join(recased) + "\n"
    assert result != text, "the heading recasing must change the document"
    return result


def _wrap_phrase(text: str, phrase: str) -> str:
    """Break a phrase across two real source lines without changing its words."""
    words = phrase.split()
    assert len(words) > 1, "the phrase must have at least two words to wrap"
    midpoint = len(words) // 2
    wrapped = " ".join(words[:midpoint]) + "\n" + " ".join(words[midpoint:])
    return _swap(text, phrase, wrapped)


def _assert_rejected(document: str, reason: str) -> None:
    """The helper must refuse the document for the intended boundary."""
    with pytest.raises(AssertionError) as failure:
        assert_current_release_truth(document)
    assert reason in str(failure.value), (
        f"expected the {reason} boundary to fail, got: {failure.value}"
    )


def test_release_boundary_helper_accepts_the_canonical_document() -> None:
    """Positive control: the canonical document satisfies the boundary."""
    assert_current_release_truth(_canonical_current_state())


def test_release_boundary_helper_tolerates_recased_and_respaced_headings() -> None:
    """Heading casing and spacing are presentation, not meaning."""
    assert_current_release_truth(_recase_headings(_canonical_current_state()))


def test_release_boundary_helper_tolerates_real_body_line_wrapping() -> None:
    """A wrapped source line must not decide a boundary assertion."""
    document = _wrap_phrase(_canonical_current_state(), HOLD_PHRASE)
    document = _wrap_phrase(document, QUALIFICATION_PHRASE)
    assert not _contains(document, HOLD_PHRASE)
    assert_current_release_truth(document)


@pytest.mark.parametrize("spaces", [1, 2, 3])
def test_release_boundary_helper_tolerates_indented_headings(spaces: int) -> None:
    """Leading spaces before a heading are valid Markdown presentation."""
    document = _indent_headings(_canonical_current_state(), spaces)
    assert "\n" + " " * spaces + "## Current phase" in document
    assert_current_release_truth(document)


def test_release_boundary_helper_accepts_negated_release_posture() -> None:
    """Negated readiness language is a valid boundary statement."""
    document = _append_to_section(
        _canonical_current_state(),
        section="Current phase",
        addition=NEGATED_POSTURE,
    )
    assert NEGATED_POSTURE.strip() in document
    assert_current_release_truth(document)


def test_release_boundary_helper_accepts_subject_level_negated_readiness() -> None:
    """Negation before the subject also preserves a valid posture statement."""
    document = _append_to_section(
        _canonical_current_state(),
        section="Current phase",
        addition=SUBJECT_NEGATED_POSTURE,
    )
    assert SUBJECT_NEGATED_POSTURE.strip() in document
    assert_current_release_truth(document)


def test_release_boundary_helper_accepts_negated_either_or_readiness() -> None:
    """A negated `neither ... nor ...` readiness claim stays valid."""
    document = _append_to_section(
        _canonical_current_state(),
        section="Current phase",
        addition=SUBJECT_NEGATED_EITHER,
    )
    assert SUBJECT_NEGATED_EITHER.strip() in document
    assert_current_release_truth(document)


def test_release_boundary_helper_accepts_negated_perfect_tense_gate_claim() -> None:
    """`the release gate has not passed` denies completion rather than claiming it."""
    document = _append_to_section(
        _canonical_current_state(),
        section="Current phase",
        addition=NEGATED_PERFECT_POSTURE,
    )
    assert NEGATED_PERFECT_POSTURE.strip() in document
    assert_current_release_truth(document)


def test_release_boundary_helper_ignores_unrelated_completion_claims() -> None:
    """Completing an unrelated task is not a release-posture claim."""
    document = _append_to_section(
        _canonical_current_state(),
        section="Current phase",
        addition=UNRELATED_COMPLETION,
    )
    assert UNRELATED_COMPLETION.strip() in document
    assert_current_release_truth(document)


def test_release_boundary_helper_rejects_a_document_without_hold() -> None:
    _assert_rejected(
        _drop(_canonical_current_state(), HOLD_PHRASE),
        REASON_RELEASE_HOLD,
    )


def test_release_boundary_helper_rejects_completion_appended_alongside_hold() -> None:
    """A retained HOLD cannot coexist with an affirmative completion claim."""
    document = _append_to_section(
        _canonical_current_state(),
        section="Current phase",
        addition=COMPLETION_CLAIM,
    )
    assert _contains(document, HOLD_PHRASE)
    _assert_rejected(document, REASON_RELEASE_CONTRADICTION)


def test_release_boundary_helper_rejects_a_hold_replaced_by_completion() -> None:
    document = _swap(
        _canonical_current_state(),
        HOLD_PHRASE,
        "the release gate is `COMPLETE`",
    )
    assert not _contains(document, HOLD_PHRASE)
    _assert_rejected(document, REASON_RELEASE_CONTRADICTION)


@pytest.mark.parametrize(
    "claim",
    [PERFECT_COMPLETION_CLAIM, PERFECT_CLOSED_CLAIM, PERFECT_MARKED_CLAIM],
)
def test_release_boundary_helper_rejects_a_perfect_tense_gate_completion(claim: str) -> None:
    """Perfect-tense completions cannot evade the contradiction scanner."""
    document = _append_to_section(
        _canonical_current_state(),
        section="Current phase",
        addition=claim,
    )
    assert _contains(document, HOLD_PHRASE)
    _assert_rejected(document, REASON_RELEASE_CONTRADICTION)


def test_release_boundary_helper_rejects_a_lifted_hold() -> None:
    """A hold that is explicitly no longer in force contradicts the HOLD."""
    document = _append_to_section(
        _canonical_current_state(),
        section="Current phase",
        addition=LIFTED_HOLD_CLAIM,
    )
    assert _contains(document, HOLD_PHRASE)
    _assert_rejected(document, REASON_RELEASE_CONTRADICTION)


def test_release_boundary_helper_ignores_readiness_of_unrelated_artifacts() -> None:
    """An artifact being release-ready is not a product readiness claim."""
    document = _append_to_section(
        _canonical_current_state(),
        section="Current phase",
        addition=ARTIFACT_READINESS_CLAIM,
    )
    assert ARTIFACT_READINESS_CLAIM.strip() in document
    assert_current_release_truth(document)


def test_release_boundary_helper_ignores_readiness_of_a_release_artifact() -> None:
    """A release-named artifact is still an artifact, not the release."""
    document = _append_to_section(
        _canonical_current_state(),
        section="Current phase",
        addition=RELEASE_ARTIFACT_READINESS_CLAIM,
    )
    assert RELEASE_ARTIFACT_READINESS_CLAIM.strip() in document
    assert_current_release_truth(document)


@pytest.mark.parametrize("claim", [
    "The release\ngate\nhas been\nmarked as\ncomplete.",
    "Release is ready.",
    "The release remains on hold, but the release is ready.",
    "The release gate, after evaluation, is complete.",
    "The release gate, after validation, is complete.",
    "The release gate, after testing, is complete.",
    "The release gate, after independent security validation, is complete.",
    "The release gate, after the review, has passed.",
    'The report says `the release is ready`.',
    'The sentence `the release is ready` is prohibited. The release is ready.',
    "Previously the gate was on hold. The release gate was complete.",
    "The release gate is **COMPLETE**.",
    "The release is _ready_.",
    'The report says "The release gate is complete" [1].',
    "Release gate: COMPLETE",
    "| Release gate | COMPLETE |",
    "Release: ready",
    "The release gate passed.",
    "The release gate closed.",
    "The release has been approved.",
    "The release is no longer on hold.",
    "- The release gate is\n  complete.\n- An unrelated task is not ready.",
    "- Nothing is ready.\n- The release gate is complete.",
])
def test_release_boundary_rejects_specific_affirmative_forms(claim: str) -> None:
    document = _append_to_section(_canonical_current_state(), section="Current phase", addition=claim)
    _assert_rejected(document, REASON_RELEASE_CONTRADICTION)


@pytest.mark.parametrize("statement", [
    "The release gate is\nnot\ncomplete.",
    "Release is not ready.",
    "Previously the release gate was complete.",
    "Previously the release gate passed.",
    "The release gate is **not complete**.",
    "The release is not what is ready.",
    'The report says "The release gate is not complete" [1].',
    'The claim "The release gate is complete" [1] is false.',
    "Release gate: not complete",
    "| Release gate | not complete |",
    "The release gate did not pass or close.",
    "The release has not been approved.",
    "The release is still on hold.",
    "- The release gate is on hold.\n- The migration guide is release-ready.",
    "The release remains on hold, but the migration guide is release-ready.",
    "The release gate remains on hold, and the migration guide is release-ready.",
    "The release gate, after evaluation, is not complete.",
    "The release gate, after validation, is not complete.",
    "The release gate, after testing, the migration guide is complete.",
    "The release gate, after evaluation, the migration guide is complete.",
    "The release gate is on hold, after evaluation, the migration guide is complete.",
    "The sentence `the release is ready` is prohibited.",
])
def test_release_boundary_accepts_specific_nonaffirmative_forms(statement: str) -> None:
    document = _append_to_section(_canonical_current_state(), section="Current phase", addition=statement)
    assert_current_release_truth(document)


def test_release_boundary_helper_rejects_a_document_without_bounded_evidence() -> None:
    _assert_rejected(
        _drop(_canonical_current_state(), BOUNDED_EVIDENCE_PHRASE),
        REASON_BOUNDED_EVIDENCE,
    )


def test_release_boundary_helper_rejects_a_document_without_separate_qualification() -> None:
    _assert_rejected(
        _drop(_canonical_current_state(), QUALIFICATION_PHRASE),
        REASON_SEPARATE_QUALIFICATION,
    )


def test_release_boundary_helper_rejects_a_document_whose_release_criteria_are_all_complete() -> None:
    document = _canonical_current_state().replace("- [ ]", "- [x]")
    assert "- [ ]" not in document
    _assert_rejected(document, REASON_UNMET_CRITERIA)


MAIN_NON_PROMOTION = (
    "that proof qualifies same-node messaging only, and share-link bearer "
    "expiry/revocation, cross-node discovery and transport, unread indicators "
    "and persisted read state, and default Beta support remain unqualified"
)

#: The non-promotion wordings the canonical document is allowed to use. The
#: contract tracks the document's current wording instead of one snapshot of
#: it, so a weekly rewrite of the document cannot decide a boundary.
NON_PROMOTION_WORDINGS = (
    "not default Beta support",
    "default Beta support remain unqualified",
)


def _current_non_promotion_wording() -> str:
    """Return the non-promotion wording the canonical document currently uses."""
    document = _canonical_current_state()
    for wording in NON_PROMOTION_WORDINGS:
        if _contains(document, wording):
            return wording
    raise AssertionError(
        "the canonical document must state that unqualified capabilities are "
        "not default Beta support"
    )


def _current_main_non_promotion_document() -> str:
    """The canonical document already states the non-promotion claim."""
    _current_non_promotion_wording()
    return _canonical_current_state()


def _document_with_alternate_non_promotion(alternate: str) -> str:
    """A document that states only the alternate non-promotion wording.

    The contract accepts either wording, so a document built to exercise the
    alternate one has to carry that wording *instead of* the current one.
    """
    document = _drop(
        _canonical_current_state(), _current_non_promotion_wording()
    )
    return _append_to_section(
        document, section="Current supported reality", addition=alternate
    )


def test_release_boundary_accepts_current_main_non_promotion_wording() -> None:
    assert_current_release_truth(_current_main_non_promotion_document())


@pytest.mark.parametrize("prefix", ["It is false that ", "It is not true that "])
def test_release_boundary_rejects_denied_current_main_non_promotion(prefix: str) -> None:
    document = _document_with_alternate_non_promotion(
        prefix + MAIN_NON_PROMOTION
    )
    _assert_rejected(document, REASON_NON_PROMOTION_CLAIM)


def test_release_boundary_rejects_quoted_denial_of_current_main_non_promotion() -> None:
    document = _document_with_alternate_non_promotion(
        '"' + MAIN_NON_PROMOTION + '." is false.'
    )
    _assert_rejected(document, REASON_NON_PROMOTION_CLAIM)


@pytest.mark.parametrize("statement", [
    "Same-node messaging is now default Beta support.",
    "Same-node human messaging is default Beta support.",
    "Not only same-node messaging is now default Beta support.",
    'The report says “Same-node messaging is now default Beta support”.',
])
def test_release_boundary_rejects_same_node_promotion(statement: str) -> None:
    document = _append_to_section(
        _current_main_non_promotion_document(), section="Current supported reality", addition=statement,
    )
    _assert_rejected(document, REASON_NON_PROMOTION_CLAIM)


def test_release_boundary_accepts_denied_same_node_promotion() -> None:
    document = _append_to_section(
        _current_main_non_promotion_document(), section="Current supported reality",
        addition="No evidence says same-node messaging is now default Beta support.",
    )
    assert_current_release_truth(document)


@pytest.mark.parametrize("statement", [
    'The claim "Same-node messaging is now default Beta support" is false.',
    'The claim “Same-node messaging is now default Beta support” is false.',
])
def test_release_boundary_accepts_quoted_denial_of_same_node_promotion(statement: str) -> None:
    document = _append_to_section(
        _current_main_non_promotion_document(), section="Current supported reality",
        addition=statement,
    )
    assert_current_release_truth(document)


def test_release_boundary_rejects_qualified_only_for_another_feature() -> None:
    document = _swap(
        _document_with_alternate_non_promotion(MAIN_NON_PROMOTION),
        MAIN_NON_PROMOTION,
        MAIN_NON_PROMOTION + " only for a different feature",
    )
    _assert_rejected(document, REASON_NON_PROMOTION_CLAIM)


def test_release_boundary_rejects_different_feature_non_promotion() -> None:
    document = _swap(
        _document_with_alternate_non_promotion(MAIN_NON_PROMOTION),
        MAIN_NON_PROMOTION,
        "same-node human messaging is now default Beta support; default Beta "
        "support remain unqualified only for a different feature",
    )
    _assert_rejected(document, REASON_NON_PROMOTION_CLAIM)


def test_release_boundary_helper_rejects_a_document_without_the_beta_non_promotion_claim() -> None:
    _assert_rejected(
        _drop(
            _canonical_current_state(), _current_non_promotion_wording()
        ),
        REASON_NON_PROMOTION_CLAIM,
    )


def test_release_boundary_helper_rejects_a_document_without_the_current_main_qualification_rule() -> None:
    _assert_rejected(
        _drop(_canonical_current_state(), NON_PROMOTION_RULE_PHRASE),
        REASON_NON_PROMOTION_RULE,
    )


def test_release_boundary_helper_rejects_a_document_that_disclaims_release_authority() -> None:
    _assert_rejected(
        _drop(_canonical_current_state(), RELEASE_READINESS_PHRASE),
        REASON_RELEASE_AUTHORITY,
    )


def test_release_boundary_helper_rejects_hold_found_only_in_an_unrelated_section() -> None:
    """A HOLD in a section that does not own the gate cannot satisfy it."""
    document = _move_to_section(
        _canonical_current_state(),
        HOLD_PHRASE,
        source="Current phase",
        target="Active blockers",
    )
    # The phrase is still present in the document, just in the wrong section.
    assert _contains(document, HOLD_PHRASE)
    _assert_rejected(document, REASON_RELEASE_HOLD)


def test_release_boundary_helper_rejects_authority_found_only_in_an_unrelated_section() -> None:
    """Release authority in a section that does not own it cannot satisfy it."""
    document = _move_to_section(
        _canonical_current_state(),
        RELEASE_READINESS_PHRASE,
        source="Interpretation rule",
        target="Active blockers",
    )
    assert _contains(document, RELEASE_READINESS_PHRASE)
    _assert_rejected(document, REASON_RELEASE_AUTHORITY)


# ── Release-posture attribution controls ───────────────────────────────────
#
# Each repaired defect gets a paired control: one statement that must still be
# accepted, and one that must be rejected for the intended boundary. Every
# rejection asserts its own REASON_* token, so a case cannot pass merely
# because an unrelated required section went missing.

#: Posture claims that contradict a recorded HOLD and must be rejected.
CONTRADICTING_POSTURE_CLAIMS = (
    # The gate itself.
    "The release gate is OPEN.",
    "Release gate: OPEN",
    "Release gate: ready",
    "The release gate is ready.",
    "The release gate is release-ready.",
    "The release gate is ready for release.",
    # The product release.
    "The release has been completed.",
    "The release has been cleared.",
    "The release has passed.",
    "The release has been passed.",
    # A product-path subject.
    "The supported path is complete.",
    "main is complete.",
    # An affirmative modifier does not weaken the claim.
    "The supported path is definitely ready for release.",
    # A negation inside a subject modifier does not cancel the predicate.
    "The release with no outstanding blockers is ready.",
)

#: Statements that must keep being accepted. A narrower artifact, a negated,
#: conditional or historical claim is not a product release posture.
NON_POSTURE_STATEMENTS = (
    "No supported path is release-ready.",
    "The release candidate is ready.",
    "The release build is green.",
    "The main documentation is release-ready.",
    "If the release is ready, begin deployment.",
    "When the release gate is complete, publish the artifacts.",
    "The release was ready in the previous cycle.",
    "The release gate was complete during the last cycle.",
    "The release never became ready.",
)

#: (contradicting claim, valid counterpart). The counterpart keeps the same
#: subject and predicate but states no present readiness, so it must remain
#: acceptable while the contradicting claim is rejected.
PAIRED_POSTURE_CONTROLS = (
    ("The release gate is OPEN.", "The release gate is still on hold."),
    ("The release gate is ready.", "The release gate is not ready."),
    ("The release has been completed.", "The release has not been completed."),
    ("The release has been cleared.", "The release has not been cleared."),
    ("The release has been passed.", "The release has not been passed."),
    ("The release has passed.", "The release has not passed."),
    ("The supported path is complete.", "The supported path is not complete."),
    ("main is complete.", "main is not complete."),
    (
        "The supported path is definitely ready for release.",
        "The supported path is definitely not ready for release.",
    ),
    (
        "The release with no outstanding blockers is ready.",
        "The release with no outstanding blockers is not ready.",
    ),
)

#: Promotions of capabilities the canonical supported-reality section names as
#: unqualified. Each is checked against the non-promotion boundary, not the
#: release-posture boundary.
UNQUALIFIED_PROMOTION_CLAIMS = (
    "Same-node messaging has become default Beta support.",
    "Same-node messaging remains default Beta support.",
    "Share links are default Beta support.",
    "Cross-node transport is default Beta support.",
    "Persisted read state is default Beta support.",
    "Connectors are default Beta support.",
    "Watchdog is default Beta support.",
)

#: A denial of the non-promotion rule promotes the capability it denies.
NON_PROMOTION_DENIALS = (
    "It is false that same-node human messaging is not default Beta support.",
)


@pytest.mark.parametrize("claim", CONTRADICTING_POSTURE_CLAIMS)
def test_release_boundary_rejects_a_contradicting_posture_claim(claim: str) -> None:
    """A posture claim that contradicts the recorded HOLD must be rejected."""
    document = _append_to_section(
        _canonical_current_state(), section="Current phase", addition=claim
    )
    _assert_rejected(document, REASON_RELEASE_CONTRADICTION)


@pytest.mark.parametrize("statement", NON_POSTURE_STATEMENTS)
def test_release_boundary_accepts_a_non_posture_statement(statement: str) -> None:
    """An artifact, negated, conditional or historical claim is not posture."""
    document = _append_to_section(
        _canonical_current_state(), section="Current phase", addition=statement
    )
    assert_current_release_truth(document)


@pytest.mark.parametrize(
    "contradiction,counterpart",
    PAIRED_POSTURE_CONTROLS,
    ids=[pair[0] for pair in PAIRED_POSTURE_CONTROLS],
)
def test_release_boundary_separates_a_contradiction_from_its_counterpart(
    contradiction: str, counterpart: str
) -> None:
    """Each repaired defect has a valid counterpart that must stay valid."""
    rejected = _append_to_section(
        _canonical_current_state(), section="Current phase", addition=contradiction
    )
    _assert_rejected(rejected, REASON_RELEASE_CONTRADICTION)
    accepted = _append_to_section(
        _canonical_current_state(), section="Current phase", addition=counterpart
    )
    assert_current_release_truth(accepted)


@pytest.mark.parametrize("claim", UNQUALIFIED_PROMOTION_CLAIMS)
def test_release_boundary_rejects_an_unqualified_capability_promotion(
    claim: str,
) -> None:
    """Promoting an unqualified capability contradicts the non-promotion rule."""
    document = _append_to_section(
        _canonical_current_state(),
        section="Current supported reality",
        addition=claim,
    )
    _assert_rejected(document, REASON_NON_PROMOTION_CLAIM)


@pytest.mark.parametrize("denial", NON_PROMOTION_DENIALS)
def test_release_boundary_rejects_a_denied_non_promotion_statement(
    denial: str,
) -> None:
    """Denying the non-promotion rule promotes the capability it denies."""
    document = _append_to_section(
        _canonical_current_state(),
        section="Current supported reality",
        addition=denial,
    )
    _assert_rejected(document, REASON_NON_PROMOTION_CLAIM)


#: An unchecked item that names no release-qualification obligation. It is an
#: unrelated task, so it cannot stand in for an unmet release criterion.
UNRELATED_UNMET_TASK = "- [ ] Optional documentation cleanup"


def _every_release_criterion_met(document: str) -> str:
    """Mark every recorded criterion met, leaving the HOLD in place."""
    met = document.replace("- [ ]", "- [x]")
    assert "- [ ]" not in met
    return met


def test_release_boundary_rejects_an_unrelated_task_standing_in_for_a_criterion() -> (
    None
):
    """An unrelated unchecked task cannot satisfy the unmet-criteria rule."""
    document = _append_to_section(
        _every_release_criterion_met(_canonical_current_state()),
        section="Release definition right now",
        addition=UNRELATED_UNMET_TASK,
    )
    _assert_rejected(document, REASON_UNMET_CRITERIA)


def test_release_boundary_accepts_an_unrelated_task_beside_unmet_criteria() -> None:
    """An unrelated task is harmless while a real criterion stays unmet."""
    document = _append_to_section(
        _canonical_current_state(),
        section="Release definition right now",
        addition=UNRELATED_UNMET_TASK,
    )
    assert_current_release_truth(document)
