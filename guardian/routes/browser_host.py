"""Development-only Guardian routes for Browser Host attachment grants."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from guardian.browser_host.http_adapter import (
    AUTHORIZATION_SCHEME,
    INSTANCE_HEADER,
    apply_no_store,
    consume_attachment,
    error_response,
    get_browser_host_negotiation_policy,
    get_attachment_grant_store,
    is_bounded_identifier,
    issue_attachment_grant,
    parse_attachment_grant_authorization,
)
from guardian.browser_host.negotiation import (
    negotiate_browser_host_hello,
    validate_browser_host_hello_request,
)
from guardian.core.dependencies import get_current_user


router = APIRouter(prefix="/dev/browser-host/v1", tags=["Browser Host (development)"])
negotiation_router = APIRouter(
    prefix="/dev/browser-host/v1", tags=["Browser Host (development)"]
)


async def _json_body(request: Request) -> Any:
    try:
        return await request.json()
    except Exception:
        return None


@router.post("/attachment-grants")
async def create_attachment_grant(
    request: Request,
    subject: str = Depends(get_current_user),
    store=Depends(get_attachment_grant_store),
):
    body = await _json_body(request)
    return issue_attachment_grant(request, body, subject, store)


@router.post("/attachments")
async def attach_browser_context(
    request: Request,
    store=Depends(get_attachment_grant_store),
):
    bearer = parse_attachment_grant_authorization(
        request.headers.get("Authorization")
    )
    if bearer is None:
        return error_response(
            401,
            "permission_denied",
            request,
            headers={"WWW-Authenticate": AUTHORIZATION_SCHEME},
        )

    instance_id = request.headers.get(INSTANCE_HEADER)
    if not is_bounded_identifier(instance_id):
        return error_response(403, "permission_denied", request)

    body = await _json_body(request)
    return consume_attachment(request, body, bearer, instance_id, store)


@negotiation_router.post("/negotiate")
async def negotiate_browser_host(
    request: Request,
    policy=Depends(get_browser_host_negotiation_policy),
):
    body = await _json_body(request)
    if not validate_browser_host_hello_request(body):
        return error_response(
            422,
            "invalid_contract",
            request,
            candidate_request_id=(
                body.get("requestCorrelationId")
                if isinstance(body, dict)
                else None
            ),
        )
    try:
        decision = negotiate_browser_host_hello(body, policy)
    except ValueError:
        return error_response(
            422,
            "invalid_contract",
            request,
            candidate_request_id=body.get("requestCorrelationId"),
        )
    response = JSONResponse(status_code=200, content=decision.to_dict())
    return apply_no_store(response)
