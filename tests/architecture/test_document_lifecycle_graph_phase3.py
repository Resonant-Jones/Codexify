"""Deterministic semantic-validation coverage for DLG Phase 3A.

These tests exercise a repository-local control-plane tool only.  They do not
start runtime services, mutate canonical nodes, create Agent Reading Packets,
or make release claims.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest

from scripts.knowledge_graph import validate_and_generate_dlg as dlg


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts/knowledge_graph/validate_and_generate_dlg.py"
SCHEMA_PATH = REPO_ROOT / "schemas/knowledge/document-lifecycle-graph.schema.json"
NODES_DIR = REPO_ROOT / "docs/knowledge-graph/nodes"
BASE_GENERATED_AT = "2026-08-08T12:25:50-04:00"


def current_repository_revision() -> str:
    """Return the committed revision governing the live repository corpus."""
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    revision = completed.stdout.strip()
    assert len(revision) == 40 and all(
        character in "0123456789abcdef" for character in revision
    )
    return revision


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def relation(relation_type: str, target_document_id: str, **overrides: str) -> dict:
    value = {
        "relation_type": relation_type,
        "target_document_id": target_document_id,
        "authority_scope": "deterministic synthetic test scope",
        "canonicality": "canonical",
        "review_status": "accepted",
        "rationale": "Synthetic reviewed relation for deterministic validator coverage.",
    }
    value.update(overrides)
    return value


def node(
    document_id: str = "codexify:doc:architecture:alpha",
    path: str = "docs/architecture/alpha.md",
    **overrides,
) -> dict:
    """Return one schema-complete non-contract node for temporary corpora."""
    value = {
        "schema_version": "1.0.0",
        "record_type": "document_node",
        "document_id": document_id,
        "path": path,
        "title": document_id.rsplit(":", 1)[-1].replace("-", " ").title(),
        "kind": "runtime_map",
        "summary": "Synthetic DLG node used only by deterministic semantic tests.",
        "aliases": [],
        "authority_class": "structural_authority",
        "authority_scopes": [f"scope:{document_id.rsplit(':', 1)[-1]}"],
        "lifecycle_state": "active",
        "freshness": {
            "state": "current",
            "verified_at": "2026-08-08T00:00:00Z",
            "verified_commit": "0" * 40,
            "triggers": ["synthetic source changes"],
        },
        "disposition": "accepted",
        "evidence_class": "proven-test",
        "owners": ["Codexify architecture maintainers"],
        "source_anchors": [
            {
                "path": path,
                "anchor_type": "document",
                "invalidates_freshness": False,
            }
        ],
        "read_when": ["running deterministic DLG Phase 3A tests"],
        "must_not_prove": ["runtime behavior", "release support"],
        "retrieval_policy": {
            "default_policy": "include",
            "applicable_intents": ["architecture_decision"],
            "excluded_intents": [],
            "priority": "primary",
        },
        "temporal": {
            "created_at": "2026-08-08T00:00:00Z",
            "effective_from": "2026-08-08T00:00:00Z",
        },
        "content_hash": "0" * 64,
        "relations": [],
        "governing_adr_posture": "not_applicable",
    }
    value.update(overrides)
    return value


def write_synthetic_repository(
    tmp_path: Path,
    nodes: list[dict],
    *,
    contents: dict[str, str] | None = None,
    schema_bytes: bytes | None = None,
) -> Path:
    """Materialize a tiny read-only-style DLG repository for a test."""
    root = tmp_path / "repository"
    schema_target = root / "schemas/knowledge/document-lifecycle-graph.schema.json"
    schema_target.parent.mkdir(parents=True, exist_ok=True)
    schema_target.write_bytes(schema_bytes if schema_bytes is not None else SCHEMA_PATH.read_bytes())
    node_dir = root / "docs/knowledge-graph/nodes"
    node_dir.mkdir(parents=True, exist_ok=True)
    content_by_id = contents or {}
    for index, original in enumerate(nodes):
        item = copy.deepcopy(original)
        filename = item.pop("_filename", f"{item['document_id']}.json")
        create_source = item.pop("_create_source", True)
        source_content = item.pop(
            "_source_content",
            content_by_id.get(item["document_id"], f"# {item['title']}\n"),
        )
        if create_source and isinstance(item.get("path"), str) and not item["path"].startswith("/"):
            source = root / item["path"]
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text(source_content, encoding="utf-8")
            item["content_hash"] = sha256_text(source_content)
        node_file = node_dir / filename
        node_file.write_text(json.dumps(item, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return root


def validation_codes(result: dlg.ValidationResult) -> set[str]:
    return {issue.code for issue in result.issues}


def validate_synthetic(root: Path) -> dlg.ValidationResult:
    return dlg.validate_repository(
        root,
        "0" * 40,
        "2026-08-08T00:00:00Z",
        check_git=False,
    )


def contract_and_adr() -> tuple[dict, dict]:
    adr = node(
        "codexify:doc:adr:999-synthetic-governance",
        "docs/architecture/adr/999-synthetic-governance.md",
        kind="adr",
        authority_class="accepted_adr",
        authority_scopes=["synthetic governance"],
        governing_adr_posture="accepted",
    )
    contract = node(
        "codexify:doc:architecture:synthetic-contract",
        "docs/architecture/synthetic-contract.md",
        kind="architecture_contract",
        authority_class="normative_contract",
        authority_scopes=["synthetic contract"],
        governing_adr_posture="accepted",
        relations=[relation("governed_by", adr["document_id"])],
    )
    return adr, contract


def test_current_nine_node_corpus_validates() -> None:
    result = dlg.validate_repository(
        REPO_ROOT, current_repository_revision(), BASE_GENERATED_AT
    )

    assert not result.has_errors
    assert result.schema_valid_node_count == 9
    assert result.source_hash_match_count == 9


def test_current_relationship_baseline_and_target_resolution() -> None:
    result = dlg.validate_repository(
        REPO_ROOT, current_repository_revision(), BASE_GENERATED_AT
    )

    assert result.edge_count == 8
    assert result.predicate_counts() == {
        "depends_on": 2,
        "evidence_for": 4,
        "governed_by": 2,
    }
    assert result.target_resolution_count == 8
    assert result.self_relation_count == 0


def test_duplicate_document_id_fails(tmp_path: Path) -> None:
    first = node()
    second = node(
        path="docs/architecture/beta.md",
        _filename="codexify:doc:architecture:beta.json",
    )
    result = validate_synthetic(write_synthetic_repository(tmp_path, [first, second]))

    assert "duplicate_document_id" in validation_codes(result)


def test_duplicate_active_path_fails(tmp_path: Path) -> None:
    first = node()
    second = node("codexify:doc:architecture:beta", path=first["path"])
    result = validate_synthetic(write_synthetic_repository(tmp_path, [first, second]))

    assert "duplicate_active_path" in validation_codes(result)


def test_missing_relation_target_fails(tmp_path: Path) -> None:
    source = node(relations=[relation("depends_on", "codexify:doc:architecture:missing")])
    result = validate_synthetic(write_synthetic_repository(tmp_path, [source]))

    assert "relationship_target_unresolved" in validation_codes(result)


def test_self_relation_fails(tmp_path: Path) -> None:
    source = node()
    source["relations"] = [relation("depends_on", source["document_id"])]
    result = validate_synthetic(write_synthetic_repository(tmp_path, [source]))

    assert "self_relation" in validation_codes(result)


@pytest.mark.parametrize("predicate", ["pointer_to", "supersedes", "derived_from"])
def test_forbidden_acyclic_predicates_reject_cycles(tmp_path: Path, predicate: str) -> None:
    first = node()
    second = node("codexify:doc:architecture:beta", "docs/architecture/beta.md")
    if predicate == "pointer_to":
        for item in (first, second):
            item["kind"] = "compatibility_pointer"
            item["authority_class"] = "pointer"
    first["relations"] = [relation(predicate, second["document_id"])]
    second["relations"] = [relation(predicate, first["document_id"])]
    result = validate_synthetic(write_synthetic_repository(tmp_path, [first, second]))

    assert result.cycle_findings[predicate]
    assert "forbidden_relation_cycle" in validation_codes(result)


def test_depends_on_cycle_is_not_a_phase3a_cycle_rule(tmp_path: Path) -> None:
    first = node(relations=[relation("depends_on", "codexify:doc:architecture:beta")])
    second = node(
        "codexify:doc:architecture:beta",
        "docs/architecture/beta.md",
        relations=[relation("depends_on", first["document_id"])],
    )
    result = validate_synthetic(write_synthetic_repository(tmp_path, [first, second]))

    assert not result.has_errors
    assert not any(result.cycle_findings[predicate] for predicate in result.cycle_findings)


def test_compatibility_pointer_requires_exactly_one_pointer_to(tmp_path: Path) -> None:
    target = node("codexify:doc:architecture:target", "docs/architecture/target.md")
    pointer = node(
        kind="compatibility_pointer",
        authority_class="pointer",
        relations=[],
    )
    result = validate_synthetic(write_synthetic_repository(tmp_path, [target, pointer]))

    assert "compatibility_pointer_cardinality" in validation_codes(result)


def test_accepted_contract_without_accepted_governing_adr_fails(tmp_path: Path) -> None:
    contract = node(
        kind="architecture_contract",
        authority_class="normative_contract",
        governing_adr_posture="accepted",
    )
    result = validate_synthetic(write_synthetic_repository(tmp_path, [contract]))

    assert "accepted_contract_governing_relation_missing" in validation_codes(result)


def test_valid_accepted_contract_governance_passes(tmp_path: Path) -> None:
    adr, contract = contract_and_adr()
    result = validate_synthetic(write_synthetic_repository(tmp_path, [adr, contract]))

    assert not result.has_errors
    assert result.accepted_contract_governance_findings == 0


def test_proof_authority_and_lifecycle_invariants_are_enforced(tmp_path: Path) -> None:
    proof = node(
        "codexify:doc:proof:synthetic-proof",
        "docs/architecture/proofs/synthetic-proof.md",
        kind="proof",
        authority_class="supplementary",
        lifecycle_state="active",
    )
    result = validate_synthetic(write_synthetic_repository(tmp_path, [proof]))

    assert {"proof_authority_invariant", "proof_lifecycle_invariant"} <= validation_codes(result)


def test_content_hash_mismatch_fails(tmp_path: Path) -> None:
    source = node()
    root = write_synthetic_repository(tmp_path, [source])
    (root / source["path"]).write_text("changed source bytes\n", encoding="utf-8")
    result = validate_synthetic(root)

    assert "content_hash_mismatch" in validation_codes(result)


def test_unknown_and_invalid_verified_git_commit_fail(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = node()
    root = write_synthetic_repository(tmp_path, [source])
    result = validate_synthetic(root)

    result.nodes[0]["freshness"]["verified_commit"] = "a" * 40
    monkeypatch.setattr(dlg, "_git_commit_exists", lambda _root, revision: revision == "0" * 40)
    dlg._validate_git_revision_integrity(result, check_git=True)
    assert "verified_commit_unknown" in validation_codes(result)

    result.nodes[0]["freshness"]["verified_commit"] = "not-a-commit"
    dlg._validate_git_revision_integrity(result, check_git=True)
    assert "verified_commit_invalid" in validation_codes(result)


def test_lfs_pointer_node_content_fails(tmp_path: Path) -> None:
    root = write_synthetic_repository(tmp_path, [])
    lfs_file = root / "docs/knowledge-graph/nodes/codexify:doc:architecture:lfs.json"
    lfs_file.write_text(
        "version https://git-lfs.github.com/spec/v1\noid sha256:abc\nsize 1\n",
        encoding="utf-8",
    )
    result = validate_synthetic(root)

    assert "node_lfs_pointer" in validation_codes(result)


def test_private_absolute_path_metadata_fails(tmp_path: Path) -> None:
    source = node(summary="Synthetic metadata references /Users/example/private-file.")
    result = validate_synthetic(write_synthetic_repository(tmp_path, [source]))

    assert "prohibited_metadata" in validation_codes(result)


def test_secret_like_metadata_fails(tmp_path: Path) -> None:
    source = node(summary="Synthetic secret sk-abcdefghijklmnopqrstuvwxyz1234567890 is forbidden.")
    result = validate_synthetic(write_synthetic_repository(tmp_path, [source]))

    assert "prohibited_metadata" in validation_codes(result)


def test_ordinary_token_vocabulary_is_not_a_secret_false_positive(tmp_path: Path) -> None:
    source = node(summary="Canonical token vocabulary remains ordinary architecture prose.")
    result = validate_synthetic(write_synthetic_repository(tmp_path, [source]))

    assert "prohibited_metadata" not in validation_codes(result)


def test_retrieval_intent_in_include_and_exclude_sets_fails(tmp_path: Path) -> None:
    source = node()
    source["retrieval_policy"]["excluded_intents"] = ["architecture_decision"]
    result = validate_synthetic(write_synthetic_repository(tmp_path, [source]))

    assert "retrieval_policy_contradiction" in validation_codes(result)


def test_adr_number_collision_collection_is_deterministic(tmp_path: Path) -> None:
    source = node()
    root = write_synthetic_repository(tmp_path, [source])
    adr_dir = root / "docs/architecture/adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / "005-first.md").write_text("# first\n", encoding="utf-8")
    (adr_dir / "005-second.md").write_text("# second\n", encoding="utf-8")
    first = validate_synthetic(root)
    second = validate_synthetic(root)

    assert first.adr_number_collisions == second.adr_number_collisions
    assert first.adr_number_collisions[0]["adr_number"] == "005"


def test_orphan_calculation_uses_reviewed_edges_only(tmp_path: Path) -> None:
    first = node(relations=[relation("depends_on", "codexify:doc:architecture:beta")])
    second = node("codexify:doc:architecture:beta", "docs/architecture/beta.md")
    orphan = node("codexify:doc:architecture:orphan", "docs/architecture/orphan.md")
    result = validate_synthetic(write_synthetic_repository(tmp_path, [first, second, orphan]))

    assert result.orphans == [
        {
            "document_id": orphan["document_id"],
            "path": orphan["path"],
            "reason": "no incoming or outgoing reviewed DLG relations",
        }
    ]


def test_release_authority_duplicate_exact_scope_becomes_conflict_without_winner(tmp_path: Path) -> None:
    first = node(
        authority_class="release_authority",
        authority_scopes=["release readiness"],
    )
    second = node(
        "codexify:doc:architecture:alternate-release",
        "docs/architecture/alternate-release.md",
        authority_class="release_authority",
        authority_scopes=["release readiness"],
    )
    result = validate_synthetic(write_synthetic_repository(tmp_path, [first, second]))

    assert len(result.authority_conflicts) == 1
    conflict = result.authority_conflicts[0]
    assert conflict["scope"] == "release readiness"
    assert "winner" not in conflict
    assert "winner" not in conflict["reason"]


def test_supersession_map_mirrors_only_reviewed_canonical_edges(tmp_path: Path) -> None:
    older = node("codexify:doc:architecture:older", "docs/architecture/older.md")
    newer = node(
        "codexify:doc:architecture:newer",
        "docs/architecture/newer.md",
        relations=[relation("supersedes", older["document_id"])],
    )
    advisory = node(
        "codexify:doc:architecture:advisory",
        "docs/architecture/advisory.md",
        relations=[
            relation(
                "supersedes",
                older["document_id"],
                canonicality="advisory",
            )
        ],
    )
    result = validate_synthetic(write_synthetic_repository(tmp_path, [older, newer, advisory]))

    assert result.supersession_set == [
        {
            "newer_document_id": newer["document_id"],
            "older_document_id": older["document_id"],
        }
    ]


def test_no_supersedes_edge_produces_empty_truthful_supersession_set(tmp_path: Path) -> None:
    result = validate_synthetic(write_synthetic_repository(tmp_path, [node()]))

    assert result.supersession_set == []


def test_graph_revision_is_deterministic_and_changes_with_node_relation_and_schema() -> None:
    result = dlg.validate_repository(
        REPO_ROOT, current_repository_revision(), BASE_GENERATED_AT
    )
    first = dlg.compute_graph_revision(result.schema, result.schema_bytes, result.nodes)
    second = dlg.compute_graph_revision(result.schema, result.schema_bytes, result.nodes)
    changed_node = copy.deepcopy(result.nodes)
    changed_node[0]["summary"] += " changed"
    changed_relation = copy.deepcopy(result.nodes)
    changed_relation[0]["relations"] = [
        relation("depends_on", changed_relation[1]["document_id"])
    ]

    assert first == second == result.graph_revision
    assert dlg.compute_graph_revision(result.schema, result.schema_bytes, changed_node) != first
    assert dlg.compute_graph_revision(result.schema, result.schema_bytes, changed_relation) != first
    assert dlg.compute_graph_revision(result.schema, result.schema_bytes + b"\n", result.nodes) != first


def test_graph_revision_ignores_timestamp_and_repository_revision(tmp_path: Path) -> None:
    root = write_synthetic_repository(tmp_path, [node()])
    first = dlg.validate_repository(root, "0" * 40, "2026-08-08T00:00:00Z", check_git=False)
    second = dlg.validate_repository(root, "f" * 40, "2030-01-01T00:00:00Z", check_git=False)

    assert first.graph_revision == second.graph_revision


def test_generated_document_graph_validates_and_all_reports_share_revision(tmp_path: Path) -> None:
    root = write_synthetic_repository(tmp_path, [node()])
    output = tmp_path / "output"
    result = dlg.generate(root, "0" * 40, "2026-08-08T00:00:00Z", output_root=output, check_git=False)
    schema = json.loads((root / "schemas/knowledge/document-lifecycle-graph.schema.json").read_text(encoding="utf-8"))
    graph = json.loads((output / "document-graph.json").read_text(encoding="utf-8"))
    report_revisions = {
        json.loads((output / filename).read_text(encoding="utf-8"))["graph_revision"]
        for filename in dlg.OUTPUT_FILENAMES
    }

    assert not result.has_errors
    jsonschema.Draft202012Validator(schema).validate(graph)
    assert report_revisions == {result.graph_revision}


def test_generated_outputs_have_required_non_authoritative_notices(tmp_path: Path) -> None:
    root = write_synthetic_repository(tmp_path, [node()])
    output = tmp_path / "output"
    result = dlg.generate(root, "0" * 40, "2026-08-08T00:00:00Z", output_root=output, check_git=False)

    assert not result.has_errors
    for filename in dlg.OUTPUT_FILENAMES:
        notice = json.loads((output / filename).read_text(encoding="utf-8"))["notice"].lower()
        for word in ("generated", "derived", "reconstructable", "non-authoritative", "hand edit"):
            assert word in notice


def test_generated_outputs_are_byte_reproducible_and_check_generated_passes(tmp_path: Path) -> None:
    root = write_synthetic_repository(tmp_path, [node()])
    first_output = tmp_path / "first"
    second_output = tmp_path / "second"
    first = dlg.generate(root, "0" * 40, "2026-08-08T00:00:00Z", output_root=first_output, check_git=False)
    second = dlg.generate(root, "0" * 40, "2026-08-08T00:00:00Z", output_root=second_output, check_git=False)
    checked = dlg.check_generated(root, "0" * 40, "2026-08-08T00:00:00Z", output_root=first_output, check_git=False)

    assert not first.has_errors and not second.has_errors and not checked.has_errors
    for filename in dlg.OUTPUT_FILENAMES:
        assert (first_output / filename).read_bytes() == (second_output / filename).read_bytes()


def test_generated_json_is_utf8_and_atomic_write_uses_same_directory_replace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "generated.json"
    real_replace = os.replace
    replacements: list[tuple[Path, Path]] = []

    def recording_replace(source: Path | str, destination: Path | str) -> None:
        replacements.append((Path(source), Path(destination)))
        real_replace(source, destination)

    monkeypatch.setattr(dlg.os, "replace", recording_replace)
    dlg.atomic_write_json(target, {"value": "UTF-8 ✓"})

    assert target.read_text(encoding="utf-8").endswith("\n")
    assert replacements and replacements[0][0].parent == target.parent
    assert replacements[0][1] == target


def test_generation_preserves_canonical_nodes_and_markdown_and_never_creates_arps(
    tmp_path: Path,
) -> None:
    source = node()
    root = write_synthetic_repository(tmp_path, [source])
    node_before = {
        path.name: path.read_bytes()
        for path in (root / "docs/knowledge-graph/nodes").glob("*.json")
    }
    markdown_before = (root / source["path"]).read_bytes()
    output = tmp_path / "output"
    result = dlg.generate(root, "0" * 40, "2026-08-08T00:00:00Z", output_root=output, check_git=False)
    node_after = {
        path.name: path.read_bytes()
        for path in (root / "docs/knowledge-graph/nodes").glob("*.json")
    }

    assert not result.has_errors
    assert node_after == node_before
    assert (root / source["path"]).read_bytes() == markdown_before
    assert sorted(path.name for path in output.iterdir()) == sorted(dlg.OUTPUT_FILENAMES)
    assert not any("arp" in path.name.lower() for path in output.iterdir())


def test_stale_source_anchor_changes_are_reported_without_mutating_node_freshness(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = node()
    source["source_anchors"][0]["invalidates_freshness"] = True
    root = write_synthetic_repository(tmp_path, [source])
    result = validate_synthetic(root)
    source_file = root / source["path"]
    anchor_matches = {(source["document_id"], source["path"]): [source_file]}
    monkeypatch.setattr(dlg, "_changed_commits_for_anchor", lambda *args: ["a" * 40])

    dlg._collect_freshness_findings(result, anchor_matches, check_git=True)

    assert result.nodes[0]["freshness"]["state"] == "current"
    assert result.changed_anchors[0]["anchor_path"] == source["path"]
    assert result.stale_documents[0]["document_id"] == source["document_id"]


def test_free_form_freshness_duration_becomes_coverage_gap_not_guessed_policy(tmp_path: Path) -> None:
    source = node()
    source["freshness"]["triggers"] = ["refresh every 7 days"]
    result = validate_synthetic(write_synthetic_repository(tmp_path, [source]))

    assert result.coverage_gaps[0]["document_id"] == source["document_id"]
    assert result.nodes[0]["freshness"].get("window_days") is None


def test_missing_repository_local_source_anchor_is_detected(tmp_path: Path) -> None:
    source = node()
    source["source_anchors"] = [
        {
            "path": "docs/architecture/missing-anchor.md",
            "anchor_type": "document",
            "invalidates_freshness": True,
        }
    ]
    result = validate_synthetic(write_synthetic_repository(tmp_path, [source]))

    assert "source_anchor_missing" in validation_codes(result)


def test_broken_local_markdown_link_is_reported_and_external_http_link_is_ignored(tmp_path: Path) -> None:
    broken = node(_source_content="# Source\n[missing](missing.md)\n")
    root = write_synthetic_repository(tmp_path / "broken", [broken])
    broken_result = validate_synthetic(root)
    assert "broken_local_markdown_link" in validation_codes(broken_result)

    external = node(_source_content="# Source\n[external](https://example.com/path)\n")
    external_root = write_synthetic_repository(tmp_path / "external", [external])
    external_result = validate_synthetic(external_root)
    assert "broken_local_markdown_link" not in validation_codes(external_result)


def test_validator_cli_runs_without_runtime_services() -> None:
    completed = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "validate"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    summary = json.loads(completed.stdout)
    assert summary["corpus"]["node_count"] == 9
    assert summary["corpus"]["edge_count"] == 8
