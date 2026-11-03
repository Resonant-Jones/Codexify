"""Credential-bearing account isolation for the OpenConnector crossing.

Two layers live in this file:

* Synthetic tests (always run): the two-account isolation matrix against an
  instrumented transport. They pin Guardian-side selection, narrowing, and
  per-account bearer use without needing a gateway.
* Live tests (skipped unless the disposable trial gateway is present): the
  same matrix through the real Guardian route and real HTTP against the
  pinned gateway, with disposable credential-bearing connections. Enable
  with ``GATEB_LIVE=1`` plus ``GATEB_LIVE_BASE_URL``,
  ``GATEB_LIVE_UUID_A/B``, ``GATEB_LIVE_TOKEN_A/B``, and
  ``GATEB_LIVE_API_KEY``. A skip is not live proof; the recorded trial run
  is.

The reviewed credential-bearing action is
``aeroleads.get_details_from_linkedin_url`` (explicit selection). The fake
provider credentials used live are intentionally invalid at the provider, so
an authorized, gateway-accepted call ends in a bounded provider rejection —
which is exactly what distinguishes Guardian authorization, gateway grant
acceptance, and provider authentication.
"""

from __future__ import annotations

import asyncio
import json
import os

import pytest

from guardian.connections.openconnector.adapter import (
    ExecutionAuthority,
    OpenConnectorAdapter,
)
from guardian.connections.openconnector.authority import CustodianUsageGrant
from guardian.connections.openconnector.bindings import (
    AccountBinding,
    BindingState,
)
from guardian.connections.openconnector.policy import (
    APPROVED_ACTIONS,
    get_approved_action,
)
from guardian.connections.openconnector.service import (
    CONNECTION_SELECTOR_HEADER,
    GatewayRequest,
    GatewayResponse,
    OpenConnectorService,
)

ACTION_ID = "aeroleads.get_details_from_linkedin_url"
PROVIDER = "aeroleads"
ACCOUNT_A = "iso-acct-a"
ACCOUNT_B = "iso-acct-b"
UUID_A = "aaaaaaaa-1111-4111-8111-aaaaaaaaaaa1"
UUID_B = "bbbbbbbb-2222-4222-8222-bbbbbbbbbbb2"
TOKEN_A = "oct_synthetic_account_alpha"
TOKEN_B = "oct_synthetic_account_beta"
REF_A = "token-ref::iso-acct-a"
REF_B = "token-ref::iso-acct-b"


def test_production_allowlist_reviews_exactly_one_credentialed_action() -> None:
    action = get_approved_action(ACTION_ID, APPROVED_ACTIONS)
    assert action is not None
    assert action.provider == PROVIDER
    assert action.credential_bearing is True
    assert str(action.connection_selection.value) == "explicit"
    credentialed = [a for a in APPROVED_ACTIONS.values()
                    if a.credential_bearing]
    assert [a.action_id for a in credentialed] == [ACTION_ID]


class _RecordingClient:
    def __init__(self, *responses: GatewayResponse) -> None:
        self.requests: list[GatewayRequest] = []
        self._responses = list(responses)

    async def send(self, request: GatewayRequest) -> GatewayResponse:
        self.requests.append(request)
        if self._responses:
            return self._responses.pop(0)
        return GatewayResponse(status_code=200, content=b'{"ok":true}')

    @property
    def dispatch_count(self) -> int:
        return len(self.requests)


class _Resolver:
    def __init__(self, bindings, tokens) -> None:
        self._bindings = bindings
        self._tokens = dict(tokens)

    async def resolve_binding(self, account_id, provider):
        for binding in self._bindings:
            if (binding.guardian_account_id == account_id
                    and binding.provider == provider):
                return binding
        return None

    async def resolve_runtime_token(self, binding):
        return self._tokens.get(str(binding.runtime_token_ref or ""))


class _Authorizer:
    def __init__(self, granted=True) -> None:
        self._granted = granted

    async def authorize(self, *, account_id, subject_id, provider,
                        action_id, task_id):
        return CustodianUsageGrant(
            guardian_account_id=account_id, subject_id=subject_id,
            provider=provider, action_id=action_id, granted=self._granted)


