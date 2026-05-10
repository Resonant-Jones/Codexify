"""Guarded Git commit helper for post-validation coding-worker flows.

This module only stages and commits inside an existing Git worktree path.
It does not create branches, create worktrees, merge, or push.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass

from guardian.protocol_tokens import ErrorCode

_GIT_TIMEOUT_SECONDS = 20
_MAX_MESSAGE_CHARS = 256
_MAX_ERROR_CHARS = 320


@dataclass(frozen=True)
class CommitGateResult:
    attempted: bool
    committed: bool
    commit_hash: str | None
    status: str
    reason_code: str | None
    message: str | None
    files_changed: list[str]
    worktree_path: str
    branch_name: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "attempted": self.attempted,
            "committed": self.committed,
            "commit_hash": self.commit_hash,
            "status": self.status,
            "reason_code": self.reason_code,
            "message": self.message,
            "files_changed": list(self.files_changed),
            "worktree_path": self.worktree_path,
            "branch_name": self.branch_name,
        }


class CommitGateError(RuntimeError):
    """Raised when commit gating encounters a hard failure."""


def commit_after_green(
    worktree_path: str,
    commit_message: str,
    branch_name: str | None = None,
) -> CommitGateResult:
    """Attempt one bounded commit in an existing Git worktree.

    Returns a structured result for worker/store event metadata.
    """
    normalized_path = str(worktree_path or "").strip()
    bounded_message = _bound_commit_message(commit_message)

    if not normalized_path:
        return CommitGateResult(
            attempted=True,
            committed=False,
            commit_hash=None,
            status="failed",
            reason_code=ErrorCode.GIT_WORKTREE_INVALID.value,
            message="worktree path is required",
            files_changed=[],
            worktree_path=normalized_path,
            branch_name=branch_name,
        )

    if not os.path.isdir(normalized_path):
        return CommitGateResult(
            attempted=True,
            committed=False,
            commit_hash=None,
            status="failed",
            reason_code=ErrorCode.GIT_WORKTREE_INVALID.value,
            message="worktree path is unavailable or not a directory",
            files_changed=[],
            worktree_path=normalized_path,
            branch_name=branch_name,
        )

    inside_worktree = _run_git(
        ["rev-parse", "--is-inside-work-tree"],
        cwd=normalized_path,
    )
    if (
        inside_worktree.returncode != 0
        or inside_worktree.stdout.strip() != "true"
    ):
        return CommitGateResult(
            attempted=True,
            committed=False,
            commit_hash=None,
            status="failed",
            reason_code=ErrorCode.GIT_WORKTREE_INVALID.value,
            message=_sanitize_error(
                inside_worktree.stderr or inside_worktree.stdout
            )
            or "worktree path is not inside a git worktree",
            files_changed=[],
            worktree_path=normalized_path,
            branch_name=branch_name,
        )

    status_result = _run_git(["status", "--porcelain"], cwd=normalized_path)
    if status_result.returncode != 0:
        return CommitGateResult(
            attempted=True,
            committed=False,
            commit_hash=None,
            status="failed",
            reason_code=ErrorCode.GIT_COMMIT_FAILED.value,
            message=_sanitize_error(status_result.stderr)
            or "failed to inspect git status",
            files_changed=[],
            worktree_path=normalized_path,
            branch_name=branch_name,
        )

    files_changed = _parse_porcelain_paths(status_result.stdout)
    if not files_changed:
        return CommitGateResult(
            attempted=True,
            committed=False,
            commit_hash=None,
            status="skipped",
            reason_code=ErrorCode.GIT_NO_CHANGES_TO_COMMIT.value,
            message="no changes to commit",
            files_changed=[],
            worktree_path=normalized_path,
            branch_name=branch_name,
        )

    add_result = _run_git(["add", "-A"], cwd=normalized_path)
    if add_result.returncode != 0:
        return CommitGateResult(
            attempted=True,
            committed=False,
            commit_hash=None,
            status="failed",
            reason_code=ErrorCode.GIT_COMMIT_FAILED.value,
            message=_sanitize_error(add_result.stderr)
            or "failed to stage changes",
            files_changed=files_changed,
            worktree_path=normalized_path,
            branch_name=branch_name,
        )

    commit_result = _run_git(
        ["commit", "-m", bounded_message],
        cwd=normalized_path,
    )
    if commit_result.returncode != 0:
        combined = "\n".join(
            item
            for item in [commit_result.stdout, commit_result.stderr]
            if item
        )
        sanitized = _sanitize_error(combined)
        if sanitized and "nothing to commit" in sanitized.lower():
            return CommitGateResult(
                attempted=True,
                committed=False,
                commit_hash=None,
                status="skipped",
                reason_code=ErrorCode.GIT_NO_CHANGES_TO_COMMIT.value,
                message="no changes to commit",
                files_changed=[],
                worktree_path=normalized_path,
                branch_name=branch_name,
            )
        return CommitGateResult(
            attempted=True,
            committed=False,
            commit_hash=None,
            status="failed",
            reason_code=ErrorCode.GIT_COMMIT_FAILED.value,
            message=sanitized or "git commit failed",
            files_changed=files_changed,
            worktree_path=normalized_path,
            branch_name=branch_name,
        )

    head_result = _run_git(["rev-parse", "HEAD"], cwd=normalized_path)
    if head_result.returncode != 0:
        return CommitGateResult(
            attempted=True,
            committed=False,
            commit_hash=None,
            status="failed",
            reason_code=ErrorCode.GIT_COMMIT_FAILED.value,
            message=_sanitize_error(head_result.stderr)
            or "failed to read git HEAD",
            files_changed=files_changed,
            worktree_path=normalized_path,
            branch_name=branch_name,
        )

    commit_hash = head_result.stdout.strip() or None
    if not commit_hash:
        return CommitGateResult(
            attempted=True,
            committed=False,
            commit_hash=None,
            status="failed",
            reason_code=ErrorCode.GIT_COMMIT_FAILED.value,
            message="commit hash missing after git commit",
            files_changed=files_changed,
            worktree_path=normalized_path,
            branch_name=branch_name,
        )

    return CommitGateResult(
        attempted=True,
        committed=True,
        commit_hash=commit_hash,
        status="committed",
        reason_code=ErrorCode.GIT_COMMIT_CREATED.value,
        message="commit created",
        files_changed=files_changed,
        worktree_path=normalized_path,
        branch_name=branch_name,
    )


def _run_git(argv: list[str], *, cwd: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["git", *argv],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            timeout=_GIT_TIMEOUT_SECONDS,
        )
    except Exception as exc:
        raise CommitGateError(
            f"git command failed: {type(exc).__name__}"
        ) from exc


def _parse_porcelain_paths(output: str) -> list[str]:
    paths: list[str] = []
    for line in str(output or "").splitlines():
        if len(line) < 4:
            continue
        raw_path = line[3:].strip()
        if " -> " in raw_path:
            _src, _arrow, dst = raw_path.partition(" -> ")
            raw_path = dst.strip() or raw_path
        if raw_path:
            paths.append(raw_path)
    deduped: list[str] = []
    for path in paths:
        if path not in deduped:
            deduped.append(path)
    return deduped


def _sanitize_error(raw: str | None) -> str | None:
    text = " ".join(str(raw or "").split())
    if not text:
        return None
    if len(text) <= _MAX_ERROR_CHARS:
        return text
    return text[: _MAX_ERROR_CHARS - 3] + "..."


def _bound_commit_message(message: str | None) -> str:
    text = str(message or "").strip()
    if not text:
        text = "Guardian commit-after-green"
    if len(text) <= _MAX_MESSAGE_CHARS:
        return text
    return text[: _MAX_MESSAGE_CHARS - 3] + "..."


__all__ = [
    "CommitGateError",
    "CommitGateResult",
    "commit_after_green",
]
