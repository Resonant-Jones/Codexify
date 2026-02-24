"""ToolSpec schema.

This module defines the canonical, model-facing schema for tools that Guardian may expose
(e.g., via OpenAI tool-calling semantics) and for internal policy evaluation.

Design goals:
- Stable identifiers (tool.name) and deterministic JSON Schema parameters.
- Carry safety-relevant metadata (risk/effect/idempotency/approval).
- Be derivable from the command bus manifest (preferred) or other registries.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class Effect(str, Enum):
    read = "read"
    write = "write"
    mutate = "mutate"
    execute = "execute"  # e.g., shell/system side-effects


class Idempotency(str, Enum):
    idempotent = "idempotent"
    non_idempotent = "non_idempotent"
    unknown = "unknown"


class ApprovalMode(str, Enum):
    never = "never"  # safe by default
    on_write = "on_write"  # require confirmation when effect != read
    always = "always"  # require confirmation regardless


class ToolArgSchema(BaseModel):
    """JSON schema payload for tool parameters.

    We store the schema as an opaque dict to avoid coupling to a specific JSON schema
    library; the command-bus already produces JSONSchema-like dicts.
    """

    schema: dict[str, Any] = Field(default_factory=dict)


class ToolSpec(BaseModel):
    """Canonical tool metadata for model exposure and policy checks."""

    name: str
    description: str

    # Routing/traceability
    command_id: str | None = None
    operation_id: str | None = None
    method: str | None = None
    path_template: str | None = None
    aliases: list[str] = Field(default_factory=list)

    # Safety metadata
    risk: RiskLevel = RiskLevel.low
    effect: Effect = Effect.read
    idempotency: Idempotency = Idempotency.unknown
    approval_mode: ApprovalMode = ApprovalMode.never

    # Model calling shape
    args_schema: ToolArgSchema = Field(default_factory=ToolArgSchema)

    # Optional: capability tags / namespaces
    tags: list[str] = Field(default_factory=list)

    def to_openai_tool(self) -> dict[str, Any]:
        """Convert to the OpenAI tool schema (function tool)."""

        # OpenAI expects: {"type":"function","function":{name,description,parameters}}
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": (
                    self.args_schema.schema
                    or {"type": "object", "properties": {}}
                ),
            },
        }


class ActorKind(str, Enum):
    human = "human"
    agent = "agent"
    system = "system"


class ActorSpec(BaseModel):
    kind: ActorKind
    id: str


class PolicyDecisionType(str, Enum):
    allow = "allow"
    require_confirmation = "require_confirmation"
    deny = "deny"


class PolicyDecision(BaseModel):
    decision: PolicyDecisionType
    reason: str
    tool: str
    risk: RiskLevel
    effect: Effect
    approval_mode: ApprovalMode
    # If confirmation is required, the caller can attach a user-facing message.
    confirm_message: str | None = None
