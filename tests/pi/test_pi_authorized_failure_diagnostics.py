from __future__ import annotations

import json
import os
import re
import shutil
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


# --- Pi 0.82.1 assistant-response telemetry malformed-payload diagnostics
# (CE-L1 post-tool-repair observability).  These tests prove the adapter
# fails closed when assistant-response telemetry is malformed on a
# successful live authorized task; readiness remains non-inference.


def _wrapper_subprocess_payload(
    monkeypatch, *, payload: dict[str, object]
) -> None:
    """Patch pi_codex_runner.subprocess.run to return a canned wrapper
    output with the supplied payload."""
    def _run(command, **kwargs):
        return subprocess.CompletedProcess(
            command, 0,
            stdout=json.dumps(payload),
            stderr="",
        )
    monkeypatch.setattr(pi_codex_runner.subprocess, "run", _run)
    monkeypatch.setenv("PI_PROVIDER", "ambient-provider")
    monkeypatch.setenv("PI_MODEL", "ambient-model")


def _valid_telemetry_payload() -> dict[str, object]:
    return {
        "status": "ok",
        "summary": "bounded",
        "actual_runtime_identity": {
            "actual_provider_id": IDENTITY.provider_id,
            "actual_model_id": IDENTITY.model_id,
            "actual_harness_id": IDENTITY.harness_id,
            "actual_harness_version": IDENTITY.harness_version,
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
            "assistant_message_event_types": ["start", "text_start", "done"],
            "assistant_tool_call_event_count": 0,
        },
    }


def test_missing_assistant_message_count_is_wrapper_protocol_failure(
    monkeypatch, tmp_path,
) -> None:
    """A live wrapper payload without `assistant_message_count` must fail
    closed as `wrapper_protocol_failed` (readiness remains exempt)."""
    payload = _valid_telemetry_payload()
    payload["tool_telemetry"] = {
        k: v for k, v in payload["tool_telemetry"].items()
        if k != "assistant_message_count"
    }
    _wrapper_subprocess_payload(monkeypatch, payload=payload)
    result = PiCodexRunnerAdapter().execute_authorized(
        AgentExecutionRequest(
            prompt="bounded", cwd=str(tmp_path), timeout_seconds=12,
        ),
        AgentExecutionIdentity(
            provider_id=IDENTITY.provider_id,
            model_id=IDENTITY.model_id,
            harness_id=IDENTITY.harness_id,
            harness_version=IDENTITY.harness_version,
        ),
        read_only=True,
    )
    assert result.status == "error"
    assert result.failure_classification == "wrapper_protocol_failed"
    assert result.failure_stage == "wrapper_protocol"


def test_negative_assistant_tool_call_event_count_is_wrapper_protocol_failure(
    monkeypatch, tmp_path,
) -> None:
    """A negative `assistant_tool_call_event_count` fails closed."""
    payload = _valid_telemetry_payload()
    payload["tool_telemetry"]["assistant_tool_call_event_count"] = -3
    _wrapper_subprocess_payload(monkeypatch, payload=payload)
    result = PiCodexRunnerAdapter().execute_authorized(
        AgentExecutionRequest(
            prompt="bounded", cwd=str(tmp_path), timeout_seconds=12,
        ),
        AgentExecutionIdentity(
            provider_id=IDENTITY.provider_id,
            model_id=IDENTITY.model_id,
            harness_id=IDENTITY.harness_id,
            harness_version=IDENTITY.harness_version,
        ),
        read_only=True,
    )
    assert result.status == "error"
    assert result.failure_classification == "wrapper_protocol_failed"


def test_non_string_assistant_message_event_type_is_wrapper_protocol_failure(
    monkeypatch, tmp_path,
) -> None:
    """A non-string entry in `assistant_message_event_types` fails closed."""
    payload = _valid_telemetry_payload()
    payload["tool_telemetry"]["assistant_message_event_types"] = [
        "start", 42, "done",
    ]
    _wrapper_subprocess_payload(monkeypatch, payload=payload)
    result = PiCodexRunnerAdapter().execute_authorized(
        AgentExecutionRequest(
            prompt="bounded", cwd=str(tmp_path), timeout_seconds=12,
        ),
        AgentExecutionIdentity(
            provider_id=IDENTITY.provider_id,
            model_id=IDENTITY.model_id,
            harness_id=IDENTITY.harness_id,
            harness_version=IDENTITY.harness_version,
        ),
        read_only=True,
    )
    assert result.status == "error"
    assert result.failure_classification == "wrapper_protocol_failed"


