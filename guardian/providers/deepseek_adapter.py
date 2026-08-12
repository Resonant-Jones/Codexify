"""DeepSeek-specific request, response, and bounded replay handling."""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class DeepSeekResponse:
    content: str
    reasoning_content: str | None
    tool_calls: list[dict[str, Any]]
    raw_assistant_message: dict[str, Any]
    raw_payload: dict[str, Any]

    def __str__(self) -> str:
        return self.content

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str):
            return self.content == other
        if not isinstance(other, DeepSeekResponse):
            return NotImplemented
        return (
            self.content,
            self.reasoning_content,
            self.tool_calls,
            self.raw_assistant_message,
            self.raw_payload,
        ) == (
            other.content,
            other.reasoning_content,
            other.tool_calls,
            other.raw_assistant_message,
            other.raw_payload,
        )


def thinking_enabled(reasoning_mode: str | None) -> bool:
    return str(reasoning_mode or "").strip().lower() in {"think", "/think"}


def build_payload(
    *,
    model: str,
    messages: list[dict[str, Any]],
    reasoning_mode: str | None = None,
    temperature: float | None = None,
    tools: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    enabled = thinking_enabled(reasoning_mode)
    payload: dict[str, Any] = {
        "model": model,
        "messages": copy.deepcopy(messages),
        "thinking": {"type": "enabled" if enabled else "disabled"},
    }
    if enabled:
        payload["reasoning_effort"] = "high"
    else:
        payload["temperature"] = 0.7 if temperature is None else float(temperature)
    if tools:
        payload["tools"] = copy.deepcopy(tools)
    return payload


def parse_response(payload: Mapping[str, Any]) -> DeepSeekResponse:
    choices = payload.get("choices")
    message = choices[0].get("message") if isinstance(choices, list) and choices else {}
    if not isinstance(message, dict):
        message = {}
    raw_message = copy.deepcopy(message)
    raw_calls = message.get("tool_calls")
    tool_calls = copy.deepcopy(raw_calls) if isinstance(raw_calls, list) else []
    content = message.get("content")
    return DeepSeekResponse(
        content=content if isinstance(content, str) else "",
        reasoning_content=(
            message.get("reasoning_content")
            if isinstance(message.get("reasoning_content"), str)
            else None
        ),
        tool_calls=tool_calls,
        raw_assistant_message=raw_message,
        raw_payload=copy.deepcopy(dict(payload)),
    )


def build_tool_definitions(
    authorized_commands: Mapping[str, Mapping[str, Any]] | list[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """Create opaque aliases for the already-authorized command subset."""
    items = (
        list(authorized_commands.items())
        if isinstance(authorized_commands, Mapping)
        else [(str(item.get("command_id") or ""), item) for item in authorized_commands]
    )
    definitions: list[dict[str, Any]] = []
    aliases: dict[str, str] = {}
    for index, (command_id, spec) in enumerate(items):
        command_id = str(command_id or "").strip()
        if not command_id:
            continue
        alias = f"codexify_tool_{index}"
        aliases[alias] = command_id
        function: dict[str, Any] = {
            "name": alias,
            "description": str(spec.get("description") or "Authorized Codexify tool"),
            "parameters": copy.deepcopy(
                spec.get("input_schema") or spec.get("parameters") or {}
            ),
        }
        definitions.append({"type": "function", "function": function})
    return definitions, aliases


def normalize_tool_calls(
    response: DeepSeekResponse,
    aliases: Mapping[str, str] | None = None,
) -> list[dict[str, Any]]:
    aliases = aliases or {}
    normalized: list[dict[str, Any]] = []
    for call in response.tool_calls:
        if isinstance(call, dict) and "command_id" in call:
            normalized.append(copy.deepcopy(call))
            continue
        function = call.get("function") if isinstance(call, dict) else None
        if not isinstance(function, dict):
            function = {}
        alias = str(function.get("name") or "").strip()
        normalized.append(
            {
                "tool_call_id": str(call.get("id") or "").strip(),
                "command_id": aliases.get(alias, ""),
                "alias": alias,
                "arguments": function.get("arguments") or {},
            }
        )
    return normalized


def build_continuation_messages(
    messages: list[dict[str, Any]],
    *,
    raw_assistant_message: Mapping[str, Any] | None,
    tool_call_id: str,
    command_result: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    """Translate the canonical tool result into the DeepSeek continuation shape.

    Continuation semantics follow the DeepSeek Chat Completions API guide and
    the Thinking Mode guide (see
    ``docs/architecture/provider-tool-turn-boundary-contract.md``). The adapter
    owns the wire translation; the caller (the generic Guardian tool-loop
    runtime) only provides:

    - The semantic raw assistant message envelope (the router already captured
      it from the provider response; it is opaque at this seam).
    - The provider-side tool-call correlation identity (``tool_call_id``).
    - The Command Bus execution result (semantic, ``command_result``).

    The adapter:

    - Replays the assistant message including any provider-private continuation
      material such as ``reasoning_content`` inside the message envelope. The
      generic runtime never inspects that field.
    - Appends a ``role: tool`` continuation message with the correct
      ``tool_call_id`` so the provider can correlate the result back to the
      original native tool call.

    The function does not decide authority, does not execute anything, and does
    not parse the command_result. It is a pure translation.
    """
    next_messages = [
        dict(message) for message in messages if isinstance(message, dict)
    ]
    if raw_assistant_message is not None:
        next_messages.append(dict(raw_assistant_message))
    next_messages.append(
        {
            "role": "tool",
            "tool_call_id": str(tool_call_id or ""),
            "content": json.dumps(
                dict(command_result or {}), ensure_ascii=False, default=str
            ),
        }
    )
    return next_messages
