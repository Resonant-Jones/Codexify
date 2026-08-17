"""Typed adapter contract for delegated CLI agents."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field


class AgentRunStatus(str):
    OK = "ok"
    ERROR = "error"


class AgentRunEnvelope(BaseModel):
    """Strict adapter output envelope for orchestration."""

    status: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    artifacts: list[dict[str, Any]] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    spec_alignment_ok: bool = True
    schema_valid: bool = True
    model_self_confidence: float | None = None
    actual_provider_id: str | None = None
    actual_model_id: str | None = None
    actual_harness_id: str | None = None
    actual_harness_version: str | None = None

    model_config = ConfigDict(extra="forbid")


@dataclass(frozen=True)
class AgentExecutionRequest:
    prompt: str
    cwd: str | None = None
    timeout_seconds: int = 120
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class AgentExecutionIdentity:
    """Explicit identity frozen by a Guardian-authorized invocation."""

    provider_id: str
    model_id: str
    harness_id: str
    harness_version: str


class AgentAdapter(Protocol):
    name: str

    def execute(self, request: AgentExecutionRequest) -> AgentRunEnvelope:
        """Execute one delegated step and return a strict run envelope."""
