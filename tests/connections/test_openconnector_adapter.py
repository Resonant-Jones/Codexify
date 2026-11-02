"""Fail-closed and two-account isolation proof for the OpenConnector adapter.

These tests exercise the adapter core against an instrumented in-process
transport. They prove adapter logic only: they are **not** live upstream
execution and they are **not** Gate B qualification.

What is proven here:

* Guardian authorization is required before any custodian dispatch, and it is
  revalidated immediately before the crossing.
* Two synthetic accounts stay isolated across positive and negative paths,
  using credential-bearing synthetic connections.
* Missing, revoked, mismatched, empty-grant, and uncertain authority all fail
  closed with zero custodian calls.
* The deployment guard and the operator admin token are never used as an
  execution credential, and there is no fallback to another account's
  credential or to a shared default connection.
* Provider error text and credential material do not escape through results.
"""

from __future__ import annotations

import asyncio
import json

import pytest

from guardian.command_bus.permission_profiles import PermissionProfile
from guardian.connections.openconnector.adapter import (
    AdapterOutcome,
    ExecutionAuthority,
    OpenConnectorAdapter,
)
from guardian.connections.openconnector.bindings import AccountBinding, BindingState
from guardian.connections.openconnector.policy import (
    APPROVED_ACTIONS,
    ApprovedAction,
)
from guardian.connections.openconnector.service import (
    CONNECTION_SELECTOR_HEADER,
    GatewayRequest,
    GatewayResponse,
    GatewayTimeoutError,
    OpenConnectorService,
)

_ACCOUNT_A = "acct-alpha"
_ACCOUNT_B = "acct-beta"
_ACCOUNT_UNKNOWN = "acct-unknown"
_CONNECTION_A = "aaaaaaaa-0000-0000-0000-00000000000a"
_CONNECTION_B = "bbbbbbbb-0000-0000-0000-00000000000b"
_TOKEN_A = "oct_scoped_token_account_alpha"
_TOKEN_B = "oct_scoped_token_account_beta"
_CUSTODIAN = "custodian-openconnector-1"
_PROVIDER = "synthetic"

#: Test-only, credential-bearing synthetic action. It is injected by the test
#: harness and never enters the production allowlist.
_SYNTHETIC_ACTION_ID = "synthetic.read_records"
_TEST_ALLOWLIST = {
    **APPROVED_ACTIONS,
    _SYNTHETIC_ACTION_ID: ApprovedAction(
        action_id=_SYNTHETIC_ACTION_ID,
        provider=_PROVIDER,
        description="Synthetic credential-bearing read action (test-only).",
        requires_connection=True,
        credential_bearing=True,
    ),
}

_DEFAULT = object()


class _RecordingClient:
    """Instrumented transport that counts dispatches."""

    def __init__(self, *responses: GatewayResponse, raise_error: Exception | None = None) -> None:
        self.requests: list[GatewayRequest] = []
        self._responses = list(responses)
        self._raise_error = raise_error

    async def send(self, request: GatewayRequest) -> GatewayResponse:
        self.requests.append(request)
        if self._raise_error is not None:
            raise self._raise_error
        if self._responses:
            return self._responses.pop(0)
        return GatewayResponse(status_code=200, content=b'{"records":[{"id":"r-1"}]}')

    @property
    def dispatch_count(self) -> int:
        return len(self.requests)


class _SyntheticResolver:
    """Test-only Guardian-owned binding resolver."""

    def __init__(
        self,
        bindings: tuple[AccountBinding, ...],
        tokens: dict[str, str] | None = None,
        *,
        forced_binding: AccountBinding | None = None,
    ) -> None:
        self._bindings = bindings
        self._tokens = dict(tokens or {})
        self._forced_binding = forced_binding
        self.token_resolutions = 0

    async def resolve_binding(
        self, guardian_account_id: str, provider: str
    ) -> AccountBinding | None:
        if self._forced_binding is not None:
            return self._forced_binding
        for binding in self._bindings:
            if (
                binding.guardian_account_id == guardian_account_id
                and binding.provider == provider
            ):
                return binding
        return None

    async def resolve_runtime_token(self, binding: AccountBinding) -> str | None:
        self.token_resolutions += 1
        return self._tokens.get(str(binding.runtime_token_ref or ""))