def test_assistant_content_block_types_not_a_list_is_wrapper_protocol_failure(
    monkeypatch, tmp_path,
) -> None:
    """`assistant_content_block_types` not a list fails closed."""
    payload = _valid_telemetry_payload()
    payload["tool_telemetry"]["assistant_content_block_types"] = "text"
    _wrapper_subprocess_payload(monkeypatch, payload=payload)
    result = PiCodexRunnerAdapter().execute_authorized(
        AgentExecutionRequest(
            prompt="bounded", cwd=str(tmp_path), timeout_seconds=12,
        ),
        AgentExecutionIdentity(
            provider_id=IDENTITY.provider_id,
            model_id=IDENTITY.model_id,
            harness_id=IDENTITY.harness_id,
            harness_version=IDENTITY.harness_version,
        ),
        read_only=True,
    )
    assert result.status == "error"
    assert result.failure_classification == "wrapper_protocol_failed"


def test_readiness_remains_exempt_from_assistant_telemetry(
    monkeypatch, tmp_path,
) -> None:
    """Preflight readiness does NOT require assistant telemetry (readiness
    is non-inference and never touches a Pi model session/prompt)."""
    payload = {
        "status": "ok",
        "summary": "readiness",
        "actual_runtime_identity": {
            "actual_provider_id": IDENTITY.provider_id,
            "actual_model_id": IDENTITY.model_id,
            "actual_harness_id": IDENTITY.harness_id,
            "actual_harness_version": IDENTITY.harness_version,
        },
        # Deliberately omit tool_telemetry entirely: readiness is
        # non-inference and does not require telemetry.
    }
    _wrapper_subprocess_payload(monkeypatch, payload=payload)
    # Use preflight API path which does not require telemetry.
    envelope = _envelope()
    outcome = preflight_guardian_authorized_pi(
        envelope=envelope,
        decision=_decision(envelope),
        timeout_seconds=12,
        cwd=tmp_path,
    )
    assert outcome.ok is True
    # The preflight's deepest stage proves the readiness path is exempt.
    # No assertions on assistant telemetry here — readiness must remain
    # non-inference.


# --- Authorized wrapper subprocess stdout framing diagnostics.
#
# The canonical authorized wrapper emits exactly one terminal JSON
# object via `console.log(JSON.stringify(payload))`. Any earlier stdout
# lines are untrusted dependency diagnostics, never persisted, and
# carry no authority. The bounded adapter MUST treat the final
# non-empty stdout line as the protocol frame and reject every other
# framing shape with `wrapper_protocol_failed`.


VALID_TELEMETRY: dict[str, object] = {
    "effective_tool_names": ["read", "bash", "edit", "write"],
    "write_tool_available": True,
    "tool_execution_start_count": 0,
    "tool_execution_end_count": 0,
    "executed_tool_names": [],
    "assistant_tool_call_count": 0,
    "assistant_message_count": 1,
    "assistant_content_block_types": ["text"],
    "assistant_message_event_types": ["start", "text_start", "done"],
    "assistant_tool_call_event_count": 0,
}


def _success_frame() -> dict[str, object]:
    return {
        "status": "ok",
        "summary": "bounded",
        "actual_runtime_identity": {
            "actual_provider_id": IDENTITY.provider_id,
            "actual_model_id": IDENTITY.model_id,
            "actual_harness_id": IDENTITY.harness_id,
            "actual_harness_version": IDENTITY.harness_version,
        },
        "runtime_identity_established": True,
        "session_initialized": True,
        "provider_request_started": True,
        "tool_telemetry": dict(VALID_TELEMETRY),
    }


def _parse_authorized_wrapper(
    *,
    stdout: str,
    returncode: int = 0,
    stderr: str = "",
    require_tool_telemetry: bool = True,
):
    """Direct invocation of the bounded authorized-path parser."""
    result = subprocess.CompletedProcess(
        ["node", "agent-wrapper.js", "guardian-authorized-task", "fixture"],
        returncode,
        stdout=stdout,
        stderr=stderr,
    )
    return PiCodexRunnerAdapter()._parse_result(
        result,
        require_runtime_identity=True,
        require_tool_telemetry=require_tool_telemetry,
    )


