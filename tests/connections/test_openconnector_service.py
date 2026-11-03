"""Wire-contract proof for the OpenConnector custodian transport.

These tests pin the pinned v1.9.4 request shape and the transport's failure
mapping. They use an instrumented in-process client: no custodian is
contacted, so nothing here is evidence of live upstream execution.

The contract being pinned:

* ``POST /v1/actions/{actionId}`` is the runtime action endpoint.
* Action arguments travel under an ``input`` wrapper.
* The connection is selected explicitly through ``x-oo-connector-app-id``.
* The body never carries ``connectionId`` or ``connectionName``.
* The bearer is the account-scoped persistent runtime token, and no
  deployment credential is ever read or presented.
* Failures carry a bounded code and never upstream response text.
* Nothing is retried automatically.
"""

from __future__ import annotations

import asyncio
import json

import pytest

from guardian.connections.openconnector.service import (
    CONNECTION_SELECTOR_HEADER,
    MAX_RESPONSE_BYTES,
    GatewayConfigurationError,
    GatewayDeniedError,
    GatewayPayloadTooLargeError,
    GatewayRequest,
    GatewayRequestRejectedError,
    GatewayResponse,
    GatewayTimeoutError,
    GatewayUnavailableError,
    OpenConnectorService,
    build_action_request,
)

_BASE_URL = "http://openconnector.internal:3000"
_SCOPED_TOKEN = "oct_scope_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
_CONNECTION_UUID = "11111111-2222-3333-4444-555555555555"


class _RecordingClient:
    """Instrumented client that records every dispatch."""

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


def _service(client: _RecordingClient, **kwargs) -> OpenConnectorService:
    return OpenConnectorService(_BASE_URL, client, **kwargs)


def _run(coro):
    return asyncio.run(coro)


def test_action_request_targets_the_runtime_action_endpoint() -> None:
    request = build_action_request(
        base_url=_BASE_URL,
        action_id="hackernews.get_top_stories",
        arguments={"limit": 5},
        connection_id=_CONNECTION_UUID,
        runtime_token=_SCOPED_TOKEN,
    )

    assert request.method == "POST"
    assert request.url == (
        f"{_BASE_URL}/v1/actions/hackernews.get_top_stories"
    )


def test_action_arguments_travel_under_the_input_envelope() -> None:
    request = build_action_request(
        base_url=_BASE_URL,
        action_id="hackernews.get_top_stories",
        arguments={"limit": 5},
        connection_id=_CONNECTION_UUID,
        runtime_token=_SCOPED_TOKEN,
    )

    payload = json.loads(request.body.decode("utf-8"))
    assert payload == {"input": {"limit": 5}}
    # The envelope wrapper is required: a flat body is rejected upstream.
    assert "limit" not in payload


def test_connection_is_selected_explicitly_by_the_measured_header() -> None:
    request = build_action_request(
        base_url=_BASE_URL,
        action_id="hackernews.get_top_stories",
        arguments={},
        connection_id=_CONNECTION_UUID,
        runtime_token=_SCOPED_TOKEN,
    )

    assert request.headers[CONNECTION_SELECTOR_HEADER] == _CONNECTION_UUID
    assert request.headers["authorization"] == f"Bearer {_SCOPED_TOKEN}"


def test_body_never_carries_a_connection_identifier() -> None:
    request = build_action_request(
        base_url=_BASE_URL,
        action_id="hackernews.get_top_stories",
        arguments={},
        connection_id=_CONNECTION_UUID,
        runtime_token=_SCOPED_TOKEN,
    )

    payload = json.loads(request.body.decode("utf-8"))
    # The body's connectionId field is not wired for selection upstream and
    # silently denies; connectionName would select by alias instead.
    assert "connectionId" not in payload
    assert "connectionName" not in payload
    assert "connectionId" not in request.body.decode("utf-8")


