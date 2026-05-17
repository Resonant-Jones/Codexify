"""Backend-internal Execution Ledger metadata storage seam.

This module provides pure helpers to read and update Execution Ledger gate
artifacts under existing work-order metadata (`extra_meta`). It does not add
schema, routes, UI behavior, queue behavior, worker behavior, or event
publication.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Mapping

from pydantic import ValidationError

from guardian.agents.execution_ledger_contracts import (
    CompletionProofGateArtifact,
    ImplementationPlanGateArtifact,
    IntentScopeGateArtifact,
)
from guardian.agents.work_orders import WorkOrderUpdate

if TYPE_CHECKING:
    from guardian.agents.work_order_store import WorkOrderStore

EXECUTION_LEDGER_KEY = "execution_ledger"
INTENT_SCOPE_GATE_KEY = "intent_scope_gate"
IMPLEMENTATION_PLAN_GATE_KEY = "implementation_plan_gate"
COMPLETION_PROOF_GATE_KEY = "completion_proof_gate"

_GATE_KEYS: tuple[str, str, str] = (
    INTENT_SCOPE_GATE_KEY,
    IMPLEMENTATION_PLAN_GATE_KEY,
    COMPLETION_PROOF_GATE_KEY,
)


def read_execution_ledger_metadata(work_order: object) -> dict[str, Any]:
    """Return normalized execution-ledger metadata for a work order.

    Returned shape is always:
    {
      "intent_scope_gate": dict | None,
      "implementation_plan_gate": dict | None,
      "completion_proof_gate": dict | None,
    }

    Invalid/non-dict stored payloads are treated as absent (`None`) so reads
    fail closed.
    """

    metadata = _extract_work_order_metadata(work_order)
    ledger = _extract_ledger_namespace(metadata)
    return {
        INTENT_SCOPE_GATE_KEY: _clone_gate_payload(
            ledger.get(INTENT_SCOPE_GATE_KEY)
        ),
        IMPLEMENTATION_PLAN_GATE_KEY: _clone_gate_payload(
            ledger.get(IMPLEMENTATION_PLAN_GATE_KEY)
        ),
        COMPLETION_PROOF_GATE_KEY: _clone_gate_payload(
            ledger.get(COMPLETION_PROOF_GATE_KEY)
        ),
    }


def get_intent_scope_gate(
    work_order: object,
) -> IntentScopeGateArtifact | None:
    payload = read_execution_ledger_metadata(work_order).get(
        INTENT_SCOPE_GATE_KEY
    )
    if not isinstance(payload, dict):
        return None
    return _validate_gate_model(IntentScopeGateArtifact, payload)


def get_implementation_plan_gate(
    work_order: object,
) -> ImplementationPlanGateArtifact | None:
    payload = read_execution_ledger_metadata(work_order).get(
        IMPLEMENTATION_PLAN_GATE_KEY
    )
    if not isinstance(payload, dict):
        return None
    return _validate_gate_model(ImplementationPlanGateArtifact, payload)


def get_completion_proof_gate(
    work_order: object,
) -> CompletionProofGateArtifact | None:
    payload = read_execution_ledger_metadata(work_order).get(
        COMPLETION_PROOF_GATE_KEY
    )
    if not isinstance(payload, dict):
        return None
    return _validate_gate_model(CompletionProofGateArtifact, payload)


def set_intent_scope_gate(
    work_order: object,
    artifact: IntentScopeGateArtifact,
) -> dict[str, Any]:
    return _set_gate_metadata(
        work_order=work_order,
        gate_key=INTENT_SCOPE_GATE_KEY,
        artifact_payload=_serialize_artifact(artifact),
    )


def set_implementation_plan_gate(
    work_order: object,
    artifact: ImplementationPlanGateArtifact,
) -> dict[str, Any]:
    return _set_gate_metadata(
        work_order=work_order,
        gate_key=IMPLEMENTATION_PLAN_GATE_KEY,
        artifact_payload=_serialize_artifact(artifact),
    )


def set_completion_proof_gate(
    work_order: object,
    artifact: CompletionProofGateArtifact,
) -> dict[str, Any]:
    return _set_gate_metadata(
        work_order=work_order,
        gate_key=COMPLETION_PROOF_GATE_KEY,
        artifact_payload=_serialize_artifact(artifact),
    )


def save_intent_scope_gate(
    store: WorkOrderStore,
    work_order_id: str,
    artifact: IntentScopeGateArtifact,
) -> object:
    return _save_gate(
        store=store,
        work_order_id=work_order_id,
        set_gate=set_intent_scope_gate,
        artifact=artifact,
    )


def save_implementation_plan_gate(
    store: WorkOrderStore,
    work_order_id: str,
    artifact: ImplementationPlanGateArtifact,
) -> object:
    return _save_gate(
        store=store,
        work_order_id=work_order_id,
        set_gate=set_implementation_plan_gate,
        artifact=artifact,
    )


def save_completion_proof_gate(
    store: WorkOrderStore,
    work_order_id: str,
    artifact: CompletionProofGateArtifact,
) -> object:
    return _save_gate(
        store=store,
        work_order_id=work_order_id,
        set_gate=set_completion_proof_gate,
        artifact=artifact,
    )


def _save_gate(
    *,
    store: WorkOrderStore,
    work_order_id: str,
    set_gate: Any,
    artifact: Any,
) -> object:
    work_order = store.get_work_order(work_order_id)
    if work_order is None:
        raise LookupError(f"unknown work_order_id: {work_order_id}")

    updated_metadata = set_gate(work_order, artifact)
    return store.update_work_order(
        work_order_id,
        WorkOrderUpdate(extra_meta=updated_metadata),
    )


def _set_gate_metadata(
    *,
    work_order: object,
    gate_key: str,
    artifact_payload: dict[str, Any],
) -> dict[str, Any]:
    metadata = _extract_work_order_metadata(work_order)
    ledger = _extract_ledger_namespace(metadata)
    ledger[gate_key] = artifact_payload

    for key in _GATE_KEYS:
        ledger.setdefault(key, None)

    updated = dict(metadata)
    updated[EXECUTION_LEDGER_KEY] = ledger
    return updated


def _extract_work_order_metadata(work_order: object) -> dict[str, Any]:
    if isinstance(work_order, Mapping):
        maybe_meta = work_order.get("extra_meta")
    else:
        maybe_meta = getattr(work_order, "extra_meta", None)

    if isinstance(maybe_meta, dict):
        return dict(maybe_meta)
    return {}


def _extract_ledger_namespace(metadata: Mapping[str, Any]) -> dict[str, Any]:
    maybe_ledger = metadata.get(EXECUTION_LEDGER_KEY)
    if isinstance(maybe_ledger, dict):
        return dict(maybe_ledger)
    return {}


def _clone_gate_payload(raw: object) -> dict[str, Any] | None:
    if isinstance(raw, dict):
        return dict(raw)
    return None


def _serialize_artifact(artifact: object) -> dict[str, Any]:
    if hasattr(artifact, "model_dump"):
        payload = artifact.model_dump(mode="json")
        if isinstance(payload, dict):
            return payload

    if hasattr(artifact, "dict"):
        payload = artifact.dict()  # pragma: no cover - pydantic v1 fallback
        if isinstance(payload, dict):
            return payload

    raise TypeError(
        "artifact must support dict serialization via model_dump() or dict()"
    )


def _validate_gate_model(model_cls: Any, payload: Mapping[str, Any]) -> Any | None:
    try:
        return model_cls.model_validate(payload)
    except (ValidationError, TypeError, ValueError):
        return None


__all__ = [
    "EXECUTION_LEDGER_KEY",
    "INTENT_SCOPE_GATE_KEY",
    "IMPLEMENTATION_PLAN_GATE_KEY",
    "COMPLETION_PROOF_GATE_KEY",
    "read_execution_ledger_metadata",
    "get_intent_scope_gate",
    "get_implementation_plan_gate",
    "get_completion_proof_gate",
    "set_intent_scope_gate",
    "set_implementation_plan_gate",
    "set_completion_proof_gate",
    "save_intent_scope_gate",
    "save_implementation_plan_gate",
    "save_completion_proof_gate",
]
