#!/usr/bin/env python3
"""Validate one Guardian Evidence Reducer input-bundle JSON file.

This is local static validation only. It reads the bundle supplied on the
command line and never reads any ``source_ref`` target.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from guardian.evidence_packets.contracts import ALLOWED_REVIEW_DEPTHS, is_allowed_review_depth
from guardian.evidence_packets.reducer_contracts import (
    ALLOWED_REDUCER_INPUT_CLASSES,
    is_allowed_reducer_input_class,
)


RESULT_SCHEMA_VERSION = "guardian_evidence_reducer_input_bundle_static_validation_result.v1"
VALIDATOR_CONTRACT_VERSION = "guardian_evidence_reducer_input_bundle_static_validator_contract.v1"
EXPECTED_BUNDLE_SCHEMA_VERSION = "guardian_evidence_reducer_input_bundle.v1"
CHECKED_BY = "scripts/guardian/validate_reducer_input_bundle.py"

REQUIRED_TOP_LEVEL_FIELDS = (
    "schema_version",
    "bundle_id",
    "review_depth",
    "inputs",
    "operator_context",
    "provenance",
    "limits",
)
REQUIRED_INPUT_FIELDS = (
    "input_id",
    "input_class",
    "source_ref",
    "evidence_posture",
    "notes",
)
CANDIDATE_ISSUE_CODES = (
    "bundle_json_invalid",
    "bundle_schema_version_missing",
    "bundle_schema_version_unsupported",
    "bundle_required_field_missing",
    "review_depth_invalid",
    "inputs_missing",
    "input_required_field_missing",
    "input_class_invalid",
    "source_ref_missing",
    "source_ref_absolute_path_warning",
    "source_ref_secret_risk",
    "source_ref_file_read_claim",
    "operator_context_not_list",
    "provenance_missing",
    "template_marker_missing",
    "static_fixture_marker_missing",
    "limits_missing",
    "boundary_language_missing",
    "evidence_ingestion_claim_risk",
    "packet_generation_claim_risk",
    "runtime_reducer_claim_risk",
    "execution_claim_risk",
    "ci_release_gate_claim_risk",
)

BOUNDARY_PATTERNS = (
    ("not evidence ingestion", r"(?:not|does not authorize)\s+evidence ingestion"),
    ("not packet generation", r"(?:not|does not authorize)\s+packet generation"),
    (
        "not runtime reducer output",
        r"(?:not|does not authorize)\s+runtime reducer (?:output|behavior)",
    ),
    ("does not authorize file reads", r"does not authorize (?:file reads|reading files)"),
    ("does not authorize command bus calls", r"does not authorize command bus calls?"),
    (
        "does not authorize Codex Runner invocation",
        r"does not authorize (?:codex runner )?(?:calls?|invocation)",
    ),
    ("does not authorize Pi Loop invocation", r"does not authorize pi loop invocation"),
    ("does not authorize source mutation", r"does not authorize source mutation"),
    ("does not authorize provider execution", r"does not authorize provider execution"),
    (
        "does not authorize Execution Ledger writes",
        r"does not authorize execution ledger writes?",
    ),
    ("does not authorize WorkOrder mutation", r"does not authorize workorders? mutation"),
    ("does not widen release support", r"does not widen release support"),
)

SECRET_PATTERN = re.compile(
    r"(?:api[_-]?key|access[_-]?token|bearer\s+[A-Za-z0-9._-]+|password|secret|"
    r"-----begin\s+[^-]+-----|\bsk-[A-Za-z0-9_-]{12,})",
    re.IGNORECASE,
)
FILE_READ_PATTERN = re.compile(
    r"(?:source[_ -]?ref|source reference|source target|target)\b[^.\n]{0,80}\b"
    r"(?:was|were|has been|should be|must be|will be)\s+read\b|"
    r"\bread\b[^.\n]{0,80}\b(?:source[_ -]?ref|source target|source reference)\b",
    re.IGNORECASE,
)
NEGATIVE_FRAMING = (
    "not",
    "no",
    "does not",
    "must not",
    "not yet",
    "outside current support",
    "requires a separate contract",
    "does not authorize",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _serialized(bundle: object) -> str:
    return json.dumps(bundle, sort_keys=True, ensure_ascii=False)


def _has_negative_framing(text: str, start: int) -> bool:
    quote_before = text.rfind('"', 0, start)
    quote_after = text.find('"', start)
    if quote_before >= 0 and quote_after >= 0:
        segment = text[quote_before + 1 : quote_after].lower()
        before = segment[: start - quote_before - 1]
        after = segment[start - quote_before - 1 :]
    else:
        before = text[max(0, start - 100) : start].lower()
        after = text[start : start + 45].lower()
    return any(marker in before for marker in NEGATIVE_FRAMING) or any(
        marker in after for marker in (" not ", " no ", " does not ", " must not ")
    )


def _has_unframed_claim(text: str, pattern: re.Pattern[str]) -> bool:
    return any(not _has_negative_framing(text, match.start()) for match in pattern.finditer(text))


def _path_is_under(bundle_path: Path, directory: str) -> bool:
    parts = bundle_path.as_posix().split("/")
    return len(parts) >= 2 and directory in parts


def validate_bundle(bundle_path: Path) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []

    def add_issue(
        severity: str,
        code: str,
        path: str,
        message: str,
        input_ref: str = "",
        remediation_hint: str = "Review the bundle against the static validator contract.",
    ) -> None:
        issues.append(
            {
                "issue_id": f"issue-{len(issues) + 1:04d}",
                "severity": severity,
                "code": code,
                "path": path,
                "message": message,
                "input_ref": input_ref,
                "remediation_hint": remediation_hint,
            }
        )

    try:
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        add_issue(
            "error",
            "bundle_json_invalid",
            "$",
            f"Bundle JSON could not be read or parsed: {exc}",
            remediation_hint="Provide one readable UTF-8 JSON object.",
        )
        return _result(bundle_path, issues)

    if not isinstance(bundle, dict):
        add_issue(
            "error",
            "bundle_json_invalid",
            "$",
            "Bundle JSON root must be an object.",
            remediation_hint="Use a JSON object shaped like ReducerInputBundle.",
        )
        return _result(bundle_path, issues)

    for field in REQUIRED_TOP_LEVEL_FIELDS:
        if field not in bundle:
            code = "bundle_required_field_missing"
            if field == "schema_version":
                code = "bundle_schema_version_missing"
            add_issue("error", code, f"$.{field}", f"Required top-level field is missing: {field}.")

    schema_version = bundle.get("schema_version")
    if schema_version is not None and schema_version != EXPECTED_BUNDLE_SCHEMA_VERSION:
        add_issue(
            "error",
            "bundle_schema_version_unsupported",
            "$.schema_version",
            f"Unsupported bundle schema version: {schema_version!r}.",
        )

    review_depth = bundle.get("review_depth")
    if review_depth is not None and not is_allowed_review_depth(review_depth):
        add_issue(
            "error",
            "review_depth_invalid",
            "$.review_depth",
            f"Review depth must be one of {sorted(ALLOWED_REVIEW_DEPTHS)}.",
        )

    inputs = bundle.get("inputs")
    if not isinstance(inputs, list) or not inputs:
        add_issue(
            "error",
            "inputs_missing",
            "$.inputs",
            "inputs must be a non-empty list.",
        )
        inputs = []

    for index, item in enumerate(inputs):
        path = f"$.inputs[{index}]"
        if not isinstance(item, dict):
            add_issue("error", "input_required_field_missing", path, "Each input must be an object.")
            continue
        for field in REQUIRED_INPUT_FIELDS:
            if field not in item:
                add_issue(
                    "error",
                    "input_required_field_missing",
                    f"{path}.{field}",
                    f"Required input field is missing: {field}.",
                    input_ref=str(item.get("input_id", "")),
                )
        input_class = item.get("input_class")
        if input_class is not None and not is_allowed_reducer_input_class(input_class):
            add_issue(
                "error",
                "input_class_invalid",
                f"{path}.input_class",
                f"Input class must be one of {sorted(ALLOWED_REDUCER_INPUT_CLASSES)}.",
                input_ref=str(item.get("input_id", "")),
            )
        source_ref = item.get("source_ref")
        if not isinstance(source_ref, str) or not source_ref.strip():
            add_issue(
                "error",
                "source_ref_missing",
                f"{path}.source_ref",
                "source_ref must be a non-empty reference string.",
                input_ref=str(item.get("input_id", "")),
            )
            continue
        if os.path.isabs(source_ref):
            add_issue(
                "warning",
                "source_ref_absolute_path_warning",
                f"{path}.source_ref",
                "source_ref is an absolute path; prefer a bounded symbolic reference.",
                input_ref=str(item.get("input_id", "")),
            )
        if SECRET_PATTERN.search(source_ref):
            add_issue(
                "warning",
                "source_ref_secret_risk",
                f"{path}.source_ref",
                "source_ref appears to contain secret-like material.",
                input_ref=str(item.get("input_id", "")),
                remediation_hint="Remove credentials and use a non-secret reference.",
            )

    operator_context = bundle.get("operator_context")
    if operator_context is not None and not isinstance(operator_context, list):
        add_issue(
            "error",
            "operator_context_not_list",
            "$.operator_context",
            "operator_context must be a list.",
        )

    provenance = bundle.get("provenance")
    if provenance is None or not isinstance(provenance, dict):
        add_issue("error", "provenance_missing", "$.provenance", "provenance must be an object.")

    if _path_is_under(bundle_path, "templates") and not (isinstance(provenance, dict) and provenance.get("template") is True):
        add_issue("warning", "template_marker_missing", "$.provenance.template", "Template path lacks provenance.template=true.")
    if _path_is_under(bundle_path, "fixtures") and not (isinstance(provenance, dict) and provenance.get("static_fixture") is True):
        add_issue("warning", "static_fixture_marker_missing", "$.provenance.static_fixture", "Fixture path lacks provenance.static_fixture=true.")

    limits = bundle.get("limits")
    if not limits:
        add_issue("warning", "limits_missing", "$.limits", "limits is missing or empty.")

    text = _serialized(bundle).lower()
    if _has_unframed_claim(text, FILE_READ_PATTERN):
        add_issue("warning", "source_ref_file_read_claim", "$", "Bundle text claims that a source reference was or should be read.")
    for label, pattern in BOUNDARY_PATTERNS:
        if not re.search(pattern, text, re.IGNORECASE):
            add_issue("warning", "boundary_language_missing", "$", f"Required boundary language is missing: {label}.")

    risky_claims = (
        ("evidence_ingestion_claim_risk", r"(?:evidence ingestion|ingest evidence)"),
        ("packet_generation_claim_risk", r"(?:packet generation|generate guardianevidencepacket)"),
        ("runtime_reducer_claim_risk", r"(?:runtime reducer support|runtime reducer behavior)"),
        ("execution_claim_risk", r"(?:execution support|execute providers|plan execution)"),
        ("ci_release_gate_claim_risk", r"(?:ci/default release gating|release gate|ci gating)"),
    )
    for code, pattern in risky_claims:
        compiled = re.compile(pattern, re.IGNORECASE)
        match = next((candidate for candidate in compiled.finditer(text) if not _has_negative_framing(text, candidate.start())), None)
        if match:
            add_issue("warning", code, "$", f"Bundle text may claim unsupported capability: {match.group(0)}.")

    return _result(bundle_path, issues)


def _result(bundle_path: Path, issues: list[dict[str, Any]]) -> dict[str, Any]:
    has_error = any(issue["severity"] == "error" for issue in issues)
    result = "fail" if has_error else "pass_with_warnings" if issues else "pass"
    return {
        "schema_version": RESULT_SCHEMA_VERSION,
        "validated_bundle_ref": str(bundle_path),
        "validator_contract_version": VALIDATOR_CONTRACT_VERSION,
        "result": result,
        "issue_count": len(issues),
        "issues": issues,
        "checked_at": _now(),
        "checked_by": CHECKED_BY,
        "limits": {
            "max_inputs": 1000,
            "max_issues": 1000,
            "reads_source_ref_targets": False,
            "writes_files": False,
            "executes": False,
        },
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate one ReducerInputBundle JSON file.")
    parser.add_argument("bundle", type=Path, help="bundle JSON file to validate")
    parser.add_argument("--json", action="store_true", dest="as_json", help="emit JSON result")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    result = validate_bundle(args.bundle)
    if args.as_json:
        print(json.dumps(result, indent=2))
    else:
        print(f"{result['result']}: {result['validated_bundle_ref']} ({result['issue_count']} issues)")
    return 1 if result["result"] == "fail" else 0


if __name__ == "__main__":
    sys.exit(main())
