"""OpenConnector adapter — the bounded execution crossing.

Guardian authorizes every invocation. The custodian executes. This module owns
the crossing between them, and it owns the refusal paths.

Order of operations, and the reason for it:

1. The action must be on the reviewed read-only allowlist. An unapproved
   action never reaches the network.
2. Guardian authority is evaluated through the existing Command Bus permission
   profile contract, requiring an authenticated subject, a matching
   actor/subject/task context, connector permission, and network permission.
   A missing profile is a denial, never a permission.
3. The Guardian-owned binding is resolved and checked: it must exist, be
   authorized, belong to the invoking account, match the provider, and carry a
   non-empty scoped grant naming the connection.
4. The custodian-side connection is selected **explicitly**, from Guardian
   state. A requested connection may only narrow to what the binding already
   grants; it can never widen, and an omitted request never falls back to a
   default or shared connection.
   The single exception is a reviewed **no-auth** action, whose
   custodian-side connection is virtual and holds no credential: for those
   actions the upstream selector is omitted, and nothing else about the
   request changes. The exception belongs to the reviewed allowlist entry
   alone — no request, argument, binding, or runtime flag can select it.
5. The account-scoped persistent runtime token is resolved. It is used only
   inside the transport.
6. Guardian authority is **revalidated immediately before dispatch**, so a
   revocation between resolution and dispatch stops the call. Every new
   invocation and every retry revalidates; no authorization decision is
   cached across invocations.
7. The custodian is called with the explicit connection selector, or — for a
   reviewed no-auth action only — without one.

The deployment guard and the operator admin token are not execution
credentials and are never reachable from this module: they are not read from
the environment, not accepted as arguments, and not present in any result.

Failures map onto ADR-024's bounded outcomes — success, denied, unavailable,
needs_configuration, timed_out, failed — and the mapping keeps Guardian
denial, custodian grant denial, provider execution failure, and custodian
unavailability distinct. A timeout preserves an **unknown** execution outcome;
it is never reported as "did not happen".

This module is internal. It registers no route, no Command Bus command, and no
catalog entry: the crossing is reached through the package's internal-only
route, and the route obtains its authority from
:mod:`guardian.connections.openconnector.authority`.
"""

from __future__ import annotations

import inspect
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Mapping, Union

from guardian.command_bus.contracts import MAX_PAYLOAD_BYTES
from guardian.command_bus.permission_profiles import (
    PermissionProfile,
    PermissionProfileDecision,
    PermissionProfileRequest,
    evaluate_permission_profile,
)
from guardian.command_bus.redaction_policy import redact_arguments
from guardian.connections.openconnector.bindings import (
    AccountBinding,
    BindingResolver,
    NoBindingResolver,
)
from guardian.connections.openconnector.policy import (
    ApprovedAction,
    ConnectionSelection,
    approved_actions_for_provider,
    get_approved_action,
    resolve_allowlist,
)
from guardian.connections.openconnector.service import (
    GatewayConfigurationError,
    GatewayDeniedError,
    GatewayError,
    GatewayPayloadTooLargeError,
    GatewayRequestRejectedError,
    GatewayTimeoutError,
    GatewayUnavailableError,
    OpenConnectorService,
)

#: A permission profile provider reads Guardian's current authority. It may be
#: synchronous or asynchronous; an asynchronous provider can re-read live
#: Guardian state at each evaluation.
PermissionProfileProvider = Union[
    Callable[[], PermissionProfile | None],
    Callable[[], Awaitable[PermissionProfile | None]],
]

#: The command class this crossing belongs to. The Command Bus classifies the
#: connection execution as a connector call that also uses the network.
COMMAND_CLASS_CONNECTOR = "connector"

#: The command id namespace for custodian actions.
COMMAND_ID_PREFIX = "openconnector"


class AdapterOutcome(str, Enum):
    """ADR-024's bounded outcome vocabulary."""

    SUCCESS = "success"
    DENIED = "denied"
    UNAVAILABLE = "unavailable"
    NEEDS_CONFIGURATION = "needs_configuration"
    TIMED_OUT = "timed_out"
    FAILED = "failed"


