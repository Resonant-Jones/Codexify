from __future__ import annotations

from dataclasses import dataclass, field
import json
import subprocess
import sys
from typing import Any

from guardian.agents.execution_ledger_contracts import (
    AcceptanceCriterionContract,
    CompletionProofGateArtifact,
    ImplementationPlanGateArtifact,
    IntentScopeGateArtifact,
)
from guardian.agents.execution_ledger_store import (
    COMPLETION_PROOF_GATE_KEY,
    EXECUTION_LEDGER_KEY,
    IMPLEMENTATION_PLAN_GATE_KEY,
    INTENT_SCOPE_GATE_KEY,
    get_completion_proof_gate,
    get_implementation_plan_gate,
    get_intent_scope_gate,
    read_execution_ledger_metadata,
    save_completion_proof_gate,
    save_implementation_plan_gate,
    save_intent_scope_gate,
    set_completion_proof_gate,
    set_implementation_plan_gate,
    set_intent_scope_gate,
)
from guardian.agents.work_orders import WorkOrderUpdate


@dataclass
class _FakeWorkOrder:
    extra_meta: dict[str, Any] = field(default_factory=dict)


class _FakeStore:
    def __init__(self, work_order: _FakeWorkOrder | None):
        self._work_order = work_order
        self.update_calls: list[tuple[str, WorkOrderUpdate]] = []

    def get_work_order(self, work_order_id: str) -> _FakeWorkOrder | None:
        if self._work_order is None:
            return None
        if work_order_id != "wo-1":
            return None
        return self._work_order

    def update_work_order(
        self,
        work_order_id: str,
        payload: WorkOrderUpdate,
    ) -> _FakeWorkOrder:
        assert self._work_order is not None
        self.update_calls.append((work_order_id, payload))
        self._work_order = _FakeWorkOrder(extra_meta=dict(payload.extra_meta or {}))
        return self._work_order


def _criterion(**overrides: Any) -> AcceptanceCriterionContract:
    payload = {
        "criterion_id": "crit-1",
        "requirement": "Unit tests pass",
        "validation_mode": "unit_test",
        "expected_evidence": "pytest passes",
        "observed_evidence": "pytest passed",
        "result": "passed",
        "linked_attempt_id": "attempt-1",
        "linked_run_id": "run-1",
    }
    payload.update(overrides)
    return AcceptanceCriterionContract.model_validate(payload)


def _intent_scope_artifact(**overrides: Any) -> IntentScopeGateArtifact:
    payload = {
        "work_order_id": "wo-1",
        "campaign_id": "camp-1",
        "source_thread_id": "thread-1",
        "source_message_id": "msg-1",
        "title": "Implement execution-ledger storage seam",
        "intent_summary": "Persist gate artifacts in work-order metadata",
        "scope_statement": "Internal store helpers only",
        "in_scope": ["guardian/agents/execution_ledger_store.py"],
        "out_of_scope": ["guardian/routes/", "frontend/"],
        "affected_files_or_domains": ["guardian/agents", "tests/agents"],
        "acceptance_criteria": [_criterion().model_dump(mode="json")],
        "reviewer": "reviewer-1",
        "decision": "approved",
        "decision_rationale": "Bounded internal seam",
        "timestamp": "2026-05-16T12:00:00Z",
    }
    payload.update(overrides)
    return IntentScopeGateArtifact.model_validate(payload)


def _implementation_plan_artifact(
    **overrides: Any,
) -> ImplementationPlanGateArtifact:
    payload = {
        "work_order_id": "wo-1",
        "plan_id": "plan-1",
        "linked_intent_scope_artifact_id": "intent-1",
        "expected_files_to_read": [
            "guardian/agents/work_order_store.py",
            "guardian/agents/work_orders.py",
        ],
        "expected_files_to_modify": [
            "guardian/agents/execution_ledger_store.py",
            "tests/agents/test_execution_ledger_store.py",
        ],
        "validation_commands": [
            ".venv/bin/pytest -v tests/agents/test_execution_ledger_store.py"
        ],
        "rollback_plan": "Revert commit if contract tests fail",
        "risk_notes": "Low risk metadata-only change",
        "dependency_notes": "Requires execution_ledger_contracts",
        "reviewer": "reviewer-2",
        "decision": "approved",
        "decision_rationale": "Plan is scoped and testable",
        "timestamp": "2026-05-16T12:05:00Z",
    }
    payload.update(overrides)
    return ImplementationPlanGateArtifact.model_validate(payload)


