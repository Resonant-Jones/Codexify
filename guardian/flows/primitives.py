"""Primitive contracts and registry for Flow Compiler v0.1."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from pydantic import BaseModel, ConfigDict, Field

from guardian.flows.spec import PrimitiveName

PrimitiveHandler = Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]


class AssembleContextParams(BaseModel):
    intent: str = Field(min_length=1)
    sources: dict[str, bool] = Field(default_factory=dict)
    window: dict[str, int] = Field(default_factory=dict)
    query: str | None = None
    search_depth: int = Field(default=2, ge=1, le=10)
    max_items: int = Field(default=50, ge=1, le=500)

    model_config = ConfigDict(extra="forbid")


class RetrieveMemoryParams(BaseModel):
    query: str = Field(min_length=1)
    scope: str = Field(default="all", min_length=1, max_length=64)
    k: int = Field(default=10, ge=1, le=200)
    confidence_threshold: float = Field(default=0.0, ge=0.0, le=1.0)
    search_depth: int = Field(default=2, ge=1, le=10)

    model_config = ConfigDict(extra="forbid")


class SummarizeParams(BaseModel):
    schema_name: str = Field(min_length=1)
    instructions: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class ClassifyParams(BaseModel):
    schema_name: str = Field(min_length=1)
    labels: list[str] = Field(min_length=1)
    instructions: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class PlanParams(BaseModel):
    schema_name: str = Field(default="plan_v1", min_length=1)
    instructions: list[str] = Field(default_factory=list)
    horizon: str | None = None

    model_config = ConfigDict(extra="forbid")


class ExtractActionsParams(BaseModel):
    schema_name: str = Field(min_length=1)
    max_actions: int = Field(default=5, ge=1, le=20)
    actionable_definition: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class CreateThreadParams(BaseModel):
    title_template: str = Field(min_length=1)
    body_template: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class AppendThreadParams(BaseModel):
    thread_id: str = Field(min_length=1)
    body_template: dict[str, Any] = Field(default_factory=dict)
    content: str | None = None

    model_config = ConfigDict(extra="forbid")


class WriteCodexEntryParams(BaseModel):
    title_template: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)
    content_from_steps: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class ScheduleCronJobParams(BaseModel):
    schedule: str = Field(min_length=1, max_length=128)
    job_type: str = Field(default="flow", min_length=1, max_length=64)
    payload: dict[str, Any] = Field(default_factory=dict)
    name: str | None = None

    model_config = ConfigDict(extra="forbid")


class EmitEventParams(BaseModel):
    event_name: str = Field(min_length=1)
    payload_from_steps: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


@dataclass(frozen=True)
class PrimitiveContract:
    """Contract metadata for a primitive."""

    name: PrimitiveName
    description: str
    params_model: type[BaseModel]
    side_effecting: bool = False


@dataclass(frozen=True)
class PrimitiveRegistration:
    """Registry entry of contract and callable handler."""

    contract: PrimitiveContract
    handler: PrimitiveHandler


def _stub_handler(name: PrimitiveName) -> PrimitiveHandler:
    """Return deterministic no-op handler for registry bootstrap."""

    def _handler(
        params: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        return {
            "primitive": name,
            "ok": True,
            "stub": True,
            "params": params,
            "context_keys": sorted(context.keys()),
        }

    return _handler


class PrimitiveRegistry:
    """Maps primitive names to typed contracts and callable handlers."""

    def __init__(self) -> None:
        self._entries: dict[PrimitiveName, PrimitiveRegistration] = {}

    def register(
        self, contract: PrimitiveContract, handler: PrimitiveHandler
    ) -> None:
        self._entries[contract.name] = PrimitiveRegistration(
            contract=contract, handler=handler
        )

    def has(self, primitive_name: PrimitiveName) -> bool:
        return primitive_name in self._entries

    def get(self, primitive_name: PrimitiveName) -> PrimitiveRegistration:
        if primitive_name not in self._entries:
            raise KeyError(f"Primitive not registered: {primitive_name}")
        return self._entries[primitive_name]

    def validate_params(
        self, primitive_name: PrimitiveName, params: dict[str, Any]
    ) -> dict[str, Any]:
        registration = self.get(primitive_name)
        parsed = registration.contract.params_model.model_validate(params)
        return parsed.model_dump(mode="json")

    def invoke(
        self,
        primitive_name: PrimitiveName,
        params: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        registration = self.get(primitive_name)
        normalized = self.validate_params(primitive_name, params)
        return registration.handler(normalized, context or {})

    def catalog(self) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        for name in sorted(self._entries):
            contract = self._entries[name].contract
            entries.append(
                {
                    "name": contract.name,
                    "description": contract.description,
                    "side_effecting": contract.side_effecting,
                    "params_schema": contract.params_model.model_json_schema(),
                }
            )
        return entries

    @classmethod
    def default(cls) -> PrimitiveRegistry:
        registry = cls()
        contracts: list[PrimitiveContract] = [
            PrimitiveContract(
                name="assemble_context",
                description="Collect thread/memory/codex context for downstream steps.",
                params_model=AssembleContextParams,
            ),
            PrimitiveContract(
                name="retrieve_memory",
                description="Retrieve semantic memory snippets for a query.",
                params_model=RetrieveMemoryParams,
            ),
            PrimitiveContract(
                name="summarize",
                description="Generate structured summary output from context.",
                params_model=SummarizeParams,
            ),
            PrimitiveContract(
                name="classify",
                description="Classify context into provided labels.",
                params_model=ClassifyParams,
            ),
            PrimitiveContract(
                name="plan",
                description="Generate a structured plan artifact.",
                params_model=PlanParams,
            ),
            PrimitiveContract(
                name="extract_actions",
                description="Extract concrete next actions from context.",
                params_model=ExtractActionsParams,
            ),
            PrimitiveContract(
                name="create_thread",
                description="Create a new thread artifact.",
                params_model=CreateThreadParams,
                side_effecting=True,
            ),
            PrimitiveContract(
                name="append_thread",
                description="Append content to an existing thread.",
                params_model=AppendThreadParams,
                side_effecting=True,
            ),
            PrimitiveContract(
                name="write_codex_entry",
                description="Write a codex entry from previous outputs.",
                params_model=WriteCodexEntryParams,
                side_effecting=True,
            ),
            PrimitiveContract(
                name="schedule_cron_job",
                description="Schedule a cron job from flow output.",
                params_model=ScheduleCronJobParams,
                side_effecting=True,
            ),
            PrimitiveContract(
                name="emit_event",
                description="Emit an event with selected step payloads.",
                params_model=EmitEventParams,
                side_effecting=True,
            ),
        ]
        for contract in contracts:
            registry.register(contract, _stub_handler(contract.name))
        return registry


def export_primitive_catalog(
    registry: PrimitiveRegistry | None = None,
) -> list[dict[str, Any]]:
    """Return a machine-readable primitive catalog."""
    return (registry or PrimitiveRegistry.default()).catalog()
