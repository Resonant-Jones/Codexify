from __future__ import annotations

from guardian.context.context_directive_resolver import (
    resolve_context_request_plans,
    serialize_context_request_plans,
)
from guardian.protocol_tokens import ContextRequestStatus


def test_context_directive_resolver_module_import_smoke() -> None:
    import guardian.context.context_directive_resolver as resolver

    assert callable(resolver.resolve_context_request_plans)
    assert callable(resolver.serialize_context_request_plans)
    assert resolver.CONTEXT_REQUEST_PLANS_ORIGIN_KEY == "context_request_plans"


def test_resolver_builds_read_only_context_plan_for_obsidian_directive() -> (
    None
):
    plans = resolve_context_request_plans(
        [
            {
                "kind": "connector_context",
                "connector_id": "obsidian",
                "invocation": "turn_scoped",
                "query_text": "memory decay",
            }
        ]
    )

    assert plans == [
        {
            "request_kind": "read_only_context_request",
            "connector_id": "obsidian",
            "invocation": "turn_scoped",
            "query_text": "memory decay",
            "status": ContextRequestStatus.ACCEPTED_NOT_EXECUTED.value,
            "execution_required": False,
        }
    ]


def test_resolver_accepts_supported_plan_shape_and_trims_query_text() -> None:
    plans = resolve_context_request_plans(
        [
            {
                "request_kind": "read_only_context_request",
                "connector_id": "obsidian",
                "invocation": "turn_scoped",
                "query_text": "  vault summary  ",
                "status": ContextRequestStatus.ACCEPTED_NOT_EXECUTED.value,
                "execution_required": False,
            }
        ]
    )

    assert plans == [
        {
            "request_kind": "read_only_context_request",
            "connector_id": "obsidian",
            "invocation": "turn_scoped",
            "query_text": "vault summary",
            "status": ContextRequestStatus.ACCEPTED_NOT_EXECUTED.value,
            "execution_required": False,
        }
    ]


def test_resolver_ignores_unsupported_directives() -> None:
    plans = resolve_context_request_plans(
        [
            {
                "request_kind": "read_only_context_request",
                "connector_id": "github",
                "invocation": "turn_scoped",
                "query_text": "repo issue",
            },
            {
                "kind": "connector_context",
                "connector_id": "obsidian",
                "invocation": "turn_scoped",
                "query_text": "   ",
            },
            {
                "request_kind": "write_request",
                "connector_id": "obsidian",
                "invocation": "turn_scoped",
                "query_text": "memory decay",
            },
        ]
    )

    assert plans == []


def test_serialize_context_request_plans_is_json_safe_and_stable() -> None:
    plans = resolve_context_request_plans(
        [
            {
                "kind": "connector_context",
                "connector_id": "obsidian",
                "invocation": "turn_scoped",
                "query_text": "memory decay",
            }
        ]
    )

    assert serialize_context_request_plans(plans) == [
        {
            "request_kind": "read_only_context_request",
            "connector_id": "obsidian",
            "invocation": "turn_scoped",
            "query_text": "memory decay",
            "status": ContextRequestStatus.ACCEPTED_NOT_EXECUTED.value,
            "execution_required": False,
        }
    ]
