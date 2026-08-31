from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

import guardian.agents.adapters.pi_codex_runner as pi_codex_runner
from guardian.agents.adapters.base import (
    AgentExecutionIdentity,
    AgentExecutionRequest,
)
from guardian.agents.adapters.pi_codex_runner import PiCodexRunnerAdapter
from guardian.pi.contracts import (
    PiGuardianBoundary,
    PiInvocationEnvelope,
    PiInvocationPolicyDecision,
    PiPermissionGrant,
    PiProviderLane,
)
from guardian.pi.invocation import (
    PiAuthorizedExecutionIdentity,
    PiAuthorizedHarnessRequest,
    PiHarnessRuntimeEvidence,
    invoke_guardian_authorized_pi,
    preflight_guardian_authorized_pi,
)
from guardian.pi.tokens import (
    PiAuthorizedFailureClass,
    PiValidationFailureReason,
)


IDENTITY = PiAuthorizedExecutionIdentity(
    provider_id="openai-codex",
    model_id="gpt-5.3-codex",
    harness_id="pi-coding-agent",
    harness_version="0.72.1",
)


def _permission(permission: str = "files.read") -> PiPermissionGrant:
    return PiPermissionGrant(
        permission=permission,
        resource=".",
        reason="diagnostic fixture scope",
    )


def _envelope(*, source_thread_id: str = "thread-diagnostics") -> PiInvocationEnvelope:
    permission = _permission()
    return PiInvocationEnvelope(
        guardian_boundary=PiGuardianBoundary(owner_account_id="acct-diagnostics"),
        source_thread_id=source_thread_id,
        source_message_id="message-diagnostics",
        authored_request_id="request-diagnostics",
        attempt_id="attempt-diagnostics",
        invocation_id="invocation-diagnostics",
        harness_id=IDENTITY.harness_id,
        harness_version=IDENTITY.harness_version,
        provider_lane=PiProviderLane(
            provider_lane_class="external",
            provider_name=IDENTITY.provider_id,
            model_id=IDENTITY.model_id,
        ),
        requested_permissions=(permission,),
        granted_permissions=(permission,),
        status="prepared",
    )


def _decision(envelope: PiInvocationEnvelope) -> PiInvocationPolicyDecision:
    return PiInvocationPolicyDecision(
        policy_decision_id="policy-diagnostics",
        invocation_id=envelope.invocation_id,
        source_thread_id=envelope.source_thread_id,
        source_message_id=envelope.source_message_id,
        harness_id=envelope.harness_id,
        decision="allowed",
        guardian_boundary=envelope.guardian_boundary,
        requested_permissions=envelope.requested_permissions,
        granted_permissions=envelope.granted_permissions,
        permission_posture="bounded",
        policy_source="guardian",
        decision_reason="deterministic diagnostic fixture",
        decided_at="2026-08-17T00:00:00Z",
        validation_status="valid",
        redaction_state="clean",
    )


def _evidence(
    *,
    status: str = "ok",
    failure_classification: str | None = None,
    failure_stage: str | None = None,
    actual_identity: bool = True,
    oauth_available: bool | None = None,
) -> PiHarnessRuntimeEvidence:
    return PiHarnessRuntimeEvidence(
        status=status,
        actual_provider_id=IDENTITY.provider_id if actual_identity else None,
        actual_model_id=IDENTITY.model_id if actual_identity else None,
        actual_harness_id=IDENTITY.harness_id if actual_identity else None,
        actual_harness_version=IDENTITY.harness_version if actual_identity else None,
        failure_classification=failure_classification,
        failure_stage=failure_stage,
        runtime_identity_established=actual_identity,
        oauth_available=oauth_available,
    )


@dataclass
class _FakeRunner:
    evidence: PiHarnessRuntimeEvidence

    def __post_init__(self) -> None:
        self.calls: list[PiAuthorizedHarnessRequest] = []

    def __call__(self, request: PiAuthorizedHarnessRequest) -> PiHarnessRuntimeEvidence:
        self.calls.append(request)
        return self.evidence


def _invoke(tmp_path: Path, runner: _FakeRunner):
    envelope = _envelope()
    return invoke_guardian_authorized_pi(
        envelope=envelope,
        decision=_decision(envelope),
        prompt="fixture prompt is never sent by these fake runners",
        cwd=tmp_path,
        timeout_seconds=5,
        harness_runner=runner,
    )


