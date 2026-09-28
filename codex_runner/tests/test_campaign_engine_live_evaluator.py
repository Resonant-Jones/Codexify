"""Provider-free CE-L2 lifecycle proof; both invocation seams use fakes."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from codex_runner.campaign_engine import live_evaluator, live_executor
from codex_runner.campaign_engine.errors import CampaignLiveEvaluatorError, CampaignLiveExecutorError
from codex_runner.campaign_engine.live_evaluator import (
    prepare_live_evaluator_campaign,
    run_live_evaluator_campaign,
)
from codex_runner.campaign_engine.live_executor import (
    prepare_live_executor_campaign,
    run_live_executor_campaign,
)
from codex_runner.campaign_engine.identity import document_hash
from codex_runner.campaign_engine.validation import validate_campaign_document
from codex_runner.tests.test_campaign_engine_live_executor import (
    FakeIdentity, FakeOutcome, _build_envelope_and_decision,
    _make_canonical_live_campaign,
)
from guardian.pi.contracts import (
    PiHarnessResult, PiInvocationArtifact, PiInvocationEnvelope,
    PiInvocationPolicyDecision, PiInvocationReceipt, PiPermissionGrant,
    PiProviderLane,
)
from guardian.pi.validation import (
    validate_harness_result_against_receipt,
    validate_receipt_against_envelope,
)


def _pi_evidence(envelope: PiInvocationEnvelope) -> tuple[PiInvocationReceipt, PiHarnessResult]:
    receipt = PiInvocationReceipt(
        receipt_id="pi-receipt-" + envelope.invocation_id,
        guardian_boundary=envelope.guardian_boundary,
        source_thread_id=envelope.source_thread_id,
        source_message_id=envelope.source_message_id,
        invocation_id=envelope.invocation_id,
        harness_id=envelope.harness_id,
        harness_version=envelope.harness_version,
        provider_lane=envelope.provider_lane,
        requested_permissions=envelope.requested_permissions,
        granted_permissions=envelope.granted_permissions,
        attempt_id=envelope.attempt_id,
        receipt_status="completed",
        result_artifact_ref="pi://test/result",
    )
    harness = PiHarnessResult(
        harness_result_id="pi-result-" + envelope.invocation_id,
        receipt_id=receipt.receipt_id,
        guardian_boundary=envelope.guardian_boundary,
        source_thread_id=envelope.source_thread_id,
        source_message_id=envelope.source_message_id,
        invocation_id=envelope.invocation_id,
        harness_id=envelope.harness_id,
        harness_version=envelope.harness_version,
        provider_lane=envelope.provider_lane,
        requested_permissions=envelope.requested_permissions,
        granted_permissions=envelope.granted_permissions,
        attempt_id=envelope.attempt_id,
        artifact=PiInvocationArtifact(artifact_id="artifact-" + envelope.invocation_id, artifact_ref="pi://test/result"),
        result_class="success",
    )
    assert validate_receipt_against_envelope(envelope, receipt).ok
    assert validate_harness_result_against_receipt(receipt, harness).ok
    return receipt, harness


@dataclass(frozen=True)
class EvaluatorOutcome:
    receipt: PiInvocationReceipt
    harness_result: PiHarnessResult
    evaluator_result: dict[str, Any] | None
    ok: bool = True
    runner_call_count: int = 1
    retry_count: int = 0
    fallback_count: int = 0
    diagnostic_class: str | None = None
    diagnostic_stage: str | None = None
    observed_execution_phases: tuple[str, ...] | None = None
    highest_observed_execution_phase: str | None = None
    requested_reasoning_effort: str = "high"
    effective_reasoning_effort: str = "high"
    automatic_retries_disabled: bool = True
    actual_identity: FakeIdentity = FakeIdentity("deepseek", "deepseek-v4-pro", "pi-coding-agent", "0.82.1")


def _verdict() -> dict[str, Any]:
    return {
        "verdict": "passed",
        "summary": "The required marker was written only to the allowed file.",
        "structured_acceptance_results": [{
            "criterion_id": "exact-marker", "verdict": "pass",
            "evidence_refs": ["changed-files", "target-snapshot"],
            "basis": "The bounded diff contains the exact marker.",
        }],
    }


def _prepare_lifecycle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, evaluator_effort: str,
    campaign_id: str = "campaign-ce-l2-provider-free-test-001",
):
    campaign_path, target, handle = _make_canonical_live_campaign(
        tmp_path, executor_provider="deepseek", executor_model="deepseek-v4-pro",
        campaign_id=campaign_id,
    )
    campaign = json.loads(campaign_path.read_text())
    campaign["tasks"][0]["objective"] = "Write CE-L2-EXACT-MARKER followed by one newline to proof_target.txt."
    campaign["tasks"][0]["acceptance_criteria"] = [{
        "criterion_id": "exact-marker",
        "description": "proof_target.txt contains exactly CE-L2-EXACT-MARKER followed by one newline; no other target file changed.",
    }]
    campaign["role_bindings"][1]["live_role_binding"].update({
        "harness_id": "pi-coding-agent", "harness_version": "0.82.1",
        "reasoning_effort": "off",
    })
    evaluator = campaign["role_bindings"][2]
    evaluator.update({
        "provider_id": "deepseek", "model_id": "deepseek-v4-pro",
        "adapter_id": "pi-provider-broker", "execution_mode": "live",
        "redaction_status": "redacted",
        "live_role_binding": {
            "provider_identity_proof": "identity-proof-ce-l2-provider-free",
            "harness_id": "pi-coding-agent", "harness_version": "0.82.1",
            "reasoning_effort": evaluator_effort,
            "target_repository_identity": str(target),
            "allowed_file_paths": ["proof_target.txt"],
            "requested_permissions": ["files.read", "network.provider.allowed"],
            "granted_permissions": ["files.read"],
            "operator_consent_reference": "ce-l2-provider-free-test-consent",
        },
    })
    campaign_path.write_text(json.dumps(campaign, indent=2))
    validate_campaign_document(campaign, "fresh CE-L2 provider-free campaign")
    executor_prep = prepare_live_executor_campaign(campaign_path, target)
    executor_envelope, executor_decision = _build_envelope_and_decision(executor_prep)
    from dataclasses import replace
    executor_envelope = replace(
        executor_envelope, harness_version="0.82.1",
        provider_lane=PiProviderLane(provider_lane_class="external", provider_name="deepseek", model_id="deepseek-v4-pro"),
    )
    executor_receipt, executor_harness = _pi_evidence(executor_envelope)

    def fake_executor(**kwargs: Any) -> FakeOutcome:
        assert kwargs["required_tool_name"] == "write"
        assert kwargs["reasoning_effort"] == "off"
        (target / "proof_target.txt").write_text("CE-L2-EXACT-MARKER\n")
        return FakeOutcome(
            ok=True,
            actual_identity=FakeIdentity("deepseek", "deepseek-v4-pro", "pi-coding-agent", "0.82.1"),
            receipt=executor_receipt, harness_result=executor_harness,
        )

    monkeypatch.setattr(live_executor, "_invoker", fake_executor)
    run_live_executor_campaign(
        executor_prep, tmp_path / "executor-checkpoint",
        envelope=executor_envelope, decision=executor_decision,
        timeout_seconds=30, campaign_path=campaign_path, reasoning_effort="off",
    )
    checkpoint = tmp_path / "executor-checkpoint" / handle["campaign_id"]
    preparation = prepare_live_evaluator_campaign(
        campaign_path, checkpoint, target,
        harness_id="pi-coding-agent", harness_version="0.82.1",
    )
    boundary = executor_envelope.guardian_boundary
    granted = (PiPermissionGrant(permission="files.read", resource="proof_target.txt"),)
    requested = granted + (PiPermissionGrant(permission="network.provider.allowed", resource="."),)
    evaluator_envelope = PiInvocationEnvelope(
        guardian_boundary=boundary, source_thread_id="ce-l2-test-thread",
        source_message_id="ce-l2-test-message", invocation_id="inv-ce-l2-test-evaluator",
        harness_id="pi-coding-agent", harness_version="0.82.1",
        provider_lane=PiProviderLane(provider_lane_class="external", provider_name="deepseek", model_id="deepseek-v4-pro"),
        requested_permissions=requested, granted_permissions=granted,
        validation_metadata={"campaign_engine": preparation.authorization_metadata()},
    )
    evaluator_decision = PiInvocationPolicyDecision(
        policy_decision_id="policy-ce-l2-test-evaluator",
        invocation_id=evaluator_envelope.invocation_id,
        source_thread_id=evaluator_envelope.source_thread_id,
        source_message_id=evaluator_envelope.source_message_id,
        harness_id=evaluator_envelope.harness_id, decision="allowed",
        guardian_boundary=boundary,
        requested_permissions=requested, granted_permissions=granted,
        permission_posture="filesystem.read.allowed",
        actor_id="operator:test", policy_source="guardian:test",
        decision_reason="ce-l2-provider-free-test", decided_at="2026-08-26T14:30:00Z",
        validation_status="validated", redaction_state="redacted",
    )
    evaluator_receipt, evaluator_harness = _pi_evidence(evaluator_envelope)
    return (
        preparation, evaluator_envelope, evaluator_decision,
        evaluator_receipt, evaluator_harness, checkpoint, target,
    )


@pytest.fixture
def prepared_lifecycle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    return _prepare_lifecycle(tmp_path, monkeypatch, evaluator_effort="high")


def test_provider_free_single_task_lifecycle(prepared_lifecycle, tmp_path, monkeypatch) -> None:
    prep, envelope, decision, receipt, harness, checkpoint, target = prepared_lifecycle
    before_checkpoint = {rel: (checkpoint / rel).read_bytes() for rel, _ in prep.checkpoint_hashes}
    calls: list[dict[str, Any]] = []

    def fake_evaluator(**kwargs: Any) -> EvaluatorOutcome:
        calls.append(kwargs)
        return EvaluatorOutcome(receipt, harness, _verdict())

    monkeypatch.setattr(live_evaluator, "_invoker", fake_evaluator)
    output = run_live_evaluator_campaign(
        prep, tmp_path / "final", envelope=envelope, decision=decision,
        timeout_seconds=30, reasoning_effort="high",
    )
    assert len(calls) == 1
    assert calls[0]["required_tool_name"] is None
    assert calls[0]["evaluator_result_contract"] == "campaign-evaluator-v0"
    assert calls[0]["reasoning_effort"] == "high"
    assert prep.expected_reasoning_effort == "high"
    assert prep.authorization_metadata()["reasoning_effort"] == "high"
    assembled = json.loads((output / "campaign-input.json").read_text())
    validate_campaign_document(assembled, "provider-free CE-L2 final")
    assert assembled["campaign"]["state"] == "completed"
    assert assembled["evaluations"][0]["independent_model_judgment"] is True
    assert assembled["receipts"][0]["provider_call_count"] == 2
    assert "CE-L2-EXACT-MARKER" in prep.evidence_packet_json
    assert "bounded_diff" in prep.evidence_packet_json
    assert all((checkpoint / rel).read_bytes() == content for rel, content in before_checkpoint.items())
    assert all(
        (output / "execution" / "executor-checkpoint" / rel).read_bytes() == content
        for rel, content in before_checkpoint.items()
    )
    assert (target / "proof_target.txt").read_text() == "CE-L2-EXACT-MARKER\n"
    assert not any(
        token in path.read_text(encoding="utf-8")
        for path in output.rglob("*.json")
        for token in ("Bearer abcdefgh12345678", "sk-abcdefghijklmnop")
    )


def test_locked_deepseek_medium_rejected_before_evaluator_invocation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        live_evaluator, "_invoker", lambda **kwargs: pytest.fail("provider seam reached"),
    )
    with pytest.raises(CampaignLiveEvaluatorError) as exc:
        _prepare_lifecycle(tmp_path, monkeypatch, evaluator_effort="medium")
    assert exc.value.reason == "evaluator_effort_unsupported"
    assert exc.value.runner_call_count == 0


def test_changed_locked_effort_changes_campaign_input_identity(tmp_path: Path) -> None:
    campaign_path, _, _ = _make_canonical_live_campaign(
        tmp_path, executor_provider="deepseek", executor_model="deepseek-v4-pro",
    )
    campaign = json.loads(campaign_path.read_text())
    evaluator = campaign["role_bindings"][2]
    evaluator["live_role_binding"] = {
        "provider_identity_proof": "identity-proof-ce-l2-effort-hash",
        "harness_id": "pi-coding-agent", "harness_version": "0.82.1",
        "reasoning_effort": "medium",
        "target_repository_identity": str(tmp_path),
        "allowed_file_paths": ["proof_target.txt"],
        "requested_permissions": ["files.read", "network.provider.allowed"],
        "granted_permissions": ["files.read"],
        "operator_consent_reference": "ce-l2-effort-hash-test",
    }
    evaluator.update({
        "provider_id": "deepseek", "model_id": "deepseek-v4-pro",
        "adapter_id": "pi-provider-broker", "execution_mode": "live",
        "redaction_status": "redacted",
    })
    validate_campaign_document(campaign, "medium locked Campaign")
    medium_hash = document_hash(campaign)
    campaign["role_bindings"][2]["live_role_binding"]["reasoning_effort"] = "high"
    validate_campaign_document(campaign, "high locked Campaign")
    assert document_hash(campaign) != medium_hash


def test_execution_effort_drift_blocks_before_invocation(
    prepared_lifecycle, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    prep, envelope, decision, _, _, _, _ = prepared_lifecycle
    monkeypatch.setattr(
        live_evaluator, "_invoker", lambda **kwargs: pytest.fail("provider seam reached"),
    )
    with pytest.raises(CampaignLiveEvaluatorError) as exc:
        run_live_evaluator_campaign(
            prep, tmp_path / "blocked-effort", envelope=envelope, decision=decision,
            timeout_seconds=30, reasoning_effort="medium",
        )
    assert exc.value.reason == "evaluator_reasoning_effort_mismatch"
    assert exc.value.runner_call_count == 0


def test_guardian_effort_metadata_drift_blocks_before_invocation(
    prepared_lifecycle, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from dataclasses import replace

    prep, envelope, decision, _, _, _, _ = prepared_lifecycle
    stale_metadata = prep.authorization_metadata()
    stale_metadata["reasoning_effort"] = "medium"
    envelope = replace(
        envelope, validation_metadata={"campaign_engine": stale_metadata},
    )
    monkeypatch.setattr(
        live_evaluator, "_invoker", lambda **kwargs: pytest.fail("provider seam reached"),
    )
    with pytest.raises(CampaignLiveEvaluatorError) as exc:
        run_live_evaluator_campaign(
            prep, tmp_path / "blocked-authorization", envelope=envelope,
            decision=decision, timeout_seconds=30, reasoning_effort="high",
        )
    assert exc.value.reason == "evaluator_authorization_drifted"
    assert exc.value.runner_call_count == 0


def test_locked_campaign_effort_drift_blocks_before_invocation(
    prepared_lifecycle, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    prep, envelope, decision, _, _, _, _ = prepared_lifecycle
    campaign = json.loads(prep.campaign_path.read_text())
    campaign["role_bindings"][2]["live_role_binding"]["reasoning_effort"] = "medium"
    prep.campaign_path.write_text(json.dumps(campaign))
    monkeypatch.setattr(
        live_evaluator, "_invoker", lambda **kwargs: pytest.fail("provider seam reached"),
    )
    with pytest.raises(CampaignLiveEvaluatorError) as exc:
        run_live_evaluator_campaign(
            prep, tmp_path / "blocked-campaign-drift", envelope=envelope,
            decision=decision, timeout_seconds=30, reasoning_effort="high",
        )
    assert exc.value.reason == "role_bindings_drifted"
    assert exc.value.runner_call_count == 0


def test_unresolved_pi_model_blocks_provider_free() -> None:
    with pytest.raises(CampaignLiveEvaluatorError) as exc:
        live_evaluator._verify_locked_evaluator_effort(
            "deepseek", "missing-model", "0.82.1", "high",
        )
    assert exc.value.reason == "evaluator_model_unresolved"
    assert exc.value.runner_call_count == 0


def test_supported_label_cannot_map_to_different_positive_effort(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    capability = {
        "harnessVersion": "0.82.1", "providerId": "deepseek",
        "modelId": "deepseek-v4-pro", "supportedEfforts": ["high"],
        "hasEffortMapping": True, "mappedEffort": "medium",
    }
    monkeypatch.setattr(
        live_evaluator.subprocess, "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0, stdout=json.dumps(capability),
        ),
    )
    with pytest.raises(CampaignLiveEvaluatorError) as exc:
        live_evaluator._verify_locked_evaluator_effort(
            "deepseek", "deepseek-v4-pro", "0.82.1", "high",
        )
    assert exc.value.reason == "evaluator_effort_unsupported"
    assert exc.value.runner_call_count == 0


def test_effective_effort_mismatch_fails_closed(
    prepared_lifecycle, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    prep, envelope, decision, receipt, harness, _, _ = prepared_lifecycle
    monkeypatch.setattr(
        live_evaluator, "_invoker",
        lambda **kwargs: EvaluatorOutcome(
            receipt, harness, _verdict(), effective_reasoning_effort="medium",
        ),
    )
    with pytest.raises(CampaignLiveEvaluatorError) as exc:
        run_live_evaluator_campaign(
            prep, tmp_path / "blocked-effective", envelope=envelope,
            decision=decision, timeout_seconds=30, reasoning_effort="high",
        )
    assert exc.value.reason == "evaluator_effort_or_retry_posture_invalid"
    assert not (tmp_path / "blocked-effective").exists()


@pytest.mark.parametrize("fault,reason", [
    ("missing_result", "evaluator_verdict_invalid"),
    ("retry", "evaluator_invocation_failed"),
    ("identity", "evaluator_actual_identity_mismatch"),
    ("unknown_ref", "evaluator_criterion_or_evidence_reference_invalid"),
])
def test_evaluator_fails_closed(prepared_lifecycle, tmp_path, monkeypatch, fault, reason) -> None:
    prep, envelope, decision, receipt, harness, _, _ = prepared_lifecycle
    verdict = _verdict()
    if fault == "unknown_ref":
        verdict["structured_acceptance_results"][0]["evidence_refs"] = ["undeclared-ref"]
    changes = {"evaluator_result": verdict}
    if fault == "missing_result":
        changes["evaluator_result"] = None
    if fault == "retry":
        changes["retry_count"] = 1
    if fault == "identity":
        changes["actual_identity"] = FakeIdentity("other", "deepseek-v4-pro", "pi-coding-agent", "0.82.1")
    monkeypatch.setattr(live_evaluator, "_invoker", lambda **kwargs: EvaluatorOutcome(receipt, harness, **changes))
    with pytest.raises(CampaignLiveEvaluatorError) as exc:
        run_live_evaluator_campaign(prep, tmp_path / "failed", envelope=envelope, decision=decision, timeout_seconds=30, reasoning_effort="high")
    assert exc.value.reason == reason
    assert not (tmp_path / "failed").exists()


def test_write_grant_blocks_before_invocation(prepared_lifecycle, tmp_path, monkeypatch) -> None:
    prep, envelope, decision, _, _, _, _ = prepared_lifecycle
    from dataclasses import replace
    write = PiPermissionGrant(permission="files.write", resource="proof_target.txt")
    envelope = replace(envelope, requested_permissions=envelope.requested_permissions + (write,), granted_permissions=envelope.granted_permissions + (write,))
    decision = replace(decision, requested_permissions=envelope.requested_permissions, granted_permissions=envelope.granted_permissions)
    monkeypatch.setattr(live_evaluator, "_invoker", lambda **kwargs: pytest.fail("provider seam reached"))
    with pytest.raises(CampaignLiveEvaluatorError) as exc:
        run_live_evaluator_campaign(prep, tmp_path / "failed", envelope=envelope, decision=decision, timeout_seconds=30, reasoning_effort="high")
    assert exc.value.reason == "evaluator_mutation_permission_forbidden"


@pytest.mark.parametrize("verdict,criterion,state,task_state", [
    ("passed", "pass", "completed", "completed"),
    ("passed_with_advisories", "advisory", "completed", "completed"),
    ("repair_required", "fail", "blocked", "repair_required"),
    ("blocked", "fail", "blocked", "blocked"),
])
def test_all_canonical_verdicts_publish_consistent_state(
    prepared_lifecycle, tmp_path, monkeypatch, verdict, criterion, state, task_state,
) -> None:
    prep, envelope, decision, receipt, harness, _, _ = prepared_lifecycle
    result = _verdict()
    result["verdict"] = verdict
    result["structured_acceptance_results"][0]["verdict"] = criterion
    monkeypatch.setattr(live_evaluator, "_invoker", lambda **kwargs: EvaluatorOutcome(receipt, harness, result))
    output = run_live_evaluator_campaign(
        prep, tmp_path / "final-verdict", envelope=envelope, decision=decision,
        timeout_seconds=30, reasoning_effort="high",
    )
    document = json.loads((output / "campaign-input.json").read_text())
    validate_campaign_document(document, "CE-L2 verdict state")
    assert document["campaign"]["state"] == state
    assert document["tasks"][0]["state"] == task_state
    assert document["receipts"][0]["final_verdict"] == verdict


def test_timeout_preserves_only_bounded_phase_diagnostics(
    prepared_lifecycle, tmp_path, monkeypatch,
) -> None:
    prep, envelope, decision, receipt, harness, _, _ = prepared_lifecycle
    phases = (
        "wrapper_started", "runtime_identity_established",
        "session_initialized", "provider_request_started",
    )
    outcome = EvaluatorOutcome(
        receipt, harness, None, ok=False,
        diagnostic_class="adapter_timeout", diagnostic_stage="adapter_timeout",
        observed_execution_phases=phases,
        highest_observed_execution_phase="provider_request_started",
    )
    monkeypatch.setattr(live_evaluator, "_invoker", lambda **kwargs: outcome)
    with pytest.raises(CampaignLiveEvaluatorError) as exc:
        run_live_evaluator_campaign(
            prep, tmp_path / "failed-timeout", envelope=envelope, decision=decision,
            timeout_seconds=30, reasoning_effort="high",
        )
    payload = exc.value.to_payload()
    assert payload["failure_reason"] == "evaluator_invocation_failed"
    assert payload["runner_call_count"] == 1
    assert payload["observed_execution_phases"] == list(phases)
    assert payload["highest_observed_execution_phase"] == "provider_request_started"
    assert "evaluator_result" not in payload
    assert not (tmp_path / "failed-timeout").exists()


def test_completed_source_campaign_cannot_be_reused(prepared_lifecycle) -> None:
    prep, _, _, _, _, _, _ = prepared_lifecycle
    source = json.loads(prep.campaign_path.read_text())
    source["campaign"]["state"] = "completed"
    source["campaign_state"]["state"] = "completed"
    prep.campaign_path.write_text(json.dumps(source))
    with pytest.raises(CampaignLiveEvaluatorError) as exc:
        prepare_live_evaluator_campaign(
            prep.campaign_path, prep.checkpoint_dir, prep.target_path,
            harness_id="pi-coding-agent", harness_version="0.82.1",
        )
    assert exc.value.reason == "source_campaign_not_fresh"


@pytest.mark.parametrize("effort,harness_version", [
    ("medium", "0.82.1"),
    ("off", "0.82.0"),
])
def test_locked_executor_configuration_blocks_before_provider(
    tmp_path, monkeypatch, effort, harness_version,
) -> None:
    campaign_path, target, _ = _make_canonical_live_campaign(
        tmp_path, executor_provider="deepseek", executor_model="deepseek-v4-pro",
    )
    campaign = json.loads(campaign_path.read_text())
    campaign["role_bindings"][1]["live_role_binding"].update({
        "harness_id": "pi-coding-agent", "harness_version": "0.82.1",
        "reasoning_effort": "off",
    })
    campaign_path.write_text(json.dumps(campaign))
    prep = prepare_live_executor_campaign(campaign_path, target)
    envelope, decision = _build_envelope_and_decision(prep)
    from dataclasses import replace
    envelope = replace(envelope, harness_version=harness_version)
    monkeypatch.setattr(live_executor, "_invoker", lambda **kwargs: pytest.fail("provider seam reached"))
    with pytest.raises(CampaignLiveExecutorError) as exc:
        run_live_executor_campaign(
            prep, tmp_path / "blocked", envelope=envelope, decision=decision,
            timeout_seconds=30, campaign_path=campaign_path,
            reasoning_effort=effort,
        )
    assert exc.value.failure_reason == "locked_executor_configuration_mismatch"
