"""Tests for ``git status --short`` and ahead/behind parsing.

Covers the MVP status test matrix: clean, staged, unstaged, modified both
staged and unstaged, untracked, and mixed. Also covers ahead/behind parsing.
"""

from __future__ import annotations

from guardian.worktrees.status import parse_ahead_behind, parse_status_short


# ---------------------------------------------------------------------------
# parse_status_short
# ---------------------------------------------------------------------------


def test_clean_status() -> None:
    counts = parse_status_short("")
    assert counts.staged == 0
    assert counts.unstaged == 0
    assert counts.untracked == 0
    assert counts.dirty == 0


def test_staged_file() -> None:
    # 'M ' => modified in index, clean in worktree.
    counts = parse_status_short("M  src/app.py\n")
    assert counts.staged == 1
    assert counts.unstaged == 0
    assert counts.untracked == 0
    assert counts.dirty == 1


def test_unstaged_file() -> None:
    # ' M' => unmodified in index, modified in worktree.
    counts = parse_status_short(" M src/app.py\n")
    assert counts.staged == 0
    assert counts.unstaged == 1
    assert counts.untracked == 0
    assert counts.dirty == 1


def test_modified_staged_and_unstaged_file() -> None:
    # 'MM' => modified in index AND worktree. Counts both, but one dirty file.
    counts = parse_status_short("MM src/app.py\n")
    assert counts.staged == 1
    assert counts.unstaged == 1
    assert counts.untracked == 0
    assert counts.dirty == 1


def test_untracked_file() -> None:
    counts = parse_status_short("?? src/new.py\n")
    assert counts.untracked == 1
    assert counts.staged == 0
    assert counts.unstaged == 0
    assert counts.dirty == 1


def test_mixed_staged_unstaged_and_untracked() -> None:
    porcelain = (
        "M  staged_only.py\n"
        " M unstaged_only.py\n"
        "MM both.py\n"
        "A  added_staged.py\n"
        "?? untracked.py\n"
        "R  renamed.py\n"
        " D deleted_in_worktree.py\n"
    )
    counts = parse_status_short(porcelain)
    # staged: M, MM, A, R => 4
    assert counts.staged == 4
    # unstaged: M(unstaged_only), MM(both), D(deleted_in_worktree) => 3
    assert counts.unstaged == 3
    # untracked: ?? => 1
    assert counts.untracked == 1
    # dirty lines: every non-empty line => 7
    assert counts.dirty == 7


def test_status_ignores_blank_lines() -> None:
    counts = parse_status_short("\nM  src/app.py\n\n")
    assert counts.staged == 1
    assert counts.dirty == 1


def test_status_handles_crlf() -> None:
    counts = parse_status_short("M  src/app.py\r\n?? new.py\r\n")
    assert counts.staged == 1
    assert counts.untracked == 1
    assert counts.dirty == 2


def test_status_too_short_line_is_ignored() -> None:
    counts = parse_status_short("X\n")
    assert counts.dirty == 0


# ---------------------------------------------------------------------------
# parse_ahead_behind
# ---------------------------------------------------------------------------


def test_ahead_behind_basic() -> None:
    ahead, behind = parse_ahead_behind("2\t3\n")
    assert ahead == 2
    assert behind == 3


def test_ahead_behind_zero_zero() -> None:
    ahead, behind = parse_ahead_behind("0\t0")
    assert ahead == 0
    assert behind == 0


def test_ahead_behind_empty_returns_none_tuple() -> None:
    assert parse_ahead_behind("") == (None, None)
    assert parse_ahead_behind("   \n") == (None, None)


def test_ahead_behind_malformed_returns_none_tuple() -> None:
    assert parse_ahead_behind("nope") == (None, None)
    assert parse_ahead_behind("1 2 3") == (None, None)
    assert parse_ahead_behind("a\tb") == (None, None)
