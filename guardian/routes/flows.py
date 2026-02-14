"""Flow Builder API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

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
    run = run_flow(compiled, context=run_context)
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
