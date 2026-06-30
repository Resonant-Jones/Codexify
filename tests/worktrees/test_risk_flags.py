"""Tests for worktree risk-flag classification.

Covers the MVP risk matrix: dirty main, dirty feature worktree, detached
HEAD, no upstream, behind upstream, staged changes, untracked files, missing
HEAD, plus the ``git_state_error`` flag and a clean lane.
"""

from __future__ import annotations

from guardian.worktrees.model import WorktreeLane
from guardian.worktrees.risk import classify_risk_flags


def _lane(**kwargs: object) -> WorktreeLane:
    base = dict(
        repo_path="/repo",
        worktree_path="/repo",
        branch="feat/x",
        head_sha="abc123",
        detached=False,
        bare=False,
        dirty_file_count=0,
        staged_file_count=0,
        unstaged_file_count=0,
        untracked_file_count=0,
        upstream="origin/feat/x",
        ahead_count=0,
        behind_count=0,
    )
    base.update(kwargs)
    return WorktreeLane(**base)  # type: ignore[arg-type]


def test_dirty_main_flagged() -> None:
    lane = _lane(branch="main", dirty_file_count=2)
    assert "dirty_main" in classify_risk_flags(lane)
    assert "dirty_worktree" not in classify_risk_flags(lane)


def test_dirty_master_also_treated_as_main() -> None:
    lane = _lane(branch="master", dirty_file_count=1)
    assert "dirty_main" in classify_risk_flags(lane)


def test_dirty_feature_worktree_flagged() -> None:
    lane = _lane(branch="feat/worktree-lane", dirty_file_count=1)
    flags = classify_risk_flags(lane)
    assert "dirty_worktree" in flags
    assert "dirty_main" not in flags


def test_detached_head_flagged() -> None:
    lane = _lane(detached=True, branch=None, upstream=None)
    assert "detached_head" in classify_risk_flags(lane)


def test_no_upstream_flagged_for_branch() -> None:
    lane = _lane(upstream=None)
    assert "no_upstream" in classify_risk_flags(lane)


def test_no_upstream_not_flagged_for_detached() -> None:
    lane = _lane(detached=True, branch=None, upstream=None)
    flags = classify_risk_flags(lane)
    assert "no_upstream" not in flags
    assert "detached_head" in flags


def test_behind_upstream_flagged() -> None:
    lane = _lane(behind_count=4)
    assert "behind_upstream" in classify_risk_flags(lane)


def test_not_behind_upstream_not_flagged() -> None:
    lane = _lane(behind_count=0)
    assert "behind_upstream" not in classify_risk_flags(lane)


def test_staged_changes_flagged() -> None:
    lane = _lane(staged_file_count=3)
    assert "staged_changes" in classify_risk_flags(lane)


def test_untracked_files_flagged() -> None:
    lane = _lane(untracked_file_count=2)
    assert "untracked_files" in classify_risk_flags(lane)


def test_missing_head_flagged() -> None:
    lane = _lane(head_sha=None)
    assert "missing_head" in classify_risk_flags(lane)


def test_missing_head_not_flagged_for_bare() -> None:
    lane = _lane(bare=True, head_sha=None, upstream=None)
    assert "missing_head" not in classify_risk_flags(lane)


def test_git_state_error_flagged() -> None:
    lane = _lane(had_git_error=True)
    assert "git_state_error" in classify_risk_flags(lane)


def test_clean_lane_has_no_flags() -> None:
    lane = _lane()
    assert classify_risk_flags(lane) == []


def test_flags_are_ordered_by_severity() -> None:
    lane = _lane(
        branch=None,
        head_sha=None,
        detached=True,
        dirty_file_count=1,
        staged_file_count=1,
        untracked_file_count=1,
        upstream=None,
        behind_count=2,
        had_git_error=True,
    )
    flags = classify_risk_flags(lane)
    # Most severe first; detached clears branch so dirty is classified as
    # dirty_worktree, and detached precludes no_upstream.
    assert flags == [
        "git_state_error",
        "missing_head",
        "detached_head",
        "dirty_worktree",
        "staged_changes",
        "untracked_files",
        "behind_upstream",
    ]
