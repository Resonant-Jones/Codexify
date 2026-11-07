"""Bind the repository's beta changelog to the order its sections are in.

Follows the precedent in ``tests/architecture/test_published_migration_head_claim.py``:
truth is derived from the repository, never hardcoded, and every assertion
failure names the specific offending text.

Two rules:

1. **The beta changelog's dated sections are in date order, newest first.** A
   mechanism that appends leaves the file permanently sorted wrong.
2. **The beta changelog's generator inserts rather than appends.** This is the
   *prevention* for rule 1: a test that only reads the produced file cannot
   stop the next run from appending a section out of order.

The `CHANGELOG.md` version-link and release-truth rules that complete this
task's scope depend on the decision about what `CHANGELOG.md` is — whether it
is still the repository's release artifact, or a relic of a release process
that was never executed. They follow in a separate change once that decision
is recorded.
"""

from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BETA_CHANGELOG_PATH = REPO_ROOT / "CHANGELOG.beta.md"
SENTINEL_PATH = REPO_ROOT / "scripts" / "release" / "beta_release_sentinel.py"

#: A dated section heading in a changelog.
SECTION_HEADING = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2})\s*$", re.MULTILINE)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _section_dates(text: str) -> list[str]:
    """Return the dates of a changelog's sections, in file order."""
    return [match.group(1) for match in SECTION_HEADING.finditer(text)]


def _load_sentinel():
    """Import the beta release sentinel module by path."""
    spec = importlib.util.spec_from_file_location(
        "beta_release_sentinel", SENTINEL_PATH
    )
    assert spec is not None and spec.loader is not None, (
        f"could not load {SENTINEL_PATH}"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["beta_release_sentinel"] = module
    spec.loader.exec_module(module)
    return module


def test_beta_changelog_sections_are_in_date_order() -> None:
    """The beta changelog's sections must be newest first."""
    dates = _section_dates(_read(BETA_CHANGELOG_PATH))

    assert dates, (
        "CHANGELOG.beta.md has no dated sections — this check must not pass "
        "vacuously"
    )

    out_of_order = [
        (dates[index], dates[index + 1])
        for index in range(len(dates) - 1)
        if dates[index] < dates[index + 1]
    ]
    assert not out_of_order, (
        f"CHANGELOG.beta.md's sections are not in date order: {out_of_order}. "
        f"The file reads {dates}. A reader looking for the most recent change "
        "must not have to read to the end."
    )


def test_beta_changelog_generator_inserts_rather_than_appends() -> None:
    """The generator must insert a new section in date order.

    This is the prevention for the ordering rule. A test that only reads the
    file the generator produced cannot stop the next run from appending a
    section out of order — only the generator's behaviour can.
    """
    sentinel = _load_sentinel()

    with tempfile.TemporaryDirectory(prefix="changelog-generator-") as tmp:
        path = Path(tmp) / "CHANGELOG.beta.md"
        path.write_text(
            "# Beta Changelog\n\nEvidence-led beta readiness changes only.\n\n"
            "## 2026-05-15\n\n### Evidence\n- older entry\n",
            encoding="utf-8",
        )

        # A newer date must land FIRST.
        sentinel.update_changelog(path, "2026-11-07", ["newest"], ["b"], ["w"])
        dates = _section_dates(path.read_text(encoding="utf-8"))
        assert dates == ["2026-11-07", "2026-05-15"], (
            f"a newer date did not land first: {dates}. The generator appends "
            "instead of inserting, so the newest section ends up last."
        )

        # An older date must land AFTER the newer one, not at the end.
        sentinel.update_changelog(path, "2026-01-01", ["oldest"], ["b"], ["w"])
        dates = _section_dates(path.read_text(encoding="utf-8"))
        assert dates == ["2026-11-07", "2026-05-15", "2026-01-01"], (
            f"an older date was not inserted in order: {dates}. The generator "
            "appends instead of inserting."
        )

        # The same date must replace its section, not duplicate it.
        sentinel.update_changelog(path, "2026-11-07", ["updated"], ["b"], ["w"])
        text = path.read_text(encoding="utf-8")
        dates = _section_dates(text)
        assert dates.count("2026-11-07") == 1, (
            f"a same-date section was duplicated: {dates}"
        )
        assert "updated" in text, "the same-date section was not replaced"
        assert "newest" not in text, "the replaced section's content survived"
