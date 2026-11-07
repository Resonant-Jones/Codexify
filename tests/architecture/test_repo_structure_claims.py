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

#: A token in a section line: either a backtick-quoted span or a bare word.
SPAN_OR_WORD = re.compile(r"`[^`\n]+`|[^\s]+")

#: A path token: one or more segments joined by "/", with an optional trailing
#: "/". A path must contain a separator — that is what distinguishes a path
#: from an ordinary word, so prose is never read as a path.
PATH_TOKEN = re.compile(r"[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*/?")

#: Tokens that may join the paths of one bullet's leading declaration.
DECLARATION_JOINERS = frozenset({"and", "&"})

#: Punctuation that may trail a path token in prose.
TRAILING_PUNCTUATION = ".,;:"

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


def _is_path_token(token: str) -> bool:
    """True when a token names a path rather than ordinary prose.

    A path is one or more segments joined by "/", with an optional trailing
    separator, so ``guardian/``, ``guardian/db/migrations/`` and
    ``docs/architecture/00-current-state.md`` all qualify.

    A path must carry a separator. That is what distinguishes a path from an
    ordinary word: "models/" names a directory, "Local" is prose. Requiring
    the separator is what keeps the rule from reading prose as a path.
    """
    return "/" in token and bool(PATH_TOKEN.fullmatch(token))


def _leading_declaration(line: str) -> list[str]:
    """Return the paths a bullet declares in its leading position.

    A bullet declares its subject in the text that follows the leading dash,
    before any prose begins. The declaration may be quoted (`` `guardian/` ``)
    or unquoted (``guardian/``); both are read, because a contributor who
    writes an unquoted path is naming a path and the validator must see it.

    A declaration may name more than one path, joined by "and".

    Returns an empty list when the bullet declares no path, which the caller
    reports as a malformed bullet rather than skipping.
    """
    body = BULLET.sub("", line, count=1).strip()
    if not body:
        return []

    declared: list[str] = []
    for token in SPAN_OR_WORD.findall(body):
        plain = token.strip("`").strip().rstrip(TRAILING_PUNCTUATION)
        if not plain:
            continue
        if plain.lower() in DECLARATION_JOINERS and declared:
            # A joiner continues the declaration only when another path follows.
            continue
        if not _is_path_token(plain):
            break
        declared.append(plain)
    return declared


def _path_claims(section: str) -> tuple[list[str], list[str]]:
    """Return (path claims, malformed bullets) for the section.

    Every path the section names is a claim and is checked for existence:

    * the paths a bullet declares in its leading position, and
    * any further backtick-quoted path the bullet mentions.

    A bullet that declares no path at all is returned as malformed. It is not
    skipped: a bullet whose subject cannot be read is a bullet whose claims
    cannot be checked, so the caller must fail on it explicitly.
    """
    claims: list[str] = []
    malformed: list[str] = []

    for line in section.splitlines():
        stripped = line.strip()
        if not stripped or not BULLET.match(line):
            continue

        declared = _leading_declaration(line)
        if not declared:
            malformed.append(stripped)
            continue

        claims.extend(declared)

        # Further quoted paths in the same bullet are additional claims.
        for span in BACKTICK_SPAN.findall(line):
            span = span.strip()
            if span and span not in declared and _is_path_token(span):
                claims.append(span)

    return claims, malformed


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
    claims, malformed = _path_claims(section)

    assert not malformed, (
        f"`{STRUCTURE_HEADING}` has bullets that declare no path: {malformed}. "
        "Every bullet must begin with the path it names, quoted or not, so its "
        "claims can be checked."
    )

    assert claims, (
        f"`{STRUCTURE_HEADING}` names no paths — this check must not pass vacuously"
    )

    missing = [claim for claim in claims if not _exists_as_path(tracked, claim)]
    assert not missing, (
        f"`{STRUCTURE_HEADING}` names paths that do not exist in the repository: "
        f"{sorted(set(missing))}. Remove the entry or point it at a real path."
    )


def test_repo_structure_claims_parse_valid_and_malformed_bullets() -> None:
    """The claim parser must read a declared path and reject an undeclared one.

    A parser-backed rule is only as good as the inputs it is exercised with.
    Testing one valid input alone leaves a malformed input silently skipped —
    which is how a bullet that names a directory the validator never reads
    reaches the document. Both shapes are therefore pinned here.
    """
    # A valid bullet: the leading declaration is the subject, and a further
    # quoted path in the same bullet is an additional claim.
    claims, malformed = _path_claims(
        "- `guardian/` - Main backend package, see `guardian/routes/`.\n"
    )
    assert not malformed, f"a well-formed bullet was reported malformed: {malformed}"
    assert claims == ["guardian/", "guardian/routes/"], (
        f"expected the declared path and the further quoted path, got {claims}"
    )

    # A bullet whose leading text is not a path declaration names no path.
    # It must be reported, not silently dropped.
    claims, malformed = _path_claims("- Local model storage\n")
    assert claims == [], f"a prose-only bullet produced claims: {claims}"
    assert malformed == ["- Local model storage"], (
        f"a prose-only bullet must be reported as malformed, got {malformed}"
    )

    # An unquoted path is still a path. It must be read as the subject so
    # that its existence is checked.
    claims, malformed = _path_claims("- models/ - Local model storage\n")
    assert not malformed, f"an unquoted path bullet was reported malformed: {malformed}"
    assert claims == ["models/"], (
        f"an unquoted leading path must be read as the subject, got {claims}"
    )

    # A later quoted path is an additional claim, never a replacement for the
    # subject.
    claims, malformed = _path_claims(
        "- models/ - Local model storage, see `backend/`\n"
    )
    assert not malformed, f"an unquoted path bullet was reported malformed: {malformed}"
    assert claims == ["models/", "backend/"], (
        f"expected the subject and the additional claim, got {claims}"
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

    named = {claim.split("/")[0] for claim in _path_claims(section)[0]}
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
