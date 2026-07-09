"""Tests for the Guardian Evidence Packet static validator script.

Tests the local validate_evidence_packet.py script against the bridge fixture
and synthetic packets, verifying error/warning codes, exit codes, and output
shape — all without requiring Docker, network, or live systems.

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
SCRIPT = ROOT / "scripts" / "guardian" / "validate_evidence_packet.py"
FIXTURE = (
    ROOT / "docs" / "architecture" / "fixtures"
    / "guardian-evidence-packet.codex-runner-bridge-proof-chain.v1.json"
)

ALLOWED_REVIEW_DEPTHS = {"light", "medium", "high", "xhigh"}
ALLOWED_CLAIM_STATUSES = {"supported", "unsupported", "blocked", "inferred", "not_evaluated"}


def _run(*args: str, **kwargs) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(SCRIPT), *args]
    return subprocess.run(cmd, capture_output=True, text=True, **kwargs)


# ---------------------------------------------------------------------------
# Script existence and imports
# ---------------------------------------------------------------------------

def test_script_exists() -> None:
    assert SCRIPT.exists()


def test_script_no_runtime_imports() -> None:
    source = SCRIPT.read_text()
    forbidden = (
        "docker", "requests", "httpx", "subprocess", "sqlite3",
        "psycopg", "sqlalchemy", "fastapi", "guardian.protocol_tokens",
    )
    for mod in forbidden:
        assert mod not in source, f"Script must not import {mod}"


def test_script_uses_stdlib_only() -> None:
    source = SCRIPT.read_text()
    lines = [line for line in source.splitlines() if line.strip().startswith(("import ", "from "))]
    for line in lines:
        # Allow only stdlib and local imports
        stripped = line.strip()
        allowed_prefixes = ("import json", "import argparse", "import sys",
                            "import os", "from datetime", "from pathlib",
                            "from __future__", "from typing",
                            "from guardian.evidence_packets.contracts")
        if not any(stripped.startswith(p) for p in allowed_prefixes):
            pytest.fail(f"Script may have non-stdlib import: {stripped}")


def test_script_uses_backend_packet_contracts_without_duplicate_shape_constants() -> None:
    source = SCRIPT.read_text()
    assert "from guardian.evidence_packets.contracts import" in source
    assert "GUARDIAN_EVIDENCE_PACKET_SCHEMA_VERSION" in source
    assert "STATIC_VALIDATION_RESULT_SCHEMA_VERSION" in source
    assert "BOUNDARY_LABEL" in source
    assert "ALLOWED_REVIEW_DEPTHS" in source
    assert "ALLOWED_CLAIM_STATUSES" in source
    assert "REQUIRED_PACKET_FIELDS" in source
    assert "REQUIRED_AUTHORITY_LOCKS" in source
    assert "SCHEMA_VERSION =" not in source
    assert "RESULT_VERSION =" not in source
    assert "BOUNDARY_LABEL_EXPECTED =" not in source
    assert "ALLOWED_REVIEW_DEPTHS = frozenset" not in source
    assert "REQUIRED_PACKET_FIELDS = (" not in source


def test_validator_issue_codes_remain_local() -> None:
    source = SCRIPT.read_text()
    assert "ISSUE_CODES = frozenset" in source
    assert "guardian.protocol_tokens" not in source


def test_local_validator_fixture_still_validates() -> None:
    proc = _run(str(ROOT / "docs/architecture/fixtures" / "guardian-evidence-packet.local-validator-toolchain.v1.json"), "--json")
    assert proc.returncode == 0


# ---------------------------------------------------------------------------
# Bridge fixture validation
# ---------------------------------------------------------------------------

def test_validate_bridge_fixture_exits_0() -> None:
    proc = _run(str(FIXTURE), "--json")
    assert proc.returncode == 0


def test_validate_bridge_fixture_result_shape() -> None:
    proc = _run(str(FIXTURE), "--json")
    data = json.loads(proc.stdout)
    assert data["schema_version"] == "guardian_evidence_packet_static_validation_result.v1"
    assert data["validator_contract_version"] == "guardian_evidence_packet_static_validator_contract.v1"
    assert data["validated_packet_ref"]
    assert data["result"] in ("pass", "pass_with_warnings", "fail")
    assert "issue_count" in data
    assert "issues" in data
    assert "checked_at" in data
    assert "checked_by" in data
    assert "limits" in data
    assert data["issue_count"] == len(data["issues"])


def test_validate_bridge_fixture_result_is_pass_or_warn() -> None:
    proc = _run(str(FIXTURE), "--json")
    data = json.loads(proc.stdout)
    assert data["result"] in ("pass", "pass_with_warnings")


# ---------------------------------------------------------------------------
# Error: invalid JSON
# ---------------------------------------------------------------------------

def test_invalid_json_exits_1(tmp_path) -> None:
    p = tmp_path / "bad.json"
    p.write_text("not json")
    proc = _run(str(p), "--json")
    assert proc.returncode == 1
    data = json.loads(proc.stdout)
    assert data["result"] == "fail"
    codes = [i["code"] for i in data["issues"]]
    assert "packet_json_invalid" in codes


# ---------------------------------------------------------------------------
# Error: missing required fields
# ---------------------------------------------------------------------------

def test_missing_top_level_field(tmp_path) -> None:
    p = tmp_path / "packet.json"
    packet = {"schema_version": "guardian_evidence_packet.v1"}
    p.write_text(json.dumps(packet))
    proc = _run(str(p), "--json")
    assert proc.returncode == 1
    codes = [i["code"] for i in json.loads(proc.stdout)["issues"]]
    assert "packet_required_field_missing" in codes


# ---------------------------------------------------------------------------
# Error: invalid review_depth
# ---------------------------------------------------------------------------

def test_invalid_review_depth(tmp_path) -> None:
    p = tmp_path / "packet.json"
    packet = _minimal_packet()
    packet["review_depth"] = "extreme"
    p.write_text(json.dumps(packet))
    proc = _run(str(p), "--json")
    assert proc.returncode == 1
    codes = [i["code"] for i in json.loads(proc.stdout)["issues"]]
    assert "review_depth_invalid" in codes


# ---------------------------------------------------------------------------
# Error: missing reducer_profile_ref
# ---------------------------------------------------------------------------

def test_missing_reducer_profile(tmp_path) -> None:
    p = tmp_path / "packet.json"
    packet = _minimal_packet()
    packet.pop("reducer_profile_ref", None)
    p.write_text(json.dumps(packet))
    proc = _run(str(p), "--json")
    assert proc.returncode == 1
    codes = [i["code"] for i in json.loads(proc.stdout)["issues"]]
    assert "reducer_profile_missing" in codes


# ---------------------------------------------------------------------------
# Error: evidence ref missing field
# ---------------------------------------------------------------------------

def test_evidence_ref_missing_field(tmp_path) -> None:
    p = tmp_path / "packet.json"
    packet = _minimal_packet()
    packet["raw_evidence_refs"] = [{"ref_id": "r1"}]
    p.write_text(json.dumps(packet))
    proc = _run(str(p), "--json")
    assert proc.returncode == 1
    codes = [i["code"] for i in json.loads(proc.stdout)["issues"]]
    assert "evidence_ref_required_field_missing" in codes


# ---------------------------------------------------------------------------
# Error: claim missing field
# ---------------------------------------------------------------------------

def test_claim_missing_field(tmp_path) -> None:
    p = tmp_path / "packet.json"
    packet = _minimal_packet()
    packet["claim_ledger"] = [{"claim_id": "c1"}]
    p.write_text(json.dumps(packet))
    proc = _run(str(p), "--json")
    assert proc.returncode == 1
    codes = [i["code"] for i in json.loads(proc.stdout)["issues"]]
    assert "claim_required_field_missing" in codes


# ---------------------------------------------------------------------------
# Error: invalid claim status
# ---------------------------------------------------------------------------

def test_invalid_claim_status(tmp_path) -> None:
    p = tmp_path / "packet.json"
    packet = _minimal_packet()
    packet["claim_ledger"] = [_minimal_claim()]
    packet["claim_ledger"][0]["status"] = "verified_beyond_doubt"
    p.write_text(json.dumps(packet))
    proc = _run(str(p), "--json")
    assert proc.returncode == 1
    codes = [i["code"] for i in json.loads(proc.stdout)["issues"]]
    assert "claim_status_invalid" in codes


# ---------------------------------------------------------------------------
# Error: claim references missing evidence ref
# ---------------------------------------------------------------------------

def test_claim_missing_evidence_ref(tmp_path) -> None:
    p = tmp_path / "packet.json"
    packet = _minimal_packet()
    packet["claim_ledger"] = [_minimal_claim()]
    packet["claim_ledger"][0]["evidence_refs"] = ["nonexistent-ref"]
    p.write_text(json.dumps(packet))
    proc = _run(str(p), "--json")
    assert proc.returncode == 1
    codes = [i["code"] for i in json.loads(proc.stdout)["issues"]]
    assert "claim_evidence_ref_missing" in codes


# ---------------------------------------------------------------------------
# Error: missing authority_state
# ---------------------------------------------------------------------------

def test_missing_authority_state(tmp_path) -> None:
    p = tmp_path / "packet.json"
    packet = _minimal_packet()
    packet.pop("authority_state", None)
    p.write_text(json.dumps(packet))
    proc = _run(str(p), "--json")
    assert proc.returncode == 1
    codes = [i["code"] for i in json.loads(proc.stdout)["issues"]]
    assert "authority_state_missing" in codes


# ---------------------------------------------------------------------------
# Error: missing authority lock
# ---------------------------------------------------------------------------

def test_missing_authority_lock(tmp_path) -> None:
    p = tmp_path / "packet.json"
    packet = _minimal_packet()
    packet["authority_state"].pop("guardian_operational", None)
    p.write_text(json.dumps(packet))
    proc = _run(str(p), "--json")
    assert proc.returncode == 1
    codes = [i["code"] for i in json.loads(proc.stdout)["issues"]]
    assert "authority_lock_missing" in codes


# ---------------------------------------------------------------------------
# Error: true authority lock on preflight
# ---------------------------------------------------------------------------

def test_true_authority_lock_preflight(tmp_path) -> None:
    p = tmp_path / "packet.json"
    packet = _minimal_packet()
    packet["authority_state"]["plan_execution_allowed"] = True
    p.write_text(json.dumps(packet))
    proc = _run(str(p), "--json")
    assert proc.returncode == 1
    codes = [i["code"] for i in json.loads(proc.stdout)["issues"]]
    assert "authority_lock_true_for_preflight" in codes


# ---------------------------------------------------------------------------
# Error: missing invariant field
# ---------------------------------------------------------------------------

def test_missing_invariant_field(tmp_path) -> None:
    p = tmp_path / "packet.json"
    packet = _minimal_packet()
    packet["invariant_checks"] = [{"invariant_id": "i1"}]
    p.write_text(json.dumps(packet))
    proc = _run(str(p), "--json")
    assert proc.returncode == 1
    codes = [i["code"] for i in json.loads(proc.stdout)["issues"]]
    assert "invariant_required_field_missing" in codes


# ---------------------------------------------------------------------------
# Warning: high-depth empty uncertainty
# ---------------------------------------------------------------------------

def test_high_depth_empty_uncertainty_warns(tmp_path) -> None:
    p = tmp_path / "packet.json"
    packet = _minimal_packet()
    packet["review_depth"] = "high"
    packet["uncertainty"] = []
    p.write_text(json.dumps(packet))
    proc = _run(str(p), "--json")
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data["result"] == "pass_with_warnings"
    codes = [i["code"] for i in data["issues"]]
    assert "uncertainty_missing_for_depth" in codes


# ---------------------------------------------------------------------------
# Warning: empty forbidden_interpretations
# ---------------------------------------------------------------------------

def test_empty_forbidden_interpretations_warns(tmp_path) -> None:
    p = tmp_path / "packet.json"
    packet = _minimal_packet()
    packet["forbidden_interpretations"] = []
    p.write_text(json.dumps(packet))
    proc = _run(str(p), "--json")
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data["result"] == "pass_with_warnings"
    codes = [i["code"] for i in data["issues"]]
    assert "forbidden_interpretations_missing" in codes


# ---------------------------------------------------------------------------
# Warning: empty next_gate_options
# ---------------------------------------------------------------------------

def test_empty_next_gate_options_warns(tmp_path) -> None:
    p = tmp_path / "packet.json"
    packet = _minimal_packet()
    packet["next_gate_options"] = []
    p.write_text(json.dumps(packet))
    proc = _run(str(p), "--json")
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data["result"] == "pass_with_warnings"
    codes = [i["code"] for i in data["issues"]]
    assert "next_gate_options_missing" in codes


# ---------------------------------------------------------------------------
# Warning: missing recommended_next_gate
# ---------------------------------------------------------------------------

def test_missing_recommended_next_gate_warns(tmp_path) -> None:
    p = tmp_path / "packet.json"
    packet = _minimal_packet()
    packet["recommended_next_gate"] = ""
    p.write_text(json.dumps(packet))
    proc = _run(str(p), "--json")
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data["result"] == "pass_with_warnings"
    codes = [i["code"] for i in data["issues"]]
    assert "recommended_next_gate_missing" in codes


# ---------------------------------------------------------------------------
# Error: missing loop_policy
# ---------------------------------------------------------------------------

def test_missing_loop_policy(tmp_path) -> None:
    p = tmp_path / "packet.json"
    packet = _minimal_packet()
    packet.pop("loop_policy", None)
    p.write_text(json.dumps(packet))
    proc = _run(str(p), "--json")
    assert proc.returncode == 1
    codes = [i["code"] for i in json.loads(proc.stdout)["issues"]]
    assert "loop_policy_missing" in codes


# ---------------------------------------------------------------------------
# Error: recursive_autonomous_loop_allowed true
# ---------------------------------------------------------------------------

def test_recursive_loop_true_fails(tmp_path) -> None:
    p = tmp_path / "packet.json"
    packet = _minimal_packet()
    packet["loop_policy"]["recursive_autonomous_loop_allowed"] = True
    p.write_text(json.dumps(packet))
    proc = _run(str(p), "--json")
    assert proc.returncode == 1
    codes = [i["code"] for i in json.loads(proc.stdout)["issues"]]
    assert "recursive_loop_allowed" in codes


# ---------------------------------------------------------------------------
# Error: boundary label missing
# ---------------------------------------------------------------------------

def test_boundary_label_missing(tmp_path) -> None:
    p = tmp_path / "packet.json"
    packet = _minimal_packet()
    packet.pop("boundary_label", None)
    p.write_text(json.dumps(packet))
    proc = _run(str(p), "--json")
    assert proc.returncode == 1
    codes = [i["code"] for i in json.loads(proc.stdout)["issues"]]
    assert "boundary_label_missing" in codes


# ---------------------------------------------------------------------------
# Warning: static_fixture marker missing for fixture path
# ---------------------------------------------------------------------------

def test_static_fixture_marker_missing(tmp_path) -> None:
    fd = tmp_path / "fixtures"
    fd.mkdir()
    p = fd / "packet.json"
    packet = _minimal_packet()
    p.write_text(json.dumps(packet))
    proc = _run(str(p), "--json")
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data["result"] == "pass_with_warnings"
    codes = [i["code"] for i in data["issues"]]
    assert "static_fixture_marker_missing" in codes


# ---------------------------------------------------------------------------
# Warning: content_hash missing
# ---------------------------------------------------------------------------

def test_content_hash_missing(tmp_path) -> None:
    p = tmp_path / "packet.json"
    packet = _minimal_packet()
    packet["raw_evidence_refs"] = [_minimal_ref()]
    p.write_text(json.dumps(packet))
    proc = _run(str(p), "--json")
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data["result"] == "pass_with_warnings"
    codes = [i["code"] for i in data["issues"]]
    assert "content_hash_missing" in codes


# ---------------------------------------------------------------------------
# Warning: release_claim_expansion_risk
# ---------------------------------------------------------------------------

def test_risky_claim_warns(tmp_path) -> None:
    p = tmp_path / "packet.json"
    packet = _minimal_packet()
    packet["reduced_summary"] = "This enables plan execution and Codexify ingestion."
    p.write_text(json.dumps(packet))
    proc = _run(str(p), "--json")
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data["result"] == "pass_with_warnings"
    codes = [i["code"] for i in data["issues"]]
    assert "release_claim_expansion_risk" in codes


def test_negatively_framed_claim_does_not_warn(tmp_path) -> None:
    p = tmp_path / "packet.json"
    packet = _minimal_packet()
    packet["reduced_summary"] = (
        "This does not authorize plan execution. "
        "Pi Loop invocation requires a separate contract. "
        "Codexify ingestion is not authorized by this proof."
    )
    p.write_text(json.dumps(packet))
    proc = _run(str(p), "--json")
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    codes = [i["code"] for i in data["issues"]]
    assert "release_claim_expansion_risk" not in codes


# ---------------------------------------------------------------------------
# No file writing
# ---------------------------------------------------------------------------

def test_script_does_not_write_files(tmp_path) -> None:
    p = tmp_path / "packet.json"
    packet = _minimal_packet()
    p.write_text(json.dumps(packet))
    before = set(str(x) for x in tmp_path.rglob("*"))
    _run(str(p), "--json")
    after = set(str(x) for x in tmp_path.rglob("*"))
    assert before == after, "Validator must not write files"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _minimal_packet() -> dict:
    return {
        "schema_version": "guardian_evidence_packet.v1",
        "packet_id": "test-packet",
        "created_at": "2026-01-01T00:00:00Z",
        "source_domain": "test",
        "evidence_class": "preflight_proof_chain",
        "review_depth": "medium",
        "subject": {"title": "test"},
        "reducer_profile_ref": "test-profile",
        "raw_evidence_refs": [],
        "reduced_summary": "test summary",
        "claim_ledger": [],
        "authority_state": {
            "guardian_operational": False,
            "plan_execution_allowed": False,
            "pi_loop_invocation_allowed": False,
            "codexify_ingestion_allowed": False,
            "durable_mutation_allowed": False,
            "provider_execution_allowed": False,
            "patch_application_allowed": False,
            "dispatch_allowed": False,
            "merge_allowed": False,
        },
        "invariant_checks": [],
        "uncertainty": [{"uncertainty_id": "u1", "description": "test", "severity": "low",
                         "missing_evidence": [], "resolution_options": []}],
        "forbidden_interpretations": [{"interpretation_id": "f1", "statement": "test"}],
        "next_gate_options": [{"gate_id": "g1", "description": "test", "prerequisites": [], "risk": "low"}],
        "recommended_next_gate": "g1",
        "loop_policy": {
            "bounded": True,
            "review_depth": "medium",
            "self_check_passes": 1,
            "recursive_autonomous_loop_allowed": False,
            "adversarial_review_required": False,
            "missing_proof_ledger_required": False,
        },
        "provenance": {"reducer_version": "v1", "profile_id": "p1", "input_artifact_ids": []},
        "limits": {"max_source_artifacts": 10, "summary_budget_tokens": 100,
                   "artifacts_consumed": 0, "tokens_consumed": None},
        "boundary_label": (
            "PREFLIGHT ONLY\n"
            "NO PI LOOP INVOCATION\n"
            "NO SOURCE MUTATION\n"
            "NO CODEXIFY INGESTION"
        ),
    }


def _minimal_ref() -> dict:
    return {
        "ref_id": "r1",
        "ref_type": "test",
        "uri_or_path": "/test",
        "source_system": "test",
        "content_hash": None,
        "timestamp": None,
        "status": "test",
        "trust_posture": "evidence_only",
        "notes": None,
    }


def _minimal_claim() -> dict:
    return {
        "claim_id": "c1",
        "claim": "test claim",
        "status": "supported",
        "evidence_refs": [],
        "confidence": "high",
        "limits": {"context_boundary": "test", "temporal_boundary": "test"},
        "counterclaims": [],
        "missing_evidence": [],
        "forbidden_interpretations": [],
    }
