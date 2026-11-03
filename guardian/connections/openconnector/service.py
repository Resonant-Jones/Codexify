"""OpenConnector custodian transport — the pinned v1.9.4 wire contract.

This module owns the HTTP crossing to the custodian (the OpenConnector
gateway). The adapter owns the authority decision that precedes it.

Wire contract, verified against the pinned v1.9.4 digest:

* ``POST /v1/actions/{actionId}`` is the runtime action endpoint.
* Action arguments travel under an ``input`` wrapper, not at the top level.
* The connection is selected explicitly by the custodian connection identity in
  the ``x-oo-connector-app-id`` header. The request body's ``connectionId``
  field is **not** wired for selection and silently denies; the body must
  never carry it.
* The bearer is an account-scoped persistent runtime token whose grant names
  the custodian connections that account may use.

One measured exception governs the selector. A **no-auth** provider's
connection is virtual: it holds no credential, it has no stored UUID, and
upstream refuses an explicit selector aimed at it with ``connection_not_allowed``.
For a reviewed no-auth action the crossing therefore **omits** the selector,
which is the only form that reaches the provider. Two properties keep this
bounded, and the transport enforces both:

* the omission is not a fallback to some other connection. Upstream resolves
  the target from the action's own provider, so an omitted selector for a
  no-auth action reaches that provider's virtual no-auth connection — never a
  credential-bearing connection belonging to another provider, and never a
  shared unscoped default;
* the omission changes nothing else about the request. The bearer is still the
  scoped account token, the deployment action allowlist still applies, the
  token's ``allowedActions`` grant still applies, and the response bound is
  unchanged.

The transport does not decide when to omit. It refuses a request that omits
the selector without saying so explicitly, and it refuses a request that both
names a connection and claims to omit it. The decision belongs to the
reviewed allowlist, and it reaches the transport as an explicit flag.

This module never reads, accepts, or presents a deployment credential. The
undistributed runtime guard and the operator admin token are deployment
infrastructure; they are not execution credentials, and no code path here
retrieves them. The only bearer this transport can send is the scoped
persistent token handed to it by the adapter, and that token never leaves the
transport except inside the ``Authorization`` header.

Failures are reported through bounded exception types that carry **no**
upstream body text. The custodian may relay provider error text verbatim; this
transport drops it rather than forwarding it, and the adapter maps the
failure to a bounded outcome.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping, Protocol, runtime_checkable
from urllib.parse import quote

from guardian.command_bus.contracts import MAX_PAYLOAD_BYTES

#: The custodian runtime action endpoint.
ACTION_PATH_TEMPLATE = "/v1/actions/{action_id}"

#: The measured primary connection selector: the custodian connection UUID.
CONNECTION_SELECTOR_HEADER = "x-oo-connector-app-id"

#: Bounded timeouts. A read timeout leaves the execution outcome unknown, so
#: it is deliberately finite and never retried.
DEFAULT_CONNECT_TIMEOUT_SECONDS = 5.0
DEFAULT_READ_TIMEOUT_SECONDS = 20.0

#: The adapter's own response bound. It may not exceed the Command Bus
#: ``MAX_PAYLOAD_BYTES``, and it is applied before any caller sees a payload.
MAX_RESPONSE_BYTES = MAX_PAYLOAD_BYTES


class GatewayError(Exception):
    """Base class for custodian failures.

    The message is a bounded, Codexify-owned code. It never contains upstream
    response text, provider text, or credential material.
    """

    def __init__(self, code: str, status_code: int | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.status_code = status_code


class GatewayDeniedError(GatewayError):
    """The custodian refused the request: a grant or credential rejection."""


class GatewayConfigurationError(GatewayError):
    """The custodian has no usable configuration for this request."""


class GatewayTimeoutError(GatewayError):
    """The custodian did not answer in time.

    The execution outcome is **unknown**: the provider request may still have
    completed. This must never be reported as "did not happen", and it is
    never retried automatically.
    """


class GatewayUnavailableError(GatewayError):
    """The custodian is unreachable or returned a server-side failure."""


class GatewayRequestRejectedError(GatewayError):
    """The custodian or the provider rejected the request payload.

    Measured behaviour: a provider credential failure arrives here as a
    rejection carrying raw provider text. That text is discarded by the
    transport.
    """


class GatewayPayloadTooLargeError(GatewayError):
    """The custodian response exceeded the adapter's response bound."""


