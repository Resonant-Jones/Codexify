"""Executor abstractions for delegation backends."""

from guardian.core.executors.base import (
    CodeExecutor,
    ExecutorRequest,
    ExecutorResult,
)

__all__ = ["CodeExecutor", "ExecutorRequest", "ExecutorResult"]
