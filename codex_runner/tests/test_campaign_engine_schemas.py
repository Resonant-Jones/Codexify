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




def _validate_single_entity(entity: str, payload: dict, label: str) -> list:
    """Validate one Campaign Engine entity using the existing schema validator."""
    schema_name = {
        "attempt": "attempt",
        "evaluation": "evaluation",
        "receipt": "receipt",
        "role_binding": "role_binding",
    }[entity]
    from jsonschema import Draft202012Validator, FormatChecker
    schema = _read_json(SCHEMA_ROOT / {
        "attempt": "attempt.schema.json",
        "evaluation": "evaluation.schema.json",
        "receipt": "receipt.schema.json",
        "role_binding": "role_binding.schema.json",
    }[entity])
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    return [
        f"{label}: {error.message}"
        for error in sorted(validator.iter_errors(payload), key=lambda item: list(item.path))
    ]


# ---------------------------------------------------------------------------
# ADR-067 live-role-execution schema proofs.
# ---------------------------------------------------------------------------


def _load_live_role_campaign() -> dict:
    return _fixture("live_role_execution_campaign.json")


def _load_valid_live_attempt() -> dict:
    return _fixture("valid_live_attempt.json")


def _load_valid_live_evaluation() -> dict:
    return _fixture("valid_live_evaluation.json")


def _load_valid_live_receipt() -> dict:
    return _fixture("valid_live_receipt.json")


# 1. existing provider-free RoleBinding fixtures remain valid.
def test_existing_provider_free_role_binding_fixtures_remain_valid() -> None:
    assert _validation_errors(_fixture("valid_campaign.json")) == []


# 2. valid live RoleBinding shape is accepted.
def test_valid_live_role_binding_shape_is_accepted() -> None:
    document = _load_live_role_campaign()
    binding = next(
        binding
        for binding in document["role_bindings"]
        if binding["binding_id"] == "binding-executor-live-001"
    )
    assert _validate_single_entity(
        "role_binding", binding, "role_binding"
    ) == []


# 4. valid live Executor Attempt is accepted.
def test_valid_live_executor_attempt_is_accepted() -> None:
    assert _validate_single_entity("attempt", _load_valid_live_attempt(), "attempt") == []


# 5. live Attempt requires authorization/envelope reference.
def test_live_attempt_requires_authorization_reference() -> None:
    payload = _load_valid_live_attempt()
    del payload["invocation_authorization_reference"]
    errors = _validate_single_entity("attempt", payload, "attempt")
    assert any("invocation_authorization_reference" in error for error in errors)


# 6. live Attempt requires permission reference.
def test_live_attempt_requires_permission_reference() -> None:
    payload = _load_valid_live_attempt()
    del payload["permission_resolution_reference"]
    errors = _validate_single_entity("attempt", payload, "attempt")
    assert any("permission_resolution_reference" in error for error in errors)


# 7. live Attempt requires expected provider/model identity.
def test_live_attempt_requires_expected_provider_and_model() -> None:
    payload = _load_valid_live_attempt()
    del payload["expected_provider_id"]
    del payload["expected_model_id"]
    errors = _validate_single_entity("attempt", payload, "attempt")
    assert any("expected_provider_id" in error for error in errors)
    assert any("expected_model_id" in error for error in errors)


# 8. live Attempt requires actual provider/model identity.
def test_live_attempt_requires_actual_provider_and_model() -> None:
    payload = _load_valid_live_attempt()
    del payload["actual_provider_id"]
    del payload["actual_model_id"]
    errors = _validate_single_entity("attempt", payload, "attempt")
    assert any("actual_provider_id" in error for error in errors)
    assert any("actual_model_id" in error for error in errors)


# 9. live Attempt requires explicit identity-verification result.
def test_live_attempt_requires_identity_verification_result() -> None:
    payload = _load_valid_live_attempt()
    del payload["identity_verification_result"]
    errors = _validate_single_entity("attempt", payload, "attempt")
    assert any("identity_verification_result" in error for error in errors)


