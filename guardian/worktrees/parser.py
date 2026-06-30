"""Pure parser for ``git worktree list --porcelain``.

The parser is deliberately string-in / structured-out so it can be unit-tested
without a git binary. It tolerates partial, empty, and malformed porcelain
output without raising.
"""

from __future__ import annotations

from guardian.worktrees.model import RawWorktreeEntry


def normalize_branch(branch_ref: str | None) -> str | None:
    """Convert a symbolic ref like ``refs/heads/main`` to ``main``.

    Returns ``None`` for empty/detached input. Non-``refs/heads/`` refs are
    returned stripped as-is so unusual branch refs are still visible.
    """
    if branch_ref is None:
        return None
    ref = branch_ref.strip()
    if not ref:
        return None
    prefix = "refs/heads/"
    if ref.startswith(prefix):
        stripped = ref[len(prefix) :].strip()
        return stripped or None
    return ref


def _entry_from_block(block: dict[str, object]) -> RawWorktreeEntry | None:
    """Build a ``RawWorktreeEntry`` from a parsed block, or None if invalid.

    A block without a ``worktree`` path is treated as malformed and skipped.
    """
    worktree_path = block.get("worktree_path")
    if not isinstance(worktree_path, str) or not worktree_path.strip():
        return None
    head_sha_raw = block.get("head_sha")
    branch_ref_raw = block.get("branch_ref")
    return RawWorktreeEntry(
        worktree_path=worktree_path.strip(),
        head_sha=head_sha_raw if isinstance(head_sha_raw, str) else None,
        branch_ref=branch_ref_raw if isinstance(branch_ref_raw, str) else None,
        detached=bool(block.get("detached", False)),
        bare=bool(block.get("bare", False)),
    )


def parse_worktree_porcelain(text: str) -> list[RawWorktreeEntry]:
    """Parse porcelain output into a list of raw worktree entries.

    Supports the documented porcelain keys (``worktree``, ``HEAD``,
    ``branch``, ``detached``, ``bare``) and tolerates extra/unknown lines such
    as ``locked`` / ``prunable`` by ignoring them. Entries are separated by
    blank lines; a trailing block without a following blank line is still
    captured.
    """
    entries: list[RawWorktreeEntry] = []
    current: dict[str, object] | None = None

    def _flush() -> None:
        nonlocal current
        if current is not None:
            entry = _entry_from_block(current)
            if entry is not None:
                entries.append(entry)
            current = None

    for raw_line in text.splitlines():
        line = raw_line.rstrip("\r")
        if not line.strip():
            _flush()
            continue
        if current is None:
            current = {}
        parts = line.split(" ", 1)
        key = parts[0]
        value = parts[1] if len(parts) > 1 else ""
        if key == "worktree":
            current["worktree_path"] = value
        elif key == "HEAD":
            current["head_sha"] = value or None
        elif key == "branch":
            current["branch_ref"] = value or None
        elif key == "detached":
            current["detached"] = True
        elif key == "bare":
            current["bare"] = True
        # Other recognized-but-ignored porcelain flags (locked, prunable,
        # and any future unknown lines) are intentionally dropped so a
        # newer git cannot crash the parser.
    _flush()
    return entries
