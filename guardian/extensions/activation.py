"""Read-time activation helpers for effective extension capabilities."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from guardian.extensions.contracts import (
    CapabilityActivationConflictDetail,
    CapabilityActivationDecision,
    CapabilityActivationMatch,
    CapabilityActivationOutcomeToken,
    CapabilityActivationRequest,
    CapabilityDispatchEnvelope,
    CapabilityExposedCommand,
    EffectiveCapabilityRecord,
    ExtensionRequestedPermission,
)
from guardian.extensions.resolver import (
    EffectiveCapabilityResolutionError,
    EffectiveCapabilityResolver,
)
from guardian.extensions.store import ExtensionProposalStore
from guardian.extensions.tokens import (
    CapabilityActivationConflictClassToken,
    CapabilityActivationContextToken,
    CapabilityActivationDenyReasonToken,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _permission_key(
    permission: ExtensionRequestedPermission,
) -> tuple[str, str]:
    return permission.permission, permission.resource or ""


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


def _requested_permission_subset(
    *,
    requested: tuple[ExtensionRequestedPermission, ...],
    approved: tuple[ExtensionRequestedPermission, ...],
) -> bool:
    requested_keys = {_permission_key(permission) for permission in requested}
    approved_keys = {_permission_key(permission) for permission in approved}
    return requested_keys.issubset(approved_keys)


def _build_request(
    *,
    account_id: str,
    requested_command_id: str,
    activation_context_token: str,
    project_id: int | None = None,
    profile_id: str | None = None,
    requested_permissions: Sequence[
        ExtensionRequestedPermission | Mapping[str, Any]
    ]
    | None = None,
    request_metadata: Mapping[str, Any] | None = None,
    source_thread_id: int | None = None,
    source_message_id: int | None = None,
    requested_at: datetime | None = None,
) -> CapabilityActivationRequest:
    return CapabilityActivationRequest(
        account_id=account_id,
        requested_command_id=requested_command_id,
        activation_context_token=activation_context_token,
        project_id=project_id,
        profile_id=profile_id,
        requested_permissions=_coerce_permissions(requested_permissions),
        request_metadata=dict(request_metadata or {}),
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


def _resolve_snapshot(
    *,
    request: CapabilityActivationRequest,
    resolver: EffectiveCapabilityResolver,
):
    if (
        request.activation_context_token
        == CapabilityActivationContextToken.OWNER_ONLY.value
    ):
        return resolver.resolve_effective_capabilities_for_owner(
            account_id=request.account_id
        )
    if (
        request.activation_context_token
        == CapabilityActivationContextToken.OWNER_PROJECT.value
    ):
        return resolver.resolve_effective_capabilities_for_owner_and_project(
            account_id=request.account_id,
            project_id=request.project_id
            if request.project_id is not None
            else 0,
        )
    if (
        request.activation_context_token
        == CapabilityActivationContextToken.OWNER_PROFILE.value
    ):
        return resolver.resolve_effective_capabilities_for_owner_and_profile(
            account_id=request.account_id,
            profile_id=request.profile_id or "",
        )
    return resolver.resolve_effective_capabilities_for_owner_project_profile(
        account_id=request.account_id,
        project_id=request.project_id if request.project_id is not None else 0,
        profile_id=request.profile_id or "",
    )


def _match_exposed_command(
    *,
    record: EffectiveCapabilityRecord,
    requested_command_id: str,
) -> tuple[CapabilityExposedCommand, str | None] | None:
    for exposed_command in record.manifest_snapshot.exposed_commands:
        if exposed_command.command_id == requested_command_id:
            return exposed_command, None
        if requested_command_id in exposed_command.tool_aliases:
            return exposed_command, requested_command_id
    return None


def _build_match(
    *,
    record: EffectiveCapabilityRecord,
    exposed_command: CapabilityExposedCommand,
    matched_alias: str | None,
) -> CapabilityActivationMatch:
    return CapabilityActivationMatch(
        account_id=record.account_id,
        registry_entry_id=record.registry_entry_id,
        proposal_id=record.proposal_id,
        binding_id=record.binding_id,
        resolved_from_scope_token=record.resolved_from_scope_token,
        manifest_snapshot=record.manifest_snapshot,
        approved_permissions=record.approved_permissions,
        exposed_command=exposed_command,
        matched_alias=matched_alias,
        source_thread_id=record.source_thread_id,
        source_message_id=record.source_message_id,
        target_surface_token=record.target_surface_token,
        match_metadata={
            "registry_status_token": record.registry_status_token,
            "binding_status_token": record.binding_status_token,
        },
    )


def _deny(
    *,
    request: CapabilityActivationRequest,
    reason_token: str,
    candidate_matches: tuple[CapabilityActivationMatch, ...] = (),
    evaluated_at: datetime | None = None,
) -> CapabilityActivationDecision:
    return CapabilityActivationDecision(
        request=request,
        outcome_token=CapabilityActivationOutcomeToken.DENIED.value,
        candidate_matches=candidate_matches,
        denial_reason_token=reason_token,
        evaluated_at=evaluated_at or _utc_now(),
        decision_metadata={
            "requested_command_id": request.requested_command_id,
            "activation_context_token": request.activation_context_token,
        },
    )


def _conflict(
    *,
    request: CapabilityActivationRequest,
    conflict_class_token: str,
    candidate_matches: tuple[CapabilityActivationMatch, ...],
    summary: str,
    evaluated_at: datetime | None = None,
    conflict_metadata: Mapping[str, Any] | None = None,
) -> CapabilityActivationDecision:
    return CapabilityActivationDecision(
        request=request,
        outcome_token=CapabilityActivationOutcomeToken.CONFLICT.value,
        candidate_matches=candidate_matches,
        conflict_details=(
            CapabilityActivationConflictDetail(
                conflict_class_token=conflict_class_token,
                requested_command_id=request.requested_command_id,
                candidate_matches=candidate_matches,
                summary=summary,
                conflict_metadata=dict(conflict_metadata or {}),
            ),
        ),
        conflict_class_token=conflict_class_token,
        evaluated_at=evaluated_at or _utc_now(),
        decision_metadata={
            "requested_command_id": request.requested_command_id,
            "activation_context_token": request.activation_context_token,
        },
    )


def _allowed(
    *,
    request: CapabilityActivationRequest,
    match: CapabilityActivationMatch,
    evaluated_at: datetime | None = None,
) -> CapabilityActivationDecision:
    envelope = CapabilityDispatchEnvelope(
        owner_account_id=request.account_id,
        requested_command_id=request.requested_command_id,
        command_id=match.exposed_command.command_id,
        activation_context_token=request.activation_context_token,
        proposal_id=match.proposal_id,
        registry_entry_id=match.registry_entry_id,
        binding_id=match.binding_id,
        resolved_from_scope_token=match.resolved_from_scope_token,
        manifest_snapshot=match.manifest_snapshot,
        approved_permissions=match.approved_permissions,
        requested_permissions=request.requested_permissions,
        matched_alias=match.matched_alias,
        actor_id=request.account_id,
        actor_session_id=None,
        delegated_by=None,
        arguments={},
        requested_at=request.requested_at,
        envelope_metadata={
            "source_thread_id": match.source_thread_id,
            "source_message_id": match.source_message_id,
            "requested_command_id": request.requested_command_id,
        },
    )
    return CapabilityActivationDecision(
        request=request,
        outcome_token=CapabilityActivationOutcomeToken.ALLOWED.value,
        candidate_matches=(match,),
        dispatch_envelope=envelope,
        evaluated_at=evaluated_at or _utc_now(),
        decision_metadata={
            "requested_command_id": request.requested_command_id,
            "activation_context_token": request.activation_context_token,
        },
    )


def _activate(
    *,
    request: CapabilityActivationRequest,
    resolver: EffectiveCapabilityResolver | None = None,
    store: ExtensionProposalStore | None = None,
) -> CapabilityActivationDecision:
    resolved = _get_resolver(resolver=resolver, store=store)
    try:
        snapshot = _resolve_snapshot(request=request, resolver=resolved)
    except EffectiveCapabilityResolutionError as exc:
        return _conflict(
            request=request,
            conflict_class_token=CapabilityActivationConflictClassToken.RESOLUTION_AMBIGUITY.value,
            candidate_matches=(),
            summary=str(exc),
            conflict_metadata={"resolution_error": str(exc)},
        )

    candidate_matches: list[CapabilityActivationMatch] = []
    for record in snapshot.records:
        exposure = _match_exposed_command(
            record=record, requested_command_id=request.requested_command_id
        )
        if exposure is None:
            continue
        exposed_command, matched_alias = exposure
        candidate_matches.append(
            _build_match(
                record=record,
                exposed_command=exposed_command,
                matched_alias=matched_alias,
            )
        )

    if not candidate_matches:
        return _deny(
            request=request,
            reason_token=CapabilityActivationDenyReasonToken.NO_MATCHING_EXPOSURE.value,
            evaluated_at=_utc_now(),
        )

    if len(candidate_matches) > 1:
        summary = (
            "multiple effective capabilities expose "
            f"{request.requested_command_id!r}"
        )
        return _conflict(
            request=request,
            conflict_class_token=CapabilityActivationConflictClassToken.SAME_COMMAND_EXPOSURE.value,
            candidate_matches=tuple(candidate_matches),
            summary=summary,
            conflict_metadata={
                "candidate_count": len(candidate_matches),
                "requested_command_id": request.requested_command_id,
            },
        )

    match = candidate_matches[0]
    if not _requested_permission_subset(
        requested=request.requested_permissions,
        approved=match.approved_permissions,
    ):
        return _deny(
            request=request,
            reason_token=CapabilityActivationDenyReasonToken.INSUFFICIENT_PERMISSIONS.value,
            candidate_matches=(match,),
        )

    return _allowed(request=request, match=match)


def activate_capability_for_owner_only(
    *,
    account_id: str,
    requested_command_id: str,
    requested_permissions: Sequence[
        ExtensionRequestedPermission | Mapping[str, Any]
    ]
    | None = None,
    resolver: EffectiveCapabilityResolver | None = None,
    store: ExtensionProposalStore | None = None,
    request_metadata: Mapping[str, Any] | None = None,
    source_thread_id: int | None = None,
    source_message_id: int | None = None,
    requested_at: datetime | None = None,
) -> CapabilityActivationDecision:
    request = _build_request(
        account_id=account_id,
        requested_command_id=requested_command_id,
        activation_context_token=CapabilityActivationContextToken.OWNER_ONLY.value,
        requested_permissions=requested_permissions,
        request_metadata=request_metadata,
        source_thread_id=source_thread_id,
        source_message_id=source_message_id,
        requested_at=requested_at,
    )
    return _activate(request=request, resolver=resolver, store=store)


def activate_capability_for_owner_and_project(
    *,
    account_id: str,
    project_id: int,
    requested_command_id: str,
    requested_permissions: Sequence[
        ExtensionRequestedPermission | Mapping[str, Any]
    ]
    | None = None,
    resolver: EffectiveCapabilityResolver | None = None,
    store: ExtensionProposalStore | None = None,
    request_metadata: Mapping[str, Any] | None = None,
    source_thread_id: int | None = None,
    source_message_id: int | None = None,
    requested_at: datetime | None = None,
) -> CapabilityActivationDecision:
    request = _build_request(
        account_id=account_id,
        requested_command_id=requested_command_id,
        activation_context_token=CapabilityActivationContextToken.OWNER_PROJECT.value,
        project_id=project_id,
        requested_permissions=requested_permissions,
        request_metadata=request_metadata,
        source_thread_id=source_thread_id,
        source_message_id=source_message_id,
        requested_at=requested_at,
    )
    return _activate(request=request, resolver=resolver, store=store)


def activate_capability_for_owner_and_profile(
    *,
    account_id: str,
    profile_id: str,
    requested_command_id: str,
    requested_permissions: Sequence[
        ExtensionRequestedPermission | Mapping[str, Any]
    ]
    | None = None,
    resolver: EffectiveCapabilityResolver | None = None,
    store: ExtensionProposalStore | None = None,
    request_metadata: Mapping[str, Any] | None = None,
    source_thread_id: int | None = None,
    source_message_id: int | None = None,
    requested_at: datetime | None = None,
) -> CapabilityActivationDecision:
    request = _build_request(
        account_id=account_id,
        requested_command_id=requested_command_id,
        activation_context_token=CapabilityActivationContextToken.OWNER_PROFILE.value,
        profile_id=profile_id,
        requested_permissions=requested_permissions,
        request_metadata=request_metadata,
        source_thread_id=source_thread_id,
        source_message_id=source_message_id,
        requested_at=requested_at,
    )
    return _activate(request=request, resolver=resolver, store=store)


def activate_capability_for_owner_project_profile(
    *,
    account_id: str,
    project_id: int,
    profile_id: str,
    requested_command_id: str,
    requested_permissions: Sequence[
        ExtensionRequestedPermission | Mapping[str, Any]
    ]
    | None = None,
    resolver: EffectiveCapabilityResolver | None = None,
    store: ExtensionProposalStore | None = None,
    request_metadata: Mapping[str, Any] | None = None,
    source_thread_id: int | None = None,
    source_message_id: int | None = None,
    requested_at: datetime | None = None,
) -> CapabilityActivationDecision:
    request = _build_request(
        account_id=account_id,
        requested_command_id=requested_command_id,
        activation_context_token=CapabilityActivationContextToken.OWNER_PROJECT_PROFILE.value,
        project_id=project_id,
        profile_id=profile_id,
        requested_permissions=requested_permissions,
        request_metadata=request_metadata,
        source_thread_id=source_thread_id,
        source_message_id=source_message_id,
        requested_at=requested_at,
    )
    return _activate(request=request, resolver=resolver, store=store)


__all__ = [
    "activate_capability_for_owner_only",
    "activate_capability_for_owner_and_project",
    "activate_capability_for_owner_and_profile",
    "activate_capability_for_owner_project_profile",
]