# 10. live Attempt requires provider/harness receipt reference.
def test_live_attempt_requires_provider_harness_receipt_reference() -> None:
    payload = _load_valid_live_attempt()
    del payload["provider_harness_receipt_reference"]
    errors = _validate_single_entity("attempt", payload, "attempt")
    assert any("provider_harness_receipt_reference" in error for error in errors)


# 11. live mutation Attempt requires bounded changed-file evidence.
def test_live_mutation_attempt_requires_changed_files() -> None:
    payload = _load_valid_live_attempt()
    payload["source_mutation_count"] = 3
    del payload["changed_files"]
    errors = _validate_single_entity("attempt", payload, "attempt")
    assert any("changed_files" in error for error in errors)


# 13a. live Attempt rejects commit_performed true.
def test_live_attempt_commit_true_is_rejected() -> None:
    payload = _load_valid_live_attempt()
    payload["commit_performed"] = True
    errors = _validate_single_entity("attempt", payload, "attempt")
    assert any("commit_performed" in error or "False was expected" in error for error in errors)


# 13b. live Attempt rejects merge_performed true.
def test_live_attempt_merge_true_is_rejected() -> None:
    payload = _load_valid_live_attempt()
    payload["merge_performed"] = True
    errors = _validate_single_entity("attempt", payload, "attempt")
    assert any("merge_performed" in error or "False was expected" in error for error in errors)


# 13c. live Attempt rejects durable_ingestion_performed true.
def test_live_attempt_durable_ingestion_true_is_rejected() -> None:
    payload = _load_valid_live_attempt()
    payload["durable_ingestion_performed"] = True
    errors = _validate_single_entity("attempt", payload, "attempt")
    # Draft 2020-12 emits 'False was expected' without the field name in the
    # message text; the field name lives in absolute_path. Accept either.
    assert any(
        "false was expected" in error.lower() for error in errors
    )


# 14. valid live Evaluation is accepted.
def test_valid_live_evaluation_is_accepted() -> None:
    assert _validate_single_entity("evaluation", _load_valid_live_evaluation(), "evaluation") == []


# 15. live Evaluation requires Evaluator binding and evaluated Attempt.
def test_live_evaluation_requires_evaluator_binding_and_evaluated_attempt() -> None:
    payload = _load_valid_live_evaluation()
    del payload["evaluator_binding_id"]
    del payload["evaluated_attempt_id"]
    errors = _validate_single_entity("evaluation", payload, "evaluation")
    assert any("evaluator_binding_id" in error for error in errors)
    assert any("evaluated_attempt_id" in error for error in errors)


# 16. live Evaluation requires expected and actual identity.
def test_live_evaluation_requires_expected_and_actual_identity() -> None:
    payload = _load_valid_live_evaluation()
    del payload["expected_provider_id"]
    del payload["actual_provider_id"]
    del payload["expected_model_id"]
    del payload["actual_model_id"]
    errors = _validate_single_entity("evaluation", payload, "evaluation")
    assert any("expected_provider_id" in error for error in errors)
    assert any("actual_provider_id" in error for error in errors)
    assert any("expected_model_id" in error for error in errors)
    assert any("actual_model_id" in error for error in errors)


# 17. live Evaluation requires identity verification.
def test_live_evaluation_requires_identity_verification() -> None:
    payload = _load_valid_live_evaluation()
    del payload["identity_verification_result"]
    errors = _validate_single_entity("evaluation", payload, "evaluation")
    assert any("identity_verification_result" in error for error in errors)


# 18. live Evaluation requires read-only assertion.
def test_live_evaluation_requires_read_only_assertion() -> None:
    payload = _load_valid_live_evaluation()
    payload["read_only_assertion"] = False
    errors = _validate_single_entity("evaluation", payload, "evaluation")
    assert any("read_only_assertion" in error or "True was expected" in error for error in errors)


