"""The internal-only OpenConnector read route, and the Command Bus invocation of it.

These tests exercise the route **and** the registration seam the OpenConnector
integration needed:

* the route is internal-only: it is absent from the public OpenAPI document and
  it is refused for every caller when the deployment uses the hosted
  ``public_allowlist`` exposure mode;
* the route is discoverable by the Command Bus through an explicit per-route
  marker, and the command it produces is classified ``read`` / ``read_only`` /
  ``safe`` / ``none``;
* Guardian authorization is required before any custodian dispatch, and it is
  revalidated immediately before the crossing;
* two synthetic accounts stay isolated, and every refusal path reaches the
  custodian zero times.

The custodian is an instrumented in-process transport. These tests prove
Guardian's route and authorization behavior; they are **not** live upstream
execution and they are **not** Gate B qualification.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from guardian.command_bus import loopback_http_adapter
from guardian.command_bus.manifest import build_manifest
from guardian.connections.openconnector import router as openconnector_router
from guardian.connections.openconnector.authority import CustodianUsageGrant
from guardian.connections.openconnector.bindings import AccountBinding, BindingState
from guardian.connections.openconnector.policy import (
    APPROVED_ACTIONS,
    ApprovedAction,
    ConnectionSelection,
)
from guardian.connections.openconnector.service import (
    CONNECTION_SELECTOR_HEADER,
    GatewayRequest,
    GatewayResponse,
)
from guardian.core.public_exposure import (
    PUBLIC_ALLOWLIST_MODE,
    PublicExposureMiddleware,
)
from guardian.core.route_visibility import build_public_route_schema, hide_paths
from guardian.routes import command_bus as command_bus_routes

_ACCOUNT_A = "acct-alpha"
_ACCOUNT_B = "acct-beta"

#: The custodian's virtual connection identity for the no-auth provider. It is
#: provider-scoped rather than account-scoped: it holds no credential, it has
#: no stored UUID, and upstream refuses an explicit selector aimed at it. The
#: production reviewed action is a no-auth action, so this is the identity its
#: binding names.
_VIRTUAL_CONNECTION = "hackernews:default"

#: Credential-bearing synthetic connections. They exist only for the injected
#: credential-bearing allowlist and never reach the production allowlist.
_CONNECTION_A = "aaaaaaaa-0000-0000-0000-00000000000a"
_CONNECTION_B = "bbbbbbbb-0000-0000-0000-00000000000b"

#: Each account's binding carries its own scoped-token reference. Once two
#: accounts name the same virtual connection, the token reference is what
#: separates them.
_TOKEN_REF_A = "token-ref::acct-alpha"
_TOKEN_REF_B = "token-ref::acct-beta"

_TOKEN_A = "oct_scoped_token_account_alpha"
_TOKEN_B = "oct_scoped_token_account_beta"
_CUSTODIAN = "custodian-openconnector-1"
_PROVIDER = "hackernews"
_ACTION = "hackernews.get_top_stories"
_API_KEY = "openconnector-test-key"
_BASE_URL = "http://custodian.test"
_ROUTE_PATH = "/api/guardian/connections/openconnector/actions/{action_id}"

#: A credential-bearing synthetic action and the allowlist that injects it.
#: The injected allowlist is a test-harness affordance; it never widens the
#: production read-only allowlist.
_CREDENTIAL_ACTION = "synthetic.read_records"
_CREDENTIAL_PROVIDER = "synthetic"
_CREDENTIAL_ALLOWLIST = {
    **APPROVED_ACTIONS,
    _CREDENTIAL_ACTION: ApprovedAction(
        action_id=_CREDENTIAL_ACTION,
        provider=_CREDENTIAL_PROVIDER,
        description="Synthetic credential-bearing read action (test-only).",
        connection_selection=ConnectionSelection.EXPLICIT,
        credential_bearing=True,
    ),
}


class _RecordingClient:
    """Instrumented custodian transport that counts dispatches."""

    def __init__(self, *responses: GatewayResponse) -> None:
        self.requests: list[GatewayRequest] = []
        self._responses = list(responses)

    async def send(self, request: GatewayRequest) -> GatewayResponse:
        self.requests.append(request)
        if self._responses:
            return self._responses.pop(0)
        return GatewayResponse(
            status_code=200,
            content=b'{"stories":[{"id":"s-1","title":"A story"}]}',
        )

    @property
    def dispatch_count(self) -> int:
        return len(self.requests)


class _SyntheticResolver:
    """Test-only Guardian-owned binding resolver."""

    def __init__(
        self,
        bindings: tuple[AccountBinding, ...],
        tokens: dict[str, str] | None = None,
    ) -> None:
        self._bindings = bindings
        self._tokens = dict(tokens or {})
        self.binding_resolutions = 0

    async def resolve_binding(
        self, guardian_account_id: str, provider: str
    ) -> AccountBinding | None:
        self.binding_resolutions += 1
        for binding in self._bindings:
            if (
                binding.guardian_account_id == guardian_account_id
                and binding.provider == provider
            ):
                return binding
        return None

    async def resolve_runtime_token(self, binding: AccountBinding) -> str | None:
        return self._tokens.get(str(binding.runtime_token_ref or ""))


def _binding(
    account_id: str,
    connection_id: str = _VIRTUAL_CONNECTION,
    *,
    provider: str = _PROVIDER,
    token_ref: str | None = None,
    state: BindingState = BindingState.AUTHORIZED,
    grants: tuple[str, ...] | None = None,
) -> AccountBinding:
    return AccountBinding(
        guardian_account_id=account_id,
        custodian_id=_CUSTODIAN,
        provider=provider,
        connection_id=connection_id,
        runtime_token_ref=(
            token_ref if token_ref is not None else f"token-ref::{account_id}"
        ),
        allowed_connections=(
            grants if grants is not None else (connection_id,)
        ),
        state=state,
    )


class _GrantingAuthorizer:
    """Test-only Guardian source of *invocation permission*.

    The grant is deliberately expressed independently of the binding: it names
    an account, a subject, a provider, and an action, and it is never derived
    from the existence of a credential.
    """

    def __init__(self, *grants: CustodianUsageGrant) -> None:
        self._grants = list(grants)
        self.authorizations = 0

    async def authorize(
        self,
        *,
        account_id: str,
        subject_id: str,
        provider: str,
        action_id: str,
        task_id: str,
    ) -> CustodianUsageGrant | None:
        self.authorizations += 1
        for grant in self._grants:
            if grant.covers(
                account_id=account_id,
                subject_id=subject_id,
                provider=provider,
                action_id=action_id,
                task_id=task_id,
            ):
                return grant
        return None


def _grant(
    account_id: str = _ACCOUNT_A,
    *,
    subject_id: str | None = None,
    provider: str = _PROVIDER,
    action_id: str = _ACTION,
    task_id: str | None = None,
    granted: bool = True,
) -> CustodianUsageGrant:
    return CustodianUsageGrant(
        guardian_account_id=account_id,
        subject_id=subject_id if subject_id is not None else account_id,
        provider=provider,
        action_id=action_id,
        task_id=task_id,
        granted=granted,
    )


def _install(
    monkeypatch: pytest.MonkeyPatch,
    *,
    resolver: _SyntheticResolver,
    client: _RecordingClient,
    authorizer: CustodianUsageAuthorizer | None = None,
    allowlist: dict[str, Any] | None = None,
) -> None:
    monkeypatch.setenv("GUARDIAN_API_KEY", _API_KEY)
    monkeypatch.setenv("DEBUG", "1")
    monkeypatch.setenv("LOCAL_DEV", "true")
    openconnector_router.configure_openconnector(
        binding_resolver=resolver,
        usage_authorizer=(
            authorizer if authorizer is not None else _GrantingAuthorizer(_grant())
        ),
        gateway_client=client,
        base_url=_BASE_URL,
        allowlist=allowlist,
    )


def _build_app() -> FastAPI:
    """Mount the OpenConnector router the way the deployment mounts it."""

    app = FastAPI(title="openconnector-route-test", version="1.0.0")
    app.include_router(openconnector_router.router)
    hide_paths(
        app,
        [
            route.path
            for route in openconnector_router.router.routes
            if getattr(route, "path", None)
        ],
    )
    return app


def _headers(account_id: str) -> dict[str, str]:
    return {"X-API-Key": _API_KEY, "X-User-Id": account_id}


def _client(app: FastAPI) -> TestClient:
    return TestClient(app)


# ── Authorization and fail-closed behavior ────────────────────────────────


def test_route_requires_an_account_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolver = _SyntheticResolver(
        (_binding(_ACCOUNT_A, _VIRTUAL_CONNECTION),), {_TOKEN_REF_A: _TOKEN_A}
    )
    transport = _RecordingClient()
    _install(monkeypatch, resolver=resolver, client=transport)
    client = _client(_build_app())

    response = client.get(
        f"/api/guardian/connections/openconnector/actions/{_ACTION}",
        headers={"X-API-Key": "not-the-configured-key"},
    )

    assert response.status_code == 401
    assert transport.dispatch_count == 0


def test_authorized_account_dispatches_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolver = _SyntheticResolver(
        (_binding(_ACCOUNT_A, _VIRTUAL_CONNECTION),), {_TOKEN_REF_A: _TOKEN_A}
    )
    transport = _RecordingClient()
    _install(monkeypatch, resolver=resolver, client=transport)
    client = _client(_build_app())

    response = client.get(
        f"/api/guardian/connections/openconnector/actions/{_ACTION}",
        headers=_headers(_ACCOUNT_A),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["outcome"] == "success"
    assert body["data"]["stories"][0]["id"] == "s-1"
    assert transport.dispatch_count == 1
    request = transport.requests[0]
    assert request.url == f"{_BASE_URL}/v1/actions/{_ACTION}"
    # The production reviewed action is a no-auth action, so its custodian-side
    # connection is virtual and the crossing omits the selector.
    assert CONNECTION_SELECTOR_HEADER not in request.headers
    assert json.loads(request.body.decode("utf-8")) == {"input": {}}


def test_response_carries_no_credential_material(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolver = _SyntheticResolver(
        (_binding(_ACCOUNT_A, _VIRTUAL_CONNECTION),), {_TOKEN_REF_A: _TOKEN_A}
    )
    transport = _RecordingClient()
    _install(monkeypatch, resolver=resolver, client=transport)
    client = _client(_build_app())

    response = client.get(
        f"/api/guardian/connections/openconnector/actions/{_ACTION}",
        headers=_headers(_ACCOUNT_A),
    )

    assert _TOKEN_A not in response.text
    assert "oct_" not in response.text


def test_unapproved_action_is_denied_without_dispatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolver = _SyntheticResolver(
        (_binding(_ACCOUNT_A, _VIRTUAL_CONNECTION),), {_TOKEN_REF_A: _TOKEN_A}
    )
    transport = _RecordingClient()
    _install(monkeypatch, resolver=resolver, client=transport)
    client = _client(_build_app())

    response = client.get(
        "/api/guardian/connections/openconnector/actions/notion.delete_everything",
        headers=_headers(_ACCOUNT_A),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "action_not_approved"
    assert transport.dispatch_count == 0


def test_missing_binding_does_not_dispatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolver = _SyntheticResolver((), {})
    transport = _RecordingClient()
    _install(monkeypatch, resolver=resolver, client=transport)
    client = _client(_build_app())

    response = client.get(
        f"/api/guardian/connections/openconnector/actions/{_ACTION}",
        headers=_headers(_ACCOUNT_A),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "missing_profile"
    assert transport.dispatch_count == 0


def test_revoked_binding_does_not_dispatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolver = _SyntheticResolver(
        (
            _binding(
                _ACCOUNT_A,
                _VIRTUAL_CONNECTION,
                state=BindingState.REVOKED,
            ),
        ),
        {_TOKEN_REF_A: _TOKEN_A},
    )
    transport = _RecordingClient()
    _install(monkeypatch, resolver=resolver, client=transport)
    client = _client(_build_app())

    response = client.get(
        f"/api/guardian/connections/openconnector/actions/{_ACTION}",
        headers=_headers(_ACCOUNT_A),
    )

    assert response.status_code == 403
    assert transport.dispatch_count == 0


def test_unknown_account_does_not_dispatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolver = _SyntheticResolver(
        (_binding(_ACCOUNT_A, _VIRTUAL_CONNECTION),), {_TOKEN_REF_A: _TOKEN_A}
    )
    transport = _RecordingClient()
    _install(monkeypatch, resolver=resolver, client=transport)
    client = _client(_build_app())

    response = client.get(
        f"/api/guardian/connections/openconnector/actions/{_ACTION}",
        headers=_headers("acct-unknown"),
    )

    assert response.status_code == 403
    assert transport.dispatch_count == 0


def test_missing_token_reference_does_not_dispatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolver = _SyntheticResolver(
        (_binding(_ACCOUNT_A, _VIRTUAL_CONNECTION),),
        {},
    )
    transport = _RecordingClient()
    _install(monkeypatch, resolver=resolver, client=transport)
    client = _client(_build_app())

    response = client.get(
        f"/api/guardian/connections/openconnector/actions/{_ACTION}",
        headers=_headers(_ACCOUNT_A),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "runtime_token_unavailable"
    assert transport.dispatch_count == 0


def test_cross_account_binding_is_not_usable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Account A cannot spend account B's binding."""

    resolver = _SyntheticResolver(
        (
            _binding(_ACCOUNT_A, _VIRTUAL_CONNECTION),
            _binding(_ACCOUNT_B, _VIRTUAL_CONNECTION),
        ),
        {_TOKEN_REF_A: _TOKEN_A, _TOKEN_REF_B: _TOKEN_B},
    )
    transport = _RecordingClient()
    _install(
        monkeypatch,
        resolver=resolver,
        client=transport,
        authorizer=_GrantingAuthorizer(_grant(account_id=_ACCOUNT_B)),
    )
    client = _client(_build_app())

    response = client.get(
        f"/api/guardian/connections/openconnector/actions/{_ACTION}",
        headers=_headers(_ACCOUNT_B),
    )

    assert response.status_code == 200
    assert transport.dispatch_count == 1
    request = transport.requests[0]
    assert CONNECTION_SELECTOR_HEADER not in request.headers
    assert _TOKEN_B in request.headers["authorization"]