def _binding(
    account_id: str = _ACCOUNT_A,
    connection_uuid: str = _CONNECTION_A,
    token_ref: str = "token-a",
    allowed: tuple[str, ...] = (_CONNECTION_A,),
    state: BindingState = BindingState.AUTHORIZED,
    provider: str = _PROVIDER,
) -> AccountBinding:
    return AccountBinding(
        guardian_account_id=account_id,
        custodian_id=_CUSTODIAN,
        provider=provider,
        connection_uuid=connection_uuid,
        connection_alias=f"alias-{connection_uuid[-1]}",
        runtime_token_ref=token_ref,
        allowed_connections=allowed,
        state=state,
    )


def _profile(account_id: str, **overrides) -> PermissionProfile:
    values = {
        "profile_id": "test-profile",
        "actor_id": account_id,
        "subject_id": account_id,
        "task_id": "task-1",
        "allowed_command_classes": ("connector",),
        "connector_allowed": True,
        "network_allowed": True,
    }
    values.update(overrides)
    return PermissionProfile(**values)


def _authority(
    account_id: str = _ACCOUNT_A,
    *,
    action_id: str = _SYNTHETIC_ACTION_ID,
    provider: str = _PROVIDER,
    profile=_DEFAULT,
    profile_provider=None,
    requested_connection: str | None = None,
    arguments: dict | None = None,
) -> ExecutionAuthority:
    if profile_provider is None:
        resolved = _profile(account_id) if profile is _DEFAULT else profile
        profile_provider = lambda: resolved
    return ExecutionAuthority(
        guardian_account_id=account_id,
        provider=provider,
        action_id=action_id,
        actor_id=account_id,
        subject_id=account_id,
        task_id="task-1",
        permission_profile_provider=profile_provider,
        arguments=dict(arguments or {}),
        requested_connection_uuid=requested_connection,
    )


def _adapter(
    client: _RecordingClient,
    resolver,
    *,
    allowlist=_TEST_ALLOWLIST,
    max_payload_bytes: int | None = None,
) -> OpenConnectorAdapter:
    service = OpenConnectorService("http://openconnector.internal:3000", client)
    if max_payload_bytes is None:
        return OpenConnectorAdapter(service, resolver, allowlist=allowlist)
    return OpenConnectorAdapter(
        service, resolver, allowlist=allowlist, max_payload_bytes=max_payload_bytes
    )


def _resolver() -> _SyntheticResolver:
    return _SyntheticResolver(
        (
            _binding(_ACCOUNT_A, _CONNECTION_A, "token-a", (_CONNECTION_A,)),
            _binding(_ACCOUNT_B, _CONNECTION_B, "token-b", (_CONNECTION_B,)),
        ),
        {"token-a": _TOKEN_A, "token-b": _TOKEN_B},
    )


def _run(coro):
    return asyncio.run(coro)


# --- allowlist ---------------------------------------------------------------


def test_production_allowlist_does_not_contain_the_synthetic_action() -> None:
    assert _SYNTHETIC_ACTION_ID not in APPROVED_ACTIONS
    assert "hackernews.get_top_stories" in APPROVED_ACTIONS


def test_unapproved_action_makes_zero_gateway_calls() -> None:
    client = _RecordingClient()
    adapter = _adapter(client, _resolver())

    result = _run(
        adapter.execute_action(
            _authority(action_id="synthetic.write_records")
        )
    )

    assert result.outcome is AdapterOutcome.DENIED
    assert result.code == "action_not_approved"
    assert client.dispatch_count == 0


# --- positive execution ------------------------------------------------------


def test_approved_action_dispatches_once_with_the_account_scoped_bearer() -> None:
    client = _RecordingClient()
    adapter = _adapter(client, _resolver())

    result = _run(adapter.execute_action(_authority(_ACCOUNT_A)))

    assert result.outcome is AdapterOutcome.SUCCESS
    assert result.dispatched is True
    assert client.dispatch_count == 1

    sent = client.requests[0]
    assert sent.headers["authorization"] == f"Bearer {_TOKEN_A}"
    assert sent.headers[CONNECTION_SELECTOR_HEADER] == _CONNECTION_A