@pytest.mark.parametrize(
    ("failure_class", "stage"),
    [
        (PiAuthorizedFailureClass.ADAPTER_TIMEOUT.value, "adapter_execution"),
        (PiAuthorizedFailureClass.WRAPPER_UNAVAILABLE.value, "wrapper_launch"),
        (PiAuthorizedFailureClass.RUNTIME_MODULE_UNAVAILABLE.value, "runtime_load"),
        (PiAuthorizedFailureClass.AUTHORIZED_IDENTITY_REJECTED.value, "authorization"),
        (PiAuthorizedFailureClass.PROVIDER_UNRESOLVED.value, "provider_resolution"),
        (PiAuthorizedFailureClass.MODEL_UNRESOLVED.value, "model_resolution"),
        (PiAuthorizedFailureClass.OAUTH_AUTH_UNAVAILABLE.value, "oauth_readiness"),
        (PiAuthorizedFailureClass.SESSION_INITIALIZATION_FAILED.value, "session_initialization"),
        (PiAuthorizedFailureClass.PROVIDER_REQUEST_FAILED.value, "provider_request"),
        (PiAuthorizedFailureClass.PROVIDER_TRANSPORT_FAILED.value, "provider_transport"),
        (PiAuthorizedFailureClass.WRAPPER_PROTOCOL_FAILED.value, "wrapper_protocol"),
        (PiAuthorizedFailureClass.UNKNOWN_ADAPTER_FAILURE.value, "adapter_execution"),
    ],
)
def test_authorized_failure_class_is_preserved_as_bounded_diagnostic(
    tmp_path: Path,
    failure_class: str,
    stage: str,
) -> None:
    runner = _FakeRunner(
        _evidence(
            status="error",
            failure_classification=failure_class,
            failure_stage=stage,
            actual_identity=False,
        )
    )

    outcome = _invoke(tmp_path, runner)

    assert not outcome.ok
    assert outcome.failure_reason == PiValidationFailureReason.ADAPTER_EXECUTION_FAILURE.value
    assert outcome.diagnostic_class == failure_class
    assert outcome.diagnostic_stage == stage
    assert outcome.runner_call_count == len(runner.calls) == 1
    assert outcome.retry_count == 0
    assert outcome.fallback_count == 0


def test_missing_actual_runtime_identity_remains_fail_closed(tmp_path: Path) -> None:
    runner = _FakeRunner(_evidence(actual_identity=False))

    outcome = _invoke(tmp_path, runner)

    assert not outcome.ok
    assert outcome.failure_reason == PiValidationFailureReason.ACTUAL_IDENTITY_MISSING.value
    assert outcome.diagnostic_class == PiAuthorizedFailureClass.ACTUAL_IDENTITY_MISSING.value
    assert outcome.runner_call_count == 1


def test_unknown_runner_exception_is_redacted_and_fail_closed(tmp_path: Path) -> None:
    envelope = _envelope()

    def runner(_request: PiAuthorizedHarnessRequest) -> PiHarnessRuntimeEvidence:
        raise RuntimeError("authorization: Bearer secret-not-returned")

    outcome = invoke_guardian_authorized_pi(
        envelope=envelope,
        decision=_decision(envelope),
        prompt="fixture",
        cwd=tmp_path,
        timeout_seconds=5,
        harness_runner=runner,
    )

    assert not outcome.ok
    assert outcome.failure_reason == PiValidationFailureReason.ADAPTER_EXECUTION_FAILURE.value
    assert outcome.diagnostic_class == PiAuthorizedFailureClass.UNKNOWN_ADAPTER_FAILURE.value
    assert "secret-not-returned" not in repr(outcome)
    assert "Bearer" not in repr(outcome)


@pytest.mark.parametrize(
    "stderr",
    [
        "Error: provider failed with access_token=secret-not-returned",
        "Error: Authorization: Bearer secret-not-returned",
        "Error: Cookie: session=secret-not-returned",
    ],
)
def test_authorized_adapter_never_returns_raw_or_secret_shaped_stderr(
    stderr: str,
) -> None:
    result = subprocess.CompletedProcess(
        ["node", "agent-wrapper.js", "guardian-authorized-task", "fixture"],
        1,
        stdout="",
        stderr=stderr,
    )

    envelope = PiCodexRunnerAdapter()._parse_result(
        result,
        require_runtime_identity=True,
    )
    payload = json.dumps(envelope.model_dump(), sort_keys=True)

    assert stderr not in payload
    assert "secret-not-returned" not in payload
    assert envelope.failure_classification in {
        PiAuthorizedFailureClass.OAUTH_AUTH_UNAVAILABLE.value,
        PiAuthorizedFailureClass.PROVIDER_REQUEST_FAILED.value,
        PiAuthorizedFailureClass.UNKNOWN_ADAPTER_FAILURE.value,
    }


