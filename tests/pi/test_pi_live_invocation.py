from __future__ import annotations

import json
import subprocess
from dataclasses import replace
from pathlib import Path
from typing import Callable

import pytest

import guardian.agents.adapters.pi_codex_runner as pi_codex_runner
from guardian.agents.adapters.base import AgentExecutionIdentity, AgentExecutionRequest
from guardian.agents.adapters.codex import CodexAdapter
from guardian.agents.adapters.pi_codex_runner import PiCodexRunnerAdapter
from guardian.pi.contracts import (
    PiGuardianBoundary,
    PiInvocationEnvelope,
    PiInvocationPolicyDecision,
    PiPermissionGrant,
    PiProviderLane,
)
from guardian.pi.invocation import (
    PiAuthorizedHarnessRequest,
    PiHarnessRuntimeEvidence,
    invoke_guardian_authorized_pi,
)
from guardian.pi.tokens import PiValidationFailureReason
from guardian.pi.validation import (
    validate_harness_result_against_receipt,
    validate_policy_decision_against_envelope,
    validate_receipt_against_envelope,
)


IDENTITY = {
    "provider_id": "openai-codex",
    "model_id": "codex-test-model",
    "harness_id": "pi-coding-agent",
    "harness_version": "0.72.1",
}


def _boundary(account_id: str = "acct-live-invocation") -> PiGuardianBoundary:
    return PiGuardianBoundary(owner_account_id=account_id)


def _read_permission() -> PiPermissionGrant:
    return PiPermissionGrant(
        permission="files.read",
        resource=".",
        reason="inspect the disposable fixture",
    )


def _write_permission(resource: str = "src") -> PiPermissionGrant:
    return PiPermissionGrant(
        permission="files.write",
        resource=resource,
        reason="bounded fixture correction",
    )


def _envelope(
    *,
    boundary: PiGuardianBoundary | None = None,
    invocation_id: str = "invocation-live-001",
    source_thread_id: str = "thread-live-001",
    source_message_id: str = "message-live-001",
    harness_id: str = IDENTITY["harness_id"],
    harness_version: str = IDENTITY["harness_version"],
    provider_id: str = IDENTITY["provider_id"],
    model_id: str = IDENTITY["model_id"],
    requested_permissions: tuple[PiPermissionGrant, ...] | None = None,
    granted_permissions: tuple[PiPermissionGrant, ...] | None = None,
    validation_metadata: dict[str, object] | None = None,
) -> PiInvocationEnvelope:
    requested = requested_permissions or (_read_permission(),)
    granted = granted_permissions if granted_permissions is not None else requested
    return PiInvocationEnvelope(
        guardian_boundary=boundary or _boundary(),
        source_thread_id=source_thread_id,
        source_message_id=source_message_id,
        authored_request_id="request-live-001",
        attempt_id="attempt-live-001",
        invocation_id=invocation_id,
        harness_id=harness_id,
        harness_version=harness_version,
        provider_lane=PiProviderLane(
            provider_lane_class="external",
            provider_name=provider_id,
            model_id=model_id,
            metadata={"lane": "test-only"},
        ),
        requested_permissions=requested,
        granted_permissions=granted,
        status="prepared",
        validation_metadata=validation_metadata or {"fixture": "live-invocation"},
    )


def _decision(
    envelope: PiInvocationEnvelope,
    *,
    decision: str = "allowed",
    boundary: PiGuardianBoundary | None = None,
    invocation_id: str | None = None,
    source_thread_id: str | None = None,
    source_message_id: str | None = None,
    harness_id: str | None = None,
    requested_permissions: tuple[PiPermissionGrant, ...] | None = None,
    granted_permissions: tuple[PiPermissionGrant, ...] | None = None,
) -> PiInvocationPolicyDecision:
    return PiInvocationPolicyDecision(
        policy_decision_id="policy-live-001",
        invocation_id=invocation_id if invocation_id is not None else envelope.invocation_id,
        source_thread_id=(
            source_thread_id
            if source_thread_id is not None
            else envelope.source_thread_id
        ),
        source_message_id=(
            source_message_id
            if source_message_id is not None
            else envelope.source_message_id
        ),
        harness_id=harness_id if harness_id is not None else envelope.harness_id,
        decision=decision,
        guardian_boundary=boundary or envelope.guardian_boundary,
        requested_permissions=(
            requested_permissions
            if requested_permissions is not None
            else envelope.requested_permissions
        ),
        granted_permissions=(
            granted_permissions
            if granted_permissions is not None
            else envelope.granted_permissions
        ),
        permission_posture="bounded",
        policy_source="guardian",
        decision_reason="deterministic test authorization",
        decided_at="2026-08-16T00:00:00Z",
        validation_status="valid",
        redaction_state="clean",
    )


