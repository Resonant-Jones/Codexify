"""Deprecated direct Codex adapter stub for Campaign Runner compatibility."""

from __future__ import annotations

from .base import AgentExecutionRequest, AgentRunEnvelope

UNSUPPORTED_DIRECT_CODEX_MESSAGE = (
    "Direct Codex CLI execution is unsupported for Campaign Runner. "
    "Use the Pi broker adapter instead. Codex may only appear as a "
    "downstream resolved provider/model identity in Pi receipts."
)


class CodexAdapter:
    name = "codex"

    def __init__(self) -> None:
        raise RuntimeError(UNSUPPORTED_DIRECT_CODEX_MESSAGE)

    def execute(self, request: AgentExecutionRequest) -> AgentRunEnvelope:
        _ = request
        raise RuntimeError(UNSUPPORTED_DIRECT_CODEX_MESSAGE)
