"""FlowSpec and FlowRun models for flow compiler v0.1."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

FLOW_SPEC_VERSION = "0.1"

PrimitiveName = Literal[
    "assemble_context",
    "retrieve_memory",
    "summarize",
    "classify",
    "plan",
    "extract_actions",
    "create_thread",
    "append_thread",
    "write_codex_entry",
    "schedule_cron_job",
    "emit_event",
]


class FlowTrigger(BaseModel):
    """Defines how a flow is started."""

    type: Literal["manual", "cron", "event"] = "manual"
    schedule: str | None = None
    event_name: str | None = None

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_trigger(self) -> "FlowTrigger":
        if self.type == "cron" and not self.schedule:
            raise ValueError("trigger.schedule is required when trigger.type='cron'")
        if self.type != "cron" and self.schedule is not None:
            raise ValueError("trigger.schedule is only valid when trigger.type='cron'")
        if self.type == "event" and not self.event_name:
            raise ValueError("trigger.event_name is required when trigger.type='event'")
        if self.type != "event" and self.event_name is not None:
            raise ValueError("trigger.event_name is only valid when trigger.type='event'")
        return self


class FlowScope(BaseModel):
    """Identity and visibility boundaries for a flow run."""

    user_id: str = Field(min_length=1)
    project_ids: list[str] = Field(default_factory=list)
    thread_ids: list[str] = Field(default_factory=list)
    persona: str | None = None

    model_config = ConfigDict(extra="forbid")


class FlowBudget(BaseModel):
    """Resource limits for deterministic execution."""

    max_steps: int = Field(default=10, ge=1, le=200)
    max_tokens: int = Field(default=4000, ge=1, le=200000)
    timeout_seconds: int = Field(default=120, ge=1, le=3600)

    model_config = ConfigDict(extra="forbid")


class FlowPolicy(BaseModel):
    """Safety and confirmation policy for execution."""

    min_confidence: float = Field(default=0.75, ge=0.0, le=1.0)
    require_confirmation_below_threshold: bool = True
    allow_side_effects_without_confirmation: bool = False

    model_config = ConfigDict(extra="forbid")


class StepBase(BaseModel):
    """Base step shape shared by all primitive-specific step variants."""

    step_id: str = Field(min_length=1, max_length=128)
    params: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class AssembleContextStep(StepBase):
    primitive: Literal["assemble_context"]


class RetrieveMemoryStep(StepBase):
    primitive: Literal["retrieve_memory"]


class SummarizeStep(StepBase):
    primitive: Literal["summarize"]


class ClassifyStep(StepBase):
    primitive: Literal["classify"]


class PlanStep(StepBase):
    primitive: Literal["plan"]


class ExtractActionsStep(StepBase):
    primitive: Literal["extract_actions"]


class CreateThreadStep(StepBase):
    primitive: Literal["create_thread"]


class AppendThreadStep(StepBase):
    primitive: Literal["append_thread"]


class WriteCodexEntryStep(StepBase):
    primitive: Literal["write_codex_entry"]


class ScheduleCronJobStep(StepBase):
    primitive: Literal["schedule_cron_job"]


class EmitEventStep(StepBase):
    primitive: Literal["emit_event"]


FlowStep = Annotated[
    AssembleContextStep
    | RetrieveMemoryStep
    | SummarizeStep
    | ClassifyStep
    | PlanStep
    | ExtractActionsStep
    | CreateThreadStep
    | AppendThreadStep
    | WriteCodexEntryStep
    | ScheduleCronJobStep
    | EmitEventStep,
    Field(discriminator="primitive"),
]


class FlowOutput(BaseModel):
    """Output sinks for flow execution artifacts."""

    store_as_thread: bool = False
    store_as_codex: bool = False
    emit_event: str | None = None

    model_config = ConfigDict(extra="forbid")


class FlowIdempotency(BaseModel):
    """Idempotency policy for deduplicating executions."""

    key_template: str | None = None
    mode: Literal["return_cached", "always_run", "skip_if_running"] = "return_cached"

    model_config = ConfigDict(extra="forbid")


class FlowAudit(BaseModel):
    """Audit and trace preferences."""

    log_trace: bool = True
    record_cost: bool = True
    redact_fields: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class FlowSpec(BaseModel):
    """Canonical flow definition used by compile and execution stages."""

    flow_id: str = Field(min_length=1, max_length=128)
    version: Literal["0.1"] = FLOW_SPEC_VERSION
    enabled: bool = True
    trigger: FlowTrigger = Field(default_factory=FlowTrigger)
    scope: FlowScope
    budget: FlowBudget = Field(default_factory=FlowBudget)
    policy: FlowPolicy = Field(default_factory=FlowPolicy)
    steps: list[FlowStep] = Field(min_length=1)
    output: FlowOutput = Field(default_factory=FlowOutput)
    idempotency: FlowIdempotency = Field(default_factory=FlowIdempotency)
    audit: FlowAudit = Field(default_factory=FlowAudit)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_step_ids_and_budget(self) -> "FlowSpec":
        step_ids = [step.step_id for step in self.steps]
        if len(step_ids) != len(set(step_ids)):
            raise ValueError("steps.step_id values must be unique")
        if len(self.steps) > self.budget.max_steps:
            raise ValueError("steps length cannot exceed budget.max_steps")
        return self


class FlowStepResult(BaseModel):
    """Runtime trace for a single executed step."""

    step_id: str
    primitive: PrimitiveName
    status: Literal["ok", "error", "skipped", "blocked"] = "ok"
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc)
    )
    ended_at: datetime | None = None
    params_redacted: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    token_usage: int | None = Field(default=None, ge=0)

    model_config = ConfigDict(extra="forbid")


class FlowRun(BaseModel):
    """Result envelope returned by deterministic flow execution."""

    run_id: str = Field(min_length=1)
    flow_id: str = Field(min_length=1)
    version: Literal["0.1"] = FLOW_SPEC_VERSION
    status: Literal["pending", "running", "success", "failed", "blocked", "cached"] = (
        "pending"
    )
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc)
    )
    ended_at: datetime | None = None
    step_results: list[FlowStepResult] = Field(default_factory=list)
    output: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None
    idempotency_key: str | None = None
    needs_confirmation: bool = False

    model_config = ConfigDict(extra="forbid")
