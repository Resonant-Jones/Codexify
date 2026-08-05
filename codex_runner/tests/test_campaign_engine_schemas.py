from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator, FormatChecker


RUNNER_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = RUNNER_ROOT / "schemas" / "campaign_engine"
FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "campaign_engine"

SCHEMA_FILES = {
    "campaign": "campaign.schema.json",
    "task": "task.schema.json",
    "role_binding": "role_binding.schema.json",
    "attempt": "attempt.schema.json",
    "evaluation": "evaluation.schema.json",
    "receipt": "receipt.schema.json",
    "decision_gate": "decision_gate.schema.json",
    "campaign_state": "campaign_state.schema.json",
}

COLLECTION_SCHEMAS = {
    "tasks": "task",
    "role_bindings": "role_binding",
    "attempts": "attempt",
    "evaluations": "evaluation",
    "receipts": "receipt",
    "decision_gates": "decision_gate",
}

ORDERED_REFERENCES = {
    "ordered_task_ids": ("tasks", "task_id"),
    "ordered_role_binding_ids": ("role_bindings", "binding_id"),
    "ordered_attempt_ids": ("attempts", "attempt_id"),
    "ordered_evaluation_ids": ("evaluations", "evaluation_id"),
    "ordered_receipt_ids": ("receipts", "receipt_id"),
    "ordered_decision_gate_ids": ("decision_gates", "decision_gate_id"),
}

IMMUTABLE_BINDING_FIELDS = (
    "role",
    "provider_id",
    "model_id",
    "adapter_id",
    "binding_revision",
    "configuration_hash",
)


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _fixture(name: str) -> dict[str, Any]:
    return _read_json(FIXTURE_ROOT / name)


def _validators() -> dict[str, Draft202012Validator]:
    validators: dict[str, Draft202012Validator] = {}
    for entity, filename in SCHEMA_FILES.items():
        schema = _read_json(SCHEMA_ROOT / filename)
        Draft202012Validator.check_schema(schema)
        validators[entity] = Draft202012Validator(
            schema,
            format_checker=FormatChecker(),
        )
    return validators


def _schema_errors(document: dict[str, Any]) -> list[str]:
    validators = _validators()
    errors = [
        f"campaign: {error.message}"
        for error in validators["campaign"].iter_errors(document["campaign"])
    ]
    errors.extend(
        f"campaign_state: {error.message}"
        for error in validators["campaign_state"].iter_errors(
            document["campaign_state"]
        )
    )
    for collection, schema_name in COLLECTION_SCHEMAS.items():
        for index, entity in enumerate(document[collection]):
            errors.extend(
                f"{collection}[{index}]: {error.message}"
                for error in validators[schema_name].iter_errors(entity)
            )
    return errors


def _indexed(
    items: list[dict[str, Any]], id_field: str
) -> dict[str, dict[str, Any]]:
    return {item[id_field]: item for item in items}


