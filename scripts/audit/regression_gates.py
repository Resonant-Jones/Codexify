#!/usr/bin/env python3
"""Regression gate checker for audit infrastructure.

This script performs automated checks for pre-merge, pre-release, and post-release
gates, outputting both automated results and required manual attestations.

Exit codes:
  0 - Success (report-only mode, or enforce mode with all deterministic checks passing)
  1 - Enforce mode failure (deterministic check failed)

Usage:
  python scripts/audit/regression_gates.py
  python scripts/audit/regression_gates.py --gate pre-merge
  python scripts/audit/regression_gates.py --gate pre-release --enforce
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Add repo root to path for imports
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.audit.lib.config import DEFAULT_CONFIG_PATH, AuditConfig
from scripts.audit.lib.git_utils import (
    check_migrations_present,
    check_risky_files_changed,
    check_tests_touched,
    get_changed_files,
    get_current_branch,
)

DEFAULT_OUTPUT_DIR = REPO_ROOT / "docs" / "audits" / "regression"


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Check regression gates.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           # Check all gates
  %(prog)s --gate pre-merge          # Check only pre-merge gate
  %(prog)s --gate pre-release        # Check only pre-release gate
  %(prog)s --enforce                 # Fail on deterministic check failures
        """,
    )
    parser.add_argument(
        "--gate",
        choices=["pre-merge", "pre-release", "post-release", "all"],
        default="all",
        help="Which gate to check (default: %(default)s)",
    )
    parser.add_argument(
        "--base",
        default="main",
        help="Base branch/ref (default: %(default)s)",
    )
    parser.add_argument(
        "--head",
        default="HEAD",
        help="Head branch/ref (default: %(default)s)",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="Path to config JSON (default: %(default)s)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Output directory (default: %(default)s)",
    )
    parser.add_argument(
        "--enforce",
        action="store_true",
        help="Fail if deterministic checks fail",
    )
    return parser.parse_args()


def check_changed_files(base: str, head: str) -> tuple[bool, list[str]]:
    """Check for changed files between base and head."""
    files = get_changed_files(base, head)
    return len(files) > 0, files


def check_tests_for_changed_files(
    files: list[str], config: AuditConfig
) -> dict[str, Any]:
    """Check if tests were touched for changed files."""
    has_tests, test_files = check_tests_touched(files, config)

    # Check if any non-test files lack test coverage
    non_test_files = [f for f in files if not config.is_test_file(f)]

    status = "pass" if has_tests else "warn"
    level = "info" if has_tests else "warning"

    return {
        "check": "tests_touched",
        "status": status,
        "level": level,
        "evidence": test_files,
        "message": f"Tests touched: {len(test_files)} files"
        if has_tests
        else "No test files changed",
        "files_without_tests": non_test_files if not has_tests else [],
    }


def check_migration_for_schema_changes(
    files: list[str], config: AuditConfig
) -> dict[str, Any]:
    """Check if migrations exist when schema files changed."""
    # Check if models.py or schema-related files changed
    schema_files = ["guardian/db/models.py"]
    schema_changed = any(
        fnmatch.fnmatch(f, pattern) for f in files for pattern in schema_files
    )

    has_migration, migration_files = check_migrations_present(files, config)

    if schema_changed and not has_migration:
        return {
            "check": "migration_present",
            "status": "fail",
            "level": "error",
            "evidence": [f for f in files if "models" in f],
            "message": "Schema files changed but no migration file found",
            "deterministic": True,
        }

    if has_migration:
        return {
            "check": "migration_present",
            "status": "pass",
            "level": "info",
            "evidence": migration_files,
            "message": f"Migration files present: {len(migration_files)}",
            "deterministic": True,
        }

    return {
        "check": "migration_present",
        "status": "pass",
        "level": "info",
        "evidence": [],
        "message": "No schema changes detected",
        "deterministic": True,
    }


