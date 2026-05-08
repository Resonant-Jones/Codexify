"""Pure reentry seam: one completed reinjection result to one assistant continuation."""

from __future__ import annotations

import json
from typing import Any, Mapping

from guardian.extensions.contracts import (
    CapabilityAssistantContinuationPayload,
    CapabilityAssistantReentryRequest,
    CapabilityAssistantReentryResult,
    CapabilityResultReinjectionResult,
)
from guardian.extensions.tokens import (
    CapabilityAssistantReentryFailureReason,
    CapabilityAssistantReentryOutcome,
    CapabilityReinjectionResultShape,
)


def _canonical_json_payload(value: Any) -> Any:
    return json.loads(json.dumps(value, sort_keys=True, default=str))


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _build_request(
    *,
    account_id: str,
    reinjection_result: CapabilityResultReinjectionResult | Mapping[str, Any],
) -> CapabilityAssistantReentryRequest:
    return CapabilityAssistantReentryRequest(
        account_id=account_id,
        reinjection_result=reinjection_result,
    )


def _continuation_payload_from_reinjection(
    request: CapabilityAssistantReentryRequest,
    *,
    outcome_token: str,
    failure_reason_token: str | None = None,
) -> CapabilityAssistantContinuationPayload:
    reinjection = request.reinjection_result

    manifest_json: dict[str, Any] | None = None
    manifest = reinjection.manifest_snapshot
    if manifest is not None:
        manifest_json = manifest.to_payload()

    approved_perms: list[dict[str, Any]] = []
    for perm in reinjection.approved_permissions:
        if hasattr(perm, "to_payload"):
            approved_perms.append(perm.to_payload())
        elif isinstance(perm, Mapping):
            approved_perms.append(dict(perm))

    return CapabilityAssistantContinuationPayload(
        account_id=request.account_id,
        proposal_id=reinjection.proposal_id,
        registry_entry_id=reinjection.registry_entry_id,
        effective_binding_id=reinjection.effective_binding_id,
        resolved_from_scope_token=reinjection.resolved_from_scope_token,
        manual_dispatch_id=reinjection.manual_dispatch_id,
        command_bus_run_id=reinjection.command_bus_run_id,
        manifest_snapshot_json=manifest_json,
        approved_permissions_json=approved_perms,
        reentry_outcome_token=outcome_token,
        reentry_failure_reason_token=failure_reason_token,
        normalized_command_result_payload=reinjection.normalized_command_result_payload,
        normalized_command_failure_payload=reinjection.normalized_command_failure_payload,
        continuation_metadata={
            "reinjection_outcome": reinjection.reinjection_outcome_token,
            "reinjection_shape": reinjection.result_shape_token,
            "reinjection_source": reinjection.reinjection_source_token,
        },
    )


def _build_result(
    request: CapabilityAssistantReentryRequest,
    *,
    outcome_token: str,
    failure_reason_token: str | None = None,
    continuation_payload: CapabilityAssistantContinuationPayload | None = None,
) -> CapabilityAssistantReentryResult:
    return CapabilityAssistantReentryResult(
        request=request,
        reentry_outcome_token=outcome_token,
        reentry_failure_reason_token=failure_reason_token,
        continuation_payload=continuation_payload,
    )


def _normalize_reinjection_for_reentry(
    *,
    request: CapabilityAssistantReentryRequest,
) -> CapabilityAssistantReentryResult:
    if request.account_id != request.reinjection_result.account_id:
        continuation = _continuation_payload_from_reinjection(
            request,
            outcome_token=CapabilityAssistantReentryOutcome.FAILED_CLOSED.value,
            failure_reason_token=(
                CapabilityAssistantReentryFailureReason.OWNER_MISMATCH.value
            ),
        )
        return _build_result(
            request,
            outcome_token=CapabilityAssistantReentryOutcome.FAILED_CLOSED.value,
            failure_reason_token=(
                CapabilityAssistantReentryFailureReason.OWNER_MISMATCH.value
            ),
            continuation_payload=continuation,
        )

    reinjection = request.reinjection_result
    result_shape = _clean_text(reinjection.result_shape_token)
    reinjection_outcome = _clean_text(reinjection.reinjection_outcome_token)

    if result_shape not in (
        CapabilityReinjectionResultShape.NORMALIZED_SUCCESS.value,
        CapabilityReinjectionResultShape.NORMALIZED_FAILURE.value,
        CapabilityReinjectionResultShape.FAILED_CLOSED.value,
    ):
        continuation = _continuation_payload_from_reinjection(
            request,
            outcome_token=CapabilityAssistantReentryOutcome.FAILED_CLOSED.value,
            failure_reason_token=(
                CapabilityAssistantReentryFailureReason.REINJECTION_RESULT_SHAPE_MISMATCH.value
            ),
        )
        return _build_result(
            request,
            outcome_token=CapabilityAssistantReentryOutcome.FAILED_CLOSED.value,
            failure_reason_token=(
                CapabilityAssistantReentryFailureReason.REINJECTION_RESULT_SHAPE_MISMATCH.value
            ),
            continuation_payload=continuation,
        )

    if (
        result_shape
        == CapabilityReinjectionResultShape.NORMALIZED_SUCCESS.value
    ):
        if reinjection_outcome != "success":
            continuation = _continuation_payload_from_reinjection(
                request,
                outcome_token=CapabilityAssistantReentryOutcome.FAILED_CLOSED.value,
                failure_reason_token=(
                    CapabilityAssistantReentryFailureReason.REINJECTION_RESULT_INCONSISTENT.value
                ),
            )
            return _build_result(
                request,
                outcome_token=CapabilityAssistantReentryOutcome.FAILED_CLOSED.value,
                failure_reason_token=(
                    CapabilityAssistantReentryFailureReason.REINJECTION_RESULT_INCONSISTENT.value
                ),
                continuation_payload=continuation,
            )
        continuation = _continuation_payload_from_reinjection(
            request,
            outcome_token=CapabilityAssistantReentryOutcome.SUCCESS.value,
        )
        return _build_result(
            request,
            outcome_token=CapabilityAssistantReentryOutcome.SUCCESS.value,
            continuation_payload=continuation,
        )

    if (
        result_shape
        == CapabilityReinjectionResultShape.NORMALIZED_FAILURE.value
    ):
        continuation = _continuation_payload_from_reinjection(
            request,
            outcome_token=CapabilityAssistantReentryOutcome.FAILURE.value,
        )
        return _build_result(
            request,
            outcome_token=CapabilityAssistantReentryOutcome.FAILURE.value,
            continuation_payload=continuation,
        )

    continuation = _continuation_payload_from_reinjection(
        request,
        outcome_token=CapabilityAssistantReentryOutcome.FAILED_CLOSED.value,
        failure_reason_token=(
            CapabilityAssistantReentryFailureReason.REINJECTION_RESULT_INCONSISTENT.value
        ),
    )
    return _build_result(
        request,
        outcome_token=CapabilityAssistantReentryOutcome.FAILED_CLOSED.value,
        failure_reason_token=(
            CapabilityAssistantReentryFailureReason.REINJECTION_RESULT_INCONSISTENT.value
        ),
        continuation_payload=continuation,
    )