def test_omitted_connection_selector_uses_the_binding_connection() -> None:
    client = _RecordingClient()
    adapter = _adapter(client, _resolver())

    result = _run(adapter.execute_action(_authority(_ACCOUNT_A)))

    assert result.outcome is AdapterOutcome.SUCCESS
    sent = client.requests[0]
    assert sent.headers[CONNECTION_SELECTOR_HEADER] == _CONNECTION_A

    # The request never falls back to a default or shared connection: the
    # selector is always present, and the body carries no connection field.
    body = sent.body.decode("utf-8")
    assert "connectionName" not in body
    assert "connectionId" not in body


# --- two-account isolation ---------------------------------------------------


def test_account_a_uses_only_its_own_binding() -> None:
    client = _RecordingClient()
    adapter = _adapter(client, _resolver())

    result = _run(adapter.execute_action(_authority(_ACCOUNT_A)))

    assert result.outcome is AdapterOutcome.SUCCESS
    assert client.requests[0].headers[CONNECTION_SELECTOR_HEADER] == _CONNECTION_A
    assert client.requests[0].headers["authorization"] == f"Bearer {_TOKEN_A}"


def test_account_b_uses_only_its_own_binding() -> None:
    client = _RecordingClient()
    adapter = _adapter(client, _resolver())

    result = _run(adapter.execute_action(_authority(_ACCOUNT_B)))

    assert result.outcome is AdapterOutcome.SUCCESS
    assert client.requests[0].headers[CONNECTION_SELECTOR_HEADER] == _CONNECTION_B
    assert client.requests[0].headers["authorization"] == f"Bearer {_TOKEN_B}"


def test_account_a_cannot_select_account_b_connection() -> None:
    client = _RecordingClient()
    adapter = _adapter(client, _resolver())

    result = _run(
        adapter.execute_action(
            _authority(_ACCOUNT_A, requested_connection=_CONNECTION_B)
        )
    )

    assert result.outcome is AdapterOutcome.DENIED
    assert result.code == "connection_not_granted"
    assert client.dispatch_count == 0


def test_account_b_cannot_select_account_a_connection() -> None:
    client = _RecordingClient()
    adapter = _adapter(client, _resolver())

    result = _run(
        adapter.execute_action(
            _authority(_ACCOUNT_B, requested_connection=_CONNECTION_A)
        )
    )

    assert result.outcome is AdapterOutcome.DENIED
    assert result.code == "connection_not_granted"
    assert client.dispatch_count == 0


def test_binding_for_another_account_is_refused() -> None:
    client = _RecordingClient()
    # A resolver that hands back account B's binding regardless of the
    # requesting account: the adapter's own account cross-check must refuse.
    resolver = _SyntheticResolver((), forced_binding=_binding(_ACCOUNT_B, _CONNECTION_B, "token-b"))
    adapter = _adapter(client, resolver)

    result = _run(adapter.execute_action(_authority(_ACCOUNT_A)))

    assert result.outcome is AdapterOutcome.DENIED
    assert result.code == "binding_account_mismatch"
    assert client.dispatch_count == 0


def test_binding_for_another_provider_is_refused() -> None:
    client = _RecordingClient()
    resolver = _SyntheticResolver(
        (), forced_binding=_binding(_ACCOUNT_A, _CONNECTION_A, "token-a", (_CONNECTION_A,), provider="other")
    )
    adapter = _adapter(client, resolver)

    result = _run(adapter.execute_action(_authority(_ACCOUNT_A)))

    assert result.outcome is AdapterOutcome.DENIED
    assert result.code == "binding_provider_mismatch"
    assert client.dispatch_count == 0


# --- fail-closed authority ----------------------------------------------------


def test_revoked_binding_prevents_dispatch() -> None:
    client = _RecordingClient()
    resolver = _SyntheticResolver(
        (
            _binding(
                _ACCOUNT_A, _CONNECTION_A, "token-a", (_CONNECTION_A,), state=BindingState.REVOKED
            ),
        ),
        {"token-a": _TOKEN_A},
    )
    adapter = _adapter(client, resolver)

    result = _run(adapter.execute_action(_authority(_ACCOUNT_A)))

    assert result.outcome is AdapterOutcome.DENIED
    assert result.code == "binding_not_authorized"
    assert client.dispatch_count == 0


