"""Bind the README's ``## Repo Structure`` section to the repository's actual shape.

Follows the precedent in ``tests/architecture/test_published_migration_head_claim.py``:
truth is derived from the repository, never hardcoded, and every assertion failure
names the specific offending text so a reader knows exactly what is wrong.

Three rules are enforced:

1. **No phantom entries.** Every path named in the section must exist in the
   repository. This is the rule that catches a bullet naming a directory that
   was never there.
2. **Every first-party surface is accounted for.** The set of top-level
   directories holding first-party source files is derived from the repository.
   Each one must be either named in the section or listed in
   ``EXCLUDED_SURFACES`` with a non-empty reason. An exclusion whose directory
   has since been removed is stale and must be deleted, not left behind.
3. **No volatile counts.** The section states no file count, directory count, or
   percentage. A hand-maintained number is itself a drift source.

Scope: the README's structure section only. This validator asserts that the
section's *static* claims are true. It does not assert that anything documented
here runs, starts, or is qualified for release.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
README_PATH = REPO_ROOT / "README.md"
STRUCTURE_HEADING = "## Repo Structure"

#: File extensions that make a path count as first-party source.
SOURCE_EXTENSIONS = frozenset(
    {".py", ".ts", ".tsx", ".js", ".mjs", ".sh", ".rs", ".swift", ".sql", ".yaml", ".yml"}
)

#: Path segments that mark vendored, generated, or installed trees. A path
#: containing any of these segments never contributes to a first-party surface.
EXCLUDED_PATH_SEGMENTS = frozenset({"node_modules", "vendor", "dist", "build"})

#: Substrings that mark a path as a packaged distribution rather than source.
EXCLUDED_PATH_MARKERS = ("egg-info",)

#: Top-level directories that are deliberately absent from the README's
#: structure section, each with the reason it is excluded. Every entry must
#: carry a non-empty reason, and every excluded directory must still exist —
#: an exclusion for a directory that has since been removed is stale.
EXCLUDED_SURFACES: dict[str, str] = {
    "browser_host_candidates": "candidate implementations, not the selected surface",
    ".playwright-cli": "Playwright CLI tool residue",
    ".playwright-tmp": "Playwright scratch output",
    ".playwright-mcp": "Playwright MCP tool residue",
    "GitHub": "duplicate of `.github/workflows/`",
    "Codexify-Beta": "beta snapshot copy",
    "archive": "retired legacy module",
    "codex_memory": "single-file helper",
    "codex_ralph_loop": "single-file loop helper",
    "codex_tasks": "task-definition corpus, not runtime code",
    "cypress": "frontend end-to-end config only",
    "data": "data fixtures only",
    "notion_codex_templates": "template files only",
    "requirements": "dependency inputs only",
}

#: A backtick-quoted span inside the section.
BACKTICK_SPAN = re.compile(r"`([^`\n]+)`")

#: A bullet in the section: a leading dash, then the path the bullet names.
BULLET = re.compile(r"^\s*-\s+")

#: A numeric quantity immediately followed by a count noun. A bare number in
#: prose is not a count claim and is deliberately not matched.
#:
#: "paths" is included because the finding this task repairs was a section
#: that "named 9 paths" — a path count is a directory count. The separator is
#: ``\s*`` rather than the Task Spec's example ``\s+`` so that "50%" is caught
#: as well as "50 percent".
VOLATILE_COUNT = re.compile(
    r"\b\d[\d,]*\s*(?:files?|directories|dirs|paths?|percent|%)", re.IGNORECASE
)


def _readme() -> str:
    return README_PATH.read_text(encoding="utf-8")


def _section(text: str, heading: str) -> str:
    """Return the body of a ``##`` section, or an empty string when absent."""
    match = re.search(
        rf"^{re.escape(heading)}\s*$(.*?)(?=^## |\Z)",
        text,
        flags=re.MULTILINE | re.DOTALL,
    )
    return match.group(1) if match else ""


def _tracked_files() -> set[str]:
    """Return every path tracked by git, relative to the repository root."""
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return {path for path in result.stdout.split("\0") if path}


def _is_excluded_path(path: str) -> bool:
    """True when a tracked path belongs to a vendored, generated, or installed tree."""
    segments = path.split("/")
    if any(segment in EXCLUDED_PATH_SEGMENTS for segment in segments):
        return True
    return any(marker in path for marker in EXCLUDED_PATH_MARKERS)


