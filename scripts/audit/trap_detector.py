#!/usr/bin/env python3
"""Trap detector for regression prevention audit.

Implements heuristic detection for the 10 preventable traps from the audit framework.
Each detector emits warning, review, or critical-review level findings.

Exit codes:
  0 - Success (report-only mode, or no traps detected)
  1 - Enforce mode and deterministic trap detected (not implemented in Pass 2)

Usage:
  python scripts/audit/trap_detector.py              # Run all detectors
  python scripts/audit/trap_detector.py --trap 3,5   # Run specific traps
  python scripts/audit/trap_detector.py --suppress TRAP-3  # Override specific trap
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# Add repo root to path for imports
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.audit.lib.config import DEFAULT_CONFIG_PATH, AuditConfig
from scripts.audit.lib.git_utils import get_changed_files

DEFAULT_OUTPUT_DIR = REPO_ROOT / "docs" / "audits" / "regression"


@dataclass
class TrapFinding:
    """A single trap detection finding."""

    trap_id: str
    trap_name: str
    level: str  # warning, review, critical-review
    files: list[str]
    message: str
    false_positive_risk: str
    false_negative_risk: str
    how_to_override: str
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "trap_id": self.trap_id,
            "trap_name": self.trap_name,
            "level": self.level,
            "files": self.files,
            "message": self.message,
            "false_positive_risk": self.false_positive_risk,
            "false_negative_risk": self.false_negative_risk,
            "how_to_override": self.how_to_override,
            "evidence": self.evidence,
        }


# Trap definitions with metadata
TRAP_DEFINITIONS = {
    "TRAP-1": {
        "name": "Framework-as-Architecture",
        "description": "Business logic buried in framework-specific files",
        "false_positive_risk": "High - may flag legitimate adapter code",
        "false_negative_risk": "Medium - may miss logic in unusual patterns",
        "how_to_override": "Add comment '#audit:framework-logic-intentional' or update config to exclude path",
    },
    "TRAP-2": {
        "name": "Prompt-as-Orchestrator",
        "description": "Routing and control flow depend on prompt wording",
        "false_positive_risk": "Medium - may flag complex but valid prompts",
        "false_negative_risk": "High - cannot detect semantic routing intent",
        "how_to_override": "Add comment '#audit:prompt-routing-intentional' or move logic to code",
    },
    "TRAP-3": {
        "name": "Silent Retrieval Drift",
        "description": "Retrieval changes without eval updates",
        "false_positive_risk": "Low",
        "false_negative_risk": "Medium - may miss subtle embedding changes",
        "how_to_override": "Update eval file or add '#audit:retrieval-evaluated' comment",
    },
    "TRAP-4": {
        "name": "Identity Bleed",
        "description": "Context crosses identity boundaries",
        "false_positive_risk": "Medium - may flag internal-only code",
        "false_negative_risk": "High - cannot detect runtime leakage",
        "how_to_override": "Add explicit scope tagging or '#audit:identity-verified' comment",
    },
    "TRAP-5": {
        "name": "Tool Power Without Governance",
        "description": "Tools available without audit logging",
        "false_positive_risk": "Low",
        "false_negative_risk": "Medium - may miss custom logging implementations",
        "how_to_override": "Add audit logging or '#audit:tool-governed' comment",
    },
    "TRAP-6": {
        "name": "Evaluation Theater",
        "description": "Tests only cover happy paths",
        "false_positive_risk": "High - cannot know intent",
        "false_negative_risk": "Medium - may miss error case gaps",
        "how_to_override": "Add error case tests or '#audit:eval-comprehensive' comment",
    },
    "TRAP-7": {
        "name": "Adapter Illusion",
        "description": "Provider-specific code outside adapter layers",
        "false_positive_risk": "Medium - may flag intentional provider features",
        "false_negative_risk": "Medium - may miss subtle coupling",
        "how_to_override": "Refactor into adapters or '#audit:adapter-pattern-verified' comment",
    },
    "TRAP-8": {
        "name": "Orchestration by Accumulated Exceptions",
        "description": "Inconsistent retry and error handling patterns",
        "false_positive_risk": "High - may flag intentional variation",
        "false_negative_risk": "Medium - may miss inconsistent patterns",
        "how_to_override": "Standardize patterns or '#audit:retry-pattern-intentional' comment",
    },
    "TRAP-9": {
        "name": "No Blast Radius Model",
        "description": "High-risk changes without risk assessment",
        "false_positive_risk": "Low",
        "false_negative_risk": "Low - but only catches obvious cases",
        "how_to_override": "Update risk matrix or add '#audit:risk-assessed' comment",
    },
    "TRAP-10": {
        "name": "Complexity Prestige",
        "description": "Unjustified subsystem growth",
        "false_positive_risk": "Medium - growth may be justified",
        "false_negative_risk": "Low",
        "how_to_override": "Document justification or '#audit:complexity-justified' comment",
    },
}


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Detect preventable traps in codebase.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           # Run all trap detectors
  %(prog)s --trap 3,5,7              # Run specific traps
  %(prog)s --suppress TRAP-3         # Override/skip specific trap
  %(prog)s --format json             # Output JSON to stdout
        """,
    )
    parser.add_argument(
        "--trap",
        type=str,
        help="Comma-separated trap IDs to run (e.g., '3,5,7')",
    )
    parser.add_argument(
        "--suppress",
        type=str,
        action="append",
        help="Trap ID(s) to suppress (can be used multiple times)",
    )
    parser.add_argument(
        "--base",
        default="main",
        help="Base branch for change detection (default: %(default)s)",
    )
    parser.add_argument(
        "--head",
        default="HEAD",
        help="Head branch for change detection (default: %(default)s)",
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
        "--format",
        choices=["json", "md"],
        help="Output format to stdout (default: write both files)",
    )
    parser.add_argument(
        "--enforce",
        action="store_true",
        help="Fail on critical-review findings (not implemented in Pass 2)",
    )
    return parser.parse_args()


