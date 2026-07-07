"""Read-only worktree discovery and state collection service.

This is the visibility layer. It runs ONLY the allowed read-only git commands
documented in the MVP spec and must never mutate the repository, working tree,
index, or branches. All mutation commands are out of scope and forbidden.
"""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path
from typing import Protocol

from guardian.worktrees.model import RawWorktreeEntry, WorktreeDiscovery, WorktreeLane
from guardian.worktrees.parser import normalize_branch, parse_worktree_porcelain
from guardian.worktrees.risk import classify_risk_flags
from guardian.worktrees.status import parse_ahead_behind, parse_status_short

logger = logging.getLogger(__name__)

# Environment variable that selects which local repo to inspect.
REPO_PATH_ENV = "CODEXIFY_WORKTREE_REPO_PATH"
# Hard ceiling on any single read-only git call so a hung git cannot wedge the
# operator surface indefinitely.
DEFAULT_GIT_TIMEOUT_SECONDS = 15.0


class GitError(RuntimeError):
    """Raised when a read-only git command fails unexpectedly."""


# A git runner takes an argv list (without the leading "git") and the worktree
# cwd, and returns stdout. It is injectable so tests can avoid subprocess.
class GitRunner(Protocol):
    def __call__(self, args: list[str], *, cwd: str) -> str: ...


def run_git(
    args: list[str],
    *,
    cwd: str,
    timeout: float = DEFAULT_GIT_TIMEOUT_SECONDS,
) -> str:
    """Run a read-only git command and return stdout.

    Uses an argv list (never ``shell=True``) so refspec tokens such as
    ``@{u}`` reach git verbatim without shell expansion or injection risk.
    Raises :class:`GitError` on non-zero exit, timeout, or OS-level failure.
    """
    try:
        env = os.environ.copy()
        # Preserve the read-only discovery contract for background status probes:
        # git status may refresh cached stat data and write the index unless
        # optional locks are disabled.
        env["GIT_OPTIONAL_LOCKS"] = "0"
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        raise GitError(
            f"git {' '.join(args)} timed out after {timeout}s in {cwd}"
        ) from exc
    except OSError as exc:
        raise GitError(f"git invocation failed in {cwd}: {exc}") from exc

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        raise GitError(
            f"git {' '.join(args)} failed in {cwd} "
            f"(rc={result.returncode}): {stderr[:300]}"
        )
    return result.stdout


def resolve_repo_path(
    explicit: str | None = None,
    *,
    env: dict[str, str] | None = None,
) -> tuple[str | None, str]:
    """Resolve the repo path to inspect and report where it came from.

    Precedence: explicit argument -> ``CODEXIFY_WORKTREE_REPO_PATH`` env ->
    development default (the repo this package ships in, clearly labeled).

    Returns ``(path_or_none, source)`` where source is one of
    ``"query"``, ``"env"``, or ``"dev_default"``.
    """
    env = env if env is not None else os.environ
    if explicit and explicit.strip():
        return explicit.strip(), "query"
    env_value = (env.get(REPO_PATH_ENV) or "").strip()
    if env_value:
        return env_value, "env"
    # Clearly-marked development default only: the repo this code ships in.
    dev_default = Path(__file__).resolve().parents[2]
    return str(dev_default), "dev_default"


