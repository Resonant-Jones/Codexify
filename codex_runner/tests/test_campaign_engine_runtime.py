"""Focused tests for the provider-free Campaign Engine runtime (ADR-066 slice).

Covers the 48 required proof points: deterministic completion, locked role
bindings, source-selection lineage, schema-valid artifacts, deterministic
identity, path/output safety, rerun determinism, CLI behavior, and loud
failure if any prohibited execution seam (Pi, Coding Loop, Guardian, command
bus, provider adapter, subprocess model, network, Git, database) is touched.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from codex_runner.campaign_engine import (  # noqa: E402
    CampaignArtifactError,
    CampaignOutputExistsError,
    CampaignValidationError,
    FixedClock,
    run_provider_free_campaign,
)
from codex_runner.campaign_engine import runtime as runtime_module  # noqa: E402
from codex_runner.campaign_engine import validation as validation_module  # noqa: E402

FIXTURE_DIR = REPO_ROOT / "codex_runner" / "tests" / "fixtures" / "campaign_engine"
CAMPAIGN_FIXTURE = FIXTURE_DIR / "provider_free_runtime_campaign.json"
SOURCE_CONTEXT_FIXTURE = FIXTURE_DIR / "provider_free_runtime_source_context.json"

FIXED_CLOCK = FixedClock(datetime(2026, 8, 14, 12, 0, 0, tzinfo=timezone.utc))


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def campaign_document() -> dict:
    return load_json(CAMPAIGN_FIXTURE)


def source_context_record() -> dict:
    return load_json(SOURCE_CONTEXT_FIXTURE)


def write_variant(tmp_path: Path, name: str, document: dict) -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    return path


def write_source_variant(tmp_path: Path, name: str, record: dict) -> Path:
    return write_variant(tmp_path, name, record)


def _append_fourth_binding(document: dict) -> None:
    """Append a fourth, locked binding with a fourth distinct model identity."""
    fourth = copy.deepcopy(document["role_bindings"][0])
    fourth.update(
        {
            "binding_id": "binding-auditor-pf-004",
            "model_id": "m-fourth-model",
            "configuration_hash": "sha256:"
            + "d" * 64,
        }
    )
    document["role_bindings"].append(fourth)
    document["campaign"]["role_binding_ids"].append(fourth["binding_id"])
    document["campaign_state"]["ordered_role_binding_ids"].append(
        fourth["binding_id"]
    )


_output_counter = {"value": 0}


def fresh_output_root(tmp_path: Path, name: str | None = None) -> Path:
    if name is None:
        name = f"out-{_output_counter['value']}"
        _output_counter["value"] += 1
    root = tmp_path / name
    root.mkdir()
    return root


def run_ok(
    output_root: Path,
    *,
    source_context: Path | None = None,
    clock: FixedClock = FIXED_CLOCK,
    campaign: Path = CAMPAIGN_FIXTURE,
):
    return run_provider_free_campaign(
        campaign, output_root, source_context_path=source_context, clock=clock
    )


def artifact_files(output_root: Path) -> dict[str, Path]:
    return {
        str(path.relative_to(output_root)): path
        for path in sorted(output_root.rglob("*"))
        if path.is_file()
    }


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run_snapshot(output_root: Path) -> dict[str, str]:
    return {
        relative: sha256_bytes(path.read_bytes())
        for relative, path in artifact_files(output_root).items()
    }


def assert_no_promoted_tree(output_root: Path, campaign_id: str) -> None:
    assert not (output_root / campaign_id).exists()
    assert not any(
        entry.name.startswith(".staging-") for entry in output_root.iterdir()
    )


class ExplodingModule:
    """Attribute access to any prohibited seam raises immediately."""

    def __getattr__(self, name: str):
        raise AssertionError(f"prohibited seam module was touched: {name}")


def patch_seam_modules(monkeypatch: pytest.MonkeyPatch, names: list[str]) -> None:
    for name in names:
        monkeypatch.setitem(sys.modules, name, ExplodingModule())


def assert_seam_untouched(
    monkeypatch: pytest.MonkeyPatch,
    names: list[str],
    tmp_path: Path,
    *,
    source_context: Path | None = SOURCE_CONTEXT_FIXTURE,
) -> None:
    """Run the full lifecycle while the named seams explode on access."""
    patch_seam_modules(monkeypatch, names)
    monkeypatch.setattr(subprocess, "run", _forbidden("subprocess.run"))
    monkeypatch.setattr(subprocess, "Popen", _forbidden("subprocess.Popen"))
    monkeypatch.setattr(os, "system", _forbidden("os.system"))
    monkeypatch.setattr(socket, "socket", _forbidden("socket.socket"))
    monkeypatch.setattr(socket, "create_connection", _forbidden("socket.create_connection"))
    result = run_ok(fresh_output_root(tmp_path, "seam"), source_context=source_context)
    assert result.provider_calls == 0
    assert result.source_mutations == 0


def _forbidden(label: str):
    def explode(*args, **kwargs):
        raise AssertionError(f"prohibited seam invoked: {label}")

    return explode


def _clean_env() -> dict[str, str]:
    return {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}


def run_cli(*args: str, cwd: Path = REPO_ROOT) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "codex_runner.campaign_engine.cli", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        env=_clean_env(),
    )


# ---------------------------------------------------------------------------
# Completion and final states
# ---------------------------------------------------------------------------


def test_valid_provider_free_campaign_completes(tmp_path: Path) -> None:
    result = run_ok(fresh_output_root(tmp_path))
    assert result.classification == "provider_free"
    assert result.final_campaign_state == "completed"
    assert result.final_task_state == "completed"
    assert result.attempt_state == "succeeded"
    assert result.evaluation_verdict == "passed"


def test_final_campaign_state_is_completed(tmp_path: Path) -> None:
    result = run_ok(fresh_output_root(tmp_path))
    state = load_json(result.output_dir / "campaign-state.json")
    assert state["state"] == "completed"
    assert state["campaign_id"] == result.campaign_id


def test_final_task_state_is_completed(tmp_path: Path) -> None:
    result = run_ok(fresh_output_root(tmp_path))
    task = load_json(result.output_dir / "tasks" / result.task_id / "task-state.json")
    assert task["state"] == "completed"
    assert task["task_id"] == result.task_id


def test_exactly_one_synthetic_attempt(tmp_path: Path) -> None:
    result = run_ok(fresh_output_root(tmp_path))
    attempts = list((result.output_dir / "attempts").iterdir())
    assert len(attempts) == 1
    assert attempts[0].name == f"{result.attempt_id}.json"


def test_exactly_one_evaluation(tmp_path: Path) -> None:
    result = run_ok(fresh_output_root(tmp_path))
    evaluations = list((result.output_dir / "evaluations").iterdir())
    assert len(evaluations) == 1
    assert evaluations[0].name == f"{result.evaluation_id}.json"


def test_exactly_one_receipt(tmp_path: Path) -> None:
    result = run_ok(fresh_output_root(tmp_path))
    receipts = list((result.output_dir / "receipts").iterdir())
    assert len(receipts) == 1
    assert receipts[0].name == f"{result.receipt_id}.json"


def test_generated_entities_validate_against_schemas(tmp_path: Path) -> None:
    result = run_ok(fresh_output_root(tmp_path), source_context=SOURCE_CONTEXT_FIXTURE)
    out = result.output_dir

    assert validation_module.validate_entity(
        "task", load_json(out / "tasks" / result.task_id / "task-state.json"), "task"
    ) == []
    assert validation_module.validate_entity(
        "attempt", load_json(out / "attempts" / f"{result.attempt_id}.json"), "attempt"
    ) == []
    assert validation_module.validate_entity(
        "evaluation",
        load_json(out / "evaluations" / f"{result.evaluation_id}.json"),
        "evaluation",
    ) == []
    assert validation_module.validate_entity(
        "receipt", load_json(out / "receipts" / f"{result.receipt_id}.json"), "receipt"
    ) == []
    assert validation_module.validate_entity(
        "campaign_state", load_json(out / "campaign-state.json"), "campaign_state"
    ) == []
    bindings = load_json(out / "bindings.json")["role_bindings"]
    for binding in bindings:
        assert validation_module.validate_entity(
            "role_binding", binding, "role_binding"
        ) == []
    validation_module.validate_campaign_document(
        load_json(out / "campaign-input.json"), "campaign-input artifact"
    )


def test_all_required_artifacts_exist(tmp_path: Path) -> None:
    result = run_ok(fresh_output_root(tmp_path))
    files = set(artifact_files(result.output_dir))
    expected = {
        "campaign-input.json",
        "bindings.json",
        f"tasks/{result.task_id}/task-state.json",
        f"attempts/{result.attempt_id}.json",
        f"evaluations/{result.evaluation_id}.json",
        f"receipts/{result.receipt_id}.json",
        "campaign-state.json",
        "run-result.json",
    }
    assert files == expected


# ---------------------------------------------------------------------------
# Role bindings
# ---------------------------------------------------------------------------


def test_bindings_remain_locked_and_semantically_unchanged(tmp_path: Path) -> None:
    document = campaign_document()
    result = run_ok(fresh_output_root(tmp_path))
    written = load_json(result.output_dir / "bindings.json")["role_bindings"]
    assert written == document["role_bindings"]
    for binding in written:
        assert binding["binding_state"] == "locked"


def test_auditor_and_evaluator_share_one_model() -> None:
    document = campaign_document()
    models = {
        binding["role"]: binding["model_id"]
        for binding in document["role_bindings"]
    }
    assert models["auditor"] == models["evaluator"]


def test_executor_uses_second_model() -> None:
    document = campaign_document()
    models = {
        binding["role"]: binding["model_id"]
        for binding in document["role_bindings"]
    }
    assert models["executor"] != models["auditor"]


@pytest.mark.parametrize("model_count", [1, 2, 3])
def test_one_two_three_model_configurations_valid(
    tmp_path: Path, model_count: int
) -> None:
    document = campaign_document()
    model_ids = {
        1: ("shared-model", "shared-model", "shared-model"),
        2: ("shared-model", "executor-model", "shared-model"),
        3: ("auditor-model", "executor-model", "evaluator-model"),
    }[model_count]
    for binding, model_id in zip(document["role_bindings"], model_ids):
        binding["model_id"] = model_id
    campaign_path = write_variant(tmp_path, "campaign.json", document)
    result = run_ok(fresh_output_root(tmp_path), campaign=campaign_path)
    assert result.final_campaign_state == "completed"


def test_fourth_distinct_model_fails_before_publication(tmp_path: Path) -> None:
    document = campaign_document()
    model_ids = ("m-auditor", "m-executor", "m-evaluator")
    for binding, model_id in zip(document["role_bindings"], model_ids):
        binding["model_id"] = model_id
    _append_fourth_binding(document)
    campaign_path = write_variant(tmp_path, "campaign.json", document)
    output_root = fresh_output_root(tmp_path)
    with pytest.raises(CampaignValidationError, match="distinct models"):
        run_ok(output_root, campaign=campaign_path)
    assert_no_promoted_tree(output_root, document["campaign"]["campaign_id"])


def test_unlocked_binding_fails_before_publication(tmp_path: Path) -> None:
    document = campaign_document()
    document["role_bindings"][1]["binding_state"] = "draft"
    campaign_path = write_variant(tmp_path, "campaign.json", document)
    output_root = fresh_output_root(tmp_path)
    with pytest.raises(CampaignValidationError, match="locked"):
        run_ok(output_root, campaign=campaign_path)
    assert_no_promoted_tree(output_root, document["campaign"]["campaign_id"])


def test_conflicting_duplicate_binding_identity_fails(tmp_path: Path) -> None:
    document = campaign_document()
    duplicate = copy.deepcopy(document["role_bindings"][1])
    duplicate["model_id"] = "synthetic-executor-model-altered"
    document["role_bindings"].append(duplicate)
    document["campaign"]["role_binding_ids"].append(duplicate["binding_id"])
    document["campaign_state"]["ordered_role_binding_ids"].append(
        duplicate["binding_id"]
    )
    campaign_path = write_variant(tmp_path, "campaign.json", document)
    with pytest.raises(CampaignValidationError, match="duplicate binding identity"):
        run_ok(fresh_output_root(tmp_path), campaign=campaign_path)


def test_malformed_binding_revision_lineage_fails(tmp_path: Path) -> None:
    document = campaign_document()
    document["role_bindings"][1]["binding_revision"] = 2
    campaign_path = write_variant(tmp_path, "campaign.json", document)
    with pytest.raises(CampaignValidationError):
        run_ok(fresh_output_root(tmp_path), campaign=campaign_path)

    document = campaign_document()
    document["role_bindings"][1].update(
        {
            "binding_revision": 2,
            "replaces_binding_id": "binding-undeclared",
            "rebind_reason": "lineage fixture",
        }
    )
    campaign_path = write_variant(tmp_path, "campaign-rebind.json", document)
    with pytest.raises(CampaignValidationError, match="replaces an undeclared binding"):
        run_ok(fresh_output_root(tmp_path), campaign=campaign_path)


def test_attempt_references_executor_binding(tmp_path: Path) -> None:
    document = campaign_document()
    executor_binding = next(
        binding
        for binding in document["role_bindings"]
        if binding["role"] == "executor"
    )
    result = run_ok(fresh_output_root(tmp_path))
    attempt = load_json(result.output_dir / "attempts" / f"{result.attempt_id}.json")
    assert attempt["role_binding_id"] == executor_binding["binding_id"]


def test_evaluation_references_evaluator_binding(tmp_path: Path) -> None:
    document = campaign_document()
    evaluator_binding = next(
        binding
        for binding in document["role_bindings"]
        if binding["role"] == "evaluator"
    )
    result = run_ok(fresh_output_root(tmp_path))
    evaluation = load_json(
        result.output_dir / "evaluations" / f"{result.evaluation_id}.json"
    )
    assert evaluation["evaluator_binding_id"] == evaluator_binding["binding_id"]


def test_evaluation_references_emitted_attempt(tmp_path: Path) -> None:
    result = run_ok(fresh_output_root(tmp_path))
    evaluation = load_json(
        result.output_dir / "evaluations" / f"{result.evaluation_id}.json"
    )
    assert evaluation["evaluated_attempt_id"] == result.attempt_id


def test_task_id_differs_from_attempt_id(tmp_path: Path) -> None:
    result = run_ok(fresh_output_root(tmp_path))
    assert result.task_id != result.attempt_id


# ---------------------------------------------------------------------------
# Zero-count and negative-truth invariants
# ---------------------------------------------------------------------------


def test_provider_call_count_remains_zero(tmp_path: Path) -> None:
    result = run_ok(fresh_output_root(tmp_path), source_context=SOURCE_CONTEXT_FIXTURE)
    envelope = load_json(result.output_dir / "run-result.json")
    assert result.provider_calls == 0
    assert envelope["provider_calls_performed"] == 0


def test_source_mutation_count_remains_zero(tmp_path: Path) -> None:
    result = run_ok(fresh_output_root(tmp_path))
    envelope = load_json(result.output_dir / "run-result.json")
    assert result.source_mutations == 0
    assert envelope["source_mutations_performed"] == 0


def test_decision_gate_count_remains_zero(tmp_path: Path) -> None:
    result = run_ok(fresh_output_root(tmp_path))
    state = load_json(result.output_dir / "campaign-state.json")
    envelope = load_json(result.output_dir / "run-result.json")
    assert result.decision_gates_opened == 0
    assert state["ordered_decision_gate_ids"] == []
    assert envelope["decision_gates_opened"] == 0


def test_no_commit_merge_or_durable_ingestion_claim(tmp_path: Path) -> None:
    result = run_ok(fresh_output_root(tmp_path))
    envelope = load_json(result.output_dir / "run-result.json")
    assert result.commit_performed is False
    assert result.merge_performed is False
    assert result.durable_ingestion_performed is False
    assert envelope["commit_performed"] is False
    assert envelope["merge_performed"] is False
    assert envelope["durable_ingestion_performed"] is False


# ---------------------------------------------------------------------------
# Deterministic identity
# ---------------------------------------------------------------------------


def test_identical_inputs_yield_stable_ids(tmp_path: Path) -> None:
    first = run_ok(
        fresh_output_root(tmp_path, "a"), source_context=SOURCE_CONTEXT_FIXTURE
    )
    second = run_ok(
        fresh_output_root(tmp_path, "b"), source_context=SOURCE_CONTEXT_FIXTURE
    )
    for first_id, second_id in (
        (first.run_id, second.run_id),
        (first.attempt_id, second.attempt_id),
        (first.evaluation_id, second.evaluation_id),
        (first.receipt_id, second.receipt_id),
        (first.campaign_state_id, second.campaign_state_id),
    ):
        assert first_id == second_id
        assert "-" in first_id  # no bare UUIDs anywhere


def test_changed_executor_binding_changes_attempt_identity(tmp_path: Path) -> None:
    document = campaign_document()
    baseline = run_ok(fresh_output_root(tmp_path, "base"))

    for binding in document["role_bindings"]:
        if binding["role"] == "executor":
            binding["model_id"] = "synthetic-executor-model-v2"
    changed = run_ok(
        fresh_output_root(tmp_path, "changed"),
        campaign=write_variant(tmp_path, "campaign.json", document),
    )
    assert changed.attempt_id != baseline.attempt_id
    assert changed.evaluation_id != baseline.evaluation_id
    # The whole input document (including the executor binding) feeds the run
    # identity, so a binding change also re-derives the run lineage.
    assert changed.run_id != baseline.run_id


def test_changed_task_changes_attempt_and_run_identity(tmp_path: Path) -> None:
    document = campaign_document()
    baseline = run_ok(fresh_output_root(tmp_path, "base"))

    document["tasks"][0]["objective"] = "A materially different task objective."
    changed = run_ok(
        fresh_output_root(tmp_path, "changed"),
        campaign=write_variant(tmp_path, "campaign.json", document),
    )
    assert changed.run_id != baseline.run_id
    assert changed.attempt_id != baseline.attempt_id


def test_changed_source_context_changes_run_lineage(tmp_path: Path) -> None:
    baseline = run_ok(
        fresh_output_root(tmp_path, "base"), source_context=SOURCE_CONTEXT_FIXTURE
    )

    record = source_context_record()
    record["graph_revision"] = (
        "f" * 63 + "e"
    )
    graph_changed = run_ok(
        fresh_output_root(tmp_path, "graph"),
        source_context=write_source_variant(tmp_path, "sc-graph.json", record),
    )
    assert graph_changed.run_id != baseline.run_id
    assert graph_changed.source_context["graph_revision"] == "f" * 63 + "e"

    record = source_context_record()
    record["packet_id"] = "codexify:arp:provider-free-runtime-fixture-v2"
    packet_changed = run_ok(
        fresh_output_root(tmp_path, "packet"),
        source_context=write_source_variant(tmp_path, "sc-packet.json", record),
    )
    assert packet_changed.run_id != baseline.run_id


def test_lineage_is_preserved_without_being_permission(tmp_path: Path) -> None:
    result = run_ok(
        fresh_output_root(tmp_path), source_context=SOURCE_CONTEXT_FIXTURE
    )
    envelope = load_json(result.output_dir / "run-result.json")
    context = envelope["source_context"]
    assert context["present"] is True
    assert context["packet_id"] == "codexify:arp:provider-free-runtime-fixture"
    assert result.provider_calls == 0
    assert result.commit_performed is False
    # The lineage envelope carries only lineage fields; nothing grants authority.
    assert set(context) == {
        "present",
        "packet_id",
        "repository_revision",
        "graph_revision",
        "authority_profile",
        "question_or_intent",
        "hash",
        "stale_warnings",
        "conflicts",
        "proof_gaps",
        "human_decisions_required",
    }
    serialized = json.dumps(envelope, sort_keys=True)
    assert "granted" not in serialized


def test_stale_conflict_and_human_decision_metadata_preserved(
    tmp_path: Path,
) -> None:
    fixture = source_context_record()
    result = run_ok(
        fresh_output_root(tmp_path), source_context=SOURCE_CONTEXT_FIXTURE
    )
    artifact = load_json(result.output_dir / "source-context.json")
    assert artifact["stale_warnings"] == fixture["stale_warnings"]
    assert artifact["conflicts"] == fixture["conflicts"]
    assert artifact["proof_gaps"] == fixture["proof_gaps"]
    assert artifact["human_decisions_required"] == fixture["human_decisions_required"]
    assert result.source_context["stale_warnings"] == fixture["stale_warnings"]
    assert result.source_context["conflicts"] == fixture["conflicts"]
    assert result.source_context["human_decisions_required"] == fixture[
        "human_decisions_required"
    ]


def test_absent_source_context_is_recorded_honestly(tmp_path: Path) -> None:
    result = run_ok(fresh_output_root(tmp_path))
    assert result.source_context["present"] is False
    assert result.hashes["source_context_hash"] == "absent"
    assert not (result.output_dir / "source-context.json").exists()
    envelope = load_json(result.output_dir / "run-result.json")
    assert envelope["source_context"]["present"] is False
    assert "no source-selection lineage fixture was supplied" in envelope[
        "source_context"
    ]["note"]


# ---------------------------------------------------------------------------
# Path and publication safety
# ---------------------------------------------------------------------------


def test_path_traversal_campaign_id_rejected(tmp_path: Path) -> None:
    for hostile_id in ("..", "a/b", "campaign-.."):
        document = campaign_document()
        document["campaign"]["campaign_id"] = hostile_id
        document["campaign_state"]["campaign_id"] = hostile_id
        document["tasks"][0]["campaign_id"] = hostile_id
        campaign_path = write_variant(tmp_path, "hostile.json", document)
        with pytest.raises(CampaignValidationError):
            run_ok(fresh_output_root(tmp_path), campaign=campaign_path)


def test_output_cannot_escape_output_root(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    output_root = fresh_output_root(tmp_path)
    (output_root / "campaign-provider-free-runtime-001").symlink_to(
        outside, target_is_directory=True
    )
    with pytest.raises(CampaignArtifactError, match="escapes output root"):
        run_ok(output_root)
    assert outside.is_dir() and not any(outside.iterdir())


def test_validation_failure_leaves_no_promoted_tree(tmp_path: Path) -> None:
    document = campaign_document()
    model_ids = ("m-auditor", "m-executor", "m-evaluator")
    for binding, model_id in zip(document["role_bindings"], model_ids):
        binding["model_id"] = model_id
    _append_fourth_binding(document)
    campaign_path = write_variant(tmp_path, "campaign.json", document)
    output_root = fresh_output_root(tmp_path)
    with pytest.raises(CampaignValidationError):
        run_ok(output_root, campaign=campaign_path)
    assert_no_promoted_tree(output_root, document["campaign"]["campaign_id"])


def test_simulated_midwrite_failure_leaves_no_promoted_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    document = campaign_document()
    campaign_id = document["campaign"]["campaign_id"]
    real_write = runtime_module.atomic_write_json
    calls = {"count": 0}

    def failing_write(directory: Path, filename: str, payload) -> Path:
        calls["count"] += 1
        if calls["count"] > 3:
            raise CampaignArtifactError("simulated mid-write failure")
        return real_write(directory, filename, payload)

    monkeypatch.setattr(runtime_module, "atomic_write_json", failing_write)
    output_root = fresh_output_root(tmp_path)
    with pytest.raises(CampaignArtifactError, match="simulated mid-write failure"):
        run_ok(output_root)
    assert calls["count"] >= 4
    assert_no_promoted_tree(output_root, campaign_id)


def test_repeated_identical_runs_are_deterministic(tmp_path: Path) -> None:
    first_root = fresh_output_root(tmp_path, "first")
    second_root = fresh_output_root(tmp_path, "second")
    run_ok(first_root, source_context=SOURCE_CONTEXT_FIXTURE)
    run_ok(second_root, source_context=SOURCE_CONTEXT_FIXTURE)
    # Every artifact except run-result.json is byte-identical across roots;
    # run-result.json differs only in its root-specific output_dir path.
    first_snapshot = run_snapshot(first_root)
    second_snapshot = run_snapshot(second_root)
    first_result_path = first_root / "campaign-provider-free-runtime-001" / "run-result.json"
    second_result_path = second_root / "campaign-provider-free-runtime-001" / "run-result.json"
    first_snapshot.pop("campaign-provider-free-runtime-001/run-result.json")
    second_snapshot.pop("campaign-provider-free-runtime-001/run-result.json")
    assert first_snapshot == second_snapshot
    first_result = load_json(first_result_path)
    second_result = load_json(second_result_path)
    first_result["output_dir"] = "<normalized>"
    second_result["output_dir"] = "<normalized>"
    assert first_result == second_result
    with pytest.raises(CampaignOutputExistsError):
        run_ok(first_root, source_context=SOURCE_CONTEXT_FIXTURE)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def test_cli_human_readable_mode_succeeds(tmp_path: Path) -> None:
    output_root = fresh_output_root(tmp_path)
    completed = run_cli(
        "run-provider-free",
        "--campaign",
        str(CAMPAIGN_FIXTURE),
        "--output-root",
        str(output_root),
    )
    assert completed.returncode == 0
    assert "Provider-free Campaign Engine run complete" in completed.stdout
    assert "provider calls:     0" in completed.stdout


def test_cli_json_mode_returns_valid_json(tmp_path: Path) -> None:
    output_root = fresh_output_root(tmp_path)
    completed = run_cli(
        "run-provider-free",
        "--campaign",
        str(CAMPAIGN_FIXTURE),
        "--source-context",
        str(SOURCE_CONTEXT_FIXTURE),
        "--output-root",
        str(output_root),
        "--json",
    )
    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload["classification"] == "provider_free"
    assert payload["run_id"].startswith("run-")


def test_cli_invalid_input_returns_nonzero(tmp_path: Path) -> None:
    bad = tmp_path / "bad-campaign.json"
    bad.write_text("{ not valid json ", encoding="utf-8")
    output_root = fresh_output_root(tmp_path)
    completed = run_cli(
        "run-provider-free",
        "--campaign",
        str(bad),
        "--output-root",
        str(output_root),
    )
    assert completed.returncode != 0
    assert "provider-free campaign failed" in completed.stderr


# ---------------------------------------------------------------------------
# Prohibited execution seams
# ---------------------------------------------------------------------------


def test_no_pi_invocation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert_seam_untouched(
        monkeypatch,
        ["pi", "pi_runtime", "codex_runner.pi_runtime", "codex_runner.pi_loop_manager"],
        tmp_path,
    )


def test_no_coding_loop_invocation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert_seam_untouched(
        monkeypatch,
        ["guardian.workers.coding_worker", "guardian.routes.agent_orchestration"],
        tmp_path,
    )


def test_no_guardian_execution_seam(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert_seam_untouched(monkeypatch, ["guardian", "guardian.guardian_api"], tmp_path)


def test_no_command_bus_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert_seam_untouched(
        monkeypatch, ["guardian.command_bus", "guardian.command_bus.invoke"], tmp_path
    )


def test_no_provider_adapter_invocation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert_seam_untouched(
        monkeypatch, ["guardian.providers", "guardian.providers.deepseek_adapter"], tmp_path
    )


def test_no_subprocess_model_invocation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert_seam_untouched(monkeypatch, [], tmp_path)


def test_no_network_access(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert_seam_untouched(monkeypatch, [], tmp_path)


def test_no_git_command_or_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert_seam_untouched(monkeypatch, ["git"], tmp_path)


def test_no_database_mutation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert_seam_untouched(
        monkeypatch, ["psycopg2", "psycopg", "sqlalchemy", "neo4j"], tmp_path
    )


def test_package_imports_no_prohibited_modules_in_clean_interpreter(
    tmp_path: Path,
) -> None:
    """Fresh interpreter: inject exploding stubs, import the runtime, run it."""
    script = tmp_path / "seam_probe.py"
    script.write_text(
        (
            "import json, os, sys\n"
            "from pathlib import Path\n"
            "sys.path.insert(0, os.getcwd())\n"
            "class ExplodingModule:\n"
            "    def __getattr__(self, name):\n"
            "        raise AssertionError('prohibited seam touched: ' + name)\n"
            "stubs = {}\n"
            "for name in ['guardian', 'guardian.command_bus', 'guardian.providers',\n"
            "            'guardian.workers', 'codex_runner.pi_runtime',\n"
            "            'codex_runner.runner', 'git', 'psycopg2', 'psycopg',\n"
            "            'sqlalchemy', 'neo4j']:\n"
            "    stub = ExplodingModule()\n"
            "    sys.modules[name] = stub\n"
            "    stubs[name] = stub\n"
            "from codex_runner.campaign_engine import run_provider_free_campaign\n"
            "result = run_provider_free_campaign(\n"
            f"    Path({str(CAMPAIGN_FIXTURE)!r}),\n"
            f"    Path({str(tmp_path)!r}) / 'probe-out',\n"
            "    source_context_path="
            f"Path({str(SOURCE_CONTEXT_FIXTURE)!r}),\n"
            ")\n"
            "prohibited = []\n"
            "for name in sys.modules:\n"
            "    if name in stubs and sys.modules[name] is stubs[name]:\n"
            "        continue  # our own guard stub, not a real import\n"
            "    if (name.split('.')[0] in {\n"
            "            'subprocess', 'socket', 'http', 'git', 'guardian',\n"
            "            'psycopg2', 'psycopg', 'sqlalchemy', 'neo4j',\n"
            "            'pi_runtime',\n"
            "        } or name in {'codex_runner.runner', 'urllib.request',\n"
            "                      'urllib.error'}):\n"
            "        prohibited.append(name)\n"
            "assert not prohibited, f'prohibited modules imported: {prohibited}'\n"
            "assert result.provider_calls == 0 and result.source_mutations == 0\n"
            "print('SEAM_PROBE_OK')\n"
        ),
        encoding="utf-8",
    )
    completed = subprocess.run(
        [sys.executable, str(script)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        env=_clean_env(),
    )
    assert completed.returncode == 0, completed.stderr
    assert "SEAM_PROBE_OK" in completed.stdout
