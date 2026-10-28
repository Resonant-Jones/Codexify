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
# and indentation are presentation, not meaning, so a recased or slightly
# indented heading must not decide a result. Markdown allows up to three
# leading spaces before an ATX heading.
_SECTION_HEADING = re.compile(r"^ {0,3}##\s+(?P<title>\S.*?)\s*$")

# ── Release-posture contradiction scanning ────────────────────────────────
#
# The scanner answers one question: does this document *affirmatively* claim
# that the release itself is complete or ready, while the release gate is
# recorded as HOLD? Three properties keep it from misfiring:
#
#   1. Subject scoping. A claim counts only when its subject is the release
#      gate, the release, the supported path, or main. Completing an unrelated
#      task or artifact is not a release-posture claim.
#   2. Negation preservation. Negation is honoured both after the copula
#      ("is not ready") and before the subject ("No supported path is
#      release-ready", "Neither main nor Preview is release-ready").
#   3. Tense coverage. Present, perfect, and passive-past completions are all
#      detected, so "the release gate has passed" cannot slip through.

# Affirmative completion states that contradict an active release HOLD.
_COMPLETION_STATES = (
    "complete",
    "completed",
    "qualified",
    "passed",
    "green",
    "released",
    "cleared",
    "closed",
    "approved",
    "lifted",
)

# Verbs that can carry a completion state. Perfect forms ("has passed",
# "has been marked as complete") are included so that a completion claim
# cannot be evaded by tense alone.
_COMPLETION_VERB = (
    r"(?:is|are|am|was|were|remains|remained|stays|stayed|now\s+is|is\s+now"
    r"|has|have|had)"
    r"(?:\s+been)?"
    r"(?:\s+(?:marked|recorded|set|flagged|labeled|certified|reported))?"
    r"(?:\s+as)?"
)

# "the release gate is `COMPLETE`", "the release gate has passed",
# "the release hold has been lifted".
_GATE_CLAIM = re.compile(
    r"\b(?:the\s+)?release\s+(?:gate|hold)\b"
    r"(?P<mid>[^.;:!?\n]{0,60}?)"
    r"\b(?P<verb>" + _COMPLETION_VERB + r")\b"
    r"\s+(?:[`\"']?)(?P<state>" + "|".join(_COMPLETION_STATES) + r")\b"
)

# "the release gate is no longer `HOLD`" — a lifted hold is a contradiction
# even though no completion word appears.
_HOLD_LIFTED = re.compile(
    r"\b(?:the\s+)?release\s+(?:gate|hold)\b"
    r"[^.;:!?\n]{0,60}?\bno\s+longer\b"
    r"[^.;:!?\n]{0,20}?\bhold\b"
)

# Nouns that turn "release" into a different object. A release checklist or a
# release guide is an artifact, not the release, so "the release checklist is
# release-ready" is a truthful narrow claim rather than a posture claim.
_RELEASE_ARTIFACT = (
    r"(?!\s+(?:gate|hold|checklist|guide|notes?|definition|metadata|plan|policy"
    r"|process|record|runbook|document|docs|readiness|evidence|artifact"
    r"|boundary|posture|matrix|tracker|status|log|sign[- ]?off|timeline))"
)

# Subjects that denote the product release posture itself.
_PRODUCT_SUBJECT = (
    r"(?:(?:the|this|that)\s+release" + _RELEASE_ARTIFACT + r")"
    r"|(?:\brelease" + _RELEASE_ARTIFACT + r")"
    r"|(?:\bthe\s+supported\s+path\b)"
    r"|(?:\bsupported\s+path\b)"
    r"|(?:\b`?main`?\b)"
)

# Verbs that can carry a readiness predicate.
_READINESS_VERB = (
    r"(?:is|are|was|were|becomes|became|has\s+become|have\s+become"
    r"|had\s+become|remains|remained|stays|stayed)"
)

# "the release is release-ready", "the supported path is ready for release".
_RELEASE_READY_CLAIM = re.compile(
    r"\b(?P<subject>" + _PRODUCT_SUBJECT + r")"
    r"(?P<mid>[^.;:!?\n]{0,60}?)"
    r"\b(?P<verb>" + _READINESS_VERB + r")\b"
    r"\s+(?:now\s+)?(?:fully\s+)?(?:[`\"']?)"
    r"(?:release[- ]ready|ready\s+for\s+release)\b"
)

