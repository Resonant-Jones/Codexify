from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone

from scripts.browser_host_harness.candidate_cases import (
    MANDATORY_CANDIDATE_CASE_IDS,
    MANDATORY_CANDIDATE_CASES,
)
from scripts.browser_host_harness.receipts import validate_receipt


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def test_candidate_case_catalog_has_unique_ids_and_all_lanes():
    assert len(MANDATORY_CANDIDATE_CASE_IDS) == len(MANDATORY_CANDIDATE_CASES)
    assert len(MANDATORY_CANDIDATE_CASES) >= 80
    assert {case.lane for case in MANDATORY_CANDIDATE_CASES} == {
        "static_boundary_inspection",
        "build_and_package",
        "launch_and_navigation",
        "renderer_credential_isolation",
        "native_authority_isolation",
        "explicit_context_capture",
        "origin_document_integrity",
        "sensitive_field_exclusion",
        "prompt_injection_resistance",
        "permission_failure_behavior",
        "renderer_failure_containment",
        "observability_redaction",
        "accessibility",
        "resource_measurement",
        "cleanup",
    }


def test_candidate_run_receipt_rejects_missing_mandatory_cases():
    receipt = {
        "runId": "candidate-test",
        "receiptKind": "candidate_proof",
        "proofMode": "candidate_run",
        "candidateId": "candidate-test",
        "candidateFamily": "test-family",
        "candidateStatus": "proof_incomplete",
        "harnessVersion": "0.1.0",
        "fixtureVersion": "1.0.0",
        "guardianStubVersion": "0.1.0",
        "startedAt": _now(),
        "completedAt": _now(),
        "cases": {},
        "invariantViolations": [],
        "cleanupStatus": "passed",
    }
    errors = validate_receipt(receipt)
    assert any("omits mandatory cases" in error for error in errors)


def test_candidate_run_receipt_accepts_terminal_catalog():
    receipt = {
        "runId": "candidate-test",
        "receiptKind": "candidate_proof",
        "proofMode": "candidate_run",
        "candidateId": "candidate-test",
        "candidateFamily": "test-family",
        "candidateStatus": "proof_complete",
        "harnessVersion": "0.1.0",
        "fixtureVersion": "1.0.0",
        "guardianStubVersion": "0.1.0",
        "startedAt": _now(),
        "completedAt": _now(),
        "cases": {
            case_id: {"status": "blocked"}
            for case_id in MANDATORY_CANDIDATE_CASE_IDS
        },
        "invariantViolations": [],
        "cleanupStatus": "passed",
    }
    assert validate_receipt(receipt) == []


def test_tauri_inspection_cli_writes_valid_receipt(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.browser_host_harness",
            "inspect-candidate",
            "--candidate",
            "tauri-incumbent",
            "--output-dir",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    receipt_path = tmp_path / "candidate-inspection.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["candidateId"] == "codexify-tauri-os-webview-incumbent-v1"
    assert receipt["candidateFamily"] == "os_webview_tauri"
    assert receipt["inspection"]["remoteCapability"]["permissions"] == [
        "allow-candidate-return-capture"
    ]
    validate = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.browser_host_harness",
            "validate-receipt",
            str(receipt_path),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert validate.returncode == 0, validate.stdout + validate.stderr
