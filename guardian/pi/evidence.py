"""Pure adapter: maps dry-run route response to Pi/Coder operator evidence.

This module is intentionally dependency-light and does NOT:
  - call the dry-run route
  - perform I/O (network, database, filesystem)
  - execute adapters/providers
  - call _store or _event_publisher
  - create receipts, artifacts, or completion verdicts
"""

from __future__ import annotations

from typing import Any, Mapping

from guardian.pi.contracts import (
    PiGuardianBoundary,
    PiInvocationOperatorEvidence,
)

FORBIDDEN_RESPONSE_KEYS = frozenset({
    "raw_args", "extra_meta", "result_json", "hidden_prompt",
    "system_prompt", "raw_diff", "raw_patch", "raw_payload",
    "raw_result", "raw_event_payload", "stack_trace", "traceback",
    "secret", "credential", "api_key", "token", "password",
    "private_key", "chain_of_thought", "completion_verdict",
    "receipt", "artifact",
})


def build_operator_evidence_from_dry_run_response(
    *,
    response: Mapping[str, Any] | None,
    safe_invocation_id: str | None = None,
    safe_source_thread_id: str | None = None,
    safe_source_message_id: str | None = None,
    safe_harness_id: str | None = None,
) -> PiInvocationOperatorEvidence:
    """Map a dry-run route response to PiInvocationOperatorEvidence.

    Derives a deterministic evidence state from the response. The adapter
    is pure — no I/O, no side effects.
    """
    if response is None:
        return _unavailable_evidence(
            safe_invocation_id,
            safe_source_thread_id,
            safe_source_message_id,
            safe_harness_id,
            reason="No dry-run response available",
        )

    # Extract safe fields
    accepted = bool(response.get("accepted", False))
    dry_run = bool(response.get("dry_run", True))
    execution_performed = bool(response.get("execution_performed", False))
    persistence_performed = bool(response.get("persistence_performed", False))
    release_support = str(response.get("release_support", "unsupported"))
    validation_status = str(response.get("validation_status", ""))
    errors = _safe_string_list(response.get("errors"))
    warnings = _safe_string_list(response.get("warnings"))
    redaction_state = str(response.get("redaction_state", ""))
    permission_posture = str(response.get("permission_posture", ""))
    invocation_id = safe_invocation_id or str(response.get("invocation_id") or "")
    source_thread_id = safe_source_thread_id or str(response.get("source_thread_id") or "")
    source_message_id = safe_source_message_id or str(response.get("source_message_id") or "")
    harness_id = safe_harness_id or str(response.get("harness_id") or "")

    # Derive evidence state
    evidence_state = _derive_state(
        accepted=accepted,
        execution_performed=execution_performed,
        persistence_performed=persistence_performed,
        release_support=release_support,
        errors=errors,
        response=response,
    )

    # Build safe metadata — filter forbidden keys
    metadata = _safe_metadata(response)

    return PiInvocationOperatorEvidence(
        operator_evidence_id="",
        invocation_id=invocation_id,
        source_thread_id=source_thread_id,
        source_message_id=source_message_id,
        harness_id=harness_id,
        evidence_state=evidence_state,
        policy_decision_summary=_safe_summary(response, "policy_decision_summary"),
        permission_posture=permission_posture,
        guardian_boundary=PiGuardianBoundary(owner_account_id=""),
        validation_status=validation_status,
        redaction_state=redaction_state,
        created_at="",
        result_summary=_safe_summary(response, "result_summary"),
        failure_reason=_failure_reason(errors),
        result_availability="available" if evidence_state == "available" else "not_available",
    )


def _derive_state(
    *,
    accepted: bool,
    execution_performed: bool,
    persistence_performed: bool,
    release_support: str,
    errors: tuple[str, ...],
    response: Mapping[str, Any],
) -> str:
    if execution_performed or persistence_performed:
        return "blocked"
    if release_support != "unsupported":
        return "blocked"
    if not accepted:
        return "validation_failed"
    if errors:
        return "validation_failed"
    # Check for presence of any safe reference or summary
    has_ref = any(
        response.get(k) for k in (
            "invocation_id", "source_thread_id", "source_message_id",
            "harness_id",
        )
    )
    has_summary = any(
        response.get(k) for k in ("result_summary",)
    )
    if has_ref or has_summary:
        return "available"
    return "partial"


def _unavailable_evidence(
    invocation_id: str | None,
    source_thread_id: str | None,
    source_message_id: str | None,
    harness_id: str | None,
    *,
    reason: str,
) -> PiInvocationOperatorEvidence:
    return PiInvocationOperatorEvidence(
        operator_evidence_id="",
        invocation_id=invocation_id or "",
        source_thread_id=source_thread_id or "",
        source_message_id=source_message_id or "",
        harness_id=harness_id or "",
        evidence_state="unavailable",
        policy_decision_summary=reason,
        permission_posture="",
        guardian_boundary=PiGuardianBoundary(owner_account_id=""),
        validation_status="",
        redaction_state="",
        created_at="",
        result_availability="not_available",
    )


def _safe_string_list(value: object) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(str(item) for item in value if str(item).strip())


def _safe_summary(response: Mapping[str, Any], key: str) -> str:
    raw = response.get(key)
    if raw is None:
        return ""
    text = str(raw).strip()
    if len(text) > 2000:
        text = text[:2000]
    return text


def _failure_reason(errors: tuple[str, ...]) -> str | None:
    if not errors:
        return None
    return errors[0] if len(errors) == 1 else "; ".join(errors[:3])


def _safe_metadata(response: Mapping[str, Any]) -> dict[str, Any]:
    """Include only safe metadata keys — filter forbidden keys."""
    result: dict[str, Any] = {}
    for key, value in response.items():
        if key.lower() in FORBIDDEN_RESPONSE_KEYS:
            continue
        if isinstance(value, (str, int, float, bool, type(None))):
            result[key] = value
        elif isinstance(value, (list, tuple)):
            result[key] = [
                item if isinstance(item, (str, int, float, bool, type(None)))
                else str(item)
                for item in value
            ][:10]
    return result


__all__ = [
    "build_operator_evidence_from_dry_run_response",
]
