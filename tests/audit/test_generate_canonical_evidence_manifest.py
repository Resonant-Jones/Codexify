"""Focused tests for the bounded canonical evidence manifest producer."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.audit.generate_canonical_evidence_manifest import generate_manifest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/audit/generate_canonical_evidence_manifest.py"

PROFILE = """name: v1-local-core-web-mcp
version: 1
surface: local-docker-compose-webui
required_services:
  - backend
  - db
optional_services:
  - redis
extension_posture:
  public: []
  internal: []
route_posture:
  enabled: []
  internal_only: []
  quarantined: []
provider_contract: {}
criticality:
  tier0:
    services: [backend, db]
    routes: []
"""


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], check=True, text=True, capture_output=True)
    return result.stdout.strip()


def migration(revision: str, down_revision: str | None = None) -> str:
    return f'''"""fixture migration."""
revision = "{revision}"
down_revision = {down_revision!r}
'''


def make_fixture(tmp_path: Path) -> dict[str, Path]:
    root = tmp_path / "repo"
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
    subprocess.run(["git", "init", "-b", "main", str(root)], check=True, capture_output=True)
    git(root, "config", "user.email", "test@example.invalid")
    git(root, "config", "user.name", "Test User")
    profile_dir = root / "config" / "supported_profiles"
    migration_dir = root / "guardian" / "db" / "migrations" / "versions"
    artifact_dir = root / "proofs"
    profile_dir.mkdir(parents=True)
    migration_dir.mkdir(parents=True)
    artifact_dir.mkdir(parents=True)
    (profile_dir / "v1-local-core-web-mcp.yaml").write_text(PROFILE, encoding="utf-8")
    compose = root / "docker-compose.yml"
    compose.write_text("name: codexify\nservices:\n  backend: {}\n  db: {}\n  redis: {}\n", encoding="utf-8")
    (migration_dir / "a_revision.py").write_text(migration("head-a"), encoding="utf-8")
    artifact = artifact_dir / "proof.txt"
    artifact.write_text("fixture proof\n", encoding="utf-8")
    metadata_path = root / "manifest-input.json"
    metadata_path.write_text(json.dumps(base_metadata(runtime_requested=False), indent=2) + "\n", encoding="utf-8")
    git(root, "add", ".")
    git(root, "commit", "-m", "fixture")
    git(root, "remote", "add", "origin", str(remote))
    git(root, "push", "-u", "origin", "main")
    return {
        "root": root,
        "remote": remote,
        "profile_dir": profile_dir,
        "migration_dir": migration_dir,
        "compose": compose,
        "artifact": artifact,
        "metadata": metadata_path,
    }


def base_metadata(*, runtime_requested: bool = True) -> dict:
    return {
        "created_at": "2026-07-13T12:00:00-04:00",
        "proof_class": "CURRENT_TEST_PROOF",
        "freshness_status": "CURRENT",
        "disposition": "ACCEPTED",
        "runtime_identity_requested": runtime_requested,
        "execution": {
            "outcome": "PASS",
            "suite_id": "fixture-suite",
            "commands": ["fixture --read-only"],
            "started_at": "2026-07-13T15:00:00Z",
            "completed_at": "2026-07-13T15:00:01Z",
            "exit_code": 0,
            "summary": "Controlled fixture observation; no command was executed by the producer.",
        },
        "claims": {"supported": [], "disproved": [], "unresolved": []},
        "artifacts": [],
        "relationships": {"supersedes": [], "contradicts": [], "derived_from": []},
    }


def collect(fixture: dict[str, Path], **kwargs: object) -> dict:
    return generate_manifest(
        fixture["root"],
        hostname="fixture-host",
        metadata=base_metadata(runtime_requested=False),
        **kwargs,
    )


def runtime_kwargs(fixture: dict[str, Path]) -> dict[str, object]:
    return {
        "runtime_identity_requested": True,
        "profiles_dir": fixture["profile_dir"],
        "compose_files": ["docker-compose.yml"],
        "audit_project": "codexify-audit",
        "migration_dir": fixture["migration_dir"],
    }


def test_provisional_manifest_is_deterministic_and_validated(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    first = collect(fixture, machine_id="developer-laptop")
    second = collect(fixture, machine_id="developer-laptop")
    assert first == second
    assert first["result"] == "pass"
    assert first["validation"]["result"] == "pass"
    assert first["validation"]["canonical_eligible"] is False
    assert first["manifest"]["authority_status"] == "PROVISIONAL"
    assert first["manifest"]["evidence_id"].startswith("evidence-sha256-")
    assert str(fixture["root"]) not in json.dumps(first)


def test_explicit_canonical_machine_and_eligible_repository_are_derived(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    result = collect(
        fixture,
        machine_id="vaultnode",
        machine_role="canonical_evidence_host",
        authority_basis="operator-confirmed-vaultnode",
        assert_canonical_machine=True,
    )
    assert result["result"] == "pass"
    assert result["manifest"]["authority_status"] == "CANONICAL"
    assert result["validation"]["canonical_eligible"] is True


def test_static_runtime_identity_is_projected_without_live_proof(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    metadata = base_metadata(runtime_requested=True)
    result = generate_manifest(fixture["root"], hostname="fixture-host", metadata=metadata, **runtime_kwargs(fixture))
    assert result["result"] == "pass"
    assert result["manifest"]["runtime"]["supported_profile"] == "v1-local-core-web-mcp"
    assert result["manifest"]["runtime"]["migration_head"] == "head-a"
    assert result["manifest"]["proof_class"] == "CURRENT_TEST_PROOF"


def test_current_live_proof_is_rejected_without_live_inspection(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    metadata = base_metadata(runtime_requested=True)
    metadata["proof_class"] = "CURRENT_LIVE_PROOF"
    result = generate_manifest(fixture["root"], hostname="fixture-host", metadata=metadata, **runtime_kwargs(fixture))
    assert result["result"] == "error"
    assert result["reason_codes"] == ["live_proof_not_supported"]


def test_artifacts_are_hashed_and_claim_references_are_resolved(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    metadata = base_metadata(runtime_requested=False)
    metadata["artifacts"] = [
        {
            "artifact_id": "proof-a",
            "path": "proofs/proof.txt",
            "media_type": "text/plain",
            "artifact_role": "fixture-proof",
        }
    ]
    metadata["claims"] = {
        "supported": [
            {
                "claim_id": "identity-observed",
                "statement": "The repository identity was observed.",
                "scope": "fixture",
                "evidence_refs": ["execution:fixture-suite", "proof-a"],
                "reason": "Bounded local observation.",
            }
        ],
        "disproved": [],
        "unresolved": [],
    }
    result = generate_manifest(fixture["root"], hostname="fixture-host", metadata=metadata)
    assert result["result"] == "pass"
    artifact = result["manifest"]["artifacts"][0]
    assert artifact["sha256"] == hashlib.sha256(b"fixture proof\n").hexdigest()
    assert result["manifest"]["claims"]["supported"][0]["evidence_refs"] == ["execution:fixture-suite", "proof-a"]


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("execution", {"outcome": "PASS", "suite_id": "fixture-suite", "commands": ["fixture"], "started_at": "2026-07-13T15:00:00Z", "completed_at": "2026-07-13T15:00:01Z", "exit_code": 1, "summary": "bad"}, "execution_outcome_inconsistent"),
        ("artifacts", [{"artifact_id": "proof-a", "path": "../outside.txt", "media_type": "text/plain", "artifact_role": "proof"}], "artifact_path_parent_traversal"),
        ("claims", {"supported": [{"claim_id": "bad", "statement": "bad", "scope": "fixture", "evidence_refs": ["summary-only"], "reason": "bad"}], "disproved": [], "unresolved": []}, "claim_evidence_reference_unresolved"),
        ("relationships", {"supersedes": ["same"], "contradicts": ["same"], "derived_from": []}, "relationship_bucket_conflict"),
    ],
)
def test_invalid_metadata_fails_closed(tmp_path: Path, field: str, value: object, reason: str) -> None:
    fixture = make_fixture(tmp_path)
    metadata = base_metadata(runtime_requested=False)
    metadata[field] = value
    result = generate_manifest(fixture["root"], hostname="fixture-host", metadata=metadata)
    assert result["result"] == "error"
    assert result["reason_codes"] == [reason]


def test_caller_evidence_id_and_secret_input_are_not_echoed(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    metadata = base_metadata(runtime_requested=False)
    metadata["evidence_id"] = "caller-selected"
    result = generate_manifest(fixture["root"], metadata=metadata)
    assert result["reason_codes"] == ["caller_evidence_id_forbidden"]
    secret = "super-secret-value"
    metadata = base_metadata(runtime_requested=False)
    metadata["secret"] = secret
    result = generate_manifest(fixture["root"], metadata=metadata)
    assert result["reason_codes"] == ["forbidden_secret_input"]
    assert secret not in json.dumps(result)


def test_repository_identity_incompleteness_is_fail_closed(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    git(fixture["root"], "branch", "--unset-upstream")
    result = collect(fixture)
    assert result["result"] == "ineligible"
    assert "missing_upstream" in result["reason_codes"]
    assert "repository_identity_incomplete" in result["reason_codes"]


def test_producer_does_not_mutate_git_or_tracked_files(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    before = {
        "head": git(fixture["root"], "rev-parse", "HEAD"),
        "refs": git(fixture["root"], "show-ref"),
        "status": git(fixture["root"], "status", "--porcelain=v1"),
        "contents": (fixture["root"] / "proofs" / "proof.txt").read_bytes(),
    }
    result = collect(fixture)
    after = {
        "head": git(fixture["root"], "rev-parse", "HEAD"),
        "refs": git(fixture["root"], "show-ref"),
        "status": git(fixture["root"], "status", "--porcelain=v1"),
        "contents": (fixture["root"] / "proofs" / "proof.txt").read_bytes(),
    }
    assert result["result"] == "pass"
    assert before == after


def test_cli_is_stdout_first_and_uses_stable_json(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    args = [
        sys.executable,
        str(SCRIPT),
        "--repo",
        str(fixture["root"]),
        "--metadata-input",
        "manifest-input.json",
        "--machine-id",
        "developer-laptop",
        "--machine-role",
        "provisional_development_host",
        "--authority-basis",
        "operator-not-asserted",
        "--no-runtime-identity",
    ]
    first = subprocess.run(args, check=False, text=True, capture_output=True)
    second = subprocess.run(args, check=False, text=True, capture_output=True)
    assert first.returncode == 0
    assert first.stdout == second.stdout
    parsed = json.loads(first.stdout)
    assert parsed["result"] == "pass"
    assert parsed["manifest"]["authority_status"] == "PROVISIONAL"