def test_malformed_authorized_wrapper_json_is_protocol_failure() -> None:
    result = subprocess.CompletedProcess(
        ["node", "agent-wrapper.js", "guardian-authorized-task", "fixture"],
        0,
        stdout="not-json-with-a-secret-shaped-value=secret-not-returned",
        stderr="",
    )

    envelope = PiCodexRunnerAdapter()._parse_result(
        result,
        require_runtime_identity=True,
    )

    assert envelope.failure_classification == PiAuthorizedFailureClass.WRAPPER_PROTOCOL_FAILED.value
    assert "secret-not-returned" not in json.dumps(envelope.model_dump())


def test_pre_execution_rejection_has_zero_runner_calls(tmp_path: Path) -> None:
    runner = _FakeRunner(_evidence())
    envelope = _envelope(source_thread_id="")

    outcome = invoke_guardian_authorized_pi(
        envelope=envelope,
        decision=_decision(envelope),
        prompt="fixture",
        cwd=tmp_path,
        timeout_seconds=5,
        harness_runner=runner,
    )

    assert outcome.failure_reason == PiValidationFailureReason.POLICY_ENVELOPE_MISMATCH.value
    assert outcome.runner_call_count == len(runner.calls) == 0
    assert outcome.retry_count == outcome.fallback_count == 0


def test_success_still_returns_valid_receipt_and_harness_result(tmp_path: Path) -> None:
    runner = _FakeRunner(_evidence())

    outcome = _invoke(tmp_path, runner)

    assert outcome.ok
    assert outcome.receipt is not None
    assert outcome.harness_result is not None
    assert outcome.harness_result.result_class == "success"
    assert outcome.diagnostic_class is None
    assert outcome.runner_call_count == 1
    assert outcome.retry_count == outcome.fallback_count == 0


def test_filesystem_posture_failure_precedes_adapter_success_claim(tmp_path: Path) -> None:
    runner = _FakeRunner(_evidence())

    def mutate(request: PiAuthorizedHarnessRequest) -> PiHarnessRuntimeEvidence:
        (request.cwd / "unauthorized.txt").write_text("mutation", encoding="utf-8")
        return runner.evidence

    runner = mutate  # type: ignore[assignment]
    envelope = _envelope()
    outcome = invoke_guardian_authorized_pi(
        envelope=envelope,
        decision=_decision(envelope),
        prompt="fixture",
        cwd=tmp_path,
        timeout_seconds=5,
        harness_runner=runner,
    )

    assert outcome.failure_reason == PiValidationFailureReason.READ_ONLY_VIOLATION.value
    assert outcome.diagnostic_class == PiAuthorizedFailureClass.TARGET_POSTURE_VIOLATION.value


def test_authorized_preflight_reaches_auth_without_prompt(tmp_path: Path) -> None:
    calls: list[PiAuthorizedHarnessRequest] = []

    def runner(request: PiAuthorizedHarnessRequest) -> PiHarnessRuntimeEvidence:
        calls.append(request)
        return _evidence(oauth_available=True)

    envelope = _envelope()
    outcome = preflight_guardian_authorized_pi(
        envelope=envelope,
        decision=_decision(envelope),
        cwd=tmp_path,
        timeout_seconds=5,
        preflight_runner=runner,
    )

    assert outcome.ok
    assert outcome.failure_class is None
    assert outcome.deepest_stage == "auth_available"
    assert outcome.oauth_available is True
    assert outcome.session_initialized is False
    assert outcome.provider_request_started is False
    assert outcome.preflight_call_count == 1
    assert calls[0].prompt == ""
    assert outcome.retry_count == outcome.fallback_count == 0


def test_authorized_preflight_failure_is_bounded(tmp_path: Path) -> None:
    envelope = _envelope()
    outcome = preflight_guardian_authorized_pi(
        envelope=envelope,
        decision=_decision(envelope),
        cwd=tmp_path,
        timeout_seconds=5,
        preflight_runner=lambda _request: _evidence(
            status="error",
            failure_classification=PiAuthorizedFailureClass.OAUTH_AUTH_UNAVAILABLE.value,
            failure_stage="oauth_readiness",
            actual_identity=True,
            oauth_available=False,
        ),
    )

    assert not outcome.ok
    assert outcome.failure_class == PiAuthorizedFailureClass.OAUTH_AUTH_UNAVAILABLE.value
    assert outcome.failure_stage == "oauth_readiness"
    assert outcome.deepest_stage == "identity_verified"
    assert outcome.retry_count == outcome.fallback_count == 0


