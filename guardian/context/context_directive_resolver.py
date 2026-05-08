from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Mapping

ContextDirectiveKind = Literal["connector_context"]
ConnectorId = Literal["obsidian"]
InvocationScope = Literal["turn_scoped"]
ContextRequestKind = Literal["read_only_context_request"]
ContextRequestStatus = Literal["accepted_not_executed"]


@dataclass(frozen=True)
class ContextDirective:
    kind: ContextDirectiveKind
    connector_id: ConnectorId
    invocation: InvocationScope
    query_text: str


@dataclass(frozen=True)
class ContextRequestPlan:
    request_kind: ContextRequestKind
    connector_id: ConnectorId
    invocation: InvocationScope
    query_text: str
    status: ContextRequestStatus
    execution_required: bool


def _normalize_context_directive(
    directive: ContextDirective | Mapping[str, Any],
) -> ContextDirective:
    if isinstance(directive, ContextDirective):
        kind = directive.kind
        connector_id = directive.connector_id
        invocation = directive.invocation
        query_text = directive.query_text
    elif isinstance(directive, Mapping):
        kind = directive.get("kind")
        connector_id = directive.get("connector_id")
        invocation = directive.get("invocation")
        query_text = directive.get("query_text")
    else:
        raise ValueError("context directive must be mapping or ContextDirective")

    if kind != "connector_context":
        raise ValueError(f"unsupported context directive kind: {kind!r}")
    if connector_id != "obsidian":
        raise ValueError(f"unsupported connector_id: {connector_id!r}")
    if invocation != "turn_scoped":
        raise ValueError(f"unsupported invocation scope: {invocation!r}")
    if not isinstance(query_text, str):
        raise ValueError("context directive query_text must be a string")

    normalized_query_text = query_text.strip()
    if not normalized_query_text:
        raise ValueError("context directive query_text cannot be blank")

    return ContextDirective(
        kind="connector_context",
        connector_id="obsidian",
        invocation="turn_scoped",
        query_text=normalized_query_text,
    )


def resolve_context_request_plans(
    directives: list[ContextDirective | Mapping[str, Any]],
) -> list[ContextRequestPlan]:
    plans: list[ContextRequestPlan] = []
    for directive in directives:
        normalized = _normalize_context_directive(directive)
        plans.append(
            ContextRequestPlan(
                request_kind="read_only_context_request",
                connector_id="obsidian",
                invocation="turn_scoped",
                query_text=normalized.query_text,
                status="accepted_not_executed",
                execution_required=False,
            )
        )
    return plans


def serialize_context_request_plans(
    plans: list[ContextRequestPlan],
) -> list[dict[str, Any]]:
    return [
        {
            "request_kind": plan.request_kind,
            "connector_id": plan.connector_id,
            "invocation": plan.invocation,
            "query_text": plan.query_text,
            "status": plan.status,
            "execution_required": plan.execution_required,
        }
        for plan in plans
    ]
