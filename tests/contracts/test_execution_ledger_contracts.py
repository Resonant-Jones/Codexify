import importlib
import json
import subprocess
import sys

import pytest
from pydantic import ValidationError

from guardian.agents.execution_ledger_contracts import (
    AcceptanceCriterionContract,
    CompletionProofGateArtifact,
    ImplementationPlanGateArtifact,
    IntentScopeGateArtifact,
    has_blocking_acceptance_failure,
    has_passed_acceptance,
)


def _valid_criterion(**overrides):
    payload = {
        "criterion_id": "crit-1",
        "requirement": "Validation command succeeds",
        "validation_mode": "unit_test",
        "expected_evidence": "pytest passes",
        "observed_evidence": "13 passed",
        "result": "passed",
        "linked_attempt_id": "attempt-1",
        "linked_run_id": "run-1",
    }
    payload.update(overrides)
    return payload


def _valid_intent_scope(**overrides):
    payload = {
        "work_order_id": "wo-1",
        "campaign_id": "camp-1",
        "source_thread_id": "thread-1",
        "source_message_id": "msg-1",
        "title": "Add ledger token docs",
        "intent_summary": "Define bounded token domain",
        "scope_statement": "Docs and contracts only",
        "in_scope": ["guardian/agents/"],
        "out_of_scope": ["guardian/routes/"],
        "affected_files_or_domains": ["contracts", "docs"],
        "acceptance_criteria": [_valid_criterion()],
        "reviewer": "reviewer-1",
        "decision": "approved",
        "decision_rationale": "Scope is bounded",
        "timestamp": "2026-05-16T10:00:00Z",
    }
    payload.update(overrides)
    return payload


def _valid_plan_artifact(**overrides):
    payload = {
        "work_order_id": "wo-1",
        "plan_id": "plan-1",
        "linked_intent_scope_artifact_id": "intent-1",
        "expected_files_to_read": ["docs/architecture/README.md"],
        "expected_files_to_modify": ["guardian/agents/execution_ledger_contracts.py"],
        "validation_commands": [".venv/bin/pytest -v tests/contracts/test_execution_ledger_contracts.py"],
        "rollback_plan": "Revert commit if contract tests fail",
        "risk_notes": "Low risk, contract-only",
        "dependency_notes": "Requires token registry",
        "reviewer": "reviewer-2",
        "decision": "approved",
        "decision_rationale": "Plan is bounded",
        "timestamp": "2026-05-16T10:05:00Z",
    }
    payload.update(overrides)
    return payload


def _valid_completion_proof(**overrides):
    payload = {
        "work_order_id": "wo-1",
        "attempt_id": "attempt-1",
        "guardian_run_id": "run-1",
        "command_run_id": "cmdrun-1",
        "completion_receipt_ref": "receipt-1",
        "validation_commands_run": ["pytest -v tests/contracts/test_execution_ledger_contracts.py"],
        "validation_result": "passed",
        "changed_files_summary": ["guardian/agents/execution_ledger_contracts.py"],
        "acceptance_criteria": [_valid_criterion()],
        "delivery_status": "source_thread_result_delivered",
        "follow_up_work_order_ids": ["wo-2"],
        "reviewer": "reviewer-3",
        "decision": "proof_accepted",
        "decision_rationale": "Durable evidence is complete",
        "timestamp": "2026-05-16T10:10:00Z",
    }
    payload.update(overrides)
    return payload


def test_valid_acceptance_criterion_contract_can_be_created() -> None:
    criterion = AcceptanceCriterionContract.model_validate(_valid_criterion())
    assert criterion.criterion_id == "crit-1"
    assert criterion.validation_mode == "unit_test"
    assert criterion.result == "passed"


def test_invalid_validation_mode_is_rejected() -> None:
    with pytest.raises(ValidationError):
        AcceptanceCriterionContract.model_validate(
            _valid_criterion(validation_mode="not_a_mode")
        )


def test_invalid_acceptance_criterion_result_is_rejected() -> None:
    with pytest.raises(ValidationError):
        AcceptanceCriterionContract.model_validate(
            _valid_criterion(result="not_a_result")
        )


def test_valid_intent_scope_gate_artifact_can_be_created() -> None:
    artifact = IntentScopeGateArtifact.model_validate(_valid_intent_scope())
    assert artifact.decision == "approved"
    assert len(artifact.acceptance_criteria) == 1


def test_invalid_intent_scope_decision_is_rejected() -> None:
    with pytest.raises(ValidationError):
        IntentScopeGateArtifact.model_validate(
            _valid_intent_scope(decision="not_a_gate_decision")
        )