def _evidence(**overrides: str | None) -> PiHarnessRuntimeEvidence:
    return PiHarnessRuntimeEvidence(
        status=str(overrides.get("status", "ok")),
        actual_provider_id=overrides.get("actual_provider_id", IDENTITY["provider_id"]),
        actual_model_id=overrides.get("actual_model_id", IDENTITY["model_id"]),
        actual_harness_id=overrides.get("actual_harness_id", IDENTITY["harness_id"]),
        actual_harness_version=overrides.get(
            "actual_harness_version", IDENTITY["harness_version"]
        ),
    )


class _RecordingRunner:
    def __init__(
        self,
        *,
        evidence: PiHarnessRuntimeEvidence | None = None,
        mutation: Callable[[PiAuthorizedHarnessRequest], None] | None = None,
        raises: bool = False,
    ) -> None:
        self.calls: list[PiAuthorizedHarnessRequest] = []
        self.evidence = evidence or _evidence()
        self.mutation = mutation
        self.raises = raises

    def __call__(self, request: PiAuthorizedHarnessRequest) -> PiHarnessRuntimeEvidence:
        self.calls.append(request)
        if self.mutation is not None:
            self.mutation(request)
        if self.raises:
            raise RuntimeError("controlled runner failure")
        return self.evidence


def _invoke(
    tmp_path: Path,
    runner: _RecordingRunner,
    *,
    envelope: PiInvocationEnvelope | None = None,
    decision: PiInvocationPolicyDecision | None = None,
) -> object:
    envelope = envelope or _envelope()
    decision = decision or _decision(envelope)
    return invoke_guardian_authorized_pi(
        envelope=envelope,
        decision=decision,
        prompt="Perform the bounded fixture task.",
        cwd=tmp_path,
        timeout_seconds=15,
        harness_runner=runner,
    )


def _assert_blocked(outcome: object, reason: PiValidationFailureReason) -> None:
    assert not outcome.ok
    assert outcome.failure_reason == reason.value
    assert outcome.retry_count == 0
    assert outcome.fallback_count == 0


def _fixture_tree(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "function.py").write_text(
        "def deterministic_value():\n    return 'before'\n", encoding="utf-8"
    )
    (tmp_path / "test_function.py").write_text(
        "from src.function import deterministic_value\n", encoding="utf-8"
    )


def _initialize_git_repository(target: Path) -> None:
    for command in (
        ["git", "init", "-q"],
        ["git", "config", "user.email", "pi-test@example.invalid"],
        ["git", "config", "user.name", "Pi Invocation Test"],
        ["git", "add", "."],
        ["git", "commit", "-qm", "fixture baseline"],
    ):
        subprocess.run(command, cwd=target, check=True, capture_output=True, text=True)


def test_invalid_envelope_blocks_before_runner(tmp_path: Path) -> None:
    runner = _RecordingRunner()
    envelope = replace(_envelope(), source_thread_id="")
    outcome = _invoke(tmp_path, runner, envelope=envelope, decision=_decision(envelope))

    _assert_blocked(outcome, PiValidationFailureReason.POLICY_ENVELOPE_MISMATCH)
    assert outcome.runner_call_count == len(runner.calls) == 0


def test_denied_policy_blocks_before_runner(tmp_path: Path) -> None:
    runner = _RecordingRunner()
    envelope = _envelope(granted_permissions=())
    outcome = _invoke(
        tmp_path,
        runner,
        envelope=envelope,
        decision=_decision(envelope, decision="denied", granted_permissions=()),
    )

    _assert_blocked(outcome, PiValidationFailureReason.AUTHORIZATION_DENIED)
    assert outcome.runner_call_count == len(runner.calls) == 0


