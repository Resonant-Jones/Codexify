"""Guardian-owned, one-shot invocation rail for the existing Pi harness.

This module deliberately owns no queue, persistence, Campaign Engine state,
FastAPI route, or Coding Worker behavior.  It evaluates immutable Guardian
authorization, invokes one injected or Pi-backed harness, and returns bounded
Pi contract records to its caller without persisting them.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping

from guardian.pi.contracts import (
    PiHarnessResult,
    PiInvocationArtifact,
    PiInvocationEnvelope,
    PiInvocationPolicyDecision,
    PiInvocationReceipt,
    PiPermissionGrant,
    PiProviderLane,
)
from guardian.pi.tokens import (
    PiAuthorizedFailureClass,
    PiHarnessResultClass,
    PiInvocationReceiptStatus,
    PiValidationFailureReason,
)
from guardian.pi.validation import (
    validate_harness_result_against_receipt,
    validate_policy_decision_against_envelope,
    validate_receipt_against_envelope,
)


_SUCCESS_STATUSES = frozenset({"ok", "success", "succeeded", "completed"})
_SENSITIVE_KEY_PARTS = frozenset(
    {
        "api_key",
        "authorization",
        "cookie",
        "credential",
        "password",
        "refresh_token",
        "secret",
        "session",
    }
)
_SENSITIVE_KEY_NAMES = frozenset(
    {
        "access_token",
        "api_token",
        "bearer_token",
        "id_token",
        "token",
    }
)
_GIT_TIMEOUT_SECONDS = 5
_AUTHORIZED_FAILURE_STAGES = frozenset(
    {
        "adapter_execution",
        "authorization",
        "identity_attestation",
        "identity_verification",
        "model_availability",
        "model_resolution",
        "oauth_readiness",
        "preflight",
        "provider_request",
        "provider_resolution",
        "provider_transport",
        "runtime_load",
        "session_initialization",
        "target_posture",
        "wrapper_launch",
        "wrapper_protocol",
    }
)


@dataclass(frozen=True, slots=True)
class PiAuthorizedExecutionIdentity:
    """Identity frozen from a validated envelope and allowed decision."""

    provider_id: str
    model_id: str
    harness_id: str
    harness_version: str


@dataclass(frozen=True, slots=True)
class PiAuthorizedHarnessRequest:
    """The only execution request a Guardian-authorized runner receives."""

    prompt: str
    cwd: Path
    timeout_seconds: int
    identity: PiAuthorizedExecutionIdentity
    read_only: bool


@dataclass(frozen=True, slots=True)
class PiHarnessRuntimeEvidence:
    """Bounded runtime identity returned by the harness itself.

    The invocation rail intentionally accepts no requested identity here.  The
    adapter must populate these values from its resolved runtime result.
    """

    status: str
    actual_provider_id: str | None
    actual_model_id: str | None
    actual_harness_id: str | None
    actual_harness_version: str | None
    failure_classification: str | None = None
    failure_stage: str | None = None
    return_code: int | None = None
    runtime_identity_established: bool = False
    session_initialized: bool | None = None
    provider_request_started: bool | None = None
    oauth_available: bool | None = None


PiAuthorizedHarnessRunner = Callable[
    [PiAuthorizedHarnessRequest], PiHarnessRuntimeEvidence
]


@dataclass(frozen=True, slots=True)
class PiLiveInvocationOutcome:
    """Terminal, non-persisted result for exactly one invocation attempt."""

    ok: bool
    failure_reason: str | None
    runner_call_count: int
    retry_count: int
    fallback_count: int
    diagnostic_class: str | None = None
    diagnostic_stage: str | None = None
    return_code: int | None = None
    runtime_identity_established: bool = False
    session_initialized: bool | None = None
    provider_request_started: bool | None = None
    oauth_available: bool | None = None
    receipt: PiInvocationReceipt | None = None
    harness_result: PiHarnessResult | None = None
    actual_identity: PiAuthorizedExecutionIdentity | None = None


@dataclass(frozen=True, slots=True)
class PiAuthorizedPreflightOutcome:
    """Non-inference result for the authorized Pi setup/readiness boundary."""

    ok: bool
    failure_class: str | None
    failure_stage: str | None
    deepest_stage: str | None
    preflight_call_count: int
    retry_count: int
    fallback_count: int
    actual_identity: PiAuthorizedExecutionIdentity | None = None
    runtime_identity_established: bool = False
    oauth_available: bool | None = None
    session_initialized: bool = False
    provider_request_started: bool = False


@dataclass(frozen=True, slots=True)
class _TargetSnapshot:
    entries: tuple[tuple[str, str], ...]
    git_head: str | None


def invoke_guardian_authorized_pi(
    *,
    envelope: PiInvocationEnvelope,
    decision: PiInvocationPolicyDecision,
    prompt: str,
    cwd: str | Path,
    timeout_seconds: int,
    harness_runner: PiAuthorizedHarnessRunner | None = None,
) -> PiLiveInvocationOutcome:
    """Authorize and invoke one Pi harness call without durable side effects.

    The function never retries, falls back, repairs a target, or writes a
    receipt/result to a database, queue, store, or Campaign Engine artifact.
    """
    authorization = validate_policy_decision_against_envelope(envelope, decision)
    if not authorization.ok:
        return _blocked(
            PiValidationFailureReason.POLICY_ENVELOPE_MISMATCH,
            runner_call_count=0,
        )
    if decision.decision != "allowed":
        return _blocked(
            PiValidationFailureReason.AUTHORIZATION_DENIED,
            runner_call_count=0,
        )
    if _contains_sensitive_keys(envelope.to_payload()) or _contains_sensitive_keys(
        decision.to_payload()
    ):
        return _blocked(
            PiValidationFailureReason.CREDENTIAL_MATERIAL_REJECTED,
            runner_call_count=0,
        )

    identity, identity_failure = _authorized_identity(envelope)
    if identity_failure is not None:
        return _blocked(identity_failure, runner_call_count=0)
    assert identity is not None

    target = Path(cwd).expanduser().resolve(strict=False)
    if not target.is_dir():
        return _blocked(
            PiValidationFailureReason.MUTATION_SCOPE_VIOLATION,
            runner_call_count=0,
        )
    write_roots, scope_failure = _granted_write_roots(envelope, target)
    if scope_failure is not None:
        return _blocked(scope_failure, runner_call_count=0)

    pre_execution = _snapshot_target(target)
    request = PiAuthorizedHarnessRequest(
        prompt=str(prompt),
        cwd=target,
        timeout_seconds=max(1, int(timeout_seconds)),
        identity=identity,
        read_only=not write_roots,
    )
    runner = harness_runner or _run_with_pi_adapter
    evidence: PiHarnessRuntimeEvidence | None = None
    runner_failed = False
    try:
        evidence = runner(request)
    except Exception:
        runner_failed = True
    post_execution = _snapshot_target(target)
    state_failure = _enforce_target_posture(
        target=target,
        pre_execution=pre_execution,
        post_execution=post_execution,
        write_roots=write_roots,
    )
    if state_failure is not None:
        return _blocked(
            state_failure,
            runner_call_count=1,
            diagnostic_class=PiAuthorizedFailureClass.TARGET_POSTURE_VIOLATION.value,
            diagnostic_stage="target_posture",
        )
    if runner_failed or evidence is None:
        return _adapter_blocked(
            PiValidationFailureReason.ADAPTER_EXECUTION_FAILURE,
            diagnostic_class=PiAuthorizedFailureClass.UNKNOWN_ADAPTER_FAILURE.value,
            runner_call_count=1,
        )
    if str(evidence.status).strip().lower() not in _SUCCESS_STATUSES:
        return _adapter_blocked(
            PiValidationFailureReason.ADAPTER_EXECUTION_FAILURE,
            diagnostic_class=_safe_failure_class(evidence.failure_classification),
            diagnostic_stage=evidence.failure_stage,
            return_code=evidence.return_code,
            runtime_identity_established=evidence.runtime_identity_established,
            session_initialized=evidence.session_initialized,
            provider_request_started=evidence.provider_request_started,
            runner_call_count=1,
        )

    actual_identity, actual_failure = _actual_identity(evidence)
    if actual_failure is not None:
        return _blocked(
            actual_failure,
            runner_call_count=1,
            diagnostic_class=PiAuthorizedFailureClass.ACTUAL_IDENTITY_MISSING.value,
        )
    assert actual_identity is not None
    identity_failure = _validate_actual_identity(identity, actual_identity)
    if identity_failure is not None:
        return _blocked(
            identity_failure,
            runner_call_count=1,
            diagnostic_class=PiAuthorizedFailureClass.AUTHORIZED_IDENTITY_REJECTED.value,
        )

    artifact_ref = f"pi://guardian-authorized/{envelope.invocation_id}/result"
    receipt = PiInvocationReceipt(
        receipt_id=f"pi-receipt-{envelope.invocation_id}",
        guardian_boundary=envelope.guardian_boundary,
        source_thread_id=envelope.source_thread_id,
        source_message_id=envelope.source_message_id,
        authored_request_id=envelope.authored_request_id,
        attempt_id=envelope.attempt_id,
        invocation_id=envelope.invocation_id,
        harness_id=envelope.harness_id,
        harness_version=envelope.harness_version,
        provider_lane=envelope.provider_lane,
        requested_permissions=envelope.requested_permissions,
        granted_permissions=envelope.granted_permissions,
        command_bus_linkage=envelope.command_bus_linkage,
        result_artifact_ref=artifact_ref,
        receipt_status=PiInvocationReceiptStatus.COMPLETED.value,
        validation_metadata={
            "guardian_authorized": True,
            "policy_decision_id": decision.policy_decision_id,
        },
    )
    receipt_validation = validate_receipt_against_envelope(envelope, receipt)
    if not receipt_validation.ok:
        return _blocked(
            PiValidationFailureReason.HARNESS_RESULT_MISMATCH,
            runner_call_count=1,
        )

    actual_lane = PiProviderLane(
        provider_lane_class=envelope.provider_lane.provider_lane_class,
        provider_name=actual_identity.provider_id,
        model_id=actual_identity.model_id,
        metadata=envelope.provider_lane.metadata,
    )
    harness_result = PiHarnessResult(
        harness_result_id=f"pi-result-{envelope.invocation_id}",
        receipt_id=receipt.receipt_id,
        guardian_boundary=envelope.guardian_boundary,
        source_thread_id=envelope.source_thread_id,
        source_message_id=envelope.source_message_id,
        authored_request_id=envelope.authored_request_id,
        attempt_id=envelope.attempt_id,
        invocation_id=envelope.invocation_id,
        harness_id=actual_identity.harness_id,
        harness_version=actual_identity.harness_version,
        provider_lane=actual_lane,
        requested_permissions=envelope.requested_permissions,
        granted_permissions=envelope.granted_permissions,
        command_bus_linkage=envelope.command_bus_linkage,
        artifact=PiInvocationArtifact(
            artifact_id=f"pi-artifact-{envelope.invocation_id}",
            artifact_ref=artifact_ref,
            artifact_class="bounded_result",
        ),
        result_class=PiHarnessResultClass.SUCCESS.value,
        validation_metadata={"actual_runtime_identity_attested": True},
    )
    result_validation = validate_harness_result_against_receipt(receipt, harness_result)
    if not result_validation.ok:
        return _blocked(
            PiValidationFailureReason.HARNESS_RESULT_MISMATCH,
            runner_call_count=1,
        )
    return PiLiveInvocationOutcome(
        ok=True,
        failure_reason=None,
        runner_call_count=1,
        retry_count=0,
        fallback_count=0,
        runtime_identity_established=True,
        session_initialized=evidence.session_initialized,
        provider_request_started=evidence.provider_request_started,
        oauth_available=evidence.oauth_available,
        receipt=receipt,
        harness_result=harness_result,
        actual_identity=actual_identity,
    )


def _run_with_pi_adapter(
    request: PiAuthorizedHarnessRequest,
) -> PiHarnessRuntimeEvidence:
    """Bridge the typed Guardian request to the approved opt-in Pi adapter."""
    from guardian.agents.adapters.base import (
        AgentExecutionIdentity,
        AgentExecutionRequest,
    )
    from guardian.agents.adapters.pi_codex_runner import PiCodexRunnerAdapter

    result = PiCodexRunnerAdapter().execute_authorized(
        AgentExecutionRequest(
            prompt=request.prompt,
            cwd=str(request.cwd),
            timeout_seconds=request.timeout_seconds,
        ),
        AgentExecutionIdentity(
            provider_id=request.identity.provider_id,
            model_id=request.identity.model_id,
            harness_id=request.identity.harness_id,
            harness_version=request.identity.harness_version,
        ),
        read_only=request.read_only,
    )
    return PiHarnessRuntimeEvidence(
        status=result.status,
        actual_provider_id=result.actual_provider_id,
        actual_model_id=result.actual_model_id,
        actual_harness_id=result.actual_harness_id,
        actual_harness_version=result.actual_harness_version,
        failure_classification=result.failure_classification,
        failure_stage=result.failure_stage,
        return_code=result.return_code,
        runtime_identity_established=result.runtime_identity_established,
        session_initialized=result.session_initialized,
        provider_request_started=result.provider_request_started,
        oauth_available=result.oauth_available,
    )


def preflight_guardian_authorized_pi(
    *,
    envelope: PiInvocationEnvelope,
    decision: PiInvocationPolicyDecision,
    cwd: str | Path,
    timeout_seconds: int,
    preflight_runner: PiAuthorizedHarnessRunner | None = None,
) -> PiAuthorizedPreflightOutcome:
    """Exercise authorized runtime/provider/model/auth setup without prompting."""
    authorization = validate_policy_decision_against_envelope(envelope, decision)
    if not authorization.ok or decision.decision != "allowed":
        return _preflight_blocked(
            PiAuthorizedFailureClass.AUTHORIZED_IDENTITY_REJECTED.value
            if authorization.ok
            else PiAuthorizedFailureClass.UNKNOWN_ADAPTER_FAILURE.value,
            stage="authorization",
        )
    if _contains_sensitive_keys(envelope.to_payload()) or _contains_sensitive_keys(
        decision.to_payload()
    ):
        return _preflight_blocked(
            PiAuthorizedFailureClass.AUTHORIZED_IDENTITY_REJECTED.value,
            stage="authorization",
        )
    identity, identity_failure = _authorized_identity(envelope)
    if identity_failure is not None or identity is None:
        return _preflight_blocked(
            PiAuthorizedFailureClass.AUTHORIZED_IDENTITY_REJECTED.value,
            stage="authorization",
        )
    target = Path(cwd).expanduser().resolve(strict=False)
    if not target.is_dir():
        return _preflight_blocked(
            PiAuthorizedFailureClass.TARGET_POSTURE_VIOLATION.value,
            stage="target_posture",
        )

    request = PiAuthorizedHarnessRequest(
        prompt="",
        cwd=target,
        timeout_seconds=max(1, int(timeout_seconds)),
        identity=identity,
        read_only=True,
    )
    runner = preflight_runner or _run_preflight_with_pi_adapter
    try:
        evidence = runner(request)
    except Exception:
        return _preflight_blocked(
            PiAuthorizedFailureClass.UNKNOWN_ADAPTER_FAILURE.value,
            stage="preflight",
        )
    if str(evidence.status).strip().lower() not in _SUCCESS_STATUSES:
        return _preflight_blocked(
            _safe_failure_class(evidence.failure_classification),
            stage=_safe_stage(evidence.failure_stage) or "preflight",
            actual_identity=_identity_from_evidence(evidence),
            runtime_identity_established=evidence.runtime_identity_established,
            oauth_available=evidence.oauth_available,
        )
    actual_identity = _identity_from_evidence(evidence)
    if actual_identity is None:
        return _preflight_blocked(
            PiAuthorizedFailureClass.ACTUAL_IDENTITY_MISSING.value,
            stage="identity_attestation",
            runtime_identity_established=False,
            oauth_available=evidence.oauth_available,
        )
    identity_failure = _validate_actual_identity(identity, actual_identity)
    if identity_failure is not None:
        return _preflight_blocked(
            PiAuthorizedFailureClass.AUTHORIZED_IDENTITY_REJECTED.value,
            stage="identity_verification",
            actual_identity=actual_identity,
            runtime_identity_established=True,
            oauth_available=evidence.oauth_available,
        )
    deepest_stage = "identity_verified"
    if evidence.oauth_available:
        deepest_stage = "auth_available"
    return PiAuthorizedPreflightOutcome(
        ok=True,
        failure_class=None,
        failure_stage=None,
        deepest_stage=deepest_stage,
        preflight_call_count=1,
        retry_count=0,
        fallback_count=0,
        actual_identity=actual_identity,
        runtime_identity_established=True,
        oauth_available=evidence.oauth_available,
        session_initialized=False,
        provider_request_started=False,
    )


def _run_preflight_with_pi_adapter(
    request: PiAuthorizedHarnessRequest,
) -> PiHarnessRuntimeEvidence:
    from guardian.agents.adapters.base import (
        AgentExecutionIdentity,
        AgentExecutionRequest,
    )
    from guardian.agents.adapters.pi_codex_runner import PiCodexRunnerAdapter

    result = PiCodexRunnerAdapter().preflight_authorized(
        AgentExecutionRequest(
            prompt="",
            cwd=str(request.cwd),
            timeout_seconds=request.timeout_seconds,
        ),
        AgentExecutionIdentity(
            provider_id=request.identity.provider_id,
            model_id=request.identity.model_id,
            harness_id=request.identity.harness_id,
            harness_version=request.identity.harness_version,
        ),
    )
    return PiHarnessRuntimeEvidence(
        status=result.status,
        actual_provider_id=result.actual_provider_id,
        actual_model_id=result.actual_model_id,
        actual_harness_id=result.actual_harness_id,
        actual_harness_version=result.actual_harness_version,
        failure_classification=result.failure_classification,
        failure_stage=result.failure_stage,
        return_code=result.return_code,
        runtime_identity_established=result.runtime_identity_established,
        session_initialized=result.session_initialized,
        provider_request_started=result.provider_request_started,
        oauth_available=result.oauth_available,
    )


def _authorized_identity(
    envelope: PiInvocationEnvelope,
) -> tuple[PiAuthorizedExecutionIdentity | None, PiValidationFailureReason | None]:
    provider_id = str(envelope.provider_lane.provider_name or "").strip()
    if not provider_id:
        return None, PiValidationFailureReason.MISSING_PROVIDER_ID
    model_id = str(envelope.provider_lane.model_id or "").strip()
    if not model_id:
        return None, PiValidationFailureReason.MISSING_MODEL_ID
    if not envelope.harness_id:
        return None, PiValidationFailureReason.MISSING_HARNESS_ID
    if not envelope.harness_version:
        return None, PiValidationFailureReason.MISSING_HARNESS_VERSION
    return (
        PiAuthorizedExecutionIdentity(
            provider_id=provider_id,
            model_id=model_id,
            harness_id=envelope.harness_id,
            harness_version=envelope.harness_version,
        ),
        None,
    )


def _actual_identity(
    evidence: PiHarnessRuntimeEvidence,
) -> tuple[PiAuthorizedExecutionIdentity | None, PiValidationFailureReason | None]:
    values = (
        evidence.actual_provider_id,
        evidence.actual_model_id,
        evidence.actual_harness_id,
        evidence.actual_harness_version,
    )
    if any(not str(value or "").strip() for value in values):
        return None, PiValidationFailureReason.ACTUAL_IDENTITY_MISSING
    return (
        PiAuthorizedExecutionIdentity(
            provider_id=str(evidence.actual_provider_id).strip(),
            model_id=str(evidence.actual_model_id).strip(),
            harness_id=str(evidence.actual_harness_id).strip(),
            harness_version=str(evidence.actual_harness_version).strip(),
        ),
        None,
    )


def _identity_from_evidence(
    evidence: PiHarnessRuntimeEvidence,
) -> PiAuthorizedExecutionIdentity | None:
    identity, _failure = _actual_identity(evidence)
    return identity


def _validate_actual_identity(
    authorized: PiAuthorizedExecutionIdentity,
    actual: PiAuthorizedExecutionIdentity,
) -> PiValidationFailureReason | None:
    if actual.provider_id != authorized.provider_id:
        return PiValidationFailureReason.PROVIDER_IDENTITY_MISMATCH
    if actual.model_id != authorized.model_id:
        return PiValidationFailureReason.MODEL_IDENTITY_MISMATCH
    if (
        actual.harness_id != authorized.harness_id
        or actual.harness_version != authorized.harness_version
    ):
        return PiValidationFailureReason.HARNESS_IDENTITY_MISMATCH
    return None


def _granted_write_roots(
    envelope: PiInvocationEnvelope,
    target: Path,
) -> tuple[tuple[Path, ...], PiValidationFailureReason | None]:
    roots: list[Path] = []
    for permission in envelope.granted_permissions:
        if permission.permission != "files.write":
            continue
        if not permission.resource:
            return (), PiValidationFailureReason.MUTATION_SCOPE_VIOLATION
        raw_path = Path(permission.resource)
        candidate = raw_path if raw_path.is_absolute() else target / raw_path
        resolved = candidate.resolve(strict=False)
        if not _inside(resolved, target):
            return (), PiValidationFailureReason.MUTATION_SCOPE_VIOLATION
        roots.append(resolved)
    return tuple(roots), None


def _snapshot_target(target: Path) -> _TargetSnapshot:
    entries: dict[str, str] = {}

    def visit(directory: Path) -> None:
        with os.scandir(directory) as iterator:
            for entry in iterator:
                if directory == target and entry.name == ".git":
                    continue
                path = Path(entry.path)
                relative = path.relative_to(target).as_posix()
                if entry.is_symlink():
                    entries[relative] = f"symlink:{os.readlink(path)}"
                elif entry.is_dir(follow_symlinks=False):
                    entries[relative] = "directory"
                    visit(path)
                elif entry.is_file(follow_symlinks=False):
                    entries[relative] = f"file:{_sha256(path)}"
                else:
                    entries[relative] = "other"

    visit(target)
    return _TargetSnapshot(
        entries=tuple(sorted(entries.items())),
        git_head=_git_head(target),
    )


def _enforce_target_posture(
    *,
    target: Path,
    pre_execution: _TargetSnapshot,
    post_execution: _TargetSnapshot,
    write_roots: tuple[Path, ...],
) -> PiValidationFailureReason | None:
    if pre_execution.git_head != post_execution.git_head:
        return PiValidationFailureReason.GIT_MUTATION_VIOLATION

    before = dict(pre_execution.entries)
    after = dict(post_execution.entries)
    changed_paths = tuple(
        path
        for path in sorted(set(before) | set(after))
        if before.get(path) != after.get(path)
    )
    if not changed_paths:
        return None
    if not write_roots:
        return PiValidationFailureReason.READ_ONLY_VIOLATION
    for relative in changed_paths:
        candidate = target / relative
        if not any(
            _inside(candidate.resolve(strict=False), root) for root in write_roots
        ):
            return PiValidationFailureReason.MUTATION_SCOPE_VIOLATION
        if candidate.is_symlink() and not _inside(
            candidate.resolve(strict=False), target
        ):
            return PiValidationFailureReason.MUTATION_SCOPE_VIOLATION
    return None


def _git_head(target: Path) -> str | None:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=target,
        capture_output=True,
        text=True,
        timeout=_GIT_TIMEOUT_SECONDS,
    )
    if completed.returncode != 0:
        return None
    return completed.stdout.strip() or None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _inside(candidate: Path, root: Path) -> bool:
    try:
        candidate.relative_to(root)
    except ValueError:
        return False
    return True


def _contains_sensitive_keys(value: object) -> bool:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            key_text = str(key).strip().lower()
            if (
                key_text in _SENSITIVE_KEY_NAMES
                or any(part in key_text for part in _SENSITIVE_KEY_PARTS)
            ):
                return True
            if _contains_sensitive_keys(nested):
                return True
    elif isinstance(value, (list, tuple, set, frozenset)):
        return any(_contains_sensitive_keys(item) for item in value)
    return False


def _blocked(
    reason: PiValidationFailureReason,
    *,
    runner_call_count: int,
    diagnostic_class: str | None = None,
    diagnostic_stage: str | None = None,
    return_code: int | None = None,
    runtime_identity_established: bool = False,
    session_initialized: bool | None = None,
    provider_request_started: bool | None = None,
) -> PiLiveInvocationOutcome:
    return PiLiveInvocationOutcome(
        ok=False,
        failure_reason=reason.value,
        runner_call_count=runner_call_count,
        retry_count=0,
        fallback_count=0,
        diagnostic_class=diagnostic_class,
        diagnostic_stage=diagnostic_stage,
        return_code=return_code,
        runtime_identity_established=runtime_identity_established,
        session_initialized=session_initialized,
        provider_request_started=provider_request_started,
    )


def _preflight_blocked(
    failure_class: str,
    *,
    stage: str,
    actual_identity: PiAuthorizedExecutionIdentity | None = None,
    runtime_identity_established: bool = False,
    oauth_available: bool | None = None,
) -> PiAuthorizedPreflightOutcome:
    return PiAuthorizedPreflightOutcome(
        ok=False,
        failure_class=_safe_failure_class(failure_class),
        failure_stage=_safe_stage(stage),
        deepest_stage=(
            "auth_available"
            if oauth_available
            else "identity_verified"
            if runtime_identity_established
            else None
        ),
        preflight_call_count=1,
        retry_count=0,
        fallback_count=0,
        actual_identity=actual_identity,
        runtime_identity_established=runtime_identity_established,
        oauth_available=oauth_available,
        session_initialized=False,
        provider_request_started=False,
    )


def _adapter_blocked(
    reason: PiValidationFailureReason,
    *,
    diagnostic_class: str,
    runner_call_count: int,
    diagnostic_stage: str | None = None,
    return_code: int | None = None,
    runtime_identity_established: bool = False,
    session_initialized: bool | None = None,
    provider_request_started: bool | None = None,
) -> PiLiveInvocationOutcome:
    return _blocked(
        reason,
        runner_call_count=runner_call_count,
        diagnostic_class=_safe_failure_class(diagnostic_class),
        diagnostic_stage=_safe_stage(diagnostic_stage),
        return_code=return_code,
        runtime_identity_established=runtime_identity_established,
        session_initialized=session_initialized,
        provider_request_started=provider_request_started,
    )


def _safe_failure_class(value: str | None) -> str:
    candidate = str(value or "").strip()
    return (
        candidate
        if candidate in {item.value for item in PiAuthorizedFailureClass}
        else PiAuthorizedFailureClass.UNKNOWN_ADAPTER_FAILURE.value
    )


def _safe_stage(value: str | None) -> str | None:
    candidate = str(value or "").strip()
    return candidate if candidate in _AUTHORIZED_FAILURE_STAGES else None


__all__ = [
    "PiAuthorizedExecutionIdentity",
    "PiAuthorizedHarnessRequest",
    "PiAuthorizedHarnessRunner",
    "PiHarnessRuntimeEvidence",
    "PiLiveInvocationOutcome",
    "PiAuthorizedPreflightOutcome",
    "invoke_guardian_authorized_pi",
    "preflight_guardian_authorized_pi",
]