def test_case_a_clean_success_frame() -> None:
    """Case A — clean success: exactly one valid JSON line."""
    payload = _success_frame()
    envelope = _parse_authorized_wrapper(stdout=json.dumps(payload))
    assert envelope.failure_classification is None
    assert envelope.status == "ok"
    assert envelope.actual_provider_id == IDENTITY.provider_id
    assert envelope.actual_model_id == IDENTITY.model_id
    assert envelope.actual_harness_id == IDENTITY.harness_id
    assert envelope.actual_harness_version == IDENTITY.harness_version
    assert envelope.runtime_identity_established is True
    assert envelope.session_initialized is True
    assert envelope.provider_request_started is True
    expected = (
        tuple(VALID_TELEMETRY["effective_tool_names"]),
        VALID_TELEMETRY["write_tool_available"],
        VALID_TELEMETRY["tool_execution_start_count"],
        VALID_TELEMETRY["tool_execution_end_count"],
        tuple(VALID_TELEMETRY["executed_tool_names"]),
        VALID_TELEMETRY["assistant_tool_call_count"],
        VALID_TELEMETRY["assistant_message_count"],
        tuple(VALID_TELEMETRY["assistant_content_block_types"]),
        tuple(VALID_TELEMETRY["assistant_message_event_types"]),
        VALID_TELEMETRY["assistant_tool_call_event_count"],
    )
    actual = (
        envelope.effective_tool_names,
        envelope.write_tool_available,
        envelope.tool_execution_start_count,
        envelope.tool_execution_end_count,
        envelope.executed_tool_names,
        envelope.assistant_tool_call_count,
        envelope.assistant_message_count,
        envelope.assistant_content_block_types,
        envelope.assistant_message_event_types,
        envelope.assistant_tool_call_event_count,
    )
    assert actual == expected


def test_case_b_leading_noise_then_success_frame() -> None:
    """Case B — leading untrusted stdout noise + valid terminal JSON.

    Demonstrates the structural defect that the prior whole-document
    parser exhibited: any leading diagnostic line would corrupt
    ``json.loads(stdout)``. The framing helper discards the leading
    lines and parses the final non-empty line.
    """
    payload = _success_frame()
    stdout = (
        "synthetic-untrusted-diagnostic-line\n"
        "synthetic-log access_token=secret-not-returned\n"
        + json.dumps(payload)
    )
    envelope = _parse_authorized_wrapper(stdout=stdout)
    assert envelope.failure_classification is None
    assert envelope.status == "ok"
    assert envelope.actual_provider_id == IDENTITY.provider_id
    # The ignored stdout diagnostics must not become a result-return
    # surface.
    payload_dump = json.dumps(envelope.model_dump(), sort_keys=True)
    assert "secret-not-returned" not in payload_dump
    assert "access_token" not in payload_dump
    assert "synthetic-untrusted-diagnostic-line" not in payload_dump


def test_case_c_leading_noise_then_bounded_wrapper_failure() -> None:
    """Case C — leading noise + bounded authorized wrapper failure.

    The bounded ``failure_class`` / ``failure_stage`` from the final
    frame must survive the framing repair intact.
    """
    payload = {
        "status": "error",
        "failure_class": PiAuthorizedFailureClass.PROVIDER_REQUEST_FAILED.value,
        "failure_stage": "provider_request",
        "actual_runtime_identity": {
            "actual_provider_id": IDENTITY.provider_id,
            "actual_model_id": IDENTITY.model_id,
            "actual_harness_id": IDENTITY.harness_id,
            "actual_harness_version": IDENTITY.harness_version,
        },
        "runtime_identity_established": True,
        "session_initialized": True,
        "provider_request_started": True,
        "tool_telemetry": dict(VALID_TELEMETRY),
    }
    stdout = (
        "diagnostic-pre-output\n"
        "another-line\n"
        + json.dumps(payload)
    )
    envelope = _parse_authorized_wrapper(stdout=stdout)
    assert envelope.failure_classification == (
        PiAuthorizedFailureClass.PROVIDER_REQUEST_FAILED.value
    )
    assert envelope.failure_stage == "provider_request"


def test_case_d_valid_frame_then_trailing_noise() -> None:
    """Case D — valid JSON frame + trailing noise fails closed.

    The final non-empty line is not the JSON object; framing fails.
    """
    payload = _success_frame()
    stdout = json.dumps(payload) + "\ntrailing-untrusted-diagnostic"
    envelope = _parse_authorized_wrapper(stdout=stdout)
    assert envelope.failure_classification == (
        PiAuthorizedFailureClass.WRAPPER_PROTOCOL_FAILED.value
    )
    assert envelope.failure_stage == "wrapper_protocol"


def test_case_e_malformed_final_frame() -> None:
    """Case E — leading diagnostic + malformed final line fails closed."""
    stdout = "leading diagnostic\n{not-json"
    envelope = _parse_authorized_wrapper(stdout=stdout)
    assert envelope.failure_classification == (
        PiAuthorizedFailureClass.WRAPPER_PROTOCOL_FAILED.value
    )
    assert envelope.failure_stage == "wrapper_protocol"


@pytest.mark.parametrize(
    "final_line",
    [
        "[]",
        '"a string"',
        "123",
        "true",
        "null",
    ],
)
def test_case_f_non_object_final_json_fails_closed(final_line: str) -> None:
    """Case F — non-object final JSON (list / string / number / bool /
    null) fails closed. Authorized protocol frame must be one JSON
    object."""
    stdout = "leading noise\n" + final_line
    envelope = _parse_authorized_wrapper(stdout=stdout)
    assert envelope.failure_classification == (
        PiAuthorizedFailureClass.WRAPPER_PROTOCOL_FAILED.value
    )
    assert envelope.failure_stage == "wrapper_protocol"


