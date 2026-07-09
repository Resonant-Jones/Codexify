#!/usr/bin/env python3
"""Local batch validator for GuardianEvidencePacket JSON fixtures.

Discovers GuardianEvidencePacket fixture files under docs/architecture/fixtures
and validates each one using the same semantics as
scripts/guardian/validate_evidence_packet.py.

Usage:
  python3 scripts/guardian/validate_evidence_packets.py [--fixtures-dir DIR] [--json]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BATCH_SCHEMA_VERSION = "guardian_evidence_packet_batch_validation_result.v1"
BATCH_SCRIPT_ID = "scripts/guardian/validate_evidence_packets.py"
DEFAULT_FIXTURES_DIR = "docs/architecture/fixtures"
FIXTURE_GLOB = "guardian-evidence-packet*.json"


def discover_fixtures(fixtures_dir: Path) -> list[Path]:
    """Discover GuardianEvidencePacket fixture files, sorted by path."""
    if not fixtures_dir.is_dir():
        return []
    matches = sorted(fixtures_dir.glob(FIXTURE_GLOB))
    return matches


def _import_validate_packet_file():
    """Import validate_packet_file from the sibling single-validator script."""
    script_dir = Path(__file__).resolve().parent
    if str(script_dir) not in sys.path:
        sys.path.insert(0, str(script_dir))
    import validate_evidence_packet  # type: ignore[import-not-found]
    return validate_evidence_packet.validate_packet_file


def validate_batch(fixtures_dir: str) -> dict[str, Any]:
    """Validate all GuardianEvidencePacket fixtures in *fixtures_dir*.

    Returns a GuardianEvidencePacketBatchValidationResult dict.
    """
    dir_path = Path(fixtures_dir)
    discovered = discover_fixtures(dir_path)

    if not discovered:
        return {
            "schema_version": BATCH_SCHEMA_VERSION,
            "fixtures_dir": str(dir_path),
            "matched_count": 0,
            "result": "fail",
            "packet_results": [],
            "issue_count": 1,
            "error_count": 1,
            "warning_count": 0,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "checked_by": BATCH_SCRIPT_ID,
            "limits": {
                "max_fixtures": 1000,
                "fixture_glob": FIXTURE_GLOB,
                "issues": [{
                    "issue_id": "batch-no-fixtures",
                    "severity": "error",
                    "code": "batch_no_matching_fixtures",
                    "path": str(dir_path),
                    "message": f"No fixture files matching '{FIXTURE_GLOB}' found in {dir_path}",
                    "evidence_ref": "",
                    "remediation_hint": "Add GuardianEvidencePacket fixture files to the fixtures directory.",
                }],
            },
        }

    try:
        validate_fn = _import_validate_packet_file()
    except Exception as exc:
        return {
            "schema_version": BATCH_SCHEMA_VERSION,
            "fixtures_dir": str(dir_path),
            "matched_count": 0,
            "result": "fail",
            "packet_results": [],
            "issue_count": 1,
            "error_count": 1,
            "warning_count": 0,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "checked_by": BATCH_SCRIPT_ID,
            "limits": {
                "max_fixtures": 1000,
                "fixture_glob": FIXTURE_GLOB,
                "issues": [{
                    "issue_id": "batch-import-error",
                    "severity": "error",
                    "code": "batch_import_error",
                    "path": str(Path(__file__).resolve()),
                    "message": f"Cannot import single-validator: {exc}",
                    "evidence_ref": "",
                    "remediation_hint": "Ensure scripts/guardian/validate_evidence_packet.py is present and importable.",
                }],
            },
        }

    packet_results: list[dict[str, Any]] = []
    total_issues = 0
    total_errors = 0
    total_warnings = 0
    batch_failed = False

    for fixture_path in discovered:
        try:
            result = validate_fn(fixture_path)
        except Exception as exc:
            result = {
                "schema_version": "guardian_evidence_packet_static_validation_result.v1",
                "validated_packet_ref": str(fixture_path),
                "validator_contract_version": "guardian_evidence_packet_static_validator_contract.v1",
                "result": "fail",
                "issue_count": 1,
                "issues": [{
                    "issue_id": "batch-exec-error",
                    "severity": "error",
                    "code": "batch_execution_error",
                    "path": str(fixture_path),
                    "message": f"Validator raised exception: {exc}",
                    "evidence_ref": "",
                    "remediation_hint": "Check fixture file and validator script.",
                }],
                "checked_at": datetime.now(timezone.utc).isoformat(),
                "checked_by": BATCH_SCRIPT_ID,
                "limits": {"max_issues": 1000, "severity_filter": "all"},
            }
        packet_results.append(result)
        total_issues += result.get("issue_count", 0)
        if result.get("result") == "fail":
            batch_failed = True
            total_errors += sum(
                1 for i in result.get("issues", [])
                if i.get("severity") == "error"
            )
        else:
            total_errors += sum(
                1 for i in result.get("issues", [])
                if i.get("severity") == "error"
            )
        total_warnings += sum(
            1 for i in result.get("issues", [])
            if i.get("severity") == "warning"
        )

    if batch_failed:
        batch_result = "fail"
    elif total_warnings > 0:
        batch_result = "pass_with_warnings"
    else:
        batch_result = "pass"

    return {
        "schema_version": BATCH_SCHEMA_VERSION,
        "fixtures_dir": str(dir_path),
        "matched_count": len(discovered),
        "result": batch_result,
        "packet_results": packet_results,
        "issue_count": total_issues,
        "error_count": total_errors,
        "warning_count": total_warnings,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "checked_by": BATCH_SCRIPT_ID,
        "limits": {
            "max_fixtures": 1000,
            "fixture_glob": FIXTURE_GLOB,
        },
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Batch-validate GuardianEvidencePacket JSON fixtures."
    )
    parser.add_argument(
        "--fixtures-dir",
        default=DEFAULT_FIXTURES_DIR,
        help=f"Directory containing fixture files (default: {DEFAULT_FIXTURES_DIR})",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output GuardianEvidencePacketBatchValidationResult as JSON",
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="Suppress summary text output",
    )
    args = parser.parse_args(argv)

    result = validate_batch(args.fixtures_dir)

    if args.json:
        print(json.dumps(result, indent=2))
    elif not args.quiet:
        status = result["result"]
        matched = result["matched_count"]
        issues = result["issue_count"]
        errors = result["error_count"]
        warnings = result["warning_count"]
        print(f"Batch validation {status}: {matched} fixture(s), "
              f"{issues} issue(s) ({errors} error(s), {warnings} warning(s))")
        for pr in result.get("packet_results", []):
            ref = pr.get("validated_packet_ref", "?")
            r = pr.get("result", "?")
            c = pr.get("issue_count", 0)
            print(f"  [{r}] {ref} ({c} issue(s))")
        if status == "pass":
            print("All packets passed static validation.")

    if result["result"] == "fail":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
