from __future__ import annotations

import pytest

from guardian.context.context_directive_resolver import (
    ContextDirective,
    resolve_context_request_plans,
    serialize_context_request_plans,
)


def test_resolver_builds_read_only_context_plan_for_obsidian_directive():
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

    assert len(plans) == 1
    plan = plans[0]
    assert plan.request_kind == "read_only_context_request"
    assert plan.connector_id == "obsidian"
    assert plan.invocation == "turn_scoped"
    assert plan.query_text == "memory decay"
    assert plan.status == "accepted_not_executed"
    assert plan.execution_required is False


def test_resolver_trims_query_text():
    plans = resolve_context_request_plans(
        [
            ContextDirective(
                kind="connector_context",
                connector_id="obsidian",
                invocation="turn_scoped",
                query_text="  vault summary  ",
            )
        ]
    )

    assert plans[0].query_text == "vault summary"


def test_serialize_context_request_plans_is_json_safe_and_stable():
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
            "status": "accepted_not_executed",
            "execution_required": False,
        }
    ]


def test_resolver_rejects_unsupported_connector_id():
    with pytest.raises(ValueError, match="unsupported connector_id"):
        resolve_context_request_plans(
            [
                {
                    "kind": "connector_context",
                    "connector_id": "github",
                    "invocation": "turn_scoped",
                    "query_text": "repo status",
                }
            ]
        )


def test_resolver_rejects_unsupported_directive_kind():
    with pytest.raises(ValueError, match="unsupported context directive kind"):
        resolve_context_request_plans(
            [
                {
                    "kind": "mcp_context",
                    "connector_id": "obsidian",
                    "invocation": "turn_scoped",
                    "query_text": "memory decay",
                }
            ]
        )


def test_resolver_rejects_blank_query_text():
    with pytest.raises(ValueError, match="cannot be blank"):
        resolve_context_request_plans(
            [
                {
                    "kind": "connector_context",
                    "connector_id": "obsidian",
                    "invocation": "turn_scoped",
                    "query_text": "   ",
                }
            ]
        )