def test_case_g_empty_stdout_fails_closed() -> None:
    """Empty stdout must remain fail-closed as wrapper_protocol_failed."""
    envelope = _parse_authorized_wrapper(stdout="")
    assert envelope.failure_classification == (
        PiAuthorizedFailureClass.WRAPPER_PROTOCOL_FAILED.value
    )
    assert envelope.failure_stage == "wrapper_protocol"


def test_case_h_nonzero_return_code_keeps_precedence() -> None:
    """Case H — nonzero subprocess exit retains precedence over stdout.

    Even when the stdout contains a valid success frame, a nonzero
    process exit must classify through the bounded stderr path rather
    than be salvaged into success.
    """
    payload = _success_frame()
    envelope = _parse_authorized_wrapper(
        stdout=json.dumps(payload),
        returncode=1,
        stderr="Error: provider not found",
    )
    assert envelope.status == "error"
    assert envelope.failure_classification in {
        PiAuthorizedFailureClass.PROVIDER_UNRESOLVED.value,
        PiAuthorizedFailureClass.PROVIDER_REQUEST_FAILED.value,
        PiAuthorizedFailureClass.UNKNOWN_ADAPTER_FAILURE.value,
    }
    # And it must NOT be classified as a wrapper_protocol success.
    assert envelope.failure_stage != "wrapper_protocol" or (
        envelope.failure_classification
        == PiAuthorizedFailureClass.WRAPPER_PROTOCOL_FAILED.value
    )
    # Specifically: no actual_runtime_identity is salvaged from stdout
    # when the subprocess returned nonzero.
    assert envelope.actual_provider_id is None or envelope.runtime_identity_established is False


def test_missing_runtime_identity_still_fail_closed() -> None:
    """A valid final JSON object without ``actual_runtime_identity`` must
    still fail as ``actual_identity_missing`` — framing parsing does
    not weaken identity attestation."""
    payload = {
        "status": "ok",
        "summary": "no-identity",
        "runtime_identity_established": False,
        "session_initialized": True,
        "provider_request_started": True,
        "tool_telemetry": dict(VALID_TELEMETRY),
    }
    envelope = _parse_authorized_wrapper(stdout=json.dumps(payload))
    assert envelope.failure_classification == (
        PiAuthorizedFailureClass.ACTUAL_IDENTITY_MISSING.value
    )


def test_missing_tool_telemetry_still_fail_closed() -> None:
    """A valid final JSON object with ``tool_telemetry=null`` must still
    return ``wrapper_protocol_failed``."""
    payload = _success_frame()
    payload["tool_telemetry"] = None
    envelope = _parse_authorized_wrapper(stdout=json.dumps(payload))
    assert envelope.failure_classification == (
        PiAuthorizedFailureClass.WRAPPER_PROTOCOL_FAILED.value
    )
    assert envelope.failure_stage == "wrapper_protocol"


def test_secret_shaped_leading_diagnostic_does_not_leak() -> None:
    """A leading line carrying a secret-shaped token must not appear in
    the resulting envelope's serialized payload."""
    payload = _success_frame()
    stdout = "synthetic-log access_token=secret-not-returned\n" + json.dumps(payload)
    envelope = _parse_authorized_wrapper(stdout=stdout)
    serialized = json.dumps(envelope.model_dump(), sort_keys=True)
    assert "secret-not-returned" not in serialized
    assert "access_token" not in serialized


def test_authorized_stdout_frame_helper_isolated_reproduction() -> None:
    """Provider-free isolation of the framing defect.

    Demonstrates the exact structural defect class that the prior
    whole-document ``json.loads(stdout.strip())`` parser exhibited:
    ANY leading stdout line corrupts the parser. The new
    ``_parse_authorized_stdout_frame`` helper discards earlier lines
    and parses the final non-empty line.
    """
    payload = {
        "status": "ok",
        "summary": "bounded",
        "actual_runtime_identity": {
            "actual_provider_id": IDENTITY.provider_id,
            "actual_model_id": IDENTITY.model_id,
            "actual_harness_id": IDENTITY.harness_id,
            "actual_harness_version": IDENTITY.harness_version,
        },
        "tool_telemetry": dict(VALID_TELEMETRY),
    }
    json_line = json.dumps(payload)
    # Leading diagnostic noise before the JSON.
    multiline = "FAKE_PI_SDK_DIAGNOSTIC\n" + json_line

    # Whole-document json.loads is the legacy parser; it raises because
    # "FAKE_PI_SDK_DIAGNOSTIC\n{...}" is not a single JSON document.
    with pytest.raises(json.JSONDecodeError):
        json.loads(multiline.strip())

    # The new framing helper recovers the JSON object.
    recovered = pi_codex_runner._parse_authorized_stdout_frame(multiline)
    assert recovered == payload
    # And it does not return any diagnostic content.
    assert "FAKE_PI_SDK_DIAGNOSTIC" not in json.dumps(recovered)

    # Empty stdout → None.
    assert pi_codex_runner._parse_authorized_stdout_frame("") is None

    # Whitespace-only stdout → None.
    assert pi_codex_runner._parse_authorized_stdout_frame("\n  \n") is None

    # Non-object final line → None.
    assert pi_codex_runner._parse_authorized_stdout_frame("noise\n[]") is None
    assert pi_codex_runner._parse_authorized_stdout_frame("noise\nnull") is None

    # Malformed final line → None.
    assert pi_codex_runner._parse_authorized_stdout_frame("noise\n{not-json") is None


