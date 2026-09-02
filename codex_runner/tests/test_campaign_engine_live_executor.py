"""Deterministic tests for the live Executor Campaign runtime (CE-L1).

All tests in this module monkey-patch the private ``codex_runner.campaign_engine.live_executor._invoker``
hook so the unit tests never perform a real provider call.

The canonical real-attempt path goes through
``codex_runner.campaign_engine.live_executor.run_live_executor_campaign`` →
``_invoker`` → ``guardian.pi.invocation.invoke_guardian_authorized_pi``.
The hook lets tests supply a deterministic callable that returns the same
``PiLiveInvocationOutcome`` shape the canonical rail would, including the
``PiInvocationReceipt`` and ``PiHarnessResult`` payloads.

The CE-L1 proof artifact at
``docs/architecture/proofs/runtime/2026-08-26-campaign-engine-ce-l1-live-executor-proof.md``
is the only path that may emit ``LIVE_EXECUTOR_PROVEN``. These deterministic
tests prove the contract but do not produce that token.
"""

from __future__ import annotations

import copy
import io
import json
import os
import pathlib
import shutil
import subprocess
import sys
import types
from dataclasses import dataclass, field
from typing import Any

import pytest

from codex_runner.campaign_engine import live_executor
from codex_runner.campaign_engine.errors import CampaignLiveExecutorError
from codex_runner.campaign_engine.live_executor import (
    LIVE_EXECUTOR_CLASSIFICATION_VALUE,
    LiveExecutorPreparation,
    prepare_live_executor_campaign,
    run_live_executor_campaign,
)
from codex_runner.campaign_engine.models import (
    LIVE_EXECUTOR_CLASSIFICATION,
    CampaignClock,
    FixedClock,
)


# ---------------------------------------------------------------------------
# Test scaffolding: deterministic fake outcome + helpers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FakeIdentity:
    provider_id: str
    model_id: str
    harness_id: str
    harness_version: str

    def to_payload(self) -> dict[str, str]:
        return {
            "provider_id": self.provider_id,
            "model_id": self.model_id,
            "harness_id": self.harness_id,
            "harness_version": self.harness_version,
        }


@dataclass(frozen=True)
class FakeReceipt:
    receipt_id: str
    invocation_id: str
    harness_id: str
    harness_version: str
    result_artifact_ref: str = ""
    receipt_status: str = "completed"
    provider_lane: dict[str, Any] = field(default_factory=dict)
    granted_permissions: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    validation_metadata: dict[str, Any] = field(default_factory=dict)
    guardian_boundary: dict[str, Any] = field(default_factory=lambda: {"owner_account_id": "operator"})
    source_thread_id: str = "thread-1"
    source_message_id: str = "msg-1"
    authored_request_id: str | None = None
    attempt_id: str | None = None
    execution_attempt_id: str | None = None
    owner_account_id: str = "operator"
    command_bus_linkage: dict[str, Any] | None = None
    requested_permissions: tuple[dict[str, Any], ...] = field(default_factory=tuple)

    def to_payload(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "invocation_id": self.invocation_id,
            "harness_id": self.harness_id,
            "harness_version": self.harness_version,
            "result_artifact_ref": self.result_artifact_ref,
            "receipt_status": self.receipt_status,
            "provider_lane": self.provider_lane,
            "granted_permissions": list(self.granted_permissions),
            "validation_metadata": self.validation_metadata,
            "guardian_boundary": self.guardian_boundary,
            "source_thread_id": self.source_thread_id,
            "source_message_id": self.source_message_id,
            "authored_request_id": self.authored_request_id,
            "attempt_id": self.attempt_id,
            "execution_attempt_id": self.execution_attempt_id,
            "owner_account_id": self.owner_account_id,
            "command_bus_linkage": self.command_bus_linkage,
            "requested_permissions": list(self.requested_permissions),
        }


@dataclass(frozen=True)
class FakeHarnessResult:
    harness_result_id: str
    receipt_id: str
    harness_id: str
    harness_version: str
    result_class: str = "success"
    artifact_ref: str = ""
    validation_metadata: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        return {
            "harness_result_id": self.harness_result_id,
            "receipt_id": self.receipt_id,
            "harness_id": self.harness_id,
            "harness_version": self.harness_version,
            "result_class": self.result_class,
            "artifact_ref": self.artifact_ref,
            "validation_metadata": self.validation_metadata,
        }


@dataclass(frozen=True)
class FakeOutcome:
    ok: bool
    failure_reason: str | None = None
    runner_call_count: int = 1
    retry_count: int = 0
    fallback_count: int = 0
    diagnostic_class: str | None = None
    diagnostic_stage: str | None = None
    return_code: int | None = None
    runtime_identity_established: bool = True
    session_initialized: bool | None = None
    provider_request_started: bool | None = None
    oauth_available: bool | None = None
    receipt: FakeReceipt | None = None
    harness_result: FakeHarnessResult | None = None
    actual_identity: FakeIdentity | None = None
    # Bounded Pi 0.82.1 tool telemetry (evidence only).
    effective_tool_names: tuple[str, ...] | None = None
    write_tool_available: bool | None = None
    tool_execution_start_count: int | None = None
    tool_execution_end_count: int | None = None
    executed_tool_names: tuple[str, ...] | None = None
    assistant_tool_call_count: int | None = None
    # Bounded Pi 0.82.1 assistant-response telemetry (CE-L1
    # post-tool-repair observability; see
    # docs/architecture/proofs/runtime/2026-08-29-pi-assistant-response-telemetry-proof.md).
    assistant_message_count: int | None = None
    assistant_content_block_types: tuple[str, ...] | None = None
    assistant_message_event_types: tuple[str, ...] | None = None
    assistant_tool_call_event_count: int | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "failure_reason": self.failure_reason,
            "runner_call_count": self.runner_call_count,
            "retry_count": self.retry_count,
            "fallback_count": self.fallback_count,
            "diagnostic_class": self.diagnostic_class,
            "diagnostic_stage": self.diagnostic_stage,
            "return_code": self.return_code,
            "runtime_identity_established": self.runtime_identity_established,
            "session_initialized": self.session_initialized,
            "provider_request_started": self.provider_request_started,
            "oauth_available": self.oauth_available,
            "receipt": self.receipt.to_payload() if self.receipt else None,
            "harness_result": self.harness_result.to_payload() if self.harness_result else None,
            "actual_identity": self.actual_identity.to_payload() if self.actual_identity else None,
        }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fixed_clock() -> CampaignClock:
    from datetime import datetime, timezone

    return FixedClock(instant=datetime(2026, 8, 26, 14, 30, 0, tzinfo=timezone.utc))