def test_empty_grant_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolver = _SyntheticResolver(
        (_binding(_ACCOUNT_A, _VIRTUAL_CONNECTION, grants=()),),
        {_TOKEN_REF_A: _TOKEN_A},
    )
    transport = _RecordingClient()
    _install(monkeypatch, resolver=resolver, client=transport)
    client = _client(_build_app())

    response = client.get(
        f"/api/guardian/connections/openconnector/actions/{_ACTION}",
        headers=_headers(_ACCOUNT_A),
    )

    assert response.status_code == 403
    assert transport.dispatch_count == 0


def test_execution_time_revalidation_stops_a_revoked_dispatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A revocation between resolution and dispatch stops the crossing.

    The binding is authorized when the route resolves it and unauthorized by the
    time the adapter revalidates immediately before the custodian call, so the
    crossing never happens.
    """

    class _RevokingResolver(_SyntheticResolver):
        async def resolve_binding(
            self, guardian_account_id: str, provider: str
        ) -> AccountBinding | None:
            self.binding_resolutions += 1
            if self.binding_resolutions <= 2:
                return _binding(_ACCOUNT_A, _VIRTUAL_CONNECTION)
            return _binding(
                _ACCOUNT_A, _VIRTUAL_CONNECTION, state=BindingState.REVOKED
            )

    resolver = _RevokingResolver((), {_TOKEN_REF_A: _TOKEN_A})
    transport = _RecordingClient()
    _install(monkeypatch, resolver=resolver, client=transport)
    client = _client(_build_app())

    response = client.get(
        f"/api/guardian/connections/openconnector/actions/{_ACTION}",
        headers=_headers(_ACCOUNT_A),
    )

    assert response.status_code == 403
    assert transport.dispatch_count == 0


def test_custodian_not_configured_reports_needs_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolver = _SyntheticResolver(
        (_binding(_ACCOUNT_A, _VIRTUAL_CONNECTION),), {_TOKEN_REF_A: _TOKEN_A}
    )
    transport = _RecordingClient()
    _install(monkeypatch, resolver=resolver, client=transport)
    openconnector_router.configure_openconnector(
        binding_resolver=resolver,
        gateway_client=transport,
        base_url="",
    )
    client = _client(_build_app())

    response = client.get(
        f"/api/guardian/connections/openconnector/actions/{_ACTION}",
        headers=_headers(_ACCOUNT_A),
    )

    assert response.status_code == 409
    assert response.json()["outcome"] == "needs_configuration"
    assert transport.dispatch_count == 0


def test_custodian_denial_and_failure_stay_distinguishable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolver = _SyntheticResolver(
        (_binding(_ACCOUNT_A, _VIRTUAL_CONNECTION),), {_TOKEN_REF_A: _TOKEN_A}
    )
    transport = _RecordingClient(
        GatewayResponse(
            status_code=403,
            content=b'{"error":"connection_not_allowed","detail":"secret upstream text"}',
        )
    )
    _install(monkeypatch, resolver=resolver, client=transport)
    client = _client(_build_app())

    denied = client.get(
        f"/api/guardian/connections/openconnector/actions/{_ACTION}",
        headers=_headers(_ACCOUNT_A),
    )

    assert denied.status_code == 403
    assert denied.json()["outcome"] == "denied"
    assert "secret upstream text" not in denied.text

    transport = _RecordingClient(
        GatewayResponse(status_code=500, content=b'{"error":"boom"}')
    )
    _install(monkeypatch, resolver=resolver, client=transport)
    failed = client.get(
        f"/api/guardian/connections/openconnector/actions/{_ACTION}",
        headers=_headers(_ACCOUNT_A),
    )

    assert failed.status_code == 503
    assert failed.json()["outcome"] == "unavailable"


def test_payload_is_bounded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An oversized custodian response is refused, and never echoed back."""

    resolver = _SyntheticResolver(
        (_binding(_ACCOUNT_A, _VIRTUAL_CONNECTION),), {_TOKEN_REF_A: _TOKEN_A}
    )
    oversized = json.dumps(
        {"stories": ["x" * 4096 for _ in range(200)]}
    ).encode("utf-8")
    transport = _RecordingClient(
        GatewayResponse(status_code=200, content=oversized)
    )
    _install(monkeypatch, resolver=resolver, client=transport)
    client = _client(_build_app())

    response = client.get(
        f"/api/guardian/connections/openconnector/actions/{_ACTION}",
        headers=_headers(_ACCOUNT_A),
    )

    assert response.status_code == 502
    body = response.json()
    assert body["outcome"] == "failed"
    assert body["code"] == "response_too_large"
    assert len(response.content) <= 262144
    assert "x" * 4096 not in response.text


