"""Data models for the read-only Worktree Lane MVP.

These models are intentionally plain dataclasses so the parser, status, and
risk-classification layers stay free of framework dependencies and easy to
unit-test. The FastAPI route layer projects them into pydantic response models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# Branch names that are treated as the protected "main" lane for risk
# classification (``dirty_main`` vs ``dirty_worktree``). Kept narrow on
# purpose: the repo ships on ``main``.
MAIN_BRANCHES: tuple[str, ...] = ("main", "master")


@dataclass
class RawWorktreeEntry:
    """A single parsed record from ``git worktree list --porcelain``.

    ``branch_ref`` is the raw symbolic ref (e.g. ``refs/heads/main``) when
    present. Detached worktrees have ``detached=True`` and ``branch_ref=None``.
    Bare worktrees have ``bare=True`` and typically no HEAD/branch.
    """

    worktree_path: Optional[str] = None
    head_sha: Optional[str] = None
    branch_ref: Optional[str] = None
    detached: bool = False
    bare: bool = False


@dataclass
class StatusCounts:
    """Aggregated counts derived from ``git status --short`` output."""

    staged: int = 0
    unstaged: int = 0
    untracked: int = 0
    dirty: int = 0


@dataclass
class WorktreeLane:
    """Full operator-facing state for a single worktree lane.

    Mirrors the required MVP data model. Two additive helper fields are kept:

    * ``exists``        — False when the worktree folder is missing/deleted.
    * ``had_git_error`` — True when a read-only git command failed
      unexpectedly (drives the ``git_state_error`` risk flag).
    """

    repo_path: str
    worktree_path: str
    branch: Optional[str] = None
    head_sha: Optional[str] = None
    detached: bool = False
    bare: bool = False
    dirty_file_count: int = 0
    staged_file_count: int = 0
    unstaged_file_count: int = 0
    untracked_file_count: int = 0
    upstream: Optional[str] = None
    ahead_count: Optional[int] = None
    behind_count: Optional[int] = None
    risk_flags: list[str] = field(default_factory=list)
    # Additive operator helpers (not part of the required model shape).
    exists: bool = True
    had_git_error: bool = False


@dataclass
class WorktreeDiscovery:
    """Result of discovering and inspecting all worktree lanes for a repo."""

    repo_path: str
    repo_path_source: str = "env"
    lanes: list[WorktreeLane] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
