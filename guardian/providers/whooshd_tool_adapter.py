"""Identity-pinned strict-structured transport for the qualified Whoosh'd target.

This module owns provider-wire translation only.  It deliberately does not
decide which capabilities Guardian advertises, grant authority, or execute a
command.  The pin is temporary containment for the one Stage 2D proof identity
and is not a provider-wide capability declaration.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from guardian.providers.whooshd_control_plane import (
    WhooshdRuntimeProvenance,
    parse_whooshd_runtime_provenance,
)
from guardian.providers.whooshd_qualification import (
    STAGE_2D_GEMMA_4_12B_IT_QAT_4BIT_RECORD,
    WhooshdQualificationOutcome,
    compare_whooshd_qualification,
)

QUALIFIED_VENDOR = "whooshd"
QUALIFIED_MODEL_ALIAS = "gemma-4-12b-it-qat-4bit"
QUALIFIED_RUNTIME_KIND = "mlx_vlm"
QUALIFIED_ADAPTER_NAME = "mlx-vlm"
QUALIFIED_RESOLUTION_SOURCE = "authoritative_registry"
QUALIFIED_EXECUTION_MODE = "managed_sidecar"
_MODEL_TURN_FIELDS = frozenset({"kind", "text", "command_id", "arguments"})
_SUPPORTED_OBJECT_SCHEMA_FIELDS = frozenset(
    {"type", "additionalProperties", "required", "properties"}
)
_SUPPORTED_STRING_SCHEMA_FIELDS = frozenset({"type", "enum"})
_MAX_ENUM_VALUES = 32
_MAX_ENUM_VALUE_LENGTH = 256


class WhooshdStructuredTransportError(ValueError):
    """A strict-structured transport precondition or response failure."""


@dataclass(frozen=True)
class PreparedWhooshdStructuredTransport:
    """The provider-only request material for one authorized tool definition."""

    command_id: str
    argument_schema: dict[str, Any]
    transport_instruction: str
    response_format: dict[str, Any]

    def inject_messages(
        self, messages: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        return [
            {"role": "system", "content": self.transport_instruction},
            *[
                dict(message)
                for message in messages
                if isinstance(message, dict)
            ],
        ]


@dataclass(frozen=True)
class WhooshdStructuredResponse:
    """Non-streaming response carrying the strict transport context."""

    content: str
    raw_payload: dict[str, Any]
    runtime_provenance: Any | None
    response_correlation: dict[str, str] | None
    command_id: str
    argument_schema: dict[str, Any]
    provider: str = QUALIFIED_VENDOR

    def __str__(self) -> str:
        return self.content


@dataclass(frozen=True)
class ParsedWhooshdModelTurn:
    """Strictly validated provider-model turn before Guardian normalization."""

    kind: str
    text: str | None
    command_id: str | None
    arguments: dict[str, Any]


def _normalized(value: Any) -> str:
    return str(value or "").strip().lower()


def is_qualified_transport_candidate(
    *,
    provider: str | None,
    provider_vendor: str | None,
    model: str | None,
    tools: Any,
) -> bool:
    """Return whether a task reaches the narrow Stage 2E containment seam.

    A non-empty tool list is enough to choose the non-streaming strict path so
    that multiple or unsupported definitions fail before provider inference.
    ``prepare_structured_transport`` performs the exact one-tool validation.
    """

    return (
        _normalized(provider) == "local"
        and _normalized(provider_vendor) == QUALIFIED_VENDOR
        and str(model or "").strip() == QUALIFIED_MODEL_ALIAS
        and isinstance(tools, list)
        and bool(tools)
    )


def _empty_arguments_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "maxProperties": 0,
    }


def _tool_argument_schema(tool: Mapping[str, Any]) -> Any:
    if "input_schema" in tool:
        return tool.get("input_schema")
    if "parameters" in tool:
        return tool.get("parameters")
    return None


def validate_supported_argument_schema(raw_schema: Any) -> dict[str, Any]:
    """Validate the intentionally small Stage 2D-proven input subset.

    Supported non-empty schemas are flat objects with all properties required,
    ``additionalProperties: false``, and string properties constrained by a
    bounded enum. Missing or empty schemas mean an exact empty argument object.
    """

    if raw_schema is None or raw_schema == {}:
        return _empty_arguments_schema()
    if not isinstance(raw_schema, dict):
        raise WhooshdStructuredTransportError(
            "Whoosh'd strict structured transport requires an object input schema"
        )
    if set(raw_schema) - _SUPPORTED_OBJECT_SCHEMA_FIELDS:
        raise WhooshdStructuredTransportError(
            "Whoosh'd strict structured transport does not support this input schema"
        )
    if raw_schema.get("type") != "object":
        raise WhooshdStructuredTransportError(
            "Whoosh'd strict structured transport requires a top-level object"
        )
    if raw_schema.get("additionalProperties") is not False:
        raise WhooshdStructuredTransportError(
            "Whoosh'd strict structured transport requires additionalProperties false"
        )
    properties = raw_schema.get("properties")
    required = raw_schema.get("required", [])
    if not isinstance(properties, dict) or not isinstance(required, list):
        raise WhooshdStructuredTransportError(
            "Whoosh'd strict structured transport requires object properties and required"
        )
    if not properties:
        if required:
            raise WhooshdStructuredTransportError(
                "Whoosh'd strict structured empty arguments cannot require fields"
            )
        return _empty_arguments_schema()
    if set(required) != set(properties) or not all(
        isinstance(name, str) and name for name in required
    ):
        raise WhooshdStructuredTransportError(
            "Whoosh'd strict structured transport requires every argument field"
        )

    validated_properties: dict[str, dict[str, Any]] = {}
    for name, property_schema in properties.items():
        if not isinstance(name, str) or not name or not isinstance(property_schema, dict):
            raise WhooshdStructuredTransportError(
                "Whoosh'd strict structured transport has an invalid argument property"
            )
        if set(property_schema) - _SUPPORTED_STRING_SCHEMA_FIELDS:
            raise WhooshdStructuredTransportError(
                "Whoosh'd strict structured transport does not support this argument constraint"
            )
        enum = property_schema.get("enum")
        if property_schema.get("type") != "string" or not isinstance(enum, list):
            raise WhooshdStructuredTransportError(
                "Whoosh'd strict structured arguments must be enum-constrained strings"
            )
        if not enum or len(enum) > _MAX_ENUM_VALUES or not all(
            isinstance(value, str)
            and value
            and len(value) <= _MAX_ENUM_VALUE_LENGTH
            for value in enum
        ):
            raise WhooshdStructuredTransportError(
                "Whoosh'd strict structured argument enum is not bounded"
            )
        validated_properties[name] = {
            "type": "string",
            "enum": list(enum),
        }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": list(required),
        "properties": validated_properties,
    }


def build_model_turn_schema(
    *, command_id: str, argument_schema: Mapping[str, Any]
) -> dict[str, Any]:
    """Build the exact two-branch Stage 2D ModelTurn schema."""

    return {
        "oneOf": [
            {
                "type": "object",
                "additionalProperties": False,
                "required": ["kind", "text", "command_id", "arguments"],
                "properties": {
                    "kind": {"const": "assistant"},
                    "text": {"type": "string"},
                    "command_id": {"type": "null"},
                    "arguments": {"type": "object", "maxProperties": 0},
                },
            },
            {
                "type": "object",
                "additionalProperties": False,
                "required": ["kind", "text", "command_id", "arguments"],
                "properties": {
                    "kind": {"const": "tool_decision"},
                    "text": {"type": "null"},
                    "command_id": {"const": command_id},
                    "arguments": copy.deepcopy(dict(argument_schema)),
                },
            },
        ]
    }


def _transport_instruction(
    *, command_id: str, description: str, argument_schema: Mapping[str, Any]
) -> str:
    rendered_schema = json.dumps(
        dict(argument_schema), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return (
        "Whoosh'd strict structured tool transport. Exactly one non-executable "
        f"capability is available: {command_id}. Description: {description}. "
        f"Its exact arguments schema is {rendered_schema}. Return kind=tool_decision "
        "only when that capability is necessary; otherwise return kind=assistant. "
        "Do not invent unavailable commands. The enforced response schema, not "
        "free-form JSON prompting, defines the required ModelTurn shape."
    )


def prepare_structured_transport(
    *,
    provider_vendor: str | None,
    model: str | None,
    tools: Any,
) -> PreparedWhooshdStructuredTransport | None:
    """Prepare exact-target request material or preserve ordinary local chat."""

    if (
        _normalized(provider_vendor) != QUALIFIED_VENDOR
        or str(model or "").strip() != QUALIFIED_MODEL_ALIAS
        or tools is None
        or tools == []
    ):
        return None
    if not isinstance(tools, list) or len(tools) != 1 or not isinstance(tools[0], dict):
        raise WhooshdStructuredTransportError(
            "Whoosh'd strict structured transport supports exactly one advertised tool"
        )
    tool = tools[0]
    command_id = str(tool.get("command_id") or "").strip()
    description = str(tool.get("description") or "").strip()
    if not command_id or not description:
        raise WhooshdStructuredTransportError(
            "Whoosh'd strict structured transport requires canonical command_id and description"
        )
    argument_schema = validate_supported_argument_schema(_tool_argument_schema(tool))
    return PreparedWhooshdStructuredTransport(
        command_id=command_id,
        argument_schema=argument_schema,
        transport_instruction=_transport_instruction(
            command_id=command_id,
            description=description,
            argument_schema=argument_schema,
        ),
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "stage2d_model_turn",
                "strict": True,
                "schema": build_model_turn_schema(
                    command_id=command_id,
                    argument_schema=argument_schema,
                ),
            },
        },
    )


def _load_json_object(content: str) -> dict[str, Any]:
    if not isinstance(content, str):
        raise WhooshdStructuredTransportError("Whoosh'd structured response is not text")

    def _reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise WhooshdStructuredTransportError(
                    "Whoosh'd structured response contains duplicate fields"
                )
            result[key] = value
        return result

    try:
        value = json.loads(content, object_pairs_hook=_reject_duplicates)
    except WhooshdStructuredTransportError:
        raise
    except (TypeError, ValueError) as exc:
        raise WhooshdStructuredTransportError(
            "Whoosh'd structured response must be one JSON object without prose"
        ) from exc
    if not isinstance(value, dict):
        raise WhooshdStructuredTransportError(
            "Whoosh'd structured response must be a JSON object"
        )
    return value


def _validate_arguments(arguments: Any, schema: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(arguments, dict):
        raise WhooshdStructuredTransportError(
            "Whoosh'd structured tool arguments must be an object"
        )
    properties = schema.get("properties")
    if not isinstance(properties, dict) or not properties:
        if arguments:
            raise WhooshdStructuredTransportError(
                "Whoosh'd structured empty arguments must be exactly empty"
            )
        return {}
    required = schema.get("required")
    if set(arguments) != set(required or []) or set(arguments) != set(properties):
        raise WhooshdStructuredTransportError(
            "Whoosh'd structured tool arguments do not match the advertised schema"
        )
    for name, property_schema in properties.items():
        value = arguments.get(name)
        enum = property_schema.get("enum") if isinstance(property_schema, dict) else None
        if not isinstance(value, str) or not isinstance(enum, list) or value not in enum:
            raise WhooshdStructuredTransportError(
                "Whoosh'd structured tool argument violates the advertised enum"
            )
    return dict(arguments)


def _provenance_mapping(raw: Any) -> Mapping[str, Any] | None:
    if hasattr(raw, "as_dict"):
        raw = raw.as_dict()
    return raw if isinstance(raw, Mapping) else None


def validate_runtime_provenance(raw: Any) -> None:
    """Require Stage 2E structure and a Stage 2F qualification match.

    This remains a provider-wire validation seam.  It neither advertises a
    tool nor authorizes the command selected by a validated response.
    """

    provenance = _provenance_mapping(raw)
    if provenance is None:
        raise WhooshdStructuredTransportError(
            "Whoosh'd structured tool decision lacks runtime provenance"
        )
    for field, expected in (
        ("requested_model_id", QUALIFIED_MODEL_ALIAS),
        ("advertised_model_id", QUALIFIED_MODEL_ALIAS),
        ("resolved_model_id", QUALIFIED_MODEL_ALIAS),
        ("runtime_kind", QUALIFIED_RUNTIME_KIND),
        ("adapter_name", QUALIFIED_ADAPTER_NAME),
        ("resolution_source", QUALIFIED_RESOLUTION_SOURCE),
        ("execution_mode", QUALIFIED_EXECUTION_MODE),
    ):
        if provenance.get(field) != expected:
            raise WhooshdStructuredTransportError(
                f"Whoosh'd structured tool decision provenance mismatch: {field}"
            )
    if provenance.get("streaming") is not False:
        raise WhooshdStructuredTransportError(
            "Whoosh'd structured tool decision must use non-streaming provenance"
        )
    parsed_provenance = (
        raw
        if isinstance(raw, WhooshdRuntimeProvenance)
        else parse_whooshd_runtime_provenance(dict(provenance))
    )
    comparison = compare_whooshd_qualification(
        STAGE_2D_GEMMA_4_12B_IT_QAT_4BIT_RECORD,
        parsed_provenance,
    )
    if comparison.outcome is not WhooshdQualificationOutcome.MATCH:
        raise WhooshdStructuredTransportError(
            "Whoosh'd structured tool decision provenance qualification "
            f"{comparison.outcome.value.lower()}: {comparison.reason}"
        )


def parse_structured_response(
    response: WhooshdStructuredResponse,
) -> ParsedWhooshdModelTurn:
    """Strictly parse the exact ModelTurn output; never extract or repair JSON."""

    payload = _load_json_object(response.content)
    if set(payload) != _MODEL_TURN_FIELDS:
        raise WhooshdStructuredTransportError(
            "Whoosh'd structured response fields do not match ModelTurn"
        )
    kind = payload.get("kind")
    if kind == "assistant":
        if (
            not isinstance(payload.get("text"), str)
            or payload.get("command_id") is not None
            or payload.get("arguments") != {}
        ):
            raise WhooshdStructuredTransportError(
                "Whoosh'd assistant ModelTurn violates the strict response schema"
            )
        return ParsedWhooshdModelTurn(
            kind="assistant",
            text=payload["text"],
            command_id=None,
            arguments={},
        )
    if kind != "tool_decision":
        raise WhooshdStructuredTransportError(
            "Whoosh'd structured response has an unknown ModelTurn kind"
        )
    if payload.get("text") is not None:
        raise WhooshdStructuredTransportError(
            "Whoosh'd tool decision ModelTurn must have null text"
        )
    if payload.get("command_id") != response.command_id:
        raise WhooshdStructuredTransportError(
            "Whoosh'd structured tool decision command_id is not advertised"
        )
    arguments = _validate_arguments(payload.get("arguments"), response.argument_schema)
    validate_runtime_provenance(response.runtime_provenance)
    return ParsedWhooshdModelTurn(
        kind="tool_decision",
        text=None,
        command_id=response.command_id,
        arguments=arguments,
    )


def build_continuation_messages(
    messages: list[dict[str, Any]],
    *,
    command_id: str,
    arguments: Mapping[str, Any],
    command_result: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Render the adapter-owned strict structured result continuation.

    The first message records the constrained semantic decision. The result is
    supplied as bounded provider protocol material, not as a new command
    definition or Guardian authority claim.
    """

    decision = {
        "kind": "tool_decision",
        "text": None,
        "command_id": command_id,
        "arguments": dict(arguments),
    }
    result_envelope = {
        "command_id": command_id,
        "arguments": dict(arguments),
        "result": dict(command_result),
        "instruction": "Use this command result to answer the user. Do not choose another command.",
    }
    next_messages = [
        dict(message) for message in messages if isinstance(message, dict)
    ]
    next_messages.extend(
        [
            {
                "role": "assistant",
                "content": json.dumps(decision, ensure_ascii=False, separators=(",", ":")),
            },
            {
                "role": "user",
                "content": "Whoosh'd structured tool result:\n"
                + json.dumps(
                    result_envelope,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ),
            },
        ]
    )
    return next_messages
