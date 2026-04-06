"""Executor abstraction layer for delegation backends."""

from __future__ import annotations

from typing import Callable, Protocol, runtime_checkable

from guardian.core.executors.contracts import (
    CanonicalEscalation,
    CanonicalTaskSummary,
    CodexifyExecutorContextBundle,
    CodexifyExecutorRequest,
    ExecutorEscalationEvent,
    ExecutorFailure,
    ExecutorProgressEvent,
    ExecutorTerminalResult,
)

ExecutorRequest = CodexifyExecutorRequest
ExecutorResult = ExecutorTerminalResult
ExecutorStreamChunk = ExecutorProgressEvent


@runtime_checkable
class CodeExecutor(Protocol):
    def execute(
        self,
        request: CodexifyExecutorRequest,
        *,
        on_output: Callable[[ExecutorProgressEvent], None] | None = None,
        should_stop: Callable[[], bool] | None = None,
    ) -> ExecutorTerminalResult:
        """Execute a code task and return a structured result."""


__all__ = [
    "CodeExecutor",
    "CanonicalEscalation",
    "CanonicalTaskSummary",
    "CodexifyExecutorContextBundle",
    "CodexifyExecutorRequest",
    "ExecutorEscalationEvent",
    "ExecutorFailure",
    "ExecutorProgressEvent",
    "ExecutorRequest",
    "ExecutorResult",
    "ExecutorStreamChunk",
    "ExecutorTerminalResult",
]
