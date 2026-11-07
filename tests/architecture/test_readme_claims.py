"""Bind the README's checkable claims to the repository's actual state.

Follows the precedent in ``tests/architecture/test_published_migration_head_claim.py``:
truth is derived from the repository, never hardcoded, and every assertion failure
names the specific offending text so a reader knows exactly what is wrong.

Scope: the README only. This validator asserts that the README's *static* claims are
true. It does not assert that the documented startup works — runtime proof belongs to
the release lane's supported-startup qualification.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
README_PATH = REPO_ROOT / "README.md"

#: The removed RAG upload endpoint. ``guardian/guardian_api.py`` carries the removal
#: note ("Removed redundant /upload-chat endpoint; use guardian/routes/migration.py
#: instead") and no route mounts it.
#:
#: This matches on a path-segment boundary rather than as a bare substring: a bare
#: ``"/upload-chat" in text`` check also matches the live sibling endpoint
#: ``/upload-chatgpt-export`` (``guardian/routes/migration.py``), which is a different
#: route and must remain documentable.
REMOVED_UPLOAD_CHAT_ROUTE = re.compile(r"/upload-chat(?![A-Za-z0-9_-])")

#: Every ``pip install -r <path>`` target the README names must exist on disk.
PIP_INSTALL_TARGET = re.compile(r"pip install -r\s+(\S+)")

#: The Documentation Map must remain a validated, navigable list of real documents.
DOC_MAP_HEADING = "## Documentation Map"
DOC_MAP_MIN_ENTRIES = 12
DOC_MAP_BULLET = re.compile(r"^\s*-\s+")
DOC_MAP_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")

#: An absolute path into a specific user's home directory.
USER_HOME_PATH = re.compile(r"/(?:Users|home)/[^/\s]+/")


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


def test_pip_install_targets_exist() -> None:
    """Every ``pip install -r <path>`` in the README must name a real file."""
    text = _readme()
    targets = PIP_INSTALL_TARGET.findall(text)
    assert targets, (
        "no `pip install -r` targets found in README.md — this check must not "
        "pass vacuously"
    )
    for target in targets:
        resolved = (REPO_ROOT / target).resolve()
        assert resolved.is_file(), (
            f"README instructs `pip install -r {target}` but no such file exists "
            f"(resolved to {resolved})"
        )


def test_documentation_map_is_present_and_fully_validated() -> None:
    """The Documentation Map must exist, stay populated, and every entry must resolve."""
    text = _readme()
    section = _section(text, DOC_MAP_HEADING)
    assert section.strip(), (
        f"README.md has no `{DOC_MAP_HEADING}` section — the document map must be "
        "present, and an absent section must not read as 'nothing to validate'"
    )

    bullets = [line for line in section.splitlines() if DOC_MAP_BULLET.match(line)]
    assert len(bullets) >= DOC_MAP_MIN_ENTRIES, (
        f"`{DOC_MAP_HEADING}` has {len(bullets)} entries; expected at least "
        f"{DOC_MAP_MIN_ENTRIES}. Removing entries must fail this check rather "
        "than silently shrink the map."
    )

    targets: list[str] = []
    for bullet in bullets:
        match = DOC_MAP_LINK.search(bullet)
        assert match is not None, (
            "Documentation Map entry is not a markdown link and would be skipped: "
            f"{bullet.strip()!r}"
        )
        targets.append(match.group(1))

    assert len(targets) == len(bullets), (
        f"parsed {len(targets)} links from {len(bullets)} bullets — an entry "
        "changed format and stopped being validated"
    )

    tracked = _tracked_files()
    for target in targets:
        assert target in tracked, (
            f"Documentation Map link target is not an existing tracked file: "
            f"{target!r}"
        )


def test_readme_has_no_user_home_absolute_path() -> None:
    """The README must not hardcode a path inside one user's home directory."""
    hits = USER_HOME_PATH.findall(_readme())
    assert not hits, (
        f"README.md contains a user-home absolute path: {hits}. Use a placeholder "
        "such as /path/to/Codexify."
    )


def test_removed_upload_chat_route_is_not_described() -> None:
    """The removed ``/upload-chat`` route must not be described as an endpoint."""
    hits = REMOVED_UPLOAD_CHAT_ROUTE.findall(_readme())
    assert not hits, (
        "README.md describes the removed `/upload-chat` endpoint. It was removed at "
        "guardian/guardian_api.py:1862; re-adding it requires updating both the "
        "route and this assertion."
    )


def test_upload_chat_boundary_does_not_match_the_live_sibling_endpoint() -> None:
    """Guard the boundary itself against regressing into a substring check."""
    assert REMOVED_UPLOAD_CHAT_ROUTE.search("/upload-chat") is not None
    assert REMOVED_UPLOAD_CHAT_ROUTE.search("`/upload-chat` returns 503") is not None
    assert REMOVED_UPLOAD_CHAT_ROUTE.search("/upload-chatgpt-export") is None
    assert REMOVED_UPLOAD_CHAT_ROUTE.search("/upload-chatgpt_export") is None
