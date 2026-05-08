"""Normalize narrow context directives into turn-scoped request plans."""

from __future__ import annotations

import json
import logging
from typing import Any
from urllib.parse import quote, unquote

from guardian.protocol_tokens import ContextRequestStatus

logger = logging.getLogger(__name__)

CONTEXT_REQUEST_PLANS_ORIGIN_KEY = "context_request_plans"
SUPPORTED_CONTEXT_REQUEST_KIND = "read_only_context_request"
SUPPORTED_CONTEXT_REQUEST_CONNECTOR_ID = "obsidian"
SUPPORTED_CONTEXT_REQUEST_INVOCATION = "turn_scoped"


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    try:
        return str(value).strip()
    except Exception:
        return ""


def _directive_list_from_value(value: Any) -> list[Any]:
    if isinstance(value, list):
        return list(value)
    if isinstance(value, dict):
        return [value]
    return []


def _resolve_directives_from_slash_intent(slash_intent: Any) -> list[Any]:
    if slash_intent is None:
        return []
    if isinstance(slash_intent, dict):
        for key in ("contextDirectives", "context_directives", "contextPlans"):
            directives = slash_intent.get(key)
            if directives is not None:
                return _directive_list_from_value(directives)
        return _directive_list_from_value(slash_intent)

    for attr_name in (
        "contextDirectives",
        "context_directives",
        "contextPlans",
    ):
        directives = getattr(slash_intent, attr_name, None)
        if directives is not None:
            return _directive_list_from_value(directives)
    return _directive_list_from_value(slash_intent)


def normalize_context_request_plan(raw_plan: Any) -> dict[str, Any] | None:
    if not isinstance(raw_plan, dict):
        return None

    request_kind = _clean_text(
        raw_plan.get("request_kind") or raw_plan.get("requestKind")
    ).lower()
    connector_id = _clean_text(
        raw_plan.get("connector_id") or raw_plan.get("connectorId")
    ).lower()
    invocation = _clean_text(raw_plan.get("invocation")).lower()
    query_text = _clean_text(
        raw_plan.get("query_text") or raw_plan.get("queryText")
    )

    if not request_kind or not connector_id or not invocation or not query_text:
        return None

    if request_kind != SUPPORTED_CONTEXT_REQUEST_KIND:
        return None
    if connector_id != SUPPORTED_CONTEXT_REQUEST_CONNECTOR_ID:
        return None
    if invocation != SUPPORTED_CONTEXT_REQUEST_INVOCATION:
        return None

    return {
        "request_kind": SUPPORTED_CONTEXT_REQUEST_KIND,
        "connector_id": SUPPORTED_CONTEXT_REQUEST_CONNECTOR_ID,
        "invocation": SUPPORTED_CONTEXT_REQUEST_INVOCATION,
        "query_text": query_text,
        "status": ContextRequestStatus.ACCEPTED_NOT_EXECUTED.value,
        "execution_required": False,
    }


def resolve_context_request_plans(
    directives: Any,
) -> list[dict[str, Any]]:
    plans: list[dict[str, Any]] = []
    for directive in _directive_list_from_value(directives):
        normalized = normalize_context_request_plan(directive)
        if normalized is not None:
            plans.append(normalized)
    return plans


def resolve_context_request_plans_from_slash_intent(
    slash_intent: Any,
) -> list[dict[str, Any]]:
    return resolve_context_request_plans(
        _resolve_directives_from_slash_intent(slash_intent)
    )


def encode_context_request_plans_origin_segment(
    plans: list[dict[str, Any]] | None,
) -> str:
    normalized_plans = resolve_context_request_plans(plans or [])
    if not normalized_plans:
        return ""
    try:
        encoded = quote(
            json.dumps(
                normalized_plans,
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            safe="",
        )
    except Exception:
        logger.debug(
            "[context-directive] failed to encode context request plans",
            exc_info=True,
        )
        return ""
    return f"|{CONTEXT_REQUEST_PLANS_ORIGIN_KEY}={encoded}"


def context_request_plans_from_origin(origin: Any) -> list[dict[str, Any]]:
    text = _clean_text(origin)
    if not text:
        return []

    for segment in text.split("|")[1:]:
        key, _, value = segment.partition("=")
        if key.strip() != CONTEXT_REQUEST_PLANS_ORIGIN_KEY:
            continue
        raw_value = unquote(value.strip())
        if not raw_value:
            return []
        try:
            parsed = json.loads(raw_value)
        except Exception:
            logger.debug(
                "[context-directive] failed to decode context request plans",
                exc_info=True,
            )
            return []
        if not isinstance(parsed, list):
            return []
        return resolve_context_request_plans(parsed)
    return []


__all__ = [
    "CONTEXT_REQUEST_PLANS_ORIGIN_KEY",
    "SUPPORTED_CONTEXT_REQUEST_KIND",
    "SUPPORTED_CONTEXT_REQUEST_CONNECTOR_ID",
    "SUPPORTED_CONTEXT_REQUEST_INVOCATION",
    "normalize_context_request_plan",
    "resolve_context_request_plans",
    "resolve_context_request_plans_from_slash_intent",
    "encode_context_request_plans_origin_segment",
    "context_request_plans_from_origin",
]
