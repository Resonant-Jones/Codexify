"""Shared release-truth contract for Guardian evidence-packet tests.

`docs/architecture/00-current-state.md` is the canonical release authority.
These helpers read that document's text and assert its release-boundary
semantics, so the protection survives rewording of the document while still
failing when the boundary itself is removed.

Every check raises `AssertionError` carrying one of the stable
`REASON_*` tokens below. Callers can therefore assert *which* boundary a
synthetic mutation broke instead of only that something failed; a test that
merely expects "an assertion failed" cannot distinguish the intended
invariant from an unrelated missing phrase.

This module is test-only and side-effect free: it never reads the filesystem,
mutates a document, launches a subprocess, or depends on application runtime
state. Callers pass the canonical document's text in.
"""

from __future__ import annotations

import re

# Stable machine-readable reason tokens. Each identifies the owning boundary
# rather than a specific wording, so the tokens survive document rewording.
REASON_RELEASE_AUTHORITY = "release-authority"
REASON_BOUNDED_EVIDENCE = "bounded-evidence"
REASON_SEPARATE_QUALIFICATION = "separate-qualification"
REASON_RELEASE_CONTRADICTION = "release-posture-contradiction"
REASON_RELEASE_HOLD = "release-hold"
REASON_UNMET_CRITERIA = "unmet-release-criteria"
REASON_NON_PROMOTION_CLAIM = "non-promotion-claim"
REASON_NON_PROMOTION_RULE = "non-promotion-rule"

# Section titles are matched case- and whitespace-insensitively. Heading casing
# is presentation, not meaning, so a recased heading must not decide a result.
_SECTION_HEADING = re.compile(r"^##\s+(?P<title>\S.*?)\s*$")

# Affirmative completion states that contradict an active release HOLD.
_GATE_STATES = (
    "complete",
    "completed",
    "qualified",
    "passed",
    "green",
    "released",
    "cleared",
    "closed",
)

# "the release gate is `COMPLETE`" and its close variants. The state word must
# directly follow the copula, so negated forms ("is not `COMPLETE`") cannot
# match and therefore never produce a false positive.
_GATE_ASSERTION = re.compile(
    r"\brelease gate\b[^.;]{0,40}?\b(?:is|is now|now is|remains|stays|"
    r"is marked|is recorded as|has become)\b\s+(?:now\s+)?(?:[`\"'])?"
    r"(?P<state>" + "|".join(_GATE_STATES) + r")\b"
)

# "the release is ready" and its close variants, again copula-anchored so that
# "the release is not ready" is preserved as a valid negated statement.
_READINESS_ASSERTION = re.compile(
    r"\brelease (?:is|is now|has become|becomes)\b\s+(?:now\s+)?(?:fully\s+)?"
    r"(?:ready|approved|qualified|green|complete|released)\b"
)

# "`main` is release-ready" — verb-anchored so "do not call the supported path
# release-ready" stays valid.
_RELEASE_READY_ASSERTION = re.compile(
    r"\b(?:is|remains|becomes|has become)\b\s+(?:now\s+)?release[- ]ready\b"
)


def _heading_key(title: str) -> str:
    """Normalize a heading title so casing and spacing cannot decide a match."""
    return " ".join(title.split()).casefold()


def _document_sections(text: str) -> dict[str, str]:
    """Split a release-truth document into its heading-delimited sections.

    Section-scoped inspection keeps each assertion anchored to the part of the
    document that actually owns a statement, instead of matching prose
    anywhere in the file. Keys are normalized heading titles, so a heading may
    be recased or respaced without changing which section owns a claim.
    """
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        heading = _SECTION_HEADING.match(line)
        if heading:
            current = _heading_key(heading.group("title"))
            sections.setdefault(current, [])
        elif current is not None:
            sections[current].append(line)
    return {name: "\n".join(body) for name, body in sections.items()}


def _normalized(text: str) -> str:
    """Collapse wrapping and casing so neither can decide a result."""
    return " ".join(text.split()).casefold()