@dataclass(frozen=True)
class GatewayRequest:
    """A fully built custodian request."""

    method: str
    url: str
    headers: Mapping[str, str]
    body: bytes
    connect_timeout_seconds: float
    read_timeout_seconds: float


@dataclass(frozen=True)
class GatewayResponse:
    """A custodian response, already size-bounded by the client."""

    status_code: int
    content: bytes


@runtime_checkable
class GatewayHttpClient(Protocol):
    """The minimal HTTP seam the transport needs.

    Implementations raise :class:`GatewayTimeoutError` on a timeout and
    :class:`GatewayUnavailableError` on a transport failure, so the transport
    itself stays free of any HTTP-library dependency.
    """

    async def send(self, request: GatewayRequest) -> GatewayResponse:
        ...


class HttpxGatewayClient:
    """Default client, backed by ``httpx``.

    ``httpx`` is imported lazily so the adapter core stays importable — and
    testable — without the HTTP stack installed. The import error, if any, is
    raised when a client is actually constructed, not at import time.
    """

    def __init__(self, client: Any | None = None) -> None:
        if client is not None:
            self._client = client
            return
        try:
            import httpx
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise RuntimeError(
                "httpx is required for the default OpenConnector transport"
            ) from exc
        self._client = httpx.AsyncClient(follow_redirects=False)

    async def send(self, request: GatewayRequest) -> GatewayResponse:
        import httpx

        timeout = httpx.Timeout(
            request.read_timeout_seconds,
            connect=request.connect_timeout_seconds,
        )
        try:
            response = await self._client.request(
                request.method,
                request.url,
                headers=dict(request.headers),
                content=request.body,
                timeout=timeout,
            )
        except httpx.TimeoutException as exc:
            raise GatewayTimeoutError("gateway_timeout") from exc
        except httpx.HTTPError as exc:
            raise GatewayUnavailableError("gateway_unreachable") from exc
        return GatewayResponse(
            status_code=int(response.status_code),
            content=bytes(response.content or b""),
        )


def build_action_request(
    *,
    base_url: str,
    action_id: str,
    arguments: Mapping[str, Any],
    connection_id: str | None,
    runtime_token: str,
    omit_connection_selector: bool = False,
    connect_timeout_seconds: float = DEFAULT_CONNECT_TIMEOUT_SECONDS,
    read_timeout_seconds: float = DEFAULT_READ_TIMEOUT_SECONDS,
) -> GatewayRequest:
    """Build the custodian action request for the pinned wire contract.

    The body carries the ``input`` envelope and nothing else — in particular
    never a ``connectionId`` or ``connectionName`` field.

    The connection selector is omitted **only** when ``omit_connection_selector``
    is set, which the adapter does only for a reviewed no-auth action. The two
    states are mutually exclusive and each is checked here, so a request can
    never silently name a connection while claiming to omit it, nor omit one
    without saying so.
    """
    action = str(action_id or "").strip()
    if not action:
        raise ValueError("action_id is required")
    connection = str(connection_id or "").strip()
    token = str(runtime_token or "").strip()
    if not token:
        raise ValueError("runtime_token is required")
    if omit_connection_selector:
        if connection:
            raise ValueError(
                "connection_id must be omitted when the connection selector is omitted"
            )
    elif not connection:
        raise ValueError("connection_id is required for explicit selection")

    payload: dict[str, Any] = {"input": dict(arguments or {})}
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    url = "{base}/v1/actions/{action}".format(
        base=str(base_url or "").rstrip("/"),
        action=quote(action, safe="."),
    )
    headers = {
        "authorization": f"Bearer {token}",
        "content-type": "application/json",
        "accept": "application/json",
    }
    if connection:
        headers[CONNECTION_SELECTOR_HEADER] = connection
    return GatewayRequest(
        method="POST",
        url=url,
        headers=headers,
        body=body,
        connect_timeout_seconds=float(connect_timeout_seconds),
        read_timeout_seconds=float(read_timeout_seconds),
    )