def test_authorized_timeout_and_missing_wrapper_are_classified_without_raw_errors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    adapter = PiCodexRunnerAdapter()
    identity = AgentExecutionIdentity(
        provider_id=IDENTITY.provider_id,
        model_id=IDENTITY.model_id,
        harness_id=IDENTITY.harness_id,
        harness_version=IDENTITY.harness_version,
    )
    request = AgentExecutionRequest(prompt="fixture", cwd=str(tmp_path), timeout_seconds=1)

    def timeout(*_args: object, **_kwargs: object) -> None:
        raise subprocess.TimeoutExpired("node", 1)

    monkeypatch.setattr(pi_codex_runner.subprocess, "run", timeout)
    timeout_result = adapter.execute_authorized(request, identity, read_only=True)
    assert timeout_result.failure_classification == PiAuthorizedFailureClass.ADAPTER_TIMEOUT.value
    assert "timed out after" not in timeout_result.summary

    def missing(*_args: object, **_kwargs: object) -> None:
        raise FileNotFoundError("/secret/path")

    monkeypatch.setattr(pi_codex_runner.subprocess, "run", missing)
    missing_result = adapter.execute_authorized(request, identity, read_only=True)
    assert missing_result.failure_classification == PiAuthorizedFailureClass.WRAPPER_UNAVAILABLE.value
    assert "/secret/path" not in missing_result.model_dump_json()


def test_readiness_wrapper_does_not_use_removed_auth_registry_facades() -> None:
    """Static regression: 0.82.1 readiness must use ModelRuntime only."""

    wrapper_path = Path(__file__).resolve().parent.parent.parent / "codex_runner" / "src" / "agent-wrapper.js"
    source = wrapper_path.read_text(encoding="utf-8")

    readiness_block = _readiness_block(source)
    assert "AuthStorage" not in readiness_block
    assert "ModelRegistry" not in readiness_block


def test_readiness_wrapper_uses_model_runtime_availability() -> None:
    """Static regression: readiness uses ModelRuntime's auth-aware catalog."""

    wrapper_path = Path(__file__).resolve().parent.parent.parent / "codex_runner" / "src" / "agent-wrapper.js"
    source = wrapper_path.read_text(encoding="utf-8")

    readiness_block = _readiness_block(source)
    assert "await modelRuntime.getAvailable()" in readiness_block


def test_readiness_wrapper_emits_session_initialized_false_and_no_provider_request() -> None:
    """Static regression: readiness mode must not start a session or a provider request.

    The readiness output schema requires:
      - session_initialized: false
      - provider_request_started: false
      - runtime_identity_established: true (when reaching OAuth readiness)
    The wrapper must emit exactly these bounded indicators.
    """

    wrapper_path = Path(__file__).resolve().parent.parent.parent / "codex_runner" / "src" / "agent-wrapper.js"
    source = wrapper_path.read_text(encoding="utf-8")

    readiness_block = _readiness_block(source)
    assert "session_initialized: false" in readiness_block
    assert "provider_request_started: false" in readiness_block
    assert "runtime_identity_established: true" in readiness_block
    assert "oauth_available: true" in readiness_block