@dataclass(frozen=True)
class ExecutionAuthority:
    """Server-derived Guardian authority for exactly one invocation.

    Every field here is server-derived. Nothing in this object may be
    populated from model-generated arguments: the account identity, the
    provider, and the action are Guardian's to state, and the permission
    profile is read from Guardian state at the moment it is needed.

    The permission profile provider may be a plain callable or an awaitable
    one. An awaitable provider lets a caller re-read live Guardian state at
    each evaluation, so the revalidation immediately before the external
    crossing observes a revocation that happened after the binding was
    resolved.
    """

    guardian_account_id: str
    provider: str
    action_id: str
    actor_id: str
    subject_id: str
    task_id: str
    permission_profile_provider: PermissionProfileProvider
    arguments: Mapping[str, Any] = field(default_factory=dict)
    requested_connection_id: str | None = None

    def command_id(self) -> str:
        return f"{COMMAND_ID_PREFIX}::{self.action_id}"


@dataclass(frozen=True)
class AdapterResult:
    """A bounded adapter result.

    ``payload`` carries provider data only on success, after redaction and
    after the response bound has been applied. ``detail`` carries a bounded,
    Codexify-owned string; it never carries upstream response text or
    credential material.
    """

    outcome: AdapterOutcome
    code: str
    detail: str | None = None
    payload: Any | None = None
    truncated: bool = False
    dispatched: bool = False


