"""Deterministic identity and hashing for the provider-free Campaign Engine runtime.

Conventions mirror the repository's existing canonical helpers
(`codex_runner/runner.py`: `canonical_json` uses ``sort_keys=True`` and
compact separators with ``ensure_ascii=False``; identities are SHA-256 over
canonical JSON). This package intentionally does NOT import `codex_runner.runner`
so the provider-free runtime carries no subprocess/Git/provider dependency.

Identity rules (test-covered):

- identical canonical campaign input + identical source context + identical
  clock instant yields identical Run/Attempt/Evaluation/Receipt IDs;
- a materially changed Task changes both the Attempt and the Run identity
  (the task is part of the campaign input hash feeding the Run identity);
- a materially changed Executor binding changes the Attempt identity;
- a materially changed source-context record changes the Run lineage identity;
- no random UUIDs: every ID is a prefixed SHA-256 over deterministic input.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

RUN_ID_PREFIX = "run"
ATTEMPT_ID_PREFIX = "attempt"
EVALUATION_ID_PREFIX = "evaluation"
RECEIPT_ID_PREFIX = "receipt"
CAMPAIGN_STATE_ID_PREFIX = "campaign-state"

_ID_HASH_CHARS = 24

_REQUIRED_BINDING_FIELDS = (
    "binding_id",
    "role",
    "provider_id",
    "model_id",
    "adapter_id",
    "binding_revision",
    "configuration_hash",
)


def canonical_json(value: Any) -> str:
    """Repository-consistent canonical serialization."""
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_canonical(payload: Any) -> str:
    """SHA-256 of the canonical JSON serialization of ``payload``."""
    return sha256_text(canonical_json(payload))


def document_hash(document: dict[str, Any]) -> str:
    """Canonical hash of the full loaded campaign document (the input bytes)."""
    return sha256_canonical(document)


def binding_identity_hash(binding: dict[str, Any]) -> str:
    """Hash of the materially identity-bearing fields of a role binding."""
    payload = {field: binding.get(field) for field in _REQUIRED_BINDING_FIELDS}
    return sha256_canonical(payload)


def _short(payload: Any) -> str:
    return sha256_canonical(payload)[:_ID_HASH_CHARS]


def build_run_id(
    campaign_id: str, campaign_input_hash: str, lineage_token: str, clock_iso: str
) -> str:
    return f"{RUN_ID_PREFIX}-" + _short(
        {
            "campaign_id": campaign_id,
            "campaign_input_hash": campaign_input_hash,
            "lineage": lineage_token,
            "clock": clock_iso,
        }
    )


def build_attempt_id(
    run_id: str,
    task_id: str,
    task_hash: str,
    executor_binding_hash: str,
    clock_iso: str,
) -> str:
    return f"{ATTEMPT_ID_PREFIX}-" + _short(
        {
            "run_id": run_id,
            "task_id": task_id,
            "task_hash": task_hash,
            "executor_binding": executor_binding_hash,
            "clock": clock_iso,
            "kind": "provider_free_synthetic",
        }
    )


def build_evaluation_id(
    run_id: str,
    attempt_id: str,
    task_id: str,
    evaluator_binding_hash: str,
    clock_iso: str,
) -> str:
    return f"{EVALUATION_ID_PREFIX}-" + _short(
        {
            "run_id": run_id,
            "attempt_id": attempt_id,
            "task_id": task_id,
            "evaluator_binding": evaluator_binding_hash,
            "clock": clock_iso,
            "kind": "provider_free_fixture",
        }
    )


def build_receipt_id(run_id: str, campaign_id: str, clock_iso: str) -> str:
    return f"{RECEIPT_ID_PREFIX}-" + _short(
        {
            "run_id": run_id,
            "campaign_id": campaign_id,
            "clock": clock_iso,
            "subject": {"subject_type": "campaign", "subject_id": campaign_id},
        }
    )


def build_campaign_state_id(run_id: str, campaign_id: str, clock_iso: str) -> str:
    return f"{CAMPAIGN_STATE_ID_PREFIX}-" + _short(
        {"run_id": run_id, "campaign_id": campaign_id, "clock": clock_iso}
    )