@pytest.mark.parametrize(
    ("decision_kwargs", "expected_reason"),
    [
        ({"invocation_id": "other-invocation"}, PiValidationFailureReason.POLICY_ENVELOPE_MISMATCH),
        ({"source_thread_id": "other-thread"}, PiValidationFailureReason.POLICY_ENVELOPE_MISMATCH),
        ({"source_message_id": "other-message"}, PiValidationFailureReason.POLICY_ENVELOPE_MISMATCH),
        ({"boundary": _boundary("other-account")}, PiValidationFailureReason.POLICY_ENVELOPE_MISMATCH),
        ({"harness_id": "other-harness"}, PiValidationFailureReason.POLICY_ENVELOPE_MISMATCH),
        (
            {"granted_permissions": (_read_permission(), _write_permission())},
            PiValidationFailureReason.POLICY_ENVELOPE_MISMATCH,
        ),
    ],
)
def test_cross_object_mismatches_block_before_runner(
    tmp_path: Path,
    decision_kwargs: dict[str, object],
    expected_reason: PiValidationFailureReason,
) -> None:
    runner = _RecordingRunner()
    envelope = _envelope()
    outcome = _invoke(
        tmp_path,
        runner,
        envelope=envelope,
        decision=_decision(envelope, **decision_kwargs),
    )

    _assert_blocked(outcome, expected_reason)
    assert outcome.runner_call_count == len(runner.calls) == 0


@pytest.mark.parametrize(
    ("provider_id", "model_id", "expected_reason"),
    [
        ("", IDENTITY["model_id"], PiValidationFailureReason.MISSING_PROVIDER_ID),
        (IDENTITY["provider_id"], "", PiValidationFailureReason.MISSING_MODEL_ID),
    ],
)
def test_missing_explicit_identity_blocks_before_runner(
    tmp_path: Path,
    provider_id: str,
    model_id: str,
    expected_reason: PiValidationFailureReason,
) -> None:
    runner = _RecordingRunner()
    envelope = _envelope(provider_id=provider_id, model_id=model_id)
    outcome = _invoke(tmp_path, runner, envelope=envelope, decision=_decision(envelope))

    _assert_blocked(outcome, expected_reason)
    assert outcome.runner_call_count == len(runner.calls) == 0


def test_credential_named_metadata_is_rejected_before_runner(tmp_path: Path) -> None:
    runner = _RecordingRunner()
    envelope = _envelope(validation_metadata={"api_key": "redacted-for-test"})
    outcome = _invoke(tmp_path, runner, envelope=envelope, decision=_decision(envelope))

    _assert_blocked(outcome, PiValidationFailureReason.CREDENTIAL_MATERIAL_REJECTED)
    assert outcome.runner_call_count == len(runner.calls) == 0


def test_exact_authorized_identity_reaches_single_read_only_runner(tmp_path: Path) -> None:
    _fixture_tree(tmp_path)
    runner = _RecordingRunner()
    outcome = _invoke(tmp_path, runner)

    assert outcome.ok
    assert outcome.runner_call_count == len(runner.calls) == 1
    request = runner.calls[0]
    assert request.identity.provider_id == IDENTITY["provider_id"]
    assert request.identity.model_id == IDENTITY["model_id"]
    assert request.identity.harness_id == IDENTITY["harness_id"]
    assert request.identity.harness_version == IDENTITY["harness_version"]
    assert request.read_only is True
    assert outcome.retry_count == 0
    assert outcome.fallback_count == 0
    assert outcome.receipt is not None
    assert outcome.harness_result is not None
    assert validate_receipt_against_envelope(_envelope(), outcome.receipt).ok
    assert validate_harness_result_against_receipt(
        outcome.receipt, outcome.harness_result
    ).ok


@pytest.mark.parametrize(
    ("evidence_kwargs", "expected_reason"),
    [
        (
            {"actual_provider_id": "different-provider"},
            PiValidationFailureReason.PROVIDER_IDENTITY_MISMATCH,
        ),
        (
            {"actual_model_id": "different-model"},
            PiValidationFailureReason.MODEL_IDENTITY_MISMATCH,
        ),
        (
            {"actual_harness_id": "different-harness"},
            PiValidationFailureReason.HARNESS_IDENTITY_MISMATCH,
        ),
        (
            {"actual_harness_version": "9.9.9"},
            PiValidationFailureReason.HARNESS_IDENTITY_MISMATCH,
        ),
        (
            {"actual_provider_id": None},
            PiValidationFailureReason.ACTUAL_IDENTITY_MISSING,
        ),
    ],
)
def test_actual_identity_mismatch_fails_closed(
    tmp_path: Path,
    evidence_kwargs: dict[str, str | None],
    expected_reason: PiValidationFailureReason,
) -> None:
    runner = _RecordingRunner(evidence=_evidence(**evidence_kwargs))
    outcome = _invoke(tmp_path, runner)

    _assert_blocked(outcome, expected_reason)
    assert outcome.runner_call_count == len(runner.calls) == 1


