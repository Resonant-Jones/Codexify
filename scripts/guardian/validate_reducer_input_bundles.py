#!/usr/bin/env python3
"""Validate all known Guardian Evidence Reducer input-bundle JSON files."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.guardian.validate_reducer_input_bundle import validate_bundle_file


RESULT_SCHEMA_VERSION = "guardian_evidence_reducer_input_bundle_batch_validation_result.v1"
VALIDATOR_CONTRACT_VERSION = "guardian_evidence_reducer_input_bundle_static_validator_contract.v1"
CHECKED_BY = "scripts/guardian/validate_reducer_input_bundles.py"
FILE_GLOB = "guardian-evidence-reducer-input-bundle*.json"
EMPTY_DISCOVERY_CODE = "input_bundle_files_missing"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def discover_bundle_files(templates_dir: Path, fixtures_dir: Path) -> list[Path]:
    """Return matching template and fixture paths in deterministic order."""
    paths = {
        path
        for directory in (templates_dir, fixtures_dir)
        for path in directory.glob(FILE_GLOB)
        if path.is_file()
    }
    return sorted(paths, key=lambda path: path.as_posix())


def validate_bundles(templates_dir: Path, fixtures_dir: Path) -> dict[str, Any]:
    """Aggregate single-file validation results without reading source refs."""
    files = []
    for path in discover_bundle_files(templates_dir, fixtures_dir):
        result = validate_bundle_file(path)
        files.append(
            {
                "path": str(path),
                "result": result["result"],
                "issue_count": result["issue_count"],
                "issues": result["issues"],
            }
        )

    batch_issues: list[dict[str, Any]] = []
    if not files:
        batch_issues.append(
            {
                "issue_id": "issue-0001",
                "severity": "error",
                "code": EMPTY_DISCOVERY_CODE,
                "path": "$.files",
                "message": f"No files matched {FILE_GLOB} in the configured directories.",
                "input_ref": "",
                "remediation_hint": "Provide a template or fixture matching the bundle filename pattern.",
            }
        )

    pass_count = sum(entry["result"] == "pass" for entry in files)
    warning_count = sum(entry["result"] == "pass_with_warnings" for entry in files)
    fail_count = sum(entry["result"] == "fail" for entry in files)
    file_issue_count = sum(entry["issue_count"] for entry in files)
    issue_count = file_issue_count + len(batch_issues)

    if fail_count or batch_issues:
        result = "fail"
    elif warning_count:
        result = "pass_with_warnings"
    else:
        result = "pass"

    return {
        "schema_version": RESULT_SCHEMA_VERSION,
        "validator_contract_version": VALIDATOR_CONTRACT_VERSION,
        "result": result,
        "matched_count": len(files),
        "pass_count": pass_count,
        "warning_count": warning_count,
        "fail_count": fail_count,
        "issue_count": issue_count,
        "validated_at": _now(),
        "checked_by": CHECKED_BY,
        "files": files,
        "issues": batch_issues,
        "limits": {
            "fixture_glob": FILE_GLOB,
            "max_files": 1000,
            "reads_source_ref_targets": False,
            "writes_files": False,
            "executes": False,
        },
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate Guardian Evidence Reducer input-bundle templates and fixtures."
    )
    parser.add_argument("--json", action="store_true", dest="as_json", help="emit JSON result")
    parser.add_argument("--templates-dir", type=Path, default=Path("docs/architecture/templates"))
    parser.add_argument("--fixtures-dir", type=Path, default=Path("docs/architecture/fixtures"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    result = validate_bundles(args.templates_dir, args.fixtures_dir)
    if args.as_json:
        print(json.dumps(result, indent=2))
    else:
        print(f"{result['result']}: {result['matched_count']} input bundles ({result['issue_count']} issues)")
    return 1 if result["result"] == "fail" else 0


if __name__ == "__main__":
    sys.exit(main())
