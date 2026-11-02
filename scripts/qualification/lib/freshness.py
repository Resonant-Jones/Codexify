"""Compute qualification freshness from repository history.

`docs/qualification/README.md` states the rule directly:

> Qualification is commit-bound. A previous PASS does not automatically
> qualify a later commit.
>
> The registry should distinguish: `current`, `stale`, `superseded`.
> A run becomes `stale` when meaningful changes touch its qualification
> surface. A later run may supersede it.

That rule is implemented here, and only here, so the generator and the
validator cannot drift apart in their interpretation of it.

The computation has three inputs:

* the commit a run receipt tested;
* the rubric's `surface_paths`, the repository paths whose changes make a
  run's evidence unrepresentative of current code;
* the current repository tip, which is the revision the registry describes.

A run is `current` when the tip is the tested commit itself, or when no path
in the surface changed between the tested commit and the tip. It is `stale`
when the surface moved under it. It is `superseded` when a later run for the
same qualification supersedes it.

Surface matching uses `git diff --name-only` between two commits and a glob
matcher restricted to the rubric's declared surface. A rubric with no
declared surface is treated as having an empty surface: its runs can only be
`current` when the tip equals the tested commit, because there is no way to
prove that nothing meaningful changed.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from scripts.qualification.lib.parsing import Rubric, RunReceipt


@dataclass(frozen=True)
class GitHistory:
    """Read-only access to the repository's commit graph."""

    repo_root: Path

    def _run(self, args: Sequence[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            check=False,
        )

    def resolve_commit(self, revision: str) -> str | None:
        """Return the full SHA for `revision`, or None when unknown."""
        result = self._run(["rev-parse", "--verify", f"{revision}^{{commit}}"])
        if result.returncode != 0:
            return None
        sha = result.stdout.strip()
        return sha or None

    def commit_exists(self, sha: str) -> bool:
        """Return whether `sha` names a commit in this repository."""
        return self.resolve_commit(sha) is not None

    def changed_paths(self, older: str, newer: str) -> list[str] | None:
        """Return repository paths changed between two commits.

        Returns None when the comparison cannot be performed, which callers
        must treat as "freshness unknown" rather than "freshness current".
        """
        result = self._run(["diff", "--name-only", older, newer])
        if result.returncode != 0:
            return None
        return [line for line in result.stdout.splitlines() if line.strip()]

    def is_ancestor(self, older: str, newer: str) -> bool:
        """Return whether `older` is an ancestor of `newer`.

        A revision that cannot be resolved is reported as not an ancestor.
        `git merge-base --is-ancestor` exits 1 when the revisions are
        unrelated and 128 when a revision is unresolvable; both mean the
        older revision is not part of the newer one's lineage, and neither
        depends on which objects happen to exist locally.
        """
        result = self._run(["merge-base", "--is-ancestor", older, newer])
        return result.returncode == 0


def match_surface(paths: Sequence[str], surface_paths: Sequence[str]) -> list[str]:
    """Return the paths from `paths` that fall inside `surface_paths`.

    Matching is performed per path segment so that a surface pattern like
    `guardian/routes/**` covers nested files, while `frontend/src/*` covers
    only direct children. `*` never matches across a segment boundary and
    `**` matches any number of segments.
    """
    matched: list[str] = []
    for path in paths:
        if any(_glob_matches(surface, path) for surface in surface_paths):
            matched.append(path)
    return matched


def _glob_matches(pattern: str, path: str) -> bool:
    """Return whether a repository path matches one glob pattern."""
    pattern_parts = [part for part in pattern.split("/") if part]
    path_parts = [part for part in path.split("/") if part]
    if not pattern_parts:
        return False
    return _match_parts(pattern_parts, path_parts)


def _match_parts(pattern_parts: list[str], path_parts: list[str]) -> bool:
    if not pattern_parts:
        return not path_parts
    head, rest = pattern_parts[0], pattern_parts[1:]
    if head == "**":
        # `**` consumes any number of segments, including zero.
        for index in range(len(path_parts) + 1):
            if _match_parts(rest, path_parts[index:]):
                return True
        return False
    if not path_parts:
        return False
    if not _match_segment(head, path_parts[0]):
        return False
    return _match_parts(rest, path_parts[1:])


def _match_segment(pattern: str, segment: str) -> bool:
    """Match one path segment against one pattern segment."""
    if pattern == "*":
        return True
    if "?" not in pattern and "*" not in pattern:
        return pattern == segment
    return _match_wildcards(pattern, segment)


def _match_wildcards(pattern: str, text: str) -> bool:
    """Match a single segment against a pattern containing `*` and `?`."""
    pattern_index = 0
    text_index = 0
    star_index = -1
    match_index = 0

    while text_index < len(text):
        if pattern_index < len(pattern) and pattern[pattern_index] in ("*", "?"):
            if pattern[pattern_index] == "?":
                pattern_index += 1
                text_index += 1
                continue
            star_index = pattern_index
            match_index = text_index
            pattern_index += 1
            continue
        if pattern_index < len(pattern) and pattern[pattern_index] == text[text_index]:
            pattern_index += 1
            text_index += 1
            continue
        if star_index != -1:
            pattern_index = star_index + 1
            match_index += 1
            text_index = match_index
            continue
        return False

    while pattern_index < len(pattern) and pattern[pattern_index] == "*":
        pattern_index += 1
    return pattern_index == len(pattern)


def compute_freshness(
    rubric: Rubric,
    receipt: RunReceipt,
    history: GitHistory,
    tip_sha: str,
) -> tuple[str, list[str], list[str]]:
    """Return the freshness of one receipt, the reasons, and the blockers.

    The freshness vocabulary is the one the registry schema permits:
    `current`, `stale`, `superseded`. `superseded` is decided by the caller
    when a later run exists for the same qualification, so this function
    returns only `current` or `stale`.

    `reasons` explains why the run is not current. `blockers` is the subset
    a reader of the registry should act on.

    The result must not depend on which objects happen to be present in the
    local object store. A commit that was never merged to `main` may still
    exist as a dangling object in one developer's clone and be absent from
    another, so ancestry is tested with `git merge-base --is-ancestor`,
    which answers "is this an ancestor of the tip?" identically in every
    checkout: exit 0 for an ancestor, non-zero for both a known
    non-ancestor and an unresolvable revision.
    """
    if receipt.commit == tip_sha:
        return "current", [], []

    if not history.is_ancestor(receipt.commit, tip_sha):
        # Either the tested commit is not part of the tip's lineage, or it
        # cannot be resolved at all. Both mean the same thing for a reader:
        # this run cannot be shown to describe the code the tip contains.
        return (
            "stale",
            ["tested_commit_not_in_tip_lineage"],
            [
                f"The tested commit {receipt.commit} is not an ancestor of the "
                "current tip, so this run cannot be shown to describe the "
                "code the tip contains. A qualification run must test a "
                "revision that is part of the lineage it qualifies."
            ],
        )

    changed = history.changed_paths(receipt.commit, tip_sha)
    if changed is None:
        # The comparison could not be performed. Treating this as current
        # would assert freshness that was never demonstrated.
        return (
            "stale",
            ["freshness_comparison_unavailable"],
            [
                "Freshness could not be computed for this run because the "
                "comparison against the current tip failed. The run is "
                "treated as not current."
            ],
        )

    touched = match_surface(changed, rubric.surface_paths)
    if not touched:
        return "current", [], []

    return (
        "stale",
        sorted(touched),
        [
            "The tested commit no longer describes the current tip: "
            f"{len(touched)} path(s) in this qualification surface changed "
            "since the run."
        ],
    )