def test_read_only_mutation_fails_closed(tmp_path: Path) -> None:
    _fixture_tree(tmp_path)
    runner = _RecordingRunner(
        mutation=lambda request: (request.cwd / "src" / "function.py").write_text(
            "mutated", encoding="utf-8"
        )
    )
    outcome = _invoke(tmp_path, runner)

    _assert_blocked(outcome, PiValidationFailureReason.READ_ONLY_VIOLATION)
    assert outcome.runner_call_count == len(runner.calls) == 1


def test_allowed_write_inside_exact_grant_succeeds(tmp_path: Path) -> None:
    _fixture_tree(tmp_path)
    permissions = (_read_permission(), _write_permission("src"))
    envelope = _envelope(
        requested_permissions=permissions,
        granted_permissions=permissions,
    )
    runner = _RecordingRunner(
        mutation=lambda request: (request.cwd / "src" / "function.py").write_text(
            "def deterministic_value():\n    return 'after'\n", encoding="utf-8"
        )
    )
    outcome = _invoke(tmp_path, runner, envelope=envelope, decision=_decision(envelope))

    assert outcome.ok
    assert outcome.runner_call_count == len(runner.calls) == 1
    assert (tmp_path / "src" / "function.py").read_text(encoding="utf-8").endswith(
        "'after'\n"
    )


def test_write_outside_granted_root_fails_closed(tmp_path: Path) -> None:
    _fixture_tree(tmp_path)
    permissions = (_read_permission(), _write_permission("src"))
    envelope = _envelope(
        requested_permissions=permissions,
        granted_permissions=permissions,
    )
    runner = _RecordingRunner(
        mutation=lambda request: (request.cwd / "outside.txt").write_text(
            "outside scope", encoding="utf-8"
        )
    )
    outcome = _invoke(tmp_path, runner, envelope=envelope, decision=_decision(envelope))

    _assert_blocked(outcome, PiValidationFailureReason.MUTATION_SCOPE_VIOLATION)
    assert outcome.runner_call_count == len(runner.calls) == 1


def test_path_traversal_write_grant_blocks_before_runner(tmp_path: Path) -> None:
    _fixture_tree(tmp_path)
    permissions = (_read_permission(), _write_permission("../outside"))
    envelope = _envelope(
        requested_permissions=permissions,
        granted_permissions=permissions,
    )
    runner = _RecordingRunner()
    outcome = _invoke(tmp_path, runner, envelope=envelope, decision=_decision(envelope))

    _assert_blocked(outcome, PiValidationFailureReason.MUTATION_SCOPE_VIOLATION)
    assert outcome.runner_call_count == len(runner.calls) == 0


def test_symlink_escape_fails_closed(tmp_path: Path) -> None:
    _fixture_tree(tmp_path)
    permissions = (_read_permission(), _write_permission("src"))
    envelope = _envelope(
        requested_permissions=permissions,
        granted_permissions=permissions,
    )
    outside = tmp_path.parent / "symlink-escape-target.txt"

    def _create_escape(request: PiAuthorizedHarnessRequest) -> None:
        escape = request.cwd / "src" / "escape"
        escape.symlink_to(outside)
        escape.write_text("outside target", encoding="utf-8")

    runner = _RecordingRunner(mutation=_create_escape)
    outcome = _invoke(tmp_path, runner, envelope=envelope, decision=_decision(envelope))

    _assert_blocked(outcome, PiValidationFailureReason.MUTATION_SCOPE_VIOLATION)
    assert outcome.runner_call_count == len(runner.calls) == 1


