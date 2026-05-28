"""Delegated CLI adapter registry."""

from .base import (
    AgentAdapter,
    AgentExecutionRequest,
    AgentRunEnvelope,
    AgentRunStatus,
)
from .pi_codex_runner import PiCodexRunnerAdapter

_pi_adapter = PiCodexRunnerAdapter()

ADAPTERS = {
    "pi": _pi_adapter,
    "pi_codex_runner": _pi_adapter,
}

__all__ = [
    "ADAPTERS",
    "AgentAdapter",
    "AgentExecutionRequest",
    "AgentRunEnvelope",
    "AgentRunStatus",
    "PiCodexRunnerAdapter",
]