def test_unknown_binding_state_prevents_dispatch() -> None:
    client = _RecordingClient()
    resolver = _SyntheticResolver(
        (
            _binding(
                _ACCOUNT_A, _CONNECTION_A, "token-a", (_CONNECTION_A,), state=BindingState.UNKNOWN
            ),
        ),
        {"token-a": _TOKEN_A},
    )
    adapter = _adapter(client, resolver)

    result = _run(adapter.execute_action(_authority(_ACCOUNT_A)))

    assert result.outcome is AdapterOutcome.DENIED
    assert client.dispatch_count == 0


def test_missing_token_reference_prevents_dispatch() -> None:
    client = _RecordingClient()
    resolver = _SyntheticResolver(
        (_binding(_ACCOUNT_A, _CONNECTION_A, "token-a", (_CONNECTION_A,)),),
        {},
    )
    adapter = _adapter(client, resolver)

    result = _run(adapter.execute_action(_authority(_ACCOUNT_A)))

    assert result.outcome is AdapterOutcome.DENIED
    assert result.code == "runtime_token_unavailable"
    assert client.dispatch_count == 0


def test_unknown_account_cannot_execute() -> None:
    client = _RecordingClient()
    adapter = _adapter(client, _resolver())

    result = _run(adapter.execute_action(_authority(_ACCOUNT_UNKNOWN)))

    assert result.outcome is AdapterOutcome.DENIED
    assert result.code == "binding_not_found"
    assert client.dispatch_count == 0


def test_missing_permission_profile_prevents_dispatch() -> None:
    client = _RecordingClient()
    adapter = _adapter(client, _resolver())

    result = _run(
        adapter.execute_action(
            _authority(_ACCOUNT_A, profile_provider=lambda: None)
        )
    )

    assert result.outcome is AdapterOutcome.DENIED
    assert result.code == "missing_profile"
    assert client.dispatch_count == 0


def test_denied_connector_permission_prevents_dispatch() -> None:
    client = _RecordingClient()
    adapter = _adapter(client, _resolver())

    result = _run(
        adapter.execute_action(
            _authority(
                _ACCOUNT_A,
                profile=_profile(_ACCOUNT_A, connector_allowed=False),
            )
        )
    )

    assert result.outcome is AdapterOutcome.DENIED
    assert result.code == "connector_denied"
    assert client.dispatch_count == 0


def test_denied_network_permission_prevents_dispatch() -> None:
    client = _RecordingClient()
    adapter = _adapter(client, _resolver())

    result = _run(
        adapter.execute_action(
            _authority(
                _ACCOUNT_A,
                profile=_profile(_ACCOUNT_A, network_allowed=False),
            )
        )
    )

    assert result.outcome is AdapterOutcome.DENIED
    assert result.code == "network_denied"
    assert client.dispatch_count == 0


def test_subject_mismatch_prevents_dispatch() -> None:
    client = _RecordingClient()
    adapter = _adapter(client, _resolver())

    authority = ExecutionAuthority(
        guardian_account_id=_ACCOUNT_A,
        provider=_PROVIDER,
        action_id=_SYNTHETIC_ACTION_ID,
        actor_id=_ACCOUNT_A,
        subject_id="someone-else",
        task_id="task-1",
        permission_profile_provider=lambda: _profile(_ACCOUNT_A),
        arguments={},
        requested_connection_uuid=None,
    )

    result = _run(adapter.execute_action(authority))

    assert result.outcome is AdapterOutcome.DENIED
    assert result.code == "subject_mismatch"
    assert client.dispatch_count == 0


def test_authority_is_revalidated_immediately_before_dispatch() -> None:
    client = _RecordingClient()
    adapter = _adapter(client, _resolver())

    calls = {"count": 0}

    def _profile_provider():
        calls["count"] += 1
        # Valid for the entry gate, gone by the pre-dispatch revalidation.
        return _profile(_ACCOUNT_A) if calls["count"] == 1 else None

    result = _run(
        adapter.execute_action(
            _authority(_ACCOUNT_A, profile_provider=_profile_provider)
        )
    )

    assert calls["count"] == 2
    assert result.outcome is AdapterOutcome.DENIED
    assert result.code == "missing_profile"
    assert client.dispatch_count == 0