def _section(sections: dict[str, str], title: str) -> str:
    """Return one owning section's normalized body."""
    return _normalized(sections.get(_heading_key(title), ""))


def _release_posture_contradiction(document: str) -> str | None:
    """Return the contradicting release-posture claim, if the document makes one.

    The scan is bound to release-posture vocabulary — a claim about the release
    gate or the release itself — so an unrelated completed task or project can
    never be mistaken for a lift of the release boundary. It deliberately looks
    at the whole document: an affirmative "the release gate is `COMPLETE`" on
    any line contradicts a retained HOLD, wherever the author placed it.
    """
    normalized = _normalized(document)
    for pattern in (
        _GATE_ASSERTION,
        _READINESS_ASSERTION,
        _RELEASE_READY_ASSERTION,
    ):
        match = pattern.search(normalized)
        if match:
            return match.group(0)
    return None


def assert_current_release_truth(current: str) -> None:
    """Assert the canonical current-state document states the release boundary.

    Establishes, section by section:

    A. Interpretation Rule — the document identifies release readiness as
       part of its authority.
    B. Supported Reality — bounded implementation evidence is distinguished
       from complete runtime qualification.
    C. Release Posture — the recorded release gate remains HOLD, and the
       document does not also assert that the release is complete or ready.
    D. Qualification — the release definition retains unmet criteria.
    E. Product-Scope Boundary — capabilities without current-main
       qualification cannot silently become default Beta support.

    Checks run in a fixed order so that a caller can predict which reason
    token a given mutation produces. The contradiction check precedes the
    affirmative-HOLD check because an affirmative completion claim is the
    governing defect: a document that says both is lying about the gate, not
    merely omitting the word.
    """
    sections = _document_sections(current)
    interpretation = _section(sections, "Interpretation rule")
    phase = _section(sections, "Current phase")
    supported = _section(sections, "Current supported reality")
    not_yet_true = _section(sections, "Not yet true / do not assume")
    release_definition = sections.get(
        _heading_key("Release definition right now"), ""
    )

    # A. The document is authoritative for release readiness.
    assert "release readiness" in interpretation, (
        f"{REASON_RELEASE_AUTHORITY}: the Interpretation rule must name release "
        "readiness as part of this document's authority"
    )

    # B1. Bounded implementation evidence is recorded as such.
    assert "bounded evidence" in supported, (
        f"{REASON_BOUNDED_EVIDENCE}: Current supported reality must describe "
        "mainline evidence as bounded evidence"
    )

    # B2. ... and bounded evidence is not runtime qualification.
    assert "qualification is a separate gate" in supported, (
        f"{REASON_SEPARATE_QUALIFICATION}: Current supported reality must keep "
        "qualification a separate gate from bounded evidence"
    )

    # C1. Affirmative HOLD and affirmative completion cannot coexist.
    contradiction = _release_posture_contradiction(current)
    assert contradiction is None, (
        f"{REASON_RELEASE_CONTRADICTION}: the document states "
        f"{contradiction!r}, which contradicts the recorded release HOLD"
    )

    # C2. The recorded release gate is still HOLD, under its owning section.
    assert "release gate remains `hold`" in phase, (
        f"{REASON_RELEASE_HOLD}: Current phase must state that the release "
        "gate remains `HOLD`"
    )

    # D. The release definition still records qualification criteria that
    #    are not met.
    unmet = [
        line
        for line in release_definition.splitlines()
        if line.strip().startswith("- [ ]")
    ]
    assert unmet, (
        f"{REASON_UNMET_CRITERIA}: the release definition must still record "
        "unmet qualification criteria"
    )

    # E1. Unqualified capabilities cannot become default Beta support.
    assert "not default beta support" in supported, (
        f"{REASON_NON_PROMOTION_CLAIM}: Current supported reality must state "
        "that unqualified capabilities are not default Beta support"
    )

    # E2. ... and the rule is stated in its own right.
    assert "without current-main qualification" in not_yet_true, (
        f"{REASON_NON_PROMOTION_RULE}: 'Not yet true / do not assume' must keep "
        "the no-promotion-without-current-main-qualification rule"
    )
