"""Canonical browser-host proof-harness registries.

Bounded, immutable vocabulary for comparative proof statuses, invariant
violations, receipt kinds, and cleanup outcomes.

These are proof-harness tokens, not production Guardian runtime protocol
tokens.  They belong in this harness package, not in guardian/protocol_tokens.py.
"""

from __future__ import annotations

from enum import Enum, unique


# ---------------------------------------------------------------------------
# Case status
# ---------------------------------------------------------------------------

@unique
class CaseStatus(str, Enum):
    NOT_RUN = "not_run"
    PASSED = "passed"
    FAILED = "failed"
    BLOCKED = "blocked"
    INCONCLUSIVE = "inconclusive"


CASE_STATUSES: frozenset[str] = frozenset(v.value for v in CaseStatus)


# ---------------------------------------------------------------------------
# Candidate proof status
# ---------------------------------------------------------------------------

@unique
class CandidateStatus(str, Enum):
    PROOF_COMPLETE = "proof_complete"
    PROOF_INCOMPLETE = "proof_incomplete"
    INVARIANT_VIOLATION = "invariant_violation"
    ENVIRONMENT_BLOCKED = "environment_blocked"


CANDIDATE_STATUSES: frozenset[str] = frozenset(v.value for v in CandidateStatus)


# ---------------------------------------------------------------------------
# Cleanup status
# ---------------------------------------------------------------------------

@unique
class CleanupStatus(str, Enum):
    NOT_RUN = "not_run"
    PASSED = "passed"
    FAILED = "failed"


CLEANUP_STATUSES: frozenset[str] = frozenset(v.value for v in CleanupStatus)


# ---------------------------------------------------------------------------
# Receipt kind
# ---------------------------------------------------------------------------

@unique
class ReceiptKind(str, Enum):
    SCAFFOLD_SELF_TEST = "scaffold_self_test"
    CANDIDATE_PROOF = "candidate_proof"


RECEIPT_KINDS: frozenset[str] = frozenset(v.value for v in ReceiptKind)


# ---------------------------------------------------------------------------
# Invariant violation codes
# ---------------------------------------------------------------------------

@unique
class InvariantViolation(str, Enum):
    RENDERER_CREDENTIAL_EXPOSURE = "renderer_credential_exposure"
    UNRELATED_NATIVE_COMMAND_ACCESS = "unrelated_native_command_access"
    UNRESTRICTED_FILESYSTEM_OR_PROCESS = "unrestricted_filesystem_or_process"
    PAGE_GRANTED_BROWSER_OR_COMMAND = "page_granted_browser_or_command"
    CAPTURE_WITHOUT_USER_INITIATION = "capture_without_user_initiation"
    SILENT_PERSISTENCE = "silent_persistence"
    SENSITIVE_FIELD_LEAKAGE = "sensitive_field_leakage"
    CROSS_ORIGIN_IFRAME_LEAKAGE = "cross_origin_iframe_leakage"
    STALE_CAPTURE_REUSE = "stale_capture_reuse"
    SECRET_BEARING_LOGS = "secret_bearing_logs"
    ADAPTER_TRUST_BOUNDARY_BYPASS = "adapter_trust_boundary_bypass"
    CONTRACT_WEAKENING = "contract_weakening"


INVARIANT_VIOLATIONS: frozenset[str] = frozenset(v.value for v in InvariantViolation)


# ---------------------------------------------------------------------------
# Aggregated lookup helpers
# ---------------------------------------------------------------------------

_ALL_STATUS_VALUES: frozenset[str] = CASE_STATUSES | CANDIDATE_STATUSES | CLEANUP_STATUSES


def is_valid_case_status(value: str) -> bool:
    return value in CASE_STATUSES


def is_valid_candidate_status(value: str) -> bool:
    return value in CANDIDATE_STATUSES


def is_valid_cleanup_status(value: str) -> bool:
    return value in CLEANUP_STATUSES


def is_valid_receipt_kind(value: str) -> bool:
    return value in RECEIPT_KINDS


def is_valid_invariant_violation(value: str) -> bool:
    return value in INVARIANT_VIOLATIONS
