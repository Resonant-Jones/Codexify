"""Shared release-truth contract for Guardian evidence-packet tests.

`docs/architecture/00-current-state.md` is the canonical release authority.
These helpers check selected release-boundary wording in that document.
They tolerate the tested rewordings, but are not a general semantic parser.

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
# This is a bounded heuristic, not a general natural-language parser. It
# recognizes the subject, tense, status, negation and Markdown forms covered
# by the evidence-packet controls. Unrecognized wording may escape detection.
# Separate Markdown list items and paragraphs do not share claim context.

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

# Readiness states contradict an active release HOLD exactly as a completion
# does: a gate that is ready is not a gate that is on HOLD.
_READINESS_STATES = (
    "ready",
    "release[- ]ready",
    r"ready\s+for\s+release",
)

# "open" is the state this repository's sibling release-boundary matcher
# already treats as contradicting HOLD.
_OPEN_STATE = "open"

# Every state that contradicts a recorded HOLD.
_CONTRADICTORY_STATES = (
    "|".join(_COMPLETION_STATES)
    + "|"
    + "|".join(_READINESS_STATES)
    + "|"
    + _OPEN_STATE
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

# Adverbs that may sit between a verb and its readiness predicate without
# changing the claim. Only affirmative modifiers are listed: a negation word
# must never be consumed here, or "is not ready" would read as "is ready".
_AFFIRMATIVE_MODIFIER = (
    r"(?:now|already|still|fully|definitely|certainly|clearly|indeed|truly"
    r"|actually|absolutely|safely|properly)"
)

# Do not consume a later clause: another release subject there must still be
# eligible to match independently. Allow a short "after ..." parenthetical
# directly before the predicate, not an intervening comma-separated clause.
_CLAIM_MID = (
    r"(?:\s*,\s*after\s+"
    r"(?:(?!\b(?:and|but|is|are|was|were|not)\b)[a-z][a-z'-]*\s+){0,3}"
    r"(?!\b(?:and|but|is|are|was|were|not)\b)[a-z][a-z'-]*\s*,\s*"
    r"|(?:(?!\b(?:but|and|although|though|while|yet|whereas)\b)[^,.;:!?\n]){0,60}?)"
)

# A noun that makes the phrase after it an artifact rather than the release
# itself. "The release candidate is ready" and "the release build is green"
# are statements about a build, not about the release posture.
_ARTIFACT_NOUN = (
    r"(?:gate|hold|checklist|guide|notes?|definition|metadata|plan|policy"
    r"|process|record|runbook|document|docs|documentation|readiness|evidence"
    r"|artifact|boundary|posture|matrix|tracker|status|log|sign[- ]?off|timeline"
    r"|candidate|build|branch|image|tag|version)"
)

# Nouns that turn "release" into a different object. A release checklist or a
# release guide is an artifact, not the release, so "the release checklist is
# release-ready" is a truthful narrow claim rather than a posture claim.
_RELEASE_ARTIFACT = r"(?!\s+(?:" + _ARTIFACT_NOUN + r"))"

# Subjects that denote the product release posture itself. The "main"
# alternative is guarded by the same artifact list, so "the main documentation
# is release-ready" stays a narrow artifact claim.
_PRODUCT_SUBJECT = (
    r"(?:(?:the|this|that)\s+release" + _RELEASE_ARTIFACT + r")"
    r"|(?:\brelease" + _RELEASE_ARTIFACT + r")"
    r"|(?:\bthe\s+supported\s+path\b)"
    r"|(?:\bsupported\s+path\b)"
    r"|(?:\b`?main`?(?!\s+(?:" + _ARTIFACT_NOUN + r"))\b)"
)

# Verbs that can carry a readiness predicate. The plain perfect forms are
# included so that "the release has passed" cannot be evaded by tense alone.
_READINESS_VERB = (
    r"(?:is|are|was|were|becomes|became|has\s+become|have\s+become"
    r"|had\s+become|(?:has|have|had)\s+been|remains|remained|stays|stayed"
    r"|has|have|had)"
)

# "the release gate is `COMPLETE`", "the release gate has passed",
# "the release hold has been lifted", "the release gate is ready".
_GATE_CLAIM = re.compile(
    r"\b(?:the\s+)?release\s+(?:gate|hold)\b"
    r"(?P<mid>" + _CLAIM_MID + r")"
    r"(?:\b(?P<verb>" + _COMPLETION_VERB + r")\b\s+"
    r"|(?=\b(?:passed|closed)\b))"
    r"(?:[`\"']?)(?P<state>" + _CONTRADICTORY_STATES + r")\b"
)

# "the release gate is no longer `HOLD`" — a lifted hold is a contradiction
# even though no completion word appears.
_HOLD_LIFTED = re.compile(
    r"\b(?:the\s+)?release\s+(?:gate|hold)\b"
    r"(?P<mid>" + _CLAIM_MID + r")\bno\s+longer\b"
    r"[^.;:!?\n]{0,20}?\bhold\b"
)

# "the release is release-ready", "the supported path is ready for release".
_RELEASE_READY_CLAIM = re.compile(
    r"\b(?P<subject>" + _PRODUCT_SUBJECT + r")"
    r"(?P<mid>" + _CLAIM_MID + r")"
    r"\b(?P<verb>" + _READINESS_VERB + r")\b"
    r"\s+(?:" + _AFFIRMATIVE_MODIFIER + r"\s+)*"
    r"(?:[`\"']?)(?:" + "|".join(_READINESS_STATES) + r")\b"
)

# "the release is ready", "the release is qualified", "the supported path is
# complete". The bare predicate is only a posture claim when the subject is
# the release itself or another product-path subject.
_RELEASE_BARE_READY = re.compile(
    r"\b(?P<subject>" + _PRODUCT_SUBJECT + r")"
    r"(?P<mid>" + _CLAIM_MID + r")"
    r"\b(?P<verb>" + _READINESS_VERB + r")\b"
    r"\s+(?:" + _AFFIRMATIVE_MODIFIER + r"\s+)*"
    r"(?:[`\"']?)(?:" + "|".join(_COMPLETION_STATES) + r"|ready)\b"
)

# Explicit label/value statuses, not arbitrary colon- or table-delimited prose.
_STATUS_CLAIM = re.compile(
    r"\b(?:the\s+)?(?:release\s+(?:gate|hold)\b|release\b"
    + _RELEASE_ARTIFACT + r")\s*(?::|\|)\s*[`\"']?"
    r"(?:" + _CONTRADICTORY_STATES + r")\b"
)

_PRODUCT_HOLD_LIFTED = re.compile(
    r"\b(?P<subject>" + _PRODUCT_SUBJECT + r")"
    r"(?P<mid>" + _CLAIM_MID + r")\b(?:is|was|remains)\s+no\s+longer\s+on\s+hold\b"
)

# Capabilities the canonical supported-reality section names as unqualified. A
# promotion claims one of them is default Beta support.
_UNQUALIFIED_CAPABILITY = (
    r"(?:same-node\s+(?:human\s+)?messaging"
    r"|share[- ]links?"
    r"|cross-node\s+(?:discovery|transport)"
    r"|(?:unread\s+indicators\s+and\s+)?persisted\s+read\s+state"
    r"|recipient-local\s+read\s+state"
    r"|connectors?|activation|browser\s+host(?:/import)?|watchdog"
    r"|hosted\s+sandbox|atlas|\bpi\b|federation"
    r"|autonomous\s+coding[- ]worker\s+work)"
)

# The state-carrying verbs a promotion may use.
_PROMOTION_VERB = (
    r"(?:is|are|was|were|becomes|became|has\s+become|have\s+become"
    r"|had\s+become|(?:has|have|had)\s+been|remains|remained|stays|stayed)"
)

# Release-qualification obligations the release definition must still record as
# unmet. An unchecked Markdown item that names none of these is an unrelated
# task, not a release criterion, so it cannot satisfy the HOLD on its own.
_REQUIRED_QUALIFICATION_GATE = re.compile(
    r"\b(?:compose|explicit[\s-]model|import[\s-]to[\s-]recall|import[\s-]recall"
    r"|scope[\s-]isolation|reasoning_effort|release metadata)\b",
    re.IGNORECASE,
)

# Negation cues. These can precede the subject ("No supported path is
# release-ready") as well as follow the copula.
_NEGATION_CUES = re.compile(
    r"\b(?:no|not|never|neither|nor|none|nothing|nobody|cannot|without"
    r"|lacks?|lacking|isn't|aren't|wasn't|weren't|doesn't|don't|didn't)\b"
)

# A negation that follows a preposition qualifies the noun it attaches to
# rather than the predicate: "the release with no outstanding blockers is
# ready" states that the release is ready, not that it is not ready.
_PREPOSITION_QUALIFIED_NEGATION = re.compile(
    r"\b(?:with|without|for|of|on|in|at|by|from|during|after|before)\b"
    r"(?:\s+\w+){0,3}\s+(?:no|not|none|never)\b"
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

# Conditional clauses state no present posture, so readiness inside one is
# not a current claim.
_CONDITIONAL_INTRODUCER = re.compile(
    r"\b(?:if|when|whenever|once|unless|in\s+case|should|would)\b",
    re.IGNORECASE,
)

# Past-tense verbs. Only a past-tense claim can be scoped to a past cycle.
_PAST_TENSE = re.compile(r"\b(?:was|were|became|remained|stayed|had|passed|closed)\b")

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
    """Join wrapped paragraphs and list items, but not distinct Markdown blocks.

    Blank lines, headings, table rows and new list markers start a new block.
    This deliberately handles ordinary soft wrapping, not full Markdown.
    """
    blocks: list[str] = []
    current: list[str] = []

    def flush() -> None:
        if current:
            text = " ".join(current).casefold()
            # Strip simple Markdown emphasis delimiters, not internal underscores.
            text = re.sub(r"(?<!\w)(?:\*\*|__|\*|_)(?=\w)|(?<=\w)(?:\*\*|__|\*|_)(?!\w)", "", text)
            blocks.append(text)
            current.clear()

    for source_line in document.splitlines():
        line = " ".join(source_line.split())
        if not line:
            flush()
            continue
        if re.match(r"(?:#{1,6}\s|[-+*]\s|\d+[.)]\s|\|)", line):
            flush()
        current.append(line)
        if line.startswith(("#", "|")):
            flush()
    flush()
    return blocks


def _section(sections: dict[str, str], title: str) -> str:
    """Return one owning section's normalized body."""
    return _normalized(sections.get(_heading_key(title), ""))


