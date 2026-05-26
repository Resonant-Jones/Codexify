"""Delegated CLI adapter registry."""

from .base import (
    AgentAdapter,
    AgentExecutionRequest,
    AgentRunEnvelope,
    AgentRunStatus,
)
from .pi_codex_runner import PiCodexRunnerAdapter

ADAPTERS = {
    "pi_codex_runner": PiCodexRunnerAdapter(),
}

__all__ = [
    "ADAPTERS",
    "AgentAdapter",
    "AgentExecutionRequest",
    "AgentRunEnvelope",
    "AgentRunStatus",
    "PiCodexRunnerAdapter",
]