def test_request_refuses_to_build_without_explicit_selection() -> None:
    with pytest.raises(ValueError):
        build_action_request(
            base_url=_BASE_URL,
            action_id="hackernews.get_top_stories",
            arguments={},
            connection_id="",
            runtime_token=_SCOPED_TOKEN,
        )


def test_transport_never_reads_a_deployment_credential(monkeypatch) -> None:
    monkeypatch.setenv("OOMOL_CONNECT_RUNTIME_TOKEN", "deployment-guard-value")
    monkeypatch.setenv("OOMOL_CONNECT_ADMIN_TOKEN", "operator-admin-value")

    client = _RecordingClient()
    service = _service(client)

    result = _run(
        service.execute_action(
            action_id="hackernews.get_top_stories",
            arguments={},
            connection_id=_CONNECTION_UUID,
            runtime_token=_SCOPED_TOKEN,
        )
    )

    assert result == {"ok": True}
    sent = client.requests[0]
    serialized = sent.body.decode("utf-8") + repr(dict(sent.headers))
    assert "deployment-guard-value" not in serialized
    assert "operator-admin-value" not in serialized
    assert sent.headers["authorization"] == f"Bearer {_SCOPED_TOKEN}"


def test_success_returns_the_parsed_payload() -> None:
    client = _RecordingClient(
        GatewayResponse(status_code=200, content=b'{"stories":[{"id":1}]}')
    )
    service = _service(client)

    payload = _run(
        service.execute_action(
            action_id="hackernews.get_top_stories",
            arguments={},
            connection_id=_CONNECTION_UUID,
            runtime_token=_SCOPED_TOKEN,
        )
    )

    assert payload == {"stories": [{"id": 1}]}
    assert client.dispatch_count == 1


@pytest.mark.parametrize(
    ("status", "expected_error", "expected_code"),
    [
        (401, GatewayDeniedError, "scoped_token_rejected"),
        (403, GatewayDeniedError, "gateway_grant_denied"),
        (404, GatewayConfigurationError, "connection_not_configured"),
        (408, GatewayTimeoutError, "gateway_timeout"),
        (504, GatewayTimeoutError, "gateway_timeout"),
        (429, GatewayUnavailableError, "gateway_rate_limited"),
        (400, GatewayRequestRejectedError, "provider_rejected"),
        (422, GatewayRequestRejectedError, "provider_rejected"),
        (500, GatewayUnavailableError, "gateway_unavailable"),
        (503, GatewayUnavailableError, "gateway_unavailable"),
    ],
)
def test_status_codes_map_to_bounded_failures(
    status: int, expected_error: type[Exception], expected_code: str
) -> None:
    client = _RecordingClient(GatewayResponse(status_code=status, content=b"{}"))
    service = _service(client)

    with pytest.raises(expected_error) as excinfo:
        _run(
            service.execute_action(
                action_id="hackernews.get_top_stories",
                arguments={},
                connection_id=_CONNECTION_UUID,
                runtime_token=_SCOPED_TOKEN,
            )
        )

    assert getattr(excinfo.value, "code") == expected_code
    assert client.dispatch_count == 1


def test_provider_error_text_never_escapes_the_transport() -> None:
    secret = "sk_live_upstream_secret_value"
    body = json.dumps({"error": f"invalid api key: {secret}"}).encode("utf-8")
    client = _RecordingClient(GatewayResponse(status_code=400, content=body))
    service = _service(client)

    with pytest.raises(GatewayRequestRejectedError) as excinfo:
        _run(
            service.execute_action(
                action_id="hackernews.get_top_stories",
                arguments={},
                connection_id=_CONNECTION_UUID,
                runtime_token=_SCOPED_TOKEN,
            )
        )

    error = excinfo.value
    assert secret not in str(error)
    assert secret not in repr(error)
    assert secret not in repr(error.__dict__)
    assert error.code == "provider_rejected"