# 19. live Evaluation rejects mutation_performed true.
def test_live_evaluation_rejects_mutation_performed_true() -> None:
    payload = _load_valid_live_evaluation()
    payload["mutation_performed"] = True
    errors = _validate_single_entity("evaluation", payload, "evaluation")
    assert any("mutation_performed" in error or "False was expected" in error for error in errors)


# 20. live Evaluation requires independent-model-judgment true.
def test_live_evaluation_requires_independent_model_judgment_true() -> None:
    payload = _load_valid_live_evaluation()
    payload["independent_model_judgment"] = False
    errors = _validate_single_entity("evaluation", payload, "evaluation")
    # Draft 2020-12 emits 'True was expected' without the field name in the
    # message text; the field name lives in absolute_path. Accept either.
    assert any(
        "true was expected" in error.lower() for error in errors
    )


# 21. provider-free Evaluation continues to require non-independent-judgment.
def test_provider_free_evaluation_continues_non_independent_judgment() -> None:
    base = _load_valid_live_evaluation()
    base["evaluation_mode"] = "provider_free"
    base["independent_model_judgment"] = False
    for key in (
        "invocation_authorization_reference", "permission_resolution_reference",
        "expected_provider_id", "expected_model_id",
        "actual_provider_id", "actual_model_id",
        "identity_verification_result", "provider_harness_receipt_reference",
        "structured_acceptance_results", "read_only_assertion",
        "mutation_performed", "secret_redaction_status",
    ):
        base.pop(key, None)
    assert _validate_single_entity("evaluation", base, "evaluation") == []


# 22. live Evaluation requires structured acceptance criteria.
def test_live_evaluation_requires_structured_acceptance_results() -> None:
    payload = _load_valid_live_evaluation()
    del payload["structured_acceptance_results"]
    errors = _validate_single_entity("evaluation", payload, "evaluation")
    assert any("structured_acceptance_results" in error for error in errors)


# 23. valid live Receipt is accepted.
def test_valid_live_receipt_is_accepted() -> None:
    assert _validate_single_entity("receipt", _load_valid_live_receipt(), "receipt") == []


# 24. live Receipt requires both role bindings and actual identities.
def test_live_receipt_requires_role_bindings_and_actual_identities() -> None:
    payload = _load_valid_live_receipt()
    del payload["executor_role_binding_id"]
    del payload["evaluator_role_binding_id"]
    del payload["actual_executor_provider_id"]
    del payload["actual_executor_model_id"]
    del payload["actual_evaluator_provider_id"]
    del payload["actual_evaluator_model_id"]
    errors = _validate_single_entity("receipt", payload, "receipt")
    assert any("executor_role_binding_id" in error for error in errors)
    assert any("evaluator_role_binding_id" in error for error in errors)
    assert any("actual_executor_provider_id" in error for error in errors)
    assert any("actual_executor_model_id" in error for error in errors)
    assert any("actual_evaluator_provider_id" in error for error in errors)
    assert any("actual_evaluator_model_id" in error for error in errors)


# 25. live Receipt requires provider/harness receipt references.
def test_live_receipt_requires_provider_harness_receipts() -> None:
    payload = _load_valid_live_receipt()
    del payload["executor_invocation_receipt_reference"]
    del payload["evaluator_invocation_receipt_reference"]
    errors = _validate_single_entity("receipt", payload, "receipt")
    assert any("executor_invocation_receipt_reference" in error for error in errors)
    assert any("evaluator_invocation_receipt_reference" in error for error in errors)


# 26. live Receipt requires source-context lineage reference/hash.
def test_live_receipt_requires_source_context_lineage() -> None:
    payload = _load_valid_live_receipt()
    del payload["source_context_reference"]
    del payload["source_context_hash"]
    errors = _validate_single_entity("receipt", payload, "receipt")
    assert any("source_context_reference" in error for error in errors)
    assert any("source_context_hash" in error for error in errors)


