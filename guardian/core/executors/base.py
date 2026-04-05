"""Minimal executor abstractions for delegation backends."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Protocol, runtime_checkable


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class ExecutorStreamChunk:
    """One streamed chunk from a delegation executor."""

    stream: str
    text: str
    sequence: int | None = None
    created_at: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ExecutorFailure:
    """Structured executor failure metadata."""

    error_code: str
    failure_class: str
    message: str
    binary: str | None = None
    command: list[str] = field(default_factory=list)
    returncode: int | None = None
    signal: int | None = None
    timeout_seconds: float | None = None
    timed_out: bool = False
    spawn_failed: bool = False
    stdout: str = ""
    stderr: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


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
    timeout_seconds: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ExecutorResult:
    delegation_id: str
    task_id: str
    status: str
    summary: str | None = None
    final_text: str | None = None
    stdout: str = ""
    stderr: str = ""
    raw_transcript: str = ""
    files_changed: list[str] = field(default_factory=list)
    commands_run: list[str] = field(default_factory=list)
    output_chunks: list[ExecutorStreamChunk] = field(default_factory=list)
    result: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    failure: ExecutorFailure | None = None
    error_message: str | None = None
    created_at: str = field(default_factory=_utc_now_iso)
    completed_at: str = field(default_factory=_utc_now_iso)

    def __post_init__(self) -> None:
        if self.final_text is None and self.summary is not None:
            self.final_text = self.summary
        if self.summary is None and self.final_text is not None:
            self.summary = self.final_text
        if not self.raw_transcript and self.stdout:
            self.raw_transcript = self.stdout
        if not self.raw_transcript and self.stderr:
            self.raw_transcript = self.stderr

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@runtime_checkable
class CodeExecutor(Protocol):
    def execute(
        self,
        request: ExecutorRequest,
        *,
        on_output: Callable[[ExecutorStreamChunk], None] | None = None,
        should_stop: Callable[[], bool] | None = None,
    ) -> ExecutorResult:
        """Execute a code task and return a structured result."""


__all__ = [
    "CodeExecutor",
    "ExecutorFailure",
    "ExecutorRequest",
    "ExecutorResult",
    "ExecutorStreamChunk",
]