def get_trap_ids_to_run(args_trap: str | None) -> list[str]:
    """Get list of trap IDs to run."""
    if args_trap:
        ids = []
        for part in args_trap.split(","):
            part = part.strip()
            if part.isdigit():
                ids.append(f"TRAP-{part}")
            elif part.startswith("TRAP-"):
                ids.append(part)
        return ids
    return list(TRAP_DEFINITIONS.keys())


def trap_1_framework_as_architecture(
    changed_files: list[str], config: AuditConfig
) -> TrapFinding | None:
    """Detect business logic in framework-specific files.

    Looks for:
    - Business logic in FastAPI/Flask decorator-heavy files
    - Complex conditionals in route handlers
    - Direct framework imports in business logic
    """
    findings: list[str] = []
    evidence: dict[str, Any] = {"framework_patterns": [], "files_checked": []}

    framework_patterns = [
        (r"@app\.(route|get|post|put|delete)", "fastapi/flask routes"),
        (r"from fastapi import|from flask import", "framework imports"),
        (r"@router\.", "APIRouter decoration"),
    ]

    for file_path in changed_files:
        if not file_path.endswith(".py"):
            continue

        full_path = REPO_ROOT / file_path
        if not full_path.exists():
            continue

        evidence["files_checked"].append(file_path)

        try:
            content = full_path.read_text(encoding="utf-8")

            # Check for framework patterns
            for pattern, desc in framework_patterns:
                if re.search(pattern, content):
                    evidence["framework_patterns"].append(
                        f"{file_path}: {desc}"
                    )

            # Look for complex business logic in framework files
            # (heuristic: conditionals + database operations in same file)
            has_conditionals = len(re.findall(r"\bif\s+", content)) > 5
            has_db_ops = (
                "session" in content
                or "query" in content
                or "models." in content
            )

            if has_conditionals and has_db_ops:
                findings.append(file_path)

        except Exception:
            pass

    if findings:
        return TrapFinding(
            trap_id="TRAP-1",
            trap_name=TRAP_DEFINITIONS["TRAP-1"]["name"],
            level="warning",
            files=findings[:5],
            message=f"Potential business logic in framework files: {len(findings)} files",
            false_positive_risk=TRAP_DEFINITIONS["TRAP-1"][
                "false_positive_risk"
            ],
            false_negative_risk=TRAP_DEFINITIONS["TRAP-1"][
                "false_negative_risk"
            ],
            how_to_override=TRAP_DEFINITIONS["TRAP-1"]["how_to_override"],
            evidence=evidence,
        )
    return None


