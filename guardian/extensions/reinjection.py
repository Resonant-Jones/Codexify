"""Pure reinjection helpers for manual capability dispatch results."""

from __future__ import annotations

import json
from typing import Any, Mapping

from guardian.command_bus.contracts import (
    CapabilityManualDispatchResult,
    CommandBusInvokeResult,
)
from guardian.extensions.contracts import (
    CapabilityReinjectedOutput,
    CapabilityResultReinjectionOutcome,
    CapabilityResultReinjectionRequest,
    CapabilityResultReinjectionResult,
    ExtensionProposalManifest,
    ExtensionRequestedPermission,
)
from guardian.extensions.tokens import (
    CapabilityReinjectionFailureReason,
    CapabilityReinjectionResultShape,
    CapabilityReinjectionSource,
)


def _canonical_json_payload(value: Any) -> Any:
    return json.loads(json.dumps(value, sort_keys=True, default=str))


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _permission_snapshot(
    manual_dispatch_result: CapabilityManualDispatchResult,
) -> tuple[ExtensionRequestedPermission, ...]:
    permissions = tuple(
        ExtensionRequestedPermission.from_payload(item)
        for item in manual_dispatch_result.approved_permissions_json or []
    )
    return permissions


def _manifest_snapshot(
    manual_dispatch_result: CapabilityManualDispatchResult,
) -> ExtensionProposalManifest:
    return ExtensionProposalManifest.from_payload(
        manual_dispatch_result.manifest_snapshot_json
    )


def _build_request(
    *,
    account_id: str,
    manual_dispatch_result: CapabilityManualDispatchResult | Mapping[str, Any],
) -> CapabilityResultReinjectionRequest:
    return CapabilityResultReinjectionRequest(
        account_id=account_id,
        manual_dispatch_result=manual_dispatch_result,
    )


def _base_output(
    request: CapabilityResultReinjectionRequest,
    *,
    outcome_token: str,
    result_shape_token: str,
    failure_reason_token: str | None = None,
) -> CapabilityReinjectedOutput:
    manual_dispatch = request.manual_dispatch_result
    return CapabilityReinjectedOutput(
        account_id=request.account_id,
        proposal_id=manual_dispatch.proposal_id,
        registry_entry_id=manual_dispatch.registry_entry_id,
        effective_binding_id=manual_dispatch.effective_binding_id,
        resolved_from_scope_token=manual_dispatch.resolved_from_scope_token,
        manual_dispatch_id=manual_dispatch.manual_dispatch_id,
        command_bus_run_id=manual_dispatch.command_bus_run_id,
        manifest_snapshot=None,
        approved_permissions=(),
        reinjection_source_token=CapabilityReinjectionSource.MANUAL_DISPATCH.value,
        reinjection_outcome_token=outcome_token,
        result_shape_token=result_shape_token,
        normalized_command_result_payload=None,
        normalized_command_failure_payload=None,
        reinjection_failure_reason_token=failure_reason_token,
    )


def _terminal_success(
    request: CapabilityResultReinjectionRequest,
    *,
    normalized_result: CommandBusInvokeResult,
    manifest_snapshot: ExtensionProposalManifest,
    approved_permissions: tuple[ExtensionRequestedPermission, ...],
    outcome_token: str,
) -> CapabilityResultReinjectionResult:
    manual_dispatch = request.manual_dispatch_result
    normalized_payload = _canonical_json_payload(
        normalized_result.model_dump(mode="json")
    )
    output = CapabilityReinjectedOutput(
        account_id=request.account_id,
        proposal_id=manual_dispatch.proposal_id,
        registry_entry_id=manual_dispatch.registry_entry_id,
        effective_binding_id=manual_dispatch.effective_binding_id,
        resolved_from_scope_token=manual_dispatch.resolved_from_scope_token,
        manual_dispatch_id=manual_dispatch.manual_dispatch_id,
        command_bus_run_id=normalized_result.run_id,
        manifest_snapshot=manifest_snapshot,
        approved_permissions=approved_permissions,
        reinjection_source_token=CapabilityReinjectionSource.MANUAL_DISPATCH.value,
        reinjection_outcome_token=outcome_token,
        result_shape_token=CapabilityReinjectionResultShape.NORMALIZED_SUCCESS.value,
        normalized_command_result_payload=normalized_payload,
        normalized_command_failure_payload=None,
        reinjection_failure_reason_token=None,
    )
    return CapabilityResultReinjectionResult(
        request=request,
        reinjection_outcome_token=outcome_token,
        result_shape_token=CapabilityReinjectionResultShape.NORMALIZED_SUCCESS.value,
        reinjection_source_token=CapabilityReinjectionSource.MANUAL_DISPATCH.value,
        reinjection_failure_reason_token=None,
        reinjected_output=output,
    )


