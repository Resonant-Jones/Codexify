"""Tests for the repository-local canonical audit evidence validator."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

from scripts.audit.validate_canonical_evidence import validate_manifest


ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "schemas/audit/canonical-audit-evidence.schema.json"
SCRIPT = ROOT / "scripts/audit/validate_canonical_evidence.py"
FIXTURES = ROOT / "tests/audit/fixtures"
CANONICAL = FIXTURES / "canonical-evidence.valid.canonical.json"
PROVISIONAL = FIXTURES / "canonical-evidence.valid.provisional.json"


def _manifest(path: Path = CANONICAL) -> dict:
    return json.loads(path.read_text())


def _write(tmp_path: Path, value: object) -> Path:
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _validate(path: Path) -> dict:
    return validate_manifest(path, SCHEMA, ROOT)


def _codes(result: dict) -> set[str]:
    return {issue["code"] for issue in result["issues"]}


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)


def test_schema_is_valid_draft_2020_12() -> None:
    Draft202012Validator.check_schema(json.loads(SCHEMA.read_text()))


def test_valid_canonical_is_pass_and_eligible() -> None:
    result = _validate(CANONICAL)
    assert result["result"] == "pass"
    assert result["canonical_eligible"] is True
    assert result["artifact_integrity_valid"] is True


def test_valid_provisional_passes_but_is_ineligible() -> None:
    result = _validate(PROVISIONAL)
    assert result["result"] == "pass"
    assert result["canonical_eligible"] is False
    assert "authority_status_not_canonical" in result["eligibility_reasons"]


def test_malformed_json_and_non_object_root_fail(tmp_path: Path) -> None:
    malformed = tmp_path / "broken.json"
    malformed.write_text("{", encoding="utf-8")
    assert "manifest_json_invalid" in _codes(_validate(malformed))
    assert "manifest_root_invalid" in _codes(_validate(_write(tmp_path, [])))


def test_schema_errors_include_stable_json_path(tmp_path: Path) -> None:
    manifest = _manifest()
    del manifest["execution"]
    result = _validate(_write(tmp_path, manifest))
    issue = next(issue for issue in result["issues"] if issue["code"] == "schema_validation_error")
    assert issue["path"] == "$"


def test_canonical_authority_and_repository_rules(tmp_path: Path) -> None:
    cases = [
        ("machine_id", "other", "canonical_machine_id_invalid"),
        ("machine_role", "provisional_development_host", "canonical_machine_role_invalid"),
        ("branch", "feature", "canonical_branch_invalid"),
        ("dirty", True, "canonical_worktree_dirty"),
        ("upstream_sha", "fedcba9876543210fedcba9876543210fedcba98", "canonical_commit_upstream_mismatch"),
    ]
    for field, value, code in cases:
        manifest = _manifest()
        target = manifest["machine"] if field.startswith("machine") else manifest["repository"]
        target[field] = value
        assert code in _codes(_validate(_write(tmp_path, manifest)))


def test_live_runtime_requires_complete_identity_and_other_proof_can_be_null(tmp_path: Path) -> None:
    manifest = _manifest()
    manifest["proof_class"] = "CURRENT_LIVE_PROOF"
    assert "live_runtime_identity_incomplete" in _codes(_validate(_write(tmp_path, manifest)))
    assert _validate(CANONICAL)["semantic_valid"] is True


def test_artifact_errors_fail_closed(tmp_path: Path) -> None:
    cases = [
        ("missing.txt", "artifact_missing"),
        ("/tmp/proof.txt", "artifact_path_absolute"),
        ("../proof.txt", "artifact_path_parent_traversal"),
    ]
    for path, code in cases:
        manifest = _manifest()
        manifest["artifacts"][0]["path"] = path
        assert code in _codes(_validate(_write(tmp_path, manifest)))
    manifest = _manifest()
    manifest["artifacts"][0]["sha256"] = "0" * 64
    assert "artifact_hash_mismatch" in _codes(_validate(_write(tmp_path, manifest)))


def test_symlink_escape_fails(tmp_path: Path) -> None:
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")
    root = tmp_path / "repo"
    root.mkdir()
    (root / "escape.txt").symlink_to(outside)
    manifest = _manifest()
    manifest["artifacts"][0]["path"] = "escape.txt"
    assert "artifact_path_outside_repo" in _codes(validate_manifest(_write(tmp_path, manifest), SCHEMA, root))


def test_stale_or_nonaccepted_canonical_records_are_ineligible(tmp_path: Path) -> None:
    for field, value in (("freshness_status", "STALE"), ("disposition", "REJECTED"), ("disposition", "SUPERSEDED")):
        manifest = _manifest()
        manifest[field] = value
        result = _validate(_write(tmp_path, manifest))
        assert result["result"] == "pass"
        assert result["canonical_eligible"] is False


def test_failure_outcomes_remain_eligible_observations(tmp_path: Path) -> None:
    for outcome in ("FAIL", "BLOCKED", "ERROR"):
        manifest = _manifest()
        manifest["execution_outcome"] = outcome
        result = _validate(_write(tmp_path, manifest))
        assert result["result"] == "pass"
        assert result["canonical_eligible"] is True


def test_result_and_cli_json_are_deterministic(tmp_path: Path) -> None:
    manifest = _manifest()
    manifest["machine"]["machine_id"] = "other"
    manifest["artifacts"][0]["path"] = "../missing.txt"
    path = _write(tmp_path, manifest)
    assert _validate(path) == _validate(path)
    first, second = _run(str(path), "--json"), _run(str(path), "--json")
    assert first.returncode == second.returncode == 1
    assert first.stdout == second.stdout
    issues = json.loads(first.stdout)["issues"]
    assert [issue["issue_id"] for issue in issues] == [f"issue-{i:04d}" for i in range(1, len(issues) + 1)]


def test_cli_exit_codes_and_human_output_are_safe(tmp_path: Path) -> None:
    assert _run(str(CANONICAL), "--json").returncode == 0
    failed = _run(str(_write(tmp_path, {"schema_version": "bad"})), "--json")
    assert failed.returncode == 1
    assert _run().returncode == 2
    human = _run(str(CANONICAL))
    assert str(ROOT) not in human.stdout