def _credential_binding(account_id, connection_id, token_ref,
                        allowed=None, state=BindingState.AUTHORIZED):
    return AccountBinding(
        guardian_account_id=account_id, custodian_id="custodian-iso",
        provider=PROVIDER, connection_id=connection_id,
        runtime_token_ref=token_ref,
        allowed_connections=(allowed if allowed is not None
                             else (connection_id,)),
        state=state)


def _profile(account_id, task_id="task-iso"):
    from guardian.command_bus.permission_profiles import PermissionProfile
    return PermissionProfile(
        profile_id="iso-profile", actor_id=account_id, subject_id=account_id,
        task_id=task_id, allowed_command_classes=("connector",),
        allowed_command_ids=(f"openconnector::{ACTION_ID}",),
        connector_allowed=True, network_allowed=True)


def _authority(account_id, *, requested=None, profile=None,
               task_id="task-iso"):
    return ExecutionAuthority(
        guardian_account_id=account_id, provider=PROVIDER, action_id=ACTION_ID,
        actor_id=account_id, subject_id=account_id, task_id=task_id,
        permission_profile_provider=(lambda: profile)
        if profile is not None else (lambda: _profile(account_id, task_id)),
        arguments={"linkedin_url": "https://www.linkedin.com/in/example"},
        requested_connection_id=requested)


def _adapter(client, resolver):
    service = OpenConnectorService("http://iso.internal:3000", client)
    return OpenConnectorAdapter(service, resolver)


def _resolver_both() -> _Resolver:
    return _Resolver(
        (_credential_binding(ACCOUNT_A, UUID_A, REF_A),
         _credential_binding(ACCOUNT_B, UUID_B, REF_B)),
        {REF_A: TOKEN_A, REF_B: TOKEN_B})


def _run(coro):
    return asyncio.run(coro)


def _bearer_of(request: GatewayRequest) -> str:
    return str(dict(request.headers).get("authorization", ""))


def test_each_account_dispatches_with_its_own_connection_and_bearer() -> None:
    client = _RecordingClient()
    adapter = _adapter(client, _resolver_both())

    result_a = _run(adapter.execute_action(_authority(ACCOUNT_A)))
    result_b = _run(adapter.execute_action(_authority(ACCOUNT_B)))

    assert result_a.outcome.value == "success"
    assert result_b.outcome.value == "success"
    assert client.dispatch_count == 2
    first, second = client.requests
    assert first.headers[CONNECTION_SELECTOR_HEADER] == UUID_A
    assert second.headers[CONNECTION_SELECTOR_HEADER] == UUID_B
    assert _bearer_of(first) == f"Bearer {TOKEN_A}"
    assert _bearer_of(second) == f"Bearer {TOKEN_B}"


def test_cross_account_selection_is_refused_without_dispatch() -> None:
    client = _RecordingClient()
    adapter = _adapter(client, _resolver_both())

    result = _run(adapter.execute_action(
        _authority(ACCOUNT_A, requested=UUID_B)))

    assert result.outcome.value == "denied"
    assert result.code == "connection_not_granted"
    assert client.dispatch_count == 0


def test_unknown_connection_is_refused_without_dispatch() -> None:
    client = _RecordingClient()
    adapter = _adapter(client, _resolver_both())

    result = _run(adapter.execute_action(
        _authority(ACCOUNT_A, requested="cccccccc-3333-4333-8333-ccccccccccc3")))

    assert result.outcome.value == "denied"
    assert client.dispatch_count == 0


def test_other_account_binding_is_unusable() -> None:
    client = _RecordingClient()
    adapter = _adapter(client, _resolver_both())

    result = _run(adapter.execute_action(_authority(ACCOUNT_B)))

    assert result.outcome.value == "success"
    assert client.requests[0].headers[CONNECTION_SELECTOR_HEADER] == UUID_B
    lone = _Resolver((_credential_binding(ACCOUNT_B, UUID_B, REF_B),),
                     {REF_B: TOKEN_B})
    denied = _run(_adapter(_RecordingClient(), lone).execute_action(
        _authority("iso-acct-stranger")))
    assert denied.outcome.value == "denied"


# --- Live qualification (disposable trial gateway only) ---------------------
#
# These tests run if and only if the trial environment is present. They drive
# the real Guardian route and real HTTP against the pinned gateway with
# disposable credential-bearing connections. A skip is not live proof; the
# recorded trial execution is.

