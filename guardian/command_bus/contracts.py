"""Contracts and protocol constants for the command bus."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from guardian.protocol_tokens import ToolLoopStopReason, ToolTurnState

MANIFEST_VERSION = "1.0"
INVOKE_VERSION = "1.0"
EVENT_PROTOCOL_VERSION = "1.0"
MAX_PAYLOAD_BYTES = 262_144

EVENT_TYPES_SUPPORTED = [
    "run.created",
    "run.started",
    "run.completed",
    "run.failed",
    "run.blocked",
]

APPROVAL_MODES_SUPPORTED = ["none", "blocked_phase1"]


class ActorSpec(BaseModel):
    """Caller identity attached to each invoke request."""

    kind: Literal["human", "agent", "system"]
    id: str = Field(min_length=1, max_length=255)
    session_id: str | None = Field(default=None, max_length=255)
    delegated_by: str | None = Field(default=None, max_length=255)

    model_config = ConfigDict(extra="forbid")


class InvokeArguments(BaseModel):
    """Transport-agnostic command arguments."""

    path_params: dict[str, Any] = Field(default_factory=dict)
    query: dict[str, Any] = Field(default_factory=dict)
    headers: dict[str, Any] = Field(default_factory=dict)
    body: dict[str, Any] | list[Any] | str | int | float | bool | None = None

    model_config = ConfigDict(extra="forbid")


class InvokeRequest(BaseModel):
    """Command invocation payload."""

    invoke_version: str = Field(min_length=1, max_length=32)
    command_id: str = Field(min_length=1, max_length=512)
    actor: ActorSpec
    arguments: InvokeArguments = Field(default_factory=InvokeArguments)
    idempotency_key: str | None = Field(default=None, max_length=255)

    model_config = ConfigDict(extra="forbid")


class CommandBusInvokeResult(BaseModel):
    """Normalized command-bus invoke response."""

    run_id: str
    status: Literal["queued", "running", "completed", "blocked", "failed"]
    invoke_version: str | None = None
    manifest_version: str | None = None
    events_url: str | None = None
    inline_result: dict[str, Any] | None = None
    error: str | None = None
    warning: str | None = None
    policy_warnings: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class BoundedToolTurnInvocation(BaseModel):
    """Bounded chat-tool turn request routed through the command bus."""

    tool_turn_id: str = Field(min_length=1, max_length=255)
    request_id: str = Field(min_length=1, max_length=255)
    command_id: str = Field(min_length=1, max_length=512)
    actor: ActorSpec
    arguments: InvokeArguments = Field(default_factory=InvokeArguments)
    idempotency_key: str | None = Field(default=None, max_length=255)

    model_config = ConfigDict(extra="forbid")


class CommandSpec(BaseModel):
    """Raw command manifest entry."""

    command_id: str
    aliases: list[str] = Field(default_factory=list)
    layer: Literal["raw"] = "raw"
    method: str
    path_template: str
    operation_id: str | None = None
    risk: Literal["read_only", "mutating"]
    effect: Literal["read", "write"]
    idempotency: Literal["safe", "unsafe"]
    approval_mode: Literal["none", "blocked_phase1"]
    input_schema: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class CapabilitiesSpec(BaseModel):
    """Server capabilities for version negotiation."""

    invoke_versions_supported: list[str] = Field(
        default_factory=lambda: [INVOKE_VERSION]
    )
    event_protocol_version: str = EVENT_PROTOCOL_VERSION
    event_types_supported: list[str] = Field(
        default_factory=lambda: list(EVENT_TYPES_SUPPORTED)
    )
    approval_modes_supported: list[str] = Field(
        default_factory=lambda: list(APPROVAL_MODES_SUPPORTED)
    )
    max_payload_bytes: int = MAX_PAYLOAD_BYTES

    model_config = ConfigDict(extra="forbid")


class ManifestResponse(BaseModel):
    """Manifest response payload."""

    manifest_version: str = MANIFEST_VERSION
    generated_at: str
    capabilities: CapabilitiesSpec
    commands: list[CommandSpec]

    model_config = ConfigDict(extra="forbid")


class BoundedToolTurnResult(BaseModel):
    """Machine-readable outcome for the bounded chat tool turn."""

    tool_turn_id: str = Field(min_length=1, max_length=255)
    request_id: str = Field(min_length=1, max_length=255)
    command_run_id: str | None = Field(default=None, max_length=255)
    tool_turn_state: ToolTurnState = ToolTurnState.IDLE
    loop_stop_reason: ToolLoopStopReason = ToolLoopStopReason.PLAIN_ANSWER
    command_status: str | None = Field(default=None, max_length=64)
    command_error: dict[str, Any] | None = None

    model_config = ConfigDict(extra="forbid")
