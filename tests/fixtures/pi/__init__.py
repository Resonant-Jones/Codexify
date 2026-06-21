"""Canonical dry-run request and response fixtures for Pi/Coder validation.

All fixtures are synthetic, deterministic, and safe (no secrets, raw payloads,
execution controls, or completion verdicts).
"""

from __future__ import annotations

from typing import Any


def valid_pi_dry_run_envelope_payload() -> dict[str, Any]:
    return {
        "guardian_boundary": {"owner_account_id": "acct-dry-run-fixture"},
        "source_thread_id": "thread-fixture-1",
        "source_message_id": "msg-fixture-1",
        "invocation_id": "inv-fixture-1",
        "harness_id": "harness-fixture-1",
        "harness_version": "1.0.0-fixture",
        "provider_lane": {"provider_lane_class": "local"},
        "requested_permissions": [
            {
                "permission": "files.read",
                "resource": "/workspace/fixture",
                "reason": "validate fixture",
            }
        ],
        "granted_permissions": [
            {
                "permission": "files.read",
                "resource": "/workspace/fixture",
                "reason": "validate fixture",
            }
        ],
        "status": "prepared",
    }


def missing_lineage_pi_dry_run_envelope_payload() -> dict[str, Any]:
    payload = valid_pi_dry_run_envelope_payload()
    payload["source_thread_id"] = ""
    payload["source_message_id"] = ""
    return payload


def forbidden_raw_payload_pi_dry_run_envelope_payload() -> dict[str, Any]:
    payload = valid_pi_dry_run_envelope_payload()
    payload["validation_metadata"] = {
        "extra_meta": "RAW_SHOULD_BE_REJECTED",
        "result_json": {"secret": "RAW_SHOULD_BE_REJECTED"},
    }
    return payload


def forbidden_execution_control_pi_dry_run_envelope_payload() -> dict[str, Any]:
    payload = valid_pi_dry_run_envelope_payload()
    payload["validation_metadata"] = {
        "dispatch": True,
        "execute": True,
    }
    return payload


def forbidden_completion_collapse_pi_dry_run_envelope_payload() -> dict[str, Any]:
    payload = valid_pi_dry_run_envelope_payload()
    payload["validation_metadata"] = {
        "completed": True,
        "execution_success": True,
    }
    return payload


def accepted_pi_dry_run_response_payload() -> dict[str, Any]:
    return {
        "dry_run": True,
        "accepted": True,
        "state": "validated",
        "validation_status": "valid",
        "errors": [],
        "warnings": [],
        "redaction_state": "clean",
        "release_support": "unsupported",
        "execution_performed": False,
        "persistence_performed": False,
        "invocation_id": "inv-fixture-1",
        "source_thread_id": "thread-fixture-1",
        "source_message_id": "msg-fixture-1",
        "harness_id": "harness-fixture-1",
        "permission_posture": "files.read",
    }


def rejected_pi_dry_run_response_payload() -> dict[str, Any]:
    return {
        "dry_run": True,
        "accepted": False,
        "state": "validation_failed",
        "validation_status": "failed_closed",
        "errors": ["missing_source_lineage"],
        "warnings": [],
        "redaction_state": "clean",
        "release_support": "unsupported",
        "execution_performed": False,
        "persistence_performed": False,
    }
