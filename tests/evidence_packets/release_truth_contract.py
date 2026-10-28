"""Shared release-truth contract for Guardian evidence-packet tests.

`docs/architecture/00-current-state.md` is the canonical release authority.
These helpers read that document's text and assert its release-boundary
semantics, so the protection survives rewording of the document while still
failing when the boundary itself is removed.

This module is test-only and side-effect free: it never reads the filesystem,
mutates a document, launches a subprocess, or depends on application runtime
state. Callers pass the canonical document's text in.
"""

from __future__ import annotations


def _document_sections(text: str) -> dict[str, str]:
    """Split a release-truth document into its heading-delimited sections.

    Section-scoped inspection keeps each assertion anchored to the part of the
    document that actually owns a statement, instead of matching prose
    anywhere in the file.
    """
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            sections[current] = []
        elif current is not None:
            sections[current].append(line)
    return {name: "\n".join(body) for name, body in sections.items()}


def _normalized(text: str) -> str:
    """Collapse wrapping and casing so neither can decide a result."""
    return " ".join(text.split()).lower()


def assert_current_release_truth(current: str) -> None:
    """Assert the canonical current-state document states the release boundary.

    Establishes, section by section:

    A. Interpretation Rule — the document identifies release readiness as
       part of its authority.
    B. Supported Reality — bounded implementation evidence is distinguished
       from complete runtime qualification.
    C. Release Posture — the recorded release gate remains HOLD.
    D. Qualification — the release definition retains unmet criteria.
    E. Product-Scope Boundary — capabilities without current-main
       qualification cannot silently become default Beta support.
    """
    sections = _document_sections(current)
    interpretation = _normalized(sections.get("Interpretation rule", ""))
    phase = _normalized(sections.get("Current phase", ""))
    supported = _normalized(sections.get("Current supported reality", ""))
    not_yet_true = _normalized(sections.get("Not yet true / do not assume", ""))
    release_definition = sections.get("Release definition right now", "")

    # A. The document is authoritative for release readiness.
    assert "release readiness" in interpretation

    # B. Bounded implementation evidence is not release qualification.
    assert "bounded evidence" in supported
    assert "qualification is a separate gate" in supported

    # C. The recorded release gate is still HOLD.
    assert "release gate remains `hold`" in phase

    # D. The release definition still records qualification criteria that
    #    are not met.
    unmet = [
        line
        for line in release_definition.splitlines()
        if line.strip().startswith("- [ ]")
    ]
    assert (
        unmet
    ), "the release definition must still record unmet qualification criteria"

    # E. Capabilities without current-main qualification are not silently
    #    promoted to default Beta support.
    assert "without current-main qualification" in not_yet_true
    assert "not default beta support" in supported