def test_revocation_between_invocations_stops_the_next_dispatch() -> None:
    client = _RecordingClient()
    adapter = _adapter(client, _resolver())

    allowed = {"value": True}

    def _profile_provider():
        return _profile(_ACCOUNT_A) if allowed["value"] else None

    first = _run(
        adapter.execute_action(
            _authority(_ACCOUNT_A, profile_provider=_profile_provider)
        )
    )
    assert first.outcome is AdapterOutcome.SUCCESS
    assert client.dispatch_count == 1

    allowed["value"] = False
    second = _run(
        adapter.execute_action(
            _authority(_ACCOUNT_A, profile_provider=_profile_provider)
        )
    )

    assert second.outcome is AdapterOutcome.DENIED
    assert client.dispatch_count == 1


def test_empty_grant_is_rejected() -> None:
    client = _RecordingClient()
    resolver = _SyntheticResolver(
        (_binding(_ACCOUNT_A, _CONNECTION_A, "token-a", ()),),
        {"token-a": _TOKEN_A},
    )
    adapter = _adapter(client, resolver)

    result = _run(adapter.execute_action(_authority(_ACCOUNT_A)))

    assert result.outcome is AdapterOutcome.DENIED
    assert result.code == "connection_grant_empty"
    assert client.dispatch_count == 0


def test_permissive_empty_grant_is_not_treated_as_unrestricted() -> None:
    binding = _binding(_ACCOUNT_A, _CONNECTION_A, "token-a", ())
    assert binding.has_scoped_grant() is False
    assert binding.grants_connection(_CONNECTION_A) is False


def test_binding_connection_outside_its_own_grant_is_refused() -> None:
    client = _RecordingClient()
    resolver = _SyntheticResolver(
        (_binding(_ACCOUNT_A, _CONNECTION_A, "token-a", (_CONNECTION_B,)),),
        {"token-a": _TOKEN_A},
    )
    adapter = _adapter(client, resolver)

    result = _run(adapter.execute_action(_authority(_ACCOUNT_A)))

    assert result.outcome is AdapterOutcome.DENIED
    assert result.code == "connection_grant_inconsistent"
    assert client.dispatch_count == 0


def test_no_binding_resolver_fails_closed() -> None:
    client = _RecordingClient()
    adapter = _adapter(client, None)

    result = _run(adapter.execute_action(_authority(_ACCOUNT_A)))

    assert result.outcome is AdapterOutcome.DENIED
    assert result.code == "binding_not_found"
    assert client.dispatch_count == 0


def test_no_deployment_credential_is_used_as_a_fallback(monkeypatch) -> None:
    monkeypatch.setenv("OOMOL_CONNECT_RUNTIME_TOKEN", "deployment-guard-value")
    monkeypatch.setenv("OOMOL_CONNECT_ADMIN_TOKEN", "operator-admin-value")

    client = _RecordingClient()
    resolver = _SyntheticResolver(
        (_binding(_ACCOUNT_A, _CONNECTION_A, "token-a", (_CONNECTION_A,)),),
        {},
    )
    adapter = _adapter(client, resolver)

    result = _run(adapter.execute_action(_authority(_ACCOUNT_A)))

    # A missing scoped token is a denial. The deployment credentials in the
    # environment are never a fallback.
    assert result.outcome is AdapterOutcome.DENIED
    assert result.code == "runtime_token_unavailable"
    assert client.dispatch_count == 0


def test_arguments_containing_credential_material_are_refused() -> None:
    client = _RecordingClient()
    adapter = _adapter(client, _resolver())

    result = _run(
        adapter.execute_action(
            _authority(_ACCOUNT_A, arguments={"note": _TOKEN_A})
        )
    )

    assert result.outcome is AdapterOutcome.DENIED
    assert result.code == "credential_material_in_arguments"
    assert client.dispatch_count == 0


# --- bounded outcomes and sanitization ---------------------------------------