def check_risk_matrix_updated(
    files: list[str], config: AuditConfig
) -> dict[str, Any]:
    """Check if risk docs were updated for high blast radius changes."""
    has_risky, risky_files = check_risky_files_changed(files, config)

    # Check if any audit-related files were updated
    audit_files_changed = any(
        fnmatch.fnmatch(f, "scripts/audit/data/*")
        or fnmatch.fnmatch(f, "docs/audits/regression/*")
        for f in files
    )

    if has_risky and not audit_files_changed:
        return {
            "check": "risk_docs_updated",
            "status": "warn",
            "level": "warning",
            "evidence": risky_files[:5],  # Limit output
            "message": f"High-blast-radius files changed ({len(risky_files)}) without risk matrix update",
            "deterministic": False,
        }

    if audit_files_changed:
        return {
            "check": "risk_docs_updated",
            "status": "pass",
            "level": "info",
            "evidence": [f for f in files if "audit" in f or "risk" in f],
            "message": "Risk matrix or audit files updated",
            "deterministic": False,
        }

    return {
        "check": "risk_docs_updated",
        "status": "pass",
        "level": "info",
        "evidence": [],
        "message": "No high-blast-radius changes",
        "deterministic": False,
    }


def check_migration_tests(config: AuditConfig) -> dict[str, Any]:
    """Check for migration test existence."""
    migration_test_paths = [
        "tests/test_migrations.py",
        "tests/migrations/",
        "guardian/db/migrations/test_",
    ]

    found = False
    evidence: list[str] = []
    for pattern in migration_test_paths:
        path = REPO_ROOT / pattern
        if path.exists():
            found = True
            evidence.append(pattern)

    return {
        "check": "migration_test_exists",
        "status": "pass" if found else "warn",
        "level": "info" if found else "warning",
        "evidence": evidence,
        "message": "Migration tests found"
        if found
        else "No migration tests detected",
        "deterministic": True,
    }


def check_tool_contract_files(config: AuditConfig) -> dict[str, Any]:
    """Best-effort check for tool contract documentation."""
    expected = config.tool_contract_patterns.get("expected_files", [])
    level = config.tool_contract_patterns.get("level", "warning")

    found: list[str] = []
    for path in expected:
        if (REPO_ROOT / path).exists():
            found.append(path)

    return {
        "check": "tool_contract_files",
        "status": "pass" if found else "warn",
        "level": "info" if found else level,
        "evidence": found,
        "message": f"Tool contract docs present: {len(found)}/{len(expected)}"
        if found
        else f"Expected tool contract docs not found (configurable check)",
        "deterministic": False,
        "note": "Best-effort check based on config",
    }


def check_identity_markers(config: AuditConfig) -> dict[str, Any]:
    """Best-effort check for identity isolation markers."""
    check_paths = config.identity_marker_patterns.get("check_paths", [])
    expected_annotations = config.identity_marker_patterns.get(
        "expected_annotations", []
    )
    level = config.identity_marker_patterns.get("level", "warning")

    # Very basic check: look for expected annotation patterns in files
    markers_found = 0
    checked_files = 0

    for path_pattern in check_paths:
        path = REPO_ROOT / path_pattern
        if path.exists():
            for py_file in path.rglob("*.py"):
                checked_files += 1
                try:
                    content = py_file.read_text(encoding="utf-8")
                    for annotation in expected_annotations:
                        if annotation in content:
                            markers_found += 1
                            break
                except Exception:
                    pass

    return {
        "check": "identity_markers",
        "status": "pass" if markers_found > 0 else "warn",
        "level": "info" if markers_found > 0 else level,
        "evidence": [f"{markers_found} files with markers"]
        if markers_found > 0
        else [],
        "message": f"Identity markers found in {markers_found}/{checked_files} files"
        if markers_found > 0
        else "Identity markers not detected (best-effort check)",
        "deterministic": False,
        "note": "Best-effort pattern matching; manual verification recommended",
    }


def check_queue_health_routes(config: AuditConfig) -> dict[str, Any]:
    """Best-effort check for queue/worker health routes."""
    health_routes = config.queue_worker_patterns.get("health_routes", [])
    level = config.queue_worker_patterns.get("level", "warning")

    # Check if health.py exists and contains queue/worker routes
    health_file = REPO_ROOT / "guardian" / "routes" / "health.py"
    found_routes: list[str] = []

    if health_file.exists():
        try:
            content = health_file.read_text(encoding="utf-8")
            for route in health_routes:
                if route in content:
                    found_routes.append(route)
        except Exception:
            pass

    return {
        "check": "queue_health_routes",
        "status": "pass" if found_routes else "warn",
        "level": "info" if found_routes else level,
        "evidence": found_routes,
        "message": f"Queue/worker health routes found: {len(found_routes)}/{len(health_routes)}"
        if found_routes
        else "Queue health routes not verified (best-effort check)",
        "deterministic": False,
        "note": "Best-effort check based on file content matching",
    }


