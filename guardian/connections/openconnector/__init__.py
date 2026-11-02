"""OpenConnector adapter core — internal, provider-agnostic, fail-closed.

OpenConnector is a **subordinate external credential custodian** and execution
substrate. It holds provider credential material and it executes provider
actions. It holds **no** Codexify account authority and it grants none.
Guardian remains the sole account-authorization authority.

Authority, and the decisions that make it real:

* :mod:`guardian.connections.openconnector.bindings` owns the typed
  Guardian-owned account-to-connection binding and its resolution interface.
  This slice ships no production registry and no credential database.
* :mod:`guardian.connections.openconnector.policy` owns the reviewed,
  server-controlled read-only action allowlist.
* :mod:`guardian.connections.openconnector.service` owns the HTTP transport
  and the pinned v1.9.4 wire contract.
* :mod:`guardian.connections.openconnector.adapter` owns the bounded
  execution crossing: authorization, explicit connection selection, and the
  bounded outcome vocabulary.
* :mod:`guardian.connections.openconnector.authority` owns the Guardian-derived
  execution authority for one invocation, including the live permission-profile
  read that backs the adapter's pre-dispatch revalidation.
* :mod:`guardian.connections.openconnector.router` owns the single internal-only
  read operation that exposes the crossing inside Guardian.

This package is internal. It registers **no** catalog entry, and it is not
promoted to any supported surface. Its route is mounted under an internal-only
posture, so its paths never appear in the public OpenAPI document. The durable
binding schema, the binding lifecycle, and the credential lifecycle belong to
Gate C; live custodian qualification and the catalog entry remain Gate B
obligations.

See the ADR-071 and ADR-094 amendments accepted 2026-11-02.
"""

from guardian.connections.openconnector.adapter import (
    COMMAND_CLASS_CONNECTOR,
    COMMAND_ID_PREFIX,
    AdapterOutcome,
    AdapterResult,
    ExecutionAuthority,
    OpenConnectorAdapter,
)
from guardian.connections.openconnector.authority import (
    GuardianAccountScope,
    build_execution_authority,
)
from guardian.connections.openconnector.bindings import (
    AccountBinding,
    BindingResolver,
    BindingState,
    NoBindingResolver,
)
from guardian.connections.openconnector.policy import (
    APPROVED_ACTIONS,
    REVIEWED_READ_ONLY_ACTIONS,
    ApprovedAction,
    approved_actions_for_provider,
    get_approved_action,
    is_approved_action,
)
from guardian.connections.openconnector.service import (
    ACTION_PATH_TEMPLATE,
    CONNECTION_SELECTOR_HEADER,
    MAX_RESPONSE_BYTES,
    GatewayConfigurationError,
    GatewayDeniedError,
    GatewayError,
    GatewayHttpClient,
    GatewayPayloadTooLargeError,
    GatewayRequest,
    GatewayRequestRejectedError,
    GatewayResponse,
    GatewayTimeoutError,
    GatewayUnavailableError,
    HttpxGatewayClient,
    OpenConnectorService,
    build_action_request,
)

__all__ = [
    "ACTION_PATH_TEMPLATE",
    "APPROVED_ACTIONS",
    "COMMAND_CLASS_CONNECTOR",
    "COMMAND_ID_PREFIX",
    "CONNECTION_SELECTOR_HEADER",
    "MAX_RESPONSE_BYTES",
    "REVIEWED_READ_ONLY_ACTIONS",
    "AccountBinding",
    "AdapterOutcome",
    "AdapterResult",
    "ApprovedAction",
    "BindingResolver",
    "BindingState",
    "ExecutionAuthority",
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
    "GuardianAccountScope",
    "HttpxGatewayClient",
    "NoBindingResolver",
    "OpenConnectorAdapter",
    "OpenConnectorService",
    "approved_actions_for_provider",
    "build_action_request",
    "build_execution_authority",
    "get_approved_action",
    "is_approved_action",
]
