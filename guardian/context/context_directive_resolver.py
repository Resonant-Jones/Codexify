"""Normalize narrow context-request directives into completion plans."""

from __future__ import annotations

from typing import Any, Mapping

from guardian.protocol_tokens import ContextRequestStatus

_SUPPORTED_KIND = "connector_context"
_SUPPORTED_REQUEST_KIND = "read_only_context_request"
_SUPPORTED_CONNECTOR_ID = "obsidian"
_SUPPORTED_INVOCATION = "turn_scoped"
_SUPPORTED_STATUS = ContextRequestStatus.ACCEPTED_NOT_EXECUTED.value


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    try:
        return " ".join(str(value).split()).strip()
    except Exception:
        return ""


def _normalize_directive(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, Mapping):
        return None

    kind = _clean_text(raw.get("kind")).lower()
    request_kind = _clean_text(
        raw.get("request_kind") or raw.get("requestKind")
    ).lower()
    connector_id = _clean_text(
        raw.get("connector_id") or raw.get("connectorId")
    ).lower()
    invocation = _clean_text(raw.get("invocation")).lower()
    query_text = _clean_text(raw.get("query_text") or raw.get("queryText"))
    status = _clean_text(raw.get("status")).lower()

    if kind == _SUPPORTED_KIND:
        if connector_id != _SUPPORTED_CONNECTOR_ID:
            return None
        if invocation != _SUPPORTED_INVOCATION:
            return None
        if not query_text:
            return None
        return {
            "request_kind": _SUPPORTED_REQUEST_KIND,
            "connector_id": _SUPPORTED_CONNECTOR_ID,
            "invocation": _SUPPORTED_INVOCATION,
            "query_text": query_text,
            "status": _SUPPORTED_STATUS,
            "execution_required": False,
        }

    if request_kind == _SUPPORTED_REQUEST_KIND:
        if connector_id != _SUPPORTED_CONNECTOR_ID:
            return None
        if invocation != _SUPPORTED_INVOCATION:
            return None
        if not query_text:
            return None
        if status and status != _SUPPORTED_STATUS:
            return None
        return {
            "request_kind": _SUPPORTED_REQUEST_KIND,
            "connector_id": _SUPPORTED_CONNECTOR_ID,
            "invocation": _SUPPORTED_INVOCATION,
            "query_text": query_text,
            "status": _SUPPORTED_STATUS,
            "execution_required": bool(
                raw.get("execution_required", False)
            ),
        }

    return None


def resolve_context_request_plans(
    context_directives: Any,
) -> list[dict[str, Any]]:
    """Normalize supported context directives into accepted plans."""

    if context_directives is None:
        return []

    if isinstance(context_directives, list):
        directives = list(context_directives)
    elif isinstance(context_directives, dict):
        directives = [context_directives]
    else:
        return []

    plans: list[dict[str, Any]] = []
    for directive in directives:
        plan = _normalize_directive(directive)
        if plan is not None:
            plans.append(plan)
    return plans


def serialize_context_request_plans(
    plans: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    return [dict(plan) for plan in plans if isinstance(plan, Mapping)]


__all__ = [
    "resolve_context_request_plans",
    "serialize_context_request_plans",
]
