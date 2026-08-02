"""Guardian-owned coding-agent execution substrates.

This package is intentionally separate from ``guardian.agents.adapters``.
Campaign Runner keeps its Pi-only delegation boundary while interactive coding
agents use the Guardian-mediated contract defined by ADR-020.
"""

from .contracts import (
    ApprovalDecision,
    CodingAgentAdapter,
    CodingAgentEvent,
    CodingAgentEventKind,
    CodingAgentSession,
    CodingTaskEnvelope,
    CodingTurnRequest,
)

__all__ = [
    "ApprovalDecision",
    "CodingAgentAdapter",
    "CodingAgentEvent",
    "CodingAgentEventKind",
    "CodingAgentSession",
    "CodingTaskEnvelope",
    "CodingTurnRequest",
]
