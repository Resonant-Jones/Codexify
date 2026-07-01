"""Pure risk-flag classification for worktree lanes.

Given a populated :class:`~guardian.worktrees.model.WorktreeLane`, produce the
deterministic ordered list of risk flags. This is a pure function so the risk
flag matrix can be unit-tested without git.
"""

from __future__ import annotations

from guardian.worktrees.model import MAIN_BRANCHES, WorktreeLane


def classify_risk_flags(lane: WorktreeLane) -> list[str]:
    """Return the ordered risk flags for a lane.

    Flags are ordered roughly by severity so the most actionable state
    surfaces first:

    ``git_state_error`` -> ``missing_head`` -> ``detached_head`` ->
    ``dirty_main`` / ``dirty_worktree`` -> ``staged_changes`` ->
    ``untracked_files`` -> ``no_upstream`` -> ``behind_upstream``.
    """
    flags: list[str] = []

    if lane.had_git_error:
        flags.append("git_state_error")

    if lane.head_sha is None and not lane.bare:
        flags.append("missing_head")

    if lane.detached:
        flags.append("detached_head")

    is_main = lane.branch in MAIN_BRANCHES
    if lane.dirty_file_count > 0:
        flags.append("dirty_main" if is_main else "dirty_worktree")

    if lane.staged_file_count > 0:
        flags.append("staged_changes")

    if lane.untracked_file_count > 0:
        flags.append("untracked_files")

    # A detached HEAD or bare worktree has no branch upstream by definition;
    # ``detached_head`` / bare state already flags it, so ``no_upstream`` is
    # only meaningful for real branches that lack an upstream.
    if lane.upstream is None and not lane.detached and not lane.bare:
        flags.append("no_upstream")

    if lane.behind_count is not None and lane.behind_count > 0:
        flags.append("behind_upstream")

    return flags