def run_pre_merge_checks(
    files: list[str], config: AuditConfig
) -> dict[str, Any]:
    """Run pre-merge gate checks."""
    automated = []

    # Deterministic checks
    automated.append(check_tests_for_changed_files(files, config))
    automated.append(check_migration_for_schema_changes(files, config))
    automated.append(check_risk_matrix_updated(files, config))

    # Get manual attestations from config
    gate_config = config.gate_checks.get("pre_merge", {})
    required = gate_config.get("manual_attestations", {}).get("required", [])
    recommended = gate_config.get("manual_attestations", {}).get(
        "recommended", []
    )

    return {
        "automated_checks": automated,
        "required_manual_attestations": required,
        "recommended_manual_attestations": recommended,
    }


def run_pre_release_checks(config: AuditConfig) -> dict[str, Any]:
    """Run pre-release gate checks."""
    automated = []

    # Deterministic checks
    automated.append(check_migration_tests(config))

    # Best-effort checks
    automated.append(check_tool_contract_files(config))
    automated.append(check_identity_markers(config))
    automated.append(check_queue_health_routes(config))

    # Get manual attestations from config
    gate_config = config.gate_checks.get("pre_release", {})
    required = gate_config.get("manual_attestations", {}).get("required", [])
    recommended = gate_config.get("manual_attestations", {}).get(
        "recommended", []
    )

    return {
        "automated_checks": automated,
        "required_manual_attestations": required,
        "recommended_manual_attestations": recommended,
    }


def run_post_release_checks(config: AuditConfig) -> dict[str, Any]:
    """Run post-release gate checks."""
    # No automated checks for post-release
    # Get manual attestations from config
    gate_config = config.gate_checks.get("post_release", {})
    required = gate_config.get("manual_attestations", {}).get("required", [])
    recommended = gate_config.get("manual_attestations", {}).get(
        "recommended", []
    )

    return {
        "automated_checks": [],
        "required_manual_attestations": required,
        "recommended_manual_attestations": recommended,
    }


def generate_report(
    base: str,
    head: str,
    files: list[str],
    config: AuditConfig,
    gate_filter: str = "all",
) -> dict[str, Any]:
    """Generate gate check report."""
    report = {
        "generated_at": datetime.now().isoformat(),
        "base": base,
        "head": head,
        "mode": "enforce" if gate_filter == "enforce" else "report-only",
        "files_changed": len(files),
        "gates": {},
    }

    if gate_filter in ("pre-merge", "all"):
        report["gates"]["pre_merge"] = run_pre_merge_checks(files, config)

    if gate_filter in ("pre-release", "all"):
        report["gates"]["pre_release"] = run_pre_release_checks(config)

    if gate_filter in ("post-release", "all"):
        report["gates"]["post_release"] = run_post_release_checks(config)

    # Calculate exit recommendation
    deterministic_failures = 0
    for gate_name, gate_data in report["gates"].items():
        for check in gate_data.get("automated_checks", []):
            if check.get("deterministic") and check.get("status") == "fail":
                deterministic_failures += 1

    report["exit_recommendation"] = {
        "report_only": "proceed_with_review"
        if deterministic_failures == 0
        else "review_required",
        "enforce_mode": "would_pass"
        if deterministic_failures == 0
        else "would_fail",
        "deterministic_failures": deterministic_failures,
    }

    return report