def _completion_proof_artifact(**overrides: Any) -> CompletionProofGateArtifact:
    payload = {
        "work_order_id": "wo-1",
        "attempt_id": "attempt-1",
        "guardian_run_id": "run-1",
        "command_run_id": "cmd-1",
        "completion_receipt_ref": "receipt-1",
        "validation_commands_run": [
            ".venv/bin/pytest -v tests/agents/test_execution_ledger_store.py"
        ],
        "validation_result": "passed",
        "changed_files_summary": [
            "guardian/agents/execution_ledger_store.py",
            "tests/agents/test_execution_ledger_store.py",
        ],
        "acceptance_criteria": [_criterion().model_dump(mode="json")],
        "delivery_status": "source_thread_result_delivered",
        "follow_up_work_order_ids": ["wo-2"],
        "reviewer": "reviewer-3",
        "decision": "proof_accepted",
        "decision_rationale": "Durable attempt evidence present",
        "timestamp": "2026-05-16T12:10:00Z",
    }
    payload.update(overrides)
    return CompletionProofGateArtifact.model_validate(payload)


def test_empty_metadata_returns_all_gates_absent() -> None:
    work_order = _FakeWorkOrder(extra_meta={})
    metadata = read_execution_ledger_metadata(work_order)
    assert metadata == {
        INTENT_SCOPE_GATE_KEY: None,
        IMPLEMENTATION_PLAN_GATE_KEY: None,
        COMPLETION_PROOF_GATE_KEY: None,
    }


def test_set_intent_scope_gate_preserves_unrelated_metadata() -> None:
    work_order = _FakeWorkOrder(
        extra_meta={
            "owner": "local",
            "priority_hint": "high",
            EXECUTION_LEDGER_KEY: {"legacy_key": "keep"},
        }
    )
    artifact = _intent_scope_artifact()

    updated = set_intent_scope_gate(work_order, artifact)

    assert updated["owner"] == "local"
    assert updated["priority_hint"] == "high"
    assert updated[EXECUTION_LEDGER_KEY]["legacy_key"] == "keep"
    assert (
        updated[EXECUTION_LEDGER_KEY][INTENT_SCOPE_GATE_KEY]["work_order_id"]
        == "wo-1"
    )


def test_setting_implementation_plan_preserves_existing_intent_scope_gate() -> None:
    work_order = _FakeWorkOrder(extra_meta={"owner": "local"})
    intent_updated = set_intent_scope_gate(work_order, _intent_scope_artifact())

    follow_on = _FakeWorkOrder(extra_meta=intent_updated)
    updated = set_implementation_plan_gate(
        follow_on,
        _implementation_plan_artifact(),
    )

    assert updated[EXECUTION_LEDGER_KEY][INTENT_SCOPE_GATE_KEY] is not None
    assert (
        updated[EXECUTION_LEDGER_KEY][INTENT_SCOPE_GATE_KEY]["title"]
        == "Implement execution-ledger storage seam"
    )
    assert (
        updated[EXECUTION_LEDGER_KEY][IMPLEMENTATION_PLAN_GATE_KEY]["plan_id"]
        == "plan-1"
    )


def test_setting_completion_proof_preserves_existing_other_gates() -> None:
    work_order = _FakeWorkOrder(extra_meta={"owner": "local"})
    with_intent = set_intent_scope_gate(work_order, _intent_scope_artifact())
    with_plan = set_implementation_plan_gate(
        _FakeWorkOrder(extra_meta=with_intent),
        _implementation_plan_artifact(),
    )

    updated = set_completion_proof_gate(
        _FakeWorkOrder(extra_meta=with_plan),
        _completion_proof_artifact(),
    )

    ledger = updated[EXECUTION_LEDGER_KEY]
    assert ledger[INTENT_SCOPE_GATE_KEY] is not None
    assert ledger[IMPLEMENTATION_PLAN_GATE_KEY] is not None
    assert ledger[COMPLETION_PROOF_GATE_KEY] is not None


def test_reading_each_stored_gate_returns_contract_models() -> None:
    work_order = _FakeWorkOrder(extra_meta={"owner": "local"})
    with_intent = set_intent_scope_gate(work_order, _intent_scope_artifact())
    with_plan = set_implementation_plan_gate(
        _FakeWorkOrder(extra_meta=with_intent),
        _implementation_plan_artifact(),
    )
    with_proof = set_completion_proof_gate(
        _FakeWorkOrder(extra_meta=with_plan),
        _completion_proof_artifact(),
    )

    hydrated = _FakeWorkOrder(extra_meta=with_proof)

    intent = get_intent_scope_gate(hydrated)
    plan = get_implementation_plan_gate(hydrated)
    proof = get_completion_proof_gate(hydrated)

    assert isinstance(intent, IntentScopeGateArtifact)
    assert isinstance(plan, ImplementationPlanGateArtifact)
    assert isinstance(proof, CompletionProofGateArtifact)


