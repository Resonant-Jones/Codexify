"""Provider-free Campaign Engine runtime — the ADR-066 authorized slice.

Implements the smallest deterministic provider-free lifecycle:

    load + validate -> role bindings -> source-selection lineage ->
    one runnable Task -> synthetic Executor Attempt -> synthetic Evaluation
    -> evidence Receipt -> final CampaignState snapshot -> run-result envelope

Every generated entity is a strict `campaign-engine/v0` schema record. The
schemas carry no provider/mutation/lineage fields, so the run-result envelope
carries the additional evidence ADR-066 requires (zero provider calls, zero
source mutations, commit/merge/durable-ingestion flags, lineage references,
and structured acceptance criteria). Receipts remain evidence, not approval.

This module imports only stdlib plus this package. No provider, Pi, Coding
Loop, Guardian, command-bus, subprocess, network, Git, or database dependency
is imported or invoked to run the lifecycle.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .artifacts import ArtifactPublisher, atomic_write_json
from .errors import CampaignArtifactError
from .identity import (
    build_attempt_id,
    build_campaign_state_id,
    build_evaluation_id,
    build_receipt_id,
    build_run_id,
    binding_identity_hash,
    document_hash,
    sha256_canonical,
)
from .models import (
    COMMIT_PERFORMED,
    DECISION_GATES_OPENED_ZERO,
    DURABLE_INGESTION_PERFORMED,
    MERGE_PERFORMED,
    PROVIDER_CALLS_ZERO,
    PROVIDER_FREE_CLASSIFICATION,
    SOURCE_MUTATIONS_ZERO,
    AcceptanceCriterionResult,
    CampaignClock,
    CampaignRunResult,
    SourceContextRecord,
    SystemClock,
    clock_iso,
)
from .validation import (
    cross_object_errors,
    parse_json_strict,
    validate_campaign_document,
    validate_path_component,
    validate_role_binding_semantics,
    validate_source_context,
    validate_task_selection,
)

SCHEMA_VERSION = "campaign-engine/v0"

_LINEAGE_ABSENT_TOKEN = "absent"


def _evaluation_summary(run_id: str) -> str:
    return (
        "Provider-free fixture evaluation: deterministic runtime verification "
        f"passed for run {run_id}. The verdict derives from campaign-engine/v0 "
        "schema validation and cross-object reference validation of the emitted "
        "run; no model was invoked and no independent model judgment is claimed. "
        "Structured acceptance criterion results are recorded in run-result.json."
    )


def run_provider_free_campaign(
    campaign_path: Path,
    output_root: Path,
    *,
    source_context_path: Path | None = None,
    clock: CampaignClock | None = None,
) -> CampaignRunResult:
    """Run the deterministic provider-free Campaign Engine lifecycle.

    Raises bounded :class:`CampaignEngineError` subclasses on any failure and
    publishes artifacts only after full validation. No provider, execution
    seam, network, Git, or database interaction occurs.
    """
    campaign_path = Path(campaign_path)
    output_root = Path(output_root)
    resolved_clock = clock if clock is not None else SystemClock()
    created_at = clock_iso(resolved_clock)

    # 1. Load and validate the campaign document (strict JSON, schemas, cross-object).
    document = parse_json_strict(campaign_path)
    validate_campaign_document(document, str(campaign_path))

    # 2. Role bindings: exactly one active locked binding per role; no rebinding.
    by_role = validate_role_binding_semantics(document)

    # 3. Source-selection lineage (evidence only; never permission).
    source_record: SourceContextRecord | None = None
    if source_context_path is not None:
        source_payload = parse_json_strict(Path(source_context_path))
        source_record = validate_source_context(
            source_payload, str(source_context_path)
        )
        lineage_token = sha256_canonical(source_record.as_artifact())
    else:
        lineage_token = _LINEAGE_ABSENT_TOKEN

    # 4. Exactly one runnable task.
    task = validate_task_selection(document)
    task_id = task["task_id"]
    validate_path_component(task_id, "task_id")
    campaign_id = document["campaign"]["campaign_id"]
    validate_path_component(campaign_id, "campaign_id")

    # 5-9. Deterministic identity (no UUIDs; canonical hashing conventions).
    campaign_input_hash = document_hash(document)
    task_hash = sha256_canonical(task)
    executor_hash = binding_identity_hash(by_role["executor"])
    evaluator_hash = binding_identity_hash(by_role["evaluator"])
    run_id = build_run_id(campaign_id, campaign_input_hash, lineage_token, created_at)
    attempt_id = build_attempt_id(
        run_id, task_id, task_hash, executor_hash, created_at
    )
    evaluation_id = build_evaluation_id(
        run_id, attempt_id, task_id, evaluator_hash, created_at
    )
    receipt_id = build_receipt_id(run_id, campaign_id, created_at)
    campaign_state_id = build_campaign_state_id(run_id, campaign_id, created_at)

    # Generated entities (schema-tight v0 records).
    final_task = {**task, "state": "completed"}
    attempt: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "attempt_id": attempt_id,
        "task_id": task_id,
        "role_binding_id": by_role["executor"]["binding_id"],
        "created_at": created_at,
        "state": "succeeded",
    }
    evaluation: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "evaluation_id": evaluation_id,
        "task_id": task_id,
        "evaluated_attempt_id": attempt_id,
        "evaluator_binding_id": by_role["evaluator"]["binding_id"],
        "created_at": created_at,
        "verdict": "passed",
        "summary": _evaluation_summary(run_id),
    }
    receipt: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "receipt_id": receipt_id,
        "created_at": created_at,
        "subject": {"subject_type": "campaign", "subject_id": campaign_id},
    }
    final_campaign_state: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "campaign_state_id": campaign_state_id,
        "campaign_id": campaign_id,
        "created_at": created_at,
        "state": "completed",
        "ordered_task_ids": [task_id],
        "ordered_role_binding_ids": document["campaign"]["role_binding_ids"],
        "ordered_attempt_ids": [attempt_id],
        "ordered_evaluation_ids": [evaluation_id],
        "ordered_receipt_ids": [receipt_id],
        "ordered_decision_gate_ids": [],
    }
    final_campaign = {**document["campaign"], "state": "completed"}
    final_document: dict[str, Any] = {
        "campaign": final_campaign,
        "tasks": [final_task],
        "role_bindings": document["role_bindings"],
        "attempts": [attempt],
        "evaluations": [evaluation],
        "receipts": [receipt],
        "decision_gates": [],
        "campaign_state": final_campaign_state,
    }

    # Validation before publication: schema + cross-object on the assembled run.
    validate_campaign_document(final_document, "generated provider-free run")
    acceptance_criteria = _build_acceptance_criteria(source_record)

    campaign_state_hash = sha256_canonical(final_campaign_state)
    source_context_hash = (
        sha256_canonical(source_record.as_artifact()) if source_record else None
    )

    result = CampaignRunResult(
        campaign_id=campaign_id,
        run_id=run_id,
        campaign_state_id=campaign_state_id,
        final_campaign_state=final_campaign_state["state"],
        task_id=task_id,
        final_task_state=final_task["state"],
        attempt_id=attempt_id,
        attempt_state=attempt["state"],
        evaluation_id=evaluation_id,
        evaluation_verdict=evaluation["verdict"],
        receipt_id=receipt_id,
        binding_ids_by_role={
            role: binding["binding_id"] for role, binding in by_role.items()
        },
        output_dir=Path(output_root).resolve() / campaign_id,
        classification=PROVIDER_FREE_CLASSIFICATION,
        provider_calls=PROVIDER_CALLS_ZERO,
        source_mutations=SOURCE_MUTATIONS_ZERO,
        decision_gates_opened=DECISION_GATES_OPENED_ZERO,
        commit_performed=COMMIT_PERFORMED,
        merge_performed=MERGE_PERFORMED,
        durable_ingestion_performed=DURABLE_INGESTION_PERFORMED,
        acceptance_criteria=tuple(acceptance_criteria),
        hashes={
            "campaign_input_hash": campaign_input_hash,
            "campaign_state_hash": campaign_state_hash,
            "source_context_hash": source_context_hash or _LINEAGE_ABSENT_TOKEN,
        },
        source_context=_source_context_envelope(source_record, source_context_hash),
        created_at=created_at,
    )

    # Stage, write, verify from disk, and atomically promote.
    publisher = ArtifactPublisher(output_root)
    staging, final_dir = publisher.create_staging(campaign_id, run_id)
    try:
        _write_artifacts(staging, document, final_task, attempt, evaluation,
                         receipt, final_campaign_state, result, source_record)
        _verify_published_artifacts(
            staging,
            document,
            final_task,
            attempt,
            evaluation,
            receipt,
            final_campaign_state,
            result,
            source_record,
        )
        publisher.promote(staging, final_dir)
    except Exception:
        publisher.cleanup(staging)
        raise
    return result


def _build_acceptance_criteria(
    source_record: SourceContextRecord | None,
) -> list[AcceptanceCriterionResult]:
    lineage_basis = (
        "source-selection lineage fixture captured with canonical hash; "
        "lineage is evidence only and grants no execution permission"
        if source_record is not None
        else "no source-context fixture supplied; lineage recorded honestly as absent"
    )
    return [
        AcceptanceCriterionResult(
            criterion="campaign-input-valid",
            result="passed",
            basis="strict JSON parse + campaign-engine/v0 schema validation + "
                  "cross-object reference validation",
        ),
        AcceptanceCriterionResult(
            criterion="role-bindings-locked",
            result="passed",
            basis="exactly one locked binding per role; at most three distinct "
                  "models; no binding created, altered, or rebound during the run",
        ),
        AcceptanceCriterionResult(
            criterion="source-selection-lineage",
            result="passed",
            basis=lineage_basis,
        ),
        AcceptanceCriterionResult(
            criterion="task-lifecycle",
            result="passed",
            basis="exactly one runnable task: ready -> running -> "
                  "awaiting_evaluation -> completed",
        ),
        AcceptanceCriterionResult(
            criterion="provider-free-execution",
            result="passed",
            basis="zero provider calls, zero source mutations, no commit, "
                  "no merge, no durable ingestion, no model invocation",
        ),
        AcceptanceCriterionResult(
            criterion="deterministic-identity",
            result="passed",
            basis="Run/Attempt/Evaluation/Receipt IDs derived from canonical input, "
                  "lineage, and clock via SHA-256; random UUIDs prohibited",
        ),
    ]


def _source_context_envelope(
    source_record: SourceContextRecord | None, source_context_hash: str | None
) -> dict[str, Any]:
    if source_record is None:
        return {
            "present": False,
            "note": "no source-selection lineage fixture was supplied for this run; "
                    "recorded honestly as absent (no ARP fabricated)",
        }
    return {
        "present": True,
        "packet_id": source_record.packet_id,
        "repository_revision": source_record.repository_revision,
        "graph_revision": source_record.graph_revision,
        "authority_profile": source_record.authority_profile,
        "question_or_intent": source_record.question_or_intent,
        "hash": source_context_hash,
        "stale_warnings": list(source_record.stale_warnings),
        "conflicts": list(source_record.conflicts),
        "proof_gaps": list(source_record.proof_gaps),
        "human_decisions_required": list(source_record.human_decisions_required),
    }


def _write_artifacts(
    staging: Path,
    document: dict[str, Any],
    final_task: dict[str, Any],
    attempt: dict[str, Any],
    evaluation: dict[str, Any],
    receipt: dict[str, Any],
    final_campaign_state: dict[str, Any],
    result: CampaignRunResult,
    source_record: SourceContextRecord | None,
) -> None:
    atomic_write_json(staging, "campaign-input.json", document)
    atomic_write_json(
        staging, "bindings.json", {"role_bindings": document["role_bindings"]}
    )
    if source_record is not None:
        atomic_write_json(staging, "source-context.json", source_record.as_artifact())
    atomic_write_json(
        staging / "tasks" / result.task_id, "task-state.json", final_task
    )
    atomic_write_json(staging / "attempts", f"{attempt['attempt_id']}.json", attempt)
    atomic_write_json(
        staging / "evaluations", f"{evaluation['evaluation_id']}.json", evaluation
    )
    atomic_write_json(staging / "receipts", f"{receipt['receipt_id']}.json", receipt)
    atomic_write_json(staging, "campaign-state.json", final_campaign_state)
    atomic_write_json(staging, "run-result.json", result.to_dict())


def _verify_published_artifacts(
    staging: Path,
    document: dict[str, Any],
    final_task: dict[str, Any],
    attempt: dict[str, Any],
    evaluation: dict[str, Any],
    receipt: dict[str, Any],
    final_campaign_state: dict[str, Any],
    result: CampaignRunResult,
    source_record: SourceContextRecord | None,
) -> None:
    """Re-read every written artifact and re-validate before promotion."""

    def read(name: str) -> dict[str, Any]:
        payload = parse_json_strict(staging / name)
        return payload

    # Exact byte-for-record agreement for each generated entity.
    if read("tasks" + f"/{result.task_id}/task-state.json") != final_task:
        raise CampaignArtifactError(
            "written task-state.json differs from generated task"
        )
    if read(f"attempts/{attempt['attempt_id']}.json") != attempt:
        raise CampaignArtifactError("written attempt differs from generated attempt")
    if read(f"evaluations/{evaluation['evaluation_id']}.json") != evaluation:
        raise CampaignArtifactError(
            "written evaluation differs from generated evaluation"
        )
    if read(f"receipts/{receipt['receipt_id']}.json") != receipt:
        raise CampaignArtifactError("written receipt differs from generated receipt")
    if read("campaign-state.json") != final_campaign_state:
        raise CampaignArtifactError(
            "written campaign-state.json differs from generated campaign state"
        )
    if read("campaign-input.json") != document:
        raise CampaignArtifactError("written campaign-input.json differs from input")
    if read("bindings.json") != {"role_bindings": document["role_bindings"]}:
        raise CampaignArtifactError("written bindings.json differs from input bindings")
    if (
        source_record is not None
        and read("source-context.json") != source_record.as_artifact()
    ):
        raise CampaignArtifactError("written source-context.json differs from fixture")
    if read("run-result.json") != result.to_dict():
        raise CampaignArtifactError("written run-result.json differs from result")

    # Schema + cross-object validation over the disk-read entities.
    disk_document = {
        "campaign": {**document["campaign"], "state": "completed"},
        "tasks": [final_task],
        "role_bindings": document["role_bindings"],
        "attempts": [attempt],
        "evaluations": [evaluation],
        "receipts": [receipt],
        "decision_gates": [],
        "campaign_state": final_campaign_state,
    }
    validate_campaign_document(disk_document, "published provider-free run")
    if cross_object_errors(disk_document):
        raise CampaignArtifactError("published artifacts fail cross-object validation")

    # Hash and invariant verification.
    if document_hash(document) != result.hashes["campaign_input_hash"]:
        raise CampaignArtifactError("campaign input hash drifted after write")
    if sha256_canonical(final_campaign_state) != result.hashes["campaign_state_hash"]:
        raise CampaignArtifactError("campaign state hash drifted after write")
    if source_record is not None:
        recomputed = sha256_canonical(source_record.as_artifact())
        if recomputed != result.hashes["source_context_hash"]:
            raise CampaignArtifactError(
                "source-context lineage hash drifted after write"
            )
    if result.provider_calls != 0:
        raise CampaignArtifactError("provider call count is nonzero")
    if result.source_mutations != 0:
        raise CampaignArtifactError("source mutation count is nonzero")
    if result.decision_gates_opened != 0:
        raise CampaignArtifactError("a decision gate is open")
    if (
        result.commit_performed
        or result.merge_performed
        or result.durable_ingestion_performed
    ):
        raise CampaignArtifactError("commit/merge/durable-ingestion claim became true")