def test_git_head_mutation_fails_closed(tmp_path: Path) -> None:
    _fixture_tree(tmp_path)
    _initialize_git_repository(tmp_path)
    permissions = (_read_permission(), _write_permission("src"))
    envelope = _envelope(
        requested_permissions=permissions,
        granted_permissions=permissions,
    )

    def _commit(request: PiAuthorizedHarnessRequest) -> None:
        (request.cwd / "src" / "function.py").write_text("committed mutation", encoding="utf-8")
        subprocess.run(["git", "add", "src/function.py"], cwd=request.cwd, check=True)
        subprocess.run(
            ["git", "commit", "-qm", "unauthorized mutation"],
            cwd=request.cwd,
            check=True,
        )

    runner = _RecordingRunner(mutation=_commit)
    outcome = _invoke(tmp_path, runner, envelope=envelope, decision=_decision(envelope))

    _assert_blocked(outcome, PiValidationFailureReason.GIT_MUTATION_VIOLATION)
    assert outcome.runner_call_count == len(runner.calls) == 1


def test_runner_exception_after_mutation_still_enforces_read_only(tmp_path: Path) -> None:
    _fixture_tree(tmp_path)
    runner = _RecordingRunner(
        mutation=lambda request: (request.cwd / "src" / "function.py").write_text(
            "mutated before error", encoding="utf-8"
        ),
        raises=True,
    )
    outcome = _invoke(tmp_path, runner)

    _assert_blocked(outcome, PiValidationFailureReason.READ_ONLY_VIOLATION)
    assert outcome.runner_call_count == len(runner.calls) == 1


def test_returned_records_do_not_contain_prompt_credentials(tmp_path: Path) -> None:
    runner = _RecordingRunner()
    envelope = _envelope()
    decision = _decision(envelope)
    outcome = invoke_guardian_authorized_pi(
        envelope=envelope,
        decision=decision,
        prompt="Do not retain credential value: test-secret-value-12345",
        cwd=tmp_path,
        timeout_seconds=15,
        harness_runner=runner,
    )

    assert outcome.ok
    payload = json.dumps(
        {
            "receipt": outcome.receipt.to_payload() if outcome.receipt else None,
            "result": outcome.harness_result.to_payload() if outcome.harness_result else None,
        },
        sort_keys=True,
    )
    assert "test-secret-value-12345" not in payload


def test_cross_object_validator_exposes_permission_expansion() -> None:
    envelope = _envelope()
    decision = _decision(
        envelope,
        granted_permissions=(_read_permission(), _write_permission("src")),
    )

    validation = validate_policy_decision_against_envelope(envelope, decision)

    assert not validation.ok
    assert PiValidationFailureReason.PERMISSION_POSTURE_INCONSISTENT.value in validation.failure_reasons


def test_authorized_adapter_uses_invocation_local_identity(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    observed: dict[str, object] = {}

    def _run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        observed["command"] = command
        observed["environment"] = kwargs["env"]
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps(
                {
                    "status": "ok",
                    "summary": "bounded",
                    "actual_runtime_identity": {
                        "actual_provider_id": IDENTITY["provider_id"],
                        "actual_model_id": IDENTITY["model_id"],
                        "actual_harness_id": IDENTITY["harness_id"],
                        "actual_harness_version": IDENTITY["harness_version"],
                    },
                    "tool_telemetry": {
                        "effective_tool_names": ["read", "bash", "edit", "write"],
                        "write_tool_available": True,
                        "tool_execution_start_count": 0,
                        "tool_execution_end_count": 0,
                        "executed_tool_names": [],
                        "assistant_tool_call_count": 0,
                        "assistant_message_count": 1,
                        "assistant_content_block_types": ["text"],
                        "assistant_message_event_types": [
                            "start", "text_start", "text_delta", "text_end", "done",
                        ],
                        "assistant_tool_call_event_count": 0,
                    },
                }
            ),
            stderr="",
        )

    monkeypatch.setattr(pi_codex_runner.subprocess, "run", _run)
    monkeypatch.setenv("PI_PROVIDER", "ambient-provider")
    monkeypatch.setenv("PI_MODEL", "ambient-model")
    result = PiCodexRunnerAdapter().execute_authorized(
        AgentExecutionRequest(prompt="bounded", cwd=str(tmp_path), timeout_seconds=12),
        AgentExecutionIdentity(**IDENTITY),
        read_only=True,
    )

    environment = observed["environment"]
    assert isinstance(environment, dict)
    assert observed["command"][-2] == "guardian-authorized-task"
    assert environment["PI_PROVIDER"] == IDENTITY["provider_id"]
    assert environment["PI_MODEL"] == IDENTITY["model_id"]
    assert environment["PI_GUARDIAN_AUTHORIZED"] == "1"
    assert environment["PI_DISABLE_TOOLS"] == "1"
    assert result.actual_provider_id == IDENTITY["provider_id"]
    assert result.actual_model_id == IDENTITY["model_id"]
    assert result.actual_harness_id == IDENTITY["harness_id"]
    assert result.actual_harness_version == IDENTITY["harness_version"]
    assert result.errors == []
    assert result.status == "ok"
    assert result.summary == "bounded"


