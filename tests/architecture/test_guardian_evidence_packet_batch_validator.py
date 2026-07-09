"""Tests for the Guardian Evidence Packet batch validator script.

Tests the local validate_evidence_packets.py batch validator against the
default fixtures directory and synthetic fixture directories.

Do not run Docker in automated tests.
Do not require /Volumes/Dev_SSD/Codex-Runner to exist.
Do not call command bus.
Do not invoke codexrun.
Do not write receipts.
Do not mutate repo files.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
BATCH_SCRIPT = ROOT / "scripts" / "guardian" / "validate_evidence_packets.py"
SINGLE_SCRIPT = ROOT / "scripts" / "guardian" / "validate_evidence_packet.py"
FIXTURE = (
    ROOT / "docs" / "architecture" / "fixtures"
    / "guardian-evidence-packet.codex-runner-bridge-proof-chain.v1.json"
)


def _run(*args: str, **kwargs) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(BATCH_SCRIPT), *args]
    return subprocess.run(cmd, capture_output=True, text=True, **kwargs)


# ---------------------------------------------------------------------------
# Script existence and imports
# ---------------------------------------------------------------------------

def test_script_exists() -> None:
    assert BATCH_SCRIPT.exists()


def test_script_no_runtime_imports() -> None:
    source = BATCH_SCRIPT.read_text()
    forbidden = (
        "docker", "requests", "httpx", "subprocess", "sqlite3",
        "psycopg", "sqlalchemy", "fastapi", "guardian.",
    )
    for mod in forbidden:
        assert mod not in source, f"Script must not import {mod}"


def test_script_uses_stdlib_only() -> None:
    source = BATCH_SCRIPT.read_text()
    lines = [line for line in source.splitlines()
             if line.strip().startswith(("import ", "from "))]
    for line in lines:
        stripped = line.strip()
        allowed_prefixes = ("import json", "import argparse", "import sys",
                            "import os", "from datetime", "from pathlib",
                            "from __future__", "from typing")
        if not any(stripped.startswith(p) for p in allowed_prefixes):
            if "validate_evidence_packet" in stripped:
                continue  # allowed: import of sibling module
            pytest.fail(f"Script may have non-stdlib import: {stripped}")


# ---------------------------------------------------------------------------
# Default fixtures directory
# ---------------------------------------------------------------------------

def test_batch_default_fixtures_exits_0() -> None:
    proc = _run("--json")
    assert proc.returncode == 0


def test_batch_default_fixtures_result_shape() -> None:
    proc = _run("--json")
    data = json.loads(proc.stdout)
    assert data["schema_version"] == "guardian_evidence_packet_batch_validation_result.v1"
    assert "fixtures_dir" in data
    assert "docs/architecture/fixtures" in data["fixtures_dir"]
    assert "matched_count" in data
    assert data["matched_count"] >= 1
    assert data["result"] in ("pass", "pass_with_warnings", "fail")
    assert "packet_results" in data
    assert "issue_count" in data
    assert "error_count" in data
    assert "warning_count" in data
    assert "checked_at" in data
    assert "checked_by" in data
    assert "limits" in data


def test_batch_matched_equals_results_len() -> None:
    proc = _run("--json")
    data = json.loads(proc.stdout)
    assert data["matched_count"] == len(data["packet_results"])


def test_batch_issue_count_equals_total() -> None:
    proc = _run("--json")
    data = json.loads(proc.stdout)
    total = sum(r.get("issue_count", 0) for r in data["packet_results"])
    assert data["issue_count"] == total


def test_batch_warning_count_correct() -> None:
    proc = _run("--json")
    data = json.loads(proc.stdout)
    total = sum(
        1 for r in data["packet_results"]
        for i in r.get("issues", []) if i.get("severity") == "warning"
    )
    assert data["warning_count"] == total


def test_batch_error_count_correct() -> None:
    proc = _run("--json")
    data = json.loads(proc.stdout)
    total = sum(
        1 for r in data["packet_results"]
        for i in r.get("issues", []) if i.get("severity") == "error"
    )
    assert data["error_count"] == total


def test_batch_result_pass_or_warn() -> None:
    proc = _run("--json")
    data = json.loads(proc.stdout)
    assert data["result"] in ("pass", "pass_with_warnings")


def test_batch_includes_bridge_fixture() -> None:
    proc = _run("--json")
    data = json.loads(proc.stdout)
    refs = [r.get("validated_packet_ref", "") for r in data["packet_results"]]
    assert any("guardian-evidence-packet.codex-runner-bridge-proof-chain" in r for r in refs)


def test_batch_includes_both_current_fixtures() -> None:
    proc = _run("--json")
    data = json.loads(proc.stdout)
    assert data["matched_count"] == 2
    refs = [r.get("validated_packet_ref", "") for r in data["packet_results"]]
    assert any("guardian-evidence-packet.codex-runner-bridge-proof-chain" in r for r in refs)
    assert any("guardian-evidence-packet.local-validator-toolchain" in r for r in refs)


def test_batch_has_no_runtime_service_imports() -> None:
    source = BATCH_SCRIPT.read_text().lower()
    for token in ("docker", "requests", "httpx", "subprocess", "sqlite3", "psycopg", "sqlalchemy", "fastapi", "command_bus", "codex_runner_bridge"):
        assert token not in source


def test_batch_preserves_content_hash_warnings() -> None:
    proc = _run("--json")
    data = json.loads(proc.stdout)
    all_codes = [
        i["code"] for r in data["packet_results"]
        for i in r.get("issues", [])
    ]
    assert "content_hash_missing" in all_codes


# ---------------------------------------------------------------------------
# Synthetic fixture directories
# ---------------------------------------------------------------------------

def _minimal_packet() -> dict:
    return {
        "schema_version": "guardian_evidence_packet.v1",
        "packet_id": "test",
        "created_at": "2026-01-01T00:00:00Z",
        "source_domain": "test",
        "evidence_class": "preflight_proof_chain",
        "review_depth": "medium",
        "subject": {"title": "test"},
        "reducer_profile_ref": "test",
        "raw_evidence_refs": [],
        "reduced_summary": "test",
        "claim_ledger": [],
        "authority_state": {
            "guardian_operational": False, "plan_execution_allowed": False,
            "pi_loop_invocation_allowed": False, "codexify_ingestion_allowed": False,
            "durable_mutation_allowed": False, "provider_execution_allowed": False,
            "patch_application_allowed": False, "dispatch_allowed": False,
            "merge_allowed": False,
        },
        "invariant_checks": [],
        "uncertainty": [{"uncertainty_id": "u1", "description": "test", "severity": "low",
                         "missing_evidence": [], "resolution_options": []}],
        "forbidden_interpretations": [{"interpretation_id": "f1", "statement": "test"}],
        "next_gate_options": [{"gate_id": "g1", "description": "test", "prerequisites": [], "risk": "low"}],
        "recommended_next_gate": "g1",
        "loop_policy": {
            "bounded": True, "review_depth": "medium", "self_check_passes": 1,
            "recursive_autonomous_loop_allowed": False,
            "adversarial_review_required": False, "missing_proof_ledger_required": False,
        },
        "provenance": {"reducer_version": "v1", "profile_id": "p1", "input_artifact_ids": []},
        "limits": {"max_source_artifacts": 10, "summary_budget_tokens": 100,
                   "artifacts_consumed": 0, "tokens_consumed": None},
        "boundary_label": "PREFLIGHT ONLY\nNO PI LOOP INVOCATION\nNO SOURCE MUTATION\nNO CODEXIFY INGESTION",
    }


def test_batch_exits_1_when_packet_fails(tmp_path) -> None:
    p = tmp_path / "guardian-evidence-packet-fail.json"
    packet = _minimal_packet()
    packet["review_depth"] = "extreme"  # triggers error
    p.write_text(json.dumps(packet))
    proc = _run("--fixtures-dir", str(tmp_path), "--json")
    assert proc.returncode == 1
    data = json.loads(proc.stdout)
    assert data["result"] == "fail"


def test_batch_exits_0_when_warnings_only(tmp_path) -> None:
    p = tmp_path / "guardian-evidence-packet-warn.json"
    packet = _minimal_packet()
    packet["uncertainty"] = []  # triggers warning for high depth
    packet["review_depth"] = "high"
    p.write_text(json.dumps(packet))
    proc = _run("--fixtures-dir", str(tmp_path), "--json")
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data["result"] == "pass_with_warnings"


def test_batch_exits_1_when_no_matching_fixtures(tmp_path) -> None:
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    proc = _run("--fixtures-dir", str(empty_dir), "--json")
    assert proc.returncode == 1
    data = json.loads(proc.stdout)
    assert data["result"] == "fail"
    assert data["matched_count"] == 0


def test_batch_uses_deterministic_sort(tmp_path) -> None:
    paths = [
        tmp_path / "guardian-evidence-packet-c.json",
        tmp_path / "guardian-evidence-packet-a.json",
        tmp_path / "guardian-evidence-packet-b.json",
    ]
    for path in paths:
        path.write_text(json.dumps(_minimal_packet()))
    proc = _run("--fixtures-dir", str(tmp_path), "--json")
    data = json.loads(proc.stdout)
    refs = [r.get("validated_packet_ref", "") for r in data["packet_results"]]
    assert refs == sorted(refs), f"Results not sorted: {refs}"


def test_batch_does_not_write_files(tmp_path) -> None:
    p = tmp_path / "guardian-evidence-packet-test.json"
    p.write_text(json.dumps(_minimal_packet()))
    before = set(str(x) for x in tmp_path.rglob("*"))
    _run("--fixtures-dir", str(tmp_path), "--json")
    after = set(str(x) for x in tmp_path.rglob("*"))
    assert before == after, "Batch validator must not write files"


# ---------------------------------------------------------------------------
# Single-validator regression
# ---------------------------------------------------------------------------

def test_single_validator_still_works() -> None:
    proc = subprocess.run(
        [sys.executable, str(SINGLE_SCRIPT), str(FIXTURE), "--json"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data["result"] in ("pass", "pass_with_warnings")


def test_single_validator_cli_unchanged() -> None:
    # Verify --json flag still works
    proc = subprocess.run(
        [sys.executable, str(SINGLE_SCRIPT), str(FIXTURE), "--json"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert "schema_version" in data
    assert data["result"] in ("pass", "pass_with_warnings")
