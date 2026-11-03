"""Internal-only Guardian route for custodian-backed read actions.

This module owns the HTTP surface of the OpenConnector crossing. It is
**internal**: the router is mounted under an internal-only posture, so its
paths never appear in the public OpenAPI document and the public-exposure
middleware refuses them for every caller, including the Command Bus loopback.

The route exposes exactly **one** operation, and it is a read:

* ``GET /api/guardian/connections/openconnector/actions/{action_id}``

A read is what makes the operation invocable through the Command Bus. The
manifest classifies a command by its HTTP method, so only a GET produces the
``read`` / ``read_only`` / ``safe`` / ``none`` command this gate requires; a
mutating method would be refused by the phase-one tool policy.

Authorization is Guardian's, and it is derived, not supplied:

* the account session is verified by Guardian's existing dependency, so the
  caller is an authenticated account;
* the account and subject come from Guardian's resolved request scope;
* the provider comes from the reviewed allowlist entry for the action, never
  from the request;
* **credential selection** — which account-owned credential may be used —
  comes from the Guardian-owned binding, resolved for the authenticated
  account;
* **invocation permission** — whether this actor may invoke that credential —
  comes from a separate Guardian usage grant naming this account, subject,
  provider, and action.

Neither substitutes for the other: a binding that exists without a usage grant
authorizes nothing, and a usage grant without a binding selects nothing. Both
default to denying. Both are re-read immediately before the external crossing,
so a revocation of either, between resolution and dispatch, stops the call.

How the custodian-side connection is named comes from the reviewed allowlist
entry for the action, never from the request. For a credential-bearing action
the connection is selected explicitly. For a reviewed **no-auth** action the
custodian's connection is virtual and holds no credential, so the crossing
omits the upstream selector — and only for those actions. The route itself
never chooses a connection and never accepts one from the caller.

The route accepts no action arguments. There is therefore no model-supplied
argument that could carry account identity, connection identity, or credential
material into the crossing.
"""

from __future__ import annotations

import os
from typing import Any, Mapping

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from guardian.connections.openconnector.adapter import (
    AdapterOutcome,
    AdapterResult,
    OpenConnectorAdapter,
)
from guardian.connections.openconnector.authority import (
    CustodianUsageAuthorizer,
    GuardianAccountScope,
    NoUsageAuthorizer,
    build_execution_authority,
)
from guardian.connections.openconnector.bindings import (
    BindingResolver,
    NoBindingResolver,
)
from guardian.connections.openconnector.policy import (
    ApprovedAction,
    get_approved_action,
    resolve_allowlist,
)
from guardian.connections.openconnector.service import (
    GatewayHttpClient,
    HttpxGatewayClient,
    OpenConnectorService,
)
from guardian.core.dependencies import (
    RequestUserScope,
    get_account_user_scope,
    require_account_session,
)
from guardian.core.route_visibility import command_visible

#: The Guardian-side base URL of the custodian. When it is unset, the route
#: reports ``needs_configuration`` instead of attempting a crossing.
BASE_URL_ENV = "CODEXIFY_OPENCONNECTOR_BASE_URL"

#: The route prefix. It lives under ``/api/guardian`` because the route is a
#: Guardian-internal execution surface, not a user-facing connector route.
PREFIX = "/api/guardian/connections/openconnector"

router = APIRouter(
    prefix=PREFIX,
    tags=["OpenConnector"],
    dependencies=[Depends(require_account_session)],
)

_binding_resolver: BindingResolver = NoBindingResolver()
_usage_authorizer: CustodianUsageAuthorizer = NoUsageAuthorizer()
_allowlist: Mapping[str, ApprovedAction] | None = None
_gateway_client: GatewayHttpClient | None = None
_base_url_override: str | None = None
_adapter: OpenConnectorAdapter | None = None


