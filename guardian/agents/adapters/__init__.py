"""Delegated CLI adapter registry."""

from .base import (
    AgentAdapter,
    AgentExecutionRequest,
    AgentRunEnvelope,
    AgentRunStatus,
)
from .claudecode import ClaudeCodeAdapter
from .codex import CodexAdapter

ADAPTERS = {
    "codex": CodexAdapter(),
    "claudecode": ClaudeCodeAdapter(),
}

__all__ = [
    "ADAPTERS",
    "AgentAdapter",
    "AgentExecutionRequest",
    "AgentRunEnvelope",
    "AgentRunStatus",
    "ClaudeCodeAdapter",
    "CodexAdapter",
]
