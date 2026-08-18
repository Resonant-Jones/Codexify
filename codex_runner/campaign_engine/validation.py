"""Strict loading and validation for the provider-free Campaign Engine runtime.

Responsibilities:

- strict JSON parsing (duplicate keys rejected);
- per-entity Draft 2020-12 validation against the existing
  `codex_runner/schemas/campaign_engine/*.schema.json` files (schemas are
  NEVER modified by this package);
- cross-object validation replicating the rules enforced by
  `codex_runner/tests/test_campaign_engine_schemas.py`;
- role-binding, task-selection, source-context, and path-component checks.

`jsonschema` is imported lazily inside the functions that need it so that
importing this package performs no dependency resolution beyond stdlib.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .errors import (
    CampaignSourceContextError,
    CampaignTaskSelectionError,
    CampaignValidationError,
    format_issues,
)
from .models import SourceContextRecord

SCHEMA_DIR = Path(__file__).resolve().parents[1] / "schemas" / "campaign_engine"

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

CAMPAIGN_ROLES = ("auditor", "executor", "evaluator")

AUTHORITY_PROFILES = (
    "release_and_support",
    "architecture_decision",
    "implementation_behavior",
    "ui_and_design",
    "historical_and_provenance",
)

SAFE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")

TOP_LEVEL_KEYS = (
    "campaign",
    "tasks",
    "role_bindings",
    "attempts",
    "evaluations",
    "receipts",
    "decision_gates",
    "campaign_state",
)


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate object key: {key!r}")
        result[key] = value
    return result


def parse_json_strict(path: Path) -> dict[str, Any]:
    """Parse a UTF-8 JSON object strictly (duplicate keys rejected)."""
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise CampaignValidationError(f"campaign file not found: {path}") from exc
    except UnicodeDecodeError as exc:
        raise CampaignValidationError(
            f"campaign file must be UTF-8 text: {path}"
        ) from exc
    try:
        payload = json.loads(raw, object_pairs_hook=_reject_duplicate_keys)
    except ValueError as exc:
        raise CampaignValidationError(
            f"invalid campaign JSON in {path}: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise CampaignValidationError(f"expected a JSON object at {path}")
    return payload


def _validator_for(entity: str):
    from jsonschema import Draft202012Validator, FormatChecker  # lazy import

    schema = json.loads((SCHEMA_DIR / SCHEMA_FILES[entity]).read_text(encoding="utf-8"))
    return Draft202012Validator(schema, format_checker=FormatChecker())


def validate_entity(entity: str, payload: dict[str, Any], label: str) -> list[str]:
    """Return schema errors for one Campaign Engine entity (empty when valid)."""
    validator = _validator_for(entity)
    return [
        f"{label}: {error.message}"
        for error in sorted(
            validator.iter_errors(payload), key=lambda item: list(item.path)
        )
    ]


def _indexed(items: list[dict[str, Any]], id_field: str) -> dict[str, dict[str, Any]]:
    return {item[id_field]: item for item in items}


def cross_object_errors(document: dict[str, Any]) -> list[str]:
    """Replicate the repository's cross-object validation rules.

    Mirrors the rules enforced by
    `codex_runner/tests/test_campaign_engine_schemas.py::_cross_object_errors`.
    """
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
        errors.append("campaign role_binding_ids must match declared binding order")

    for task in tasks.values():
        if task["campaign_id"] != campaign["campaign_id"]:
            errors.append(f"task {task['task_id']} belongs to another campaign")

    referenced_bindings = [
        bindings[binding_id]
        for binding_id in campaign["role_binding_ids"]
        if binding_id in bindings
    ]
    roles = {binding["role"] for binding in referenced_bindings}
    required_roles = set(CAMPAIGN_ROLES)
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
        if (
            subject_type != "action"
            and subject["subject_id"] not in subject_indexes[subject_type]
        ):
            errors.append(
                f"receipt {receipt['receipt_id']} references an undeclared subject"
            )

    for gate in decision_gates.values():
        if gate["campaign_id"] != campaign["campaign_id"]:
            errors.append(
                f"decision gate {gate['decision_gate_id']} belongs to "
                "another campaign"
            )
        if "task_id" in gate and gate["task_id"] not in tasks:
            errors.append(
                f"decision gate {gate['decision_gate_id']} references an "
                "undeclared task"
            )
        if "attempt_id" in gate and gate["attempt_id"] not in attempts:
            errors.append(
                f"decision gate {gate['decision_gate_id']} references an "
                "undeclared attempt"
            )

    return errors


def validate_campaign_document(document: dict[str, Any], source: str) -> None:
    """Schema-validate each entity and cross-validate the document; raise on failure."""
    issues: list[str] = []
    missing = [key for key in TOP_LEVEL_KEYS if key not in document]
    if missing:
        issues.append(f"missing top-level document key(s): {', '.join(missing)}")

    issues.extend(validate_entity("campaign", document.get("campaign", {}), "campaign"))
    issues.extend(
        validate_entity(
            "campaign_state", document.get("campaign_state", {}), "campaign_state"
        )
    )
    for collection, schema_name in COLLECTION_SCHEMAS.items():
        for index, entity in enumerate(document.get(collection, [])):
            issues.extend(
                validate_entity(schema_name, entity, f"{collection}[{index}]")
            )

    if not missing:
        issues.extend(cross_object_errors(document))

    if issues:
        raise CampaignValidationError(
            f"campaign document validation failed for {source}: "
            f"{format_issues(issues)}",
            issues=issues,
        )


def validate_role_binding_semantics(
    document: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Return role -> binding for the campaign bindings; raise on violation."""
    campaign = document["campaign"]
    bindings = {binding["binding_id"]: binding for binding in document["role_bindings"]}
    by_role: dict[str, dict[str, Any]] = {}
    for binding_id in campaign["role_binding_ids"]:
        binding = bindings[binding_id]
        by_role.setdefault(binding["role"], binding)

    for role in CAMPAIGN_ROLES:
        if role not in by_role:
            raise CampaignValidationError(f"campaign declares no {role!r} role binding")
    counts = {role: 0 for role in CAMPAIGN_ROLES}
    for binding_id in campaign["role_binding_ids"]:
        counts[bindings[binding_id]["role"]] += 1
    for role, count in counts.items():
        if count != 1:
            raise CampaignValidationError(
                f"campaign must declare exactly one active {role!r} "
                f"binding; found {count}"
            )
    for binding in by_role.values():
        if binding["binding_state"] != "locked":
            raise CampaignValidationError(
                f"role binding {binding['binding_id']} is not locked "
                f"(state={binding['binding_state']!r})"
            )
    return by_role


