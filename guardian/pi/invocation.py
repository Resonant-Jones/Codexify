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
_NON_SECRET_AUTHORITY_KEYS = frozenset({"authorization_digest"})
_GIT_TIMEOUT_SECONDS = 5


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
    granted_permissions: tuple[PiPermissionGrant, ...]
    authorization_digest: str

    @property
    def read_only(self) -> bool:
        """Compatibility view; authority remains the structural grant set."""
        return not any(
            permission.permission == "files.write"
            for permission in self.granted_permissions
        )


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
    receipt: PiInvocationReceipt | None = None
    harness_result: PiHarnessResult | None = None
    actual_identity: PiAuthorizedExecutionIdentity | None = None


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
            _authorization_failure_reason(authorization.failure_reasons),
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
        granted_permissions=envelope.granted_permissions,
        authorization_digest=decision.authorization_digest,
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
        return _blocked(state_failure, runner_call_count=1)
    if runner_failed or evidence is None:
        return _blocked(
            PiValidationFailureReason.ADAPTER_EXECUTION_FAILURE,
            runner_call_count=1,
        )
    if str(evidence.status).strip().lower() not in _SUCCESS_STATUSES:
        return _blocked(
            PiValidationFailureReason.ADAPTER_EXECUTION_FAILURE,
            runner_call_count=1,
        )

    actual_identity, actual_failure = _actual_identity(evidence)
    if actual_failure is not None:
        return _blocked(actual_failure, runner_call_count=1)
    assert actual_identity is not None
    identity_failure = _validate_actual_identity(identity, actual_identity)
    if identity_failure is not None:
        return _blocked(identity_failure, runner_call_count=1)

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
        granted_permissions=request.granted_permissions,
        authorization_digest=request.authorization_digest,
    )
    return PiHarnessRuntimeEvidence(
        status=result.status,
        actual_provider_id=result.actual_provider_id,
        actual_model_id=result.actual_model_id,
        actual_harness_id=result.actual_harness_id,
        actual_harness_version=result.actual_harness_version,
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
            if key_text not in _NON_SECRET_AUTHORITY_KEYS and (
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
) -> PiLiveInvocationOutcome:
    return PiLiveInvocationOutcome(
        ok=False,
        failure_reason=reason.value,
        runner_call_count=runner_call_count,
        retry_count=0,
        fallback_count=0,
    )


def _authorization_failure_reason(
    failure_reasons: tuple[str, ...],
) -> PiValidationFailureReason:
    """Preserve canonical missing-identity failures instead of flattening them."""
    for reason in (
        PiValidationFailureReason.MISSING_HARNESS_ID,
        PiValidationFailureReason.MISSING_HARNESS_VERSION,
        PiValidationFailureReason.MISSING_PROVIDER_ID,
        PiValidationFailureReason.MISSING_MODEL_ID,
        PiValidationFailureReason.MISSING_AUTHORIZATION_BINDING,
        PiValidationFailureReason.AUTHORIZATION_BINDING_MISMATCH,
    ):
        if reason.value in failure_reasons:
            return reason
    return PiValidationFailureReason.POLICY_ENVELOPE_MISMATCH


__all__ = [
    "PiAuthorizedExecutionIdentity",
    "PiAuthorizedHarnessRequest",
    "PiAuthorizedHarnessRunner",
    "PiHarnessRuntimeEvidence",
    "PiLiveInvocationOutcome",
    "invoke_guardian_authorized_pi",
]