def trap_2_prompt_as_orchestrator(
    changed_files: list[str], config: AuditConfig
) -> TrapFinding | None:
    """Detect routing and control flow in prompts.

    Looks for:
    - Conditional keywords in prompt files
    - Routing instructions in prompts
    - Complex decision trees in prompt text
    """
    findings: list[str] = []
    evidence: dict[str, Any] = {"prompt_patterns": []}

    prompt_patterns = [
        (
            r"\b(if|else|then|otherwise)\b.*\b(route|select|choose|decide)\b",
            "conditional routing",
        ),
        (
            r"\b(you should|the system must|if the user)\b.*\b(then|otherwise)\b",
            "imperative conditionals",
        ),
        (
            r"\b(step 1|first|then|next|finally)\b.*\b(if|when|depending)\b",
            "conditional steps",
        ),
    ]

    for file_path in changed_files:
        # Check common prompt file patterns
        if not any(
            x in file_path.lower() for x in ["prompt", "template", "system"]
        ):
            continue

        full_path = REPO_ROOT / file_path
        if not full_path.exists():
            continue

        try:
            content = full_path.read_text(encoding="utf-8").lower()

            for pattern, desc in prompt_patterns:
                if re.search(pattern, content):
                    findings.append(file_path)
                    evidence["prompt_patterns"].append(f"{file_path}: {desc}")
                    break

        except Exception:
            pass

    if findings:
        return TrapFinding(
            trap_id="TRAP-2",
            trap_name=TRAP_DEFINITIONS["TRAP-2"]["name"],
            level="review",
            files=list(set(findings))[:5],
            message=f"Potential prompt-as-orchestrator patterns: {len(findings)} files",
            false_positive_risk=TRAP_DEFINITIONS["TRAP-2"][
                "false_positive_risk"
            ],
            false_negative_risk=TRAP_DEFINITIONS["TRAP-2"][
                "false_negative_risk"
            ],
            how_to_override=TRAP_DEFINITIONS["TRAP-2"]["how_to_override"],
            evidence=evidence,
        )
    return None


def trap_3_silent_retrieval_drift(
    changed_files: list[str], config: AuditConfig
) -> TrapFinding | None:
    """Flag retrieval changes without eval updates.

    Looks for:
    - Changes to embedding/retrieval code without eval file changes
    - Vector store changes without corresponding tests
    """
    retrieval_files: list[str] = []
    eval_files_changed: list[str] = []
    evidence: dict[str, Any] = {"retrieval_patterns": []}

    retrieval_patterns = [
        "embedding",
        "retrieval",
        "vector",
        "similarity",
        "index",
        "guardian/services/document_embed",
        "guardian/services/retrieval",
    ]

    eval_patterns = ["eval", "test_retrieval", "test_embedding", "benchmark"]

    for file_path in changed_files:
        path_lower = file_path.lower()

        # Check if this is a retrieval-related change
        if any(p in path_lower for p in retrieval_patterns):
            retrieval_files.append(file_path)
            evidence["retrieval_patterns"].append(file_path)

        # Check if eval files were updated
        if any(p in path_lower for p in eval_patterns):
            eval_files_changed.append(file_path)

    if retrieval_files and not eval_files_changed:
        return TrapFinding(
            trap_id="TRAP-3",
            trap_name=TRAP_DEFINITIONS["TRAP-3"]["name"],
            level="review",
            files=retrieval_files[:5],
            message=f"Retrieval changes ({len(retrieval_files)} files) without eval updates",
            false_positive_risk=TRAP_DEFINITIONS["TRAP-3"][
                "false_positive_risk"
            ],
            false_negative_risk=TRAP_DEFINITIONS["TRAP-3"][
                "false_negative_risk"
            ],
            how_to_override=TRAP_DEFINITIONS["TRAP-3"]["how_to_override"],
            evidence=evidence,
        )
    return None


