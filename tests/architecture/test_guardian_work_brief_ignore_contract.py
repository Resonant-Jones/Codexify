"""Contract tests for generated Guardian Work Brief packet ignores.

The checks are read-only: they verify Git's ignore behavior without creating,
deleting, moving, or mutating any generated reporting packet files.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
IGNORE_FILE = ROOT / "docs" / "guardian" / "work-briefs" / ".gitignore"
WORK_BRIEF_DATE = "docs/guardian/work-briefs/2026-07-12"

GENERATED_PACKET_PATTERNS = (
    "20*/axis-brief.md",
    "20*/codex-next-task-packet.md",
    "20*/decision-log.md",
    "20*/truth-ledger.md",
)


def _check_ignore(path: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "check-ignore", path],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_work_brief_ignore_file_exists() -> None:
    assert IGNORE_FILE.is_file()


def test_ignore_file_lists_only_the_generated_packet_patterns() -> None:
    patterns = {
        line.strip()
        for line in IGNORE_FILE.read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }

    for pattern in GENERATED_PACKET_PATTERNS:
        assert pattern in patterns

    for forbidden_pattern in (
        "*.md",
        "20*/",
        "docs/guardian/work-briefs/",
        "worktree-drift-classification.md",
    ):
        assert forbidden_pattern not in patterns


def test_generated_packets_are_ignored() -> None:
    for filename in (
        "axis-brief.md",
        "codex-next-task-packet.md",
        "decision-log.md",
        "truth-ledger.md",
    ):
        proc = _check_ignore(f"{WORK_BRIEF_DATE}/{filename}")
        assert proc.returncode == 0, proc.stderr


def test_manually_authored_documents_remain_trackable() -> None:
    for filename in (
        "worktree-drift-classification.md",
        "manual-follow-through.md",
    ):
        proc = _check_ignore(f"{WORK_BRIEF_DATE}/{filename}")
        assert proc.returncode != 0, proc.stdout
