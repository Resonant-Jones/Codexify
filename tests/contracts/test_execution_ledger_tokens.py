import json
import importlib.util
from pathlib import Path
import subprocess
import sys

_ROOT = Path(__file__).resolve().parents[2]
_TOKEN_MODULE_PATH = _ROOT / "guardian" / "agents" / "execution_ledger_tokens.py"


def _load_token_module():
    spec = importlib.util.spec_from_file_location(
        "execution_ledger_tokens_under_test",
        _TOKEN_MODULE_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ledger_tokens = _load_token_module()


def test_gate_phase_tokens_are_stable() -> None:
    expected = (
        "intent_scope",
        "implementation_plan",
        "completion_proof",
    )
    assert ledger_tokens.GATE_PHASES == expected


def test_gate_decision_tokens_are_stable() -> None:
    expected = (
        "pending",
        "approved",
        "rejected",
        "changes_requested",
        "deferred",
        "superseded",
    )
    assert ledger_tokens.GATE_DECISIONS == expected


def test_plan_state_tokens_are_stable() -> None:
    expected = (
        "not_started",
        "draft",
        "ready_for_review",
        "approved",
        "changes_requested",
        "superseded",
        "abandoned",
    )
    assert ledger_tokens.PLAN_STATES == expected


def test_acceptance_validation_mode_tokens_are_stable() -> None:
    expected = (
        "manual_review",
        "unit_test",
        "integration_test",
        "typecheck",
        "lint",
        "runtime_probe",
        "docs_validation",
        "diff_inspection",
    )
    assert ledger_tokens.ACCEPTANCE_VALIDATION_MODES == expected


def test_acceptance_criterion_result_tokens_are_stable() -> None:
    expected = (
        "not_checked",
        "passed",
        "failed",
        "blocked",
        "not_applicable",
    )
    assert ledger_tokens.ACCEPTANCE_CRITERION_RESULTS == expected


def test_proof_decision_tokens_are_stable() -> None:
    expected = (
        "proof_pending",
        "proof_accepted",
        "proof_rejected",
        "follow_up_required",
        "evidence_incomplete",
    )
    assert ledger_tokens.PROOF_DECISIONS == expected


def test_escalation_reason_tokens_are_stable() -> None:
    expected = (
        "scope_unclear",
        "plan_rejected",
        "validation_failed",
        "delivery_failed",
        "lineage_missing",
        "attempt_failed",
        "evidence_incomplete",
        "out_of_scope_change",
        "requires_human_decision",
    )
    assert ledger_tokens.ESCALATION_REASONS == expected


def test_token_collections_are_non_empty_and_unique() -> None:
    collections = (
        ledger_tokens.GATE_PHASES,
        ledger_tokens.GATE_DECISIONS,
        ledger_tokens.PLAN_STATES,
        ledger_tokens.ACCEPTANCE_VALIDATION_MODES,
        ledger_tokens.ACCEPTANCE_CRITERION_RESULTS,
        ledger_tokens.PROOF_DECISIONS,
        ledger_tokens.ESCALATION_REASONS,
    )
    for values in collections:
        assert values
        assert len(values) == len(set(values))


def test_validators_accept_known_values() -> None:
    for value in ledger_tokens.GATE_PHASES:
        assert ledger_tokens.is_valid_gate_phase(value)
    for value in ledger_tokens.GATE_DECISIONS:
        assert ledger_tokens.is_valid_gate_decision(value)
    for value in ledger_tokens.PLAN_STATES:
        assert ledger_tokens.is_valid_plan_state(value)
    for value in ledger_tokens.ACCEPTANCE_VALIDATION_MODES:
        assert ledger_tokens.is_valid_acceptance_validation_mode(value)
    for value in ledger_tokens.ACCEPTANCE_CRITERION_RESULTS:
        assert ledger_tokens.is_valid_acceptance_criterion_result(value)
    for value in ledger_tokens.PROOF_DECISIONS:
        assert ledger_tokens.is_valid_proof_decision(value)
    for value in ledger_tokens.ESCALATION_REASONS:
        assert ledger_tokens.is_valid_escalation_reason(value)


def test_validators_reject_unknown_values() -> None:
    unknown = "not_a_valid_execution_ledger_token"
    assert not ledger_tokens.is_valid_gate_phase(unknown)
    assert not ledger_tokens.is_valid_gate_decision(unknown)
    assert not ledger_tokens.is_valid_plan_state(unknown)
    assert not ledger_tokens.is_valid_acceptance_validation_mode(unknown)
    assert not ledger_tokens.is_valid_acceptance_criterion_result(unknown)
    assert not ledger_tokens.is_valid_proof_decision(unknown)
    assert not ledger_tokens.is_valid_escalation_reason(unknown)


def test_overlapping_approved_value_is_domain_scoped() -> None:
    assert "approved" in ledger_tokens.GATE_DECISIONS
    assert "approved" in ledger_tokens.PLAN_STATES
    assert ledger_tokens.is_valid_gate_decision("approved")
    assert ledger_tokens.is_valid_plan_state("approved")
    assert not ledger_tokens.is_valid_gate_phase("approved")


def test_overlapping_evidence_incomplete_value_is_domain_scoped() -> None:
    assert "evidence_incomplete" in ledger_tokens.PROOF_DECISIONS
    assert "evidence_incomplete" in ledger_tokens.ESCALATION_REASONS
    assert ledger_tokens.is_valid_proof_decision("evidence_incomplete")
    assert ledger_tokens.is_valid_escalation_reason("evidence_incomplete")
    assert not ledger_tokens.is_valid_acceptance_criterion_result(
        "evidence_incomplete"
    )


def test_execution_ledger_tokens_module_import_is_pure() -> None:
    script = f"""
import importlib.util
import json
from pathlib import Path
import sys

before = set(sys.modules)
module_path = Path({str(_TOKEN_MODULE_PATH)!r})
spec = importlib.util.spec_from_file_location(
    'execution_ledger_tokens_subprocess',
    module_path,
)
module = importlib.util.module_from_spec(spec)
assert spec is not None
assert spec.loader is not None
spec.loader.exec_module(module)
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