def test_valid_implementation_plan_gate_artifact_can_be_created() -> None:
    artifact = ImplementationPlanGateArtifact.model_validate(
        _valid_plan_artifact()
    )
    assert artifact.decision == "approved"
    assert artifact.validation_commands


def test_invalid_implementation_plan_decision_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ImplementationPlanGateArtifact.model_validate(
            _valid_plan_artifact(decision="not_a_gate_decision")
        )


def test_valid_completion_proof_gate_artifact_can_be_created() -> None:
    artifact = CompletionProofGateArtifact.model_validate(
        _valid_completion_proof()
    )
    assert artifact.decision == "proof_accepted"
    assert artifact.validation_result == "passed"


def test_invalid_proof_decision_is_rejected() -> None:
    with pytest.raises(ValidationError):
        CompletionProofGateArtifact.model_validate(
            _valid_completion_proof(decision="not_a_proof_decision")
        )


@pytest.mark.parametrize(
    "builder,field_name",
    [
        (_valid_criterion, "criterion_id"),
        (_valid_criterion, "requirement"),
        (_valid_intent_scope, "work_order_id"),
        (_valid_intent_scope, "decision_rationale"),
        (_valid_plan_artifact, "rollback_plan"),
        (_valid_plan_artifact, "reviewer"),
        (_valid_completion_proof, "attempt_id"),
        (_valid_completion_proof, "decision_rationale"),
    ],
)
def test_required_empty_string_fields_are_rejected(builder, field_name) -> None:
    with pytest.raises(ValidationError):
        payload = builder(**{field_name: "   "})
        model_map = {
            _valid_criterion: AcceptanceCriterionContract,
            _valid_intent_scope: IntentScopeGateArtifact,
            _valid_plan_artifact: ImplementationPlanGateArtifact,
            _valid_completion_proof: CompletionProofGateArtifact,
        }
        model_map[builder].model_validate(payload)


def test_list_defaults_are_not_shared_between_instances() -> None:
    first = IntentScopeGateArtifact.model_validate(
        _valid_intent_scope(
            in_scope=[],
            out_of_scope=[],
            affected_files_or_domains=[],
            acceptance_criteria=[],
        )
    )
    second = IntentScopeGateArtifact.model_validate(
        _valid_intent_scope(
            work_order_id="wo-2",
            campaign_id="camp-2",
            title="Second",
            in_scope=[],
            out_of_scope=[],
            affected_files_or_domains=[],
            acceptance_criteria=[],
        )
    )

    first.in_scope.append("guardian/agents/")
    first.acceptance_criteria.append(
        AcceptanceCriterionContract.model_validate(_valid_criterion())
    )

    assert second.in_scope == []
    assert second.acceptance_criteria == []


def test_contract_objects_serialize_to_dicts() -> None:
    artifact = CompletionProofGateArtifact.model_validate(
        _valid_completion_proof()
    )
    payload = artifact.model_dump(mode="json")
    assert payload["work_order_id"] == "wo-1"
    assert payload["decision"] == "proof_accepted"
    assert payload["acceptance_criteria"][0]["criterion_id"] == "crit-1"


def test_contract_module_import_is_pure() -> None:
    script = """
import importlib
import json
import sys

before = set(sys.modules)
importlib.import_module('guardian.agents.execution_ledger_contracts')
after = set(sys.modules) - before
blocked_prefixes = ('guardian.routes', 'guardian.workers', 'guardian.db', 'frontend')
violations = sorted(name for name in after if name.startswith(blocked_prefixes))
print(json.dumps(violations))
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        check=True,
        text=True,
    )
    violations = json.loads(result.stdout.strip() or "[]")
    assert violations == []


def test_acceptance_helpers_identify_passed_and_blocking_failures() -> None:
    passed = [
        AcceptanceCriterionContract.model_validate(_valid_criterion()),
        AcceptanceCriterionContract.model_validate(
            _valid_criterion(criterion_id="crit-2", result="passed")
        ),
    ]
    assert has_passed_acceptance(passed)
    assert not has_blocking_acceptance_failure(passed)

    mixed = [
        AcceptanceCriterionContract.model_validate(_valid_criterion()),
        AcceptanceCriterionContract.model_validate(
            _valid_criterion(criterion_id="crit-3", result="blocked")
        ),
    ]
    assert not has_passed_acceptance(mixed)
    assert has_blocking_acceptance_failure(mixed)

    assert not has_passed_acceptance([])
    assert not has_blocking_acceptance_failure([])