def test_legacy_pi_adapter_keeps_task_mode_and_output_shape(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    observed: dict[str, object] = {}

    def _run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        observed["command"] = command
        observed["environment"] = kwargs["env"]
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps({"status": "ok", "summary": "legacy task"}),
            stderr="",
        )

    monkeypatch.setattr(pi_codex_runner.subprocess, "run", _run)
    result = PiCodexRunnerAdapter().execute(
        AgentExecutionRequest(prompt="legacy", cwd=str(tmp_path), timeout_seconds=12)
    )

    assert observed["command"][-2] == "task"
    assert result.status == "ok"
    assert result.summary == "legacy task"
    assert result.actual_provider_id is None
    assert result.actual_model_id is None
    assert result.actual_harness_id is None
    assert result.actual_harness_version is None


def test_direct_codex_adapter_remains_unsupported() -> None:
    with pytest.raises(RuntimeError, match="unsupported"):
        CodexAdapter()


# --- Pi 0.82.1 tool telemetry propagation regressions ---
#
# These tests verify that the bounded Pi 0.82.1 tool telemetry flows from the
# PiHarnessRuntimeEvidence into the PiLiveInvocationOutcome without being
# mutated by Guardian.  No real provider is used.

def _evidence_with_tool_telemetry(
    **telemetry_overrides: object,
) -> PiHarnessRuntimeEvidence:
    import dataclasses
    base = _evidence()
    return dataclasses.replace(
        base,
        effective_tool_names=telemetry_overrides.get(
            "effective_tool_names", ("read", "bash", "edit", "write")
        ),
        write_tool_available=telemetry_overrides.get(
            "write_tool_available", True
        ),
        tool_execution_start_count=telemetry_overrides.get(
            "tool_execution_start_count", 1
        ),
        tool_execution_end_count=telemetry_overrides.get(
            "tool_execution_end_count", 1
        ),
        executed_tool_names=telemetry_overrides.get(
            "executed_tool_names", ("write",)
        ),
        assistant_tool_call_count=telemetry_overrides.get(
            "assistant_tool_call_count", 1
        ),
    )


def test_tool_telemetry_propagates_into_pi_live_invocation_outcome(tmp_path: Path) -> None:
    """Tool telemetry from evidence flows into outcome unchanged."""
    runner = _RecordingRunner(evidence=_evidence_with_tool_telemetry())
    outcome = _invoke(tmp_path, runner)
    assert outcome.ok
    assert outcome.effective_tool_names == (
        "read", "bash", "edit", "write",
    )
    assert outcome.write_tool_available is True
    assert outcome.tool_execution_start_count == 1
    assert outcome.tool_execution_end_count == 1
    assert outcome.executed_tool_names == ("write",)
    assert outcome.assistant_tool_call_count == 1


def test_tool_telemetry_none_propagates_as_none(tmp_path: Path) -> None:
    """Missing telemetry survives as None — no fabrication.

    This is the readiness path: the wrapper does not run a session, so
    no telemetry is emitted.  The adapter does not require telemetry on
    the readiness path; outcome fields are None."""
    runner = _RecordingRunner(evidence=_evidence())
    outcome = _invoke(tmp_path, runner)
    assert outcome.ok
    assert outcome.effective_tool_names is None
    assert outcome.write_tool_available is None
    assert outcome.tool_execution_start_count is None
    assert outcome.tool_execution_end_count is None
    assert outcome.executed_tool_names is None
    assert outcome.assistant_tool_call_count is None


