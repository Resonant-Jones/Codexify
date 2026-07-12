#!/usr/bin/env python3
"""Local static validator for GuardianEvidencePacket JSON fixtures.

Validates packet shape and guardrail presence according to
docs/architecture/guardian-evidence-packet-static-validator-contract.md.

This is local tooling only. It does not wire into runtime, command bus,
API routes, frontend, or any live system.

Usage:
  python3 scripts/guardian/validate_evidence_packet.py PACKET_PATH [--json]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Direct script execution starts with scripts/guardian on sys.path. Add only
# the repository root so this local tool can import its pure contract package.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from guardian.evidence_packets.contracts import (
    ALLOWED_CLAIM_STATUSES,
    ALLOWED_REVIEW_DEPTHS,
    BOUNDARY_LABEL,
    GUARDIAN_EVIDENCE_PACKET_SCHEMA_VERSION,
    REQUIRED_AUTHORITY_LOCKS,
    REQUIRED_CLAIM_FIELDS,
    REQUIRED_EVIDENCE_REF_FIELDS,
    REQUIRED_INVARIANT_CHECK_FIELDS,
    REQUIRED_LOOP_POLICY_FIELDS,
    REQUIRED_PACKET_FIELDS,
    STATIC_VALIDATION_RESULT_SCHEMA_VERSION,
    authority_locks_true,
    is_allowed_claim_status,
    is_allowed_review_depth,
    is_preflight_evidence_class,
    missing_authority_locks,
    missing_claim_fields,
    missing_evidence_ref_fields,
    missing_invariant_check_fields,
    missing_loop_policy_fields,
    missing_packet_fields,
    packet_declares_boundary_label,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALIDATOR_VERSION = "guardian_evidence_packet_static_validator_contract.v1"
SCRIPT_ID = "scripts/guardian/validate_evidence_packet.py"

ALLOWED_RESULTS = frozenset({"pass", "pass_with_warnings", "fail"})

# Candidate validator issue codes (not runtime protocol tokens)
ISSUE_CODES = frozenset({
    "packet_json_invalid",
    "packet_schema_version_missing",
    "packet_schema_version_unsupported",
    "packet_required_field_missing",
    "review_depth_invalid",
    "reducer_profile_missing",
    "evidence_ref_required_field_missing",
    "claim_required_field_missing",
    "claim_status_invalid",
    "claim_evidence_ref_missing",
    "authority_state_missing",
    "authority_lock_missing",
    "authority_lock_true_for_preflight",
    "invariant_required_field_missing",
    "uncertainty_missing_for_depth",
    "forbidden_interpretations_missing",
    "next_gate_options_missing",
    "recommended_next_gate_missing",
    "loop_policy_missing",
    "recursive_loop_allowed",
    "boundary_label_missing",
    "release_claim_expansion_risk",
    "content_hash_missing",
    "static_fixture_marker_missing",
})

# ---------------------------------------------------------------------------
# Release-claim scan: positive claims that should warn if not negatively framed
# ---------------------------------------------------------------------------

_RISKY_CLAIM_PATTERNS: list[tuple[str, str]] = [
    ("plan execution", "execution"),
    ("pi loop", "pi loop"),
    ("source mutation", "mutation"),
    ("provider execution", "provider"),
    ("codexify ingestion", "ingestion"),
    ("workorder", "workorder"),
    ("execution ledger", "ledger"),
]

_NEGATIVE_FRAMING = (
    "not", "no ", "does not", "not yet", "outside current support",
    "requires a separate contract", "requires a separate explicit contract",
    "not implemented", "not authorized", "not supported",
    "not proven", "remains deferred", "future", "not add",
    "not establish", "not claim",
)


def _is_negatively_framed(context: str) -> bool:
    """Check whether *context* contains negative framing near a risky claim."""
    return any(phrase in context for phrase in _NEGATIVE_FRAMING)


# ---------------------------------------------------------------------------
# Issue collector
# ---------------------------------------------------------------------------

def _issue(
    issue_id: str,
    severity: str,
    code: str,
    path: str,
    message: str,
    evidence_ref: str = "",
    remediation_hint: str = "",
) -> dict[str, str]:
    return {
        "issue_id": issue_id,
        "severity": severity,
        "code": code,
        "path": path,
        "message": message,
        "evidence_ref": evidence_ref,
        "remediation_hint": remediation_hint,
    }


# ---------------------------------------------------------------------------
# Main validator
# ---------------------------------------------------------------------------

def validate_packet(packet_path: str) -> dict[str, Any]:
    """Validate a GuardianEvidencePacket JSON file.

    Returns a GuardianEvidencePacketStaticValidationResult dict.
    """
    issues: list[dict[str, str]] = []
    packet: dict[str, Any] | None = None
    packet_ref = str(packet_path)
    issue_counter = [0]  # mutable counter

    def add(
        severity: str,
        code: str,
        path: str,
        message: str,
        evidence_ref: str = "",
        remediation_hint: str = "",
    ) -> None:
        issue_counter[0] += 1
        issues.append(_issue(
            f"issue-{issue_counter[0]:04d}",
            severity, code, path, message, evidence_ref, remediation_hint,
        ))

    # Parse
    try:
        raw = Path(packet_path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        add("error", "packet_json_invalid", "$", f"Cannot read file: {exc}")
        return _build_result(packet_ref, "fail", issues)
    try:
        packet = json.loads(raw)
    except json.JSONDecodeError as exc:
        add("error", "packet_json_invalid", "$", f"Invalid JSON: {exc}")
        return _build_result(packet_ref, "fail", issues)
    if not isinstance(packet, dict):
        add("error", "packet_json_invalid", "$", "Packet root must be a JSON object")
        return _build_result(packet_ref, "fail", issues)

    # Top-level
    _check_schema_version(packet, add)
    _check_required_fields(packet, add)

    # Reducer profile
    _check_review_depth(packet, add)
    _check_reducer_profile(packet, add)

    # Evidence refs
    ref_id_set = _check_evidence_refs(packet, add)

    # Claim ledger
    _check_claim_ledger(packet, ref_id_set, add)

    # Authority
    _check_authority(packet, add)

    # Invariant checks
    _check_invariant_checks(packet, add)

    # Uncertainty
    _check_uncertainty(packet, add)

    # Forbidden interpretations
    _check_forbidden_interpretations(packet, add)

    # Next gate
    _check_next_gate(packet, add)

    # Loop policy
    _check_loop_policy(packet, add)

    # Boundary label
    _check_boundary_label(packet, add)

    # Release guardrails
    _check_release_guardrails(raw, add)

    # Static fixture marker
    _check_static_fixture_marker(packet, packet_path, add)

    # Determine result
    errors = [i for i in issues if i["severity"] == "error"]
    warnings = [i for i in issues if i["severity"] == "warning"]
    if errors:
        result = "fail"
    elif warnings:
        result = "pass_with_warnings"
    else:
        result = "pass"

    return _build_result(packet_ref, result, issues)


# ---------------------------------------------------------------------------
# Check functions
# ---------------------------------------------------------------------------

def _check_schema_version(packet: dict, add) -> None:
    sv = packet.get("schema_version")
    if sv is None:
        add("error", "packet_schema_version_missing", "$.schema_version",
            "schema_version is required")
    elif sv != GUARDIAN_EVIDENCE_PACKET_SCHEMA_VERSION:
        add("error", "packet_schema_version_unsupported", "$.schema_version",
            f"schema_version must be '{GUARDIAN_EVIDENCE_PACKET_SCHEMA_VERSION}', got '{sv}'")


def _check_required_fields(packet: dict, add) -> None:
    for field in missing_packet_fields(packet):
        if field not in packet:
            add("error", "packet_required_field_missing", f"$.{field}",
                f"Required field '{field}' is missing")


def _check_review_depth(packet: dict, add) -> None:
    rd = packet.get("review_depth")
    if rd is not None and not is_allowed_review_depth(rd):
        add("error", "review_depth_invalid", "$.review_depth",
            f"review_depth must be one of {sorted(ALLOWED_REVIEW_DEPTHS)}, got '{rd}'")


def _check_reducer_profile(packet: dict, add) -> None:
    rpr = packet.get("reducer_profile_ref")
    if not rpr or not isinstance(rpr, str) or not rpr.strip():
        add("error", "reducer_profile_missing", "$.reducer_profile_ref",
            "reducer_profile_ref is required and must be non-empty")


def _check_evidence_refs(packet: dict, add) -> set[str]:
    refs = packet.get("raw_evidence_refs", [])
    if not isinstance(refs, list):
        return set()
    ref_id_set: set[str] = set()
    for idx, ref in enumerate(refs):
        if not isinstance(ref, dict):
            add("error", "evidence_ref_required_field_missing",
                f"$.raw_evidence_refs[{idx}]", "Evidence ref must be an object")
            continue
        for field in missing_evidence_ref_fields(ref):
            if field not in ref:
                add("error", "evidence_ref_required_field_missing",
                    f"$.raw_evidence_refs[{idx}].{field}",
                    f"Evidence ref missing required field '{field}'")
        rid = ref.get("ref_id")
        if isinstance(rid, str) and rid:
            ref_id_set.add(rid)
        ch = ref.get("content_hash")
        if ch is None or ch == "" or (isinstance(ch, str) and ch.strip() == ""):
            add("warning", "content_hash_missing",
                f"$.raw_evidence_refs[{idx}].content_hash",
                "content_hash is null or empty",
                remediation_hint="Provide content_hash if available")
    return ref_id_set


def _check_claim_ledger(packet: dict, ref_id_set: set[str], add) -> None:
    claims = packet.get("claim_ledger", [])
    if not isinstance(claims, list):
        return
    for idx, claim in enumerate(claims):
        if not isinstance(claim, dict):
            add("error", "claim_required_field_missing",
                f"$.claim_ledger[{idx}]", "Claim must be an object")
            continue
        for field in missing_claim_fields(claim):
            if field not in claim:
                add("error", "claim_required_field_missing",
                    f"$.claim_ledger[{idx}].{field}",
                    f"Claim missing required field '{field}'")
        status = claim.get("status")
        if isinstance(status, str) and not is_allowed_claim_status(status):
            add("error", "claim_status_invalid",
                f"$.claim_ledger[{idx}].status",
                f"Claim status must be one of {sorted(ALLOWED_CLAIM_STATUSES)}, got '{status}'")
        ev_refs = claim.get("evidence_refs", [])
        if isinstance(ev_refs, list):
            for er in ev_refs:
                if isinstance(er, str) and er not in ref_id_set:
                    add("error", "claim_evidence_ref_missing",
                        f"$.claim_ledger[{idx}].evidence_refs",
                        f"Claim references unknown evidence ref '{er}'")


def _check_authority(packet: dict, add) -> None:
    auth = packet.get("authority_state")
    if auth is None or not isinstance(auth, dict):
        add("error", "authority_state_missing", "$.authority_state",
            "authority_state is required")
        return
    for lock in missing_authority_locks(auth):
        add("error", "authority_lock_missing", f"$.authority_state.{lock}",
            f"Authority lock '{lock}' is missing from authority_state")
    true_locks = authority_locks_true(auth)
    for lock in REQUIRED_AUTHORITY_LOCKS:
        if lock not in true_locks:
            continue
        ec = packet.get("evidence_class", "")
        bl = packet.get("boundary_label", "")
        preflight = is_preflight_evidence_class(ec) or "PREFLIGHT ONLY" in str(bl)
        if preflight or str(ec):
            add("error", "authority_lock_true_for_preflight",
                f"$.authority_state.{lock}",
                f"Authority lock '{lock}' is true in a preflight-only packet")


def _check_invariant_checks(packet: dict, add) -> None:
    invs = packet.get("invariant_checks", [])
    if not isinstance(invs, list):
        return
    for idx, inv in enumerate(invs):
        if not isinstance(inv, dict):
            continue
        for field in missing_invariant_check_fields(inv):
            if field not in inv:
                add("error", "invariant_required_field_missing",
                    f"$.invariant_checks[{idx}].{field}",
                    f"Invariant check missing required field '{field}'")


def _check_uncertainty(packet: dict, add) -> None:
    rd = packet.get("review_depth", "")
    unc = packet.get("uncertainty", [])
    if rd in ("high", "xhigh") and isinstance(unc, list) and len(unc) == 0:
        add("warning", "uncertainty_missing_for_depth",
            "$.uncertainty",
            f"uncertainty is empty for review_depth={rd}",
            remediation_hint="Add uncertainty entries or consider using medium/light depth")


def _check_forbidden_interpretations(packet: dict, add) -> None:
    fi = packet.get("forbidden_interpretations", [])
    if isinstance(fi, list) and len(fi) == 0:
        add("warning", "forbidden_interpretations_missing",
            "$.forbidden_interpretations",
            "forbidden_interpretations is empty",
            remediation_hint="Add forbidden interpretation entries")


def _check_next_gate(packet: dict, add) -> None:
    ngo = packet.get("next_gate_options", [])
    if isinstance(ngo, list) and len(ngo) == 0:
        add("warning", "next_gate_options_missing",
            "$.next_gate_options",
            "next_gate_options is empty",
            remediation_hint="Add next gate options")
    rng = packet.get("recommended_next_gate")
    if not rng or not isinstance(rng, str) or not rng.strip():
        add("warning", "recommended_next_gate_missing",
            "$.recommended_next_gate",
            "recommended_next_gate is missing or empty",
            remediation_hint="Set a recommended_next_gate")


def _check_loop_policy(packet: dict, add) -> None:
    lp = packet.get("loop_policy")
    if lp is None or not isinstance(lp, dict):
        add("error", "loop_policy_missing", "$.loop_policy",
            "loop_policy is required")
        return
    for field in missing_loop_policy_fields(lp):
        if field not in lp:
            add("error", "loop_policy_missing", f"$.loop_policy.{field}",
                f"loop_policy missing required field '{field}'")
    if lp.get("recursive_autonomous_loop_allowed") is True:
        add("error", "recursive_loop_allowed",
            "$.loop_policy.recursive_autonomous_loop_allowed",
            "recursive_autonomous_loop_allowed must not be true",
            remediation_hint="Set recursive_autonomous_loop_allowed to false")


def _check_boundary_label(packet: dict, add) -> None:
    bl = packet.get("boundary_label")
    if not bl or not isinstance(bl, str) or not bl.strip():
        add("error", "boundary_label_missing", "$.boundary_label",
            "boundary_label is missing or empty")
        return
    if not packet_declares_boundary_label({"boundary_label": bl}):
        missing_lines = [line for line in BOUNDARY_LABEL.splitlines() if line not in bl]
        add("error", "boundary_label_missing", "$.boundary_label",
            f"boundary_label missing required lines: {missing_lines}")


def _check_release_guardrails(raw_text: str, add) -> None:
    # Parse the packet to extract only human-facing text fields for scanning.
    # Scanning raw JSON catches field names like "plan_execution_allowed" which
    # are not human-facing claims.
    try:
        packet = json.loads(raw_text)
    except (json.JSONDecodeError, TypeError):
        return
    summary = str(packet.get("reduced_summary", "")).lower()
    text_to_scan = summary
    # Also scan claim texts
    claims = packet.get("claim_ledger", [])
    if isinstance(claims, list):
        for claim in claims:
            if isinstance(claim, dict):
                text_to_scan += " " + str(claim.get("claim", "")).lower()
    text_lower = text_to_scan
    for _pattern, tag in _RISKY_CLAIM_PATTERNS:
        if tag not in text_lower:
            continue
        idx = text_lower.find(tag)
        start = max(0, idx - 80)
        end = min(len(text_lower), idx + len(tag) + 80)
        context = text_lower[start:end]
        if not _is_negatively_framed(context):
            add("warning", "release_claim_expansion_risk",
                "$",
                f"Packet text may contain unqualified claim about '{tag}' without negative framing",
                remediation_hint=f"Ensure claims about '{tag}' include forbidden/negative framing")


def _check_static_fixture_marker(packet: dict, packet_path: str, add) -> None:
    pp = str(Path(packet_path).as_posix())
    if "/fixtures/" not in pp and "fixtures/" not in pp:
        return
    prov = packet.get("provenance", {})
    if isinstance(prov, dict) and prov.get("static_fixture") is not True:
        add("warning", "static_fixture_marker_missing",
            "$.provenance.static_fixture",
            "Fixture file under fixtures/ should declare static_fixture: true in provenance",
            remediation_hint="Set provenance.static_fixture to true")


# ---------------------------------------------------------------------------
# Result builder
# ---------------------------------------------------------------------------

def _build_result(
    packet_ref: str,
    result: str,
    issues: list[dict[str, str]],
) -> dict[str, Any]:
    return {
        "schema_version": STATIC_VALIDATION_RESULT_SCHEMA_VERSION,
        "validated_packet_ref": packet_ref,
        "validator_contract_version": VALIDATOR_VERSION,
        "result": result,
        "issue_count": len(issues),
        "issues": issues,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "checked_by": SCRIPT_ID,
        "limits": {
            "max_issues": 1000,
            "severity_filter": "all",
        },
    }


def validate_packet_file(packet_file: Path) -> dict[str, Any]:
    """Validate a GuardianEvidencePacket JSON file.

    Returns a GuardianEvidencePacketStaticValidationResult dict.
    Import-friendly wrapper for use by batch validators and other tools.
    """
    return validate_packet(str(packet_file))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate a GuardianEvidencePacket JSON fixture."
    )
    parser.add_argument("packet_path", help="Path to the packet JSON file")
    parser.add_argument("--json", action="store_true",
                        help="Output GuardianEvidencePacketStaticValidationResult as JSON")
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress summary text output")
    args = parser.parse_args(argv)

    result = validate_packet(args.packet_path)

    if args.json:
        print(json.dumps(result, indent=2))
    elif not args.quiet:
        status = result["result"]
        count = result["issue_count"]
        print(f"Validation {status} ({count} issue(s))")
        for issue in result["issues"]:
            print(f"  [{issue['severity'].upper()}] {issue['code']}: {issue['message']}")
        if status == "pass":
            print("Packet passed static validation.")

    if result["result"] == "fail":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
