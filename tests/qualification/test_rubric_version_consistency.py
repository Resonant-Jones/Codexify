"""Tests that a rubric's declared version is stated once, consistently.

A rubric states its version twice: as a number in the machine-readable
metadata block, and as the number in the document's `## Version` heading.
The metadata is what a run receipt binds to; the heading is what a reader
sees. When they disagree, a receipt can declare a version that no document
claims, and nothing in the tooling notices.

This checks the repository's own rubrics, so it is a property of the
repository rather than of a fixture.
"""

from __future__ import annotations

import re
from pathlib import Path

from scripts.qualification.lib.parsing import (
    QualificationParseError,
    parse_rubric,
)


ROOT = Path(__file__).resolve().parents[2]
RUBRICS_DIR = ROOT / "docs/qualification/rubrics"

_VERSION_HEADING = re.compile(r"^## Version\s*$", re.MULTILINE)
_VERSION_VALUE = re.compile(r"^`(\d+)`\s*$", re.MULTILINE)


def _documented_version(path: Path) -> int | None:
    """Return the version stated in the rubric's `## Version` heading."""
    text = path.read_text(encoding="utf-8")
    heading = _VERSION_HEADING.search(text)
    if heading is None:
        return None
    value = _VERSION_VALUE.search(text, heading.end())
    if value is None:
        return None
    return int(value.group(1))


def test_every_rubric_states_one_version() -> None:
    """Each rubric's heading version must equal its metadata version."""
    mismatched: list[str] = []
    unstated: list[str] = []

    for path in sorted(RUBRICS_DIR.glob("*.md")):
        try:
            rubric = parse_rubric(path, ROOT)
        except QualificationParseError:
            # The rubrics README is a template, not a rubric.
            continue

        documented = _documented_version(path)
        if documented is None:
            unstated.append(path.name)
            continue
        if documented != rubric.version:
            mismatched.append(
                f"{path.name}: heading says {documented}, metadata says {rubric.version}"
            )

    assert not unstated, (
        "rubrics without a '## Version' heading stating a version: "
        + "; ".join(unstated)
    )
    assert not mismatched, (
        "rubrics whose heading version differs from their metadata version: "
        + "; ".join(mismatched)
    )