def test_tool_telemetry_into_receipt_validation_metadata(tmp_path: Path) -> None:
    """Pi Receipt and Harness Result carry bounded tool_telemetry metadata."""
    runner = _RecordingRunner(evidence=_evidence_with_tool_telemetry())
    outcome = _invoke(tmp_path, runner)
    assert outcome.ok
    receipt_payload = outcome.receipt.to_payload() if hasattr(outcome.receipt, "to_payload") else {}
    # Receipt stores telemetry under validation_metadata["tool_telemetry"]
    telemetry = receipt_payload.get("validation_metadata", {}).get("tool_telemetry")
    assert telemetry is not None
    assert telemetry.get("effective_tool_names") == [
        "read", "bash", "edit", "write",
    ]
    assert telemetry.get("write_tool_available") is True
    assert telemetry.get("tool_execution_start_count") == 1
    assert telemetry.get("tool_execution_end_count") == 1
    assert telemetry.get("executed_tool_names") == ["write"]
    assert telemetry.get("assistant_tool_call_count") == 1


# --- Pi 0.82.1 assistant-response telemetry propagation regressions (CE-L1
# post-tool-repair observability).  All use the adapter subprocess-mock
# path so the wrapper->adapter telemetry chain is exercised.  No provider
# calls; no prompt execution; no credential access.


def _mock_wrapper_subprocess_assistant(
    monkeypatch: pytest.MonkeyPatch,
    *,
    tool_telemetry=None,
    omit_assistant_fields=(),
):
    """Patch pi_codex_runner.subprocess.run to return a canned wrapper output.

    `tool_telemetry=None` means the wrapper payload has no tool_telemetry
    field at all.  `omit_assistant_fields` is a tuple of names to strip
    from the telemetry dict (e.g. ("assistant_message_count",)).
    """
    payload_telemetry = (
        None if tool_telemetry is None
        else {k: v for k, v in tool_telemetry.items() if k not in omit_assistant_fields}
    )

    def _run(command, **kwargs):
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps(
                {
                    "status": "ok",
                    "summary": "bounded",
                    "actual_runtime_identity": {
                        "actual_provider_id": IDENTITY["provider_id"],
                        "actual_model_id": IDENTITY["model_id"],
                        "actual_harness_id": IDENTITY["harness_id"],
                        "actual_harness_version": IDENTITY["harness_version"],
                    },
                    **({"tool_telemetry": payload_telemetry}
                       if payload_telemetry is not None else {}),
                }
            ),
            stderr="",
        )

    monkeypatch.setattr(pi_codex_runner.subprocess, "run", _run)
    monkeypatch.setenv("PI_PROVIDER", "ambient-provider")
    monkeypatch.setenv("PI_MODEL", "ambient-model")


def _default_assistant_telemetry():
    return {
        "effective_tool_names": ["read", "bash", "edit", "write"],
        "write_tool_available": True,
        "tool_execution_start_count": 0,
        "tool_execution_end_count": 0,
        "executed_tool_names": [],
        "assistant_tool_call_count": 0,
        "assistant_message_count": 1,
        "assistant_content_block_types": ["text"],
        "assistant_message_event_types": [
            "start", "text_start", "text_delta", "text_end", "done",
        ],
        "assistant_tool_call_event_count": 0,
    }


def test_assistant_telemetry_present_propagates_into_adapter(
    monkeypatch, tmp_path,
):
    """All four assistant-response fields propagate through the adapter envelope."""
    _mock_wrapper_subprocess_assistant(
        monkeypatch, tool_telemetry=_default_assistant_telemetry(),
    )
    result = PiCodexRunnerAdapter().execute_authorized(
        AgentExecutionRequest(
            prompt="bounded", cwd=str(tmp_path), timeout_seconds=12,
        ),
        AgentExecutionIdentity(**IDENTITY),
        read_only=True,
    )
    assert result.status == "ok"
    assert result.assistant_message_count == 1
    assert result.assistant_content_block_types == ("text",)
    assert result.assistant_message_event_types == (
        "start", "text_start", "text_delta", "text_end", "done",
    )
    assert result.assistant_tool_call_event_count == 0