def trap_4_identity_bleed(
    changed_files: list[str], config: AuditConfig
) -> TrapFinding | None:
    """Check for missing identity scope tagging.

    Looks for:
    - Route/agent files without identity annotations
    - Missing scope markers in boundary-crossing code
    """
    findings: list[str] = []
    evidence: dict[str, Any] = {
        "files_without_identity": [],
        "files_checked": [],
    }

    identity_markers = config.identity_marker_patterns.get(
        "expected_annotations", []
    )
    check_paths = config.identity_marker_patterns.get("check_paths", [])

    for file_path in changed_files:
        if not file_path.endswith(".py"):
            continue

        # Only check files in specified paths
        if not any(cp in file_path for cp in check_paths):
            continue

        full_path = REPO_ROOT / file_path
        if not full_path.exists():
            continue

        evidence["files_checked"].append(file_path)

        try:
            content = full_path.read_text(encoding="utf-8")

            # Check for identity markers
            has_marker = any(marker in content for marker in identity_markers)

            if not has_marker:
                findings.append(file_path)
                evidence["files_without_identity"].append(file_path)

        except Exception:
            pass

    if findings:
        return TrapFinding(
            trap_id="TRAP-4",
            trap_name=TRAP_DEFINITIONS["TRAP-4"]["name"],
            level="review",
            files=findings[:5],
            message=f"Files without identity markers: {len(findings)} files",
            false_positive_risk=TRAP_DEFINITIONS["TRAP-4"][
                "false_positive_risk"
            ],
            false_negative_risk=TRAP_DEFINITIONS["TRAP-4"][
                "false_negative_risk"
            ],
            how_to_override=TRAP_DEFINITIONS["TRAP-4"]["how_to_override"],
            evidence=evidence,
        )
    return None


def trap_5_tool_power_without_governance(
    changed_files: list[str], config: AuditConfig
) -> TrapFinding | None:
    """Detect tools without audit logging.

    Looks for:
    - Tool definitions without audit log calls
    - Tool execution without scope/trace markers
    """
    findings: list[str] = []
    evidence: dict[str, Any] = {"tools_without_logging": []}

    audit_patterns = [
        "audit_log",
        "log_audit",
        "audit(",
        "trace_id",
        "correlation_id",
        "scope=",
    ]

    for file_path in changed_files:
        if not file_path.endswith(".py"):
            continue

        # Focus on tools and routes
        if "tool" not in file_path.lower() and "route" not in file_path.lower():
            continue

        full_path = REPO_ROOT / file_path
        if not full_path.exists():
            continue

        try:
            content = full_path.read_text(encoding="utf-8")

            # Check for tool-like patterns
            has_tool_def = "def " in content and (
                "tool" in content.lower() or "@router" in content
            )
            has_audit = any(pattern in content for pattern in audit_patterns)

            if has_tool_def and not has_audit:
                findings.append(file_path)
                evidence["tools_without_logging"].append(file_path)

        except Exception:
            pass

    if findings:
        return TrapFinding(
            trap_id="TRAP-5",
            trap_name=TRAP_DEFINITIONS["TRAP-5"]["name"],
            level="warning",
            files=findings[:5],
            message=f"Potential tools without audit logging: {len(findings)} files",
            false_positive_risk=TRAP_DEFINITIONS["TRAP-5"][
                "false_positive_risk"
            ],
            false_negative_risk=TRAP_DEFINITIONS["TRAP-5"][
                "false_negative_risk"
            ],
            how_to_override=TRAP_DEFINITIONS["TRAP-5"]["how_to_override"],
            evidence=evidence,
        )
    return None


def trap_6_evaluation_theater(
    changed_files: list[str], config: AuditConfig
) -> TrapFinding | None:
    """Check for tests without error cases.

    Looks for:
    - Test files with only success cases
    - Missing error/exception test coverage
    """
    findings: list[str] = []
    evidence: dict[str, Any] = {"tests_without_errors": []}

    for file_path in changed_files:
        if not file_path.endswith(".py"):
            continue

        if not config.is_test_file(file_path):
            continue

        full_path = REPO_ROOT / file_path
        if not full_path.exists():
            continue

        try:
            content = full_path.read_text(encoding="utf-8")

            # Count test functions
            test_funcs = len(re.findall(r"^def test_", content, re.MULTILINE))

            # Look for error case patterns
            error_patterns = [
                r"pytest\.raises",
                r"with self\.assertRaises",
                r"except.*Error",
                r"Error.*expected",
                r"should.*raise",
                r"should.*fail",
            ]
            has_error_cases = any(re.search(p, content) for p in error_patterns)

            if test_funcs > 0 and not has_error_cases:
                findings.append(file_path)
                evidence["tests_without_errors"].append(
                    {
                        "file": file_path,
                        "test_functions": test_funcs,
                    }
                )

        except Exception:
            pass

    if findings:
        return TrapFinding(
            trap_id="TRAP-6",
            trap_name=TRAP_DEFINITIONS["TRAP-6"]["name"],
            level="review",
            files=findings[:5],
            message=f"Tests without error cases: {len(findings)} files",
            false_positive_risk=TRAP_DEFINITIONS["TRAP-6"][
                "false_positive_risk"
            ],
            false_negative_risk=TRAP_DEFINITIONS["TRAP-6"][
                "false_negative_risk"
            ],
            how_to_override=TRAP_DEFINITIONS["TRAP-6"]["how_to_override"],
            evidence=evidence,
        )
    return None


