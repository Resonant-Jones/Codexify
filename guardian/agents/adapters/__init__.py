"""Delegated CLI adapter registry."""

from .base import (
    AgentAdapter,
    AgentExecutionRequest,
    AgentRunEnvelope,
    AgentRunStatus,
)
from .claudecode import ClaudeCodeAdapter
from .codex import CodexAdapter
from .pi_codex_runner import PiCodexRunnerAdapter

ADAPTERS = {
    "codex": CodexAdapter(),
    "claudecode": ClaudeCodeAdapter(),
    "pi_codex_runner": PiCodexRunnerAdapter(),
}

__all__ = [
    "ADAPTERS",
    "AgentAdapter",
    "AgentExecutionRequest",
    "AgentRunEnvelope",
    "AgentRunStatus",
    "ClaudeCodeAdapter",
    "CodexAdapter",
    "PiCodexRunnerAdapter",
]