def test_assistant_telemetry_missing_assistant_message_count_fails_closed(
    monkeypatch, tmp_path,
):
    """Missing assistant_message_count -> wrapper_protocol_failed."""
    _mock_wrapper_subprocess_assistant(
        monkeypatch,
        tool_telemetry=_default_assistant_telemetry(),
        omit_assistant_fields=("assistant_message_count",),
    )
    result = PiCodexRunnerAdapter().execute_authorized(
        AgentExecutionRequest(
            prompt="bounded", cwd=str(tmp_path), timeout_seconds=12,
        ),
        AgentExecutionIdentity(**IDENTITY),
        read_only=True,
    )
    assert result.status == "error"
    assert result.failure_classification == "wrapper_protocol_failed"
    assert result.failure_stage == "wrapper_protocol"


def test_assistant_telemetry_negative_assistant_message_count_fails_closed(
    monkeypatch, tmp_path,
):
    """Negative assistant_message_count -> wrapper_protocol_failed."""
    tm = _default_assistant_telemetry()
    tm["assistant_message_count"] = -1
    _mock_wrapper_subprocess_assistant(monkeypatch, tool_telemetry=tm)
    result = PiCodexRunnerAdapter().execute_authorized(
        AgentExecutionRequest(
            prompt="bounded", cwd=str(tmp_path), timeout_seconds=12,
        ),
        AgentExecutionIdentity(**IDENTITY),
        read_only=True,
    )
    assert result.status == "error"
    assert result.failure_classification == "wrapper_protocol_failed"


def test_assistant_telemetry_non_string_block_type_member_fails_closed(
    monkeypatch, tmp_path,
):
    """Non-string list member in assistant_content_block_types -> wrapper_protocol_failed."""
    tm = _default_assistant_telemetry()
    tm["assistant_content_block_types"] = ["text", 42]
    _mock_wrapper_subprocess_assistant(monkeypatch, tool_telemetry=tm)
    result = PiCodexRunnerAdapter().execute_authorized(
        AgentExecutionRequest(
            prompt="bounded", cwd=str(tmp_path), timeout_seconds=12,
        ),
        AgentExecutionIdentity(**IDENTITY),
        read_only=True,
    )
    assert result.status == "error"
    assert result.failure_classification == "wrapper_protocol_failed"


def test_assistant_telemetry_non_list_block_types_fails_closed(
    monkeypatch, tmp_path,
):
    """assistant_content_block_types not a list -> wrapper_protocol_failed."""
    tm = _default_assistant_telemetry()
    tm["assistant_content_block_types"] = "not-a-list"
    _mock_wrapper_subprocess_assistant(monkeypatch, tool_telemetry=tm)
    result = PiCodexRunnerAdapter().execute_authorized(
        AgentExecutionRequest(
            prompt="bounded", cwd=str(tmp_path), timeout_seconds=12,
        ),
        AgentExecutionIdentity(**IDENTITY),
        read_only=True,
    )
    assert result.status == "error"
    assert result.failure_classification == "wrapper_protocol_failed"


def test_assistant_telemetry_negative_assistant_tool_call_event_count_fails_closed(
    monkeypatch, tmp_path,
):
    """Negative assistant_tool_call_event_count -> wrapper_protocol_failed."""
    tm = _default_assistant_telemetry()
    tm["assistant_tool_call_event_count"] = -1
    _mock_wrapper_subprocess_assistant(monkeypatch, tool_telemetry=tm)
    result = PiCodexRunnerAdapter().execute_authorized(
        AgentExecutionRequest(
            prompt="bounded", cwd=str(tmp_path), timeout_seconds=12,
        ),
        AgentExecutionIdentity(**IDENTITY),
        read_only=True,
    )
    assert result.status == "error"
    assert result.failure_classification == "wrapper_protocol_failed"


def test_assistant_telemetry_string_event_types_with_invalid_member_fails_closed(
    monkeypatch, tmp_path,
):
    """assistant_message_event_types with non-string entry -> wrapper_protocol_failed."""
    tm = _default_assistant_telemetry()
    tm["assistant_message_event_types"] = ["text_start", None, "text_end"]
    _mock_wrapper_subprocess_assistant(monkeypatch, tool_telemetry=tm)
    result = PiCodexRunnerAdapter().execute_authorized(
        AgentExecutionRequest(
            prompt="bounded", cwd=str(tmp_path), timeout_seconds=12,
        ),
        AgentExecutionIdentity(**IDENTITY),
        read_only=True,
    )
    assert result.status == "error"
    assert result.failure_classification == "wrapper_protocol_failed"
