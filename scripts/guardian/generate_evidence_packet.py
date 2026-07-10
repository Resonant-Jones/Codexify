#!/usr/bin/env python3
"""Generate one stdout-only GuardianEvidencePacket from a bounded-read result."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from guardian.evidence_packets.contracts import BOUNDARY_LABEL, false_authority_state
from scripts.guardian import validate_evidence_packet as packet_validator

RESULT_SCHEMA = "guardian_evidence_packet_generator_result.v1"
CONTRACT_VERSION = "guardian_evidence_packet_generator_contract.v1"
DEFAULT_PACKET_ID = "guardian-evidence-packet.generated-local-tooling.v1"
LIMITS = (
    "no_execution", "no_evidence_ingestion", "no_command_bus", "no_codex_runner",
    "no_pi_loop", "no_source_mutation", "no_provider_execution", "no_workorder_mutation",
    "no_execution_ledger_write", "no_release_support_expansion", "stdout_only", "no_fixture_write",
)


def _validate(packet: dict[str, Any]) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    counter = [0]
    def add(severity: str, code: str, path: str, message: str, evidence_ref: str = "", remediation_hint: str = "") -> None:
        counter[0] += 1
        issues.append(packet_validator._issue(f"issue-{counter[0]:04d}", severity, code, path, message, evidence_ref, remediation_hint))
    packet_validator._check_schema_version(packet, add)
    packet_validator._check_required_fields(packet, add)
    packet_validator._check_review_depth(packet, add)
    packet_validator._check_reducer_profile(packet, add)
    refs = packet_validator._check_evidence_refs(packet, add)
    packet_validator._check_claim_ledger(packet, refs, add)
    packet_validator._check_authority(packet, add)
    packet_validator._check_invariant_checks(packet, add)
    packet_validator._check_uncertainty(packet, add)
    packet_validator._check_forbidden_interpretations(packet, add)
    packet_validator._check_next_gate(packet, add)
    packet_validator._check_loop_policy(packet, add)
    packet_validator._check_boundary_label(packet, add)
    packet_validator._check_release_guardrails(json.dumps(packet), add)
    result = "fail" if any(i["severity"] == "error" for i in issues) else "pass_with_warnings" if issues else "pass"
    output = packet_validator._build_result("<stdout-only-generated-packet>", result, issues)
    output["checked_at"] = "generated-deterministic"
    return output


def _packet(data: dict[str, Any], packet_id: str) -> dict[str, Any]:
    results = data["read_results"]
    refs = []
    uncertainty = []
    for index, item in enumerate(results, start=1):
        ref_id = f"bounded-read-{index}"
        if item["read_status"] == "read":
            refs.append({"ref_id": ref_id, "ref_type": "bounded_read_artifact", "uri_or_path": item["source_ref"], "source_system": "guardian_bounded_read", "content_hash": item["content_hash"], "timestamp": None, "status": "read", "trust_posture": "evidence_only", "notes": "Bounded local read artifact; source truth is not approved."})
        else:
            uncertainty.append({"uncertainty_id": f"omitted-{index}", "description": f"{item['source_ref']} was {item['read_status']}.", "severity": "medium", "missing_evidence": [item.get("omitted_content_reason") or "bounded-read content unavailable"], "resolution_options": ["Review the bounded-read artifact; do not infer source truth."]})
    claim_refs = [r["ref_id"] for r in refs]
    claim = {"claim_id": "bounded-read-artifact-generated", "claim": "A bounded-read artifact was converted into a local stdout-only packet; this does not establish source truth, authority, execution, ingestion, WorkOrder mutation, or Execution Ledger write.", "status": "supported", "evidence_refs": claim_refs, "confidence": "medium", "limits": {"context_boundary": "bounded-read artifact facts only", "temporal_boundary": "fixture-derived local output"}, "counterclaims": [], "missing_evidence": [u["description"] for u in uncertainty], "forbidden_interpretations": ["Generated packet is not authority or source truth approval."]}
    forbidden = [
        "generated packet is not authority", "generated packet is not execution", "generated packet is not evidence ingestion", "generated packet is not source truth approval", "generated packet is not receipt trust", "generated packet is not WorkOrder mutation", "generated packet is not Execution Ledger write", "generated packet is not release approval",
    ]
    return {"schema_version": "guardian_evidence_packet.v1", "packet_id": packet_id, "created_at": "2026-07-10T00:00:00Z", "source_domain": "guardian_evidence_bounded_read", "evidence_class": "preflight_bounded_read_artifact", "review_depth": "medium", "subject": {"title": "Guardian Evidence bounded-read local tooling packet", "packet_scope": "bounded_read_local_tooling", "related_system": "Guardian Evidence Packet generator"}, "reducer_profile_ref": "guardian_reducer_profile.bounded_read_local_tooling_medium.v1", "raw_evidence_refs": refs, "reduced_summary": "Bounded-read artifact facts were converted to a local stdout-only packet. This is not authority, source truth approval, execution, ingestion, receipt trust, WorkOrder mutation, Execution Ledger write, or release approval.", "claim_ledger": [claim], "authority_state": false_authority_state(), "invariant_checks": [{"invariant_id": "authority-locks-false", "status": "pass", "evidence_refs": claim_refs, "notes": "All authority locks remain false."}], "uncertainty": uncertainty, "forbidden_interpretations": [{"interpretation_id": f"not-{i}", "statement": statement, "applies_to_claims": [claim["claim_id"]], "applies_to_evidence": claim_refs} for i, statement in enumerate(forbidden, start=1)] + [{"interpretation_id": "boundary", "statement": BOUNDARY_LABEL, "applies_to_claims": [], "applies_to_evidence": []}], "next_gate_options": [{"gate_id": "human-review", "description": "Review generated packet boundaries before any separate future action.", "prerequisites": ["Static validation result reviewed"], "risk": "low"}], "recommended_next_gate": "human-review", "loop_policy": {"bounded": True, "review_depth": "medium", "self_check_passes": 1, "passes_executed": 1, "pass_results": ["static_validation"], "recursive_autonomous_loop_allowed": False, "adversarial_review_required": False, "missing_proof_ledger_required": True}, "provenance": {"reducer_version": "local-stdout-generator.v1", "profile_id": "bounded_read_local_tooling_medium.v1", "template": False, "static_fixture": False, "input_artifact_ids": [data["input_bundle_ref"]], "bounded_read_result_ref": "explicit-cli-input"}, "limits": {"max_source_artifacts": len(results), "summary_budget_tokens": 1000, "artifacts_consumed": len(refs), "tokens_consumed": None, "not_evidence": False, "not_runtime_reducer_output": True, "not_codexify_ingestion": True, "not_execution_ledger_truth": True, "not_workorder_mutation": True, "does_not_authorize_execution": True, "does_not_authorize_source_mutation": True, "does_not_authorize_pi_loop_invocation": True, "does_not_authorize_provider_execution": True, "does_not_widen_release_support": True, "guardrail_notes": forbidden, "boundary_label": BOUNDARY_LABEL}, "boundary_label": BOUNDARY_LABEL}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate one stdout-only GuardianEvidencePacket from a bounded-read JSON artifact.")
    parser.add_argument("bounded_read_result", type=Path)
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--packet-id", default=DEFAULT_PACKET_ID)
    args = parser.parse_args(argv)
    try:
        data = json.loads(args.bounded_read_result.read_text(encoding="utf-8"))
        if data.get("schema_version") != "guardian_evidence_bounded_read_batch_result.v1" or data.get("result") == "fail" or not isinstance(data.get("read_results"), list):
            raise ValueError("bounded-read result is invalid or failed")
        packet = _packet(data, args.packet_id)
        validation = _validate(packet)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, KeyError, TypeError) as exc:
        print(f"generator error: {exc}", file=sys.stderr)
        return 1
    output = {"schema_version": RESULT_SCHEMA, "generator_contract_version": CONTRACT_VERSION, "bounded_read_result_ref": str(args.bounded_read_result), "packet": packet, "packet_validation_result": validation, "authority_state": false_authority_state(), "diagnostics": {"source_ref_read_policy": "reads bounded-read result only; does not read source_ref targets", "evidence_ref_count": len(packet["raw_evidence_refs"]), "claim_count": len(packet["claim_ledger"]), "uncertainty_count": len(packet["uncertainty"]), "forbidden_interpretation_count": len(packet["forbidden_interpretations"]), "contradiction_count": 0, "omitted_source_count": len(packet["uncertainty"]), "bounded_read_result": data["result"]}, "limits": list(LIMITS)}
    if args.as_json:
        print(json.dumps(output, indent=2))
    else:
        print(f"Generated packet {packet['packet_id']}: validation={validation['result']}")
    return 0 if validation["result"] != "fail" else 1


if __name__ == "__main__":
    sys.exit(main())
