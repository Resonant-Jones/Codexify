"""Deprecated compatibility module for the removed direct Codex adapter."""

from __future__ import annotations

from .base import AgentExecutionRequest, AgentRunEnvelope

_ERROR_MESSAGE = (
    "Direct Codex CLI execution is unsupported for Campaign Runner. "
    "Use the Pi broker adapter instead. Codex may appear only as a "
    "downstream resolved provider/model identity in Pi receipts."
)


class CodexAdapter:
    """Compatibility stub that fails closed for removed direct execution."""

    name = "codex"

    def __init__(self) -> None:
        raise RuntimeError(_ERROR_MESSAGE)

    def execute(self, request: AgentExecutionRequest) -> AgentRunEnvelope:
        del request
        raise RuntimeError(_ERROR_MESSAGE)


__all__ = ["CodexAdapter"]
