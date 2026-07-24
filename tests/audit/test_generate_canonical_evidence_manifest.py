"""Focused tests for the bounded canonical evidence manifest producer."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

import scripts.audit.generate_canonical_evidence_manifest as producer_module
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
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout.strip()


def migration(revision: str, down_revision: str | None = None) -> str:
    return f'''"""fixture migration."""
revision = "{revision}"
down_revision = {down_revision!r}
'''


def make_fixture(tmp_path: Path) -> dict[str, Path]:
    root = tmp_path / "repo"
    remote = tmp_path / "remote.git"
    subprocess.run(
        ["git", "init", "--bare", str(remote)], check=True, capture_output=True
    )
    subprocess.run(
        ["git", "init", "-b", "main", str(root)],
        check=True,
        capture_output=True,
    )
    git(root, "config", "user.email", "test@example.invalid")
    git(root, "config", "user.name", "Test User")
    profile_dir = root / "config" / "supported_profiles"
    migration_dir = root / "guardian" / "db" / "migrations" / "versions"
    artifact_dir = root / "proofs"
    profile_dir.mkdir(parents=True)
    migration_dir.mkdir(parents=True)
    artifact_dir.mkdir(parents=True)
    (profile_dir / "v1-local-core-web-mcp.yaml").write_text(
        PROFILE, encoding="utf-8"
    )
    compose = root / "docker-compose.yml"
    compose.write_text(
        "name: codexify\nservices:\n  backend: {}\n  db: {}\n  redis: {}\n",
        encoding="utf-8",
    )
    (migration_dir / "a_revision.py").write_text(
        migration("head-a"), encoding="utf-8"
    )
    artifact = artifact_dir / "proof.txt"
    artifact.write_text("fixture proof\n", encoding="utf-8")
    gitignore = root / ".gitignore"
    gitignore.write_text(
        "live-proof-receipt.json\nreceipt-link.json\n", encoding="utf-8"
    )
    metadata_path = root / "manifest-input.json"
    metadata_path.write_text(
        json.dumps(base_metadata(runtime_requested=False), indent=2) + "\n",
        encoding="utf-8",
    )
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
        "relationships": {
            "supersedes": [],
            "contradicts": [],
            "derived_from": [],
        },
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


def test_provisional_manifest_is_deterministic_and_validated(
    tmp_path: Path,
) -> None:
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


def test_explicit_canonical_machine_and_eligible_repository_are_derived(
    tmp_path: Path,
) -> None:
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


def test_static_runtime_identity_is_projected_without_live_proof(
    tmp_path: Path,
) -> None:
    fixture = make_fixture(tmp_path)
    metadata = base_metadata(runtime_requested=True)
    result = generate_manifest(
        fixture["root"],
        hostname="fixture-host",
        metadata=metadata,
        **runtime_kwargs(fixture),
    )
    assert result["result"] == "pass"
    assert (
        result["manifest"]["runtime"]["supported_profile"]
        == "v1-local-core-web-mcp"
    )
    assert result["manifest"]["runtime"]["migration_head"] == "head-a"
    assert result["manifest"]["proof_class"] == "CURRENT_TEST_PROOF"


def test_live_proof_without_receipt_path_fails_closed(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    metadata = base_metadata(runtime_requested=True)
    metadata["proof_class"] = "CURRENT_LIVE_PROOF"
    result = generate_manifest(
        fixture["root"],
        hostname="fixture-host",
        metadata=metadata,
        **runtime_kwargs(fixture),
    )
    assert result["result"] == "error"
    assert result["reason_codes"] == ["live_proof_receipt_required"]


def test_artifacts_are_hashed_and_claim_references_are_resolved(
    tmp_path: Path,
) -> None:
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
    result = generate_manifest(
        fixture["root"], hostname="fixture-host", metadata=metadata
    )
    assert result["result"] == "pass"
    artifact = result["manifest"]["artifacts"][0]
    assert artifact["sha256"] == hashlib.sha256(b"fixture proof\n").hexdigest()
    assert result["manifest"]["claims"]["supported"][0]["evidence_refs"] == [
        "execution:fixture-suite",
        "proof-a",
    ]


def test_generated_evidence_ids_are_valid_lineage_references(
    tmp_path: Path,
) -> None:
    fixture = make_fixture(tmp_path)
    first = collect(fixture)
    first_id = first["manifest"]["evidence_id"]
    second_metadata = base_metadata(runtime_requested=False)
    second_metadata["relationships"] = {
        "supersedes": [],
        "contradicts": [],
        "derived_from": [first_id],
    }
    second = generate_manifest(
        fixture["root"], hostname="fixture-host", metadata=second_metadata
    )
    assert second["result"] == "pass"
    assert second["manifest"]["relationships"]["derived_from"] == [first_id]
    assert second["manifest"]["evidence_id"] != first_id


def test_only_the_newly_generated_id_is_rejected_as_self_reference(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = make_fixture(tmp_path)
    generated_id = "evidence-sha256-" + "a" * 64
    monkeypatch.setattr(
        producer_module, "_evidence_id", lambda manifest: generated_id
    )
    metadata = base_metadata(runtime_requested=False)
    metadata["relationships"] = {
        "supersedes": [],
        "contradicts": [],
        "derived_from": [generated_id],
    }
    result = generate_manifest(
        fixture["root"], hostname="fixture-host", metadata=metadata
    )
    assert result["result"] == "error"
    assert result["reason_codes"] == ["relationship_self_reference"]


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        (
            "execution",
            {
                "outcome": "PASS",
                "suite_id": "fixture-suite",
                "commands": ["fixture"],
                "started_at": "2026-07-13T15:00:00Z",
                "completed_at": "2026-07-13T15:00:01Z",
                "exit_code": 1,
                "summary": "bad",
            },
            "execution_outcome_inconsistent",
        ),
        (
            "artifacts",
            [
                {
                    "artifact_id": "proof-a",
                    "path": "../outside.txt",
                    "media_type": "text/plain",
                    "artifact_role": "proof",
                }
            ],
            "artifact_path_parent_traversal",
        ),
        (
            "claims",
            {
                "supported": [
                    {
                        "claim_id": "bad",
                        "statement": "bad",
                        "scope": "fixture",
                        "evidence_refs": ["summary-only"],
                        "reason": "bad",
                    }
                ],
                "disproved": [],
                "unresolved": [],
            },
            "claim_evidence_reference_unresolved",
        ),
        (
            "relationships",
            {
                "supersedes": ["same"],
                "contradicts": ["same"],
                "derived_from": [],
            },
            "relationship_bucket_conflict",
        ),
    ],
)
def test_invalid_metadata_fails_closed(
    tmp_path: Path, field: str, value: object, reason: str
) -> None:
    fixture = make_fixture(tmp_path)
    metadata = base_metadata(runtime_requested=False)
    metadata[field] = value
    result = generate_manifest(
        fixture["root"], hostname="fixture-host", metadata=metadata
    )
    assert result["result"] == "error"
    assert result["reason_codes"] == [reason]


@pytest.mark.parametrize(
    "secret_value",
    [
        "postgresql://user:password@db.example.invalid/audit",
        "redis://user:password@cache.example.invalid/0",
        "mysql://user:password@db.example.invalid/audit",
    ],
)
def test_secret_input_is_rejected_and_not_echoed(
    tmp_path: Path, secret_value: str
) -> None:
    fixture = make_fixture(tmp_path)
    metadata = base_metadata(runtime_requested=False)
    metadata["execution"]["summary"] = f"Observed {secret_value} during a test."
    result = generate_manifest(fixture["root"], metadata=metadata)
    assert result["reason_codes"] == ["forbidden_secret_input"]
    assert secret_value not in json.dumps(result)


def test_secret_database_url_in_claim_is_rejected_and_not_echoed(
    tmp_path: Path,
) -> None:
    fixture = make_fixture(tmp_path)
    secret_value = "postgresql://user:password@db.example.invalid/audit"
    metadata = base_metadata(runtime_requested=False)
    metadata["claims"] = {
        "supported": [
            {
                "claim_id": "secret",
                "statement": secret_value,
                "scope": "fixture",
                "evidence_refs": ["execution:fixture-suite"],
                "reason": "not accepted",
            }
        ],
        "disproved": [],
        "unresolved": [],
    }
    result = generate_manifest(fixture["root"], metadata=metadata)
    assert result["reason_codes"] == ["forbidden_secret_input"]
    assert secret_value not in json.dumps(result)


def test_diagnostic_working_path_is_rejected_as_nonportable(
    tmp_path: Path,
) -> None:
    fixture = make_fixture(tmp_path)
    result = collect(fixture, diagnostic_working_path=True)
    assert result["result"] == "error"
    assert result["reason_codes"] == ["nonportable_absolute_path"]


def test_caller_evidence_id_is_rejected(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    result = generate_manifest(
        fixture["root"],
        metadata=base_metadata(runtime_requested=False),
        evidence_id="caller-selected",
    )
    assert result["reason_codes"] == ["caller_evidence_id_forbidden"]


def test_repository_identity_incompleteness_is_fail_closed(
    tmp_path: Path,
) -> None:
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


# ---------------------------------------------------------------------------
# Live proof receipt helpers
# ---------------------------------------------------------------------------

from scripts.audit.collect_canonical_live_proof_receipt import (  # noqa: E402
    receipt_id as compute_receipt_id,
)


def _receipt_json(
    fixture: dict[str, Path],
    *,
    authority_status: str = "PROVISIONAL",
    execution_outcome: str = "PASS",
    machine_overrides: dict[str, Any] | None = None,
    repo_overrides: dict[str, Any] | None = None,
    runtime_overrides: dict[str, Any] | None = None,
    target_overrides: dict[str, Any] | None = None,
    receipt_id_override: str | None = None,
) -> dict[str, Any]:
    """Build a minimal but valid live proof receipt for a fixture."""
    root = fixture["root"]
    head = git(root, "rev-parse", "HEAD")
    upstream = git(root, "rev-parse", "@{u}")
    repo_root_id = git(root, "rev-parse", "--show-toplevel")
    repo_root_id = f"git:{hashlib.sha256(repo_root_id.encode()).hexdigest()}"

    machine = {
        "machine_id": "local",
        "machine_role": "provisional_development_host",
        "hostname": "fixture-host",
        "authority_basis": "operator_not_asserted",
    }
    if machine_overrides:
        machine.update(machine_overrides)

    repo = {
        "repository_root_identity": repo_root_id,
        "branch": "main",
        "commit_sha": head,
        "upstream_sha": upstream,
        "dirty": False,
        "worktree_identity": f"worktree:{hashlib.sha256(str(root).encode()).hexdigest()}",
    }
    if repo_overrides:
        repo.update(repo_overrides)

    runtime_base = {
        "supported_profile": "v1-local-core-web-mcp",
        "effective_config_hash": "e" * 64,
        "compose_project": "codexify-audit",
        "compose_files": ["docker-compose.yml"],
        "migration_head": "head-a",
        "service_identities": ["backend"],
        "required_services": ["backend"],
        "optional_services": ["redis"],
    }
    if runtime_overrides:
        runtime_base.update(runtime_overrides)

    target = {
        "compose_project": "codexify-audit",
        "project_role": "audit",
        "audit_project": "codexify-audit",
        "serving_project": "codexify-serving",
        "compose_environment_file": None,
    }
    if target_overrides:
        target.update(target_overrides)

    receipt = {
        "schema_version": "canonical_live_proof_receipt.v1",
        "receipt_id": "",
        "suite_id": "supported_compose_live_health.v1",
        "proof_class": "CURRENT_LIVE_PROOF",
        "authority_status": authority_status,
        "execution_outcome": execution_outcome,
        "created_at": "2026-07-15T12:00:00Z",
        "started_at": "2026-07-15T12:00:00Z",
        "completed_at": "2026-07-15T12:00:05Z",
        "machine": machine,
        "repository": repo,
        "runtime": runtime_base,
        "target": target,
        "docker": {"client_version": "27.1.1", "server_version": "27.1.1"},
        "services": [
            {
                "service": "backend",
                "required": True,
                "lifecycle": "long_running",
                "container_identity": "codexify-audit-backend-1",
                "image_id": "sha256:" + "b" * 64,
                "image_digest": None,
                "state": "running",
                "health_status": "healthy",
                "exit_code": 0,
                "observation_result": "PASS",
                "reason_codes": [],
            }
        ],
        "probes": [
            {
                "probe_id": "api_ping",
                "method": "GET",
                "path": "/ping",
                "status_code": 200,
                "started_at": "2026-07-15T12:00:01Z",
                "completed_at": "2026-07-15T12:00:01Z",
                "duration_ms": 1,
                "outcome": "PASS",
                "response_body_sha256": hashlib.sha256(b"pong\n").hexdigest(),
                "projection": {},
                "reason_codes": [],
            }
        ],
        "commands": [
            ["docker", "version", "--format", "json"],
            [
                "docker",
                "compose",
                "-f",
                "docker-compose.yml",
                "-p",
                "codexify-audit",
                "ps",
                "--all",
                "--format",
                "json",
            ],
        ],
        "reason_codes": [],
    }
    if receipt_id_override is not None:
        receipt["receipt_id"] = receipt_id_override
    else:
        receipt["receipt_id"] = compute_receipt_id(receipt)
    return receipt


def write_receipt(
    fixture: dict[str, Path], **kwargs: Any
) -> tuple[str, dict[str, Any]]:
    """Write a receipt to the fixture repo and return the relative path and receipt dict.

    Collects identity AFTER writing so dirty/untracked state matches what the producer sees.
    Also collects actual runtime identity for accurate comparison.
    """
    from scripts.audit.collect_canonical_evidence_identity import (
        collect_identity,
    )
    from scripts.audit.collect_canonical_runtime_identity import (
        collect_runtime_identity,
    )

    machine_overrides = kwargs.pop("machine_overrides", None) or {}
    repo_overrides = kwargs.pop("repo_overrides", None) or {}
    runtime_overrides = kwargs.pop("runtime_overrides", None) or {}
    target_overrides = kwargs.pop("target_overrides", None) or {}

    # Build a draft receipt first, write it, then collect identity with receipt present
    draft = _receipt_json(fixture, **kwargs)
    receipt_path = fixture["root"] / "live-proof-receipt.json"
    receipt_path.write_text(
        json.dumps(draft, indent=2, sort_keys=True), encoding="utf-8"
    )

    # Now collect identity WITH the receipt file present (repo may be dirty)
    identity = collect_identity(fixture["root"], hostname="fixture-host")
    collected_machine = identity.get("machine", {})
    full_machine = {
        "machine_id": collected_machine.get("machine_id", "local"),
        "machine_role": collected_machine.get(
            "machine_role", "provisional_development_host"
        ),
        "hostname": collected_machine.get("hostname", "fixture-host"),
        "authority_basis": collected_machine.get(
            "authority_basis", "operator_not_asserted"
        ),
    }
    full_machine.update(machine_overrides)

    collected_repo = identity.get("repository", {})
    full_repo = {
        "repository_root_identity": collected_repo.get(
            "repository_root_identity", ""
        ),
        "branch": collected_repo.get("branch", "main"),
        "commit_sha": collected_repo.get("commit_sha", ""),
        "upstream_sha": collected_repo.get("upstream_sha", ""),
        "dirty": collected_repo.get("dirty", False),
        "worktree_identity": collected_repo.get("worktree_identity", ""),
    }
    full_repo.update(repo_overrides)

    # Collect actual runtime identity
    rt = collect_runtime_identity(
        fixture["root"],
        profile_name="v1-local-core-web-mcp",
        profiles_dir=fixture["profile_dir"],
        compose_files=["docker-compose.yml"],
        audit_project="codexify-audit",
        migration_dir=fixture["migration_dir"],
    )
    collected_rt = rt.get("runtime", {})
    full_runtime = {
        "supported_profile": collected_rt.get(
            "supported_profile", "v1-local-core-web-mcp"
        ),
        "effective_config_hash": collected_rt.get("effective_config_hash", ""),
        "compose_project": collected_rt.get(
            "compose_project", "codexify-audit"
        ),
        "compose_files": collected_rt.get(
            "compose_files", ["docker-compose.yml"]
        ),
        "migration_head": collected_rt.get("migration_head", "head-a"),
        "service_identities": collected_rt.get(
            "service_identities", ["backend"]
        ),
        "required_services": collected_rt.get("compose_identity", {}).get(
            "required_services", ["backend"]
        ),
        "optional_services": collected_rt.get("compose_identity", {}).get(
            "optional_services", ["redis"]
        ),
    }
    full_runtime.update(runtime_overrides)

    receipt = _receipt_json(
        fixture,
        machine_overrides=full_machine,
        repo_overrides=full_repo,
        runtime_overrides=full_runtime,
        target_overrides=target_overrides,
        **kwargs,
    )
    receipt_path.write_text(
        json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8"
    )
    return "live-proof-receipt.json", receipt


def live_proof_metadata(
    receipt_path: str, *, runtime_requested: bool = True
) -> dict[str, Any]:
    return {
        "created_at": "2026-07-15T12:00:00-04:00",
        "proof_class": "CURRENT_LIVE_PROOF",
        "freshness_status": "CURRENT",
        "disposition": "ACCEPTED",
        "runtime_identity_requested": runtime_requested,
        "live_proof_receipt_path": receipt_path,
        "execution": {
            "outcome": "PASS",
            "suite_id": "unused-suite",
            "commands": ["unused"],
            "started_at": "2026-07-15T12:00:00Z",
            "completed_at": "2026-07-15T12:00:05Z",
            "exit_code": 0,
            "summary": "placeholder; will be overridden by receipt.",
        },
        "claims": {"supported": [], "disproved": [], "unresolved": []},
        "artifacts": [],
        "relationships": {
            "supersedes": [],
            "contradicts": [],
            "derived_from": [],
        },
    }


# ---------------------------------------------------------------------------
# Live proof receipt integration tests
# ---------------------------------------------------------------------------


def test_valid_canonical_pass_receipt_produces_deterministic_manifest(
    tmp_path: Path,
) -> None:
    fixture = make_fixture(tmp_path)
    receipt_path, receipt = write_receipt(
        fixture,
        authority_status="CANONICAL",
        machine_overrides={
            "machine_id": "vaultnode",
            "machine_role": "canonical_evidence_host",
            "hostname": "fixture-host",
            "authority_basis": "operator-confirmed-vaultnode",
        },
    )
    kwargs = runtime_kwargs(fixture)
    metadata = live_proof_metadata(receipt_path)
    first = generate_manifest(
        fixture["root"],
        hostname="fixture-host",
        metadata=metadata,
        machine_id="vaultnode",
        machine_role="canonical_evidence_host",
        authority_basis="operator-confirmed-vaultnode",
        assert_canonical_machine=True,
        **kwargs,
    )
    second = generate_manifest(
        fixture["root"],
        hostname="fixture-host",
        metadata=metadata,
        machine_id="vaultnode",
        machine_role="canonical_evidence_host",
        authority_basis="operator-confirmed-vaultnode",
        assert_canonical_machine=True,
        **kwargs,
    )
    assert first == second
    assert first["result"] in ("pass", "ineligible")
    assert first["manifest"] is not None
    assert first["validation"]["result"] == "pass"
    assert first["manifest"]["authority_status"] == "CANONICAL"
    assert first["manifest"]["proof_class"] == "CURRENT_LIVE_PROOF"
    assert first["manifest"]["execution_outcome"] == "PASS"
    assert first["manifest"]["execution"]["exit_code"] == 0
    assert receipt["receipt_id"] in first["manifest"]["execution"]["summary"]
    # receipt is an artifact
    artifact = first["manifest"]["artifacts"][0]
    assert artifact["artifact_id"] == receipt["receipt_id"]
    assert artifact["artifact_role"] == "canonical_live_proof_receipt"
    assert artifact["media_type"] == "application/json"
    assert artifact["path"] == receipt_path
    # lineage
    assert (
        receipt["receipt_id"]
        in first["manifest"]["relationships"]["derived_from"]
    )
    # evidence_id
    assert first["manifest"]["evidence_id"].startswith("evidence-sha256-")


def test_valid_provisional_pass_receipt_produces_provisional_manifest(
    tmp_path: Path,
) -> None:
    fixture = make_fixture(tmp_path)
    receipt_path, receipt = write_receipt(
        fixture, authority_status="PROVISIONAL"
    )
    kwargs = runtime_kwargs(fixture)
    metadata = live_proof_metadata(receipt_path)
    result = generate_manifest(
        fixture["root"], hostname="fixture-host", metadata=metadata, **kwargs
    )
    assert result["result"] in ("pass", "ineligible")
    assert result["manifest"] is not None
    assert result["manifest"]["authority_status"] == "PROVISIONAL"
    assert result["manifest"]["proof_class"] == "CURRENT_LIVE_PROOF"


def test_missing_receipt_input_fails_closed(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    metadata = base_metadata(runtime_requested=True)
    metadata["proof_class"] = "CURRENT_LIVE_PROOF"
    result = generate_manifest(
        fixture["root"],
        hostname="fixture-host",
        metadata=metadata,
        **runtime_kwargs(fixture),
    )
    assert result["result"] == "error"
    assert "live_proof_receipt_required" in result["reason_codes"]


def test_missing_receipt_file_fails_closed(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    metadata = live_proof_metadata("nonexistent-receipt.json")
    kwargs = runtime_kwargs(fixture)
    result = generate_manifest(
        fixture["root"], hostname="fixture-host", metadata=metadata, **kwargs
    )
    assert result["result"] == "error"
    assert "live_proof_receipt_not_found" in result["reason_codes"]


def test_invalid_json_receipt_fails_closed(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    receipt_path = fixture["root"] / "bad-receipt.json"
    receipt_path.write_text("not json", encoding="utf-8")
    metadata = live_proof_metadata("bad-receipt.json")
    kwargs = runtime_kwargs(fixture)
    result = generate_manifest(
        fixture["root"], hostname="fixture-host", metadata=metadata, **kwargs
    )
    assert result["result"] == "error"
    assert "live_proof_receipt_schema_invalid" in result["reason_codes"]


def test_schema_invalid_receipt_fails_closed(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    receipt = _receipt_json(fixture)
    del receipt["machine"]  # remove required field
    receipt["receipt_id"] = compute_receipt_id(receipt)
    receipt_path = fixture["root"] / "invalid-receipt.json"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    metadata = live_proof_metadata("invalid-receipt.json")
    kwargs = runtime_kwargs(fixture)
    result = generate_manifest(
        fixture["root"], hostname="fixture-host", metadata=metadata, **kwargs
    )
    assert result["result"] == "error"
    assert "live_proof_receipt_schema_invalid" in result["reason_codes"]


def test_invalid_receipt_id_fails_closed(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    receipt_path, _ = write_receipt(
        fixture, receipt_id_override="live-proof-receipt-sha256-" + "0" * 64
    )
    metadata = live_proof_metadata(receipt_path)
    kwargs = runtime_kwargs(fixture)
    result = generate_manifest(
        fixture["root"], hostname="fixture-host", metadata=metadata, **kwargs
    )
    assert result["result"] == "error"
    assert "live_proof_receipt_id_invalid" in result["reason_codes"]


def test_receipt_byte_change_changes_manifest_evidence_id(
    tmp_path: Path,
) -> None:
    fixture = make_fixture(tmp_path)
    receipt_path, _ = write_receipt(fixture)
    kwargs = runtime_kwargs(fixture)
    metadata = live_proof_metadata(receipt_path)
    first = generate_manifest(
        fixture["root"], hostname="fixture-host", metadata=metadata, **kwargs
    )
    # change receipt bytes
    receipt_file = fixture["root"] / receipt_path
    receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
    receipt["reason_codes"] = ["some_reason"]
    receipt["receipt_id"] = compute_receipt_id(receipt)
    receipt_file.write_text(json.dumps(receipt), encoding="utf-8")
    second = generate_manifest(
        fixture["root"], hostname="fixture-host", metadata=metadata, **kwargs
    )
    assert first["manifest"]["evidence_id"] != second["manifest"]["evidence_id"]
    assert (
        first["manifest"]["artifacts"][0]["sha256"]
        != second["manifest"]["artifacts"][0]["sha256"]
    )


def test_machine_identity_mismatch_fails_closed(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    # receipt has hostname="other-host"; producer collects hostname="fixture-host"
    receipt_path, _ = write_receipt(
        fixture, machine_overrides={"hostname": "other-host"}
    )
    metadata = live_proof_metadata(receipt_path)
    kwargs = runtime_kwargs(fixture)
    result = generate_manifest(
        fixture["root"], hostname="fixture-host", metadata=metadata, **kwargs
    )
    assert result["result"] == "error"
    assert "live_proof_machine_identity_mismatch" in result["reason_codes"]


def test_repository_identity_mismatch_fails_closed(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    receipt_path, _ = write_receipt(
        fixture, repo_overrides={"branch": "other-branch"}
    )
    metadata = live_proof_metadata(receipt_path)
    kwargs = runtime_kwargs(fixture)
    result = generate_manifest(
        fixture["root"], hostname="fixture-host", metadata=metadata, **kwargs
    )
    assert result["result"] == "error"
    assert "live_proof_repository_identity_mismatch" in result["reason_codes"]


def test_commit_mismatch_fails_closed(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    receipt_path, _ = write_receipt(
        fixture, repo_overrides={"commit_sha": "0" * 40}
    )
    metadata = live_proof_metadata(receipt_path)
    kwargs = runtime_kwargs(fixture)
    result = generate_manifest(
        fixture["root"], hostname="fixture-host", metadata=metadata, **kwargs
    )
    assert result["result"] == "error"
    assert "live_proof_commit_mismatch" in result["reason_codes"]


def test_runtime_identity_mismatch_fails_closed(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    receipt_path, _ = write_receipt(
        fixture, runtime_overrides={"compose_files": ["other-compose.yml"]}
    )
    metadata = live_proof_metadata(receipt_path)
    kwargs = runtime_kwargs(fixture)
    result = generate_manifest(
        fixture["root"], hostname="fixture-host", metadata=metadata, **kwargs
    )
    assert result["result"] == "error"
    assert "live_proof_runtime_identity_mismatch" in result["reason_codes"]


def test_effective_config_mismatch_fails_closed(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    receipt_path, _ = write_receipt(
        fixture, runtime_overrides={"effective_config_hash": "f" * 64}
    )
    metadata = live_proof_metadata(receipt_path)
    kwargs = runtime_kwargs(fixture)
    result = generate_manifest(
        fixture["root"], hostname="fixture-host", metadata=metadata, **kwargs
    )
    assert result["result"] == "error"
    assert "live_proof_effective_config_mismatch" in result["reason_codes"]


def test_profile_mismatch_fails_closed(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    receipt_path, _ = write_receipt(
        fixture, runtime_overrides={"supported_profile": "wrong-profile"}
    )
    metadata = live_proof_metadata(receipt_path)
    kwargs = runtime_kwargs(fixture)
    result = generate_manifest(
        fixture["root"], hostname="fixture-host", metadata=metadata, **kwargs
    )
    assert result["result"] == "error"
    assert "live_proof_profile_mismatch" in result["reason_codes"]


def test_compose_project_mismatch_fails_closed(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    receipt_path, _ = write_receipt(
        fixture,
        runtime_overrides={"compose_project": "wrong-project"},
        target_overrides={"compose_project": "wrong-project"},
    )
    metadata = live_proof_metadata(receipt_path)
    kwargs = runtime_kwargs(fixture)
    result = generate_manifest(
        fixture["root"], hostname="fixture-host", metadata=metadata, **kwargs
    )
    assert result["result"] == "error"
    assert "live_proof_compose_project_mismatch" in result["reason_codes"]


def test_role_mismatch_fails_closed(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    receipt_path, _ = write_receipt(
        fixture,
        target_overrides={"project_role": "serving"},
    )
    metadata = live_proof_metadata(receipt_path)
    kwargs = runtime_kwargs(fixture)
    # audit receipt with serving role is inconsistent
    result = generate_manifest(
        fixture["root"], hostname="fixture-host", metadata=metadata, **kwargs
    )
    assert result["result"] == "error"
    assert "live_proof_role_mismatch" in result["reason_codes"]


def test_receipt_authority_mismatch_fails_closed(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    receipt_path, _ = write_receipt(
        fixture, authority_status="CANONICAL"
    )  # receipt is CANONICAL but machine is not vaultnode
    metadata = live_proof_metadata(receipt_path)
    kwargs = runtime_kwargs(fixture)
    result = generate_manifest(
        fixture["root"], hostname="fixture-host", metadata=metadata, **kwargs
    )
    # derived authority is PROVISIONAL, receipt says CANONICAL → mismatch
    assert result["result"] == "error"
    assert "live_proof_authority_ineligible" in result["reason_codes"]


def test_fail_receipt_cannot_become_live_proof(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    receipt_path, _ = write_receipt(fixture, execution_outcome="FAIL")
    metadata = live_proof_metadata(receipt_path)
    kwargs = runtime_kwargs(fixture)
    result = generate_manifest(
        fixture["root"], hostname="fixture-host", metadata=metadata, **kwargs
    )
    assert result["result"] == "error"
    assert "live_proof_receipt_not_pass" in result["reason_codes"]


def test_blocked_receipt_cannot_become_live_proof(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    receipt_path, _ = write_receipt(fixture, execution_outcome="BLOCKED")
    metadata = live_proof_metadata(receipt_path)
    kwargs = runtime_kwargs(fixture)
    result = generate_manifest(
        fixture["root"], hostname="fixture-host", metadata=metadata, **kwargs
    )
    assert result["result"] == "error"
    assert "live_proof_receipt_not_pass" in result["reason_codes"]


def test_error_receipt_cannot_become_live_proof(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    receipt_path, _ = write_receipt(fixture, execution_outcome="ERROR")
    metadata = live_proof_metadata(receipt_path)
    kwargs = runtime_kwargs(fixture)
    result = generate_manifest(
        fixture["root"], hostname="fixture-host", metadata=metadata, **kwargs
    )
    assert result["result"] == "error"
    assert "live_proof_receipt_not_pass" in result["reason_codes"]


def test_absolute_receipt_path_fails_closed(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    receipt_path, _ = write_receipt(fixture)
    abs_path = str(fixture["root"] / receipt_path)
    metadata = live_proof_metadata(abs_path)
    kwargs = runtime_kwargs(fixture)
    result = generate_manifest(
        fixture["root"], hostname="fixture-host", metadata=metadata, **kwargs
    )
    assert result["result"] == "error"
    assert "live_proof_receipt_path_absolute" in result["reason_codes"]


def test_parent_traversal_receipt_path_fails_closed(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    metadata = live_proof_metadata("../outside-receipt.json")
    kwargs = runtime_kwargs(fixture)
    result = generate_manifest(
        fixture["root"], hostname="fixture-host", metadata=metadata, **kwargs
    )
    assert result["result"] == "error"
    assert "live_proof_receipt_path_parent_traversal" in result["reason_codes"]


def test_symlink_receipt_path_fails_closed(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    receipt_path, _ = write_receipt(fixture)
    symlink_path = fixture["root"] / "receipt-link.json"
    symlink_path.symlink_to(fixture["root"] / receipt_path)
    metadata = live_proof_metadata("receipt-link.json")
    kwargs = runtime_kwargs(fixture)
    result = generate_manifest(
        fixture["root"], hostname="fixture-host", metadata=metadata, **kwargs
    )
    assert result["result"] == "error"
    assert "live_proof_receipt_path_symlink" in result["reason_codes"]


def test_deterministic_live_proof_output(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    receipt_path, _ = write_receipt(fixture)
    kwargs = runtime_kwargs(fixture)
    metadata = live_proof_metadata(receipt_path)
    first = generate_manifest(
        fixture["root"], hostname="fixture-host", metadata=metadata, **kwargs
    )
    second = generate_manifest(
        fixture["root"], hostname="fixture-host", metadata=metadata, **kwargs
    )
    assert first == second
    assert first["manifest"]["evidence_id"] == second["manifest"]["evidence_id"]


def test_non_live_proof_classes_remain_backward_compatible(
    tmp_path: Path,
) -> None:
    """Existing non-live proof classes continue to work unchanged."""
    fixture = make_fixture(tmp_path)
    result = collect(fixture, machine_id="developer-laptop")
    assert result["result"] == "pass"
    assert result["manifest"]["proof_class"] == "CURRENT_TEST_PROOF"
    assert result["manifest"]["execution_outcome"] == "PASS"


def test_live_proof_receipt_not_mutated(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    receipt_path, receipt = write_receipt(fixture)
    receipt_file = fixture["root"] / receipt_path
    before = receipt_file.read_bytes()
    kwargs = runtime_kwargs(fixture)
    metadata = live_proof_metadata(receipt_path)
    result = generate_manifest(
        fixture["root"], hostname="fixture-host", metadata=metadata, **kwargs
    )
    after = receipt_file.read_bytes()
    assert result["result"] in ("pass", "ineligible")
    assert result["manifest"] is not None
    assert before == after


def test_pass_receipt_cannot_upgrade_provisional_authority(
    tmp_path: Path,
) -> None:
    """A PASS receipt with CANONICAL authority but non-canonical machine must be rejected."""
    fixture = make_fixture(tmp_path)
    # Receipt claims CANONICAL, but machine ID is not vaultnode
    receipt_path, _ = write_receipt(
        fixture,
        authority_status="CANONICAL",
        machine_overrides={
            "machine_id": "not-vaultnode",
            "machine_role": "provisional_development_host",
        },
    )
    metadata = live_proof_metadata(receipt_path)
    kwargs = runtime_kwargs(fixture)
    result = generate_manifest(
        fixture["root"], hostname="fixture-host", metadata=metadata, **kwargs
    )
    # Machine identity must also match — the machine_id in receipt is "not-vaultnode"
    # but the producer observes "test-machine" from defaults → machine mismatch
    assert result["result"] == "error"
    assert "live_proof_machine_identity_mismatch" in result["reason_codes"]


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