def _live_env() -> dict[str, str] | None:
    if os.getenv("GATEB_LIVE") != "1":
        return None
    required = ("GATEB_LIVE_BASE_URL", "GATEB_LIVE_UUID_A",
                "GATEB_LIVE_UUID_B", "GATEB_LIVE_TOKEN_A",
                "GATEB_LIVE_TOKEN_B", "GATEB_LIVE_API_KEY")
    missing = [key for key in required if not os.getenv(key, "").strip()]
    if missing:
        pytest.fail(f"GATEB_LIVE=1 but missing trial env: {missing}")
    return {key: str(os.getenv(key, "")) for key in required}


LIVE_REASON = "needs disposable trial gateway (GATEB_LIVE=1 plus trial env)"


class _LiveRecorder:
    """Dispatch observer over the real HTTP transport.

    Records URL, method, header names, bearer presence, selector value, and
    body length. Bearer VALUES are never stored.
    """

    def __init__(self, base_url: str) -> None:
        self._client = None
        self._service_base = base_url
        self.requests: list[dict] = []

    def _gateway_client(self):
        # Constructed lazily inside the live event loop: an httpx client
        # created outside it binds to the wrong (closed) loop under pytest.
        if self._client is None:
            import httpx

            from guardian.connections.openconnector.service import (
                HttpxGatewayClient,
            )
            self._client = HttpxGatewayClient(
                httpx.AsyncClient(follow_redirects=False, trust_env=False))
        return self._client

    def service(self) -> OpenConnectorService:
        return OpenConnectorService(self._service_base, self)

    async def send(self, request: GatewayRequest) -> GatewayResponse:
        headers = dict(request.headers)
        auth = str(headers.get("authorization", ""))
        self.requests.append({
            "method": request.method,
            "url": request.url,
            "bearer_present": auth.startswith("Bearer ") and len(auth) > 20,
            "selector": headers.get(CONNECTION_SELECTOR_HEADER),
            "body_len": len(request.body or b""),
        })
        return await self._gateway_client().send(request)

    @property
    def dispatch_count(self) -> int:
        return len(self.requests)


def _live_binding(account_id: str, connection_id: str) -> AccountBinding:
    return AccountBinding(
        guardian_account_id=account_id, custodian_id="custodian-gateb5-trial",
        provider=PROVIDER, connection_id=connection_id,
        runtime_token_ref=f"token-ref::{account_id}",
        allowed_connections=(connection_id,),
        state=BindingState.AUTHORIZED)


def _live_fixtures(env: dict[str, str]):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from guardian.connections.openconnector import router as oc_router
    from guardian.core.route_visibility import hide_paths

    recorder = _LiveRecorder(env["GATEB_LIVE_BASE_URL"])
    resolver = _Resolver(
        (_live_binding(ACCOUNT_A, env["GATEB_LIVE_UUID_A"]),
         _live_binding(ACCOUNT_B, env["GATEB_LIVE_UUID_B"])),
        {f"token-ref::{ACCOUNT_A}": env["GATEB_LIVE_TOKEN_A"],
         f"token-ref::{ACCOUNT_B}": env["GATEB_LIVE_TOKEN_B"]})
    oc_router.configure_openconnector(
        binding_resolver=resolver, usage_authorizer=_Authorizer(True),
        gateway_client=recorder, base_url=env["GATEB_LIVE_BASE_URL"])
    app = FastAPI(title="gateb5-live-isolation", version="1.0.0")
    app.include_router(oc_router.router)
    hide_paths(app, [route.path for route in oc_router.router.routes
                     if getattr(route, "path", None)])
    client = TestClient(app, raise_server_exceptions=False)
    return app, client, recorder


from contextlib import contextmanager


@contextmanager
def _live_client(env: dict[str, str]):
    """Entered TestClient: one persistent portal/loop for the test.

    A TestClient used without entering starts a fresh event loop per
    request, which would strand the shared HTTP pool (created inside the
    recorder) on a closed loop between the first and second request.
    """
    _, client, recorder = _live_fixtures(env)
    with client:
        yield client, recorder


def _live_headers(env: dict[str, str], account_id: str) -> dict[str, str]:
    return {"X-API-Key": env["GATEB_LIVE_API_KEY"], "X-User-Id": account_id}


def _live_get(client, env, account_id: str):
    return client.get(
        f"/api/guardian/connections/openconnector/actions/{ACTION_ID}",
        headers=_live_headers(env, account_id))


