"""Bind the consulting capability audit's checkable claims to the repository.

Follows the precedent in ``tests/architecture/test_published_migration_head_claim.py``:
truth is derived from the repository, never hardcoded, and every assertion
failure names the specific offending text.

The audit is a **dated snapshot**. It states counts that were correct at the
revision it was authored against, and it links into the repository. Three
rules keep both honest:

1. **No absolute machine paths.** A link that targets one developer's checkout
   resolves for that developer and for nobody else.
2. **Every relative link resolves**, with exact case — CI checks out on a
   case-sensitive filesystem, so a link that resolves only because the author's
   filesystem folds case is broken there.
3. **The stated counts are bound to the audited revision.** A snapshot's counts
   are historical facts about the revision it describes, not live values. This
   rule checks them against that revision, so a count that was right stays
   right, and a count that was always wrong fails.

Scope: the audit document. This validator asserts that the document's *static*
claims are true. It does not assert that any capability it describes is
qualified for release, and it does not assert that anything it names works.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_PATH = REPO_ROOT / "docs" / "consulting" / "Codexify_Codebase_Capability_Audit.md"

#: A markdown link target.
LINK_TARGET = re.compile(r"\]\(([^)\s]+)\)")

#: An absolute filesystem path in a link target.
ABSOLUTE_LINK = re.compile(r"\]\((/[^)\s]*)\)")

#: The snapshot header: the revision and the date the audit describes. The
#: header is a blockquote that wraps across lines, so the word "revision" and
#: the commit it names may be separated by a line break and a quote marker.
AUDITED_REVISION = re.compile(
    r"revision[\s>]*\[`(?P<revision>[0-9a-f]{7,40})`\]", re.IGNORECASE
)
AUDITED_DATE = re.compile(r"authored\s+(?P<date>\d{4}-\d{2}-\d{2})", re.IGNORECASE)

#: The countable claims the audit states, each with the derivation that
#: produced it. The derivation is run against the audited revision.
#:
#: Each entry is (claim pattern, derivation). A claim may be stated more than
#: once — the appendix repeats two of them — so every occurrence is checked
#: against the same derivation.
COUNT_CLAIMS: tuple[tuple[str, str], ...] = (
    (
        r"(?P<count>\d+)\s+Python test files",
        "tests_python_files",
    ),
    (
        r"(?P<count>\d+)\s+test/spec files",
        "frontend_test_files",
    ),
    (
        r"(?P<count>\d+)\s+route modules",
        "route_modules",
    ),
    (
        r"(?P<count>\d+)\s+worker modules",
        "worker_modules",
    ),
    (
        r"\((?P<count>\d+)\s+architecture files\)",
        "architecture_files",
    ),
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _tracked_at(revision: str) -> set[str]:
    """Return every path tracked at a revision, relative to the repository root."""
    result = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", revision],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return {path for path in result.stdout.splitlines() if path}


def _count_tests_python_files(paths: set[str]) -> int:
    return sum(1 for path in paths if path.startswith("tests/") and path.endswith(".py"))


def _count_frontend_test_files(paths: set[str]) -> int:
    return sum(
        1
        for path in paths
        if path.startswith("frontend/src/")
        and re.search(r"\.(test|spec)\.[jt]sx?$", path)
    )


def _count_route_modules(paths: set[str]) -> int:
    return sum(
        1
        for path in paths
        if re.fullmatch(r"guardian/routes/[^/]+\.py", path)
    )


def _count_worker_modules(paths: set[str]) -> int:
    return sum(
        1
        for path in paths
        if re.fullmatch(r"guardian/workers/[^/]+\.py", path)
    )


def _count_architecture_files(paths: set[str]) -> int:
    return sum(
        1
        for path in paths
        if path.startswith("docs/architecture/") and path.endswith(".md")
    )


DERIVATIONS = {
    "tests_python_files": _count_tests_python_files,
    "frontend_test_files": _count_frontend_test_files,
    "route_modules": _count_route_modules,
    "worker_modules": _count_worker_modules,
    "architecture_files": _count_architecture_files,
}


def _audited_revision(text: str) -> str:
    """Return the revision the audit states it describes."""
    match = AUDITED_REVISION.search(text)
    assert match is not None, (
        "the capability audit states no audited revision. A snapshot that does "
        "not say which revision it describes cannot be checked — its counts "
        "read as live values and rot."
    )
    return match.group("revision")


def test_capability_audit_has_no_absolute_machine_paths() -> None:
    """No link in the audit may target an absolute filesystem path."""
    text = _read(AUDIT_PATH)
    hits = ABSOLUTE_LINK.findall(text)
    assert not hits, (
        f"the capability audit links to absolute filesystem paths: {sorted(set(hits))}. "
        "An absolute path is specific to one machine and resolves for nobody "
        "else — not in CI, not in a clone, not in a review. Use a "
        "repository-relative link."
    )


def test_capability_audit_links_resolve_with_exact_case() -> None:
    """Every relative link in the audit must resolve, with exact case."""
    tracked = _tracked_files()
    doc_dir = AUDIT_PATH.parent.relative_to(REPO_ROOT)

    missing: list[tuple[str, str]] = []
    for target in _link_targets(_read(AUDIT_PATH)):
        resolved = os.path.normpath(os.path.join(str(doc_dir), target))
        if not _resolves_exactly(tracked, resolved):
            missing.append((target, resolved))

    assert not missing, (
        "the capability audit links to paths that do not exist in the repository "
        f"with exact case: {missing}. A link that resolves only on a "
        "case-insensitive filesystem is broken in CI. Correct the link's case or "
        "point it at a real path."
    )


def test_capability_audit_counts_are_bound_to_the_audited_revision() -> None:
    """Each countable claim must match the repository at the audited revision."""
    text = _read(AUDIT_PATH)
    revision = _audited_revision(text)
    paths = _tracked_at(revision)

    problems: list[str] = []
    for pattern, derivation in COUNT_CLAIMS:
        matches = list(re.finditer(pattern, text))
        assert matches, (
            f"the capability audit states no countable claim matching {pattern!r} — "
            "this check must not pass vacuously"
        )
        actual = DERIVATIONS[derivation](paths)
        for match in matches:
            stated = int(match.group("count"))
            if stated != actual:
                problems.append(
                    f"{match.group(0)!r}: the audit states {stated}, but the "
                    f"repository at {revision[:12]} has {actual}"
                )

    assert not problems, (
        "the capability audit's counts do not match the repository at the "
        f"revision it audits ({revision[:12]}): {problems}. A snapshot's counts "
        "are historical facts about that revision; if they were never right, "
        "the claim is wrong rather than dated."
    )


def test_capability_audit_states_the_revision_it_describes() -> None:
    """The audit must name a revision, and that revision must be reachable.

    A snapshot that does not say which revision it describes cannot be checked:
    its counts read as live values and rot. The revision must also be present
    in the repository, because the counts are verified against it.
    """
    text = _read(AUDIT_PATH)

    date = AUDITED_DATE.search(text)
    assert date is not None, (
        "the capability audit states no as-of date. Without one, its counts read "
        "as present-tense claims about the repository rather than as a snapshot."
    )

    revision = _audited_revision(text)
    exists = subprocess.run(
        ["git", "cat-file", "-e", f"{revision}^{{commit}}"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    ).returncode == 0
    assert exists, (
        f"the capability audit names revision {revision[:12]}, which is not in "
        "the repository. The counts are verified against that revision, so it "
        "must be reachable."
    )


def test_capability_audit_link_resolution_rejects_a_case_mismatched_path() -> None:
    """A link whose case does not match a tracked path must be rejected.

    A validator that only ever passes is not evidence. This pins the
    case-sensitive behaviour in both directions.
    """
    tracked = {"docs/consulting/Codexify_Codebase_Capability_Audit.md"}

    assert _resolves_exactly(tracked, "docs/consulting/Codexify_Codebase_Capability_Audit.md"), (
        "an exactly-matching tracked path must resolve"
    )
    assert not _resolves_exactly(tracked, "docs/Consulting/Codexify_Codebase_Capability_Audit.md"), (
        "a case-mismatched path must not resolve — CI checks out on a "
        "case-sensitive filesystem"
    )


def test_capability_audit_count_binding_rejects_a_wrong_count() -> None:
    """A count that does not match the audited revision must be detected.

    The binding is only evidence if it distinguishes a right count from a wrong
    one. Both directions are pinned here: the count as the audit states it
    agrees with the repository at the audited revision, and a corrupted count
    does not.
    """
    revision = "def1b12a4572a55602d6141ab6d0863508853a42"
    paths = _tracked_at(revision)
    text = _read(AUDIT_PATH)

    for pattern, derivation in COUNT_CLAIMS:
        matches = list(re.finditer(pattern, text))
        assert matches, f"no claim matching {pattern!r}"

        actual = DERIVATIONS[derivation](paths)
        for match in matches:
            assert int(match.group("count")) == actual, (
                f"the audit states {match.group(0)!r} but the repository at "
                f"{revision[:12]} has {actual}"
            )

        # Corrupting one occurrence must break the agreement. A count stated in
        # more than one place is checked in each place, so corrupting one
        # occurrence is enough to make the document disagree with the
        # repository.
        corrupted = text[: match.start()] + re.sub(
            r"\d+", "999", match.group(0)
        ) + text[match.end():]
        corrupted_matches = list(re.finditer(pattern, corrupted))
        assert corrupted_matches
        assert any(
            int(corrupted_match.group("count")) != actual
            for corrupted_match in corrupted_matches
        ), (
            f"corrupting the count in {match.group(0)!r} did not break the "
            "binding — the check is vacuous"
        )


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
        if raw.startswith(("http://", "https://", "mailto:", "/")):
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