def _readiness_block(source: str) -> str:
    """Locate the bounded `checkGuardianAuthorizedReadiness` body in agent-wrapper.js.

    The readiness branch is dispatched by `else if (guardianAuthorizedReadinessMode)`
    and calls `checkGuardianAuthorizedReadiness()`. We return the function body
    (between the `async function checkGuardianAuthorizedReadiness() {` opener
    and the next top-level function or sentinel) so static assertions evaluate
    only the readiness body, not the help text or task-mode branch.
    """

    fn_marker = "async function checkGuardianAuthorizedReadiness"
    fn_start = source.find(fn_marker)
    assert fn_start != -1, "checkGuardianAuthorizedReadiness not found in agent-wrapper.js"
    body_open = source.find("{", fn_start)
    assert body_open != -1, "checkGuardianAuthorizedReadiness body open brace not found"
    depth = 0
    for i in range(body_open, len(source)):
        ch = source[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return source[body_open : i + 1]
    raise AssertionError("checkGuardianAuthorizedReadiness body close brace not found")


# Regression guard for the live `runAgent()` task-mode path.
#
# The CE-L0 live qualification proof (2026-08-26) established that
# `runAgent()` destructures `harnessId` and `harnessVersion` from
# `await loadPiSdk()` without first declaring those bindings. Because
# the wrapper runs as an ES module (strict mode), the destructuring
# assignment raised `ReferenceError: harnessId is not defined` before
# provider execution. The readiness path (`checkGuardianAuthorizedReadiness`)
# does not exercise this destructuring, and the Python `test_pi_live_invocation`
# suite stubs `harness_runner` before the wrapper subprocess reaches this
# code, so the existing tests cannot catch this regression. These static
# regressions lock the binding declarations in place.
_HARNESS_ID_LET_PATTERN = re.compile(r"^\s*let\s+harnessId\s*;\s*$", re.MULTILINE)
_HARNESS_VERSION_LET_PATTERN = re.compile(r"^\s*let\s+harnessVersion\s*;\s*$", re.MULTILINE)
_RUN_AGENT_DESTRUCTURES_HARNESS_ID_PATTERN = re.compile(
    r"\bharnessId\s*,\s*\n\s*harnessVersion\s*,"
)


def _run_agent_block(source: str) -> str:
    """Locate the bounded `runAgent` body in agent-wrapper.js.

    Returns the function body (between the `async function runAgent() {` opener
    and the closing brace) so static assertions evaluate only the live task
    body, not the readiness body or help text.
    """

    fn_marker = "async function runAgent"
    fn_start = source.find(fn_marker)
    assert fn_start != -1, "runAgent not found in agent-wrapper.js"
    body_open = source.find("{", fn_start)
    assert body_open != -1, "runAgent body open brace not found"
    depth = 0
    for i in range(body_open, len(source)):
        ch = source[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return source[body_open : i + 1]
    raise AssertionError("runAgent body close brace not found")


def test_run_agent_declares_harness_id_before_load_pi_sdk_destructuring() -> None:
    """Static regression: `runAgent()` must declare `harnessId` with `let`.

    The destructuring assignment `({ ..., harnessId, harnessVersion } = await
    loadPiSdk())` requires both names to be declared before assignment; in
    ES-module strict mode an undeclared binding raises `ReferenceError`,
    which the rail classifies as `wrapper_unavailable / runtime_load`.
    """

    wrapper_path = (
        Path(__file__).resolve().parent.parent.parent
        / "codex_runner"
        / "src"
        / "agent-wrapper.js"
    )
    source = wrapper_path.read_text(encoding="utf-8")

    run_agent_body = _run_agent_block(source)
    assert _HARNESS_ID_LET_PATTERN.search(run_agent_body) is not None, (
        "agent-wrapper.js runAgent() must declare `let harnessId;` so the "
        "`await loadPiSdk()` destructuring assignment does not raise "
        "`ReferenceError: harnessId is not defined` in strict ES-module mode."
    )


def test_run_agent_declares_harness_version_before_load_pi_sdk_destructuring() -> None:
    """Static regression: `runAgent()` must declare `harnessVersion` with `let`.

    Same rationale as the `harnessId` regression: `harnessVersion` is
    destructured from `loadPiSdk()` and must be declared first.
    """

    wrapper_path = (
        Path(__file__).resolve().parent.parent.parent
        / "codex_runner"
        / "src"
        / "agent-wrapper.js"
    )
    source = wrapper_path.read_text(encoding="utf-8")

    run_agent_body = _run_agent_block(source)
    assert _HARNESS_VERSION_LET_PATTERN.search(run_agent_body) is not None, (
        "agent-wrapper.js runAgent() must declare `let harnessVersion;` so the "
        "`await loadPiSdk()` destructuring assignment does not raise "
        "`ReferenceError: harnessVersion is not defined` in strict ES-module mode."
    )


def test_run_agent_still_destructures_harness_id_and_version_from_load_pi_sdk() -> None:
    """Static regression: `runAgent()` must keep destructuring both bindings.

    The repair adds the local `let` declarations; the destructuring
    assignment from `await loadPiSdk()` must remain unchanged so harness
    identity still flows from the SDK/runtime rather than being hardcoded.
    """

    wrapper_path = (
        Path(__file__).resolve().parent.parent.parent
        / "codex_runner"
        / "src"
        / "agent-wrapper.js"
    )
    source = wrapper_path.read_text(encoding="utf-8")

    run_agent_body = _run_agent_block(source)
    assert _RUN_AGENT_DESTRUCTURES_HARNESS_ID_PATTERN.search(run_agent_body) is not None, (
        "agent-wrapper.js runAgent() must continue destructuring "
        "`harnessId, harnessVersion` from `await loadPiSdk()` so the "
        "harness identity remains SDK-derived rather than hardcoded."
    )
