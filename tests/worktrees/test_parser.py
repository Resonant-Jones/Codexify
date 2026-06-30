"""Tests for the ``git worktree list --porcelain`` parser.

Covers the MVP porcelain test matrix: single main worktree, multiple
worktrees, detached, bare, missing branch line, unexpected extra lines, empty
output, and malformed output. Also covers ``refs/heads/`` normalization.
"""

from __future__ import annotations

from guardian.worktrees.parser import normalize_branch, parse_worktree_porcelain


# ---------------------------------------------------------------------------
# normalize_branch
# ---------------------------------------------------------------------------


def test_normalize_branch_strips_refs_heads_prefix() -> None:
    assert normalize_branch("refs/heads/main") == "main"


def test_normalize_branch_handles_feature_slash() -> None:
    assert normalize_branch("refs/heads/feat/worktree-lane-mvp") == (
        "feat/worktree-lane-mvp"
    )


def test_normalize_branch_none_for_detached() -> None:
    assert normalize_branch(None) is None


def test_normalize_branch_empty_string_is_none() -> None:
    assert normalize_branch("") is None
    assert normalize_branch("   ") is None


def test_normalize_branch_passes_through_non_heads_ref() -> None:
    assert normalize_branch("refs/tags/v1") == "refs/tags/v1"


# ---------------------------------------------------------------------------
# parse_worktree_porcelain — required porcelain matrix
# ---------------------------------------------------------------------------


def test_single_main_worktree() -> None:
    porcelain = (
        "worktree /Users/chris/Repos/Codexify\n"
        "HEAD abc123\n"
        "branch refs/heads/main\n"
    )
    entries = parse_worktree_porcelain(porcelain)
    assert len(entries) == 1
    entry = entries[0]
    assert entry.worktree_path == "/Users/chris/Repos/Codexify"
    assert entry.head_sha == "abc123"
    assert entry.branch_ref == "refs/heads/main"
    assert entry.detached is False
    assert entry.bare is False


def test_multiple_worktrees() -> None:
    porcelain = (
        "worktree /Users/chris/Repos/Codexify\n"
        "HEAD abc123\n"
        "branch refs/heads/main\n"
        "\n"
        "worktree /Users/chris/Repos/Codexify-queue\n"
        "HEAD def456\n"
        "branch refs/heads/feat/worktree-lane-mvp\n"
    )
    entries = parse_worktree_porcelain(porcelain)
    assert len(entries) == 2
    assert entries[0].worktree_path == "/Users/chris/Repos/Codexify"
    assert entries[1].worktree_path == "/Users/chris/Repos/Codexify-queue"
    assert entries[1].branch_ref == "refs/heads/feat/worktree-lane-mvp"
    assert entries[1].head_sha == "def456"


def test_detached_worktree() -> None:
    porcelain = (
        "worktree /Users/chris/Repos/Codexify-detached\n" "HEAD deadbeef\n" "detached\n"
    )
    entries = parse_worktree_porcelain(porcelain)
    assert len(entries) == 1
    entry = entries[0]
    assert entry.detached is True
    assert entry.bare is False
    assert entry.branch_ref is None
    assert entry.head_sha == "deadbeef"


def test_bare_worktree_marker() -> None:
    porcelain = "worktree /Users/chris/Repos/Codexify.git\nbare\n"
    entries = parse_worktree_porcelain(porcelain)
    assert len(entries) == 1
    entry = entries[0]
    assert entry.bare is True
    assert entry.detached is False
    assert entry.branch_ref is None


def test_missing_branch_line_keeps_entry_with_none_branch() -> None:
    porcelain = "worktree /Users/chris/Repos/Codexify\n" "HEAD abc123\n"
    entries = parse_worktree_porcelain(porcelain)
    assert len(entries) == 1
    entry = entries[0]
    assert entry.branch_ref is None
    assert entry.detached is False
    assert entry.bare is False
    assert entry.head_sha == "abc123"


def test_unexpected_extra_porcelain_lines_are_ignored() -> None:
    porcelain = (
        "worktree /Users/chris/Repos/Codexify\n"
        "HEAD abc123\n"
        "branch refs/heads/main\n"
        "locked\n"
        "prunable gc\n"
        "future-unknown-flag value\n"
    )
    entries = parse_worktree_porcelain(porcelain)
    assert len(entries) == 1
    entry = entries[0]
    assert entry.worktree_path == "/Users/chris/Repos/Codexify"
    assert entry.branch_ref == "refs/heads/main"
    assert entry.head_sha == "abc123"


def test_empty_porcelain_output() -> None:
    assert parse_worktree_porcelain("") == []
    assert parse_worktree_porcelain("\n\n\n") == []
    assert parse_worktree_porcelain("   \n  \n") == []


def test_malformed_porcelain_output_skips_block_without_worktree() -> None:
    # Block missing a worktree path is dropped; a trailing good block still
    # parses.
    porcelain = (
        "HEAD orphansa\n"
        "branch refs/heads/orphan\n"
        "\n"
        "worktree /Users/chris/Repos/Real\n"
        "HEAD real123\n"
        "branch refs/heads/main\n"
    )
    entries = parse_worktree_porcelain(porcelain)
    assert len(entries) == 1
    assert entries[0].worktree_path == "/Users/chris/Repos/Real"


def test_trailing_blank_line_does_not_create_empty_entry() -> None:
    porcelain = (
        "worktree /Users/chris/Repos/Codexify\n"
        "HEAD abc123\n"
        "branch refs/heads/main\n"
        "\n"
    )
    entries = parse_worktree_porcelain(porcelain)
    assert len(entries) == 1
    assert entries[0].worktree_path == "/Users/chris/Repos/Codexify"


def test_crlf_line_endings_are_handled() -> None:
    porcelain = (
        "worktree /Users/chris/Repos/Codexify\r\n"
        "HEAD abc123\r\n"
        "branch refs/heads/main\r\n"
        "\r\n"
        "worktree /Users/chris/Repos/Other\r\n"
        "HEAD def456\r\n"
        "detached\r\n"
    )
    entries = parse_worktree_porcelain(porcelain)
    assert len(entries) == 2
    assert entries[1].detached is True
    assert entries[1].head_sha == "def456"