def _terminal_failure(
    request: CapabilityResultReinjectionRequest,
    *,
    normalized_result: CommandBusInvokeResult,
    manifest_snapshot: ExtensionProposalManifest,
    approved_permissions: tuple[ExtensionRequestedPermission, ...],
    outcome_token: str,
) -> CapabilityResultReinjectionResult:
    manual_dispatch = request.manual_dispatch_result
    normalized_payload = _canonical_json_payload(
        normalized_result.model_dump(mode="json")
    )
    output = CapabilityReinjectedOutput(
        account_id=request.account_id,
        proposal_id=manual_dispatch.proposal_id,
        registry_entry_id=manual_dispatch.registry_entry_id,
        effective_binding_id=manual_dispatch.effective_binding_id,
        resolved_from_scope_token=manual_dispatch.resolved_from_scope_token,
        manual_dispatch_id=manual_dispatch.manual_dispatch_id,
        command_bus_run_id=normalized_result.run_id,
        manifest_snapshot=manifest_snapshot,
        approved_permissions=approved_permissions,
        reinjection_source_token=CapabilityReinjectionSource.MANUAL_DISPATCH.value,
        reinjection_outcome_token=outcome_token,
        result_shape_token=CapabilityReinjectionResultShape.NORMALIZED_FAILURE.value,
        normalized_command_result_payload=None,
        normalized_command_failure_payload=normalized_payload,
        reinjection_failure_reason_token=None,
    )
    return CapabilityResultReinjectionResult(
        request=request,
        reinjection_outcome_token=outcome_token,
        result_shape_token=CapabilityReinjectionResultShape.NORMALIZED_FAILURE.value,
        reinjection_source_token=CapabilityReinjectionSource.MANUAL_DISPATCH.value,
        reinjection_failure_reason_token=None,
        reinjected_output=output,
    )


def _unusable_result(
    request: CapabilityResultReinjectionRequest,
    *,
    failure_reason_token: str,
) -> CapabilityResultReinjectionResult:
    output = _base_output(
        request,
        outcome_token=CapabilityResultReinjectionOutcome.UNUSABLE.value,
        result_shape_token=CapabilityReinjectionResultShape.FAILED_CLOSED.value,
        failure_reason_token=failure_reason_token,
    )
    return CapabilityResultReinjectionResult(
        request=request,
        reinjection_outcome_token=CapabilityResultReinjectionOutcome.UNUSABLE.value,
        result_shape_token=CapabilityReinjectionResultShape.FAILED_CLOSED.value,
        reinjection_source_token=CapabilityReinjectionSource.MANUAL_DISPATCH.value,
        reinjection_failure_reason_token=failure_reason_token,
        reinjected_output=output,
    )


def _reinjection_failure_reason(
    value: CapabilityReinjectionFailureReason,
) -> str:
    return value.value


