"""Tests for the static GuardianEvidencePacket authoring aids."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "docs" / "architecture" / "templates" / "guardian-evidence-packet-template.v1.json"
GUIDE = ROOT / "docs" / "architecture" / "guardian-evidence-packet-authoring-guide.md"
FIXTURES = ROOT / "docs" / "architecture" / "fixtures"

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
BOUNDARY_LABEL = "PREFLIGHT ONLY\nNO PI LOOP INVOCATION\nNO SOURCE MUTATION\nNO CODEXIFY INGESTION"
REVIEW_DEPTHS = {"light", "medium", "high", "xhigh"}
CLAIM_STATUSES = {"supported", "unsupported", "blocked", "inferred", "not_evaluated"}
REQUIRED_GUIDE_SECTIONS = [
    "Purpose", "Status", "Scope", "When to Author a GuardianEvidencePacket",
    "When Not to Author a GuardianEvidencePacket", "Authoring Inputs",
    "Choosing review_depth", "Evidence Reference Rules", "Claim Ledger Rules",
    "Authority State Rules", "Invariant Check Rules", "Uncertainty Rules",
    "Forbidden Interpretation Rules", "Next Gate Rules", "Loop Policy Rules",
    "Template Usage", "Validation Ritual", "Review Ritual",
    "Relationship to Runtime Reducer", "Relationship to Future UI",
    "Relationship to Execution Ledger and WorkOrder", "Failure Modes",
    "Forbidden Interpretations", "Bottom Line",
]


def _template() -> dict:
    return json.loads(TEMPLATE.read_text())


def test_authoring_template_exists_and_is_valid_json() -> None:
    assert TEMPLATE.exists()
    assert isinstance(_template(), dict)


def test_template_has_schema_and_required_fields() -> None:
    packet = _template()
    assert packet["schema_version"] == "guardian_evidence_packet.v1"
    assert REQUIRED_FIELDS <= packet.keys()


def test_template_is_not_a_fixture() -> None:
    assert TEMPLATE.parent == ROOT / "docs" / "architecture" / "templates"
    assert TEMPLATE.parent != FIXTURES
    assert TEMPLATE not in FIXTURES.glob("guardian-evidence-packet*.json")


def test_template_has_false_authority_locks() -> None:
    authority = _template()["authority_state"]
    assert AUTHORITY_LOCKS <= authority.keys()
    assert all(authority[key] is False for key in AUTHORITY_LOCKS)


def test_template_has_boundary_and_authoring_guidance() -> None:
    packet = _template()
    assert packet["limits"]["boundary_label"] == BOUNDARY_LABEL
    assert packet["provenance"]["template"] is True
    assert REVIEW_DEPTHS <= set(packet["limits"]["allowed_review_depths"])
    assert CLAIM_STATUSES <= set(packet["limits"]["allowed_claim_statuses"])
    notes = packet["limits"]["guardrail_notes"]
    for phrase in (
        "This is a template.", "This is not evidence.",
        "This is not runtime reducer output.", "This is not Codexify ingestion.",
        "This is not Execution Ledger truth.", "This is not WorkOrder mutation.",
        "This does not authorize execution.", "This does not authorize source mutation.",
        "This does not authorize Pi Loop invocation.",
        "This does not authorize provider execution.",
        "This does not widen release support.",
    ):
        assert phrase in notes


def test_authoring_guide_exists_and_has_required_sections() -> None:
    guide = GUIDE.read_text()
    assert GUIDE.exists()
    for section in REQUIRED_GUIDE_SECTIONS:
        assert f"## " in guide and section in guide
    for phrase in (
        "review_depth controls evidence handling and self-check policy, not model personality",
        "Passing validation does not prove claim truth",
        "promote evidence to authority",
        "Future runtime reducer implementation requires a separate explicit contract",
        "Future UI surfacing requires a separate explicit contract",
        "Future Execution Ledger adoption requires a separate explicit contract",
        "Future WorkOrder mutation requires a separate explicit contract",
        "Identify evidence domain.",
        "Review warnings without treating them as authority.",
    ):
        assert phrase in guide


def test_contracts_and_current_truth_link_authoring_aids() -> None:
    reducer = (ROOT / "docs/architecture/guardian-evidence-packet-reducer-contract.md").read_text()
    validator = (ROOT / "docs/architecture/guardian-evidence-packet-static-validator-contract.md").read_text()
    readme = (ROOT / "docs/architecture/README.md").read_text()
    current = (ROOT / "docs/architecture/00-current-state.md").read_text()
    assert "templates/guardian-evidence-packet-template.v1.json" in reducer
    assert "guardian-evidence-packet-authoring-guide.md" in reducer
    assert "intentionally outside `docs/architecture/fixtures`" in validator
    assert "guardian-evidence-packet-template.v1.json" in readme
    assert "guardian-evidence-packet-authoring-guide.md" in readme
    assert "Guardian Evidence Packet authoring template and guide" in current


def test_batch_target_validates_fixtures_not_template() -> None:
    proc = subprocess.run(
        ["make", "guardian-evidence-packets-validate"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert "guardian_evidence_packet_batch_validation_result.v1" in proc.stdout
    assert str(TEMPLATE) not in proc.stdout
    assert '"matched_count": 1' in proc.stdout
