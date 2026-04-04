"""Minimal executor abstractions for delegation backends."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol, runtime_checkable


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class ExecutorRequest:
    delegation_id: str
    task_id: str
    repo_path: str
    executor: str
    task_prompt: str
    context: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    thread_id: int | None = None
    project_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ExecutorResult:
    delegation_id: str
    task_id: str
    status: str
    summary: str | None = None
    result: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None
    created_at: str = field(default_factory=_utc_now_iso)
    completed_at: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@runtime_checkable
class CodeExecutor(Protocol):
    def execute(self, request: ExecutorRequest) -> ExecutorResult:
        """Execute a code task and return a structured result."""
        ...


__all__ = ["ExecutorRequest", "ExecutorResult", "CodeExecutor"]
