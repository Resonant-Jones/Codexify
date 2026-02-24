"""Canonical ToolSpec schema for model-callable tool definitions."""

from __future__ import annotations

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

    tool_id: str
    name: str
    description: str = ""
    input_schema: dict[str, Any] = Field(default_factory=default_internal_invoke_schema)
    risk: RiskLevel = "unknown"
    effect: Effect = "unknown"
    idempotency: Idempotency = "unknown"
    requires_confirmation: bool = False
    tags: list[str] = Field(default_factory=list)

    command_id: str
    operation_id: str | None = None
    method: HttpMethod = "GET"
    path_template: str = "/"
    aliases: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")

    def to_openai_function_tool(self) -> dict[str, Any]:
        """Render OpenAI function-calling tool shape."""

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description or self.command_id,
                "parameters": self.input_schema or default_internal_invoke_schema(),
            },
        }

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
            dict(args.get("query")) if isinstance(args.get("query"), dict) else {}
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