def _governing_clause(prefix: str) -> str:
    """The clause that governs a match: the text after the last boundary."""
    boundaries = list(_CLAUSE_BOUNDARY.finditer(prefix))
    if boundaries:
        return prefix[boundaries[-1].end():]
    return prefix


def _clause_suffix(suffix: str) -> str:
    """The bounded remainder of the clause that follows a match.

    Only the current clause is returned, so a qualifier in a later sentence
    cannot silence a claim here.
    """
    boundary = _CLAUSE_BOUNDARY.search(suffix)
    if boundary:
        return suffix[:boundary.start()]
    return suffix


def _without_preposition_qualified_negation(text: str) -> str:
    """Drop negations that qualify a noun rather than the predicate."""
    return _PREPOSITION_QUALIFIED_NEGATION.sub(
        lambda match: match.group(0).rsplit(None, 1)[0] + " ", text
    )


def _release_posture_contradiction(document: str) -> str | None:
    """Return the contradicting release-posture claim, if the document makes one.

    This recognizes only the tested vocabulary and constructions. It is not
    proof that arbitrary prose, quotations or Markdown cannot conceal a claim.
    """
    for block in _logical_lines(document):
        for pattern in (
            _GATE_CLAIM,
            _HOLD_LIFTED,
            _PRODUCT_HOLD_LIFTED,
            _RELEASE_READY_CLAIM,
            _RELEASE_BARE_READY,
            _STATUS_CLAIM,
        ):
            for match in pattern.finditer(block):
                prefix = block[:match.start()]
                clause = _governing_clause(prefix)
                suffix = block[match.end():]
                trailing = _clause_suffix(suffix)
                mid = match.groupdict().get("mid") or ""
                scope = _NOT_ONLY.sub(
                    " ",
                    _without_preposition_qualified_negation(clause + " " + mid),
                )
                if _NEGATION_CUES.search(scope):
                    continue
                # A conditional clause asserts no present posture.
                if _CONDITIONAL_INTRODUCER.search(
                    clause
                ) or _CONDITIONAL_INTRODUCER.search(trailing):
                    continue
                if _PAST_TENSE.search(match.group(0)) and _HISTORICAL_CUES.search(
                    clause + " " + mid + " " + trailing
                ):
                    continue
                # A quoted claim explicitly denied after its closing quote is
                # not an affirmation; allow a simple Markdown citation first.
                if re.match(r"[`*_]*[\"']\s*(?:\[[^\]]+\]\s*)?(?:is|was)\s+(?:false|not\s+true)\b", suffix):
                    continue
                # A complete quote described as prohibited is not itself a
                # posture assertion; require the same opening/closing marker.
                if prefix.endswith(("`", '"', "'")) and re.match(
                    re.escape(prefix[-1]) + r"\s+(?:is|was)\s+prohibited\b", suffix
                ):
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

    def denied(prefix: str) -> bool:
        clause = _governing_clause(prefix)
        return bool(
            _NEGATION_CUES.search(_NOT_ONLY.sub(" ", clause))
            or re.search(r"\b(?:false|untrue|incorrect)\b", clause)
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

    # B2. ... and bounded evidence is not runtime qualification. The separation
    # must be asserted: a clause that denies it states the opposite of the
    # boundary this check preserves, so mere presence of the wording is not
    # enough.
    separation_claimed = any(
        not denied(supported[: match.start()])
        for match in re.finditer(
            re.escape("qualification is a separate gate"), supported
        )
    )
    assert separation_claimed, (
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
    #    are not met. An unchecked item that names no release-qualification
    #    obligation is an unrelated task, not a release criterion, so it cannot
    #    keep the recorded HOLD honest on its own.
    unmet = [
        line
        for line in release_definition.splitlines()
        if line.strip().startswith("- [ ]")
        and _REQUIRED_QUALIFICATION_GATE.search(line)
    ]
    assert unmet, (
        f"{REASON_UNMET_CRITERIA}: the release definition must still record "
        "unmet qualification criteria"
    )

    # E1. Accept the original wording or the tested current-main distinction,
    # provided the latter is not explicitly denied in its governing clause.
    current_main_phrase = (
        "that proof qualifies same-node messaging only, and share-link bearer "
        "expiry/revocation, cross-node discovery and transport, unread indicators "
        "and persisted read state, and default beta support remain unqualified."
    )
    supported_blocks = _logical_lines(sections.get(_heading_key("Current supported reality"), ""))
    current_main_non_promotion = False
    same_node_promotion = False
    non_promotion_denied = False
    promotion_pattern = re.compile(
        r"\b(?P<capability>" + _UNQUALIFIED_CAPABILITY + r")"
        r"\s+(?:" + _PROMOTION_VERB + r")\s+"
        r"(?:now\s+)?default\s+beta\s+support\b"
    )
    non_promotion_wording = re.compile(r"\bnot\s+default\s+beta\s+support\b")

    for block in supported_blocks:
        for match in re.finditer(re.escape(current_main_phrase), block):
            prefix = block[:match.start()]
            suffix = block[match.end():]
            quoted_denial = prefix.endswith(('"', "'", "`")) and re.match(
                re.escape(prefix[-1]) + r"\s+(?:is|was)\s+(?:false|not\s+true|prohibited)\b",
                suffix,
            )
            if not denied(prefix) and not quoted_denial:
                current_main_non_promotion = True
        # A required non-promotion statement that is explicitly denied is not
        # a non-promotion statement: denying it promotes the capability.
        for match in non_promotion_wording.finditer(block):
            prefix = block[:match.start()]
            suffix = block[match.end():]
            quoted_denial = prefix.endswith(('"', "'", "`")) and re.match(
                re.escape(prefix[-1]) + r"\s+(?:is|was)\s+(?:false|not\s+true|prohibited)\b",
                suffix,
            )
            if denied(prefix) or quoted_denial:
                non_promotion_denied = True
            else:
                current_main_non_promotion = True
        for match in promotion_pattern.finditer(block):
            prefix = block[:match.start()]
            suffix = block[match.end():]
            # A conditional clause states no present posture, so a promotion
            # inside one is a rule, not a claim about the current release.
            if _CONDITIONAL_INTRODUCER.search(
                _governing_clause(prefix)
            ) or _CONDITIONAL_INTRODUCER.search(_clause_suffix(suffix)):
                continue
            quote_pairs = {'"': '"', "'": "'", '`': '`', '“': '”', '‘': '’'}
            closing = quote_pairs.get(prefix[-1:])
            quoted_denial = closing and re.match(
                re.escape(closing) + r"\s+(?:is|was)\s+(?:false|not\s+true|prohibited)\b",
                suffix,
            )
            if not denied(prefix) and not quoted_denial:
                same_node_promotion = True
    assert (
        ("not default beta support" in supported or current_main_non_promotion)
        and not same_node_promotion
        and not non_promotion_denied
    ), (
        f"{REASON_NON_PROMOTION_CLAIM}: Current supported reality must state "
        "that unqualified capabilities are not default Beta support"
    )

    # E2. ... and the rule is stated in its own right.
    assert "without current-main qualification" in not_yet_true, (
        f"{REASON_NON_PROMOTION_RULE}: 'Not yet true / do not assume' must keep "
        "the no-promotion-without-current-main-qualification rule"
    )