class OpenConnectorAdapter:
    """Provider-agnostic, fail-closed adapter for one custodian."""

    def __init__(
        self,
        service: OpenConnectorService,
        binding_resolver: BindingResolver | None = None,
        *,
        allowlist: Mapping[str, ApprovedAction] | None = None,
        max_payload_bytes: int = MAX_PAYLOAD_BYTES,
    ) -> None:
        self._service = service
        self._resolver: BindingResolver = binding_resolver or NoBindingResolver()
        self._allowlist = resolve_allowlist(allowlist)
        self._max_payload_bytes = int(max_payload_bytes)

    @property
    def allowlist(self) -> Mapping[str, ApprovedAction]:
        return self._allowlist

    async def discover_actions(
        self, authority: ExecutionAuthority
    ) -> list[dict[str, Any]]:
        """Return bounded action metadata for the authorized provider.

        Discovery is a projection of the reviewed, server-controlled
        allowlist. It performs no custodian call, returns no credential or
        setup state, and never derives its content from the custodian
        catalog.
        """
        decision = await self._evaluate_authority(authority)
        if not decision.allowed:
            return []
        actions = approved_actions_for_provider(authority.provider, self._allowlist)
        return [_action_metadata(action) for action in actions]

    async def execute_action(
        self, authority: ExecutionAuthority
    ) -> AdapterResult:
        """Execute one reviewed action for one authorized account."""
        action = get_approved_action(authority.action_id, self._allowlist)
        if action is None:
            return AdapterResult(
                outcome=AdapterOutcome.DENIED,
                code="action_not_approved",
                detail="action is not on the reviewed read-only allowlist",
            )
        if (
            action.connection_selection is ConnectionSelection.NO_AUTH
            and action.credential_bearing
        ):
            # A reviewed entry may not both declare the no-auth mode and spend a
            # provider credential. Such an entry is contradictory, and a
            # contradiction is refused rather than resolved.
            return AdapterResult(
                outcome=AdapterOutcome.DENIED,
                code="action_contract_inconsistent",
                detail="the reviewed action declares an inconsistent execution mode",
            )

        decision = await self._evaluate_authority(authority)
        if not decision.allowed:
            return AdapterResult(
                outcome=AdapterOutcome.DENIED,
                code=decision.code,
                detail=decision.reason,
            )

        binding = await self._resolver.resolve_binding(
            authority.guardian_account_id, authority.provider
        )
        if binding is None:
            return _denied("binding_not_found", "no Guardian binding for this account")

        binding_refusal = _check_binding(binding, authority)
        if binding_refusal is not None:
            return binding_refusal

        # The reviewed action alone decides how the custodian-side connection is
        # named. A no-auth action has no selectable account-owned connection, so
        # a request that names one is refused instead of being narrowed away.
        if action.connection_selection is ConnectionSelection.NO_AUTH:
            if str(authority.requested_connection_id or "").strip():
                return _denied(
                    "connection_not_selectable",
                    "a no-auth action has no selectable account-owned connection",
                )
            connection_id: str | None = None
            omit_connection_selector = True
        else:
            selected = _select_connection(binding, authority)
            if selected is None:
                return _denied(
                    "connection_not_granted",
                    "the requested connection is not granted to this account",
                )
            connection_id = selected
            omit_connection_selector = False

        arguments = _checked_arguments(authority.arguments)
        if isinstance(arguments, AdapterResult):
            return arguments

        runtime_token = await self._resolver.resolve_runtime_token(binding)
        token = str(runtime_token or "").strip()
        if not token:
            return _denied(
                "runtime_token_unavailable",
                "no account-scoped runtime token is available for this binding",
            )
        if token in json.dumps(arguments, default=str):
            return _denied(
                "credential_material_in_arguments",
                "action arguments must not contain credential material",
            )

        # Revalidation immediately before the external crossing. The profile is
        # read fresh, so a revocation between resolution and dispatch stops the
        # call, and every new invocation revalidates.
        decision = await self._evaluate_authority(authority)
        if not decision.allowed:
            return AdapterResult(
                outcome=AdapterOutcome.DENIED,
                code=decision.code,
                detail=decision.reason,
            )

        try:
            payload = await self._service.execute_action(
                action_id=authority.action_id,
                arguments=arguments,
                connection_id=connection_id,
                runtime_token=token,
                omit_connection_selector=omit_connection_selector,
            )
        except GatewayDeniedError as exc:
            return AdapterResult(
                outcome=AdapterOutcome.DENIED,
                code=exc.code,
                detail="the custodian refused the request",
                dispatched=True,
            )
        except GatewayConfigurationError as exc:
            return AdapterResult(
                outcome=AdapterOutcome.NEEDS_CONFIGURATION,
                code=exc.code,
                detail="the custodian has no usable configuration for this connection",
                dispatched=True,
            )
        except GatewayTimeoutError as exc:
            return AdapterResult(
                outcome=AdapterOutcome.TIMED_OUT,
                code=exc.code,
                detail="the custodian did not answer; the execution outcome is unknown",
                dispatched=True,
            )
        except GatewayUnavailableError as exc:
            return AdapterResult(
                outcome=AdapterOutcome.UNAVAILABLE,
                code=exc.code,
                detail="the custodian is unavailable",
                dispatched=True,
            )
        except GatewayRequestRejectedError as exc:
            return AdapterResult(
                outcome=AdapterOutcome.FAILED,
                code=exc.code,
                detail="the request was rejected by the custodian or the provider",
                dispatched=True,
            )
        except GatewayPayloadTooLargeError as exc:
            return AdapterResult(
                outcome=AdapterOutcome.FAILED,
                code=exc.code,
                detail="the custodian response exceeded the adapter bound",
                dispatched=True,
            )
        except GatewayError as exc:
            return AdapterResult(
                outcome=AdapterOutcome.UNAVAILABLE,
                code=exc.code,
                detail="the custodian call failed",
                dispatched=True,
            )

        bounded, truncated = _bound_payload(payload, self._max_payload_bytes)
        return AdapterResult(
            outcome=AdapterOutcome.SUCCESS,
            code="ok",
            payload=_redact_payload(bounded),
            truncated=truncated,
            dispatched=True,
        )

    async def _evaluate_authority(self, authority: ExecutionAuthority):
        account = str(authority.guardian_account_id or "").strip()
        if not account:
            return _deny_decision("missing_account", "an authenticated account is required")
        profile = authority.permission_profile_provider()
        if inspect.isawaitable(profile):
            profile = await profile
        request = PermissionProfileRequest(
            actor_id=authority.actor_id,
            subject_id=authority.subject_id,
            task_id=authority.task_id,
            command_id=authority.command_id(),
            command_class=COMMAND_CLASS_CONNECTOR,
            uses_connector=True,
            uses_network=True,
        )
        return evaluate_permission_profile(profile, request)


def _deny_decision(code: str, reason: str) -> PermissionProfileDecision:
    return PermissionProfileDecision(allowed=False, code=code, reason=reason)


def _denied(code: str, reason: str) -> AdapterResult:
    return AdapterResult(outcome=AdapterOutcome.DENIED, code=code, detail=reason)