def test_non_json_body_is_rejected_without_surfacing_text() -> None:
    client = _RecordingClient(
        GatewayResponse(status_code=200, content=b"<html>not json</html>")
    )
    service = _service(client)

    with pytest.raises(GatewayRequestRejectedError) as excinfo:
        _run(
            service.execute_action(
                action_id="hackernews.get_top_stories",
                arguments={},
                connection_id=_CONNECTION_UUID,
                runtime_token=_SCOPED_TOKEN,
            )
        )

    assert excinfo.value.code == "response_not_json"


def test_oversized_response_is_refused() -> None:
    oversized = b"x" * (MAX_RESPONSE_BYTES + 1)
    client = _RecordingClient(GatewayResponse(status_code=200, content=oversized))
    service = _service(client)

    with pytest.raises(GatewayPayloadTooLargeError) as excinfo:
        _run(
            service.execute_action(
                action_id="hackernews.get_top_stories",
                arguments={},
                connection_id=_CONNECTION_UUID,
                runtime_token=_SCOPED_TOKEN,
            )
        )

    assert excinfo.value.code == "response_too_large"
    assert MAX_RESPONSE_BYTES <= 262_144


def test_a_timeout_is_not_replayed() -> None:
    class _TimeoutClient:
        def __init__(self) -> None:
            self.dispatch_count = 0

        async def send(self, request: GatewayRequest) -> GatewayResponse:
            self.dispatch_count += 1
            raise GatewayTimeoutError("gateway_timeout")

    client = _TimeoutClient()
    service = _service(client)  # type: ignore[arg-type]

    with pytest.raises(GatewayTimeoutError):
        _run(
            service.execute_action(
                action_id="hackernews.get_top_stories",
                arguments={},
                connection_id=_CONNECTION_UUID,
                runtime_token=_SCOPED_TOKEN,
            )
        )

    # An unknown outcome is never replayed automatically: one crossing, one
    # attempt. The provider may still have completed the work.
    assert client.dispatch_count == 1


def test_timeouts_are_bounded_and_passed_to_the_client() -> None:
    client = _RecordingClient()
    service = _service(
        client, connect_timeout_seconds=3.0, read_timeout_seconds=11.0
    )

    _run(
        service.execute_action(
            action_id="hackernews.get_top_stories",
            arguments={},
            connection_id=_CONNECTION_UUID,
            runtime_token=_SCOPED_TOKEN,
        )
    )

    request = client.requests[0]
    assert request.connect_timeout_seconds == 3.0
    assert request.read_timeout_seconds == 11.0
    assert request.connect_timeout_seconds > 0
    assert request.read_timeout_seconds > 0


def test_no_auth_omission_sends_no_selector_but_keeps_the_scoped_bearer() -> None:
    request = build_action_request(
        base_url=_BASE_URL,
        action_id="hackernews.get_top_stories",
        arguments={},
        connection_id=None,
        runtime_token=_SCOPED_TOKEN,
        omit_connection_selector=True,
    )

    assert CONNECTION_SELECTOR_HEADER not in request.headers
    assert request.headers["authorization"] == f"Bearer {_SCOPED_TOKEN}"
    assert json.loads(request.body.decode("utf-8")) == {"input": {}}


def test_no_auth_omission_refuses_a_named_connection() -> None:
    with pytest.raises(ValueError):
        build_action_request(
            base_url=_BASE_URL,
            action_id="hackernews.get_top_stories",
            arguments={},
            connection_id=_CONNECTION_UUID,
            runtime_token=_SCOPED_TOKEN,
            omit_connection_selector=True,
        )


def test_explicit_selection_refuses_an_undeclared_omission() -> None:
    with pytest.raises(ValueError):
        build_action_request(
            base_url=_BASE_URL,
            action_id="hackernews.get_top_stories",
            arguments={},
            connection_id=None,
            runtime_token=_SCOPED_TOKEN,
        )