# "the release is ready", "the release is qualified". The bare predicate is
# only a posture claim when the subject is the release itself.
_RELEASE_BARE_READY = re.compile(
    r"\b(?P<subject>(?:the|this|that)\s+release" + _RELEASE_ARTIFACT + r")"
    r"(?P<mid>[^.;:!?\n]{0,60}?)"
    r"\b(?P<verb>" + _READINESS_VERB + r")\b"
    r"\s+(?:now\s+)?(?:fully\s+)?(?:[`\"']?)"
    r"(?:ready|approved|qualified|green|complete|released)\b"
)

# Negation cues. These can precede the subject ("No supported path is
# release-ready") as well as follow the copula.
_NEGATION_CUES = re.compile(
    r"\b(?:no|not|never|neither|nor|none|nothing|nobody|cannot|without"
    r"|lacks?|lacking|isn't|aren't|wasn't|weren't|doesn't|don't|didn't)\b"
)

# Qualifiers that scope a completion claim to a past cycle rather than to the
# current posture.
_HISTORICAL_CUES = re.compile(
    r"\b(?:previous|previously|former|formerly|prior|earlier|past|historical"
    r"|used\s+to|last\s+(?:cycle|release|run|window|pass))\b"
)

# Clause boundaries. The text after the last boundary is the clause that
# governs a match, so a negation or a qualifier in an earlier clause cannot
# silence a claim in a later one.
_CLAUSE_BOUNDARY = re.compile(
    r"[,;:.!?]|\b(?:but|and|although|though|while|yet|whereas)\b"
)

# Past-tense verbs. Only a past-tense claim can be scoped to a past cycle.
_PAST_TENSE = re.compile(r"\b(?:was|were|became|remained|stayed|had)\b")

# "not only" / "not just" intensify rather than negate.
_NOT_ONLY = re.compile(r"\bnot\s+(?:only|just)\b")


def _heading_key(title: str) -> str:
    """Normalize a heading title so casing and spacing cannot decide a match."""
    return " ".join(title.split()).casefold()


def _document_sections(text: str) -> dict[str, str]:
    """Split a release-truth document into its heading-delimited sections.

    Section-scoped inspection keeps each assertion anchored to the part of the
    document that actually owns a statement, instead of matching prose
    anywhere in the file. Keys are normalized heading titles, so a heading may
    be recased, respaced, or slightly indented without changing which section
    owns a claim.
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


def _scan_text(text: str) -> str:
    """Casefold for matching while preserving source-line boundaries."""
    return text.casefold()


def _logical_lines(document: str) -> list[str]:
    """Normalized, casefolded, non-empty source lines.

    The canonical document is line-oriented: one claim per line. Scanning
    line by line keeps the context of a claim inside its own line, so a
    negation in an unrelated list item cannot silence it.
    """
    return [
        " ".join(line.split()).casefold()
        for line in document.splitlines()
        if line.strip()
    ]


def _section(sections: dict[str, str], title: str) -> str:
    """Return one owning section's normalized body."""
    return _normalized(sections.get(_heading_key(title), ""))


def _governing_clause(prefix: str) -> str:
    """The clause that governs a match: the text after the last boundary."""
    boundaries = list(_CLAUSE_BOUNDARY.finditer(prefix))
    if boundaries:
        return prefix[boundaries[-1].end():]
    return prefix


def _release_posture_contradiction(document: str) -> str | None:
    """Return the contradicting release-posture claim, if the document makes one.

    The scan is bound to release-posture vocabulary and to the product subject
    it names, so an unrelated completed task, project, or artifact can never
    be mistaken for a lift of the release boundary. Negated claims are
    preserved, and a past-tense claim scoped to a past cycle is not read as a
    statement about the current posture.
    """
    lines = _logical_lines(document)
    for index, line in enumerate(lines):
        following = lines[index + 1] if index + 1 < len(lines) else ""
        window = f"{line} {following}" if following else line
        for pattern in (
            _GATE_CLAIM,
            _HOLD_LIFTED,
            _RELEASE_READY_CLAIM,
            _RELEASE_BARE_READY,
        ):
            for match in pattern.finditer(window):
                if match.start() >= len(line):
                    # The claim begins on the following line; it must not
                    # inherit the preceding line's context.
                    prefix = window[len(line) + 1: match.start()]
                else:
                    prefix = window[: match.start()]
                clause = _governing_clause(prefix)
                if _NEGATION_CUES.search(_NOT_ONLY.sub(" ", clause)):
                    continue
                if _PAST_TENSE.search(match.group(0)) and _HISTORICAL_CUES.search(prefix):
                    continue
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
