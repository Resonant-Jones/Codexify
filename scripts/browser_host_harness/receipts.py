"""Machine-readable and human-readable proof receipt contracts.

Provides:
- Typed candidate-proof receipt schema
- Scaffold self-test receipt schema
- JSON receipt writer with stable key ordering, atomic writes, and redaction
- Markdown summary writer
- Receipt validator
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .contracts import (
    CASE_STATUSES,
    CANDIDATE_STATUSES,
    CLEANUP_STATUSES,
    RECEIPT_KINDS,
    CaseStatus,
    CandidateStatus,
    CleanupStatus,
    ReceiptKind,
)

# ---------------------------------------------------------------------------
# Receipt validation
# ---------------------------------------------------------------------------


class ReceiptValidationError(Exception):
    """Raised when a receipt fails validation."""


def _iso_to_dt(iso_str: str) -> datetime | None:
    try:
        # Handle various ISO formats
        s = iso_str.replace("Z", "+00:00")
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None


_SECRET_VALUE_PATTERNS: list[re.Pattern] = [
    re.compile(r"CODEXIFY-HARNESS-SENTINEL-[a-f0-9]+-NOT-A-REAL-CREDENTIAL", re.IGNORECASE),
    re.compile(r"s3cret_p@ssw0rd", re.IGNORECASE),
    re.compile(r"hidden-csrf-token-value", re.IGNORECASE),
]


def _contains_secrets(value: Any, depth: int = 0) -> bool:
    """Recursively check if a JSON-serializable value contains secrets."""
    if depth > 10:
        return False
    if isinstance(value, str):
        for pat in _SECRET_VALUE_PATTERNS:
            if pat.search(value):
                return True
    elif isinstance(value, dict):
        for v in value.values():
            if _contains_secrets(v, depth + 1):
                return True
    elif isinstance(value, list):
        for item in value:
            if _contains_secrets(item, depth + 1):
                return True
    return False


def validate_receipt(receipt: dict) -> list[str]:
    """Validate a proof receipt against canonical constraints.

    Returns a list of validation error messages (empty list = valid).
    """
    errors: list[str] = []

    # Required top-level fields
    required = {
        "runId",
        "receiptKind",
        "harnessVersion",
        "fixtureVersion",
        "guardianStubVersion",
        "startedAt",
        "completedAt",
    }
    missing = required - set(receipt.keys())
    if missing:
        errors.append(f"missing required fields: {sorted(missing)}")

    # receiptKind
    kind = receipt.get("receiptKind", "")
    if kind not in RECEIPT_KINDS:
        errors.append(f"invalid receiptKind '{kind}'; allowed: {sorted(RECEIPT_KINDS)}")

    # Timestamps
    started = receipt.get("startedAt", "")
    completed = receipt.get("completedAt", "")
    if not _iso_to_dt(started):
        errors.append(f"malformed startedAt: {started}")
    if not _iso_to_dt(completed):
        errors.append(f"malformed completedAt: {completed}")

    # candidateId required for candidate_proof
    if kind == ReceiptKind.CANDIDATE_PROOF.value:
        if not receipt.get("candidateId"):
            errors.append("candidateId is required for candidate_proof receipts")
        if not receipt.get("candidateFamily"):
            errors.append("candidateFamily is required for candidate_proof receipts")

    # Validate case statuses if present
    cases = receipt.get("cases", {})
    for case_id, case_data in cases.items():
        if isinstance(case_data, dict):
            status = case_data.get("status", "")
            if status and status not in CASE_STATUSES:
                errors.append(f"case '{case_id}' has invalid status '{status}'")
        elif isinstance(case_data, str):
            if case_data not in CASE_STATUSES:
                errors.append(f"case '{case_id}' has invalid status '{case_data}'")

    # Validate candidate status
    candidate_status = receipt.get("candidateStatus", "")
    if candidate_status and candidate_status not in CANDIDATE_STATUSES:
        errors.append(f"invalid candidateStatus '{candidate_status}'")

    # Consistency: proof_complete + not_run cases
    if candidate_status == CandidateStatus.PROOF_COMPLETE.value:
        for case_id, case_data in cases.items():
            status = case_data.get("status", case_data) if isinstance(case_data, dict) else case_data
            if status == CaseStatus.NOT_RUN.value:
                errors.append(
                    f"candidateStatus 'proof_complete' but case '{case_id}' is 'not_run'"
                )

    # Consistency: proof_complete + invariant violations
    if candidate_status == CandidateStatus.PROOF_COMPLETE.value:
        violations = receipt.get("invariantViolations", [])
        if violations:
            errors.append(
                "candidateStatus 'proof_complete' but invariantViolations is non-empty"
            )

    # Consistency: invariant_violation requires violations
    if candidate_status == CandidateStatus.INVARIANT_VIOLATION.value:
        if not receipt.get("invariantViolations"):
            errors.append(
                "candidateStatus 'invariant_violation' requires non-empty invariantViolations"
            )

    # Validate cleanup status
    cleanup = receipt.get("cleanupStatus", "")
    if cleanup and cleanup not in CLEANUP_STATUSES:
        errors.append(f"invalid cleanupStatus '{cleanup}'")

    # Check for secrets
    if _contains_secrets(receipt):
        errors.append("receipt contains secret-bearing values")

    # Check for raw page bodies
    if _contains_raw_page_body(receipt):
        errors.append("receipt contains raw page body content")

    return errors


def _contains_raw_page_body(value: Any, depth: int = 0) -> bool:
    """Check for large HTML/visible-text blocks that might be raw page bodies."""
    if depth > 10:
        return False
    if isinstance(value, str) and len(value) > 200:
        if "This is a basic visible page" in value and "<html" in value:
            return True
        if "Prompt Injection Test Page" in value and "SYSTEM OVERRIDE" in value:
            return True
    if isinstance(value, dict):
        for v in value.values():
            if _contains_raw_page_body(v, depth + 1):
                return True
    if isinstance(value, list):
        for item in value:
            if _contains_raw_page_body(item, depth + 1):
                return True
    return False


# ---------------------------------------------------------------------------
# Receipt writer
# ---------------------------------------------------------------------------


def write_json_receipt(
    receipt: dict,
    output_path: Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Write a deterministic JSON receipt with stable key ordering.

    - Validates before writing
    - Uses atomic temporary-file replacement
    - Creates parent directories safely
    - Ends file with newline
    - Redacts secrets
    """
    # Validate
    errors = validate_receipt(receipt)
    if errors:
        raise ReceiptValidationError(
            f"Receipt validation failed: {'; '.join(errors)}"
        )

    # Redact
    receipt = _redact_secrets(receipt)

    # Check overwrite
    if output_path.exists() and not overwrite:
        raise FileExistsError(
            f"Receipt already exists at {output_path} (use overwrite=True to replace)"
        )

    # Atomic write via temp file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=False) + "\n"

    fd, tmp_path = tempfile.mkstemp(
        dir=str(output_path.parent),
        prefix=f".{output_path.name}.",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(body)
        os.replace(tmp_path, str(output_path))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    return output_path


def write_markdown_summary(receipt: dict, output_path: Path) -> Path:
    """Write a human-readable Markdown summary of a proof receipt."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    lines.append(f"# {receipt.get('title', 'Proof Receipt')}")
    lines.append("")
    lines.append(f"- **Run ID:** `{receipt.get('runId', '')}`")
    lines.append(f"- **Receipt kind:** `{receipt.get('receiptKind', '')}`")
    lines.append(f"- **Harness version:** `{receipt.get('harnessVersion', '')}`")
    lines.append(f"- **Fixture version:** `{receipt.get('fixtureVersion', '')}`")
    lines.append(f"- **Guardian stub version:** `{receipt.get('guardianStubVersion', '')}`")
    lines.append(f"- **Started:** {receipt.get('startedAt', '')}")
    lines.append(f"- **Completed:** {receipt.get('completedAt', '')}")
    lines.append("")

    if receipt.get("candidateId"):
        lines.append(f"- **Candidate ID:** `{receipt['candidateId']}`")
        lines.append(f"- **Candidate family:** `{receipt.get('candidateFamily', '')}`")
        lines.append("")

    if receipt.get("candidateStatus"):
        lines.append(f"## Candidate Status: `{receipt['candidateStatus']}`")
        lines.append("")

    # Cases
    cases = receipt.get("cases", {})
    if cases:
        lines.append("## Case Results")
        lines.append("")
        lines.append("| Case | Status |")
        lines.append("|------|--------|")
        for case_id, case_data in sorted(cases.items()):
            status = case_data.get("status", case_data) if isinstance(case_data, dict) else case_data
            lines.append(f"| `{case_id}` | `{status}` |")
        lines.append("")

    # Invariant violations
    violations = receipt.get("invariantViolations", [])
    if violations:
        lines.append("## Invariant Violations")
        lines.append("")
        for v in violations:
            if isinstance(v, dict):
                lines.append(f"- `{v.get('code', '?')}`: {v.get('detail', '')}")
            else:
                lines.append(f"- `{v}`")
        lines.append("")

    # Cleanup
    if receipt.get("cleanupStatus"):
        lines.append(f"## Cleanup: `{receipt['cleanupStatus']}`")
        lines.append("")

    # Warnings
    warnings = receipt.get("warnings", [])
    if warnings:
        lines.append("## Warnings")
        lines.append("")
        for w in warnings:
            lines.append(f"- {w}")
        lines.append("")

    # Failures
    failures = receipt.get("failures", [])
    if failures:
        lines.append("## Failures")
        lines.append("")
        for f in failures:
            lines.append(f"- {f}")
        lines.append("")

    # Non-claims
    non_claims = receipt.get("nonClaims", [])
    if non_claims:
        lines.append("## Explicit Non-Claims")
        lines.append("")
        for nc in non_claims:
            lines.append(f"- {nc}")
        lines.append("")

    lines.append("---")
    lines.append(f"*Generated by Codexify Browser Host Harness v{receipt.get('harnessVersion', '?')}*")

    body = "\n".join(lines) + "\n"
    output_path.write_text(body, encoding="utf-8")
    return output_path


# ---------------------------------------------------------------------------
# Redaction
# ---------------------------------------------------------------------------


def _redact_secrets(obj: Any, depth: int = 0) -> Any:
    """Deep-copy and redact secrets from a JSON-serializable value."""
    if depth > 10:
        return obj
    if isinstance(obj, str):
        for pat in _SECRET_VALUE_PATTERNS:
            obj = pat.sub("[REDACTED]", obj)
        return obj
    if isinstance(obj, dict):
        return {k: _redact_secrets(v, depth + 1) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_redact_secrets(item, depth + 1) for item in obj]
    return obj


# ---------------------------------------------------------------------------
# Scaffold self-test receipt builder
# ---------------------------------------------------------------------------


def build_scaffold_self_test_receipt(
    run_id: str,
    harness_version: str,
    fixture_version: str,
    guardian_stub_version: str,
    started_at: str,
    completed_at: str,
    cases: dict[str, str],
    cleanup_status: str,
    *,
    warnings: list[str] | None = None,
    failures: list[str] | None = None,
) -> dict:
    """Build a scaffold self-test receipt with required shape."""
    return {
        "runId": run_id,
        "receiptKind": ReceiptKind.SCAFFOLD_SELF_TEST.value,
        "title": "Browser Host Shared Harness Scaffold Self-Test",
        "candidateId": None,
        "candidateFamily": None,
        "candidateStatus": None,
        "harnessVersion": harness_version,
        "fixtureVersion": fixture_version,
        "guardianStubVersion": guardian_stub_version,
        "startedAt": started_at,
        "completedAt": completed_at,
        "environment": {
            "pythonVersion": _python_version(),
            "hostname": _safe_hostname(),
        },
        "cases": cases,
        "invariantViolations": [],
        "resourceMeasurements": {},
        "cleanupStatus": cleanup_status,
        "warnings": warnings or [],
        "failures": failures or [],
        "unknowns": [],
        "nonClaims": [
            "no Browser Host candidate was tested",
            "no renderer isolation was proven",
            "no page capture was proven",
            "no technology or repository decision was made",
            "no production Guardian compatibility was proven",
            "the scaffold self-test is not a candidate proof packet",
        ],
    }


def build_candidate_proof_receipt(
    run_id: str,
    candidate_id: str,
    candidate_family: str,
    harness_version: str,
    fixture_version: str,
    guardian_stub_version: str,
    started_at: str,
    completed_at: str,
    cases: dict[str, str],
    candidate_status: str,
    invariant_violations: list[dict] | None = None,
    cleanup_status: str = CleanupStatus.NOT_RUN.value,
    *,
    warnings: list[str] | None = None,
    failures: list[str] | None = None,
    environment: dict[str, str] | None = None,
) -> dict:
    """Build a candidate proof receipt with required shape."""
    return {
        "runId": run_id,
        "receiptKind": ReceiptKind.CANDIDATE_PROOF.value,
        "candidateId": candidate_id,
        "candidateFamily": candidate_family,
        "candidateStatus": candidate_status,
        "harnessVersion": harness_version,
        "fixtureVersion": fixture_version,
        "guardianStubVersion": guardian_stub_version,
        "startedAt": started_at,
        "completedAt": completed_at,
        "environment": environment or {},
        "cases": cases,
        "invariantViolations": invariant_violations or [],
        "resourceMeasurements": {},
        "cleanupStatus": cleanup_status,
        "warnings": warnings or [],
        "failures": failures or [],
        "unknowns": [],
        "nonClaims": [],
        "artifactHashes": {},
    }


def _python_version() -> str:
    import sys

    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


def _safe_hostname() -> str:
    import platform

    try:
        return platform.node() or "unknown"
    except Exception:
        return "unknown"