def _check_binding(
    binding: AccountBinding, authority: ExecutionAuthority
) -> AdapterResult | None:
    if not binding.is_authorized():
        return _denied(
            "binding_not_authorized",
            "the binding is not in an authorized state",
        )
    if str(binding.guardian_account_id or "").strip() != str(
        authority.guardian_account_id or ""
    ).strip():
        return _denied(
            "binding_account_mismatch",
            "the binding belongs to a different account",
        )
    if str(binding.provider or "").strip() != str(authority.provider or "").strip():
        return _denied(
            "binding_provider_mismatch",
            "the binding is for a different provider",
        )
    if not binding.has_scoped_grant():
        return _denied(
            "connection_grant_empty",
            "the binding carries no scoped connection grant",
        )
    if not binding.grants_connection(binding.connection_id):
        return _denied(
            "connection_grant_inconsistent",
            "the binding's own connection is outside its scoped grant",
        )
    return None


def _select_connection(
    binding: AccountBinding, authority: ExecutionAuthority
) -> str | None:
    """Resolve the explicit connection for this execution.

    A requested connection may only narrow to what the binding already
    grants. Omitting the request uses the binding's own connection; it never
    falls back to a custodian default or a shared connection.
    """
    requested = str(authority.requested_connection_id or "").strip()
    candidate = requested or str(binding.connection_id or "").strip()
    if not candidate:
        return None
    if not binding.grants_connection(candidate):
        return None
    return candidate


def _checked_arguments(arguments: Mapping[str, Any]) -> Any:
    """Validate the action arguments before they cross the boundary."""
    if arguments is None:
        return {}
    if not isinstance(arguments, Mapping):
        return _denied(
            "invalid_arguments", "action arguments must be a mapping"
        )
    try:
        encoded = json.dumps(dict(arguments), default=str)
    except (TypeError, ValueError):
        return _denied("invalid_arguments", "action arguments are not serializable")
    if len(encoded.encode("utf-8")) > MAX_PAYLOAD_BYTES:
        return _denied(
            "arguments_too_large", "action arguments exceed the request bound"
        )
    return dict(arguments)


def _action_metadata(action: ApprovedAction) -> dict[str, Any]:
    return {
        "action_id": action.action_id,
        "provider": action.provider,
        "description": action.description,
        "connection_selection": action.connection_selection.value,
        "credential_bearing": action.credential_bearing,
        "read_only": True,
    }


def _redact_payload(payload: Any) -> Any:
    """Apply Codexify's sensitive-key redaction to a success payload."""
    if isinstance(payload, Mapping):
        return redact_arguments("openconnector::payload", dict(payload))
    return redact_arguments("openconnector::payload", {"result": payload})["result"]


def _bound_payload(payload: Any, max_bytes: int) -> tuple[Any, bool]:
    """Bound a payload before any caller sees it.

    Returns the bounded payload and whether truncation happened. The bound is
    applied here, before the payload can reach a result, a model context, or a
    log.
    """
    if _encoded_size(payload) <= max_bytes:
        return payload, False
    return _truncate(payload, max_bytes), True


def _encoded_size(payload: Any) -> int:
    try:
        return len(json.dumps(payload, default=str).encode("utf-8"))
    except (TypeError, ValueError):
        return MAX_PAYLOAD_BYTES


def _truncate(payload: Any, max_bytes: int) -> Any:
    """Deterministically truncate a payload until it fits the bound."""
    if isinstance(payload, list):
        kept: list[Any] = []
        for item in payload:
            candidate = kept + [item]
            if _encoded_size(candidate) > max_bytes:
                break
            kept = candidate
        kept.append(_truncation_marker(len(payload), len(kept)))
        return kept
    if isinstance(payload, Mapping):
        kept_map: dict[str, Any] = {}
        for key, value in payload.items():
            candidate = dict(kept_map)
            candidate[str(key)] = value
            if _encoded_size(candidate) > max_bytes:
                break
            kept_map = candidate
        kept_map["_truncated"] = _truncation_marker(len(payload), len(kept_map))
        return kept_map
    if isinstance(payload, str):
        return payload[: max_bytes]
    return _truncation_marker(1, 0)


def _truncation_marker(original: int, kept: int) -> dict[str, Any]:
    return {
        "truncated": True,
        "original_items": original,
        "returned_items": kept,
        "reason": "response_exceeded_adapter_bound",
    }


__all__ = [
    "COMMAND_CLASS_CONNECTOR",
    "COMMAND_ID_PREFIX",
    "AdapterOutcome",
    "AdapterResult",
    "ExecutionAuthority",
    "OpenConnectorAdapter",
]
