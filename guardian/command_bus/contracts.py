"""Contracts and protocol constants for the command bus."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from guardian.extensions.tokens import (
    normalize_extension_install_binding_scope,
)
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


class InvokePermissionProfile(BaseModel):
    """Optional supplied profile for pre-dispatch permission checks."""

    profile_id: str = Field(min_length=1, max_length=255)
    actor_id: str = Field(min_length=1, max_length=255)
    subject_id: str = Field(min_length=1, max_length=255)
    task_id: str = Field(min_length=1, max_length=255)
    project_id: str | None = Field(default=None, max_length=255)
    thread_id: str | None = Field(default=None, max_length=255)
    allowed_command_classes: tuple[str, ...] = Field(default_factory=tuple)
    denied_command_classes: tuple[str, ...] = Field(default_factory=tuple)
    allowed_command_ids: tuple[str, ...] = Field(default_factory=tuple)
    denied_command_ids: tuple[str, ...] = Field(default_factory=tuple)
    filesystem_access: Literal["none", "read_only", "write_scoped"] = "none"
    allowed_write_roots: tuple[str, ...] = Field(default_factory=tuple)
    shell_allowed: bool = False
    shell_read_only: bool = True
    allowed_shell_commands: tuple[str, ...] = Field(default_factory=tuple)
    network_allowed: bool = False
    connector_allowed: bool = False

    # Optional explicit request metadata for evaluator construction.
    request_task_id: str | None = Field(default=None, max_length=255)
    request_project_id: str | None = Field(default=None, max_length=255)
    request_thread_id: str | None = Field(default=None, max_length=255)
    request_command_class: str | None = Field(default=None, max_length=64)
    requested_write_paths: tuple[str, ...] = Field(default_factory=tuple)
    uses_shell: bool = False
    shell_command: str | None = Field(default=None, max_length=1024)
    shell_mutates: bool = False
    uses_network: bool = False
    uses_connector: bool = False

    model_config = ConfigDict(extra="forbid")


class InvokeExternalPolicyRule(BaseModel):
    """Optional supplied rule for external transport policy checks."""

    effect: Literal["allow", "deny"]
    connector_name: str | None = Field(default=None, max_length=255)
    transport: str | None = Field(default=None, max_length=64)
    command_namespace: str | None = Field(default=None, max_length=255)
    command_name: str | None = Field(default=None, max_length=255)
    url_host_pattern: str | None = Field(default=None, max_length=512)
    url_scheme: str | None = Field(default=None, max_length=32)
    project_id: str | None = Field(default=None, max_length=255)
    thread_id: str | None = Field(default=None, max_length=255)
    reason: str = Field(default="", max_length=1024)

    model_config = ConfigDict(extra="forbid")


class InvokeRequest(BaseModel):
    """Command invocation payload."""

    invoke_version: str = Field(min_length=1, max_length=32)
    command_id: str = Field(min_length=1, max_length=512)
    actor: ActorSpec
    arguments: InvokeArguments = Field(default_factory=InvokeArguments)
    idempotency_key: str | None = Field(default=None, max_length=255)
    provenance_json: dict[str, Any] = Field(default_factory=dict)
    permission_profile: InvokePermissionProfile | None = None
    external_transport: str | None = Field(default=None, max_length=64)
    external_target_url: str | None = Field(default=None, max_length=2048)
    external_policy_rules: tuple[InvokeExternalPolicyRule, ...] = Field(
        default_factory=tuple
    )
    external_command_namespace: str | None = Field(
        default=None, max_length=255
    )
    external_command_name: str | None = Field(default=None, max_length=255)
    external_project_id: str | None = Field(default=None, max_length=255)
    external_thread_id: str | None = Field(default=None, max_length=255)
    external_connector_name: str | None = Field(default=None, max_length=255)

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


class CapabilityManualDispatchResult(BaseModel):
    """Manual command-bus dispatch result with bounded extension lineage."""

    manual_dispatch_id: str = Field(min_length=1, max_length=255)
    account_id: str = Field(min_length=1, max_length=255)
    proposal_id: str = Field(min_length=1, max_length=255)
    registry_entry_id: str = Field(min_length=1, max_length=255)
    effective_binding_id: str = Field(min_length=1, max_length=255)
    resolved_from_scope_token: str = Field(min_length=1, max_length=64)
    command_bus_run_id: str | None = Field(default=None, max_length=255)
    command_bus_result_json: dict[str, Any] = Field(default_factory=dict)
    manifest_snapshot_json: dict[str, Any] = Field(default_factory=dict)
    approved_permissions_json: list[dict[str, Any]] = Field(default_factory=list)
    dispatch_metadata_json: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")

    @field_validator("resolved_from_scope_token")
    @classmethod
    def _validate_scope_token(cls, value: str) -> str:
        return normalize_extension_install_binding_scope(value)

    @classmethod
    def from_payload(
        cls, payload: dict[str, Any] | None
    ) -> "CapabilityManualDispatchResult":
        return cls.model_validate(dict(payload or {}))

    def to_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