def _cross_object_errors(document: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    campaign = document["campaign"]
    campaign_state = document["campaign_state"]

    tasks = _indexed(document["tasks"], "task_id")
    attempts = _indexed(document["attempts"], "attempt_id")
    evaluations = _indexed(document["evaluations"], "evaluation_id")
    receipts = _indexed(document["receipts"], "receipt_id")
    decision_gates = _indexed(document["decision_gates"], "decision_gate_id")

    bindings: dict[str, dict[str, Any]] = {}
    for binding in document["role_bindings"]:
        prior = bindings.get(binding["binding_id"])
        if prior is not None:
            prior_identity = tuple(prior[field] for field in IMMUTABLE_BINDING_FIELDS)
            current_identity = tuple(
                binding[field] for field in IMMUTABLE_BINDING_FIELDS
            )
            if prior_identity != current_identity:
                errors.append(
                    "duplicate binding identity has conflicting "
                    "provider/model/configuration within one revision"
                )
            else:
                errors.append("duplicate binding identity is not allowed")
            continue
        bindings[binding["binding_id"]] = binding

    if campaign_state["campaign_id"] != campaign["campaign_id"]:
        errors.append("campaign state must belong to the declared campaign")
    if campaign_state["state"] != campaign["state"]:
        errors.append("campaign state snapshot must match the campaign state")

    for ordered_field, (collection, id_field) in ORDERED_REFERENCES.items():
        declared_order = [item[id_field] for item in document[collection]]
        if campaign_state[ordered_field] != declared_order:
            errors.append(f"{ordered_field} must match declared entity order")

    if campaign["task_ids"] != list(tasks):
        errors.append("campaign task_ids must match declared task order")
    if campaign["role_binding_ids"] != list(bindings):
        errors.append(
            "campaign role_binding_ids must match declared binding order"
        )

    for task in tasks.values():
        if task["campaign_id"] != campaign["campaign_id"]:
            errors.append(f"task {task['task_id']} belongs to another campaign")

    referenced_bindings = [
        bindings[binding_id]
        for binding_id in campaign["role_binding_ids"]
        if binding_id in bindings
    ]
    roles = {binding["role"] for binding in referenced_bindings}
    required_roles = {"auditor", "executor", "evaluator"}
    if not required_roles.issubset(roles):
        errors.append("campaign must declare auditor, executor, and evaluator roles")
    if any(binding["binding_state"] != "locked" for binding in referenced_bindings):
        errors.append("campaign role bindings must be locked")

    distinct_models = {
        (binding["provider_id"], binding["model_id"])
        for binding in referenced_bindings
    }
    model_limit = campaign["role_policy"]["maximum_distinct_models"]
    if not 1 <= len(distinct_models) <= model_limit:
        errors.append(
            f"campaign uses {len(distinct_models)} distinct models; "
            f"maximum is {model_limit}"
        )

    for binding in bindings.values():
        replaces_id = binding.get("replaces_binding_id")
        if replaces_id is None:
            continue
        if not campaign["role_policy"]["runtime_rebinding_allowed"]:
            errors.append("runtime rebinding is forbidden by campaign policy")
        replaced = bindings.get(replaces_id)
        if replaced is None:
            errors.append(
                f"binding {binding['binding_id']} replaces an undeclared binding"
            )
            continue
        if binding["binding_id"] == replaces_id:
            errors.append("rebinding must create a new binding identity")
        if binding["role"] != replaced["role"]:
            errors.append("rebinding must preserve the role")
        if binding["binding_revision"] != replaced["binding_revision"] + 1:
            errors.append("rebinding must increment binding_revision by one")

    for attempt in attempts.values():
        if attempt["task_id"] not in tasks:
            errors.append(
                f"attempt {attempt['attempt_id']} references an undeclared task"
            )
        if attempt["role_binding_id"] not in bindings:
            errors.append(
                f"attempt {attempt['attempt_id']} references an undeclared role binding"
            )

    for evaluation in evaluations.values():
        if evaluation["task_id"] not in tasks:
            errors.append(
                f"evaluation {evaluation['evaluation_id']} references an "
                "undeclared task"
            )
        if evaluation["evaluated_attempt_id"] not in attempts:
            errors.append(
                f"evaluation {evaluation['evaluation_id']} references an "
                "undeclared attempt"
            )
        evaluator_binding = bindings.get(evaluation["evaluator_binding_id"])
        if evaluator_binding is None:
            errors.append(
                f"evaluation {evaluation['evaluation_id']} references an "
                "undeclared evaluator binding"
            )
        elif evaluator_binding["role"] != "evaluator":
            errors.append("evaluation must use an evaluator role binding")

    subject_indexes: dict[str, set[str]] = {
        "campaign": {campaign["campaign_id"]},
        "task": set(tasks),
        "role_binding": set(bindings),
        "attempt": set(attempts),
        "evaluation": set(evaluations),
        "decision_gate": set(decision_gates),
    }
    for receipt in receipts.values():
        subject = receipt["subject"]
        subject_type = subject["subject_type"]
        if subject_type != "action" and subject["subject_id"] not in subject_indexes[
            subject_type
        ]:
            errors.append(
                f"receipt {receipt['receipt_id']} references an undeclared subject"
            )

    for gate in decision_gates.values():
        if gate["campaign_id"] != campaign["campaign_id"]:
            errors.append(
                f"decision gate {gate['decision_gate_id']} belongs to another campaign"
            )
        if "task_id" in gate and gate["task_id"] not in tasks:
            errors.append(
                f"decision gate {gate['decision_gate_id']} references an undeclared task"
            )
        if "attempt_id" in gate and gate["attempt_id"] not in attempts:
            errors.append(
                f"decision gate {gate['decision_gate_id']} references an undeclared attempt"
            )

    return errors


def _validation_errors(document: dict[str, Any]) -> list[str]:
    return _schema_errors(document) + _cross_object_errors(document)


def _set_model_count(document: dict[str, Any], count: int) -> None:
    model_ids = {
        1: ("shared-model", "shared-model", "shared-model"),
        2: ("shared-model", "executor-model", "shared-model"),
        3: ("auditor-model", "executor-model", "evaluator-model"),
    }[count]
    for binding, model_id in zip(document["role_bindings"], model_ids):
        binding["model_id"] = model_id


def test_every_campaign_engine_schema_is_valid_draft_2020_12() -> None:
    assert set(_validators()) == set(SCHEMA_FILES)


def test_valid_campaign_fixture_passes_validation() -> None:
    assert _validation_errors(_fixture("valid_campaign.json")) == []


def test_invalid_model_limit_fixture_is_rejected() -> None:
    errors = _validation_errors(
        _fixture("invalid_role_binding_model_limit.json")
    )
    assert any("uses 4 distinct models; maximum is 3" in error for error in errors)


def test_invalid_runtime_rebinding_fixture_is_rejected() -> None:
    errors = _validation_errors(_fixture("invalid_runtime_rebinding.json"))
    assert any("duplicate binding identity has conflicting" in error for error in errors)


@pytest.mark.parametrize("model_count", [1, 2, 3])
def test_campaign_accepts_one_two_or_three_distinct_models(
    model_count: int,
) -> None:
    document = _fixture("valid_campaign.json")
    _set_model_count(document, model_count)
    assert _validation_errors(document) == []


def test_auditor_and_evaluator_may_share_a_model() -> None:
    document = _fixture("valid_campaign.json")
    bindings = {binding["role"]: binding for binding in document["role_bindings"]}
    assert bindings["auditor"]["model_id"] == bindings["evaluator"]["model_id"]
    assert _validation_errors(document) == []


def test_fourth_distinct_model_is_rejected() -> None:
    errors = _validation_errors(
        _fixture("invalid_role_binding_model_limit.json")
    )
    assert any("uses 4 distinct models" in error for error in errors)


def test_duplicate_binding_identity_with_conflicting_configuration_is_rejected() -> None:
    errors = _validation_errors(_fixture("invalid_runtime_rebinding.json"))
    assert any("provider/model/configuration" in error for error in errors)


def test_attempt_must_reference_a_declared_role_binding() -> None:
    document = deepcopy(_fixture("valid_campaign.json"))
    document["attempts"][0]["role_binding_id"] = "binding-undeclared"
    errors = _validation_errors(document)
    assert any(
        "attempt-executor-001 references an undeclared role binding" in error
        for error in errors
    )


def test_evaluation_must_reference_a_declared_attempt() -> None:
    document = deepcopy(_fixture("valid_campaign.json"))
    document["evaluations"][0]["evaluated_attempt_id"] = "attempt-undeclared"
    errors = _validation_errors(document)
    assert any(
        "evaluation-001 references an undeclared attempt" in error
        for error in errors
    )
