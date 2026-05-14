"""Typed contracts for Guardian-mediated coding-agent execution.

This module is intentionally dependency-light and does not execute adapters.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

CodingAgentAdapterKind = Literal[
    "pi_sdk",
    "pi_codex_runner",
    "codex",
    "claudecode",
]
CodingAgentTaskStatus = Literal[
    "queued",
    "dispatching",
    "running",
    "completed",
    "failed_retryable",
    "failed_fatal",
    "cancelled",
]


@dataclass(frozen=True)
class CodingAgentPermissionPolicy:
    allow_shell: bool
    allow_network: bool
    allow_write: bool
    allowed_paths: tuple[str, ...]
    max_runtime_seconds: int


@dataclass(frozen=True)
class CodingAgentTaskEnvelope:
    coding_task_id: str
    thread_id: str
    source_message_id: str
    attempt_id: str
    user_id: str
    project_id: str | None
    adapter_kind: CodingAgentAdapterKind
    instructions: str
    repo_root: str | None
    context_summary: str | None
    permission_policy: CodingAgentPermissionPolicy
    campaign_id: str | None = None
    work_order_id: str | None = None
    # Optional supervised validation command executed once after adapter return.
    validation_command: str | None = None
    max_validation_attempts: int = 1
    worktree_lease_id: str | None = None
    require_worktree_lease: bool = False
    commit_after_validation: bool = False
    commit_message: str | None = None
    require_human_review_before_merge: bool = True


@dataclass(frozen=True)
class CodingAgentResult:
    coding_task_id: str
    attempt_id: str
    status: CodingAgentTaskStatus
    summary: str
    files_changed: tuple[str, ...]
    artifacts: tuple[str, ...]
    logs_summary: str | None
    error_code: str | None
    error_message: str | None
    adapter_session_ref: str | None
    validation_results: dict[str, object] | None = None


__all__ = [
    "CodingAgentAdapterKind",
    "CodingAgentPermissionPolicy",
    "CodingAgentResult",
    "CodingAgentTaskEnvelope",
    "CodingAgentTaskStatus",
]