def render_markdown(report: dict[str, Any]) -> str:
    """Render report as Markdown."""
    lines: list[str] = []

    lines.append("# Regression Gate Check Report")
    lines.append("")
    lines.append(f"**Generated:** {report['generated_at']}")
    lines.append(f"**Base:** `{report['base']}`")
    lines.append(f"**Head:** `{report['head']}`")
    lines.append(f"**Mode:** {report['mode']}")
    lines.append(f"**Files Changed:** {report['files_changed']}")
    lines.append("")

    # Summary
    lines.append("## Summary")
    lines.append("")
    exit_rec = report["exit_recommendation"]
    if exit_rec["deterministic_failures"] == 0:
        lines.append("✅ **All deterministic checks passed**")
    else:
        lines.append(
            f"⚠️ **{exit_rec['deterministic_failures']} deterministic check(s) failed**"
        )
    lines.append("")

    # Gates
    for gate_name, gate_data in report["gates"].items():
        lines.append(f"## {gate_name.replace('_', ' ').title()} Gate")
        lines.append("")

        # Automated checks
        if gate_data.get("automated_checks"):
            lines.append("### Automated Checks")
            lines.append("")
            lines.append("| Check | Status | Level | Message |")
            lines.append("|-------|--------|-------|---------|")
            for check in gate_data["automated_checks"]:
                status_icon = (
                    "✅"
                    if check["status"] == "pass"
                    else "⚠️"
                    if check["status"] == "warn"
                    else "❌"
                )
                lines.append(
                    f"| {check['check']} | {status_icon} {check['status']} | {check['level']} | {check['message']} |"
                )
            lines.append("")

        # Required attestations
        if gate_data.get("required_manual_attestations"):
            lines.append("### Required Manual Attestations")
            lines.append("")
            for att in gate_data["required_manual_attestations"]:
                lines.append(f"- **{att['id']}**: {att['description']}")
                lines.append(f"  - *Why manual: {att['rationale']}*")
            lines.append("")

        # Recommended attestations
        if gate_data.get("recommended_manual_attestations"):
            lines.append("### Recommended Manual Attestations")
            lines.append("")
            for att in gate_data["recommended_manual_attestations"]:
                lines.append(f"- **{att['id']}**: {att['description']}")
                lines.append(f"  - *Why manual: {att['rationale']}*")
            lines.append("")

    # Files changed
    if report.get("files_changed", 0) > 0:
        lines.append("## Files Changed")
        lines.append("")
        lines.append(f"Total: {report['files_changed']} files")
        lines.append("")

    return "\n".join(lines)


def write_output(
    output_dir: Path, report: dict[str, Any], markdown: str
) -> tuple[Path, Path]:
    """Write JSON and Markdown output files."""
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    json_path = output_dir / f"gates-{timestamp}.json"
    md_path = output_dir / f"gates-{timestamp}.md"

    # Atomic write for JSON
    temp_json = json_path.with_suffix(".json.tmp")
    temp_json.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )
    temp_json.replace(json_path)

    # Atomic write for Markdown
    temp_md = md_path.with_suffix(".md.tmp")
    temp_md.write_text(markdown, encoding="utf-8")
    temp_md.replace(md_path)

    return json_path, md_path


def main() -> int:
    """Main entry point."""
    args = parse_args()

    # Load config
    try:
        config = AuditConfig.from_file(args.config)
    except FileNotFoundError:
        print(f"Error: Config file not found: {args.config}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"Error: Invalid config JSON: {e}", file=sys.stderr)
        return 1

    # Get changed files
    has_changes, files = check_changed_files(args.base, args.head)

    # Generate report
    report = generate_report(
        base=args.base,
        head=args.head,
        files=files,
        config=config,
        gate_filter=args.gate,
    )

    # Render markdown
    markdown = render_markdown(report)

    # Write output
    json_path, md_path = write_output(args.output_dir, report, markdown)
    print(f"Wrote {json_path.relative_to(REPO_ROOT)}")
    print(f"Wrote {md_path.relative_to(REPO_ROOT)}")

    # Print summary
    exit_rec = report["exit_recommendation"]
    print(f"\nGate Check Summary:")
    print(f"  Files changed: {report['files_changed']}")
    print(f"  Deterministic failures: {exit_rec['deterministic_failures']}")
    print(f"  Report-only recommendation: {exit_rec['report_only']}")
    if args.enforce:
        print(f"  Enforce mode: {exit_rec['enforce_mode']}")

    # Determine exit code
    if args.enforce:
        # In enforce mode, fail on deterministic failures
        return 1 if exit_rec["deterministic_failures"] > 0 else 0
    else:
        # Report-only mode always exits 0
        return 0


if __name__ == "__main__":
    sys.exit(main())
