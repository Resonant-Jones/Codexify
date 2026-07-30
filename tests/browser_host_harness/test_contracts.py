"""Contract tests for canonical harness registries.

Proves exact status values, immutability, and invariant-violation membership.
"""

from __future__ import annotations

import pytest

from scripts.browser_host_harness.contracts import (
    CASE_STATUSES,
    CANDIDATE_STATUSES,
    CLEANUP_STATUSES,
    RECEIPT_KINDS,
    INVARIANT_VIOLATIONS,
    CaseStatus,
    CandidateStatus,
    CleanupStatus,
    InvariantViolation,
    ReceiptKind,
    is_valid_case_status,
    is_valid_candidate_status,
    is_valid_cleanup_status,
    is_valid_receipt_kind,
    is_valid_invariant_violation,
)


class TestCaseStatus:
    def test_exact_values(self):
        assert CaseStatus.NOT_RUN.value == "not_run"
        assert CaseStatus.PASSED.value == "passed"
        assert CaseStatus.FAILED.value == "failed"
        assert CaseStatus.BLOCKED.value == "blocked"
        assert CaseStatus.INCONCLUSIVE.value == "inconclusive"

    def test_frozenset_membership(self):
        for v in CaseStatus:
            assert v.value in CASE_STATUSES
        assert len(CASE_STATUSES) == 5

    def test_immutability(self):
        with pytest.raises(AttributeError):
            CASE_STATUSES.add("new_value")  # type: ignore[attr-defined]

    def test_validator(self):
        assert is_valid_case_status("passed")
        assert is_valid_case_status("not_run")
        assert not is_valid_case_status("running")
        assert not is_valid_case_status("")
        assert not is_valid_case_status("proof_complete")


class TestCandidateStatus:
    def test_exact_values(self):
        assert CandidateStatus.PROOF_COMPLETE.value == "proof_complete"
        assert CandidateStatus.PROOF_INCOMPLETE.value == "proof_incomplete"
        assert CandidateStatus.INVARIANT_VIOLATION.value == "invariant_violation"
        assert CandidateStatus.ENVIRONMENT_BLOCKED.value == "environment_blocked"

    def test_frozenset_membership(self):
        for v in CandidateStatus:
            assert v.value in CANDIDATE_STATUSES
        assert len(CANDIDATE_STATUSES) == 4

    def test_validator(self):
        assert is_valid_candidate_status("proof_complete")
        assert is_valid_candidate_status("environment_blocked")
        assert not is_valid_candidate_status("passed")
        assert not is_valid_candidate_status("")


class TestCleanupStatus:
    def test_exact_values(self):
        assert CleanupStatus.NOT_RUN.value == "not_run"
        assert CleanupStatus.PASSED.value == "passed"
        assert CleanupStatus.FAILED.value == "failed"

    def test_frozenset(self):
        assert len(CLEANUP_STATUSES) == 3

    def test_validator(self):
        assert is_valid_cleanup_status("passed")
        assert not is_valid_cleanup_status("blocked")


class TestReceiptKind:
    def test_exact_values(self):
        assert ReceiptKind.SCAFFOLD_SELF_TEST.value == "scaffold_self_test"
        assert ReceiptKind.CANDIDATE_PROOF.value == "candidate_proof"

    def test_frozenset(self):
        assert len(RECEIPT_KINDS) == 2

    def test_validator(self):
        assert is_valid_receipt_kind("scaffold_self_test")
        assert is_valid_receipt_kind("candidate_proof")
        assert not is_valid_receipt_kind("unknown_kind")


class TestInvariantViolations:
    def test_required_codes_exist(self):
        required = {
            "renderer_credential_exposure",
            "unrelated_native_command_access",
            "unrestricted_filesystem_or_process",
            "page_granted_browser_or_command",
            "capture_without_user_initiation",
            "silent_persistence",
            "sensitive_field_leakage",
            "cross_origin_iframe_leakage",
            "stale_capture_reuse",
            "secret_bearing_logs",
            "adapter_trust_boundary_bypass",
            "contract_weakening",
        }
        for code in required:
            assert code in INVARIANT_VIOLATIONS, f"Missing: {code}"
        assert len(INVARIANT_VIOLATIONS) >= 12

    def test_validator(self):
        assert is_valid_invariant_violation("renderer_credential_exposure")
        assert not is_valid_invariant_violation("unknown_violation")

    def test_enum_values_match_frozenset(self):
        for v in InvariantViolation:
            assert v.value in INVARIANT_VIOLATIONS
