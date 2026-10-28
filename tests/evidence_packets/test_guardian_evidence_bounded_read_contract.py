import json
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
NON_PROMOTION_PHRASE = "not default Beta support"
NON_PROMOTION_RULE_PHRASE = "without current-main qualification"
RELEASE_READINESS_PHRASE = "release readiness"

COMPLETION_CLAIM = " The release gate is `COMPLETE` and the release is ready."
NEGATED_POSTURE = " The release is not ready. The release gate is not `COMPLETE`."
UNRELATED_COMPLETION = (
    " The saved-widget storage foundation is complete and the retrieval lane is ready."
)


def _canonical_current_state() -> str:
    return CURRENT_STATE.read_text()


def _drop(text: str, phrase: str) -> str:
    """Remove a phrase, leaving the rest of the document intact."""
    assert phrase in text, f"canonical phrase missing: {phrase!r}"
    return text.replace(phrase, "")


def _swap(text: str, old: str, new: str) -> str:
    """Replace a phrase, leaving the rest of the document intact."""
    assert old in text, f"canonical phrase missing: {old!r}"
    return text.replace(old, new)


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
        if current == source and phrase in line:
            moved.append(line.replace(phrase, ""))
            continue
        moved.append(line)
    result = "\n".join(moved) + "\n"
    assert phrase in result, "the phrase must survive the move"
    return result


def _append_to_section(text: str, *, section: str, addition: str) -> str:
    """Add a sentence inside one section, leaving every other line untouched."""
    marker = f"## {section}"
    lines = text.splitlines()
    assert marker in lines, f"section heading missing: {marker!r}"
    lines.insert(lines.index(marker) + 1, addition)
    return "\n".join(lines) + "\n"


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
    assert HOLD_PHRASE not in document
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
    assert HOLD_PHRASE in document
    _assert_rejected(document, REASON_RELEASE_CONTRADICTION)


def test_release_boundary_helper_rejects_a_hold_replaced_by_completion() -> None:
    document = _swap(
        _canonical_current_state(),
        HOLD_PHRASE,
        "the release gate is `COMPLETE`",
    )
    assert HOLD_PHRASE not in document
    _assert_rejected(document, REASON_RELEASE_CONTRADICTION)


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


def test_release_boundary_helper_rejects_a_document_without_the_beta_non_promotion_claim() -> None:
    _assert_rejected(
        _drop(_canonical_current_state(), NON_PROMOTION_PHRASE),
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
    assert HOLD_PHRASE in document
    _assert_rejected(document, REASON_RELEASE_HOLD)


def test_release_boundary_helper_rejects_authority_found_only_in_an_unrelated_section() -> None:
    """Release authority in a section that does not own it cannot satisfy it."""
    document = _move_to_section(
        _canonical_current_state(),
        RELEASE_READINESS_PHRASE,
        source="Interpretation rule",
        target="Active blockers",
    )
    assert RELEASE_READINESS_PHRASE in document
    _assert_rejected(document, REASON_RELEASE_AUTHORITY)