def _normalize_manual_dispatch_result(
    *,
    request: CapabilityResultReinjectionRequest,
    expected_outcome_token: str | None = None,
) -> CapabilityResultReinjectionResult:
    manual_dispatch = request.manual_dispatch_result

    if request.account_id != manual_dispatch.account_id:
        return _unusable_result(
            request,
            failure_reason_token=_reinjection_failure_reason(
                CapabilityReinjectionFailureReason.OWNER_MISMATCH
            ),
        )

    try:
        normalized_result = CommandBusInvokeResult.model_validate(
            manual_dispatch.command_bus_result_json
        )
    except Exception:
        return _unusable_result(
            request,
            failure_reason_token=_reinjection_failure_reason(
                CapabilityReinjectionFailureReason.INVALID_COMMAND_BUS_RESULT
            ),
        )

    expected_run_id = _clean_text(manual_dispatch.command_bus_run_id)
    if not expected_run_id:
        return _unusable_result(
            request,
            failure_reason_token=_reinjection_failure_reason(
                CapabilityReinjectionFailureReason.MISSING_COMMAND_BUS_RUN_LINKAGE
            ),
        )
    if expected_run_id != _clean_text(normalized_result.run_id):
        return _unusable_result(
            request,
            failure_reason_token=_reinjection_failure_reason(
                CapabilityReinjectionFailureReason.INCONSISTENT_COMMAND_BUS_RESULT
            ),
        )

    try:
        manifest_snapshot = _manifest_snapshot(manual_dispatch)
        approved_permissions = _permission_snapshot(manual_dispatch)
    except Exception:
        return _unusable_result(
            request,
            failure_reason_token=_reinjection_failure_reason(
                CapabilityReinjectionFailureReason.INVALID_COMMAND_BUS_RESULT
            ),
        )

    status = _clean_text(normalized_result.status)
    if expected_outcome_token == CapabilityResultReinjectionOutcome.SUCCESS.value:
        if status != "completed":
            return _unusable_result(
                request,
                failure_reason_token=_reinjection_failure_reason(
                    CapabilityReinjectionFailureReason.INCONSISTENT_COMMAND_BUS_RESULT
                ),
            )
    elif expected_outcome_token == CapabilityResultReinjectionOutcome.FAILURE.value:
        if status not in {"blocked", "failed"}:
            return _unusable_result(
                request,
                failure_reason_token=_reinjection_failure_reason(
                    CapabilityReinjectionFailureReason.INCONSISTENT_COMMAND_BUS_RESULT
                ),
            )

    if status == "completed":
        if normalized_result.inline_result is None:
            return _unusable_result(
                request,
                failure_reason_token=_reinjection_failure_reason(
                    CapabilityReinjectionFailureReason.MISSING_INLINE_RESULT
                ),
            )
        if normalized_result.error is not None:
            return _unusable_result(
                request,
                failure_reason_token=_reinjection_failure_reason(
                    CapabilityReinjectionFailureReason.INCONSISTENT_COMMAND_BUS_RESULT
                ),
            )
        return _terminal_success(
            request,
            normalized_result=normalized_result,
            manifest_snapshot=manifest_snapshot,
            approved_permissions=approved_permissions,
            outcome_token=CapabilityResultReinjectionOutcome.SUCCESS.value,
        )

    if status in {"blocked", "failed"}:
        if normalized_result.error is None:
            return _unusable_result(
                request,
                failure_reason_token=_reinjection_failure_reason(
                    CapabilityReinjectionFailureReason.MISSING_ERROR
                ),
            )
        if normalized_result.inline_result is not None:
            return _unusable_result(
                request,
                failure_reason_token=_reinjection_failure_reason(
                    CapabilityReinjectionFailureReason.INCONSISTENT_COMMAND_BUS_RESULT
                ),
            )
        return _terminal_failure(
            request,
            normalized_result=normalized_result,
            manifest_snapshot=manifest_snapshot,
            approved_permissions=approved_permissions,
            outcome_token=CapabilityResultReinjectionOutcome.FAILURE.value,
        )

    return _unusable_result(
        request,
        failure_reason_token=_reinjection_failure_reason(
            CapabilityReinjectionFailureReason.INCONSISTENT_COMMAND_BUS_RESULT
        ),
    )


def reinject_successful_manual_capability_dispatch_result(
    *,
    account_id: str,
    manual_dispatch_result: CapabilityManualDispatchResult | Mapping[str, Any],
) -> CapabilityResultReinjectionResult:
    request = _build_request(
        account_id=account_id, manual_dispatch_result=manual_dispatch_result
    )
    return _normalize_manual_dispatch_result(
        request=request,
        expected_outcome_token=CapabilityResultReinjectionOutcome.SUCCESS.value,
    )


def reinject_failed_manual_capability_dispatch_result(
    *,
    account_id: str,
    manual_dispatch_result: CapabilityManualDispatchResult | Mapping[str, Any],
) -> CapabilityResultReinjectionResult:
    request = _build_request(
        account_id=account_id, manual_dispatch_result=manual_dispatch_result
    )
    return _normalize_manual_dispatch_result(
        request=request,
        expected_outcome_token=CapabilityResultReinjectionOutcome.FAILURE.value,
    )


def reinject_capability_manual_dispatch_result(
    *,
    account_id: str,
    manual_dispatch_result: CapabilityManualDispatchResult | Mapping[str, Any],
) -> CapabilityResultReinjectionResult:
    request = _build_request(
        account_id=account_id, manual_dispatch_result=manual_dispatch_result
    )
    return _normalize_manual_dispatch_result(request=request)


__all__ = [
    "reinject_successful_manual_capability_dispatch_result",
    "reinject_failed_manual_capability_dispatch_result",
    "reinject_capability_manual_dispatch_result",
]
