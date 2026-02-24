"""Canonical ToolSpec and manifest envelope schemas."""

from __future__ import annotations

import hashlib
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

HttpMethod = Literal[
    "GET",
    "HEAD",
    "POST",
    "PUT",
    "PATCH",
    "DELETE",
    "OPTIONS",
]
RiskLevel = Literal["read_only", "mutating", "unknown"]
Effect = Literal["read", "write", "unknown"]
Idempotency = Literal["safe", "unsafe", "unknown"]


def default_internal_invoke_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "path_params": {"type": "object", "properties": {}},
            "query": {"type": "object", "properties": {}},
            "headers": {"type": "object", "properties": {}},
            "body": {},
        },
        "additionalProperties": False,
    }


class ToolSpec(BaseModel):
    """Canonical tool descriptor derived from command-bus manifest entries."""

    tool_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str
    input_schema: dict[str, Any]
    risk: RiskLevel
    effect: Effect
    idempotency: Idempotency
    requires_confirmation: bool
    tags: list[str] = Field(default_factory=list)

    command_id: str = Field(min_length=1)
    operation_id: str | None = None
    method: HttpMethod
    path_template: str = Field(min_length=1)
    aliases: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")

    def to_openai_function_tool(self) -> dict[str, Any]:
        """Render OpenAI function-calling tool shape."""

        return {
            "type": "function",
            "function": {
                "name": self.openai_function_name(),
                "description": self.description or self.command_id,
                "parameters": self.input_schema
                or default_internal_invoke_schema(),
            },
        }

    def openai_function_name(self) -> str:
        """Return a stable, OpenAI-safe function name derived from tool identity."""

        base = _sanitize_name(self.name or self.tool_id)
        digest = hashlib.sha1(self.tool_id.encode("utf-8")).hexdigest()[:8]
        suffix = f"_{digest}"
        max_base_len = max(1, 64 - len(suffix))
        return f"{base[:max_base_len]}{suffix}"

    def to_internal_invoke_args(
        self, raw_args: dict[str, Any] | None
    ) -> dict[str, Any]:
        """Normalize model/tool-call args into command-bus invoke arguments."""

        args = dict(raw_args or {})
        path_params = (
            dict(args.get("path_params"))
            if isinstance(args.get("path_params"), dict)
            else {}
        )
        query = (
            dict(args.get("query"))
            if isinstance(args.get("query"), dict)
            else {}
        )
        headers = (
            dict(args.get("headers"))
            if isinstance(args.get("headers"), dict)
            else {}
        )
        body = args.get("body") if "body" in args else None

        has_explicit_transport_keys = any(
            key in args for key in ("path_params", "query", "headers", "body")
        )
        if not has_explicit_transport_keys and args:
            if self.method in {"GET", "HEAD"}:
                query = dict(args)
            else:
                body = args

        return {
            "path_params": path_params,
            "query": query,
            "headers": headers,
            "body": body,
        }


class ToolManifestEnvelope(BaseModel):
    """Stable envelope returned by /tools/manifest and /api/tools/manifest."""

    tool_manifest_version: str = "2.0"
    manifest_version: str = Field(min_length=1)
    generated_at: str = Field(min_length=1)
    command_manifest_hash: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-f]{64}$",
    )
    tools: list[ToolSpec] = Field(default_factory=list)
    openai_tools: list[dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


_NON_NAME_CHARS = re.compile(r"[^A-Za-z0-9_]+")


def _sanitize_name(raw: str) -> str:
    value = _NON_NAME_CHARS.sub("_", raw).strip("_")
    if not value:
        value = "tool"
    if not (value[0].isalpha() or value[0] == "_"):
        value = f"tool_{value}"
    return value