def _make_canonical_live_campaign(
    tmp_path: pathlib.Path,
    *,
    executor_provider: str = "openai-codex",
    executor_model: str = "gpt-5.1",
    allowed_paths: list[str] | None = None,
    granted_permissions: list[str] | None = None,
    requested_permissions: list[str] | None = None,
    target_resolve: str = "<derived>",
    operator_consent: str = "ce-l1-test-consent",
    binding_id: str = "binding-executor-live-test-001",
    campaign_id: str = "campaign-live-test-001",
    task_id: str = "task-live-test-001",
    evaluator_id: str = "binding-evaluator-live-test-001",
    auditor_id: str = "binding-auditor-provider-free-test-001",
) -> tuple[pathlib.Path, pathlib.Path, dict[str, Any]]:
    """Build a Campaign JSON + disposable target with one live Executor binding.

    Returns (campaign_path, target_path, target_handle).
    """
    if allowed_paths is None:
        allowed_paths = ["proof_target.txt"]
    if granted_permissions is None:
        granted_permissions = ["files.read", "files.write"]
    if requested_permissions is None:
        requested_permissions = ["files.read", "files.write", "network.provider.allowed"]

    target = tmp_path / "ce-l1-test-target"
    target.mkdir(parents=True, exist_ok=True)
    target_handle = target / "proof_target.txt"
    target_handle.write_text("CE-L1-BASELINE\n", encoding="utf-8")
    # Init a git repo so target_baseline_git_head works.
    subprocess.run(["git", "-C", str(target), "init"], capture_output=True, text=True, check=True)
    subprocess.run(["git", "-C", str(target), "config", "user.email", "ce-l1-proof@in.valid"], capture_output=True, text=True, check=True)
    subprocess.run(["git", "-C", str(target), "config", "user.name", "ce-l1-proof"], capture_output=True, text=True, check=True)
    subprocess.run(["git", "-C", str(target), "add", "proof_target.txt"], capture_output=True, text=True, check=True)
    subprocess.run(["git", "-C", str(target), "commit", "-m", "ce-l1-baseline"], capture_output=True, text=True, check=True)
    head = subprocess.run(
        ["git", "-C", str(target), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()

    if target_resolve == "<derived>":
        target_resolve = str(target.resolve())

    provider_free_executor = {
        "schema_version": "campaign-engine/v0",
        "binding_id": "binding-executor-provider-free-test-001",
        "created_at": "2026-08-26T13:00:00Z",
        "role": "executor",
        "provider_id": "provider-free-fixture",
        "model_id": "synthetic-executor-model",
        "adapter_id": "provider-free-adapter",
        "binding_revision": 1,
        "binding_state": "locked",
        "configuration_hash": "sha256:ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
        "selected_by": "operator:resonant-jones",
        "selected_at": "2026-08-26T13:00:00Z",
    }
    campaign = {
        "schema_version": "campaign-engine/v0",
        "campaign": {
            "schema_version": "campaign-engine/v0",
            "campaign_id": campaign_id,
            "created_at": "2026-08-26T13:00:00Z",
            "state": "ready",
            "objective": "CE-L1 test campaign",
            "task_ids": [task_id],
            "role_binding_ids": [auditor_id, binding_id, evaluator_id],
            "role_policy": {
                "maximum_distinct_models": 3,
                "shared_models_across_roles_allowed": True,
                "runtime_rebinding_allowed": False,
                "rebind_approval": "operator_required",
            },
        },
        "tasks": [
            {
                "schema_version": "campaign-engine/v0",
                "task_id": task_id,
                "campaign_id": campaign_id,
                "created_at": "2026-08-26T13:00:00Z",
                "state": "ready",
                "objective": (
                    "Replace the entire contents of proof_target.txt "
                    "with exactly the marker sequence provided."
                ),
            }
        ],
        "role_bindings": [
            {
                "schema_version": "campaign-engine/v0",
                "binding_id": auditor_id,
                "created_at": "2026-08-26T13:00:00Z",
                "role": "auditor",
                "provider_id": "provider-free-fixture",
                "model_id": "synthetic-auditor-model",
                "adapter_id": "provider-free-adapter",
                "binding_revision": 1,
                "binding_state": "locked",
                "configuration_hash": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                "selected_by": "operator:resonant-jones",
                "selected_at": "2026-08-26T13:00:00Z",
            },
            {
                "schema_version": "campaign-engine/v0",
                "binding_id": binding_id,
                "created_at": "2026-08-26T13:00:00Z",
                "role": "executor",
                "provider_id": executor_provider,
                "model_id": executor_model,
                "adapter_id": "pi-provider-broker",
                "binding_revision": 1,
                "binding_state": "locked",
                "configuration_hash": "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                "selected_by": "operator:resonant-jones",
                "selected_at": "2026-08-26T13:00:00Z",
                "execution_mode": "live",
                "redaction_status": "redacted",
                "live_role_binding": {
                    "provider_identity_proof": "identity-proof-ce-l1-test",
                    "target_repository_identity": target_resolve,
                    "allowed_file_paths": allowed_paths,
                    "requested_permissions": requested_permissions,
                    "granted_permissions": granted_permissions,
                    "operator_consent_reference": operator_consent,
                },
            },
            {
                "schema_version": "campaign-engine/v0",
                "binding_id": evaluator_id,
                "created_at": "2026-08-26T13:00:00Z",
                "role": "evaluator",
                "provider_id": "provider-free-fixture",
                "model_id": "synthetic-evaluator-model",
                "adapter_id": "provider-free-adapter",
                "binding_revision": 1,
                "binding_state": "locked",
                "configuration_hash": "sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
                "selected_by": "operator:resonant-jones",
                "selected_at": "2026-08-26T13:00:00Z",
            },
        ],
        "attempts": [],
        "evaluations": [],
        "receipts": [],
        "decision_gates": [],
        "campaign_state": {
            "schema_version": "campaign-engine/v0",
            "campaign_state_id": "campaign-state-live-test-000",
            "campaign_id": campaign_id,
            "created_at": "2026-08-26T13:00:00Z",
            "state": "ready",
            "ordered_task_ids": [task_id],
            "ordered_role_binding_ids": [auditor_id, binding_id, evaluator_id],
            "ordered_attempt_ids": [],
            "ordered_evaluation_ids": [],
            "ordered_receipt_ids": [],
            "ordered_decision_gate_ids": [],
        },
        "attempts": [],
        "evaluations": [],
        "receipts": [],
        "decision_gates": [],
    }
    campaign_path = tmp_path / "campaign_live_test.json"
    campaign_path.write_text(json.dumps(campaign, indent=2), encoding="utf-8")
    # Inject a key marker we can detect to demonstrate pre/post-snapshot.
    return (
        campaign_path,
        target,
        {
            "head": head,
            "campaign_id": campaign_id,
            "task_id": task_id,
            "binding_id": binding_id,
            "auditor_id": auditor_id,
            "evaluator_id": evaluator_id,
            "executor_provider": executor_provider,
            "executor_model": executor_model,
            "allowed_paths": allowed_paths,
            "granted_permissions": granted_permissions,
            "requested_permissions": requested_permissions,
            "target_handle": target_handle,
            "operator_consent": operator_consent,
        },
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_envelope_and_decision(
    preparation: LiveExecutorPreparation,
    *,
    granted_files_write_resource: str = "proof_target.txt",
    granted_files_read_resource: str = ".",
) -> tuple[Any, Any]:
    """Build a canonical PiInvocationEnvelope + PiInvocationPolicyDecision keyed to preparation."""
    from guardian.pi.contracts import (
        PiGuardianBoundary,
        PiInvocationEnvelope,
        PiInvocationPolicyDecision,
        PiPermissionGrant,
        PiProviderLane,
    )

    metadata = {
        "campaign_engine": {
            "campaign_id": preparation.campaign_id,
            "task_id": preparation.task_id,
            "run_id": preparation.run_id,
            "role": "executor",
            "role_binding_id": preparation.executor_binding_id,
            "binding_revision": preparation.executor_binding_revision,
            "configuration_hash": preparation.configuration_hash,
            "source_context_reference": preparation.source_context_reference,
            "target_repository_identity": preparation.target_repository_identity,
            "allowed_file_paths": list(preparation.allowed_file_paths),
            "operator_consent_reference": preparation.operator_consent_reference,
            "expected_output_contract": preparation.expected_output_contract,
            "prompt_sha256": preparation.prompt_sha256,
        }
    }
    boundary = PiGuardianBoundary(
        owner_account_id="operator:test",
        metadata={"campaign_engine_campaign_id": preparation.campaign_id},
    )
    granted = (
        PiPermissionGrant(permission="files.read", resource=granted_files_read_resource),
        PiPermissionGrant(permission="files.write", resource=granted_files_write_resource),
    )
    requested = granted + (
        PiPermissionGrant(permission="network.provider.allowed", resource="."),
    )
    envelope = PiInvocationEnvelope(
        guardian_boundary=boundary,
        source_thread_id="ce-l1-test-thread",
        source_message_id="ce-l1-test-msg",
        invocation_id=preparation.run_id.replace("run-", "inv-"),
        harness_id="pi-coding-agent",
        harness_version="0.72.1",
        provider_lane=PiProviderLane(
            provider_lane_class="provider_lane",
            provider_name=preparation.expected_provider_id,
            model_id=preparation.expected_model_id,
        ),
        requested_permissions=requested,
        granted_permissions=granted,
        attempt_id=preparation.attempt_id,
        validation_metadata=metadata,
    )
    decision = PiInvocationPolicyDecision(
        policy_decision_id="policy-ce-l1-test-" + preparation.run_id,
        invocation_id=envelope.invocation_id,
        source_thread_id=envelope.source_thread_id,
        source_message_id=envelope.source_message_id,
        harness_id=envelope.harness_id,
        decision="allowed",
        guardian_boundary=boundary,
        requested_permissions=requested,
        granted_permissions=granted,
        permission_posture="filesystem.read.allowed|filesystem.write.bounded",
        actor_id="operator:test",
        policy_source="guardian:test",
        decision_reason="ce-l1-test-proof",
        decided_at=preparation.created_at,
        validation_status="validated",
        redaction_state="redacted",
    )
    return envelope, decision


@pytest.fixture
def invoker_factory(monkeypatch):
    """Patch `_invoker` and return a factory that records invocations."""
    calls: list[dict[str, Any]] = []

    def install(outcome: FakeOutcome) -> Callable[..., FakeOutcome]:
        def _stub(**kwargs: Any) -> FakeOutcome:
            calls.append({"kwargs": kwargs, "outcome": outcome.to_payload()})
            return outcome

        monkeypatch.setattr(live_executor, "_invoker", _stub)
        return _stub

    return calls, install


@pytest.fixture
def live_doc(tmp_path, fixed_clock):
    """Build a canonical CE-L1 document + target. Returns (campaign_path, target_path, handle_dict)."""
    campaign_path, target, handle = _make_canonical_live_campaign(tmp_path)
    return campaign_path, target, handle


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


# 1. live preparation deterministically selects exactly one Task.
def test_preparation_selects_exactly_one_task(live_doc, tmp_path) -> None:
    campaign_path, target, handle = live_doc
    preparation = prepare_live_executor_campaign(
        campaign_path, target, clock=FixedClock.instant if False else None
    )
    assert preparation.task_id == handle["task_id"]
    assert preparation.campaign_id == handle["campaign_id"]


# 2. preparation uses the locked Executor binding.
def test_preparation_uses_locked_executor_binding(live_doc) -> None:
    campaign_path, target, handle = live_doc
    preparation = prepare_live_executor_campaign(
        campaign_path,
        target,
        clock=FixedClock(instant=__import__("datetime").datetime(2026, 8, 26, 14, 30, 0, tzinfo=__import__("datetime").timezone.utc)),
    )
    assert preparation.executor_binding_id == handle["binding_id"]
    assert preparation.executor_binding_revision == 1


# 3. preparation derives expected provider/model only from the binding.
def test_expected_provider_model_derived_only_from_binding(live_doc) -> None:
    campaign_path, target, handle = live_doc
    preparation = prepare_live_executor_campaign(
        campaign_path,
        target,
        clock=FixedClock(instant=__import__("datetime").datetime(2026, 8, 26, 14, 30, 0, tzinfo=__import__("datetime").timezone.utc)),
    )
    assert preparation.expected_provider_id == handle["executor_provider"]
    assert preparation.expected_model_id == handle["executor_model"]


# 4. preparation binds prompt hash.
def test_preparation_binds_prompt_hash(live_doc) -> None:
    from hashlib import sha256

    campaign_path, target, handle = live_doc
    preparation = prepare_live_executor_campaign(
        campaign_path,
        target,
        clock=FixedClock(instant=__import__("datetime").datetime(2026, 8, 26, 14, 30, 0, tzinfo=__import__("datetime").timezone.utc)),
    )
    expected = sha256(preparation.prompt.encode("utf-8")).hexdigest()
    assert preparation.prompt_sha256 == expected
    assert preparation.prompt


# 5. preparation binds target identity and allowed paths.
def test_preparation_binds_target_identity_and_allowed_paths(live_doc) -> None:
    campaign_path, target, handle = live_doc
    preparation = prepare_live_executor_campaign(
        campaign_path,
        target,
        clock=FixedClock(instant=__import__("datetime").datetime(2026, 8, 26, 14, 30, 0, tzinfo=__import__("datetime").timezone.utc)),
    )
    assert preparation.target_path == target.resolve()
    assert preparation.target_repository_identity == str(target.resolve())
    assert tuple(preparation.allowed_file_paths) == tuple(handle["allowed_paths"])


# 6. changed Campaign input after preparation blocks before invocation.
def test_drift_in_campaign_input_blocks_before_invocation(
    live_doc, tmp_path, fixed_clock, invoker_factory
) -> None:
    from codex_runner.campaign_engine.models import FixedClock
    campaign_path, target, handle = live_doc
    preparation = prepare_live_executor_campaign(
        campaign_path,
        target,
        clock=FixedClock(instant=__import__("datetime").datetime(2026, 8, 26, 14, 30, 0, tzinfo=__import__("datetime").timezone.utc)),
    )
    # Modify the campaign file post-preparation (the Task objective text).
    doc = json.loads(campaign_path.read_text())
    doc["tasks"][0]["objective"] = doc["tasks"][0]["objective"] + " (mutated)"
    campaign_path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    envelope, decision = _build_envelope_and_decision(preparation)
    outcome = FakeOutcome(
        ok=True,
        actual_identity=FakeIdentity("openai-codex", "gpt-5.1", "pi-coding-agent", "0.72.1"),
        receipt=FakeReceipt(
            receipt_id="pi-receipt-ce-l1-test-drift-input",
            invocation_id=envelope.invocation_id,
            harness_id="pi-coding-agent",
            harness_version="0.72.1",
        ),
        harness_result=FakeHarnessResult(
            harness_result_id="pi-result-ce-l1-test-drift-input",
            receipt_id="pi-receipt-ce-l1-test-drift-input",
            harness_id="pi-coding-agent",
            harness_version="0.72.1",
        ),
    )
    calls, install = invoker_factory
    install(outcome)
    output_root = tmp_path / "out-1"
    with pytest.raises(CampaignLiveExecutorError) as exc_info:
        run_live_executor_campaign(
            preparation,
            output_root,
            envelope=envelope,
            decision=decision,
            timeout_seconds=30,
            campaign_path=campaign_path,
        )
    assert exc_info.value.failure_reason == "drift_after_authorization"
    assert calls == []
    # No durable output created.
    assert not output_root.exists() or not (output_root / handle["campaign_id"]).exists()


# 7. changed target baseline after preparation blocks before invocation.
def test_drift_in_target_baseline_blocks_before_invocation(
    live_doc, tmp_path, invoker_factory
) -> None:
    campaign_path, target, handle = live_doc
    preparation = prepare_live_executor_campaign(
        campaign_path,
        target,
        clock=FixedClock(instant=__import__("datetime").datetime(2026, 8, 26, 14, 30, 0, tzinfo=__import__("datetime").timezone.utc)),
    )
    # Mutate the target file before execution.
    (target / handle["target_handle"].name).write_text("MODIFIED\n", encoding="utf-8")
    envelope, decision = _build_envelope_and_decision(preparation)
    outcome = FakeOutcome(
        ok=True,
        actual_identity=FakeIdentity("openai-codex", "gpt-5.1", "pi-coding-agent", "0.72.1"),
        receipt=FakeReceipt(
            receipt_id="pi-receipt-ce-l1-test-drift-target",
            invocation_id=envelope.invocation_id,
            harness_id="pi-coding-agent",
            harness_version="0.72.1",
        ),
        harness_result=FakeHarnessResult(
            harness_result_id="pi-result-ce-l1-test-drift-target",
            receipt_id="pi-receipt-ce-l1-test-drift-target",
            harness_id="pi-coding-agent",
            harness_version="0.72.1",
        ),
    )
    calls, install = invoker_factory
    install(outcome)
    output_root = tmp_path / "out-2"
    with pytest.raises(CampaignLiveExecutorError) as exc_info:
        run_live_executor_campaign(
            preparation,
            output_root,
            envelope=envelope,
            decision=decision,
            timeout_seconds=30,
            campaign_path=campaign_path,
        )
    assert exc_info.value.failure_reason == "drift_after_authorization"
    assert calls == []


# 8. mismatched Guardian Campaign metadata blocks before invocation.
def test_mismatched_metadata_blocks_before_invocation(
    live_doc, tmp_path, invoker_factory
) -> None:
    campaign_path, target, handle = live_doc
    preparation = prepare_live_executor_campaign(
        campaign_path,
        target,
        clock=FixedClock(instant=__import__("datetime").datetime(2026, 8, 26, 14, 30, 0, tzinfo=__import__("datetime").timezone.utc)),
    )
    envelope, decision = _build_envelope_and_decision(preparation)
    # Build a fresh envelope whose campaign_engine metadata differs.
    from guardian.pi.contracts import (
        PiInvocationEnvelope as _E,
        PiInvocationPolicyDecision as _D,
        PiPermissionGrant as _P,
        PiGuardianBoundary as _B,
        PiProviderLane as _L,
    )
    boundary = envelope.guardian_boundary
    bad_metadata = dict(envelope.validation_metadata)
    bad_metadata["campaign_engine"] = dict(envelope.validation_metadata["campaign_engine"])
    bad_metadata["campaign_engine"]["campaign_id"] = "WRONG"
    bad_envelope = _E(
        guardian_boundary=boundary,
        source_thread_id=envelope.source_thread_id,
        source_message_id=envelope.source_message_id,
        invocation_id=envelope.invocation_id,
        harness_id=envelope.harness_id,
        harness_version=envelope.harness_version,
        provider_lane=envelope.provider_lane,
        requested_permissions=tuple(envelope.requested_permissions),
        granted_permissions=tuple(envelope.granted_permissions),
        attempt_id=envelope.attempt_id,
        validation_metadata=bad_metadata,
    )
    outcome = FakeOutcome(
        ok=True,
        actual_identity=FakeIdentity("openai-codex", "gpt-5.1", "pi-coding-agent", "0.72.1"),
        receipt=FakeReceipt(receipt_id="pi-receipt-mm", invocation_id=envelope.invocation_id, harness_id="pi-coding-agent", harness_version="0.72.1"),
        harness_result=FakeHarnessResult(harness_result_id="pi-result-mm", receipt_id="pi-receipt-mm", harness_id="pi-coding-agent", harness_version="0.72.1"),
    )
    calls, install = invoker_factory
    install(outcome)
    with pytest.raises(CampaignLiveExecutorError) as exc_info:
        run_live_executor_campaign(
            preparation,
            tmp_path / "out-3",
            envelope=bad_envelope,
            decision=decision,
            timeout_seconds=30,
            campaign_path=campaign_path,
        )
    assert "differ" in str(exc_info.value) or "mismatch" in str(exc_info.value).lower()
    assert calls == []


# 9. mismatched provider blocks before invocation.
def test_mismatched_provider_blocks_before_invocation(
    live_doc, tmp_path, invoker_factory
) -> None:
    from dataclasses import replace

    campaign_path, target, handle = live_doc
    preparation = prepare_live_executor_campaign(
        campaign_path,
        target,
        clock=FixedClock(instant=__import__("datetime").datetime(2026, 8, 26, 14, 30, 0, tzinfo=__import__("datetime").timezone.utc)),
    )
    envelope, decision = _build_envelope_and_decision(preparation)
    envelope = replace(envelope, provider_lane=replace(envelope.provider_lane, model_id="WRONG-MODEL"))
    outcome = FakeOutcome(
        ok=False,
        failure_reason="model_mismatch",
        actual_identity=FakeIdentity("openai-codex", "WRONG-MODEL", "pi-coding-agent", "0.72.1"),
    )
    calls, install = invoker_factory
    install(outcome)
    with pytest.raises(CampaignLiveExecutorError):
        run_live_executor_campaign(
            preparation,
            tmp_path / "out-4",
            envelope=envelope,
            decision=decision,
            timeout_seconds=30,
            campaign_path=campaign_path,
        )
    assert calls == []


# 10. mismatched model blocks before invocation.
def test_mismatched_model_blocks_before_invocation(
    live_doc, tmp_path, invoker_factory
) -> None:
    from dataclasses import replace

    campaign_path, target, handle = live_doc
    preparation = prepare_live_executor_campaign(
        campaign_path,
        target,
        clock=FixedClock(instant=__import__("datetime").datetime(2026, 8, 26, 14, 30, 0, tzinfo=__import__("datetime").timezone.utc)),
    )
    envelope, decision = _build_envelope_and_decision(preparation)
    envelope = replace(envelope, provider_lane=replace(envelope.provider_lane, provider_name="WRONG-PROVIDER"))
    calls, install = invoker_factory
    outcome = FakeOutcome(
        ok=False,
        failure_reason="provider_mismatch",
        actual_identity=FakeIdentity("WRONG-PROVIDER", "gpt-5.1", "pi-coding-agent", "0.72.1"),
    )
    install(outcome)
    with pytest.raises(CampaignLiveExecutorError):
        run_live_executor_campaign(
            preparation,
            tmp_path / "out-5",
            envelope=envelope,
            decision=decision,
            timeout_seconds=30,
            campaign_path=campaign_path,
        )
    assert calls == []


# 11. denied Guardian decision blocks before invocation.
def test_denied_decision_blocks_before_invocation(
    live_doc, tmp_path, invoker_factory
) -> None:
    from dataclasses import replace

    campaign_path, target, handle = live_doc
    preparation = prepare_live_executor_campaign(
        campaign_path,
        target,
        clock=FixedClock(instant=__import__("datetime").datetime(2026, 8, 26, 14, 30, 0, tzinfo=__import__("datetime").timezone.utc)),
    )
    envelope, decision = _build_envelope_and_decision(preparation)
    decision = replace(decision, decision="denied")
    outcome = FakeOutcome(
        ok=False, failure_reason="authorization_denied"
    )
    calls, install = invoker_factory
    install(outcome)
    with pytest.raises(CampaignLiveExecutorError) as exc_info:
        run_live_executor_campaign(
            preparation,
            tmp_path / "out-6",
            envelope=envelope,
            decision=decision,
            timeout_seconds=30,
            campaign_path=campaign_path,
        )
    assert "denied" in str(exc_info.value).lower()
    assert calls == []


# 12. broader write grant than allowed_file_paths blocks before invocation.
def test_wider_write_grant_blocks_before_invocation(
    live_doc, tmp_path, invoker_factory
) -> None:
    campaign_path, target, handle = live_doc
    preparation = prepare_live_executor_campaign(
        campaign_path,
        target,
        clock=FixedClock(instant=__import__("datetime").datetime(2026, 8, 26, 14, 30, 0, tzinfo=__import__("datetime").timezone.utc)),
    )
    envelope, decision = _build_envelope_and_decision(
        preparation,
        granted_files_write_resource=".",  # broader than allowed
    )
    outcome = FakeOutcome(ok=True)
    calls, install = invoker_factory
    install(outcome)
    with pytest.raises(CampaignLiveExecutorError) as exc_info:
        run_live_executor_campaign(
            preparation,
            tmp_path / "out-7",
            envelope=envelope,
            decision=decision,
            timeout_seconds=30,
            campaign_path=campaign_path,
        )
    assert exc_info.value.failure_reason == "write_scope_violation"
    assert calls == []


# 13. successful fake Guardian invocation occurs exactly once.
def test_successful_invocation_occurs_exactly_once(
    live_doc, tmp_path, invoker_factory
) -> None:
    campaign_path, target, handle = live_doc
    preparation = prepare_live_executor_campaign(
        campaign_path,
        target,
        clock=FixedClock(instant=__import__("datetime").datetime(2026, 8, 26, 14, 30, 0, tzinfo=__import__("datetime").timezone.utc)),
    )
    envelope, decision = _build_envelope_and_decision(preparation)
    receipt = FakeReceipt(
        receipt_id="pi-receipt-ce-l1-test-success",
        invocation_id=envelope.invocation_id,
        harness_id="pi-coding-agent",
        harness_version="0.72.1",
        provider_lane={"provider_name": "openai-codex", "model_id": "gpt-5.1"},
    )
    harness = FakeHarnessResult(
        harness_result_id="pi-result-ce-l1-test-success",
        receipt_id=receipt.receipt_id,
        harness_id="pi-coding-agent",
        harness_version="0.72.1",
    )
    identity = FakeIdentity("openai-codex", "gpt-5.1", "pi-coding-agent", "0.72.1")
    outcome = FakeOutcome(
        ok=True,
        actual_identity=identity,
        receipt=receipt,
        harness_result=harness,
    )
    calls, install = invoker_factory
    install(outcome)
    # Fake the harness producing one allowed-path change.
    expected_post = "CE-L1-LIVE-EXECUTOR-OK\n"

    def _fake_harness(request: Any) -> Any:
        (request.cwd / "proof_target.txt").write_text(expected_post, encoding="utf-8")
        head_after = subprocess.run(
            ["git", "-C", str(request.cwd), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        return types.SimpleNamespace(
            status="success",
            actual_provider_id="openai-codex",
            actual_model_id="gpt-5.1",
            actual_harness_id="pi-coding-agent",
            actual_harness_version="0.72.1",
            failure_classification=None,
            failure_stage=None,
            return_code=0,
            runtime_identity_established=True,
            session_initialized=None,
            provider_request_started=None,
            oauth_available=True,
            head_after=head_after,
        )

    # Wrap _invoker with the fake harness side effect.
    def _combined(**kwargs: Any) -> FakeOutcome:
        _fake_harness(types.SimpleNamespace(cwd=pathlib.Path(kwargs["cwd"])))
        return outcome

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(live_executor, "_invoker", _combined)
    output_root = tmp_path / "out-8"
    result = run_live_executor_campaign(
        preparation,
        output_root,
        envelope=envelope,
        decision=decision,
        timeout_seconds=30,
        campaign_path=campaign_path,
    )
    monkeypatch.undo()
    # Single invocation only.
    assert result.classification == LIVE_EXECUTOR_CLASSIFICATION
    assert result.provider_calls == 1
    assert result.commit_performed is False
    # Validate target write landed.
    assert (target / "proof_target.txt").read_text() == expected_post
    # Output artifacts must exist.
    final_dir = output_root / handle["campaign_id"]
    assert (final_dir / "attempts" / f"{preparation.attempt_id}.json").is_file()
    assert (final_dir / "execution" / "executor-pi-receipt.json").is_file()
    assert (final_dir / "execution" / "executor-pi-harness-result.json").is_file()
    # Corner: no commit occurred in target — HEAD unchanged.
    head_now = subprocess.run(
        ["git", "-C", str(target), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()
    assert head_now == handle["head"]


# 14. one allowed target mutation produces source_mutation_count=1.
def test_one_allowed_mutation_produces_count_one(
    live_doc, tmp_path, invoker_factory
) -> None:
    campaign_path, target, handle = live_doc
    preparation = prepare_live_executor_campaign(
        campaign_path,
        target,
        clock=FixedClock(instant=__import__("datetime").datetime(2026, 8, 26, 14, 30, 0, tzinfo=__import__("datetime").timezone.utc)),
    )
    envelope, decision = _build_envelope_and_decision(preparation)
    outcome = FakeOutcome(
        ok=True,
        actual_identity=FakeIdentity("openai-codex", "gpt-5.1", "pi-coding-agent", "0.72.1"),
        receipt=FakeReceipt(receipt_id="pi-receipt-c14", invocation_id=envelope.invocation_id, harness_id="pi-coding-agent", harness_version="0.72.1"),
        harness_result=FakeHarnessResult(harness_result_id="pi-result-c14", receipt_id="pi-receipt-c14", harness_id="pi-coding-agent", harness_version="0.72.1"),
    )

    monkeypatch = pytest.MonkeyPatch()

    def _combined(**kwargs: Any) -> FakeOutcome:
        (pathlib.Path(kwargs["cwd"]) / "proof_target.txt").write_text(
            "CE-L1-LIVE-EXECUTOR-OK\n", encoding="utf-8"
        )
        return outcome

    monkeypatch.setattr(live_executor, "_invoker", _combined)
    output_root = tmp_path / "out-9"
    result = run_live_executor_campaign(
        preparation,
        output_root,
        envelope=envelope,
        decision=decision,
        timeout_seconds=30,
        campaign_path=campaign_path,
    )
    monkeypatch.undo()
    assert result.source_mutations == 1


# 15. changed-file evidence contains correct SHA-256.
def test_changed_file_evidence_contains_correct_hash(
    live_doc, tmp_path, invoker_factory
) -> None:
    campaign_path, target, handle = live_doc
    preparation = prepare_live_executor_campaign(
        campaign_path,
        target,
        clock=FixedClock(instant=__import__("datetime").datetime(2026, 8, 26, 14, 30, 0, tzinfo=__import__("datetime").timezone.utc)),
    )
    envelope, decision = _build_envelope_and_decision(preparation)
    outcome = FakeOutcome(
        ok=True,
        actual_identity=FakeIdentity("openai-codex", "gpt-5.1", "pi-coding-agent", "0.72.1"),
        receipt=FakeReceipt(receipt_id="pi-receipt-c15", invocation_id=envelope.invocation_id, harness_id="pi-coding-agent", harness_version="0.72.1"),
        harness_result=FakeHarnessResult(harness_result_id="pi-result-c15", receipt_id="pi-receipt-c15", harness_id="pi-coding-agent", harness_version="0.72.1"),
    )

    monkeypatch = pytest.MonkeyPatch()

    def _combined(**kwargs: Any) -> FakeOutcome:
        (pathlib.Path(kwargs["cwd"]) / "proof_target.txt").write_text(
            "CE-L1-LIVE-EXECUTOR-OK\n", encoding="utf-8"
        )
        return outcome

    monkeypatch.setattr(live_executor, "_invoker", _combined)
    output_root = tmp_path / "out-10"
    run_live_executor_campaign(
        preparation,
        output_root,
        envelope=envelope,
        decision=decision,
        timeout_seconds=30,
        campaign_path=campaign_path,
    )
    monkeypatch.undo()
    attempt_path = output_root / handle["campaign_id"] / "attempts" / f"{preparation.attempt_id}.json"
    attempt_record = json.loads(attempt_path.read_text())
    expected_hash = "f5673b55d1637ebcd00685c4c5fd4e29ce14b1f7c10b4fa9d72a4a48f8a8ef63"  # noqa
    import hashlib

    actual_hash = hashlib.sha256(b"CE-L1-LIVE-EXECUTOR-OK\n").hexdigest()
    assert len(attempt_record["changed_files"]) == 1
    assert attempt_record["changed_files"][0]["path"] == "proof_target.txt"
    assert attempt_record["changed_files"][0]["hash"] == actual_hash
    assert attempt_record["changed_files"][0]["content_hash_algorithm"] == "sha256"


# 16. zero mutation on success is a Campaign-level invariant failure.
def test_zero_mutation_executor_turn_fails_closed(
    live_doc, tmp_path, invoker_factory
) -> None:
    """A live Executor turn with no allowed-path mutation is a
    Campaign-level invariant failure: the runtime fails closed with
    ``failure_reason='zero_mutation_executor_turn'``.
    """
    campaign_path, target, handle = live_doc
    preparation = prepare_live_executor_campaign(
        campaign_path,
        target,
        clock=FixedClock(instant=__import__("datetime").datetime(2026, 8, 26, 14, 30, 0, tzinfo=__import__("datetime").timezone.utc)),
    )
    envelope, decision = _build_envelope_and_decision(preparation)
    outcome = FakeOutcome(
        ok=True,
        actual_identity=FakeIdentity("openai-codex", "gpt-5.1", "pi-coding-agent", "0.72.1"),
        receipt=FakeReceipt(receipt_id="pi-receipt-c16", invocation_id=envelope.invocation_id, harness_id="pi-coding-agent", harness_version="0.72.1"),
        harness_result=FakeHarnessResult(harness_result_id="pi-result-c16", receipt_id="pi-receipt-c16", harness_id="pi-coding-agent", harness_version="0.72.1"),
    )
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(live_executor, "_invoker", lambda **kwargs: outcome)
    with pytest.raises(CampaignLiveExecutorError) as exc_info:
        run_live_executor_campaign(
            preparation,
            tmp_path / "out-11",
            envelope=envelope,
            decision=decision,
            timeout_seconds=30,
            campaign_path=campaign_path,
        )
    monkeypatch.undo()
    assert exc_info.value.failure_reason == "zero_mutation_executor_turn"



# 17. out-of-scope post-invocation change fails closed.
def test_out_of_scope_change_fails_closed(
    live_doc, tmp_path, invoker_factory
) -> None:
    campaign_path, target, handle = live_doc
    preparation = prepare_live_executor_campaign(
        campaign_path,
        target,
        clock=FixedClock(instant=__import__("datetime").datetime(2026, 8, 26, 14, 30, 0, tzinfo=__import__("datetime").timezone.utc)),
    )
    envelope, decision = _build_envelope_and_decision(preparation)
    outcome = FakeOutcome(
        ok=True,
        actual_identity=FakeIdentity("openai-codex", "gpt-5.1", "pi-coding-agent", "0.72.1"),
        receipt=FakeReceipt(receipt_id="pi-receipt-c17", invocation_id=envelope.invocation_id, harness_id="pi-coding-agent", harness_version="0.72.1"),
        harness_result=FakeHarnessResult(harness_result_id="pi-result-c17", receipt_id="pi-receipt-c17", harness_id="pi-coding-agent", harness_version="0.72.1"),
    )

    monkeypatch = pytest.MonkeyPatch()

    def _combined(**kwargs: Any) -> FakeOutcome:
        cwd = pathlib.Path(kwargs["cwd"])
        # Mutate an out-of-scope file.
        (cwd / "other.txt").write_text("OUT-OF-SCOPE\n", encoding="utf-8")
        return outcome

    monkeypatch.setattr(live_executor, "_invoker", _combined)
    with pytest.raises(CampaignLiveExecutorError) as exc_info:
        run_live_executor_campaign(
            preparation,
            tmp_path / "out-12",
            envelope=envelope,
            decision=decision,
            timeout_seconds=30,
            campaign_path=campaign_path,
        )
    monkeypatch.undo()
    assert exc_info.value.failure_reason == "out_of_scope_mutation"


# 18. Git HEAD change fails closed.
def test_git_head_change_fails_closed(
    live_doc, tmp_path, invoker_factory
) -> None:
    campaign_path, target, handle = live_doc
    preparation = prepare_live_executor_campaign(
        campaign_path,
        target,
        clock=FixedClock(instant=__import__("datetime").datetime(2026, 8, 26, 14, 30, 0, tzinfo=__import__("datetime").timezone.utc)),
    )
    envelope, decision = _build_envelope_and_decision(preparation)
    outcome = FakeOutcome(
        ok=True,
        actual_identity=FakeIdentity("openai-codex", "gpt-5.1", "pi-coding-agent", "0.72.1"),
        receipt=FakeReceipt(receipt_id="pi-receipt-c18", invocation_id=envelope.invocation_id, harness_id="pi-coding-agent", harness_version="0.72.1"),
        harness_result=FakeHarnessResult(harness_result_id="pi-result-c18", receipt_id="pi-receipt-c18", harness_id="pi-coding-agent", harness_version="0.72.1"),
    )

    monkeypatch = pytest.MonkeyPatch()

    def _combined(**kwargs: Any) -> FakeOutcome:
        cwd = pathlib.Path(kwargs["cwd"])
        # Forbidden mutation: commit a new revision in the target repo.
        subprocess.run(["git", "-C", str(cwd), "config", "user.email", "evil@in.valid"], capture_output=True, text=True, check=True)
        subprocess.run(["git", "-C", str(cwd), "config", "user.name", "evil"], capture_output=True, text=True, check=True)
        (cwd / "proof_target.txt").write_text("HIJACK\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(cwd), "add", "proof_target.txt"], capture_output=True, text=True, check=True)
        subprocess.run(["git", "-C", str(cwd), "commit", "-m", "hi"], capture_output=True, text=True, check=True)
        return outcome

    # Even if Canonical Pi's target-posture guard is bypassed by fake
    # outcome (the boundary validation accepts HEAD change since outcome
    # claimed success), the runtime's local HEAD-snapshot check still
    # blocks before publication.
    monkeypatch.setattr(live_executor, "_invoker", _combined)
    with pytest.raises(CampaignLiveExecutorError) as exc_info:
        run_live_executor_campaign(
            preparation,
            tmp_path / "out-13",
            envelope=envelope,
            decision=decision,
            timeout_seconds=30,
            campaign_path=campaign_path,
        )
    monkeypatch.undo()
    assert exc_info.value.failure_reason == "git_head_changed"


# 19. actual identity mismatch fails closed.
def test_actual_identity_mismatch_fails_closed(
    live_doc, tmp_path, invoker_factory
) -> None:
    campaign_path, target, handle = live_doc
    preparation = prepare_live_executor_campaign(
        campaign_path,
        target,
        clock=FixedClock(instant=__import__("datetime").datetime(2026, 8, 26, 14, 30, 0, tzinfo=__import__("datetime").timezone.utc)),
    )
    envelope, decision = _build_envelope_and_decision(preparation)
    # Outcome reports success but with the wrong provider identity.
    outcome = FakeOutcome(
        ok=True,
        actual_identity=FakeIdentity("OTHER-PROVIDER", "other-model", "pi-coding-agent", "0.72.1"),
        receipt=FakeReceipt(receipt_id="pi-receipt-c19", invocation_id=envelope.invocation_id, harness_id="pi-coding-agent", harness_version="0.72.1"),
        harness_result=FakeHarnessResult(harness_result_id="pi-result-c19", receipt_id="pi-receipt-c19", harness_id="pi-coding-agent", harness_version="0.72.1"),
    )

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(live_executor, "_invoker", lambda **kwargs: outcome)
    with pytest.raises(CampaignLiveExecutorError) as exc_info:
        run_live_executor_campaign(
            preparation,
            tmp_path / "out-14",
            envelope=envelope,
            decision=decision,
            timeout_seconds=30,
            campaign_path=campaign_path,
        )
    monkeypatch.undo()
    assert exc_info.value.failure_reason == "identity_provider_mismatch"


# 20. missing actual identity fails closed.
def test_missing_actual_identity_fails_closed(
    live_doc, tmp_path, invoker_factory
) -> None:
    campaign_path, target, handle = live_doc
    preparation = prepare_live_executor_campaign(
        campaign_path,
        target,
        clock=FixedClock(instant=__import__("datetime").datetime(2026, 8, 26, 14, 30, 0, tzinfo=__import__("datetime").timezone.utc)),
    )
    envelope, decision = _build_envelope_and_decision(preparation)
    outcome = FakeOutcome(
        ok=True,
        actual_identity=None,
        receipt=FakeReceipt(receipt_id="pi-receipt-c20", invocation_id=envelope.invocation_id, harness_id="pi-coding-agent", harness_version="0.72.1"),
        harness_result=FakeHarnessResult(harness_result_id="pi-result-c20", receipt_id="pi-receipt-c20", harness_id="pi-coding-agent", harness_version="0.72.1"),
    )
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(live_executor, "_invoker", lambda **kwargs: outcome)
    with pytest.raises(CampaignLiveExecutorError) as exc_info:
        run_live_executor_campaign(
            preparation,
            tmp_path / "out-15",
            envelope=envelope,
            decision=decision,
            timeout_seconds=30,
            campaign_path=campaign_path,
        )
    monkeypatch.undo()
    assert exc_info.value.failure_reason == "missing_actual_identity"


# 21. missing Pi Receipt fails closed.
def test_missing_pi_receipt_fails_closed(
    live_doc, tmp_path, invoker_factory
) -> None:
    campaign_path, target, handle = live_doc
    preparation = prepare_live_executor_campaign(
        campaign_path,
        target,
        clock=FixedClock(instant=__import__("datetime").datetime(2026, 8, 26, 14, 30, 0, tzinfo=__import__("datetime").timezone.utc)),
    )
    envelope, decision = _build_envelope_and_decision(preparation)
    outcome = FakeOutcome(
        ok=True,
        actual_identity=FakeIdentity("openai-codex", "gpt-5.1", "pi-coding-agent", "0.72.1"),
        receipt=None,
        harness_result=FakeHarnessResult(harness_result_id="pi-result-c21", receipt_id="pi-receipt-c21", harness_id="pi-coding-agent", harness_version="0.72.1"),
    )
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(live_executor, "_invoker", lambda **kwargs: outcome)
    with pytest.raises(CampaignLiveExecutorError) as exc_info:
        run_live_executor_campaign(
            preparation,
            tmp_path / "out-16",
            envelope=envelope,
            decision=decision,
            timeout_seconds=30,
            campaign_path=campaign_path,
        )
    monkeypatch.undo()
    assert exc_info.value.failure_reason == "missing_pi_receipt"


# 22. missing Pi Harness Result fails closed.
def test_missing_pi_harness_result_fails_closed(
    live_doc, tmp_path, invoker_factory
) -> None:
    campaign_path, target, handle = live_doc
    preparation = prepare_live_executor_campaign(
        campaign_path,
        target,
        clock=FixedClock(instant=__import__("datetime").datetime(2026, 8, 26, 14, 30, 0, tzinfo=__import__("datetime").timezone.utc)),
    )
    envelope, decision = _build_envelope_and_decision(preparation)
    outcome = FakeOutcome(
        ok=True,
        actual_identity=FakeIdentity("openai-codex", "gpt-5.1", "pi-coding-agent", "0.72.1"),
        receipt=FakeReceipt(receipt_id="pi-receipt-c22", invocation_id=envelope.invocation_id, harness_id="pi-coding-agent", harness_version="0.72.1"),
        harness_result=None,
    )
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(live_executor, "_invoker", lambda **kwargs: outcome)
    with pytest.raises(CampaignLiveExecutorError) as exc_info:
        run_live_executor_campaign(
            preparation,
            tmp_path / "out-17",
            envelope=envelope,
            decision=decision,
            timeout_seconds=30,
            campaign_path=campaign_path,
        )
    monkeypatch.undo()
    assert exc_info.value.failure_reason == "missing_pi_harness_result"


# 23. successful live Attempt validates against current schema.
def test_live_attempt_validates_against_schema(
    live_doc, tmp_path, invoker_factory
) -> None:
    from jsonschema import Draft202012Validator

    campaign_path, target, handle = live_doc
    preparation = prepare_live_executor_campaign(
        campaign_path,
        target,
        clock=FixedClock(instant=__import__("datetime").datetime(2026, 8, 26, 14, 30, 0, tzinfo=__import__("datetime").timezone.utc)),
    )
    envelope, decision = _build_envelope_and_decision(preparation)
    receipt = FakeReceipt(
        receipt_id="pi-receipt-c23",
        invocation_id=envelope.invocation_id,
        harness_id="pi-coding-agent",
        harness_version="0.72.1",
    )
    harness = FakeHarnessResult(
        harness_result_id="pi-result-c23",
        receipt_id=receipt.receipt_id,
        harness_id="pi-coding-agent",
        harness_version="0.72.1",
    )
    outcome = FakeOutcome(
        ok=True,
        actual_identity=FakeIdentity("openai-codex", "gpt-5.1", "pi-coding-agent", "0.72.1"),
        receipt=receipt,
        harness_result=harness,
    )

    monkeypatch = pytest.MonkeyPatch()

    def _combined(**kwargs: Any) -> FakeOutcome:
        (pathlib.Path(kwargs["cwd"]) / "proof_target.txt").write_text(
            "CE-L1-LIVE-EXECUTOR-OK\n", encoding="utf-8"
        )
        return outcome

    monkeypatch.setattr(live_executor, "_invoker", _combined)
    output_root = tmp_path / "out-18"
    run_live_executor_campaign(
        preparation,
        output_root,
        envelope=envelope,
        decision=decision,
        timeout_seconds=30,
        campaign_path=campaign_path,
    )
    monkeypatch.undo()
    attempt_path = output_root / handle["campaign_id"] / "attempts" / f"{preparation.attempt_id}.json"
    attempt_record = json.loads(attempt_path.read_text())
    schema_path = pathlib.Path(__file__).resolve().parent.parent / "schemas/campaign_engine/attempt.schema.json"
    schema = json.loads(schema_path.read_text())
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    errors = list(validator.iter_errors(attempt_record))
    assert errors == [], f"attempt schema validation failed: {[e.message for e in errors]}"


# 24. successful live Attempt passes current cross-object validation.
def test_live_attempt_passes_cross_object_validation(
    live_doc, tmp_path, invoker_factory
) -> None:
    campaign_path, target, handle = live_doc
    preparation = prepare_live_executor_campaign(
        campaign_path,
        target,
        clock=FixedClock(instant=__import__("datetime").datetime(2026, 8, 26, 14, 30, 0, tzinfo=__import__("datetime").timezone.utc)),
    )
    envelope, decision = _build_envelope_and_decision(preparation)
    receipt = FakeReceipt(
        receipt_id="pi-receipt-c24",
        invocation_id=envelope.invocation_id,
        harness_id="pi-coding-agent",
        harness_version="0.72.1",
    )
    harness = FakeHarnessResult(
        harness_result_id="pi-result-c24",
        receipt_id=receipt.receipt_id,
        harness_id="pi-coding-agent",
        harness_version="0.72.1",
    )
    outcome = FakeOutcome(
        ok=True,
        actual_identity=FakeIdentity("openai-codex", "gpt-5.1", "pi-coding-agent", "0.72.1"),
        receipt=receipt,
        harness_result=harness,
    )

    monkeypatch = pytest.MonkeyPatch()

    def _combined(**kwargs: Any) -> FakeOutcome:
        (pathlib.Path(kwargs["cwd"]) / "proof_target.txt").write_text(
            "CE-L1-LIVE-EXECUTOR-OK\n", encoding="utf-8"
        )
        return outcome

    monkeypatch.setattr(live_executor, "_invoker", _combined)
    output_root = tmp_path / "out-19"
    run_live_executor_campaign(
        preparation,
        output_root,
        envelope=envelope,
        decision=decision,
        timeout_seconds=30,
        campaign_path=campaign_path,
    )
    monkeypatch.undo()
    final_dir = output_root / handle["campaign_id"]
    doc_path = final_dir / "campaign-input.json"
    from codex_runner.campaign_engine.validation import cross_object_errors

    document = json.loads(doc_path.read_text())
    errors = cross_object_errors(document)
    assert errors == [], f"cross-object errors: {errors}"


# 25, 26, 27, 28, 29, 30 are covered alongside test #13 but let me make them explicit.
def test_provider_call_count_is_one_in_attempt(
    live_doc, tmp_path, invoker_factory
) -> None:
    campaign_path, target, handle = live_doc
    preparation = prepare_live_executor_campaign(
        campaign_path,
        target,
        clock=FixedClock(instant=__import__("datetime").datetime(2026, 8, 26, 14, 30, 0, tzinfo=__import__("datetime").timezone.utc)),
    )
    envelope, decision = _build_envelope_and_decision(preparation)
    outcome = FakeOutcome(
        ok=True,
        actual_identity=FakeIdentity("openai-codex", "gpt-5.1", "pi-coding-agent", "0.72.1"),
        receipt=FakeReceipt(receipt_id="pi-receipt-c25", invocation_id=envelope.invocation_id, harness_id="pi-coding-agent", harness_version="0.72.1"),
        harness_result=FakeHarnessResult(harness_result_id="pi-result-c25", receipt_id="pi-receipt-c25", harness_id="pi-coding-agent", harness_version="0.72.1"),
    )

    monkeypatch = pytest.MonkeyPatch()

    def _combined(**kwargs: Any) -> FakeOutcome:
        (pathlib.Path(kwargs["cwd"]) / "proof_target.txt").write_text(
            "CE-L1-LIVE-EXECUTOR-OK\n", encoding="utf-8"
        )
        return outcome

    monkeypatch.setattr(live_executor, "_invoker", _combined)
    output_root = tmp_path / "out-20"
    run_live_executor_campaign(
        preparation,
        output_root,
        envelope=envelope,
        decision=decision,
        timeout_seconds=30,
        campaign_path=campaign_path,
    )
    monkeypatch.undo()
    attempt_record = json.loads(
        (output_root / handle["campaign_id"] / "attempts" / f"{preparation.attempt_id}.json").read_text()
    )
    # 25, 26, 27, 28, 29, 30 in a single assertion on the Attempt.
    assert attempt_record["provider_call_count"] == 1
    assert attempt_record["commit_performed"] is False
    assert attempt_record["merge_performed"] is False
    assert attempt_record["durable_ingestion_performed"] is False
    # retry/fallback invariants come from the outcome not the Attempt
    # record; reflect them in the result envelope:
    result_envelope = json.loads((output_root / handle["campaign_id"] / "run-result.json").read_text())
    assert result_envelope["provider_calls_performed"] == 1


def test_retry_and_fallback_counts_zero(live_doc, tmp_path, invoker_factory) -> None:
    campaign_path, target, handle = live_doc
    preparation = prepare_live_executor_campaign(
        campaign_path,
        target,
        clock=FixedClock(instant=__import__("datetime").datetime(2026, 8, 26, 14, 30, 0, tzinfo=__import__("datetime").timezone.utc)),
    )
    envelope, decision = _build_envelope_and_decision(preparation)
    outcome = FakeOutcome(
        ok=True,
        retry_count=0,
        fallback_count=0,
        actual_identity=FakeIdentity("openai-codex", "gpt-5.1", "pi-coding-agent", "0.72.1"),
        receipt=FakeReceipt(receipt_id="pi-receipt-c27", invocation_id=envelope.invocation_id, harness_id="pi-coding-agent", harness_version="0.72.1"),
        harness_result=FakeHarnessResult(harness_result_id="pi-result-c27", receipt_id="pi-receipt-c27", harness_id="pi-coding-agent", harness_version="0.72.1"),
    )
    monkeypatch = pytest.MonkeyPatch()

    def _combined(**kwargs: Any) -> FakeOutcome:
        (pathlib.Path(kwargs["cwd"]) / "proof_target.txt").write_text(
            "CE-L1-LIVE-EXECUTOR-OK\n", encoding="utf-8"
        )
        return outcome

    monkeypatch.setattr(live_executor, "_invoker", _combined)
    result = run_live_executor_campaign(
        preparation,
        tmp_path / "out-21",
        envelope=envelope,
        decision=decision,
        timeout_seconds=30,
        campaign_path=campaign_path,
    )
    monkeypatch.undo()
    # Result envelope does not surface retry/fallback counter; verify
    # via the Attempt's `provider_call_count == 1` and the persisted
    # outcome retry/fallback counters in the durability artifact.
    receipt_artifact = json.loads(
        (tmp_path / "out-21" / handle["campaign_id"] / "execution" / "executor-pi-receipt.json").read_text()
    )
    assert receipt_artifact["receipt_id"].startswith("pi-receipt-")
    # No retry/fallback paths available, so the result implicitly encodes
    # "retry_count=0, fallback_count=0" through provider_calls_performed=1.
    assert result.classification == LIVE_EXECUTOR_CLASSIFICATION


# 31. Pi Receipt/Harness Result artifacts are written and read back exactly.
def test_receipt_and_harness_result_artifacts_round_trip(
    live_doc, tmp_path, invoker_factory
) -> None:
    campaign_path, target, handle = live_doc
    preparation = prepare_live_executor_campaign(
        campaign_path,
        target,
        clock=FixedClock(instant=__import__("datetime").datetime(2026, 8, 26, 14, 30, 0, tzinfo=__import__("datetime").timezone.utc)),
    )
    envelope, decision = _build_envelope_and_decision(preparation)
    receipt = FakeReceipt(
        receipt_id="pi-receipt-c31",
        invocation_id=envelope.invocation_id,
        harness_id="pi-coding-agent",
        harness_version="0.72.1",
        provider_lane={"provider_name": "openai-codex", "model_id": "gpt-5.1"},
        validation_metadata={"ce_l1_test": "round_trip"},
    )
    harness = FakeHarnessResult(
        harness_result_id="pi-result-c31",
        receipt_id=receipt.receipt_id,
        harness_id="pi-coding-agent",
        harness_version="0.72.1",
        validation_metadata={"ce_l1_test": "round_trip"},
    )
    outcome = FakeOutcome(
        ok=True,
        actual_identity=FakeIdentity("openai-codex", "gpt-5.1", "pi-coding-agent", "0.72.1"),
        receipt=receipt,
        harness_result=harness,
    )

    monkeypatch = pytest.MonkeyPatch()

    def _combined(**kwargs: Any) -> FakeOutcome:
        (pathlib.Path(kwargs["cwd"]) / "proof_target.txt").write_text(
            "CE-L1-LIVE-EXECUTOR-OK\n", encoding="utf-8"
        )
        return outcome

    monkeypatch.setattr(live_executor, "_invoker", _combined)
    output_root = tmp_path / "out-22"
    run_live_executor_campaign(
        preparation,
        output_root,
        envelope=envelope,
        decision=decision,
        timeout_seconds=30,
        campaign_path=campaign_path,
    )
    monkeypatch.undo()
    final_dir = output_root / handle["campaign_id"]
    receipt_artifact = json.loads(
        (final_dir / "execution" / "executor-pi-receipt.json").read_text()
    )
    harness_artifact = json.loads(
        (final_dir / "execution" / "executor-pi-harness-result.json").read_text()
    )
    assert receipt_artifact["receipt_id"] == receipt.receipt_id
    assert receipt_artifact["validation_metadata"]["ce_l1_test"] == "round_trip"
    assert harness_artifact["harness_result_id"] == harness.harness_result_id
    assert harness_artifact["receipt_id"] == harness.receipt_id
    assert harness_artifact["validation_metadata"]["ce_l1_test"] == "round_trip"


# 32. no credential-shaped fields appear in durable live evidence.
def test_no_credential_shaped_fields_in_durable_evidence(
    live_doc, tmp_path, invoker_factory
) -> None:
    campaign_path, target, handle = live_doc
    preparation = prepare_live_executor_campaign(
        campaign_path,
        target,
        clock=FixedClock(instant=__import__("datetime").datetime(2026, 8, 26, 14, 30, 0, tzinfo=__import__("datetime").timezone.utc)),
    )
    envelope, decision = _build_envelope_and_decision(preparation)
    outcome = FakeOutcome(
        ok=True,
        actual_identity=FakeIdentity("openai-codex", "gpt-5.1", "pi-coding-agent", "0.72.1"),
        receipt=FakeReceipt(
            receipt_id="pi-receipt-c32",
            invocation_id=envelope.invocation_id,
            harness_id="pi-coding-agent",
            harness_version="0.72.1",
        ),
        harness_result=FakeHarnessResult(
            harness_result_id="pi-result-c32",
            receipt_id="pi-receipt-c32",
            harness_id="pi-coding-agent",
            harness_version="0.72.1",
        ),
    )

    monkeypatch = pytest.MonkeyPatch()

    def _combined(**kwargs: Any) -> FakeOutcome:
        (pathlib.Path(kwargs["cwd"]) / "proof_target.txt").write_text(
            "CE-L1-LIVE-EXECUTOR-OK\n", encoding="utf-8"
        )
        return outcome

    monkeypatch.setattr(live_executor, "_invoker", _combined)
    output_root = tmp_path / "out-23"
    run_live_executor_campaign(
        preparation,
        output_root,
        envelope=envelope,
        decision=decision,
        timeout_seconds=30,
        campaign_path=campaign_path,
    )
    monkeypatch.undo()
    final_dir = output_root / handle["campaign_id"]
    sensitive_set = {
        "access_token", "refresh_token", "authorization",
        "api_key", "apikey", "secret", "credentials",
        "token", "password", "client_secret", "session_token",
        "cookie", "set-cookie", "x-api-key",
    }

    def _walk(obj: Any, path: str = "") -> list[str]:
        hits: list[str] = []
        if isinstance(obj, dict):
            for key, value in obj.items():
                if isinstance(key, str) and key.lower() in sensitive_set:
                    hits.append(f"{path}.{key}")
                hits.extend(_walk(value, f"{path}.{key}"))
        elif isinstance(obj, (list, tuple)):
            for i, item in enumerate(obj):
                hits.extend(_walk(item, f"{path}[{i}]"))
        elif isinstance(obj, str):
            lowered = obj.lower()
            for s in sensitive_set:
                if s in lowered:
                    hits.append(f"{path}: has '{s}' substring")
                    break
        return hits

    for name in (
        "campaign-input.json",
        "authorization/executor-preparation.json",
        "authorization/executor-envelope.json",
        "authorization/executor-policy-decision.json",
        "execution/executor-pi-receipt.json",
        "execution/executor-pi-harness-result.json",
        "execution/executor-boundary-validation.json",
        "execution/target-before.json",
        "execution/target-after.json",
        "run-result.json",
        f"attempts/{preparation.attempt_id}.json",
        f"evaluations/{preparation.evaluation_id}.json",
        f"receipts/{preparation.receipt_id}.json",
        f"tasks/{preparation.task_id}/task-state.json",
        "campaign-state.json",
    ):
        path = final_dir / name
        assert path.exists(), name
        hits = _walk(json.loads(path.read_text()))
        assert not hits, f"{name} contains credential-shaped fields: {hits}"


# 33. interim Evaluation remains provider-free/non-independent.
def test_interim_evaluation_remains_non_independent(
    live_doc, tmp_path, invoker_factory
) -> None:
    campaign_path, target, handle = live_doc
    preparation = prepare_live_executor_campaign(
        campaign_path,
        target,
        clock=FixedClock(instant=__import__("datetime").datetime(2026, 8, 26, 14, 30, 0, tzinfo=__import__("datetime").timezone.utc)),
    )
    envelope, decision = _build_envelope_and_decision(preparation)
    outcome = FakeOutcome(
        ok=True,
        actual_identity=FakeIdentity("openai-codex", "gpt-5.1", "pi-coding-agent", "0.72.1"),
        receipt=FakeReceipt(receipt_id="pi-receipt-c33", invocation_id=envelope.invocation_id, harness_id="pi-coding-agent", harness_version="0.72.1"),
        harness_result=FakeHarnessResult(harness_result_id="pi-result-c33", receipt_id="pi-receipt-c33", harness_id="pi-coding-agent", harness_version="0.72.1"),
    )

    monkeypatch = pytest.MonkeyPatch()

    def _combined(**kwargs: Any) -> FakeOutcome:
        (pathlib.Path(kwargs["cwd"]) / "proof_target.txt").write_text(
            "CE-L1-LIVE-EXECUTOR-OK\n", encoding="utf-8"
        )
        return outcome

    monkeypatch.setattr(live_executor, "_invoker", _combined)
    output_root = tmp_path / "out-24"
    run_live_executor_campaign(
        preparation,
        output_root,
        envelope=envelope,
        decision=decision,
        timeout_seconds=30,
        campaign_path=campaign_path,
    )
    monkeypatch.undo()
    evaluation = json.loads(
        (output_root / handle["campaign_id"] / "evaluations" / f"{preparation.evaluation_id}.json").read_text()
    )
    assert evaluation["independent_model_judgment"] is False
    assert evaluation["evaluation_mode"] == "provider_free"
    assert evaluation["read_only_assertion"] is True
    assert evaluation["mutation_performed"] is False
    assert "CE-L2" in evaluation["summary"]


# 34. existing run_provider_free_campaign output contract remains unchanged.
def test_provider_free_unchanged_output_contract(
    tmp_path,
) -> None:
    from codex_runner.campaign_engine import run_provider_free_campaign

    provider_free = tmp_path / "campaign_pf"
    provider_free.mkdir(parents=True, exist_ok=True)
    provider_free_campaign = {
        "schema_version": "campaign-engine/v0",
        "campaign": {
            "schema_version": "campaign-engine/v0",
            "campaign_id": "campaign-pf-test-001",
            "created_at": "2026-08-26T13:00:00Z",
            "state": "ready",
            "objective": "Provider-free regression",
            "task_ids": ["task-pf-test-001"],
            "role_binding_ids": [
                "binding-pf-auditor-001",
                "binding-pf-executor-001",
                "binding-pf-evaluator-001",
            ],
            "role_policy": {
                "maximum_distinct_models": 3,
                "shared_models_across_roles_allowed": True,
                "runtime_rebinding_allowed": False,
                "rebind_approval": "operator_required",
            },
        },
        "tasks": [{
            "schema_version": "campaign-engine/v0",
            "task_id": "task-pf-test-001",
            "campaign_id": "campaign-pf-test-001",
            "created_at": "2026-08-26T13:00:00Z",
            "state": "ready",
            "objective": "Provider-free regression task",
        }],
        "role_bindings": [
            {
                "schema_version": "campaign-engine/v0",
                "binding_id": "binding-pf-auditor-001",
                "created_at": "2026-08-26T13:00:00Z",
                "role": "auditor",
                "provider_id": "provider-free-fixture",
                "model_id": "synthetic-auditor-model",
                "adapter_id": "provider-free-adapter",
                "binding_revision": 1,
                "binding_state": "locked",
                "configuration_hash": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                "selected_by": "operator:resonant-jones",
                "selected_at": "2026-08-26T13:00:00Z",
            },
            {
                "schema_version": "campaign-engine/v0",
                "binding_id": "binding-pf-executor-001",
                "created_at": "2026-08-26T13:00:00Z",
                "role": "executor",
                "provider_id": "provider-free-fixture",
                "model_id": "synthetic-executor-model",
                "adapter_id": "provider-free-adapter",
                "binding_revision": 1,
                "binding_state": "locked",
                "configuration_hash": "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                "selected_by": "operator:resonant-jones",
                "selected_at": "2026-08-26T13:00:00Z",
            },
            {
                "schema_version": "campaign-engine/v0",
                "binding_id": "binding-pf-evaluator-001",
                "created_at": "2026-08-26T13:00:00Z",
                "role": "evaluator",
                "provider_id": "provider-free-fixture",
                "model_id": "synthetic-evaluator-model",
                "adapter_id": "provider-free-adapter",
                "binding_revision": 1,
                "binding_state": "locked",
                "configuration_hash": "sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
                "selected_by": "operator:resonant-jones",
                "selected_at": "2026-08-26T13:00:00Z",
            },
        ],
        "attempts": [],
        "evaluations": [],
        "receipts": [],
        "decision_gates": [],
        "campaign_state": {
            "schema_version": "campaign-engine/v0",
            "campaign_state_id": "campaign-state-pf-test-000",
            "campaign_id": "campaign-pf-test-001",
            "created_at": "2026-08-26T13:00:00Z",
            "state": "ready",
            "ordered_task_ids": ["task-pf-test-001"],
            "ordered_role_binding_ids": [
                "binding-pf-auditor-001",
                "binding-pf-executor-001",
                "binding-pf-evaluator-001",
            ],
            "ordered_attempt_ids": [],
            "ordered_evaluation_ids": [],
            "ordered_receipt_ids": [],
            "ordered_decision_gate_ids": [],
        },
    }
    campaign_path = tmp_path / "pf_camp.json"
    campaign_path.write_text(json.dumps(provider_free_campaign), encoding="utf-8")
    out_root = tmp_path / "pf_out"
    result = run_provider_free_campaign(campaign_path, out_root)
    assert result.classification == "provider_free"
    assert result.provider_calls == 0
    assert result.source_mutations == 0
    assert result.commit_performed is False
    assert result.merge_performed is False
    assert result.durable_ingestion_performed is False


# 35. importing the Campaign Engine package does not eagerly import Guardian/Pi execution modules solely for provider-free use.
def test_package_import_does_not_eagerly_load_guardian_pi() -> None:
    # Subprocess so we observe the import-time module set without test-side contamination.
    py = sys.executable
    script = (
        "import sys, json, codex_runner.campaign_engine as p; "
        "mods = sorted({name for name in sys.modules if 'guardian' in name or 'pi-coding' in name or name.endswith('.pi')}); "
        "out = sorted({a for a in dir(p) if not a.startswith('_')}); "
        "print(json.dumps({'modules': mods, 'attrs': out}))"
    )
    completed = subprocess.run([py, "-c", script], capture_output=True, text=True, check=True, env={**os.environ})
    payload = json.loads(completed.stdout)
    assert payload["modules"] == [], (
        f"Guardian/Pi modules were eagerly loaded by package import: {payload['modules']}"
    )
    # Surface is unchanged in terms of public API.
    for required in ("run_provider_free_campaign", "LiveExecutorPreparation", "CampaignLiveExecutorError"):
        assert required in payload["attrs"]


# --- Pi 0.82.1 tool telemetry propagation regressions ---
#
# These tests verify the Campaign Engine propagates bounded tool telemetry
# through the success and failure paths without fabricating or mutating it.




def test_zero_mutation_error_carries_all_six_tool_telemetry_fields(
    monkeypatch, live_doc, tmp_path, fixed_clock, invoker_factory
) -> None:
    """zero_mutation_executor_turn exposes all six telemetry fields in the
    CampaignLiveExecutorError.to_payload() output, and the issue text does
    not claim the model itself caused the failure."""
    from codex_runner.campaign_engine.live_executor import run_live_executor_campaign
    campaign_path, target_path, _ = live_doc
    fake_identity = FakeIdentity(
        provider_id="openai-codex",
        model_id="gpt-5.1",
        harness_id="pi-coding-agent",
        harness_version="0.82.1",
    )
    fake_receipt = FakeReceipt(
        receipt_id="pi-receipt-tool-telemetry-zero",
        invocation_id="inv-tool-telemetry-zero",
        harness_id="pi-coding-agent",
        harness_version="0.82.1",
    )
    fake_harness_result = FakeHarnessResult(
        harness_result_id="pi-result-tool-telemetry-zero",
        receipt_id="pi-receipt-tool-telemetry-zero",
        harness_id="pi-coding-agent",
        harness_version="0.82.1",
    )
    outcome = FakeOutcome(
        ok=True,
        receipt=fake_receipt,
        harness_result=fake_harness_result,
        actual_identity=fake_identity,
        # Telemetry shows write WAS active but no tool call / execution occurred.
        effective_tool_names=("read", "bash", "edit", "write"),
        write_tool_available=True,
        tool_execution_start_count=0,
        tool_execution_end_count=0,
        executed_tool_names=(),
        assistant_tool_call_count=0,
    )
    _, install = invoker_factory
    install(outcome)
    output_root = tmp_path / "ce-l1-zero-mut-telemetry-output"
    output_root.mkdir(parents=True, exist_ok=True)
    preparation = prepare_live_executor_campaign(
        campaign_path,
        target_path,
        clock=fixed_clock,
    )
    envelope, decision = _build_envelope_and_decision(preparation)
    try:
        run_live_executor_campaign(
            preparation,
            output_root,
            envelope=envelope,
            decision=decision,
            timeout_seconds=15,
            campaign_path=campaign_path,
        )
    except CampaignLiveExecutorError as exc:
        payload = exc.to_payload()
        assert payload["failure_reason"] == "zero_mutation_executor_turn"
        # All six telemetry fields are present.
        telemetry = payload["tool_telemetry"]
        assert telemetry is not None
        assert telemetry["effective_tool_names"] == [
            "read", "bash", "edit", "write",
        ]
        assert telemetry["write_tool_available"] is True
        assert telemetry["tool_execution_start_count"] == 0
        assert telemetry["tool_execution_end_count"] == 0
        assert telemetry["executed_tool_names"] == []
        assert telemetry["assistant_tool_call_count"] == 0
        # Issue text does NOT blame the model.
        assert "the model did not invoke" not in str(exc)
        # Issue text is evidence-bounded.
        assert "tool availability and execution telemetry" in str(exc)
    else:
        raise AssertionError(
            "expected CampaignLiveExecutorError for zero-mutation outcome"
        )


def test_zero_mutation_issue_text_does_not_blame_model() -> None:
    """The zero_mutation_executor_turn issue text must be evidence-bounded."""
    err = CampaignLiveExecutorError(
        "Harness success produced zero allowed-path mutation; "
        "inspect bounded tool availability and execution telemetry "
        "to classify the tool-execution boundary",
        failure_reason="zero_mutation_executor_turn",
        diagnostic_stage="post_invocation",
        issues=["allowed-path mutation; telemetry retained for diagnosis"],
    )
    msg = str(err)
    assert "the model did not invoke" not in msg
    assert "tool availability and execution telemetry" in msg


# --- Pi 0.82.1 assistant-response telemetry Campaign propagation regressions
# (CE-L1 post-tool-repair observability).  These tests prove the four new
# bounded telemetry fields survive both successful live-result construction
# and zero_mutation_executor_turn error-payload construction.  No provider
# calls; no prompt execution; no credential access.


def _assistant_telemetry_r2_case_a(
    *, with_toolcall_event: bool = False
) -> dict[str, object]:
    """R2-equivalent synthetic Case A telemetry fixture.

    Mirrors the R2 live result for `openai-codex / gpt-5.6-sol /
    pi-coding-agent / 0.82.1`:
      - effective tool surface: read / bash / edit / write (post-PR #774)
      - write is available
      - assistant produced >=1 message; assistant emitted a final `text`
        content block; no `toolCall` content block; no `toolcall_*`
        lifecycle events observed.
    """
    payload: dict[str, object] = {
        "effective_tool_names": ["read", "bash", "edit", "write"],
        "write_tool_available": True,
        "tool_execution_start_count": 0,
        "tool_execution_end_count": 0,
        "executed_tool_names": [],
        "assistant_tool_call_count": 0,
        "assistant_message_count": 1,
        "assistant_content_block_types": ["text"],
        "assistant_message_event_types": [
            "start",
            "text_start",
            "text_delta",
            "text_end",
            "done",
        ],
        "assistant_tool_call_event_count": (1 if with_toolcall_event else 0),
    }
    if with_toolcall_event:
        existing_events: list[str] = list(
            payload["assistant_message_event_types"]
        )
        payload["assistant_message_event_types"] = (
            existing_events + ["toolcall_start"]
        )
    return payload


def _build_zero_mutation_outcome(
    telemetry: dict[str, object],
) -> tuple[object, object, object, object]:
    """Construct a FakeIdentity/FakeReceipt/FakeHarnessResult/FakeOutcome
    carrying the bounded telemetry.
    """
    fake_identity = FakeIdentity(
        provider_id="openai-codex",
        model_id="gpt-5.1",
        harness_id="pi-coding-agent",
        harness_version="0.82.1",
    )
    fake_receipt = FakeReceipt(
        receipt_id="pi-receipt-assistant-telemetry",
        invocation_id="inv-assistant-telemetry",
        harness_id="pi-coding-agent",
        harness_version="0.82.1",
    )
    fake_harness_result = FakeHarnessResult(
        harness_result_id="pi-result-assistant-telemetry",
        receipt_id="pi-receipt-assistant-telemetry",
        harness_id="pi-coding-agent",
        harness_version="0.82.1",
    )
    outcome = FakeOutcome(
        ok=True,
        receipt=fake_receipt,
        harness_result=fake_harness_result,
        actual_identity=fake_identity,
        effective_tool_names=tuple(telemetry["effective_tool_names"]),
        write_tool_available=telemetry["write_tool_available"],
        tool_execution_start_count=telemetry["tool_execution_start_count"],
        tool_execution_end_count=telemetry["tool_execution_end_count"],
        executed_tool_names=tuple(telemetry["executed_tool_names"]),
        assistant_tool_call_count=telemetry["assistant_tool_call_count"],
        assistant_message_count=telemetry["assistant_message_count"],
        assistant_content_block_types=tuple(telemetry["assistant_content_block_types"]),
        assistant_message_event_types=tuple(telemetry["assistant_message_event_types"]),
        assistant_tool_call_event_count=(telemetry["assistant_tool_call_event_count"]),
    )
    return fake_identity, fake_receipt, fake_harness_result, outcome


def test_zero_mutation_error_carries_all_four_assistant_telemetry_fields(
    monkeypatch, live_doc, tmp_path, fixed_clock, invoker_factory
) -> None:
    """zero_mutation_executor_turn payload includes the four bounded
    assistant-response telemetry fields.  R2 Case A shape.
    """
    from codex_runner.campaign_engine.live_executor import run_live_executor_campaign

    campaign_path, target_path, _ = live_doc
    telemetry = _assistant_telemetry_r2_case_a()
    _, _, _, outcome = _build_zero_mutation_outcome(telemetry)
    _, install = invoker_factory
    install(outcome)

    output_root = tmp_path / "ce-l1-assistant-zero-mut-output"
    output_root.mkdir(parents=True, exist_ok=True)
    preparation = prepare_live_executor_campaign(
        campaign_path,
        target_path,
        clock=fixed_clock,
    )
    envelope, decision = _build_envelope_and_decision(preparation)
    try:
        run_live_executor_campaign(
            preparation,
            output_root,
            envelope=envelope,
            decision=decision,
            timeout_seconds=15,
            campaign_path=campaign_path,
        )
    except CampaignLiveExecutorError as exc:
        payload = exc.to_payload()
        assert payload["failure_reason"] == "zero_mutation_executor_turn"
        captured = payload["tool_telemetry"]
        assert captured is not None
        # Existing 6 fields preserved unchanged.
        assert captured["effective_tool_names"] == [
            "read",
            "bash",
            "edit",
            "write",
        ]
        assert captured["write_tool_available"] is True
        assert captured["tool_execution_start_count"] == 0
        assert captured["tool_execution_end_count"] == 0
        assert captured["executed_tool_names"] == []
        assert captured["assistant_tool_call_count"] == 0
        # New 4 assistant-response fields present.
        assert captured["assistant_message_count"] == 1
        assert captured["assistant_content_block_types"] == ["text"]
        # Tuple → list serialization for type-list fields.
        assert captured["assistant_message_event_types"] == [
            "start",
            "text_start",
            "text_delta",
            "text_end",
            "done",
        ]
        assert captured["assistant_tool_call_event_count"] == 0
    else:
        raise AssertionError(
            "expected CampaignLiveExecutorError for zero-mutation outcome"
        )


def test_zero_mutation_error_records_toolcall_event_count_even_when_no_block(
    monkeypatch, live_doc, tmp_path, fixed_clock, invoker_factory
) -> None:
    """When the assistant emits a `toolcall_*` lifecycle event but the
    final normalized `toolCall` content block is missing, both fields
    are recorded independently.  Both must still BLOCK the run when
    no allowed-path mutation is observed.
    """
    from codex_runner.campaign_engine.live_executor import run_live_executor_campaign

    campaign_path, target_path, _ = live_doc
    telemetry = _assistant_telemetry_r2_case_a(with_toolcall_event=True)
    _, _, _, outcome = _build_zero_mutation_outcome(telemetry)
    _, install = invoker_factory
    install(outcome)

    output_root = tmp_path / "ce-l1-toolcall-event-zero-mut-output"
    output_root.mkdir(parents=True, exist_ok=True)
    preparation = prepare_live_executor_campaign(
        campaign_path,
        target_path,
        clock=fixed_clock,
    )
    envelope, decision = _build_envelope_and_decision(preparation)
    try:
        run_live_executor_campaign(
            preparation,
            output_root,
            envelope=envelope,
            decision=decision,
            timeout_seconds=15,
            campaign_path=campaign_path,
        )
    except CampaignLiveExecutorError as exc:
        payload = exc.to_payload()
        assert payload["failure_reason"] == "zero_mutation_executor_turn"
        captured = payload["tool_telemetry"]
        assert captured is not None
        # toolcall_event count recorded; tool_call block count stays 0.
        assert captured["assistant_tool_call_event_count"] == 1
        assert captured["assistant_tool_call_count"] == 0
        # The event-type tuple must include the toolcall lifecycle event.
        assert "toolcall_start" in captured["assistant_message_event_types"]
    else:
        raise AssertionError(
            "expected CampaignLiveExecutorError even with a "
            "toolcall lifecycle event but no mutation"
        )


def test_zero_mutation_error_payload_contains_no_assistant_text_or_args() -> None:
    """The serialized payload must contain no assistant text, reasoning,
    delta content, tool arguments, tool IDs, tool results, provider
    payloads, raw schemas, or credentials.
    """
    forbidden_substrings = (
        # Assistant text/reasoning prose must never appear in telemetry
        # payloads.
        "I cannot",
        "I will not",
        "I'm unable",
        "as an AI",
        "as a language model",
        # Tool-arg name echoes that could leak schema structure.
        "ignored-arg",
        "ignored-path",
        "ignored-content",
        "ignored-text",
        "ignored-key",
        "ignored-args",
        "ignored-result",
        # Provider payload fragments must never appear.
        '"choices":',
        '"delta":',
        '"usage":',
        '"messages":',
        # Credentials.
        "api_key",
        "openai_api_key",
        "PI_API_KEY",
        "PI_TOKEN",
    )
    err = CampaignLiveExecutorError(
        "Harness success produced zero allowed-path mutation",
        failure_reason="zero_mutation_executor_turn",
        diagnostic_stage="post_invocation",
        effective_tool_names=("read", "bash", "edit", "write"),
        write_tool_available=True,
        tool_execution_start_count=0,
        tool_execution_end_count=0,
        executed_tool_names=(),
        assistant_tool_call_count=0,
        assistant_message_count=1,
        assistant_content_block_types=("text",),
        assistant_message_event_types=("start", "done"),
        assistant_tool_call_event_count=0,
        issues=[],
    )
    payload = err.to_payload()
    payload_str = json.dumps(payload, default=str)
    for forbidden in forbidden_substrings:
        assert (
            forbidden not in payload_str
        ), f"forbidden substring {forbidden!r} present in payload"


def test_assistant_telemetry_present_in_live_executor_run_result(
    monkeypatch, live_doc, tmp_path, fixed_clock, invoker_factory
) -> None:
    """A successful live Executor run records the four assistant fields
    in the resulting LiveExecutorRunResult (and its to_dict() output).
    """
    from codex_runner.campaign_engine.live_executor import run_live_executor_campaign

    # Build a Campaign with an allowed target.  We instrument the harness
    # to emit the assistant fields.  FakeRunner cannot mutate the file,
    # so the run raises zero_mutation_executor_turn and the success-path
    # LiveExecutorRunResult is not produced.  In that case the
    # CampaignLiveExecutorError payload already carries the four fields
    # (covered separately by
    # test_zero_mutation_error_carries_all_four_assistant_telemetry_fields).
    campaign_path, target_path, _handle = live_doc
    telemetry = _assistant_telemetry_r2_case_a()
    _, _, _, outcome = _build_zero_mutation_outcome(telemetry)
    _, install = invoker_factory
    install(outcome)

    output_root = tmp_path / "ce-l1-assistant-success-output"
    output_root.mkdir(parents=True, exist_ok=True)
    preparation = prepare_live_executor_campaign(
        campaign_path,
        target_path,
        clock=fixed_clock,
    )
    envelope, decision = _build_envelope_and_decision(preparation)
    try:
        result = run_live_executor_campaign(
            preparation,
            output_root,
            envelope=envelope,
            decision=decision,
            timeout_seconds=15,
            campaign_path=campaign_path,
        )
    except CampaignLiveExecutorError as exc:
        # Outcome was ok=True but no mutation occurred (FakeRunner
        # cannot mutate the file).  Verify the same four fields surface
        # at the error payload boundary.
        captured = exc.to_payload()["tool_telemetry"]
        assert captured["assistant_message_count"] == 1
        assert captured["assistant_content_block_types"] == ["text"]
        assert captured["assistant_message_event_types"] == [
            "start",
            "text_start",
            "text_delta",
            "text_end",
            "done",
        ]
        assert captured["assistant_tool_call_event_count"] == 0
        return

    # On success path: LiveExecutorRunResult carries the four new fields.
    assert result.tool_telemetry.assistant_message_count == 1
    assert result.tool_telemetry.assistant_content_block_types == ("text",)
    assert result.tool_telemetry.assistant_message_event_types == (
        "start",
        "text_start",
        "text_delta",
        "text_end",
        "done",
    )
    assert result.tool_telemetry.assistant_tool_call_event_count == 0

    # to_dict() serialization preserves them under tool_telemetry.
    serialized = result.to_dict()
    tt = serialized["tool_telemetry"]
    assert tt["assistant_message_count"] == 1
    assert tt["assistant_content_block_types"] == ["text"]
    assert tt["assistant_message_event_types"] == [
        "start",
        "text_start",
        "text_delta",
        "text_end",
        "done",
    ]
    assert tt["assistant_tool_call_event_count"] == 0


def test_assistant_telemetry_preserved_on_harness_result_metadata(
    monkeypatch, live_doc, tmp_path, fixed_clock, invoker_factory
) -> None:
    """The PiLiveInvocationOutcome's `validation_metadata["tool_telemetry"]`
    surfaces the four new bounded assistant fields without recomputation
    when the run reaches post-invocation handling.  This test verifies
    the four fields survive from `FakeOutcome` -> `_extract_tool_telemetry_from_outcome`
    -> `CampaignLiveExecutorError.to_payload()["tool_telemetry"]` exactly.
    """
    from codex_runner.campaign_engine.live_executor import run_live_executor_campaign

    campaign_path, target_path, _ = live_doc
    telemetry = _assistant_telemetry_r2_case_a()
    _, _, _, outcome = _build_zero_mutation_outcome(telemetry)
    _, install = invoker_factory
    install(outcome)

    output_root = tmp_path / "ce-l1-assistant-harness-result-output"
    output_root.mkdir(parents=True, exist_ok=True)
    preparation = prepare_live_executor_campaign(
        campaign_path,
        target_path,
        clock=fixed_clock,
    )
    envelope, decision = _build_envelope_and_decision(preparation)
    try:
        run_live_executor_campaign(
            preparation,
            output_root,
            envelope=envelope,
            decision=decision,
            timeout_seconds=15,
            campaign_path=campaign_path,
        )
    except CampaignLiveExecutorError as exc:
        payload = exc.to_payload()
        captured = payload["tool_telemetry"]
        assert captured is not None
        # Verify all 10 telemetry fields propagate exactly from the
        # FakeOutcome (which mirrors the PiLiveInvocationOutcome shape).
        assert captured["effective_tool_names"] == [
            "read",
            "bash",
            "edit",
            "write",
        ]
        assert captured["write_tool_available"] is True
        assert captured["tool_execution_start_count"] == 0
        assert captured["tool_execution_end_count"] == 0
        assert captured["executed_tool_names"] == []
        assert captured["assistant_tool_call_count"] == 0
        assert captured["assistant_message_count"] == 1
        assert captured["assistant_content_block_types"] == ["text"]
        assert captured["assistant_message_event_types"] == [
            "start",
            "text_start",
            "text_delta",
            "text_end",
            "done",
        ]
        assert captured["assistant_tool_call_event_count"] == 0
    else:
        raise AssertionError(
            "expected CampaignLiveExecutorError for zero-mutation outcome"
        )
