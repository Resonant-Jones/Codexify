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
                "connector_id": "obsidian",
                "invocation": "turn_scoped",
                "query_text": "memory decay",
            }
        ]
    }

    assert resolve_context_request_plans_from_slash_intent(slash_intent) == [
        {
            "request_kind": "read_only_context_request",
            "connector_id": "obsidian",
            "invocation": "turn_scoped",
            "query_text": "memory decay",
            "status": ContextRequestStatus.ACCEPTED_NOT_EXECUTED.value,
            "execution_required": False,
        }
    ]