@pytest.mark.skipif(_live_env() is None, reason=LIVE_REASON)
def test_live_each_account_uses_its_own_connection() -> None:
    env = _live_env()
    assert env is not None
    with _live_client(env) as (client, recorder):
        response_a = _live_get(client, env, ACCOUNT_A)
        response_b = _live_get(client, env, ACCOUNT_B)

        # The fake credentials fail at the provider: Guardian authorized
        # and the gateway accepted the scoped selection, then the provider
        # rejected the key. That rejection IS the expected live shape, and
        # it proves the call reached the provider with the right
        # connection.
        for response in (response_a, response_b):
            assert response.status_code == 502, response.text
            assert response.json().get("outcome") == "failed"
        assert recorder.dispatch_count == 2
        first, second = recorder.requests
        assert first["selector"] == env["GATEB_LIVE_UUID_A"]
        assert second["selector"] == env["GATEB_LIVE_UUID_B"]
        assert first["bearer_present"] and second["bearer_present"]
        assert first["url"].endswith(f"/v1/actions/{ACTION_ID}")


@pytest.mark.skipif(_live_env() is None, reason=LIVE_REASON)
def test_live_cross_account_selection_is_refused_before_dispatch() -> None:
    env = _live_env()
    assert env is not None
    _, _, recorder = _live_fixtures(env)
    service = recorder.service()
    adapter = OpenConnectorAdapter(
        service,
        _Resolver(
            (_live_binding(ACCOUNT_A, env["GATEB_LIVE_UUID_A"]),),
            {f"token-ref::{ACCOUNT_A}": env["GATEB_LIVE_TOKEN_A"]}))

    result = _run(adapter.execute_action(_authority(
        ACCOUNT_A, requested=env["GATEB_LIVE_UUID_B"])))

    assert result.outcome.value == "denied"
    assert result.code == "connection_not_granted"
    assert recorder.dispatch_count == 0


@pytest.mark.skipif(_live_env() is None, reason=LIVE_REASON)
def test_live_unknown_connection_is_refused_before_dispatch() -> None:
    env = _live_env()
    assert env is not None
    _, _, recorder = _live_fixtures(env)
    adapter = OpenConnectorAdapter(
        recorder.service(),
        _Resolver(
            (_live_binding(ACCOUNT_A, env["GATEB_LIVE_UUID_A"]),),
            {f"token-ref::{ACCOUNT_A}": env["GATEB_LIVE_TOKEN_A"]}))

    result = _run(adapter.execute_action(_authority(
        ACCOUNT_A, requested="cccccccc-3333-4333-8333-ccccccccccc3")))

    assert result.outcome.value == "denied"
    assert recorder.dispatch_count == 0


@pytest.mark.skipif(_live_env() is None, reason=LIVE_REASON)
def test_live_gateway_grant_denies_a_foreign_token_pairing() -> None:
    """The gateway's independent enforcement, over real HTTP.

    Account A's scoped bearer aimed at account B's connection must be refused
    by the gateway grant itself. A master-class bearer would bypass the
    grant, so this denial also proves the live dispatches above ran under
    scoped bearers rather than a privileged credential.
    """
    import urllib.request

    env = _live_env()
    assert env is not None
    request = urllib.request.Request(
        f"{env['GATEB_LIVE_BASE_URL']}/v1/actions/{ACTION_ID}",
        data=json.dumps(
            {"input": {"linkedin_url": "https://www.linkedin.com/in/example"}}
        ).encode(),
        method="POST")
    request.add_header("Content-Type", "application/json")
    request.add_header("Authorization", f"Bearer {env['GATEB_LIVE_TOKEN_A']}")
    request.add_header(CONNECTION_SELECTOR_HEADER, env["GATEB_LIVE_UUID_B"])
    try:
        with urllib.request.urlopen(request, timeout=30):
            status, code = 200, None
    except urllib.error.HTTPError as exc:
        try:
            code = json.loads(exc.read().decode("utf-8", "replace")).get(
                "errorCode")
        except Exception:
            code = None
        status = exc.code
    assert (status, code) == (403, "connection_not_allowed")