def _first_party_surfaces(tracked: set[str]) -> set[str]:
    """Derive the top-level directories that contain first-party source files."""
    surfaces: set[str] = set()
    for path in tracked:
        parts = path.split("/")
        if len(parts) < 2:
            # A tracked file at the repository root is not a directory.
            continue
        if _is_excluded_path(path):
            continue
        if Path(path).suffix.lower() not in SOURCE_EXTENSIONS:
            continue
        surfaces.add(parts[0])
    return surfaces


def _path_claims(section: str) -> list[str]:
    """Return every path the section names.

    A claim is any backtick-quoted span that contains a path separator, plus
    the first backtick-quoted span of each bullet (the subject of the bullet,
    which may be written without a trailing separator).
    """
    claims: list[str] = []
    for line in section.splitlines():
        if not BULLET.match(line):
            continue
        spans = BACKTICK_SPAN.findall(line)
        if not spans:
            continue
        first = spans[0].strip()
        if first:
            claims.append(first)
        claims.extend(span.strip() for span in spans[1:] if "/" in span)
    return claims


def _exists_as_path(tracked: set[str], claim: str) -> bool:
    """True when the claimed path is a tracked file or a directory holding tracked files."""
    normalised = claim.rstrip("/")
    if not normalised:
        return False
    if normalised in tracked:
        return True
    prefix = f"{normalised}/"
    return any(path.startswith(prefix) for path in tracked)


def test_repo_structure_named_paths_exist() -> None:
    """Every path named in the structure section must exist in the repository."""
    section = _section(_readme(), STRUCTURE_HEADING)
    assert section.strip(), (
        f"README.md has no `{STRUCTURE_HEADING}` section — the structure section "
        "must be present, and an absent section must not read as 'nothing to validate'"
    )

    tracked = _tracked_files()
    claims = _path_claims(section)
    assert claims, (
        f"`{STRUCTURE_HEADING}` names no paths — this check must not pass vacuously"
    )

    missing = [claim for claim in claims if not _exists_as_path(tracked, claim)]
    assert not missing, (
        f"`{STRUCTURE_HEADING}` names paths that do not exist in the repository: "
        f"{sorted(set(missing))}. Remove the entry or point it at a real path."
    )


def test_repo_structure_accounts_for_every_first_party_surface() -> None:
    """Every first-party top-level surface must be named in the section or excluded with a reason."""
    section = _section(_readme(), STRUCTURE_HEADING)
    assert section.strip(), (
        f"README.md has no `{STRUCTURE_HEADING}` section — the structure section "
        "must be present, and an absent section must not read as 'nothing to validate'"
    )

    tracked = _tracked_files()
    surfaces = _first_party_surfaces(tracked)
    assert surfaces, (
        "no first-party surfaces derived from the repository — this check must not "
        "pass vacuously"
    )

    named = {claim.split("/")[0] for claim in _path_claims(section)}
    excluded = {key.strip("/") for key in EXCLUDED_SURFACES}

    unaccounted = sorted(surfaces - named - excluded)
    assert not unaccounted, (
        "first-party source directories are neither named in "
        f"`{STRUCTURE_HEADING}` nor excluded with a reason: {unaccounted}. Name each "
        "one, or add it to EXCLUDED_SURFACES with the reason it is deliberately "
        "absent."
    )

    for key, reason in EXCLUDED_SURFACES.items():
        assert reason.strip(), (
            f"EXCLUDED_SURFACES[{key!r}] has no reason — an exclusion without a "
            "reason is itself a failure"
        )
        assert _exists_as_path(tracked, key), (
            f"EXCLUDED_SURFACES[{key!r}] names a directory that no longer exists — "
            "the exclusion is stale and must be deleted, not left behind"
        )


def test_repo_structure_states_no_volatile_counts() -> None:
    """The structure section must state no file count, directory count, or percentage."""
    section = _section(_readme(), STRUCTURE_HEADING)
    assert section.strip(), (
        f"README.md has no `{STRUCTURE_HEADING}` section — the structure section "
        "must be present, and an absent section must not read as 'nothing to validate'"
    )

    hits = VOLATILE_COUNT.findall(section)
    assert not hits, (
        f"`{STRUCTURE_HEADING}` states a count: {hits}. A hand-maintained number is "
        "itself a drift source — describe the surface by responsibility instead."
    )