def validate_task_selection(document: dict[str, Any]) -> dict[str, Any]:
    """Require exactly one runnable task in pending/ready state."""
    tasks = document["tasks"]
    if not tasks:
        raise CampaignTaskSelectionError("campaign declares zero tasks")
    if len(tasks) != 1:
        raise CampaignTaskSelectionError(
            f"this slice requires exactly one task; campaign declares {len(tasks)}"
        )
    task = tasks[0]
    if task["state"] not in ("pending", "ready"):
        raise CampaignTaskSelectionError(
            f"task {task['task_id']} is not runnable (state={task['state']!r}); "
            "accepted initial states: pending, ready"
        )
    return task


def validate_path_component(value: str, label: str) -> None:
    """Reject path-unsafe identity values before they become path components."""
    if not isinstance(value, str) or not SAFE_ID_RE.match(value) or ".." in value:
        raise CampaignValidationError(
            f"{label} {value!r} is not a safe path component "
            "(allowed: 1-128 chars of [A-Za-z0-9._-], no leading dot, no '..')"
        )


def validate_source_context(
    payload: dict[str, Any], source: str
) -> SourceContextRecord:
    """Validate the minimum lineage shape ADR-066 requires; preserve the rest.

    This is NOT full Agent Reading Packet validation: the runtime does not
    implement the DLG resolver and must not interpret lineage as permission.
    """
    required = ("packet_id", "repository_revision", "graph_revision",
                "authority_profile", "question_or_intent")
    missing = [key for key in required if key not in payload]
    if missing:
        raise CampaignSourceContextError(
            f"source-context fixture {source} missing required lineage field(s): "
            f"{', '.join(missing)}"
        )
    for key in required:
        if not isinstance(payload[key], str) or not payload[key]:
            raise CampaignSourceContextError(
                f"source-context fixture {source}: {key!r} must be a non-empty string"
            )
    if not GIT_SHA_RE.match(payload["repository_revision"]):
        raise CampaignSourceContextError(
            f"source-context fixture {source}: repository_revision must be a "
            "lowercase 40-character Git SHA"
        )
    if not SHA256_HEX_RE.match(payload["graph_revision"]):
        raise CampaignSourceContextError(
            f"source-context fixture {source}: graph_revision must be a "
            "lowercase 64-character SHA-256 hex digest"
        )
    if payload["authority_profile"] not in AUTHORITY_PROFILES:
        raise CampaignSourceContextError(
            f"source-context fixture {source}: unknown authority_profile "
            f"{payload['authority_profile']!r}"
        )
    for optional_list in ("stale_warnings", "conflicts", "proof_gaps",
                          "human_decisions_required"):
        if optional_list in payload and not isinstance(payload[optional_list], list):
            raise CampaignSourceContextError(
                f"source-context fixture {source}: {optional_list!r} must be an array "
                "when present"
            )
    created_at = payload.get("created_at")
    if created_at is not None and not isinstance(created_at, str):
        raise CampaignSourceContextError(
            f"source-context fixture {source}: created_at must be a string when present"
        )
    return SourceContextRecord(
        packet_id=payload["packet_id"],
        repository_revision=payload["repository_revision"],
        graph_revision=payload["graph_revision"],
        authority_profile=payload["authority_profile"],
        question_or_intent=payload["question_or_intent"],
        created_at=created_at,
        stale_warnings=tuple(payload.get("stale_warnings", [])),
        conflicts=tuple(payload.get("conflicts", [])),
        proof_gaps=tuple(payload.get("proof_gaps", [])),
        human_decisions_required=tuple(payload.get("human_decisions_required", [])),
        raw=payload,
    )