def test_invalid_stored_gate_payload_fails_closed_to_none() -> None:
    work_order = _FakeWorkOrder(
        extra_meta={
            EXECUTION_LEDGER_KEY: {
                INTENT_SCOPE_GATE_KEY: {"work_order_id": "wo-1"},
                IMPLEMENTATION_PLAN_GATE_KEY: "not-a-dict",
                COMPLETION_PROOF_GATE_KEY: {"decision": "proof_accepted"},
            }
        }
    )

    assert get_intent_scope_gate(work_order) is None
    assert get_implementation_plan_gate(work_order) is None
    assert get_completion_proof_gate(work_order) is None


def test_existing_non_execution_ledger_metadata_is_unchanged() -> None:
    original = {
        "owner": "local",
        "keep_number": 7,
        "keep_list": ["a", "b"],
    }
    work_order = _FakeWorkOrder(extra_meta=dict(original))

    updated = set_intent_scope_gate(work_order, _intent_scope_artifact())

    assert updated["owner"] == original["owner"]
    assert updated["keep_number"] == original["keep_number"]
    assert updated["keep_list"] == original["keep_list"]


def test_nested_list_fields_round_trip_correctly() -> None:
    artifact = _intent_scope_artifact(
        in_scope=["guardian/agents", "tests/agents"],
        out_of_scope=["guardian/routes", "frontend/src"],
        affected_files_or_domains=["agents", "contracts"],
        acceptance_criteria=[
            _criterion(
                criterion_id="crit-1",
                result="passed",
                expected_evidence="pytest output",
                observed_evidence="2 tests passed",
            ).model_dump(mode="json"),
            _criterion(
                criterion_id="crit-2",
                result="not_checked",
                expected_evidence="manual review",
                observed_evidence=None,
            ).model_dump(mode="json"),
        ],
    )

    updated = set_intent_scope_gate(_FakeWorkOrder(extra_meta={}), artifact)
    loaded = get_intent_scope_gate(_FakeWorkOrder(extra_meta=updated))

    assert loaded is not None
    assert loaded.in_scope == ["guardian/agents", "tests/agents"]
    assert loaded.out_of_scope == ["guardian/routes", "frontend/src"]
    assert loaded.affected_files_or_domains == ["agents", "contracts"]
    assert [c.criterion_id for c in loaded.acceptance_criteria] == [
        "crit-1",
        "crit-2",
    ]


def test_module_import_is_pure() -> None:
    script = """
import importlib
import json
import sys

before = set(sys.modules)
importlib.import_module('guardian.agents.execution_ledger_store')
after = set(sys.modules) - before
blocked_prefixes = (
    'guardian.routes',
    'guardian.workers',
    'frontend',
    'codex_runner',
    'guardian.queue',
)
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


def test_store_backed_save_helpers_use_work_order_update_path() -> None:
    store = _FakeStore(_FakeWorkOrder(extra_meta={"owner": "local"}))

    updated = save_intent_scope_gate(store, "wo-1", _intent_scope_artifact())
    assert isinstance(updated, _FakeWorkOrder)
    assert len(store.update_calls) == 1

    work_order_id, payload = store.update_calls[0]
    assert work_order_id == "wo-1"
    assert isinstance(payload, WorkOrderUpdate)
    assert payload.extra_meta is not None
    assert EXECUTION_LEDGER_KEY in payload.extra_meta

    save_implementation_plan_gate(store, "wo-1", _implementation_plan_artifact())
    save_completion_proof_gate(store, "wo-1", _completion_proof_artifact())

    final_meta = store._work_order.extra_meta
    assert final_meta[EXECUTION_LEDGER_KEY][INTENT_SCOPE_GATE_KEY] is not None
    assert (
        final_meta[EXECUTION_LEDGER_KEY][IMPLEMENTATION_PLAN_GATE_KEY]
        is not None
    )
    assert final_meta[EXECUTION_LEDGER_KEY][COMPLETION_PROOF_GATE_KEY] is not None


def test_save_helpers_raise_when_work_order_missing() -> None:
    store = _FakeStore(work_order=None)

    try:
        save_intent_scope_gate(store, "wo-missing", _intent_scope_artifact())
    except LookupError as exc:
        assert "unknown work_order_id" in str(exc)
    else:
        raise AssertionError("Expected LookupError for missing work order")