@pytest.mark.skipif(_live_env() is None, reason=LIVE_REASON)
def test_live_revoked_empty_and_missing_authority_fail_closed() -> None:
    env = _live_env()
    assert env is not None
    import dataclasses

    from guardian.connections.openconnector import router as oc_router

    with _live_client(env) as (client, recorder):

        def install(resolver, authorizer=None):
            oc_router.configure_openconnector(
                binding_resolver=resolver,
                usage_authorizer=(authorizer if authorizer is not None
                                  else _Authorizer(True)),
                gateway_client=recorder,
                base_url=env["GATEB_LIVE_BASE_URL"])

        install(_Resolver((), {}))
        response = _live_get(client, env, ACCOUNT_A)
        assert response.status_code == 403
        assert recorder.dispatch_count == 0

        revoked = dataclasses.replace(
            _live_binding(ACCOUNT_A, env["GATEB_LIVE_UUID_A"]),
            state=BindingState.REVOKED)
        install(_Resolver(
            (revoked,),
            {f"token-ref::{ACCOUNT_A}": env["GATEB_LIVE_TOKEN_A"]}))
        response = _live_get(client, env, ACCOUNT_A)
        assert response.status_code == 403
        assert recorder.dispatch_count == 0

        empty = dataclasses.replace(
            _live_binding(ACCOUNT_A, env["GATEB_LIVE_UUID_A"]),
            allowed_connections=())
        install(_Resolver(
            (empty,),
            {f"token-ref::{ACCOUNT_A}": env["GATEB_LIVE_TOKEN_A"]}))
        response = _live_get(client, env, ACCOUNT_A)
        assert response.status_code == 403
        assert recorder.dispatch_count == 0

        install(_Resolver(
            (_live_binding(ACCOUNT_A, env["GATEB_LIVE_UUID_A"]),),
            {f"token-ref::{ACCOUNT_A}": env["GATEB_LIVE_TOKEN_A"]}),
            _Authorizer(False))
        response = _live_get(client, env, ACCOUNT_A)
        assert response.status_code == 403
        assert recorder.dispatch_count == 0


@pytest.mark.skipif(_live_env() is None, reason=LIVE_REASON)
def test_live_revalidation_stops_a_revoked_dispatch() -> None:
    """Matrix H: authority revoked between check and dispatch.

    The profile provider grants on first evaluation and denies on second,
    simulating a revocation landing mid-flight. The live-configured adapter
    must refuse without dispatching.
    """
    from guardian.command_bus.permission_profiles import PermissionProfile

    env = _live_env()
    assert env is not None
    _, _, recorder = _live_fixtures(env)
    calls = {"count": 0}

    def flipping_provider():
        calls["count"] += 1
        if calls["count"] == 1:
            return PermissionProfile(
                profile_id="iso-live", actor_id=ACCOUNT_A,
                subject_id=ACCOUNT_A, task_id="task-live-h",
                allowed_command_classes=("connector",),
                allowed_command_ids=(f"openconnector::{ACTION_ID}",),
                connector_allowed=True, network_allowed=True)
        return None

    authority = ExecutionAuthority(
        guardian_account_id=ACCOUNT_A, provider=PROVIDER, action_id=ACTION_ID,
        actor_id=ACCOUNT_A, subject_id=ACCOUNT_A, task_id="task-live-h",
        permission_profile_provider=flipping_provider,
        arguments={"linkedin_url": "https://www.linkedin.com/in/example"},
        requested_connection_id=None)
    adapter = OpenConnectorAdapter(
        recorder.service(),
        _Resolver(
            (_live_binding(ACCOUNT_A, env["GATEB_LIVE_UUID_A"]),),
            {f"token-ref::{ACCOUNT_A}": env["GATEB_LIVE_TOKEN_A"]}))

    result = _run(adapter.execute_action(authority))

    assert calls["count"] == 2
    assert result.outcome.value == "denied"
    assert recorder.dispatch_count == 0


@pytest.mark.skipif(_live_env() is None, reason=LIVE_REASON)
def test_live_evidence_carries_no_credential_material() -> None:
    env = _live_env()
    assert env is not None
    with _live_client(env) as (client, recorder):
        response = _live_get(client, env, ACCOUNT_A)

        corpus = response.text + json.dumps(recorder.requests, default=str)
        for secret in (env["GATEB_LIVE_TOKEN_A"], env["GATEB_LIVE_TOKEN_B"]):
            assert secret not in corpus
        assert "FAKE_GATEB5" not in corpus
