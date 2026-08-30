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
    failure_classification: str | None = None
    failure_stage: str | None = None
    return_code: int | None = None
    runtime_identity_established: bool = False
    session_initialized: bool | None = None
    provider_request_started: bool | None = None
    oauth_available: bool | None = None

    # Bounded Pi 0.82.1 tool activation + execution telemetry.
    # Evidence only — confers no execution authority.
    # Optional on readiness path; required on successful live authorized task.
    effective_tool_names: tuple[str, ...] | None = None
    write_tool_available: bool | None = None
    tool_execution_start_count: int | None = Field(default=None, ge=0)
    tool_execution_end_count: int | None = Field(default=None, ge=0)
    executed_tool_names: tuple[str, ...] | None = None
    assistant_tool_call_count: int | None = Field(default=None, ge=0)

    # Bounded Pi 0.82.1 assistant-response telemetry.
    # Records only type names and counts.  Never text/reasoning/args/IDs.
    # `assistant_message_count` is the count of assistant-role messages in
    # the final session state.
    # `assistant_content_block_types` is an ordered unique tuple of Pi
    # AssistantMessage.content[*].type values (e.g. "text", "thinking",
    # "toolCall").
    # `assistant_message_event_types` is an ordered unique tuple of
    # event.assistantMessageEvent.type values observed on
    # message_update events (e.g. "text_start", "text_delta", "text_end",
    # "thinking_*", "toolcall_*", "done", "error").
    # `assistant_tool_call_event_count` is the count of message_update
    # events carrying assistantMessageEvent.type in
    # {"toolcall_start","toolcall_delta","toolcall_end"}.
    assistant_message_count: int | None = Field(default=None, ge=0)
    assistant_content_block_types: tuple[str, ...] | None = None
    assistant_message_event_types: tuple[str, ...] | None = None
    assistant_tool_call_event_count: int | None = Field(default=None, ge=0)

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
