# guardian/tools/spec.py
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

HttpMethod = Literal["GET", "POST", "PUT", "PATCH", "DELETE"]


class ToolPolicy(BaseModel):
    # Access control
    visibility: Literal["public", "internal", "admin"] = "public"
    require_identity: bool = True

    # Safety posture
    side_effects: bool = False  # writes/mutations
    network_egress: bool = False  # any outbound net access
    egress_domains: list[str] = Field(default_factory=list)

    # Execution constraints
    rate_limit: str | None = None  # "60/min", etc
    timeout_seconds: int | None = None

    # Command bus constraints
    require_loopback: bool = True  # your opinionated default for Docker mode
    allow_in_automations: bool = True  # can be invoked by scheduler lane


class ToolArgSpec(BaseModel):
    # JSON-schema-like payloads (don’t overcomplicate initially)
    schema: dict[str, Any] = Field(default_factory=dict)
    required: list[str] = Field(default_factory=list)
    examples: list[dict[str, Any]] = Field(default_factory=list)


class ToolSpec(BaseModel):
    # Stable tool identifier (what the model uses)
    tool_id: str

    # Linkage to command bus
    command_id: str
    operation_id: str | None = None

    # HTTP mapping (useful for introspection / UI)
    method: HttpMethod
    path_template: str

    # Human affordances
    title: str
    description: str = ""

    # Args and policy
    args: ToolArgSpec = Field(default_factory=ToolArgSpec)
    policy: ToolPolicy = Field(default_factory=ToolPolicy)

    # Manifest versioning (tool registry)
    tool_version: str = "1.0"