# --- Real wrapper subprocess integration with disposable fake Pi package.
#
# This is the canonical end-to-end framing-repair proof: the REAL
# ``codex_runner/src/agent-wrapper.js`` writes its terminal authorized
# result via ``console.log(JSON.stringify(payload))``. A fake Pi 0.82.1
# package materialized under ``tmp_path/fake_pi_package`` deliberately
# writes one diagnostic line to stdout before the wrapper's terminal
# JSON. The bounded adapter must parse the final line and produce a
# bounded ``AgentRunEnvelope`` — not ``wrapper_protocol_failed`` from a
# JSON decode error on the multi-line stdout.
#
# The fake package performs no network, no DNS, no socket, no real
# provider SDK. The subprocess runs with ``HOME=<disposable tmp_path>``
# and ``PI_CODING_AGENT_PACKAGE_ROOT=<materialized tmp package>``.
#
# Per spec §23-§25, this exercises:
#   fake Pi SDK (from tracked source fixture) -> real agent-wrapper.js
#   -> real subprocess stdout -> real PiCodexRunnerAdapter parser
#   without a provider.
#
# The tracked source fixture is the in-tree
# ``tests/pi/fixtures/fake_pi_package/source/index.js`` plus the
# ``package.json`` metadata. The test materializes these into a
# fresh ``tmp_path/fake_pi_package`` so the integration proof is
# reproducible from tracked state alone (no hidden ignored
# ``dist/`` dependency).


# Tracked fixture source locations (these are the only files needed
# from the repository for the real-wrapper integration tests).  The
# generated ``dist/index.js`` is materialized under pytest's
# ``tmp_path`` and is NOT a tracked artifact.
_FIXTURE_SOURCE_DIR = (
    Path(__file__).parent / "fixtures" / "fake_pi_package"
)
_FIXTURE_SOURCE_INDEX = _FIXTURE_SOURCE_DIR / "source" / "index.js"
_FIXTURE_PACKAGE_JSON = _FIXTURE_SOURCE_DIR / "package.json"
_WRAPPER_PATH = (
    Path(__file__).parent.parent.parent
    / "codex_runner"
    / "src"
    / "agent-wrapper.js"
)


def _materialize_fake_pi_package(tmp_path: Path) -> Path:
    """Materialize a fresh fake Pi 0.82.1 package under ``tmp_path``.

    The materialized package contains:

        package.json           (copied from the tracked fixture)
        dist/index.js          (copied from the tracked source fixture)

    The materialized root is what the test must point
    ``PI_CODING_AGENT_PACKAGE_ROOT`` at.  No real-wrapper integration
    test may point directly at the in-repository fixture directory;
    that would silently depend on a stale ignored ``dist/`` artifact
    and would not be reproducible from a clean checkout.
    """
    package_root = tmp_path / "fake_pi_package"
    (package_root / "dist").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(_FIXTURE_PACKAGE_JSON, package_root / "package.json")
    shutil.copyfile(_FIXTURE_SOURCE_INDEX, package_root / "dist" / "index.js")
    return package_root