class OpenConnectorService:
    """HTTP transport for one custodian instance.

    The service is deliberately narrow: it sends one reviewed action with a
    scoped bearer, names the custodian-side connection unless the reviewed
    action is a no-auth action, and it returns either a bounded payload or a
    bounded failure. It performs no retry.
    """

    def __init__(
        self,
        base_url: str,
        client: GatewayHttpClient,
        *,
        connect_timeout_seconds: float = DEFAULT_CONNECT_TIMEOUT_SECONDS,
        read_timeout_seconds: float = DEFAULT_READ_TIMEOUT_SECONDS,
        max_response_bytes: int = MAX_RESPONSE_BYTES,
    ) -> None:
        self._base_url = str(base_url or "").strip()
        self._client = client
        self._connect_timeout_seconds = float(connect_timeout_seconds)
        self._read_timeout_seconds = float(read_timeout_seconds)
        self._max_response_bytes = int(max_response_bytes)

    @property
    def base_url(self) -> str:
        return self._base_url

    async def execute_action(
        self,
        *,
        action_id: str,
        arguments: Mapping[str, Any],
        connection_id: str | None,
        runtime_token: str,
        omit_connection_selector: bool = False,
    ) -> Any:
        """Execute one action and return the parsed custodian payload.

        Raises a :class:`GatewayError` subclass on any failure. The raised
        error carries a bounded code only.
        """
        request = build_action_request(
            base_url=self._base_url,
            action_id=action_id,
            arguments=arguments,
            connection_id=connection_id,
            runtime_token=runtime_token,
            omit_connection_selector=omit_connection_selector,
            connect_timeout_seconds=self._connect_timeout_seconds,
            read_timeout_seconds=self._read_timeout_seconds,
        )
        response = await self._client.send(request)
        if len(response.content) > self._max_response_bytes:
            raise GatewayPayloadTooLargeError("response_too_large")
        return self._interpret(response)

    def _interpret(self, response: GatewayResponse) -> Any:
        status = int(response.status_code)
        if 200 <= status < 300:
            return _parse_json(response.content)
        if status == 401:
            raise GatewayDeniedError("scoped_token_rejected", status)
        if status == 403:
            raise GatewayDeniedError("gateway_grant_denied", status)
        if status == 404:
            raise GatewayConfigurationError("connection_not_configured", status)
        if status in (408, 504):
            raise GatewayTimeoutError("gateway_timeout", status)
        if status == 429:
            raise GatewayUnavailableError("gateway_rate_limited", status)
        if status in (400, 422):
            raise GatewayRequestRejectedError("provider_rejected", status)
        if status >= 500:
            raise GatewayUnavailableError("gateway_unavailable", status)
        raise GatewayRequestRejectedError("request_rejected", status)


def _parse_json(content: bytes) -> Any:
    if not content:
        return None
    try:
        return json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        # A malformed body is not a usable payload. It is reported as a
        # rejection rather than surfaced as raw text.
        raise GatewayRequestRejectedError("response_not_json") from None


__all__ = [
    "ACTION_PATH_TEMPLATE",
    "CONNECTION_SELECTOR_HEADER",
    "DEFAULT_CONNECT_TIMEOUT_SECONDS",
    "DEFAULT_READ_TIMEOUT_SECONDS",
    "MAX_RESPONSE_BYTES",
    "GatewayConfigurationError",
    "GatewayDeniedError",
    "GatewayError",
    "GatewayHttpClient",
    "GatewayPayloadTooLargeError",
    "GatewayRequest",
    "GatewayRequestRejectedError",
    "GatewayResponse",
    "GatewayTimeoutError",
    "GatewayUnavailableError",
    "HttpxGatewayClient",
    "OpenConnectorService",
    "build_action_request",
]
