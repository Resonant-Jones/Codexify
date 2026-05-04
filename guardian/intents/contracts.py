"""Canonical intent spine contracts.

The first operational slice currently supports command-bus invocation and
cron job creation as dispatch targets. The envelope is intentionally broader
so later surfaces can normalize into the same shape without inventing a second
request vocabulary.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from guardian.command_bus.contracts import ActorSpec, InvokeArguments

IntentSourceSurface = Literal["chat", "voice", "automation", "cli", "plugin"]
IntentKind = Literal["command_bus.invoke", "cron.create"]
IntentApprovalState = Literal["pending", "approved", "blocked"]
IntentExecutionState = Literal[
    "accepted",
    "blocked",
    "running",
    "completed",
    "failed",
]


def _intent_id() -> str:
    return f"intent_{uuid4().hex}"


def _requested_at() -> str:
    return datetime.now(timezone.utc).isoformat()


class GuardianIntentScope(BaseModel):
    """Optional user, project, and workspace boundaries for an intent."""

    thread_id: int | None = None
    source_message_id: int | None = None
    project_id: int | None = None
    repo_root: str | None = Field(default=None, max_length=2048)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")

    @field_validator("repo_root")
    @classmethod
    def _normalize_repo_root(cls, value: str | None) -> str | None:
        if value is None:
            return None
        resolved = value.strip()
        return resolved or None


class GuardianIntentPolicy(BaseModel):
    """High-level policy controls for a dispatched intent."""

    approval_required: bool = False
    allow_write_execution: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class GuardianCommandBusIntentTarget(BaseModel):
    """Command-bus dispatch target for the first intent-spine slice."""

    command_id: str = Field(min_length=1, max_length=512)
    arguments: InvokeArguments = Field(default_factory=InvokeArguments)
    idempotency_key: str | None = Field(default=None, max_length=255)

    model_config = ConfigDict(extra="forbid")

    @field_validator("command_id")
    @classmethod
    def _normalize_command_id(cls, value: str) -> str:
        resolved = value.strip()
        if not resolved:
            raise ValueError("command_id is required")
        return resolved


class GuardianCronCreateIntentTarget(BaseModel):
    """Cron-dispatch target for durable scheduled job creation."""

    name: str = Field(min_length=1, max_length=255)
    schedule: str = Field(min_length=1, max_length=128)
    job_type: str = Field(default="noop", min_length=1, max_length=32)
    payload: dict[str, Any] = Field(default_factory=dict)
    is_enabled: bool = True

    model_config = ConfigDict(extra="forbid")

    @field_validator("name", "schedule", "job_type")
    @classmethod
    def _normalize_text(cls, value: str) -> str:
        resolved = value.strip()
        if not resolved:
            raise ValueError("value is required")
        return resolved


GuardianIntentTarget = (
    GuardianCommandBusIntentTarget | GuardianCronCreateIntentTarget
)


class GuardianIntentRequest(BaseModel):
    """Canonical Guardian-owned intent envelope."""

    intent_id: str = Field(
        default_factory=_intent_id, min_length=1, max_length=255
    )
    actor: ActorSpec
    source_surface: IntentSourceSurface
    intent_kind: IntentKind = "command_bus.invoke"
    target: GuardianIntentTarget
    scope: GuardianIntentScope = Field(default_factory=GuardianIntentScope)
    policy: GuardianIntentPolicy = Field(default_factory=GuardianIntentPolicy)
    provenance_json: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str | None = Field(default=None, max_length=255)
    requested_at: str = Field(default_factory=_requested_at, min_length=1)
    approval_state: IntentApprovalState = "pending"
    execution_state: IntentExecutionState | None = None
    receipt_ref: str | None = Field(default=None, max_length=255)

    model_config = ConfigDict(extra="forbid")

    @field_validator("intent_id", "requested_at")
    @classmethod
    def _normalize_text(cls, value: str) -> str:
        resolved = value.strip()
        if not resolved:
            raise ValueError("value is required")
        return resolved


class GuardianIntentDispatchResult(BaseModel):
    """Durable receipt-shaped result for a dispatched Guardian intent."""

    intent_id: str = Field(min_length=1, max_length=255)
    status: Literal["accepted", "blocked", "failed"]
    dispatch_target: Literal["command_bus", "cron"]
    intent_kind: IntentKind = "command_bus.invoke"
    source_surface: IntentSourceSurface
    receipt_ref: str | None = Field(default=None, max_length=255)
    downstream_result_json: dict[str, Any] = Field(default_factory=dict)
    rejection_reason: str | None = Field(default=None, max_length=512)
    execution_state: IntentExecutionState | None = None
    provenance_json: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")
