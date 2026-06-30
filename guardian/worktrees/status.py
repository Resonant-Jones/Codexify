"""Pure parsers for read-only git status / ahead-behind output.

Both functions are string-in / structured-out so they can be unit-tested
without a git binary.
"""

from __future__ import annotations

from guardian.worktrees.model import StatusCounts


def parse_status_short(text: str) -> StatusCounts:
    """Parse ``git status --short`` output into staged/unstaged/untracked counts.

    Interpetation (per the MVP spec):

    * Lines beginning with ``??`` count as untracked.
    * First status column (index) non-blank counts as staged.
    * Second status column (worktree) non-blank counts as unstaged.
    * Any non-empty status line counts toward the total dirty file count.

    A file that is both staged and unstaged (e.g. ``MM``) increments both
    counters but still counts as a single dirty file.
    """
    counts = StatusCounts()
    for raw_line in text.splitlines():
        line = raw_line.rstrip("\r")
        if not line:
            continue
        # A well-formed porcelain v1 status line is at least "XY <path>".
        if len(line) < 2:
            continue
        x = line[0]
        y = line[1]
        if line.startswith("??"):
            counts.untracked += 1
            counts.dirty += 1
            continue
        if x != " ":
            counts.staged += 1
        if y != " ":
            counts.unstaged += 1
        counts.dirty += 1
    return counts


def parse_ahead_behind(text: str) -> tuple[int | None, int | None]:
    """Parse ``git rev-list --left-right --count HEAD...@{u}`` output.

    Output is two whitespace-separated integers: ``<ahead>\\t<behind>`` where
    ``ahead`` is commits reachable from HEAD but not the upstream, and
    ``behind`` is the reverse. Returns ``(None, None)`` on empty/malformed
    output instead of raising.
    """
    stripped = text.strip()
    if not stripped:
        return (None, None)
    parts = stripped.split()
    if len(parts) != 2:
        return (None, None)
    try:
        ahead = int(parts[0])
        behind = int(parts[1])
    except ValueError:
        return (None, None)
    return (ahead, behind)