def _subprocess_authorized_wrapper(
    materialized_fake_pi: Path,
    *,
    prompt: str = "fixture prompt",
    disable_tools: bool = False,
    fake_home: Path,
    cwd: Path,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run the REAL ``agent-wrapper.js`` against a materialized fake
    Pi package, in a disposable HOME, with the canonical authorized
    env contract.  ``PI_CODING_AGENT_PACKAGE_ROOT`` MUST point at the
    materialized package — never at the in-repository fixture
    directory.
    """
    env: dict[str, str] = {
        # Preserve PATH so the wrapper subprocess can find ``node``.
        # Strip any inherited provider secrets so the fixture cannot
        # accidentally talk to a real provider.
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(fake_home),
        "TMPDIR": str(cwd),
        "PI_CODING_AGENT_PACKAGE_ROOT": str(materialized_fake_pi),
        "PI_PROVIDER": "openai-codex",
        "PI_MODEL": "gpt-5.6-sol",
        "PI_GUARDIAN_AUTHORIZED": "1",
        "PI_GUARDIAN_HARNESS_ID": "pi-coding-agent",
        "PI_GUARDIAN_HARNESS_VERSION": "0.82.1",
        "PI_DISABLE_TOOLS": "1" if disable_tools else "0",
    }
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["node", str(_WRAPPER_PATH), "guardian-authorized-task", prompt],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


def _envelope_from_wrapper_result(
    result: subprocess.CompletedProcess[str],
):
    """Run the adapter's bounded parser against a real subprocess result."""
    return PiCodexRunnerAdapter()._parse_result(
        result,
        require_runtime_identity=True,
        require_tool_telemetry=True,
    )


@pytest.mark.skipif(
    not _FIXTURE_SOURCE_INDEX.exists(),
    reason="tracked fake Pi source fixture is missing",
)
def test_real_wrapper_noisy_stdout_success_protocol(tmp_path: Path) -> None:
    """Real wrapper + fake Pi success path: stdout contains one
    diagnostic line BEFORE the canonical terminal JSON.

    The fixture is materialized under ``tmp_path`` from the tracked
    source ``tests/pi/fixtures/fake_pi_package/source/index.js``.  No
    hidden ignored file is required for this test to pass.

    The framing repair must NOT collapse this multi-line stdout into
    ``wrapper_protocol_failed`` at the JSON decode step.  After the
    Guardian-authorized ten-field telemetry repair, the wrapper emits
    a complete 10-field ``tool_telemetry`` object and the real
    ``execute_authorized`` path accepts the success frame (not a
    bounded ``wrapper_protocol_failed``).

    The secret-shaped leading diagnostic (``access_token=secret-not-returned``)
    must not appear in the returned envelope's serialized payload.
    """
    materialized = _materialize_fake_pi_package(tmp_path)
    fake_home = tmp_path / "home"
    fake_home.mkdir(parents=True, exist_ok=True)
    result = _subprocess_authorized_wrapper(
        materialized,
        fake_home=fake_home,
        cwd=tmp_path,
    )
    assert result.returncode == 0, (
        f"wrapper subprocess failed unexpectedly: "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    # The fake MUST have emitted its diagnostic line.
    assert "FAKE_PI_SDK_DIAGNOSTIC" in result.stdout
    # The wrapper's terminal JSON MUST also be present (last line).
    final_line = result.stdout.strip().splitlines()[-1]
    parsed = json.loads(final_line)
    assert isinstance(parsed, dict)
    assert "actual_runtime_identity" in parsed
    # After the 10-field telemetry repair, the wrapper emits a complete
    # 10-field tool_telemetry object on success.
    assert parsed["status"] == "ok", (
        f"pre-repair 6-field payload expected; got status={parsed['status']!r}: {parsed!r}"
    )
    tt = parsed["tool_telemetry"]
    expected_keys = {
        "effective_tool_names",
        "write_tool_available",
        "tool_execution_start_count",
        "tool_execution_end_count",
        "executed_tool_names",
        "assistant_tool_call_count",
        "assistant_message_count",
        "assistant_content_block_types",
        "assistant_message_event_types",
        "assistant_tool_call_event_count",
    }
    assert set(tt.keys()) == expected_keys, (
        f"tool_telemetry keys mismatch: missing={expected_keys - set(tt.keys())} "
        f"extra={set(tt.keys()) - expected_keys}"
    )
    # The adapter's framing helper recovers the same payload.
    recovered = pi_codex_runner._parse_authorized_stdout_frame(result.stdout)
    assert recovered == parsed
    # And the adapter does NOT raise a JSON-decode error from the
    # multi-line stdout — it parses the framing correctly.
    envelope = _envelope_from_wrapper_result(result)
    assert envelope is not None
    # Identity IS retained end-to-end via the framing repair.
    assert envelope.actual_provider_id == "openai-codex"
    assert envelope.actual_model_id == "gpt-5.6-sol"
    assert envelope.actual_harness_id == "pi-coding-agent"
    assert envelope.actual_harness_version == "0.82.1"
    assert envelope.runtime_identity_established is True
    # Secret-shaped leading diagnostic MUST NOT appear in the envelope.
    payload_dump = json.dumps(envelope.model_dump(), sort_keys=True)
    assert "secret-not-returned" not in payload_dump
    assert "FAKE_PI_SDK_DIAGNOSTIC" not in payload_dump


# --- Guardian-authorized ten-field telemetry contract tests.
#
# These tests exercise the real wrapper against the materialized fake Pi
# package.  The fake exposes two behavior modes:
#   default            (no PI_FAKE_I_BEHAVIOR)  -> zero-event success
#   assistant-tool-call (PI_FAKE_I_BEHAVIOR=assistant-tool-call)
#                                           -> bounded event sequence
# The default path produces a clean zero-event success with all ten
# telemetry fields populated to bounded zero/empty values.  The
# assistant-tool-call path produces a sentinel lifecycle with the
# exact field values spec'd in the bounded-live-substrate-proof
# recipe (Requirement 19).

ZERO_EVENT_EXPECTED = {
    "effective_tool_names": ("read", "bash", "edit", "write"),
    "write_tool_available": True,
    "tool_execution_start_count": 0,
    "tool_execution_end_count": 0,
    "executed_tool_names": (),
    "assistant_tool_call_count": 0,
    "assistant_message_count": 0,
    "assistant_content_block_types": (),
    "assistant_message_event_types": (),
    "assistant_tool_call_event_count": 0,
}

SENTINEL_EXPECTED = {
    "effective_tool_names": ("read", "bash", "edit", "write"),
    "write_tool_available": True,
    "tool_execution_start_count": 1,
    "tool_execution_end_count": 1,
    "executed_tool_names": ("write",),
    "assistant_tool_call_count": 1,
    "assistant_message_count": 1,
    "assistant_content_block_types": ("toolCall",),
    "assistant_message_event_types": ("toolcall_start", "toolcall_end"),
    "assistant_tool_call_event_count": 2,
}


def _last_json(stdout: str) -> dict:
    final_line = stdout.strip().splitlines()[-1]
    return json.loads(final_line)


def _envelope_tt_dict(envelope) -> dict[str, object]:
    """Map the bounded envelope's individual telemetry attributes to a
    dict for spec-mapped comparison."""
    return {
        "effective_tool_names": envelope.effective_tool_names,
        "write_tool_available": envelope.write_tool_available,
        "tool_execution_start_count": envelope.tool_execution_start_count,
        "tool_execution_end_count": envelope.tool_execution_end_count,
        "executed_tool_names": envelope.executed_tool_names,
        "assistant_tool_call_count": envelope.assistant_tool_call_count,
        "assistant_message_count": envelope.assistant_message_count,
        "assistant_content_block_types": envelope.assistant_content_block_types,
        "assistant_message_event_types": envelope.assistant_message_event_types,
        "assistant_tool_call_event_count": envelope.assistant_tool_call_event_count,
    }


@pytest.mark.skipif(
    not _FIXTURE_SOURCE_INDEX.exists(),
    reason="tracked fake Pi source fixture is missing",
)
def test_real_wrapper_ten_field_zero_event_success(tmp_path: Path) -> None:
    """Canonical 10-field zero-event success: the wrapper emits a
    complete tool_telemetry object with all four newly-wired assistant
    fields present (default behavior; no events emitted)."""
    materialized = _materialize_fake_pi_package(tmp_path)
    fake_home = tmp_path / "home"
    fake_home.mkdir(parents=True, exist_ok=True)
    result = _subprocess_authorized_wrapper(
        materialized,
        fake_home=fake_home,
        cwd=tmp_path,
    )
    assert result.returncode == 0, (
        f"wrapper subprocess failed: stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    parsed = _last_json(result.stdout)
    assert parsed["status"] == "ok"
    envelope = _envelope_from_wrapper_result(result)
    assert envelope.status == "ok"
    assert envelope.runtime_identity_established is True
    actual = _envelope_tt_dict(envelope)
    for key, expected in ZERO_EVENT_EXPECTED.items():
        assert actual[key] == expected, (
            f"telemetry field {key!r}: expected {expected!r}, got {actual[key]!r}"
        )


@pytest.mark.skipif(
    not _FIXTURE_SOURCE_INDEX.exists(),
    reason="tracked fake Pi source fixture is missing",
)
def test_real_wrapper_ten_field_assistant_tool_call_sentinel(tmp_path: Path) -> None:
    """Sentinel lifecycle: fake Pi emits one toolcall_start, one
    tool_execution_start (write), one tool_execution_end (write), and
    one toolcall_end.  Final session state contains one assistant
    message with one toolCall block carrying a secret-shaped
    argument.  The wrapper must surface the exact 10-field values
    from SENTINEL_EXPECTED and MUST NOT retain the secret-shaped
    argument anywhere in the bounded envelope."""
    materialized = _materialize_fake_pi_package(tmp_path)
    fake_home = tmp_path / "home"
    fake_home.mkdir(parents=True, exist_ok=True)
    extra_env = {"PI_FAKE_I_BEHAVIOR": "assistant-tool-call"}
    result = _subprocess_authorized_wrapper(
        materialized,
        fake_home=fake_home,
        cwd=tmp_path,
        extra_env=extra_env,
    )
    assert result.returncode == 0, (
        f"wrapper subprocess failed: stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    parsed = _last_json(result.stdout)
    assert parsed["status"] == "ok"
    envelope = _envelope_from_wrapper_result(result)
    assert envelope.status == "ok"
    assert envelope.runtime_identity_established is True
    actual = _envelope_tt_dict(envelope)
    for key, expected in SENTINEL_EXPECTED.items():
        assert actual[key] == expected, (
            f"telemetry field {key!r}: expected {expected!r}, got {actual[key]!r}"
        )
    # Content-redaction proof: secret-shaped argument MUST NOT appear
    # in any serialized envelope field.
    payload_dump = json.dumps(envelope.model_dump(), sort_keys=True)
    assert "secret-not-returned" not in payload_dump, (
        "secret-shaped argument leaked into the bounded envelope"
    )


def test_remove_assistant_message_count_fails_closed() -> None:
    """Missing one assistant field (assistant_message_count) in an
    otherwise valid authorized success frame must still return
    wrapper_protocol_failed at wrapper_protocol.  The framing
    repair must not weaken the 10-field strictness contract."""
    payload = {
        "status": "ok",
        "summary": "bounded",
        "actual_runtime_identity": {
            "actual_provider_id": "openai-codex",
            "actual_model_id": "gpt-5.6-sol",
            "actual_harness_id": "pi-coding-agent",
            "actual_harness_version": "0.82.1",
        },
        "execution_result": {
            "status": "completed",
            "result_kind": "structured",
            "content_omitted": True,
        },
        "session_initialized": True,
        "provider_request_started": True,
        "tool_telemetry": {
            "effective_tool_names": ["read", "bash", "edit", "write"],
            "write_tool_available": True,
            "tool_execution_start_count": 0,
            "tool_execution_end_count": 0,
            "executed_tool_names": [],
            "assistant_tool_call_count": 0,
            # assistant_message_count omitted
            "assistant_content_block_types": [],
            "assistant_message_event_types": [],
            "assistant_tool_call_event_count": 0,
        },
    }
    result = subprocess.CompletedProcess(
        ["node", "agent-wrapper.js", "guardian-authorized-task", "fixture"],
        0,
        json.dumps(payload),
        "",
    )
    envelope = PiCodexRunnerAdapter()._parse_result(
        result,
        require_runtime_identity=True,
        require_tool_telemetry=True,
    )
    assert envelope.failure_classification == (
        PiAuthorizedFailureClass.WRAPPER_PROTOCOL_FAILED.value
    )
    assert envelope.failure_stage == "wrapper_protocol"


@pytest.mark.skipif(
    not _FIXTURE_SOURCE_INDEX.exists(),
    reason="tracked fake Pi source fixture is missing",
)
def test_real_wrapper_noisy_stdout_failure_protocol(tmp_path: Path) -> None:
    """Real wrapper + fake Pi failure path: the fake session raises a
    synthetic provider-request error so the wrapper emits its bounded
    failure JSON as the final stdout line, with one leading diagnostic
    line above it.

    The framing repair must NOT confuse the multi-line stdout for an
    invalid JSON envelope.  The bounded ``failure_class`` /
    ``failure_stage`` from the final frame must survive intact.

    The fixture is materialized under ``tmp_path`` from the tracked
    source.  No hidden ignored file is required.
    """
    materialized = _materialize_fake_pi_package(tmp_path)
    fake_home = tmp_path / "home"
    fake_home.mkdir(parents=True, exist_ok=True)
    # The success/failure behavior is selected by an env knob the fake
    # reads from the subprocess environment.
    extra_env = {"PI_FAKE_I_BEHAVIOR": "failure"}
    result = _subprocess_authorized_wrapper(
        materialized,
        fake_home=fake_home,
        cwd=tmp_path,
        extra_env=extra_env,
    )
    assert result.returncode == 0
    assert "FAKE_PI_SDK_DIAGNOSTIC" in result.stdout
    final_line = result.stdout.strip().splitlines()[-1]
    parsed = json.loads(final_line)
    assert parsed["status"] == "error"
    assert parsed["failure_class"] in {
        "provider_request_failed",
        "session_initialization_failed",
        "wrapper_unavailable",
        "runtime_module_unavailable",
        "authorized_identity_rejected",
        "provider_unresolved",
        "model_unresolved",
        "oauth_auth_unavailable",
        "provider_transport_failed",
        "wrapper_protocol_failed",
        "unknown_adapter_failure",
        "adapter_timeout",
    }

    envelope = _envelope_from_wrapper_result(result)
    # Adapter MUST classify the bounded failure rather than the
    # multi-line stdout itself.
    assert envelope.status == "error"
    assert envelope.failure_classification == parsed["failure_class"]
    assert envelope.failure_stage == parsed["failure_stage"]
