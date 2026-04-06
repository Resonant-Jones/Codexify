"""Executor abstractions for delegation backends."""

from guardian.core.executors.base import (
    CanonicalEscalation,
    CanonicalTaskSummary,
    CodeExecutor,
    CodexifyExecutorContextBundle,
    CodexifyExecutorRequest,
    ExecutorEscalationEvent,
    ExecutorFailure,
    ExecutorProgressEvent,
    ExecutorRequest,
    ExecutorResult,
    ExecutorStreamChunk,
    ExecutorTerminalResult,
)
from guardian.core.executors.codex_executor import CodexExecutor
from guardian.core.executors.registry import (
    ExecutorAuthMode,
    ExecutorCapability,
    ExecutorId,
    ExecutorRegistryEntry,
    ExecutorReleasePosture,
    get_executor_entry,
    get_executor_registry,
    is_supported_executor,
)

__all__ = [
    "CanonicalEscalation",
    "CanonicalTaskSummary",
    "CodeExecutor",
    "CodexExecutor",
    "CodexifyExecutorContextBundle",
    "CodexifyExecutorRequest",
    "ExecutorAuthMode",
    "ExecutorCapability",
    "ExecutorEscalationEvent",
    "ExecutorFailure",
    "ExecutorId",
    "ExecutorProgressEvent",
    "ExecutorReleasePosture",
    "ExecutorRegistryEntry",
    "ExecutorRequest",
    "ExecutorResult",
    "ExecutorStreamChunk",
    "ExecutorTerminalResult",
    "get_executor_entry",
    "get_executor_registry",
    "is_supported_executor",
]
