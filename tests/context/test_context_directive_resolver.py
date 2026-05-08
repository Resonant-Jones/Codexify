from __future__ import annotations

from urllib.parse import quote

from guardian.context.context_directive_resolver import (
    CONTEXT_REQUEST_PLANS_ORIGIN_KEY,
    context_request_plans_from_origin,
    encode_context_request_plans_origin_segment,
    normalize_context_request_plan,
    resolve_context_request_plans,
    resolve_context_request_plans_from_slash_intent,
)
from guardian.protocol_tokens import ContextRequestStatus


def test_normalize_supported_obsidian_context_request_plan() -> None:
    plan = normalize_context_request_plan(
        {
            "request_kind": "read_only_context_request",
            "connector_id": "obsidian",
            "invocation": "turn_scoped",
            "query_text": " memory decay ",
        }
    )

    assert plan == {
        "request_kind": "read_only_context_request",
        "connector_id": "obsidian",
        "invocation": "turn_scoped",
        "query_text": "memory decay",
        "status": ContextRequestStatus.ACCEPTED_NOT_EXECUTED.value,
        "execution_required": False,
    }


def test_context_request_plans_round_trip_from_origin() -> None:
    plan = {
        "request_kind": "read_only_context_request",
        "connector_id": "obsidian",
        "invocation": "turn_scoped",
        "query_text": "memory decay",
        "status": ContextRequestStatus.ACCEPTED_NOT_EXECUTED.value,
        "execution_required": False,
    }
    origin = (
        "api:chat.complete|turn_id=abc"
        + encode_context_request_plans_origin_segment([plan])
    )

    assert context_request_plans_from_origin(origin) == [plan]


def test_context_request_plans_from_origin_handles_malformed_payload() -> None:
    origin = (
        "api:chat.complete|turn_id=abc|"
        f"{CONTEXT_REQUEST_PLANS_ORIGIN_KEY}={quote('not-json')}"
    )

    assert context_request_plans_from_origin(origin) == []


def test_resolve_context_request_plans_fail_closed_for_unsupported_connector() -> (
    None
):
    assert (
        resolve_context_request_plans(
            [
                {
                    "request_kind": "read_only_context_request",
                    "connector_id": "github",
                    "invocation": "turn_scoped",
                    "query_text": "repo search",
                }
            ]
        )
        == []
    )


def test_resolve_context_request_plans_from_slash_intent() -> None:
    slash_intent = {
        "contextDirectives": [
            {
                "request_kind": "read_only_context_request",
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
    }

    assert resolve_context_request_plans_from_slash_intent(slash_intent) == [
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
