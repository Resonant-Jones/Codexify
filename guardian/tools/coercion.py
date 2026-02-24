"""Argument coercion and validation for callable tools lane."""

from __future__ import annotations

import logging
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as JSONSchemaValidationError

from guardian.tools.spec import ToolSpec

logger = logging.getLogger(__name__)

_CANONICAL_KEYS = ("path_params", "query", "headers", "body")


class ToolArgumentCoercionError(ValueError):
    """Raised when input arguments cannot be normalized for tool execution."""

    def __init__(
        self,
        *,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


def _schema_properties(
    schema: dict[str, Any] | None, section: str
) -> dict[str, Any]:
    if not isinstance(schema, dict):
        return {}
    props = schema.get("properties")
    if not isinstance(props, dict):
        return {}
    section_schema = props.get(section)
    if not isinstance(section_schema, dict):
        return {}
    section_props = section_schema.get("properties")
    if not isinstance(section_props, dict):
        return {}
    return section_props


def _section_schema(
    schema: dict[str, Any] | None, section: str
) -> dict[str, Any]:
    if not isinstance(schema, dict):
        return {}
    props = schema.get("properties")
    if not isinstance(props, dict):
        return {}
    candidate = props.get(section)
    return candidate if isinstance(candidate, dict) else {}


def _normalize_object(raw: Any, *, section: str) -> dict[str, Any]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ToolArgumentCoercionError(
            code="invalid_argument_section",
            message=f"{section} must be an object when provided",
            details={"section": section},
        )
    return dict(raw)


def _validate_schema(value: Any, schema: dict[str, Any], *, label: str) -> None:
    if not isinstance(schema, dict) or not schema:
        return
    try:
        Draft202012Validator(schema).validate(value)
    except JSONSchemaValidationError as exc:
        raise ToolArgumentCoercionError(
            code="invalid_arguments_schema",
            message=f"{label} failed schema validation: {exc.message}",
            details={
                "label": label,
                "path": list(exc.path),
                "validator": exc.validator,
            },
        ) from exc


def _merge_passthrough(
    *,
    normalized: dict[str, Any],
    passthrough: dict[str, Any],
    tool: ToolSpec,
) -> None:
    if not passthrough:
        return
    logger.warning(
        "tool_argument_passthrough_enabled tool_id=%s keys=%s",
        tool.tool_id,
        ",".join(sorted(passthrough.keys())),
    )
    if tool.method in {"GET", "HEAD"}:
        normalized["query"].update(passthrough)
        return

    current_body = normalized.get("body")
    if current_body in (None, {}):
        normalized["body"] = dict(passthrough)
        return
    if isinstance(current_body, dict):
        current_body.update(passthrough)
        return
    raise ToolArgumentCoercionError(
        code="invalid_body_passthrough",
        message=(
            "cannot merge passthrough arguments into non-object body; "
            "provide structured path_params/query/headers/body instead"
        ),
        details={"tool_id": tool.tool_id},
    )


def coerce_tool_arguments(
    tool: ToolSpec, arguments: dict[str, Any] | None
) -> dict[str, Any]:
    """
    Normalize caller arguments into canonical invoke transport shape.

    Returns a dict with keys:
      - path_params
      - query
      - headers
      - body
    """

    source = dict(arguments or {})
    normalized: dict[str, Any] = {
        "path_params": {},
        "query": {},
        "headers": {},
        "body": {},
    }
    has_explicit_transport = any(key in source for key in _CANONICAL_KEYS)

    if has_explicit_transport:
        unknown_top_level = {
            key: value
            for key, value in source.items()
            if key not in _CANONICAL_KEYS
        }
        if unknown_top_level and not tool.allow_passthrough_arguments:
            raise ToolArgumentCoercionError(
                code="unknown_argument_keys",
                message="unknown argument keys are not allowed",
                details={"unknown_keys": sorted(unknown_top_level.keys())},
            )

        normalized["path_params"] = _normalize_object(
            source.get("path_params"), section="path_params"
        )
        normalized["query"] = _normalize_object(
            source.get("query"), section="query"
        )
        normalized["headers"] = _normalize_object(
            source.get("headers"), section="headers"
        )
        if "body" in source:
            normalized["body"] = source.get("body")
        if normalized["body"] is None:
            normalized["body"] = {}

        if unknown_top_level:
            _merge_passthrough(
                normalized=normalized,
                passthrough=unknown_top_level,
                tool=tool,
            )
    else:
        path_props = _schema_properties(tool.input_schema, "path_params")
        query_props = _schema_properties(tool.input_schema, "query")
        header_props = _schema_properties(tool.input_schema, "headers")

        unknown: dict[str, Any] = {}
        implicit_body: dict[str, Any] = {}
        for key, value in source.items():
            if key in path_props:
                normalized["path_params"][key] = value
            elif key in query_props:
                normalized["query"][key] = value
            elif key in header_props:
                normalized["headers"][key] = value
            elif key == "body":
                normalized["body"] = value
            else:
                if tool.method in {"GET", "HEAD"}:
                    unknown[key] = value
                else:
                    implicit_body[key] = value

        if implicit_body:
            current_body = normalized.get("body")
            if current_body in (None, {}):
                normalized["body"] = dict(implicit_body)
            elif isinstance(current_body, dict):
                current_body.update(implicit_body)
            else:
                raise ToolArgumentCoercionError(
                    code="invalid_argument_section",
                    message=(
                        "body must be an object when combining flat arguments "
                        "for non-GET tool calls"
                    ),
                    details={"section": "body"},
                )

        if unknown:
            if not tool.allow_passthrough_arguments:
                raise ToolArgumentCoercionError(
                    code="unknown_argument_keys",
                    message="unknown argument keys are not allowed",
                    details={"unknown_keys": sorted(unknown.keys())},
                )
            _merge_passthrough(
                normalized=normalized, passthrough=unknown, tool=tool
            )

        if normalized["body"] is None:
            normalized["body"] = {}

    _validate_schema(
        normalized["path_params"],
        _section_schema(tool.input_schema, "path_params"),
        label="path_params",
    )
    _validate_schema(
        normalized["query"],
        _section_schema(tool.input_schema, "query"),
        label="query",
    )
    _validate_schema(
        normalized["headers"],
        _section_schema(tool.input_schema, "headers"),
        label="headers",
    )
    _validate_schema(
        normalized["body"],
        _section_schema(tool.input_schema, "body"),
        label="body",
    )
    _validate_schema(
        normalized,
        tool.input_schema,
        label="arguments",
    )
    return normalized