# 27. live Receipt requires identity-verification results.
def test_live_receipt_requires_identity_verification_results() -> None:
    payload = _load_valid_live_receipt()
    del payload["executor_identity_verification_result"]
    del payload["evaluator_identity_verification_result"]
    errors = _validate_single_entity("receipt", payload, "receipt")
    assert any("executor_identity_verification_result" in error for error in errors)
    assert any("evaluator_identity_verification_result" in error for error in errors)


# 28. live Receipt requires redaction status.
def test_live_receipt_requires_redaction_status() -> None:
    payload = _load_valid_live_receipt()
    del payload["redaction_result"]
    errors = _validate_single_entity("receipt", payload, "receipt")
    assert any("redaction_result" in error for error in errors)


# 29. live Receipt rejects rebinding_performed true.
def test_live_receipt_rejects_rebinding_true() -> None:
    payload = _load_valid_live_receipt()
    payload["rebinding_performed"] = True
    errors = _validate_single_entity("receipt", payload, "receipt")
    assert any("rebinding_performed" in error or "False was expected" in error for error in errors)


# 30. live Receipt requires final verdict.
def test_live_receipt_requires_final_verdict() -> None:
    payload = _load_valid_live_receipt()
    del payload["final_verdict"]
    errors = _validate_single_entity("receipt", payload, "receipt")
    assert any("final_verdict" in error for error in errors)


# 31. existing provider-free runtime fixture remains valid.
def test_existing_provider_free_runtime_fixture_remains_valid() -> None:
    runtime_fixture = FIXTURE_ROOT.parent.parent.parent / "tests" / "fixtures" / "campaign_engine" / "provider_free_runtime_campaign.json"
    document = _read_json(runtime_fixture)
    assert _validation_errors(document) == []


# 32. existing provider-free runtime records remain valid.
def test_existing_provider_free_runtime_records_remain_valid() -> None:
    runtime_fixture = FIXTURE_ROOT.parent.parent.parent / "tests" / "fixtures" / "campaign_engine" / "provider_free_runtime_campaign.json"
    document = _read_json(runtime_fixture)
    minimal_attempt = {
        "schema_version": "campaign-engine/v0",
        "attempt_id": "attempt-pf-regression-001",
        "task_id": document["tasks"][0]["task_id"],
        "role_binding_id": document["role_bindings"][0]["binding_id"],
        "created_at": "2026-08-14T13:00:00Z",
        "state": "succeeded",
    }
    minimal_evaluation = {
        "schema_version": "campaign-engine/v0",
        "evaluation_id": "evaluation-pf-regression-001",
        "task_id": document["tasks"][0]["task_id"],
        "evaluated_attempt_id": "attempt-pf-regression-001",
        "evaluator_binding_id": document["role_bindings"][2]["binding_id"],
        "created_at": "2026-08-14T13:00:00Z",
        "verdict": "passed",
        "summary": "Provider-free regression check passes.",
    }
    minimal_receipt = {
        "schema_version": "campaign-engine/v0",
        "receipt_id": "receipt-pf-regression-001",
        "created_at": "2026-08-14T13:00:00Z",
        "subject": {"subject_type": "campaign", "subject_id": document["campaign"]["campaign_id"]},
    }
    assert _validate_single_entity("attempt", minimal_attempt, "attempt") == []
    assert _validate_single_entity("evaluation", minimal_evaluation, "evaluation") == []
    assert _validate_single_entity("receipt", minimal_receipt, "receipt") == []


# 33. existing invalid Campaign Engine fixtures remain invalid.
def test_existing_invalid_fixtures_remain_invalid() -> None:
    document = _fixture("valid_campaign.json")
    document["role_bindings"][0]["binding_state"] = "draft"
    errors = _validation_errors(document)
    assert any("locked" in error for error in errors)
