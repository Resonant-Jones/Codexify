"""Bind the architecture KB index's checkable claims to the repository and to release truth.

The KB index (``docs/architecture/README.md``) is the entry point to the
architecture knowledge base. It makes two kinds of claim that can be checked
mechanically:

* **Link claims.** Every relative link points at another document. A link that
  resolves on the author's filesystem but not in CI is a false claim.
* **Status claims.** It states, in prose, what the qualification registry
  projects per surface, and what the release posture is.

Follows the precedent in ``tests/architecture/test_published_migration_head_claim.py``:
truth is derived from the repository, never hardcoded, and every assertion
failure names the specific offending text.

Scope: the KB index and the documents it is reconciled against. This validator
asserts that the index's *static* claims are true. It does not assert that any
surface it names is qualified for release, and it does not assert that anything
documented here runs.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
KB_INDEX_PATH = REPO_ROOT / "docs" / "architecture" / "README.md"
CURRENT_STATE_PATH = REPO_ROOT / "docs" / "architecture" / "00-current-state.md"
REGISTRY_PATH = REPO_ROOT / "docs" / "qualification" / "registry.json"

#: A markdown link target inside the KB index.
LINK_TARGET = re.compile(r"\]\(([^)\s]+)\)")

#: A release-gate posture, as both documents state it: "release gate remains
#: `HOLD`". The posture word is captured so the two documents can be compared
#: rather than the phrase being matched literally — the surrounding prose is
#: rewritten regularly, the posture is the claim.
RELEASE_GATE = re.compile(
    r"release gate remains\s+`(?P<posture>[A-Z]+)`", re.IGNORECASE
)

#: A qualification surface's status, as the KB index states it:
#: "``supported-compose-stock`` as ``PASS``". Surfaces may be listed in a
#: conjunction ("``a`` and ``b`` as ``HOLD``"), so every surface named before
#: the status word shares that status. The capture therefore collects the whole
#: run of surfaces, and the caller attributes the status to each of them.
SURFACE_STATUS = re.compile(
    r"(?P<surfaces>`[A-Za-z0-9._-]+`(?:\s+and\s+`[A-Za-z0-9._-]+`)*)"
    r"\s+as\s+`(?P<status>PASS|HOLD)`"
)


#: A heading in the KB index.
HEADING = re.compile(r"^##\s+(?P<title>.+?)\s*$", re.MULTILINE)

#: The one section title the KB index must carry exactly once. Two sections
#: with the same title give a reader two different "Doc Map"s and make an
#: anchor to the section ambiguous.
DOC_MAP_TITLE = "Doc Map"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


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


def _link_targets(text: str) -> list[str]:
    """Return the relative link targets in a document, in order."""
    targets: list[str] = []
    for raw in LINK_TARGET.findall(text):
        if raw.startswith(("http://", "https://", "mailto:")):
            continue
        target = raw.split("#")[0]
        if target:
            targets.append(target)
    return targets


def _resolves_exactly(tracked: set[str], path: str) -> bool:
    """True when a path is a tracked file, or a directory holding tracked files.

    The comparison is case-sensitive. CI checks out on a case-sensitive
    filesystem, so a link that resolves only because the author's filesystem
    folds case is broken there.
    """
    normalised = path.rstrip("/")
    if normalised in tracked:
        return True
    prefix = f"{normalised}/"
    return any(candidate.startswith(prefix) for candidate in tracked)


def _resolve(index_dir: Path, target: str) -> str:
    """Resolve a link target to a repository-relative path.

    The result stays relative to the repository root, so it can be compared
    against git's tracked paths directly. An absolute filesystem path would
    not compare equal to a tracked path and would make every link look broken.
    """
    return os.path.normpath(os.path.join(str(index_dir), target))


def test_kb_index_links_resolve_with_exact_case() -> None:
    """Every relative link in the KB index must resolve, with exact case."""
    tracked = _tracked_files()
    index_dir = KB_INDEX_PATH.parent.relative_to(REPO_ROOT)

    missing: list[tuple[str, str]] = []
    for target in _link_targets(_read(KB_INDEX_PATH)):
        resolved = _resolve(index_dir, target)
        if not _resolves_exactly(tracked, resolved):
            missing.append((target, resolved))

    assert not missing, (
        "the KB index links to paths that do not exist in the repository with "
        f"exact case: {missing}. A link that resolves only on a case-insensitive "
        "filesystem is broken in CI. Correct the link's case or point it at a "
        "real path."
    )


def test_kb_index_has_exactly_one_doc_map_section() -> None:
    """The KB index must carry exactly one `## Doc Map` section."""
    titles = [match.group("title") for match in HEADING.finditer(_read(KB_INDEX_PATH))]
    doc_maps = [title for title in titles if title == DOC_MAP_TITLE]

    assert len(doc_maps) == 1, (
        f"the KB index has {len(doc_maps)} `{DOC_MAP_TITLE}` sections; it must "
        f"have exactly one. Two sections with the same title give a reader two "
        "different maps and make the section anchor ambiguous."
    )


def test_kb_index_states_the_release_gate_and_agrees_with_release_truth() -> None:
    """The KB index must state the release gate, and agree with release truth."""
    index_text = _read(KB_INDEX_PATH)
    current_text = _read(CURRENT_STATE_PATH)

    index_gates = {match.group("posture").upper() for match in RELEASE_GATE.finditer(index_text)}
    truth_gates = {match.group("posture").upper() for match in RELEASE_GATE.finditer(current_text)}

    assert truth_gates, (
        "00-current-state.md states no release-gate posture — the validator's "
        "source of truth for the gate is missing"
    )
    assert index_gates, (
        "the KB index states no release-gate posture. A reader who arrives at "
        "the KB index sees per-surface verdicts and nothing about the release "
        "as a whole. State the gate explicitly."
    )
    assert index_gates == truth_gates, (
        f"the KB index states the release gate as {sorted(index_gates)} but "
        f"00-current-state.md states {sorted(truth_gates)}. Release truth is "
        "00-current-state.md; the index must agree with it."
    )


def test_kb_index_names_every_registry_surface_with_an_agreeing_status() -> None:
    """Every surface the registry projects must be named, with an agreeing status."""
    registry = json.loads(_read(REGISTRY_PATH))
    surfaces = registry["qualifications"]
    assert surfaces, (
        "the qualification registry projects no surfaces — this check must not "
        "pass vacuously"
    )

    index_text = _read(KB_INDEX_PATH)

    stated: dict[str, set[str]] = {}
    for match in SURFACE_STATUS.finditer(index_text):
        status = match.group("status")
        for surface in re.findall(r"`([A-Za-z0-9._-]+)`", match.group("surfaces")):
            stated.setdefault(surface, set()).add(status)

    problems: list[str] = []
    for surface, entry in sorted(surfaces.items()):
        expected = entry["status"]
        if surface not in stated:
            problems.append(
                f"{surface}: not named in the KB index (registry status {expected})"
            )
            continue
        found = stated[surface]
        if expected not in found:
            problems.append(
                f"{surface}: KB index states {sorted(found)} but the registry "
                f"records {expected}"
            )

    assert not problems, (
        "the KB index does not reconcile with the qualification registry: "
        f"{problems}. The registry is generated and drift-gated; it is the "
        "machine-readable authority for a surface's status."
    )


def test_kb_index_link_resolution_rejects_a_case_mismatched_path() -> None:
    """A link whose case does not match a tracked path must be rejected.

    A validator that only ever passes is not evidence. This pins the
    case-sensitive behaviour in both directions: an exactly-matching path
    resolves, and a case-mismatched one does not.
    """
    tracked = {"docs/Collaborators/paul/README.md"}

    assert _resolves_exactly(tracked, "docs/Collaborators/paul/README.md"), (
        "an exactly-matching tracked path must resolve"
    )
    assert not _resolves_exactly(tracked, "docs/collaborators/paul/README.md"), (
        "a case-mismatched path must not resolve — CI checks out on a "
        "case-sensitive filesystem"
    )
    assert not _resolves_exactly(tracked, "docs/Collaborators/paul/other.md"), (
        "a path that exists only under a different case must not resolve"
    )
    assert _resolves_exactly(tracked, "docs/Collaborators/paul"), (
        "a directory holding tracked files must resolve"
    )