def reentry_from_successful_reinjection(
    *,
    account_id: str,
    reinjection_result: CapabilityResultReinjectionResult | Mapping[str, Any],
) -> CapabilityAssistantReentryResult:
    """Convert one successful reinjection result into an assistant continuation payload.

    The seam requires explicit owner/account identity, preserves proposal / registry /
    binding / manual-dispatch / command-bus / reinjection traceability, and produces
    a deterministic normalized output. It does not call the command bus or a provider.

    Args:
        account_id: The explicit owner account identity.
        reinjection_result: One completed reinjection result (from a prior
            reinject_successful_manual_capability_dispatch_result call).

    Returns:
        A CapabilityAssistantReentryResult with one CapabilityAssistantContinuationPayload.
        On owner mismatch or inconsistent reinjection provenance, returns a
        failed_closed result with an explicit failure reason.
    """
    request = _build_request(
        account_id=account_id,
        reinjection_result=reinjection_result,
    )
    return _normalize_reinjection_for_reentry(request=request)


def reentry_from_failed_reinjection(
    *,
    account_id: str,
    reinjection_result: CapabilityResultReinjectionResult | Mapping[str, Any],
) -> CapabilityAssistantReentryResult:
    """Convert one failed reinjection result into an assistant continuation payload.

    The seam requires explicit owner/account identity, preserves proposal / registry /
    binding / manual-dispatch / command-bus / reinjection traceability, and produces
    a deterministic normalized output. It does not call the command bus or a provider.

    Args:
        account_id: The explicit owner account identity.
        reinjection_result: One completed reinjection result (from a prior
            reinject_failed_manual_capability_dispatch_result call).

    Returns:
        A CapabilityAssistantReentryResult with one CapabilityAssistantContinuationPayload
        carrying the bounded failure classification. On owner mismatch or inconsistent
        reinjection provenance, returns a failed_closed result with an explicit failure reason.
    """
    request = _build_request(
        account_id=account_id,
        reinjection_result=reinjection_result,
    )
    return _normalize_reinjection_for_reentry(request=request)


def reentry_from_reinjection_result(
    *,
    account_id: str,
    reinjection_result: CapabilityResultReinjectionResult | Mapping[str, Any],
) -> CapabilityAssistantReentryResult:
    """Convert one reinjection result (success or failure) into an assistant continuation.

    This is the general entry point that handles both successful and failed reinjection
    results. It requires explicit owner/account identity, preserves proposal / registry /
    binding / manual-dispatch / command-bus / reinjection traceability, and produces
    a deterministic normalized output. It does not call the command bus or a provider.

    If the reinjection result is ambiguous, incomplete, or inconsistent with its
    provenance chain, this returns a failed_closed result with an explicit reentry
    failure reason rather than guessing.

    Args:
        account_id: The explicit owner account identity.
        reinjection_result: One completed reinjection result (from any of the
            reinjection helpers).

    Returns:
        A CapabilityAssistantReentryResult with exactly one
        CapabilityAssistantContinuationPayload. On inconsistent provenance or
        owner mismatch, returns failed_closed with an explicit failure reason.
    """
    request = _build_request(
        account_id=account_id,
        reinjection_result=reinjection_result,
    )
    return _normalize_reinjection_for_reentry(request=request)


__all__ = [
    "reentry_from_successful_reinjection",
    "reentry_from_failed_reinjection",
    "reentry_from_reinjection_result",
]