def trap_7_adapter_illusion(
    changed_files: list[str], config: AuditConfig
) -> TrapFinding | None:
    """Detect provider-specific code outside adapters.

    Looks for:
    - Direct provider SDK imports outside adapter directories
    - Provider-specific error handling outside adapters
    """
    findings: list[str] = []
    evidence: dict[str, Any] = {"provider_patterns": []}

    provider_patterns = [
        (r"from anthropic import|import anthropic", "anthropic"),
        (r"from openai import|import openai", "openai"),
        (r"from google\.generativeai|import google\.generativeai", "google"),
        (r"boto3\.|import boto3", "aws/bedrock"),
    ]

    for file_path in changed_files:
        if not file_path.endswith(".py"):
            continue

        # Skip adapter files themselves
        if "adapter" in file_path.lower():
            continue

        full_path = REPO_ROOT / file_path
        if not full_path.exists():
            continue

        try:
            content = full_path.read_text(encoding="utf-8")

            for pattern, provider in provider_patterns:
                if re.search(pattern, content):
                    findings.append(file_path)
                    evidence["provider_patterns"].append(
                        f"{file_path}: {provider}"
                    )
                    break

        except Exception:
            pass

    if findings:
        return TrapFinding(
            trap_id="TRAP-7",
            trap_name=TRAP_DEFINITIONS["TRAP-7"]["name"],
            level="warning",
            files=list(set(findings))[:5],
            message=f"Provider-specific code outside adapters: {len(findings)} files",
            false_positive_risk=TRAP_DEFINITIONS["TRAP-7"][
                "false_positive_risk"
            ],
            false_negative_risk=TRAP_DEFINITIONS["TRAP-7"][
                "false_negative_risk"
            ],
            how_to_override=TRAP_DEFINITIONS["TRAP-7"]["how_to_override"],
            evidence=evidence,
        )
    return None


def trap_8_orchestration_by_exceptions(
    changed_files: list[str], config: AuditConfig
) -> TrapFinding | None:
    """Detect inconsistent retry and error handling patterns.

    Looks for:
    - Mixed retry strategies in similar contexts
    - Inconsistent timeout values
    - Different exception handling patterns
    """
    findings: list[str] = []
    evidence: dict[str, Any] = {"retry_patterns": {}}

    retry_patterns = [
        (r"retry\s*=\s*(\d+)", "retry count"),
        (r"@retry", "retry decorator"),
        (r"tenacity", "tenacity library"),
        (r"backoff\s*=", "backoff parameter"),
        (r"timeout\s*=\s*(\d+)", "timeout value"),
    ]

    files_with_retry: dict[str, list[str]] = {}

    for file_path in changed_files:
        if not file_path.endswith(".py"):
            continue

        full_path = REPO_ROOT / file_path
        if not full_path.exists():
            continue

        try:
            content = full_path.read_text(encoding="utf-8")

            found_patterns: list[str] = []
            for pattern, desc in retry_patterns:
                if re.search(pattern, content):
                    found_patterns.append(desc)

            if found_patterns:
                files_with_retry[file_path] = found_patterns

        except Exception:
            pass

    # Check for inconsistency across files
    if len(files_with_retry) > 1:
        pattern_sets = [set(patterns) for patterns in files_with_retry.values()]
        if len({str(s) for s in pattern_sets}) > 1:
            findings = list(files_with_retry.keys())[:5]
            evidence["retry_patterns"] = files_with_retry

            return TrapFinding(
                trap_id="TRAP-8",
                trap_name=TRAP_DEFINITIONS["TRAP-8"]["name"],
                level="review",
                files=findings,
                message=f"Inconsistent retry patterns across {len(files_with_retry)} files",
                false_positive_risk=TRAP_DEFINITIONS["TRAP-8"][
                    "false_positive_risk"
                ],
                false_negative_risk=TRAP_DEFINITIONS["TRAP-8"][
                    "false_negative_risk"
                ],
                how_to_override=TRAP_DEFINITIONS["TRAP-8"]["how_to_override"],
                evidence=evidence,
            )
    return None


