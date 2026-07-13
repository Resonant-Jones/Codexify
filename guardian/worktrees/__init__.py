"""Read-only Worktree Lane MVP package.

Discovers local Git worktrees for a configured repository and reports their
operational state (branch, HEAD, dirty/staged/untracked counts, upstream,
ahead/behind, and risk flags) without mutating anything.

See ``docs/architecture/agent-protocol-operations.md`` and the Worktree Lane
MVP task spec for the visibility-only boundary this package enforces.
"""

from __future__ import annotations

from guardian.worktrees.model import (
    MAIN_BRANCHES,
    RawWorktreeEntry,
    StatusCounts,
    WorktreeDiscovery,
    WorktreeLane,
)
from guardian.worktrees.parser import normalize_branch, parse_worktree_porcelain
from guardian.worktrees.risk import classify_risk_flags
from guardian.worktrees.service import (
    DEFAULT_GIT_TIMEOUT_SECONDS,
    GitError,
    discover_worktree_lanes,
    resolve_repo_path,
    run_git,
)
from guardian.worktrees.status import parse_ahead_behind, parse_status_short

__all__ = [
    "DEFAULT_GIT_TIMEOUT_SECONDS",
    "GitError",
    "MAIN_BRANCHES",
    "RawWorktreeEntry",
    "StatusCounts",
    "WorktreeDiscovery",
    "WorktreeLane",
    "classify_risk_flags",
    "discover_worktree_lanes",
    "normalize_branch",
    "parse_ahead_behind",
    "parse_status_short",
    "parse_worktree_porcelain",
    "resolve_repo_path",
    "run_git",
]