# ── Credential selection and invocation permission are separate ───────────


def test_binding_without_a_usage_grant_does_not_dispatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A binding's existence does not substitute for the permission check."""

    resolver = _SyntheticResolver(
        (_binding(_ACCOUNT_A, _VIRTUAL_CONNECTION),), {_TOKEN_REF_A: _TOKEN_A}
    )
    transport = _RecordingClient()
    _install(
        monkeypatch,
        resolver=resolver,
        client=transport,
        authorizer=_GrantingAuthorizer(),
    )
    client = _client(_build_app())

    response = client.get(
        f"/api/guardian/connections/openconnector/actions/{_ACTION}",
        headers=_headers(_ACCOUNT_A),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "missing_profile"
    assert transport.dispatch_count == 0


def test_usage_grant_without_a_binding_does_not_dispatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Permission without a credential selects nothing."""

    resolver = _SyntheticResolver((), {})
    transport = _RecordingClient()
    _install(
        monkeypatch,
        resolver=resolver,
        client=transport,
        authorizer=_GrantingAuthorizer(_grant()),
    )
    client = _client(_build_app())

    response = client.get(
        f"/api/guardian/connections/openconnector/actions/{_ACTION}",
        headers=_headers(_ACCOUNT_A),
    )

    assert response.status_code == 403
    assert transport.dispatch_count == 0


def test_no_authorizer_configured_denies_every_crossing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The default is fail-closed, not "the binding implies permission"."""

    resolver = _SyntheticResolver(
        (_binding(_ACCOUNT_A, _VIRTUAL_CONNECTION),), {_TOKEN_REF_A: _TOKEN_A}
    )
    transport = _RecordingClient()
    _install(monkeypatch, resolver=resolver, client=transport)
    openconnector_router.configure_openconnector(
        binding_resolver=resolver,
        gateway_client=transport,
        base_url=_BASE_URL,
    )
    client = _client(_build_app())

    response = client.get(
        f"/api/guardian/connections/openconnector/actions/{_ACTION}",
        headers=_headers(_ACCOUNT_A),
    )

    assert response.status_code == 403
    assert transport.dispatch_count == 0


def test_usage_grant_for_another_action_does_not_dispatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The grant narrows the crossing to the action it names."""

    resolver = _SyntheticResolver(
        (_binding(_ACCOUNT_A, _VIRTUAL_CONNECTION),), {_TOKEN_REF_A: _TOKEN_A}
    )
    transport = _RecordingClient()
    _install(
        monkeypatch,
        resolver=resolver,
        client=transport,
        authorizer=_GrantingAuthorizer(
            _grant(action_id="some.other.read_action")
        ),
    )
    client = _client(_build_app())

    response = client.get(
        f"/api/guardian/connections/openconnector/actions/{_ACTION}",
        headers=_headers(_ACCOUNT_A),
    )

    assert response.status_code == 403
    assert transport.dispatch_count == 0


def test_usage_grant_for_another_account_does_not_dispatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolver = _SyntheticResolver(
        (_binding(_ACCOUNT_A, _VIRTUAL_CONNECTION),), {_TOKEN_REF_A: _TOKEN_A}
    )
    transport = _RecordingClient()
    _install(
        monkeypatch,
        resolver=resolver,
        client=transport,
        authorizer=_GrantingAuthorizer(_grant(account_id=_ACCOUNT_B)),
    )
    client = _client(_build_app())

    response = client.get(
        f"/api/guardian/connections/openconnector/actions/{_ACTION}",
        headers=_headers(_ACCOUNT_A),
    )

    assert response.status_code == 403
    assert transport.dispatch_count == 0


def test_revoked_usage_grant_stops_the_crossing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The independent permission is revalidated immediately before dispatch."""

    class _RevokingAuthorizer(_GrantingAuthorizer):
        async def authorize(self, **kwargs: Any) -> CustodianUsageGrant | None:
            self.authorizations += 1
            # The adapter evaluates the profile once on entry and once
            # immediately before dispatch; the grant is revoked in between.
            if self.authorizations <= 1:
                return _grant()
            return _grant(granted=False)

    resolver = _SyntheticResolver(
        (_binding(_ACCOUNT_A, _VIRTUAL_CONNECTION),), {_TOKEN_REF_A: _TOKEN_A}
    )
    transport = _RecordingClient()
    _install(
        monkeypatch,
        resolver=resolver,
        client=transport,
        authorizer=_RevokingAuthorizer(),
    )
    client = _client(_build_app())

    response = client.get(
        f"/api/guardian/connections/openconnector/actions/{_ACTION}",
        headers=_headers(_ACCOUNT_A),
    )

    assert response.status_code == 403
    assert transport.dispatch_count == 0


# ── Visibility and registration ───────────────────────────────────────────


def test_route_is_absent_from_the_public_document() -> None:
    app = _build_app()

    public_paths = set(build_public_route_schema(app).get("paths", {}))

    assert _ROUTE_PATH not in public_paths


def test_route_is_registered_as_a_read_command() -> None:
    app = _build_app()

    manifest = build_manifest(app)
    command = next(
        command
        for command in manifest.commands
        if command.command_id == "op::openconnector_execute_read_action"
    )

    assert command.method == "GET"
    assert command.path_template == _ROUTE_PATH
    assert command.effect == "read"
    assert command.risk == "read_only"
    assert command.idempotency == "safe"
    assert command.approval_mode == "none"


def test_hosted_public_allowlist_posture_refuses_the_internal_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The hosted posture refuses the internal route for every caller.

    The hosted deployment runs the ``public_allowlist`` exposure mode, which
    refuses every internal-only path for every caller — including the Command
    Bus loopback. The hosted path is therefore unqualified: the command is
    registered, and it cannot be invoked there.
    """

    resolver = _SyntheticResolver(
        (_binding(_ACCOUNT_A, _VIRTUAL_CONNECTION),), {_TOKEN_REF_A: _TOKEN_A}
    )
    transport = _RecordingClient()
    _install(monkeypatch, resolver=resolver, client=transport)

    app = _build_app()
    app.add_middleware(
        PublicExposureMiddleware,
        exposure_mode=PUBLIC_ALLOWLIST_MODE,
        internal_only_paths=app.state.supported_profile_hidden_paths,
    )
    client = _client(app)

    response = client.get(
        f"/api/guardian/connections/openconnector/actions/{_ACTION}",
        headers=_headers(_ACCOUNT_A),
    )

    assert response.status_code == 403
    assert transport.dispatch_count == 0


# ── Actual Command Bus invocation ─────────────────────────────────────────


def _install_asgi_loopback(monkeypatch: pytest.MonkeyPatch, app: FastAPI) -> None:
    """Route the Command Bus loopback into the application under test.

    The loopback request travels the real Guardian stack — the real path
    rendering, the real forwarded headers, the real routing, the real
    dependencies, and the real route handler — over an in-process ASGI
    transport instead of a TCP socket.
    """

    real_client = httpx.AsyncClient

    def _factory(*args: Any, **kwargs: Any) -> httpx.AsyncClient:
        kwargs["transport"] = httpx.ASGITransport(app=app)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(
        loopback_http_adapter.httpx, "AsyncClient", _factory
    )


def _invoke(app: FastAPI, client: TestClient, *, account_id: str) -> dict[str, Any]:
    response = client.post(
        "/api/guardian/commands/invoke",
        headers=_headers(account_id),
        json={
            "invoke_version": "1.0",
            "command_id": "op::openconnector_execute_read_action",
            "actor": {"kind": "agent", "id": account_id},
            "arguments": {"path_params": {"action_id": _ACTION}},
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_command_bus_invokes_the_internal_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolver = _SyntheticResolver(
        (_binding(_ACCOUNT_A, _VIRTUAL_CONNECTION),), {_TOKEN_REF_A: _TOKEN_A}
    )
    transport = _RecordingClient()
    _install(monkeypatch, resolver=resolver, client=transport)
    monkeypatch.setenv(
        "GUARDIAN_COMMAND_BUS_LOOPBACK_BASE", "http://127.0.0.1:9999"
    )
    command_bus_routes.configure_db(None)

    app = _build_app()
    app.include_router(command_bus_routes.router)
    _install_asgi_loopback(monkeypatch, app)
    client = _client(app)

    result = _invoke(app, client, account_id=_ACCOUNT_A)

    assert result["status"] == "completed"
    assert transport.dispatch_count == 1
    assert CONNECTION_SELECTOR_HEADER not in transport.requests[0].headers


def test_command_bus_invocation_fails_closed_without_a_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolver = _SyntheticResolver((), {})
    transport = _RecordingClient()
    _install(monkeypatch, resolver=resolver, client=transport)
    monkeypatch.setenv(
        "GUARDIAN_COMMAND_BUS_LOOPBACK_BASE", "http://127.0.0.1:9999"
    )
    command_bus_routes.configure_db(None)

    app = _build_app()
    app.include_router(command_bus_routes.router)
    _install_asgi_loopback(monkeypatch, app)
    client = _client(app)

    result = _invoke(app, client, account_id=_ACCOUNT_A)

    assert result["status"] == "completed"
    assert transport.dispatch_count == 0
    inline = result.get("inline_result", {})
    assert inline.get("body", {}).get("outcome") == "denied"


# ── Credential-bearing selection is unchanged by the no-auth mode ──────────


def _credential_binding(account_id: str = _ACCOUNT_A) -> AccountBinding:
    """A binding for a credential-bearing synthetic provider."""

    return _binding(
        account_id,
        _CONNECTION_A,
        provider=_CREDENTIAL_PROVIDER,
        token_ref=_TOKEN_REF_A,
    )


def test_credential_bearing_action_names_the_connection_through_the_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The credential-bearing path still sends the explicit selector."""

    resolver = _SyntheticResolver(
        (_credential_binding(_ACCOUNT_A),), {_TOKEN_REF_A: _TOKEN_A}
    )
    transport = _RecordingClient()
    _install(
        monkeypatch,
        resolver=resolver,
        client=transport,
        authorizer=_GrantingAuthorizer(
            _grant(provider=_CREDENTIAL_PROVIDER, action_id=_CREDENTIAL_ACTION)
        ),
        allowlist=_CREDENTIAL_ALLOWLIST,
    )
    client = _client(_build_app())

    response = client.get(
        f"/api/guardian/connections/openconnector/actions/{_CREDENTIAL_ACTION}",
        headers=_headers(_ACCOUNT_A),
    )

    assert response.status_code == 200
    assert transport.dispatch_count == 1
    request = transport.requests[0]
    assert request.headers[CONNECTION_SELECTOR_HEADER] == _CONNECTION_A
    assert request.headers["authorization"] == f"Bearer {_TOKEN_A}"


def test_credential_bearing_action_is_never_downgraded_to_no_auth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A missing binding is a denial, not a reason to omit the selector."""

    resolver = _SyntheticResolver((), {})
    transport = _RecordingClient()
    _install(
        monkeypatch,
        resolver=resolver,
        client=transport,
        authorizer=_GrantingAuthorizer(
            _grant(provider=_CREDENTIAL_PROVIDER, action_id=_CREDENTIAL_ACTION)
        ),
        allowlist=_CREDENTIAL_ALLOWLIST,
    )
    client = _client(_build_app())

    response = client.get(
        f"/api/guardian/connections/openconnector/actions/{_CREDENTIAL_ACTION}",
        headers=_headers(_ACCOUNT_A),
    )

    assert response.status_code == 403
    assert transport.dispatch_count == 0


def test_no_auth_action_never_sends_a_connection_selector(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The no-auth crossing omits the selector and names no connection."""

    resolver = _SyntheticResolver(
        (_binding(_ACCOUNT_A, _VIRTUAL_CONNECTION),), {_TOKEN_REF_A: _TOKEN_A}
    )
    transport = _RecordingClient()
    _install(monkeypatch, resolver=resolver, client=transport)
    client = _client(_build_app())

    response = client.get(
        f"/api/guardian/connections/openconnector/actions/{_ACTION}",
        headers=_headers(_ACCOUNT_A),
    )

    assert response.status_code == 200
    request = transport.requests[0]
    assert CONNECTION_SELECTOR_HEADER not in request.headers
    assert request.headers["authorization"] == f"Bearer {_TOKEN_A}"
    assert json.loads(request.body.decode("utf-8")) == {"input": {}}