def test_gateway_grant_denial_is_distinct_from_guardian_denial() -> None:
    client = _RecordingClient(GatewayResponse(status_code=403, content=b"{}"))
    adapter = _adapter(client, _resolver())

    result = _run(adapter.execute_action(_authority(_ACCOUNT_A)))

    assert result.outcome is AdapterOutcome.DENIED
    assert result.code == "gateway_grant_denied"
    assert result.dispatched is True


def test_provider_execution_failure_is_distinct_from_gateway_denial() -> None:
    client = _RecordingClient(GatewayResponse(status_code=400, content=b"{}"))
    adapter = _adapter(client, _resolver())

    result = _run(adapter.execute_action(_authority(_ACCOUNT_A)))

    assert result.outcome is AdapterOutcome.FAILED
    assert result.code == "provider_rejected"


def test_gateway_unavailability_is_distinct_from_provider_failure() -> None:
    client = _RecordingClient(GatewayResponse(status_code=503, content=b"{}"))
    adapter = _adapter(client, _resolver())

    result = _run(adapter.execute_action(_authority(_ACCOUNT_A)))

    assert result.outcome is AdapterOutcome.UNAVAILABLE
    assert result.code == "gateway_unavailable"


def test_provider_error_text_is_sanitized_in_the_result() -> None:
    secret = "sk_live_provider_secret"
    body = json.dumps({"error": f"invalid credential: {secret}"}).encode("utf-8")
    client = _RecordingClient(GatewayResponse(status_code=400, content=body))
    adapter = _adapter(client, _resolver())

    result = _run(adapter.execute_action(_authority(_ACCOUNT_A)))

    assert result.outcome is AdapterOutcome.FAILED
    serialized = json.dumps(
        {"code": result.code, "detail": result.detail, "payload": result.payload},
        default=str,
    )
    assert secret not in serialized


def test_credential_material_never_appears_in_the_result() -> None:
    client = _RecordingClient(
        GatewayResponse(status_code=200, content=b'{"records":[{"token":"leak-me"}]}')
    )
    adapter = _adapter(client, _resolver())

    result = _run(adapter.execute_action(_authority(_ACCOUNT_A)))

    assert result.outcome is AdapterOutcome.SUCCESS
    serialized = json.dumps(
        {"code": result.code, "detail": result.detail, "payload": result.payload},
        default=str,
    )
    assert _TOKEN_A not in serialized
    assert "leak-me" not in serialized


def test_payload_is_bounded_before_it_reaches_a_caller() -> None:
    oversized = json.dumps({"records": ["x" * 256 for _ in range(200)]}).encode("utf-8")
    client = _RecordingClient(GatewayResponse(status_code=200, content=oversized))
    adapter = _adapter(client, _resolver(), max_payload_bytes=1024)

    result = _run(adapter.execute_action(_authority(_ACCOUNT_A)))

    assert result.outcome is AdapterOutcome.SUCCESS
    assert result.truncated is True
    assert len(json.dumps(result.payload, default=str).encode("utf-8")) <= 1024


def test_timeout_reports_an_unknown_outcome_and_is_not_replayed() -> None:
    client = _RecordingClient(raise_error=GatewayTimeoutError("gateway_timeout"))
    adapter = _adapter(client, _resolver())

    result = _run(adapter.execute_action(_authority(_ACCOUNT_A)))

    assert result.outcome is AdapterOutcome.TIMED_OUT
    assert result.code == "gateway_timeout"
    assert "unknown" in str(result.detail)
    assert client.dispatch_count == 1


# --- discovery ---------------------------------------------------------------


def test_discovery_returns_bounded_metadata_without_dispatch() -> None:
    client = _RecordingClient()
    adapter = _adapter(client, _resolver())

    actions = _run(adapter.discover_actions(_authority(_ACCOUNT_A, provider="hackernews")))

    assert client.dispatch_count == 0
    assert actions
    for entry in actions:
        assert set(entry) == {
            "action_id",
            "provider",
            "description",
            "requires_connection",
            "read_only",
        }
        assert entry["read_only"] is True


def test_discovery_requires_authority() -> None:
    client = _RecordingClient()
    adapter = _adapter(client, _resolver())

    actions = _run(
        adapter.discover_actions(
            _authority(_ACCOUNT_A, provider="hackernews", profile_provider=lambda: None)
        )
    )

    assert actions == []
    assert client.dispatch_count == 0
