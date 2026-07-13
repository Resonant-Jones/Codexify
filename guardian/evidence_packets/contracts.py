"""Pure, side-effect-free Guardian Evidence Packet contract helpers.

This module is a code-level shape contract for future reducer work. It does
not validate files, read configuration, call services, or perform execution.
"""

from __future__ import annotations

import json
from collections.abc import Mapping

GUARDIAN_EVIDENCE_PACKET_SCHEMA_VERSION = "guardian_evidence_packet.v1"
STATIC_VALIDATION_RESULT_SCHEMA_VERSION = (
    "guardian_evidence_packet_static_validation_result.v1"
)
BATCH_VALIDATION_RESULT_SCHEMA_VERSION = (
    "guardian_evidence_packet_batch_validation_result.v1"
)

BOUNDARY_LABEL = (
    "PREFLIGHT ONLY\n"
    "NO PI LOOP INVOCATION\n"
    "NO SOURCE MUTATION\n"
    "NO CODEXIFY INGESTION"
)

ALLOWED_REVIEW_DEPTHS = frozenset({"light", "medium", "high", "xhigh"})
ALLOWED_CLAIM_STATUSES = frozenset({
    "supported",
    "unsupported",
    "blocked",
    "inferred",
    "not_evaluated",
})

REQUIRED_PACKET_FIELDS = (
    "schema_version",
    "packet_id",
    "created_at",
    "source_domain",
    "evidence_class",
    "review_depth",
    "subject",
    "reducer_profile_ref",
    "raw_evidence_refs",
    "reduced_summary",
    "claim_ledger",
    "authority_state",
    "invariant_checks",
    "uncertainty",
    "forbidden_interpretations",
    "next_gate_options",
    "recommended_next_gate",
    "loop_policy",
    "provenance",
    "limits",
)

REQUIRED_EVIDENCE_REF_FIELDS = (
    "ref_id",
    "ref_type",
    "uri_or_path",
    "source_system",
    "content_hash",
    "timestamp",
    "status",
    "trust_posture",
    "notes",
)

REQUIRED_CLAIM_FIELDS = (
    "claim_id",
    "claim",
    "status",
    "evidence_refs",
    "confidence",
    "limits",
    "counterclaims",
    "missing_evidence",
    "forbidden_interpretations",
)

REQUIRED_AUTHORITY_LOCKS = (
    "guardian_operational",
    "plan_execution_allowed",
    "pi_loop_invocation_allowed",
    "codexify_ingestion_allowed",
    "durable_mutation_allowed",
    "provider_execution_allowed",
    "patch_application_allowed",
    "dispatch_allowed",
    "merge_allowed",
)

REQUIRED_INVARIANT_CHECK_FIELDS = (
    "invariant_id",
    "status",
    "evidence_refs",
    "notes",
)

REQUIRED_LOOP_POLICY_FIELDS = (
    "bounded",
    "review_depth",
    "self_check_passes",
    "recursive_autonomous_loop_allowed",
    "adversarial_review_required",
    "missing_proof_ledger_required",
)


def false_authority_state() -> dict[str, bool]:
    """Return a fresh authority state with every lock set to ``False``."""
    return {lock: False for lock in REQUIRED_AUTHORITY_LOCKS}


def missing_packet_fields(packet: Mapping[str, object]) -> tuple[str, ...]:
    """Return required packet fields absent from *packet*, in contract order."""
    return tuple(field for field in REQUIRED_PACKET_FIELDS if field not in packet)


def missing_evidence_ref_fields(ref: Mapping[str, object]) -> tuple[str, ...]:
    """Return required evidence-reference fields absent from *ref*."""
    return tuple(field for field in REQUIRED_EVIDENCE_REF_FIELDS if field not in ref)


def missing_claim_fields(claim: Mapping[str, object]) -> tuple[str, ...]:
    """Return required claim-ledger fields absent from *claim*."""
    return tuple(field for field in REQUIRED_CLAIM_FIELDS if field not in claim)


def missing_authority_locks(
    authority_state: Mapping[str, object],
) -> tuple[str, ...]:
    """Return required authority locks absent from *authority_state*."""
    return tuple(lock for lock in REQUIRED_AUTHORITY_LOCKS if lock not in authority_state)


def authority_locks_true(
    authority_state: Mapping[str, object],
) -> tuple[str, ...]:
    """Return authority lock names whose value is exactly ``True``."""
    return tuple(
        lock for lock in REQUIRED_AUTHORITY_LOCKS if authority_state.get(lock) is True
    )


def missing_invariant_check_fields(
    check: Mapping[str, object],
) -> tuple[str, ...]:
    """Return required invariant-check fields absent from *check*."""
    return tuple(field for field in REQUIRED_INVARIANT_CHECK_FIELDS if field not in check)


def missing_loop_policy_fields(
    loop_policy: Mapping[str, object],
) -> tuple[str, ...]:
    """Return required loop-policy fields absent from *loop_policy*."""
    return tuple(field for field in REQUIRED_LOOP_POLICY_FIELDS if field not in loop_policy)


def is_allowed_review_depth(value: object) -> bool:
    """Return whether *value* is one of the canonical review depths."""
    return isinstance(value, str) and value in ALLOWED_REVIEW_DEPTHS


def is_allowed_claim_status(value: object) -> bool:
    """Return whether *value* is one of the canonical claim statuses."""
    return isinstance(value, str) and value in ALLOWED_CLAIM_STATUSES


def packet_declares_boundary_label(packet: object) -> bool:
    """Return whether JSON-serializable *packet* contains every boundary line."""
    try:
        serialized = json.dumps(packet, sort_keys=True)
    except (TypeError, ValueError):
        return False
    return all(line in serialized for line in BOUNDARY_LABEL.splitlines())


def is_preflight_evidence_class(value: object) -> bool:
    """Return whether a string identifies conservative preflight evidence."""
    if not isinstance(value, str):
        return False
    normalized = value.lower().replace("-", "_")
    return "preflight" in normalized or (
        "bridge" in normalized and "proof" in normalized and "chain" in normalized
    )