def configure_openconnector(
    *,
    binding_resolver: BindingResolver | None = None,
    usage_authorizer: CustodianUsageAuthorizer | None = None,
    allowlist: Mapping[str, ApprovedAction] | None = None,
    gateway_client: GatewayHttpClient | None = None,
    base_url: str | None = None,
) -> None:
    """Configure the internal execution seam.

    ``binding_resolver`` supplies *credential selection* — which account-owned
    credential may be used. ``usage_authorizer`` supplies *invocation
    permission* — whether this actor may invoke that credential. Both are
    required; neither substitutes for the other, and both default to denying.

    Supplying an ``allowlist`` is a **test-harness** affordance for
    credential-bearing synthetic actions. It must never widen the production
    read-only allowlist, and no production caller sets it.
    """

    global _binding_resolver, _usage_authorizer, _allowlist, _gateway_client
    global _base_url_override, _adapter
    _binding_resolver = binding_resolver or NoBindingResolver()
    _usage_authorizer = usage_authorizer or NoUsageAuthorizer()
    _allowlist = allowlist
    _gateway_client = gateway_client
    _base_url_override = base_url
    _adapter = None


def _configured_base_url() -> str:
    if _base_url_override is not None:
        return str(_base_url_override or "").strip()
    return str(os.getenv(BASE_URL_ENV) or "").strip()


def current_adapter() -> OpenConnectorAdapter | None:
    """Return the configured adapter, or ``None`` when the custodian is unset.

    An unset custodian base URL is a configuration gap, not a failure: the
    route reports ``needs_configuration`` rather than attempting a crossing.
    """

    global _adapter
    if _adapter is not None:
        return _adapter
    base_url = _configured_base_url()
    if not base_url:
        return None
    client = _gateway_client or HttpxGatewayClient()
    service = OpenConnectorService(base_url, client)
    _adapter = OpenConnectorAdapter(
        service,
        _binding_resolver,
        allowlist=resolve_allowlist(_allowlist),
    )
    return _adapter


def _scope_from_request(scope: RequestUserScope) -> GuardianAccountScope:
    """Reduce Guardian's resolved request scope to an execution scope."""

    account_id = str(scope.account_id or scope.user_id or "").strip()
    subject_id = str(scope.subject_id or scope.account_id or scope.user_id or "").strip()
    return GuardianAccountScope.for_invocation(
        account_id=account_id,
        subject_id=subject_id,
    )


def _response_for(result: AdapterResult) -> tuple[int, dict[str, Any]]:
    """Map a bounded adapter result onto an HTTP status and body."""

    body: dict[str, Any] = {
        "outcome": result.outcome.value,
        "code": result.code,
    }
    if result.outcome is AdapterOutcome.SUCCESS:
        body["data"] = result.payload
        body["truncated"] = bool(result.truncated)
        return 200, body
    body["detail"] = result.detail
    status = {
        AdapterOutcome.DENIED: 403,
        AdapterOutcome.NEEDS_CONFIGURATION: 409,
        AdapterOutcome.UNAVAILABLE: 503,
        AdapterOutcome.TIMED_OUT: 504,
        AdapterOutcome.FAILED: 502,
    }.get(result.outcome, 500)
    return status, body


@router.get(
    "/actions/{action_id}",
    operation_id="openconnector_execute_read_action",
    summary="Execute one reviewed read-only custodian action for the account.",
)
@command_visible()
async def openconnector_execute_read_action(
    action_id: str,
    scope: RequestUserScope = Depends(get_account_user_scope),
) -> JSONResponse:
    """Execute one reviewed read-only action for the authenticated account."""

    action = get_approved_action(action_id, resolve_allowlist(_allowlist))
    if action is None:
        # An action that is not on the reviewed allowlist never reaches the
        # network, and the refusal does not disclose the custodian catalog.
        status, body = _response_for(
            AdapterResult(
                outcome=AdapterOutcome.DENIED,
                code="action_not_approved",
                detail="action is not on the reviewed read-only allowlist",
            )
        )
        return JSONResponse(status_code=status, content=body)

    adapter = current_adapter()
    if adapter is None:
        status, body = _response_for(
            AdapterResult(
                outcome=AdapterOutcome.NEEDS_CONFIGURATION,
                code="custodian_not_configured",
                detail="the custodian endpoint is not configured for this deployment",
            )
        )
        return JSONResponse(status_code=status, content=body)

    execution_scope = _scope_from_request(scope)
    authority = build_execution_authority(
        scope=execution_scope,
        provider=action.provider,
        action_id=action.action_id,
        resolver=_binding_resolver,
        authorizer=_usage_authorizer,
    )
    result = await adapter.execute_action(authority)
    status, body = _response_for(result)
    return JSONResponse(status_code=status, content=body)


__all__ = [
    "BASE_URL_ENV",
    "PREFIX",
    "configure_openconnector",
    "current_adapter",
    "router",
]
