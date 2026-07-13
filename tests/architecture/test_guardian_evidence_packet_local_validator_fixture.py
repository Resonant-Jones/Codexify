"""Tests for the second static GuardianEvidencePacket fixture."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "docs/architecture/fixtures/guardian-evidence-packet.local-validator-toolchain.v1.json"
SINGLE = ROOT / "scripts/guardian/validate_evidence_packet.py"
BATCH = ROOT / "scripts/guardian/validate_evidence_packets.py"
GUIDE = ROOT / "docs/architecture/guardian-evidence-packet-authoring-guide.md"
STATIC_CONTRACT = ROOT / "docs/architecture/guardian-evidence-packet-static-validator-contract.md"
REDUCER_CONTRACT = ROOT / "docs/architecture/guardian-evidence-packet-reducer-contract.md"
README = ROOT / "docs/architecture/README.md"
CURRENT = ROOT / "docs/architecture/00-current-state.md"

REQUIRED_FIELDS = {
    "schema_version", "packet_id", "created_at", "source_domain", "evidence_class",
    "review_depth", "subject", "reducer_profile_ref", "raw_evidence_refs",
    "reduced_summary", "claim_ledger", "authority_state", "invariant_checks",
    "uncertainty", "forbidden_interpretations", "next_gate_options",
    "recommended_next_gate", "loop_policy", "provenance", "limits",
}
AUTHORITY_LOCKS = {
    "guardian_operational", "plan_execution_allowed", "pi_loop_invocation_allowed",
    "codexify_ingestion_allowed", "durable_mutation_allowed", "provider_execution_allowed",
    "patch_application_allowed", "dispatch_allowed", "merge_allowed",
}
CLAIM_FIELDS = {
    "claim_id", "claim", "status", "evidence_refs", "confidence", "limits",
    "counterclaims", "missing_evidence", "forbidden_interpretations",
}
ALLOWED_STATUSES = {"supported", "unsupported", "blocked", "inferred", "not_evaluated"}
BOUNDARY_LABEL = "PREFLIGHT ONLY\nNO PI LOOP INVOCATION\nNO SOURCE MUTATION\nNO CODEXIFY INGESTION"


def _packet() -> dict:
    return json.loads(FIXTURE.read_text())


def _run(script: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(script), str(FIXTURE), "--json"],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )


def test_fixture_exists_and_is_valid_json() -> None:
    assert FIXTURE.exists()
    assert isinstance(_packet(), dict)


def test_fixture_identity_and_required_shape() -> None:
    packet = _packet()
    assert packet["schema_version"] == "guardian_evidence_packet.v1"
    assert packet["source_domain"] == "guardian_evidence_packet_validation"
    assert packet["evidence_class"] == "local_static_validation_toolchain"
    assert packet["review_depth"] == "high"
    assert REQUIRED_FIELDS <= packet.keys()
    assert packet["subject"] == {
        "repo": "Codexify",
        "packet_scope": "guardian_evidence_packet_local_validation_toolchain",
        "related_system": "Guardian Evidence Packet local tooling",
        "branch_or_ref": "main",
        "title": "Guardian Evidence Packet Local Validation Toolchain Evidence Summary",
    }


def test_fixture_provenance_authority_and_boundary() -> None:
    packet = _packet()
    assert packet["provenance"]["static_fixture"] is True
    assert packet["provenance"]["authored_from_template"] is True
    assert AUTHORITY_LOCKS <= packet["authority_state"].keys()
    assert all(packet["authority_state"][key] is False for key in AUTHORITY_LOCKS)
    assert packet["limits"]["boundary_label"] == BOUNDARY_LABEL
    assert packet["boundary_label"] == BOUNDARY_LABEL


def test_fixture_evidence_refs_and_claim_ledger_are_bound() -> None:
    packet = _packet()
    refs = {ref["ref_id"]: ref for ref in packet["raw_evidence_refs"]}
    paths = {ref["uri_or_path"] for ref in packet["raw_evidence_refs"]}
    assert len(refs) >= 14
    assert "scripts/guardian/validate_evidence_packet.py" in paths
    assert "scripts/guardian/validate_evidence_packets.py" in paths
    assert "Makefile" in paths
    assert "docs/architecture/templates/guardian-evidence-packet-template.v1.json" in paths
    assert "docs/architecture/guardian-evidence-packet-authoring-guide.md" in paths
    assert len(packet["claim_ledger"]) >= 18
    for claim in packet["claim_ledger"]:
        assert CLAIM_FIELDS <= claim.keys()
        assert claim["status"] in ALLOWED_STATUSES
        assert set(claim["evidence_refs"]) <= refs.keys()


def test_fixture_preserves_negative_interpretations_and_next_gate() -> None:
    packet = _packet()
    text = json.dumps(packet).lower()
    for phrase in (
        "passing static validation does not prove claim truth",
        "passing static validation does not promote evidence to authority",
        "passing static validation is not codexify ingestion",
        "passing static validation is not execution ledger truth",
        "passing static validation is not workorder mutation",
        "local validation toolchain is not runtime support",
        "local validation toolchain is not ci or default release gating",
    ):
        assert phrase in text
    assert packet["recommended_next_gate"] == "guardian_evidence_packet_runtime_reducer_design_contract"


def test_single_validator_accepts_fixture() -> None:
    proc = _run(SINGLE)
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)["result"] in {"pass", "pass_with_warnings"}


def test_batch_validator_discovers_both_fixtures() -> None:
    proc = subprocess.run(
        [sys.executable, str(BATCH), "--json"],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data["matched_count"] >= 2
    refs = [result["validated_packet_ref"] for result in data["packet_results"]]
    assert any("guardian-evidence-packet.local-validator-toolchain" in ref for ref in refs)
    assert any("guardian-evidence-packet.codex-runner-bridge-proof-chain" in ref for ref in refs)


def test_make_target_validates_both_fixtures() -> None:
    proc = subprocess.run(
        ["make", "guardian-evidence-packets-validate"],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert '"matched_count": 3' in proc.stdout


def test_docs_name_second_fixture_and_boundary() -> None:
    assert "local validator toolchain fixture" in GUIDE.read_text()
    assert "multiple fixtures" in STATIC_CONTRACT.read_text()
    assert "overfit to one evidence source" in REDUCER_CONTRACT.read_text()
    assert "guardian-evidence-packet.local-validator-toolchain.v1.json" in README.read_text()
    assert "second GuardianEvidencePacket fixture" in CURRENT.read_text()
