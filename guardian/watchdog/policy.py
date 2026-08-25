"""Pure, local Watchdog automated-review policy resolution."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from guardian.core.egress import EgressDeniedError, assert_egress_allowed
from guardian.core.provider_registry import (
    normalize_model_id,
    normalize_provider,
    provider_governance,
)
from guardian.watchdog.contracts import (
    WatchdogEscalationMode,
    WatchdogModelSelectionSource,
    WatchdogOperation,
    WatchdogPolicyBlockReason,
    WatchdogPolicyResolutionState,
)


@dataclass(frozen=True)
class WatchdogPolicySnapshot:
    """Immutable system-default policy decision for one review attempt."""

    operation: str
    provider_id: str | None
    model_id: str | None
    inference_mode: str | None
    model_selection_source: str
    escalation_mode: str
    escalation_provider_id: str | None
    escalation_model_id: str | None
    policy_resolution_state: str
    policy_reason_code: str | None
    policy_fingerprint: str


def resolve_automated_review_policy(
    settings: Any,
) -> WatchdogPolicySnapshot:
    """Resolve the sole active Watchdog precedence level without I/O."""
    operation = WatchdogOperation.AUTOMATED_REVIEW.value
    selection_source = WatchdogModelSelectionSource.SYSTEM_DEFAULT.value
    configured_provider = _clean_text(
        getattr(
            settings,
            "CODEXIFY_GITHUB_WATCHDOG_AUTOMATED_REVIEW_PROVIDER",
            None,
        )
    )
    configured_model = normalize_model_id(
        getattr(
            settings,
            "CODEXIFY_GITHUB_WATCHDOG_AUTOMATED_REVIEW_MODEL",
            None,
        )
    )
    inference_mode = _clean_text(
        getattr(
            settings,
            "CODEXIFY_GITHUB_WATCHDOG_AUTOMATED_REVIEW_INFERENCE_MODE",
            None,
        )
    )
    escalation_mode, escalation_provider_id, escalation_model_id, escalation_error = (
        _resolve_escalation_configuration(settings)
    )

    provider_id = (
        normalize_provider(configured_provider) if configured_provider else None
    )
    snapshot = _snapshot(
        operation=operation,
        provider_id=provider_id,
        model_id=configured_model or None,
        inference_mode=inference_mode,
        selection_source=selection_source,
        escalation_mode=escalation_mode,
        escalation_provider_id=escalation_provider_id,
        escalation_model_id=escalation_model_id,
        resolution_state=WatchdogPolicyResolutionState.RESOLVED,
        reason_code=None,
    )

    if escalation_error is not None:
        return _blocked(snapshot, escalation_error)
    if provider_id is None:
        return _blocked(snapshot, WatchdogPolicyBlockReason.CONFIGURATION_MISSING)
    if not configured_model:
        return _blocked(snapshot, WatchdogPolicyBlockReason.MODEL_MISSING)

    try:
        governance = provider_governance(provider_id)
    except ValueError:
        return _blocked(snapshot, WatchdogPolicyBlockReason.PROVIDER_UNKNOWN)

    if governance["governance_classification"] == "disabled":
        return _blocked(
            snapshot, WatchdogPolicyBlockReason.PROVIDER_GOVERNANCE_DISABLED
        )

    if not bool(governance["local_only"]):
        try:
            assert_egress_allowed(provider_id, settings=settings)
        except EgressDeniedError:
            return _blocked(snapshot, _cloud_block_reason(settings))
        if not bool(getattr(settings, "ALLOW_CLOUD_PROVIDERS", False)):
            return _blocked(
                snapshot,
                WatchdogPolicyBlockReason.CLOUD_PROVIDERS_DISABLED,
            )

    return snapshot


def block_policy_for_missing_head_sha(
    snapshot: WatchdogPolicySnapshot,
) -> WatchdogPolicySnapshot:
    """Represent an immutable-source failure without making a runnable attempt."""
    return _blocked(snapshot, WatchdogPolicyBlockReason.HEAD_SHA_MISSING)


def _resolve_escalation_configuration(
    settings: Any,
) -> tuple[str, str | None, str | None, WatchdogPolicyBlockReason | None]:
    raw_mode = _clean_text(
        getattr(
            settings,
            "CODEXIFY_GITHUB_WATCHDOG_AUTOMATED_REVIEW_ESCALATION_MODE",
            None,
        )
    )
    mode = raw_mode or WatchdogEscalationMode.DISABLED.value
    if mode not in {
        WatchdogEscalationMode.DISABLED.value,
        WatchdogEscalationMode.EXPLICIT_ONLY.value,
    }:
        return (
            WatchdogEscalationMode.DISABLED.value,
            None,
            None,
            WatchdogPolicyBlockReason.CONFIGURATION_MISSING,
        )
    if mode == WatchdogEscalationMode.DISABLED.value:
        return mode, None, None, None

    provider_id = _clean_text(
        getattr(
            settings,
            "CODEXIFY_GITHUB_WATCHDOG_AUTOMATED_REVIEW_ESCALATION_PROVIDER",
            None,
        )
    )
    model_id = normalize_model_id(
        getattr(
            settings,
            "CODEXIFY_GITHUB_WATCHDOG_AUTOMATED_REVIEW_ESCALATION_MODEL",
            None,
        )
    )
    if not provider_id or not model_id:
        return (
            mode,
            normalize_provider(provider_id) if provider_id else None,
            model_id or None,
            WatchdogPolicyBlockReason.CONFIGURATION_MISSING,
        )
    return mode, normalize_provider(provider_id), model_id, None


def _cloud_block_reason(settings: Any) -> WatchdogPolicyBlockReason:
    if bool(getattr(settings, "CODEXIFY_LOCAL_ONLY_MODE", True)):
        return WatchdogPolicyBlockReason.LOCAL_ONLY_MODE_FORBIDS_CLOUD
    if not bool(getattr(settings, "ALLOW_CLOUD_PROVIDERS", False)):
        return WatchdogPolicyBlockReason.CLOUD_PROVIDERS_DISABLED
    return WatchdogPolicyBlockReason.EGRESS_POLICY_FORBIDS_PROVIDER


def _blocked(
    snapshot: WatchdogPolicySnapshot,
    reason: WatchdogPolicyBlockReason,
) -> WatchdogPolicySnapshot:
    return _snapshot(
        operation=snapshot.operation,
        provider_id=snapshot.provider_id,
        model_id=snapshot.model_id,
        inference_mode=snapshot.inference_mode,
        selection_source=snapshot.model_selection_source,
        escalation_mode=snapshot.escalation_mode,
        escalation_provider_id=snapshot.escalation_provider_id,
        escalation_model_id=snapshot.escalation_model_id,
        resolution_state=WatchdogPolicyResolutionState.BLOCKED,
        reason_code=reason.value,
    )


def _snapshot(
    *,
    operation: str,
    provider_id: str | None,
    model_id: str | None,
    inference_mode: str | None,
    selection_source: str,
    escalation_mode: str,
    escalation_provider_id: str | None,
    escalation_model_id: str | None,
    resolution_state: WatchdogPolicyResolutionState,
    reason_code: str | None,
) -> WatchdogPolicySnapshot:
    fingerprint_material = {
        "escalation_mode": escalation_mode,
        "escalation_model_id": escalation_model_id,
        "escalation_provider_id": escalation_provider_id,
        "inference_mode": inference_mode,
        "model_id": model_id,
        "operation": operation,
        "provider_id": provider_id,
        "resolution_state": resolution_state.value,
        "reason_code": reason_code,
        "selection_source": selection_source,
    }
    encoded = json.dumps(
        fingerprint_material, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return WatchdogPolicySnapshot(
        operation=operation,
        provider_id=provider_id,
        model_id=model_id,
        inference_mode=inference_mode,
        model_selection_source=selection_source,
        escalation_mode=escalation_mode,
        escalation_provider_id=escalation_provider_id,
        escalation_model_id=escalation_model_id,
        policy_resolution_state=resolution_state.value,
        policy_reason_code=reason_code,
        policy_fingerprint=hashlib.sha256(encoded).hexdigest(),
    )


def _clean_text(value: object) -> str | None:
    clean = str(value or "").strip()
    return clean or None
