"""Manual capability-to-command-bus dispatch helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from fastapi import HTTPException

from guardian.command_bus.contracts import (
    ActorSpec,
    CommandBusInvokeResult,
    InvokeArguments,
    InvokeRequest,
)
from guardian.command_bus.invoke import execute_invoke
from guardian.command_bus.store import CommandBusStore
from guardian.extensions.activation import (
    activate_capability_for_owner_and_profile,
    activate_capability_for_owner_and_project,
    activate_capability_for_owner_only,
    activate_capability_for_owner_project_profile,
)
from guardian.extensions.contracts import (
    CapabilityActivationDecision,
    CapabilityActivationDenyReasonToken,
    CapabilityDispatchEnvelope,
    CapabilityManualDispatchDenyReasonToken,
    CapabilityManualDispatchOutcomeToken,
    CapabilityManualDispatchRequest,
    CapabilityManualDispatchResult,
    ExtensionRequestedPermission,
)
from guardian.extensions.resolver import EffectiveCapabilityResolver
from guardian.extensions.store import ExtensionProposalStore
from guardian.extensions.tokens import CapabilityDispatchSourceToken


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _coerce_permissions(
    value: Sequence[ExtensionRequestedPermission | Mapping[str, Any]] | None,
) -> tuple[ExtensionRequestedPermission, ...]:
    if value is None:
        return ()
    normalized: list[ExtensionRequestedPermission] = []
    for item in value:
        if isinstance(item, ExtensionRequestedPermission):
            normalized.append(item)
        elif isinstance(item, Mapping):
            normalized.append(ExtensionRequestedPermission.from_payload(item))
        else:
            raise ValueError(
                "requested permissions must be extension permission records or mappings"
            )
    return tuple(normalized)


def _permissions_subset(
    *,
    requested: tuple[ExtensionRequestedPermission, ...],
    approved: tuple[ExtensionRequestedPermission, ...],
) -> bool:
    requested_keys = {
        (permission.permission, permission.resource or "")
        for permission in requested
    }
    approved_keys = {
        (permission.permission, permission.resource or "")
        for permission in approved
    }
    return requested_keys.issubset(approved_keys)


def _build_request(
    *,
    account_id: str,
    requested_command_id: str,
    command_arguments: InvokeArguments | Mapping[str, Any],
    project_id: int | None = None,
    profile_id: str | None = None,
    requested_permissions: Sequence[
        ExtensionRequestedPermission | Mapping[str, Any]
    ]
    | None = None,
    request_metadata: Mapping[str, Any] | None = None,
    dispatch_envelope: CapabilityDispatchEnvelope | None = None,
    idempotency_key: str | None = None,
    source_thread_id: int | None = None,
    source_message_id: int | None = None,
    requested_at: datetime | None = None,
) -> CapabilityManualDispatchRequest:
    return CapabilityManualDispatchRequest(
        account_id=account_id,
        requested_command_id=requested_command_id,
        command_arguments=command_arguments,
        project_id=project_id,
        profile_id=profile_id,
        requested_permissions=_coerce_permissions(requested_permissions),
        request_metadata=dict(request_metadata or {}),
        dispatch_envelope=dispatch_envelope,
        idempotency_key=idempotency_key,
        source_thread_id=source_thread_id,
        source_message_id=source_message_id,
        requested_at=requested_at or _utc_now(),
    )


def _get_resolver(
    *,
    resolver: EffectiveCapabilityResolver | None = None,
    store: ExtensionProposalStore | None = None,
) -> EffectiveCapabilityResolver:
    if resolver is not None:
        return resolver
    return EffectiveCapabilityResolver(store)


def _activation_metadata(
    *,
    activation_decision: CapabilityActivationDecision,
) -> dict[str, Any]:
    return {
        "activation_outcome_token": activation_decision.outcome_token,
        "activation_context_token": activation_decision.request.activation_context_token,
        "activation_deny_reason_token": activation_decision.denial_reason_token,
        "activation_conflict_class_token": activation_decision.conflict_class_token,
        "activation_request_json": activation_decision.request.to_payload(),
    }


def _manual_provenance_json(
    *,
    request: CapabilityManualDispatchRequest,
    envelope: CapabilityDispatchEnvelope,
) -> dict[str, Any]:
    envelope_payload = envelope.to_payload()
    if isinstance(envelope_payload.get("requested_at"), datetime):
        envelope_payload["requested_at"] = envelope_payload[
            "requested_at"
        ].isoformat()
    requested_at = (
        request.requested_at.isoformat() if request.requested_at else None
    )
    provenance = {
        "manual_dispatch_source_token": request.invocation_source_token,
        "idempotency_class_token": request.idempotency_class_token,
        "capability_dispatch_envelope_json": envelope_payload,
        "requested_command_id": request.requested_command_id,
        "requested_permissions_json": [
            permission.to_payload()
            for permission in request.requested_permissions
        ],
        "request_metadata_json": dict(request.request_metadata),
        "source_thread_id": request.source_thread_id,
        "source_message_id": request.source_message_id,
        "requested_at": requested_at,
    }
    return provenance


def _build_command_bus_request(
    *,
    request: CapabilityManualDispatchRequest,
    envelope: CapabilityDispatchEnvelope,
) -> InvokeRequest:
    provenance_json = _manual_provenance_json(
        request=request, envelope=envelope
    )
    return InvokeRequest(
        invoke_version=envelope.invoke_version,
        command_id=envelope.command_id,
        actor=ActorSpec(
            kind=envelope.actor_kind,
            id=request.account_id,
            session_id=envelope.actor_session_id,
            delegated_by=envelope.delegated_by,
        ),
        arguments=request.command_arguments,
        idempotency_key=request.idempotency_key or envelope.idempotency_key,
        provenance_json=provenance_json,
    )


def _bus_result_to_outcome_token(
    command_bus_result: CommandBusInvokeResult,
) -> str:
    if command_bus_result.status in {"blocked", "failed"}:
        return CapabilityManualDispatchOutcomeToken.BUS_REJECTED.value
    return CapabilityManualDispatchOutcomeToken.DISPATCHED.value


def _result_from_activation_denial(
    *,
    request: CapabilityManualDispatchRequest,
    activation_decision: CapabilityActivationDecision,
) -> CapabilityManualDispatchResult:
    if activation_decision.is_conflict:
        reason_token = (
            CapabilityManualDispatchDenyReasonToken.ACTIVATION_CONFLICT.value
        )
        outcome_token = CapabilityManualDispatchOutcomeToken.CONFLICT.value
    else:
        reason_token = (
            CapabilityManualDispatchDenyReasonToken.ACTIVATION_DENIED.value
        )
        if (
            activation_decision.denial_reason_token
            == CapabilityActivationDenyReasonToken.INSUFFICIENT_PERMISSIONS.value
        ):
            reason_token = (
                CapabilityManualDispatchDenyReasonToken.INSUFFICIENT_PERMISSIONS.value
            )
        outcome_token = CapabilityManualDispatchOutcomeToken.DENIED.value
    return CapabilityManualDispatchResult(
        request=request,
        outcome_token=outcome_token,
        activation_decision=activation_decision,
        denial_reason_token=reason_token,
        result_metadata=_activation_metadata(
            activation_decision=activation_decision
        ),
    )


def _result_from_invalid_envelope(
    *,
    request: CapabilityManualDispatchRequest,
    envelope: CapabilityDispatchEnvelope,
    reason_token: str,
) -> CapabilityManualDispatchResult:
    return CapabilityManualDispatchResult(
        request=request,
        outcome_token=CapabilityManualDispatchOutcomeToken.DENIED.value,
        dispatch_envelope=envelope,
        denial_reason_token=reason_token,
        result_metadata={
            "capability_dispatch_envelope_json": envelope.to_payload(),
            "manual_dispatch_source_token": request.invocation_source_token,
            "idempotency_class_token": request.idempotency_class_token,
        },
    )


async def _invoke_allowed_envelope(
    *,
    request: CapabilityManualDispatchRequest,
    envelope: CapabilityDispatchEnvelope,
    store: CommandBusStore,
    app: Any,
    activation_decision: CapabilityActivationDecision | None = None,
) -> CapabilityManualDispatchResult:
    if not _permissions_subset(
        requested=request.requested_permissions,
        approved=envelope.approved_permissions,
    ):
        return CapabilityManualDispatchResult(
            request=request,
            outcome_token=CapabilityManualDispatchOutcomeToken.DENIED.value,
            dispatch_envelope=envelope,
            denial_reason_token=(
                CapabilityManualDispatchDenyReasonToken.INSUFFICIENT_PERMISSIONS.value
            ),
            result_metadata={
                "capability_dispatch_envelope_json": envelope.to_payload(),
                "manual_dispatch_source_token": request.invocation_source_token,
                "idempotency_class_token": request.idempotency_class_token,
            },
        )

    command_bus_request = _build_command_bus_request(
        request=request, envelope=envelope
    )
    try:
        command_bus_response = await execute_invoke(
            payload=command_bus_request,
            auth_subject=request.account_id,
            inbound_headers={},
            store=store,
            app=app,
            execution_lane="tools",
            allow_write_execution=True,
            confirmation_granted=False,
        )
    except HTTPException as exc:
        return CapabilityManualDispatchResult(
            request=request,
            outcome_token=CapabilityManualDispatchOutcomeToken.BUS_REJECTED.value,
            dispatch_envelope=envelope,
            command_bus_request=command_bus_request,
            denial_reason_token=(
                CapabilityManualDispatchDenyReasonToken.COMMAND_BUS_REJECTED.value
            ),
            result_metadata={
                "error": exc.detail if exc.detail is not None else str(exc),
                "capability_dispatch_envelope_json": envelope.to_payload(),
                "manual_dispatch_source_token": request.invocation_source_token,
                "idempotency_class_token": request.idempotency_class_token,
            },
        )
    except Exception as exc:
        return CapabilityManualDispatchResult(
            request=request,
            outcome_token=CapabilityManualDispatchOutcomeToken.BUS_REJECTED.value,
            dispatch_envelope=envelope,
            command_bus_request=command_bus_request,
            denial_reason_token=(
                CapabilityManualDispatchDenyReasonToken.COMMAND_BUS_REJECTED.value
            ),
            result_metadata={
                "error": str(exc),
                "error_type": exc.__class__.__name__,
                "capability_dispatch_envelope_json": envelope.to_payload(),
                "manual_dispatch_source_token": request.invocation_source_token,
                "idempotency_class_token": request.idempotency_class_token,
            },
        )

    command_bus_result = CommandBusInvokeResult.model_validate(
        command_bus_response
    )
    outcome_token = _bus_result_to_outcome_token(command_bus_result)
    denial_reason_token = None
    if outcome_token == CapabilityManualDispatchOutcomeToken.BUS_REJECTED.value:
        denial_reason_token = (
            CapabilityManualDispatchDenyReasonToken.COMMAND_BUS_REJECTED.value
        )

    return CapabilityManualDispatchResult(
        request=request,
        outcome_token=outcome_token,
        activation_decision=activation_decision,
        dispatch_envelope=envelope,
        command_bus_request=command_bus_request,
        command_bus_result=command_bus_result,
        command_run_id=command_bus_result.run_id,
        denial_reason_token=denial_reason_token,
        result_metadata={
            "command_bus_status": command_bus_result.status,
            "capability_dispatch_envelope_json": envelope.to_payload(),
            "manual_dispatch_source_token": request.invocation_source_token,
            "idempotency_class_token": request.idempotency_class_token,
        },
    )


def _envelope_from_activation(
    activation_decision: CapabilityActivationDecision,
) -> CapabilityDispatchEnvelope:
    if (
        not activation_decision.is_allowed
        or activation_decision.dispatch_envelope is None
    ):
        raise ValueError("allowed activation is required for manual dispatch")
    return activation_decision.dispatch_envelope


async def _dispatch_after_activation(
    *,
    request: CapabilityManualDispatchRequest,
    activation_decision: CapabilityActivationDecision,
    store: CommandBusStore,
    app: Any,
) -> CapabilityManualDispatchResult:
    if not activation_decision.is_allowed:
        return _result_from_activation_denial(
            request=request, activation_decision=activation_decision
        )
    envelope = _envelope_from_activation(activation_decision)
    return await _invoke_allowed_envelope(
        request=CapabilityManualDispatchRequest(
            account_id=request.account_id,
            requested_command_id=request.requested_command_id,
            command_arguments=request.command_arguments,
            project_id=request.project_id,
            profile_id=request.profile_id,
            requested_permissions=request.requested_permissions,
            request_metadata=request.request_metadata,
            dispatch_envelope=envelope,
            invocation_source_token=request.invocation_source_token,
            idempotency_class_token=request.idempotency_class_token,
            idempotency_key=request.idempotency_key,
            source_thread_id=request.source_thread_id,
            source_message_id=request.source_message_id,
            requested_at=request.requested_at,
        ),
        envelope=envelope,
        store=store,
        app=app,
        activation_decision=activation_decision,
    )


async def manual_dispatch_capability_for_owner_only(
    *,
    account_id: str,
    requested_command_id: str,
    command_arguments: InvokeArguments | Mapping[str, Any],
    requested_permissions: Sequence[
        ExtensionRequestedPermission | Mapping[str, Any]
    ]
    | None = None,
    resolver: EffectiveCapabilityResolver | None = None,
    store: ExtensionProposalStore | None = None,
    command_bus_store: CommandBusStore | None = None,
    app: Any = None,
    request_metadata: Mapping[str, Any] | None = None,
    idempotency_key: str | None = None,
    source_thread_id: int | None = None,
    source_message_id: int | None = None,
    requested_at: datetime | None = None,
) -> CapabilityManualDispatchResult:
    dispatch_request = _build_request(
        account_id=account_id,
        requested_command_id=requested_command_id,
        command_arguments=command_arguments,
        requested_permissions=requested_permissions,
        request_metadata=request_metadata,
        idempotency_key=idempotency_key,
        source_thread_id=source_thread_id,
        source_message_id=source_message_id,
        requested_at=requested_at,
    )
    activation_decision = activate_capability_for_owner_only(
        account_id=account_id,
        requested_command_id=requested_command_id,
        requested_permissions=requested_permissions,
        resolver=resolver,
        store=store,
        request_metadata=request_metadata,
        source_thread_id=source_thread_id,
        source_message_id=source_message_id,
        requested_at=requested_at,
    )
    return await _dispatch_after_activation(
        request=dispatch_request,
        activation_decision=activation_decision,
        store=command_bus_store or CommandBusStore(),
        app=app,
    )


async def manual_dispatch_capability_for_owner_and_project(
    *,
    account_id: str,
    project_id: int,
    requested_command_id: str,
    command_arguments: InvokeArguments | Mapping[str, Any],
    requested_permissions: Sequence[
        ExtensionRequestedPermission | Mapping[str, Any]
    ]
    | None = None,
    resolver: EffectiveCapabilityResolver | None = None,
    store: ExtensionProposalStore | None = None,
    command_bus_store: CommandBusStore | None = None,
    app: Any = None,
    request_metadata: Mapping[str, Any] | None = None,
    idempotency_key: str | None = None,
    source_thread_id: int | None = None,
    source_message_id: int | None = None,
    requested_at: datetime | None = None,
) -> CapabilityManualDispatchResult:
    dispatch_request = _build_request(
        account_id=account_id,
        requested_command_id=requested_command_id,
        command_arguments=command_arguments,
        project_id=project_id,
        requested_permissions=requested_permissions,
        request_metadata=request_metadata,
        idempotency_key=idempotency_key,
        source_thread_id=source_thread_id,
        source_message_id=source_message_id,
        requested_at=requested_at,
    )
    activation_decision = activate_capability_for_owner_and_project(
        account_id=account_id,
        project_id=project_id,
        requested_command_id=requested_command_id,
        requested_permissions=requested_permissions,
        resolver=resolver,
        store=store,
        request_metadata=request_metadata,
        source_thread_id=source_thread_id,
        source_message_id=source_message_id,
        requested_at=requested_at,
    )
    return await _dispatch_after_activation(
        request=dispatch_request,
        activation_decision=activation_decision,
        store=command_bus_store or CommandBusStore(),
        app=app,
    )


async def manual_dispatch_capability_for_owner_and_profile(
    *,
    account_id: str,
    profile_id: str,
    requested_command_id: str,
    command_arguments: InvokeArguments | Mapping[str, Any],
    requested_permissions: Sequence[
        ExtensionRequestedPermission | Mapping[str, Any]
    ]
    | None = None,
    resolver: EffectiveCapabilityResolver | None = None,
    store: ExtensionProposalStore | None = None,
    command_bus_store: CommandBusStore | None = None,
    app: Any = None,
    request_metadata: Mapping[str, Any] | None = None,
    idempotency_key: str | None = None,
    source_thread_id: int | None = None,
    source_message_id: int | None = None,
    requested_at: datetime | None = None,
) -> CapabilityManualDispatchResult:
    dispatch_request = _build_request(
        account_id=account_id,
        requested_command_id=requested_command_id,
        command_arguments=command_arguments,
        profile_id=profile_id,
        requested_permissions=requested_permissions,
        request_metadata=request_metadata,
        idempotency_key=idempotency_key,
        source_thread_id=source_thread_id,
        source_message_id=source_message_id,
        requested_at=requested_at,
    )
    activation_decision = activate_capability_for_owner_and_profile(
        account_id=account_id,
        profile_id=profile_id,
        requested_command_id=requested_command_id,
        requested_permissions=requested_permissions,
        resolver=resolver,
        store=store,
        request_metadata=request_metadata,
        source_thread_id=source_thread_id,
        source_message_id=source_message_id,
        requested_at=requested_at,
    )
    return await _dispatch_after_activation(
        request=dispatch_request,
        activation_decision=activation_decision,
        store=command_bus_store or CommandBusStore(),
        app=app,
    )


async def manual_dispatch_capability_for_owner_project_profile(
    *,
    account_id: str,
    project_id: int,
    profile_id: str,
    requested_command_id: str,
    command_arguments: InvokeArguments | Mapping[str, Any],
    requested_permissions: Sequence[
        ExtensionRequestedPermission | Mapping[str, Any]
    ]
    | None = None,
    resolver: EffectiveCapabilityResolver | None = None,
    store: ExtensionProposalStore | None = None,
    command_bus_store: CommandBusStore | None = None,
    app: Any = None,
    request_metadata: Mapping[str, Any] | None = None,
    idempotency_key: str | None = None,
    source_thread_id: int | None = None,
    source_message_id: int | None = None,
    requested_at: datetime | None = None,
) -> CapabilityManualDispatchResult:
    dispatch_request = _build_request(
        account_id=account_id,
        requested_command_id=requested_command_id,
        command_arguments=command_arguments,
        project_id=project_id,
        profile_id=profile_id,
        requested_permissions=requested_permissions,
        request_metadata=request_metadata,
        idempotency_key=idempotency_key,
        source_thread_id=source_thread_id,
        source_message_id=source_message_id,
        requested_at=requested_at,
    )
    activation_decision = activate_capability_for_owner_project_profile(
        account_id=account_id,
        project_id=project_id,
        profile_id=profile_id,
        requested_command_id=requested_command_id,
        requested_permissions=requested_permissions,
        resolver=resolver,
        store=store,
        request_metadata=request_metadata,
        source_thread_id=source_thread_id,
        source_message_id=source_message_id,
        requested_at=requested_at,
    )
    return await _dispatch_after_activation(
        request=dispatch_request,
        activation_decision=activation_decision,
        store=command_bus_store or CommandBusStore(),
        app=app,
    )


async def manual_dispatch_capability_from_envelope(
    *,
    account_id: str,
    dispatch_envelope: CapabilityDispatchEnvelope,
    command_arguments: InvokeArguments | Mapping[str, Any],
    requested_permissions: Sequence[
        ExtensionRequestedPermission | Mapping[str, Any]
    ]
    | None = None,
    command_bus_store: CommandBusStore | None = None,
    app: Any = None,
    request_metadata: Mapping[str, Any] | None = None,
    idempotency_key: str | None = None,
    source_thread_id: int | None = None,
    source_message_id: int | None = None,
    requested_at: datetime | None = None,
) -> CapabilityManualDispatchResult:
    if not account_id.strip():
        raise ValueError("account_id is required")
    request = _build_request(
        account_id=account_id,
        requested_command_id=dispatch_envelope.requested_command_id,
        command_arguments=command_arguments,
        requested_permissions=requested_permissions,
        request_metadata=request_metadata,
        dispatch_envelope=dispatch_envelope,
        idempotency_key=idempotency_key,
        source_thread_id=source_thread_id,
        source_message_id=source_message_id,
        requested_at=requested_at,
    )
    if dispatch_envelope.owner_account_id != request.account_id:
        return _result_from_invalid_envelope(
            request=request,
            envelope=dispatch_envelope,
            reason_token=(
                CapabilityManualDispatchDenyReasonToken.OWNER_ACCOUNT_MISMATCH.value
            ),
        )
    if (
        dispatch_envelope.dispatch_source_token
        != CapabilityDispatchSourceToken.CAPABILITY_ACTIVATION.value
    ):
        return _result_from_invalid_envelope(
            request=request,
            envelope=dispatch_envelope,
            reason_token=(
                CapabilityManualDispatchDenyReasonToken.INVALID_ENVELOPE.value
            ),
        )
    if dispatch_envelope.requested_command_id != dispatch_envelope.command_id:
        return _result_from_invalid_envelope(
            request=request,
            envelope=dispatch_envelope,
            reason_token=(
                CapabilityManualDispatchDenyReasonToken.INVALID_ENVELOPE.value
            ),
        )
    return await _invoke_allowed_envelope(
        request=request,
        envelope=dispatch_envelope,
        store=command_bus_store or CommandBusStore(),
        app=app,
    )


__all__ = [
    "manual_dispatch_capability_for_owner_only",
    "manual_dispatch_capability_for_owner_and_project",
    "manual_dispatch_capability_for_owner_and_profile",
    "manual_dispatch_capability_for_owner_project_profile",
    "manual_dispatch_capability_from_envelope",
]
