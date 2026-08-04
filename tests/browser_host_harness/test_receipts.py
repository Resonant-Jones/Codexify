"""Receipt contract tests.

Proves valid receipt validation and rejection, candidate-status consistency,
invariant-violation consistency, stable JSON output, Markdown summary,
redaction, atomic writes, overwrite refusal, and absence of raw content.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from scripts.browser_host_harness.contracts import (
    CaseStatus,
    CandidateStatus,
    CleanupStatus,
    ReceiptKind,
)
from scripts.browser_host_harness.receipts import (
    ReceiptValidationError,
    build_candidate_proof_receipt,
    build_scaffold_self_test_receipt,
    validate_receipt,
    write_json_receipt,
    write_markdown_summary,
)


class TestValidateReceipt:
    def test_valid_scaffold_receipt_passes(self):
        receipt = build_scaffold_self_test_receipt(
            run_id="test-run",
            harness_version="0.1.0",
            fixture_version="1.0.0",
            guardian_stub_version="0.1.0",
            started_at="2026-07-30T12:00:00+00:00",
            completed_at="2026-07-30T12:01:00+00:00",
            cases={"case1": CaseStatus.PASSED.value},
            cleanup_status=CleanupStatus.PASSED.value,
        )
        errors = validate_receipt(receipt)
        assert errors == [], f"Unexpected errors: {errors}"

    def test_missing_required_fields(self):
        receipt = {"runId": "test"}
        errors = validate_receipt(receipt)
        assert len(errors) > 0
        assert any("missing required fields" in e for e in errors)

    def test_invalid_receipt_kind(self):
        receipt = build_scaffold_self_test_receipt(
            run_id="test",
            harness_version="0.1.0",
            fixture_version="1.0.0",
            guardian_stub_version="0.1.0",
            started_at="2026-07-30T12:00:00+00:00",
            completed_at="2026-07-30T12:01:00+00:00",
            cases={},
            cleanup_status=CleanupStatus.PASSED.value,
        )
        receipt["receiptKind"] = "invalid_kind"
        errors = validate_receipt(receipt)
        assert any("receiptKind" in e for e in errors)

    def test_invalid_case_status(self):
        receipt = build_scaffold_self_test_receipt(
            run_id="test",
            harness_version="0.1.0",
            fixture_version="1.0.0",
            guardian_stub_version="0.1.0",
            started_at="2026-07-30T12:00:00+00:00",
            completed_at="2026-07-30T12:01:00+00:00",
            cases={"case1": "running"},
            cleanup_status=CleanupStatus.PASSED.value,
        )
        errors = validate_receipt(receipt)
        assert any("invalid status" in e for e in errors)

    def test_invalid_candidate_status(self):
        receipt = build_candidate_proof_receipt(
            run_id="test",
            candidate_id="cand-1",
            candidate_family="test-family",
            harness_version="0.1.0",
            fixture_version="1.0.0",
            guardian_stub_version="0.1.0",
            started_at="2026-07-30T12:00:00+00:00",
            completed_at="2026-07-30T12:01:00+00:00",
            cases={},
            candidate_status="nonsense",
        )
        errors = validate_receipt(receipt)
        assert any("candidateStatus" in e for e in errors)

    def test_malformed_timestamps(self):
        receipt = build_scaffold_self_test_receipt(
            run_id="test",
            harness_version="0.1.0",
            fixture_version="1.0.0",
            guardian_stub_version="0.1.0",
            started_at="not-a-timestamp",
            completed_at="also-not",
            cases={},
            cleanup_status=CleanupStatus.PASSED.value,
        )
        errors = validate_receipt(receipt)
        assert any("startedAt" in e for e in errors)
        assert any("completedAt" in e for e in errors)

    def test_proof_complete_with_not_run_case(self):
        receipt = build_candidate_proof_receipt(
            run_id="test",
            candidate_id="cand-1",
            candidate_family="test",
            harness_version="0.1.0",
            fixture_version="1.0.0",
            guardian_stub_version="0.1.0",
            started_at="2026-07-30T12:00:00+00:00",
            completed_at="2026-07-30T12:01:00+00:00",
            cases={"case1": CaseStatus.NOT_RUN.value},
            candidate_status=CandidateStatus.PROOF_COMPLETE.value,
        )
        errors = validate_receipt(receipt)
        assert any("not_run" in e for e in errors)

    def test_proof_complete_with_invariant_violations(self):
        receipt = build_candidate_proof_receipt(
            run_id="test",
            candidate_id="cand-1",
            candidate_family="test",
            harness_version="0.1.0",
            fixture_version="1.0.0",
            guardian_stub_version="0.1.0",
            started_at="2026-07-30T12:00:00+00:00",
            completed_at="2026-07-30T12:01:00+00:00",
            cases={},
            candidate_status=CandidateStatus.PROOF_COMPLETE.value,
            invariant_violations=[{"code": "test_violation", "detail": "test"}],
        )
        errors = validate_receipt(receipt)
        assert any("invariantViolations" in e for e in errors)

    def test_invariant_violation_requires_violations(self):
        receipt = build_candidate_proof_receipt(
            run_id="test",
            candidate_id="cand-1",
            candidate_family="test",
            harness_version="0.1.0",
            fixture_version="1.0.0",
            guardian_stub_version="0.1.0",
            started_at="2026-07-30T12:00:00+00:00",
            completed_at="2026-07-30T12:01:00+00:00",
            cases={},
            candidate_status=CandidateStatus.INVARIANT_VIOLATION.value,
        )
        errors = validate_receipt(receipt)
        assert any("invariant_violation" in e for e in errors)

    def test_missing_candidate_id_for_candidate_proof(self):
        receipt = build_candidate_proof_receipt(
            run_id="test",
            candidate_id="",
            candidate_family="test",
            harness_version="0.1.0",
            fixture_version="1.0.0",
            guardian_stub_version="0.1.0",
            started_at="2026-07-30T12:00:00+00:00",
            completed_at="2026-07-30T12:01:00+00:00",
            cases={},
            candidate_status=CandidateStatus.PROOF_INCOMPLETE.value,
        )
        errors = validate_receipt(receipt)
        assert any("candidateId" in e for e in errors)

    def test_rejects_raw_page_body(self):
        receipt = build_scaffold_self_test_receipt(
            run_id="test",
            harness_version="0.1.0",
            fixture_version="1.0.0",
            guardian_stub_version="0.1.0",
            started_at="2026-07-30T12:00:00+00:00",
            completed_at="2026-07-30T12:01:00+00:00",
            cases={},
            cleanup_status=CleanupStatus.PASSED.value,
        )
        # Must be > 200 chars to trigger detection threshold
        base = "This is a basic visible page with stable text content for capture verification. <html>"
        receipt["raw_content"] = base + (" padding " * 15)
        errors = validate_receipt(receipt)
        assert any("raw page body" in e.lower() for e in errors)

    def test_rejects_secrets(self):
        receipt = build_scaffold_self_test_receipt(
            run_id="test",
            harness_version="0.1.0",
            fixture_version="1.0.0",
            guardian_stub_version="0.1.0",
            started_at="2026-07-30T12:00:00+00:00",
            completed_at="2026-07-30T12:01:00+00:00",
            cases={},
            cleanup_status=CleanupStatus.PASSED.value,
        )
        receipt["secret"] = "CODEXIFY-HARNESS-SENTINEL-abc123-NOT-A-REAL-CREDENTIAL"
        errors = validate_receipt(receipt)
        assert any("secret-bearing" in e for e in errors)


class TestWriteJsonReceipt:
    def test_writes_valid_json(self, tmp_path):
        receipt = build_scaffold_self_test_receipt(
            run_id="test",
            harness_version="0.1.0",
            fixture_version="1.0.0",
            guardian_stub_version="0.1.0",
            started_at="2026-07-30T12:00:00+00:00",
            completed_at="2026-07-30T12:01:00+00:00",
            cases={},
            cleanup_status=CleanupStatus.PASSED.value,
        )
        path = tmp_path / "receipt.json"
        result = write_json_receipt(receipt, path)
        assert result.exists()
        content = result.read_text(encoding="utf-8")
        assert content.endswith("\n")
        parsed = json.loads(content)
        assert parsed["runId"] == "test"

    def test_stable_key_ordering(self, tmp_path):
        receipt = build_scaffold_self_test_receipt(
            run_id="test",
            harness_version="0.1.0",
            fixture_version="1.0.0",
            guardian_stub_version="0.1.0",
            started_at="2026-07-30T12:00:00+00:00",
            completed_at="2026-07-30T12:01:00+00:00",
            cases={},
            cleanup_status=CleanupStatus.PASSED.value,
        )
        path = tmp_path / "receipt.json"
        write_json_receipt(receipt, path)
        content1 = path.read_text(encoding="utf-8")
        write_json_receipt(receipt, path, overwrite=True)
        content2 = path.read_text(encoding="utf-8")
        assert content1 == content2

    def test_refuses_overwrite_by_default(self, tmp_path):
        receipt = build_scaffold_self_test_receipt(
            run_id="test",
            harness_version="0.1.0",
            fixture_version="1.0.0",
            guardian_stub_version="0.1.0",
            started_at="2026-07-30T12:00:00+00:00",
            completed_at="2026-07-30T12:01:00+00:00",
            cases={},
            cleanup_status=CleanupStatus.PASSED.value,
        )
        path = tmp_path / "receipt.json"
        write_json_receipt(receipt, path)
        with pytest.raises(FileExistsError):
            write_json_receipt(receipt, path)

    def test_redacts_credential_in_values(self, tmp_path):
        receipt = build_scaffold_self_test_receipt(
            run_id="test",
            harness_version="0.1.0",
            fixture_version="1.0.0",
            guardian_stub_version="0.1.0",
            started_at="2026-07-30T12:00:00+00:00",
            completed_at="2026-07-30T12:01:00+00:00",
            cases={},
            cleanup_status=CleanupStatus.PASSED.value,
        )
        receipt["test_field"] = "CODEXIFY-HARNESS-SENTINEL-deadbeef-NOT-A-REAL-CREDENTIAL"
        path = tmp_path / "receipt.json"
        # This will fail validation because of the secret
        # But we need to test redaction at the raw level
        # So let's test the internal redact function
        from scripts.browser_host_harness.receipts import _redact_secrets
        redacted = _redact_secrets(receipt)
        assert "[REDACTED]" in redacted.get("test_field", "")


class TestWriteMarkdownSummary:
    def test_creates_file(self, tmp_path):
        receipt = build_scaffold_self_test_receipt(
            run_id="test-run",
            harness_version="0.1.0",
            fixture_version="1.0.0",
            guardian_stub_version="0.1.0",
            started_at="2026-07-30T12:00:00+00:00",
            completed_at="2026-07-30T12:01:00+00:00",
            cases={"test_case": CaseStatus.PASSED.value},
            cleanup_status=CleanupStatus.PASSED.value,
        )
        path = tmp_path / "summary.md"
        result = write_markdown_summary(receipt, path)
        assert result.exists()
        content = result.read_text(encoding="utf-8")
        assert "test-run" in content
        assert "scaffold_self_test" in content
        assert "test_case" in content
        assert "passed" in content.lower()


class TestCandidateProofReceipt:
    def test_build_candidate_receipt(self):
        receipt = build_candidate_proof_receipt(
            run_id="run-1",
            candidate_id="tauri-candidate",
            candidate_family="os-webview-tauri",
            harness_version="0.1.0",
            fixture_version="1.0.0",
            guardian_stub_version="0.1.0",
            started_at="2026-07-30T12:00:00+00:00",
            completed_at="2026-07-30T12:05:00+00:00",
            cases={
                "basic_visible": CaseStatus.PASSED.value,
                "credential_isolation": CaseStatus.FAILED.value,
            },
            candidate_status=CandidateStatus.PROOF_INCOMPLETE.value,
            cleanup_status=CleanupStatus.PASSED.value,
        )
        assert receipt["receiptKind"] == ReceiptKind.CANDIDATE_PROOF.value
        assert receipt["candidateId"] == "tauri-candidate"
        assert receipt["candidateStatus"] == CandidateStatus.PROOF_INCOMPLETE.value
        assert len(receipt["cases"]) == 2

    def test_valid_candidate_receipt_passes_validator(self):
        receipt = build_candidate_proof_receipt(
            run_id="run-1",
            candidate_id="tauri-candidate",
            candidate_family="os-webview-tauri",
            harness_version="0.1.0",
            fixture_version="1.0.0",
            guardian_stub_version="0.1.0",
            started_at="2026-07-30T12:00:00+00:00",
            completed_at="2026-07-30T12:05:00+00:00",
            cases={"case1": CaseStatus.PASSED.value},
            candidate_status=CandidateStatus.PROOF_COMPLETE.value,
            cleanup_status=CleanupStatus.PASSED.value,
        )
        errors = validate_receipt(receipt)
        assert errors == []