def trap_9_no_blast_radius_model(
    changed_files: list[str], config: AuditConfig
) -> TrapFinding | None:
    """Flag high-risk changes without risk assessment.

    Looks for:
    - High blast radius files changed without risk doc updates
    - Core files changed without review markers
    """
    high_risk_changed: list[str] = []
    evidence: dict[str, Any] = {"high_risk_files": []}

    for file_path in changed_files:
        if config.is_high_blast_radius(file_path):
            high_risk_changed.append(file_path)
            evidence["high_risk_files"].append(file_path)

    # Check if risk docs were updated
    risk_docs_updated = any(
        "audit" in f or "risk" in f.lower() for f in changed_files
    )

    if high_risk_changed and not risk_docs_updated:
        return TrapFinding(
            trap_id="TRAP-9",
            trap_name=TRAP_DEFINITIONS["TRAP-9"]["name"],
            level="warning",
            files=high_risk_changed[:5],
            message=f"High blast radius changes without risk assessment: {len(high_risk_changed)} files",
            false_positive_risk=TRAP_DEFINITIONS["TRAP-9"][
                "false_positive_risk"
            ],
            false_negative_risk=TRAP_DEFINITIONS["TRAP-9"][
                "false_negative_risk"
            ],
            how_to_override=TRAP_DEFINITIONS["TRAP-9"]["how_to_override"],
            evidence=evidence,
        )
    return None


def trap_10_complexity_prestige(
    changed_files: list[str], config: AuditConfig
) -> TrapFinding | None:
    """Track subsystem count growth.

    Looks for:
    - New subsystem additions
    - Unjustified complexity increases
    """
    evidence: dict[str, Any] = {"new_subsystems": [], "current_counts": {}}

    # Count files per subsystem
    subsystem_counts: dict[str, int] = {}
    for file_path in changed_files:
        subsystem = config.get_subsystem_for_path(file_path)
        if subsystem:
            subsystem_counts[subsystem] = subsystem_counts.get(subsystem, 0) + 1

    evidence["current_counts"] = subsystem_counts

    # Heuristic: flag if many subsystems touched at once
    if len(subsystem_counts) > 3:
        return TrapFinding(
            "TRAP-10",
            TRAP_DEFINITIONS["TRAP-10"]["name"],
            "warning",
            list(subsystem_counts.keys())[:5],
            f"Changes span {len(subsystem_counts)} subsystems - consider if justified",
            TRAP_DEFINITIONS["TRAP-10"]["false_positive_risk"],
            TRAP_DEFINITIONS["TRAP-10"]["false_negative_risk"],
            TRAP_DEFINITIONS["TRAP-10"]["how_to_override"],
            evidence,
        )
    return None


# Map trap IDs to detector functions
TRAP_DETECTORS = {
    "TRAP-1": trap_1_framework_as_architecture,
    "TRAP-2": trap_2_prompt_as_orchestrator,
    "TRAP-3": trap_3_silent_retrieval_drift,
    "TRAP-4": trap_4_identity_bleed,
    "TRAP-5": trap_5_tool_power_without_governance,
    "TRAP-6": trap_6_evaluation_theater,
    "TRAP-7": trap_7_adapter_illusion,
    "TRAP-8": trap_8_orchestration_by_exceptions,
    "TRAP-9": trap_9_no_blast_radius_model,
    "TRAP-10": trap_10_complexity_prestige,
}


def run_detectors(
    trap_ids: list[str],
    changed_files: list[str],
    config: AuditConfig,
) -> list[TrapFinding]:
    """Run specified trap detectors."""
    findings: list[TrapFinding] = []

    for trap_id in trap_ids:
        detector = TRAP_DETECTORS.get(trap_id)
        if detector:
            result = detector(changed_files, config)
            if result:
                findings.append(result)

    return findings


