"""Deprecated direct Claude Code adapter stub for Campaign Runner compatibility."""

from __future__ import annotations

from .base import AgentExecutionRequest, AgentRunEnvelope

UNSUPPORTED_DIRECT_CLAUDE_MESSAGE = (
    "Direct Claude / Claude Code CLI execution is unsupported for Campaign "
    "Runner. Use the Pi broker adapter instead. Claude may only appear as a "
    "downstream resolved provider/model identity in Pi receipts."
)


class ClaudeCodeAdapter:
    name = "claudecode"

    def __init__(self) -> None:
        raise RuntimeError(UNSUPPORTED_DIRECT_CLAUDE_MESSAGE)

    def execute(self, request: AgentExecutionRequest) -> AgentRunEnvelope:
        _ = request
        raise RuntimeError(UNSUPPORTED_DIRECT_CLAUDE_MESSAGE)