def discover_worktree_lanes(
    repo_path: str,
    *,
    repo_path_source: str = "env",
    git_runner: GitRunner = run_git,
) -> WorktreeDiscovery:
    """Discover all worktrees for ``repo_path`` and collect their lane state.

    Non-destructive: only runs read-only git commands. If the repo cannot be
    inspected at all, returns a :class:`WorktreeDiscovery` with a populated
    ``errors`` list (the caller decides how to surface that). Per-worktree
    problems (missing folder, missing upstream) degrade gracefully into lane
    warnings/risk flags rather than failing the whole discovery.
    """
    repo = Path(repo_path)
    if not repo.exists() or not repo.is_dir():
        return WorktreeDiscovery(
            repo_path=str(repo),
            repo_path_source=repo_path_source,
            errors=["repo_path does not exist or is not a directory"],
        )

    porcelain: str
    try:
        porcelain = git_runner(["worktree", "list", "--porcelain"], cwd=str(repo))
    except GitError as exc:
        return WorktreeDiscovery(
            repo_path=str(repo),
            repo_path_source=repo_path_source,
            errors=[
                "repo_path is not a Git repository or git is unavailable: " + str(exc)
            ],
        )

    raw_entries = parse_worktree_porcelain(porcelain)
    lanes: list[WorktreeLane] = []
    warnings: list[str] = []
    for raw in raw_entries:
        lane = _collect_lane_state(raw, repo_path=str(repo), git_runner=git_runner)
        if not lane.exists:
            warnings.append(f"worktree path no longer exists: {lane.worktree_path}")
        lanes.append(lane)

    if not lanes:
        warnings.append("no worktrees discovered beyond main")

    return WorktreeDiscovery(
        repo_path=str(repo),
        repo_path_source=repo_path_source,
        lanes=lanes,
        warnings=warnings,
    )


def _collect_lane_state(
    raw: RawWorktreeEntry,
    *,
    repo_path: str,
    git_runner: GitRunner,
) -> WorktreeLane:
    """Collect full state for one worktree from read-only git commands."""
    worktree_path = raw.worktree_path or ""
    lane = WorktreeLane(
        repo_path=repo_path,
        worktree_path=worktree_path,
        branch=normalize_branch(raw.branch_ref),
        head_sha=raw.head_sha,
        detached=raw.detached,
        bare=raw.bare,
    )

    wt_path = Path(worktree_path)
    if not worktree_path or not wt_path.exists():
        # Deleted/missing worktree folder: keep porcelain-derived facts, do not
        # attempt to run git inside a non-existent cwd. Mark missing so the
        # operator gets a clear warning instead of a crash.
        lane.exists = False
        lane.risk_flags = classify_risk_flags(lane)
        return lane

    # Branch confirmation (empty output => detached).
    try:
        branch_out = git_runner(["branch", "--show-current"], cwd=worktree_path)
        current = branch_out.strip()
        if current:
            lane.branch = current
            lane.detached = False
        else:
            lane.detached = True
            lane.branch = None
    except GitError:
        lane.had_git_error = True

    # HEAD sha.
    try:
        head_out = git_runner(["rev-parse", "HEAD"], cwd=worktree_path)
        sha = head_out.strip()
        lane.head_sha = sha or None
    except GitError:
        lane.head_sha = None
        lane.had_git_error = True

    # Dirty / staged / unstaged / untracked counts.
    try:
        status_out = git_runner(["status", "--short"], cwd=worktree_path)
        counts = parse_status_short(status_out)
        lane.staged_file_count = counts.staged
        lane.unstaged_file_count = counts.unstaged
        lane.untracked_file_count = counts.untracked
        lane.dirty_file_count = counts.dirty
    except GitError:
        lane.had_git_error = True

    # Upstream + ahead/behind only apply to real (non-detached, non-bare)
    # branches. A missing upstream is an expected condition and is surfaced
    # via the ``no_upstream`` risk flag rather than ``git_state_error``.
    if not lane.detached and not lane.bare:
        try:
            up_out = git_runner(
                ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
                cwd=worktree_path,
            )
            upstream = up_out.strip()
            lane.upstream = upstream or None
        except GitError:
            lane.upstream = None

        if lane.upstream is not None:
            try:
                ab_out = git_runner(
                    ["rev-list", "--left-right", "--count", "HEAD...@{u}"],
                    cwd=worktree_path,
                )
                ahead, behind = parse_ahead_behind(ab_out)
                lane.ahead_count = ahead
                lane.behind_count = behind
            except GitError:
                lane.had_git_error = True

    lane.risk_flags = classify_risk_flags(lane)
    return lane
