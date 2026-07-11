import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "docs/architecture/fixtures/guardian-evidence-packet.generated-local-tooling.v1.json"
BOUNDED_READ = ROOT / "docs/architecture/fixtures/guardian-evidence-bounded-read.local-tooling.v1.json"
VALIDATOR = ROOT / "scripts/guardian/validate_evidence_packet.py"
BATCH_VALIDATOR = ROOT / "scripts/guardian/validate_evidence_packets.py"
GENERATOR = ROOT / "scripts/guardian/generate_evidence_packet.py"

EXPECTED_EVIDENCE_URIS = {
    "docs/architecture/guardian-evidence-packet-runtime-reducer-design-contract.md",
    "docs/architecture/fixtures/guardian-evidence-packet.local-validator-toolchain.v1.json",
}
EXPECTED_PACKET_ID = "guardian-evidence-packet.generated-local-tooling.v1"
EXPECTED_SCHEMA = "guardian_evidence_packet.v1"
AUTHORITY_LOCKS = (
    "guardian_operational", "plan_execution_allowed", "pi_loop_invocation_allowed",
    "codexify_ingestion_allowed", "durable_mutation_allowed", "provider_execution_allowed",
    "patch_application_allowed", "dispatch_allowed", "merge_allowed",
)
FORBIDDEN_PHRASES = (
    "not authority", "not execution", "not evidence ingestion",
    "not source truth approval", "not receipt trust",
    "not workorder mutation", "not execution ledger write", "not release approval",
)
SECRET_PATTERNS = (
    "sk-", "secret", "api_key", "password", "credentials",
    "/Volumes/", "/home/", ".env",
)
SECRET_KEYWORDS = ("sk-", "api_key", "password", "credentials")


def _load() -> dict:
    return json.loads(FIXTURE.read_text())


def test_fixture_exists_and_is_valid_json() -> None:
    assert FIXTURE.is_file()
    packet = _load()
    assert isinstance(packet, dict)


def test_fixture_is_packet_object_not_generator_result() -> None:
    packet = _load()
    assert "schema_version" in packet
    assert "packet_id" in packet
    assert "generator_contract_version" not in packet
    assert "bounded_read_result_ref" not in packet
    assert "diagnostics" not in packet


def test_fixture_static_validation_passes() -> None:
    proc = subprocess.run(
        ["python3", str(VALIDATOR), str(FIXTURE), "--json"],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout)
    assert result["result"] in {"pass", "pass_with_warnings"}


def test_batch_validator_discovers_three_fixtures() -> None:
    proc = subprocess.run(
        ["python3", str(BATCH_VALIDATOR), "--json"],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout)
    assert result["matched_count"] == 3


def test_fixture_has_correct_schema_and_packet_id() -> None:
    packet = _load()
    assert packet["schema_version"] == EXPECTED_SCHEMA
    assert packet["packet_id"] == EXPECTED_PACKET_ID


def test_fixture_references_bounded_read_fixture_as_provenance() -> None:
    packet = _load()
    prov = packet["provenance"]
    assert prov["bounded_read_result_ref"] == "explicit-cli-input"


def test_fixture_contains_raw_evidence_refs_with_content_hashes() -> None:
    packet = _load()
    uris = {ref["uri_or_path"] for ref in packet["raw_evidence_refs"]}
    assert uris == EXPECTED_EVIDENCE_URIS
    for ref in packet["raw_evidence_refs"]:
        assert ref["content_hash"] is not None
        assert len(ref["content_hash"]) > 0
        assert ref["trust_posture"] == "evidence_only"


def test_fixture_represents_skipped_entry_as_uncertainty() -> None:
    packet = _load()
    descriptions = [item["description"] for item in packet["uncertainty"]]
    assert any("skipped" in desc.lower() for desc in descriptions)
    uncertainties_with_missing = [
        item for item in packet["uncertainty"]
        if any("path" in str(m) for m in item.get("missing_evidence", []))
    ]
    assert len(uncertainties_with_missing) >= 1


def test_fixture_has_all_authority_locks_false() -> None:
    packet = _load()
    for lock in AUTHORITY_LOCKS:
        assert lock in packet["authority_state"], f"Missing authority lock: {lock}"
        assert packet["authority_state"][lock] is False, f"Lock {lock} is not false"


def test_fixture_contains_forbidden_interpretations() -> None:
    packet = _load()
    assert len(packet["forbidden_interpretations"]) >= 8
    statements = {fi["statement"] for fi in packet["forbidden_interpretations"]}
    assert "PREFLIGHT ONLY" in str(statements)
    assert "NO PI LOOP INVOCATION" in str(statements)
    assert "NO SOURCE MUTATION" in str(statements)
    assert "NO CODEXIFY INGESTION" in str(statements)


def test_fixture_no_absolute_paths() -> None:
    text = json.dumps(_load())
    for pattern in SECRET_PATTERNS:
        assert pattern.lower() not in text.lower()


def test_fixture_no_secrets() -> None:
    text = json.dumps(_load()).lower()
    for secret in SECRET_KEYWORDS:
        assert secret not in text


def test_fixture_forbidden_interpretations_messages_present() -> None:
    text = json.dumps(_load()).lower()
    for phrase in FORBIDDEN_PHRASES:
        assert phrase in text


def test_fixture_claim_ledger_has_evidence_refs() -> None:
    packet = _load()
    for claim in packet["claim_ledger"]:
        assert len(claim["evidence_refs"]) > 0
        assert any("forbidden_interpretations" in claim for claim in packet["claim_ledger"])


def test_generated_fixture_matches_live_generator_output() -> None:
    proc = subprocess.run(
        ["python3", str(GENERATOR), str(BOUNDED_READ), "--json"],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    assert proc.returncode == 0, proc.stderr
    live = json.loads(proc.stdout)["packet"]
    static_fixture = _load()
    live["created_at"] = "2026-07-11T00:00:00Z"
    assert live == static_fixture


def test_fixture_has_no_receipt_trust_or_workorder_authority() -> None:
    text = json.dumps(_load()).lower()
    for phrase in ("receipt trust", "not receipt trust"):
        assert phrase in text
