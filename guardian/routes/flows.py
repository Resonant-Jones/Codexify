"""Flow Builder API routes."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from guardian.cognition.system_profiles.resolver import (
    persist_flow_profile_override,
)
from guardian.core.dependencies import require_api_key
from guardian.flows.compiler import compile_flow
from guardian.flows.runner import run_flow
from guardian.flows.spec import FlowRun, FlowSpec

router = APIRouter(
    prefix="/api/flows",
    tags=["Flows"],
    dependencies=[Depends(require_api_key)],
)

_FLOWS: dict[str, FlowSpec] = {}
_FLOW_RUNS: dict[str, list[FlowRun]] = {}
_RUN_INDEX: dict[str, FlowRun] = {}


class FlowRunRequest(BaseModel):
    context: dict[str, Any] = Field(default_factory=dict)
    confirmed: bool = False
    execution_context: dict[str, Any] | None = None

    model_config = ConfigDict(extra="forbid")


class FlowImportRequest(BaseModel):
    source: str = Field(min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)
    imported_at: datetime | None = None

    model_config = ConfigDict(extra="forbid")


def _deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _require_flow(flow_id: str) -> FlowSpec:
    flow = _FLOWS.get(flow_id)
    if flow is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Flow '{flow_id}' not found",
        )
    return flow


def _coerce_thread_id(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _resolve_thread_id(flow: FlowSpec, context: dict[str, Any]) -> int | None:
    for key in ("thread_id", "chat_thread_id"):
        parsed = _coerce_thread_id(context.get(key))
        if parsed is not None:
            return parsed
    if len(flow.scope.thread_ids) == 1:
        return _coerce_thread_id(flow.scope.thread_ids[0])
    return None


def _looks_like_profile_payload(payload: Any) -> bool:
    return isinstance(payload, dict) and isinstance(
        payload.get("profile_id"), str
    )


def _extract_profile_override_payload(
    run: FlowRun, context: dict[str, Any]
) -> dict[str, Any] | None:
    candidates: list[dict[str, Any]] = []
    direct_context = context.get("profile_override_payload")
    if _looks_like_profile_payload(direct_context):
        candidates.append(direct_context)

    output_payload = run.output.get("profile_override_payload")
    if _looks_like_profile_payload(output_payload):
        candidates.append(output_payload)

    step_outputs = run.output.get("step_outputs")
    if isinstance(step_outputs, dict):
        for output in step_outputs.values():
            if not isinstance(output, dict):
                continue
            nested = output.get("profile_override_payload")
            if _looks_like_profile_payload(nested):
                candidates.append(nested)
            elif _looks_like_profile_payload(output):
                candidates.append(output)

    if not candidates:
        return None
    return candidates[-1]


def _runtime_deps() -> tuple[Any | None, Any | None]:
    try:
        from guardian.core import dependencies as core_dependencies

        db = getattr(core_dependencies, "chatlog_db", None)
        bus = getattr(core_dependencies, "event_bus", None)
        return db, bus
    except Exception:
        return None, None


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_flow(flow_spec: FlowSpec) -> dict[str, Any]:
    if flow_spec.flow_id in _FLOWS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Flow '{flow_spec.flow_id}' already exists",
        )
    _FLOWS[flow_spec.flow_id] = flow_spec
    _FLOW_RUNS.setdefault(flow_spec.flow_id, [])
    return {"ok": True, "flow": flow_spec.model_dump(mode="json")}


@router.get("")
async def list_flows() -> dict[str, Any]:
    flows = [flow.model_dump(mode="json") for flow in _FLOWS.values()]
    return {"ok": True, "flows": flows}


@router.get("/{flow_id}")
async def get_flow(flow_id: str) -> dict[str, Any]:
    flow = _require_flow(flow_id)
    return {"ok": True, "flow": flow.model_dump(mode="json")}


@router.post("/import")
async def import_flow(_payload: FlowImportRequest) -> dict[str, Any]:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=(
            "Flow import/install is disabled for MVP. "
            "Only user-created local flow definitions are supported."
        ),
    )


@router.patch("/{flow_id}")
async def patch_flow(
    flow_id: str,
    patch: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    current = _require_flow(flow_id)
    if "flow_id" in patch and str(patch["flow_id"]) != flow_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="flow_id cannot be changed via PATCH",
        )
    merged_payload = _deep_merge(current.model_dump(mode="json"), patch)
    merged_flow = FlowSpec.model_validate(merged_payload)
    _FLOWS[flow_id] = merged_flow
    return {"ok": True, "flow": merged_flow.model_dump(mode="json")}


@router.post("/{flow_id}/validate")
async def validate_flow(flow_id: str) -> dict[str, Any]:
    flow = _require_flow(flow_id)
    compiled = compile_flow(flow)
    return {
        "ok": True,
        "compiled_flow": compiled.model_dump(mode="json"),
        "warnings": [
            warning.model_dump(mode="json") for warning in compiled.warnings
        ],
        "needs_confirmation": compiled.requires_confirmation,
    }


@router.post("/{flow_id}/run")
async def run_flow_now(flow_id: str, body: FlowRunRequest) -> dict[str, Any]:
    flow = _require_flow(flow_id)
    compiled = compile_flow(flow)
    run_context = dict(body.context)
    run_context["confirmed"] = body.confirmed
    supplied_execution_context = run_context.pop("execution_context", None)
    merged_execution_context: dict[str, Any] = {}
    if isinstance(supplied_execution_context, dict):
        merged_execution_context.update(supplied_execution_context)
    if isinstance(body.execution_context, dict):
        merged_execution_context.update(body.execution_context)
    merged_execution_context.setdefault("pre_authenticated", True)
    run_context["execution_context"] = merged_execution_context
    run = run_flow(compiled, context=run_context)

    profile_override_payload = _extract_profile_override_payload(
        run, run_context
    )
    if profile_override_payload:
        thread_id = _resolve_thread_id(flow, run_context)
        applied: dict[str, Any]
        if thread_id is None:
            applied = {
                "ok": False,
                "reason": "thread_id_unresolved",
                "profile_override_payload": profile_override_payload,
            }
        else:
            db, bus = _runtime_deps()
            if db is None:
                applied = {
                    "ok": False,
                    "reason": "chat_db_unavailable",
                    "thread_id": thread_id,
                    "profile_override_payload": profile_override_payload,
                }
            else:
                try:
                    resolved = persist_flow_profile_override(
                        thread_id,
                        profile_override_payload,
                        chatlog_db=db,
                    )
                    applied = {
                        "ok": True,
                        "thread_id": thread_id,
                        "active_profile_id": resolved.active_profile_id,
                        "provider_override": resolved.provider_override,
                        "model_override": resolved.model_override,
                        "profile_override_payload": profile_override_payload,
                    }
                    if bus is not None and hasattr(bus, "emit_event"):
                        try:
                            bus.emit_event(
                                "thread.profile.override.applied",
                                {
                                    "thread_id": thread_id,
                                    "flow_id": flow_id,
                                    "active_profile_id": resolved.active_profile_id,
                                    "provider_override": resolved.provider_override,
                                    "model_override": resolved.model_override,
                                },
                            )
                        except Exception:
                            pass
                except Exception as exc:
                    applied = {
                        "ok": False,
                        "reason": str(exc),
                        "thread_id": thread_id,
                        "profile_override_payload": profile_override_payload,
                    }
        run.output["profile_override"] = applied

    _FLOW_RUNS.setdefault(flow_id, []).append(run)
    _RUN_INDEX[run.run_id] = run
    return {"ok": True, "run": run.model_dump(mode="json")}


@router.get("/{flow_id}/runs")
async def list_flow_runs(flow_id: str) -> dict[str, Any]:
    _require_flow(flow_id)
    runs = [run.model_dump(mode="json") for run in _FLOW_RUNS.get(flow_id, [])]
    return {"ok": True, "runs": runs}


@router.get("/runs/{run_id}")
async def get_flow_run(run_id: str) -> dict[str, Any]:
    run = _RUN_INDEX.get(run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Flow run '{run_id}' not found",
        )
    return {"ok": True, "run": run.model_dump(mode="json")}