def render_markdown(findings: list[TrapFinding]) -> str:
    """Render findings as Markdown."""
    lines: list[str] = []

    lines.append("# Trap Detection Report")
    lines.append("")
    lines.append(f"**Generated:** {datetime.now().isoformat()}")
    lines.append("")

    # Summary
    lines.append("## Summary")
    lines.append("")

    counts = {"warning": 0, "review": 0, "critical-review": 0}
    for f in findings:
        counts[f.level] = counts.get(f.level, 0) + 1

    lines.append(f"- **Warnings:** {counts['warning']}")
    lines.append(f"- **Reviews:** {counts['review']}")
    lines.append(f"- **Critical Reviews:** {counts['critical-review']}")
    lines.append("")

    if not findings:
        lines.append("✅ No traps detected.")
        lines.append("")
        return "\n".join(lines)

    # Findings by level
    for level in ["critical-review", "review", "warning"]:
        level_findings = [f for f in findings if f.level == level]
        if level_findings:
            lines.append(f"## {level.replace('-', ' ').title()} Findings")
            lines.append("")

            for finding in level_findings:
                lines.append(f"### {finding.trap_id}: {finding.trap_name}")
                lines.append("")
                lines.append(f"**Message:** {finding.message}")
                lines.append("")

                if finding.files:
                    lines.append("**Files:**")
                    for f in finding.files:
                        lines.append(f"- `{f}`")
                    lines.append("")

                lines.append(
                    f"**False Positive Risk:** {finding.false_positive_risk}"
                )
                lines.append(
                    f"**False Negative Risk:** {finding.false_negative_risk}"
                )
                lines.append("")
                lines.append(f"**How to Override:** {finding.how_to_override}")
                lines.append("")

    return "\n".join(lines)


def write_output(
    output_dir: Path, findings: list[TrapFinding]
) -> tuple[Path, Path]:
    """Write JSON and Markdown output files."""
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    json_path = output_dir / f"traps-{timestamp}.json"
    md_path = output_dir / f"traps-{timestamp}.md"

    # Prepare output data
    output_data = {
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "warning": sum(1 for f in findings if f.level == "warning"),
            "review": sum(1 for f in findings if f.level == "review"),
            "critical-review": sum(
                1 for f in findings if f.level == "critical-review"
            ),
            "total": len(findings),
        },
        "findings": [f.to_dict() for f in findings],
    }

    # Atomic write for JSON
    temp_json = json_path.with_suffix(".json.tmp")
    temp_json.write_text(
        json.dumps(output_data, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )
    temp_json.replace(json_path)

    # Atomic write for Markdown
    markdown = render_markdown(findings)
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

    # Get trap IDs to run
    trap_ids = get_trap_ids_to_run(args.trap)

    # Filter suppressed traps
    if args.suppress:
        suppressed = set(args.suppress)
        trap_ids = [t for t in trap_ids if t not in suppressed]

    # Get changed files
    changed_files = get_changed_files(args.base, args.head)

    # Run detectors
    findings = run_detectors(trap_ids, changed_files, config)

    # Render markdown
    markdown = render_markdown(findings)

    # Output based on format
    if args.format == "json":
        output_data = {
            "generated_at": datetime.now().isoformat(),
            "findings": [f.to_dict() for f in findings],
        }
        print(
            json.dumps(
                output_data, indent=2, sort_keys=True, ensure_ascii=False
            )
        )
    elif args.format == "md":
        print(markdown)
    else:
        # Write both files
        json_path, md_path = write_output(args.output_dir, findings)
        print(f"Wrote {json_path.relative_to(REPO_ROOT)}")
        print(f"Wrote {md_path.relative_to(REPO_ROOT)}")

        # Print summary
        counts = {"warning": 0, "review": 0, "critical-review": 0}
        for f in findings:
            counts[f.level] = counts.get(f.level, 0) + 1

        print(f"\nTrap Detection Summary:")
        print(f"  Total findings: {len(findings)}")
        print(f"  Warnings: {counts['warning']}")
        print(f"  Reviews: {counts['review']}")
        print(f"  Critical Reviews: {counts['critical-review']}")

    # Report-only mode always exits 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
