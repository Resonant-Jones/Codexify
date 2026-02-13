from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from guardian.flows.compiler import compile_flow
from guardian.flows.nl_compiler import (
    compile_draft_with_gating,
    draft_flow_from_text,
)
from guardian.flows.primitives import PrimitiveRegistry
from guardian.flows.runner import clear_run_cache, run_flow
from guardian.flows.spec import FlowSpec


def _base_flow_spec() -> dict:
    return {
        "flow_id": "unit_test_flow_v1",
        "version": "0.1",
        "enabled": True,
        "trigger": {"type": "manual", "schedule": None, "event_name": None},
        "scope": {
            "user_id": "default",
            "project_ids": [],
            "thread_ids": [],
            "persona": "guardian.tests",
        },
        "budget": {"max_steps": 5, "max_tokens": 3000, "timeout_seconds": 60},
        "policy": {
            "min_confidence": 0.75,
            "require_confirmation_below_threshold": True,
            "allow_side_effects_without_confirmation": True,
        },
        "steps": [
            {
                "step_id": "ctx",
                "primitive": "assemble_context",
                "params": {
                    "intent": "Summarize activity.",
                    "sources": {"threads": True, "memory": True},
                    "window": {"threads_days": 3, "memory_days": 7},
                    "search_depth": 2,
                    "max_items": 20,
                },
            },
            {
                "step_id": "sum",
                "primitive": "summarize",
                "params": {
                    "schema_name": "summary_v1",
                    "instructions": ["Return concise bullets."],
                },
            },
        ],
        "output": {
            "store_as_thread": False,
            "store_as_codex": False,
            "emit_event": None,
        },
        "idempotency": {
            "key_template": "unit_test_flow_v1::{{date}}",
            "mode": "return_cached",
        },
        "audit": {"log_trace": True, "record_cost": True, "redact_fields": []},
    }


def _build_flows_router_test_client():
    previous_dependencies_module = sys.modules.get("guardian.core.dependencies")
    stub = types.ModuleType("guardian.core.dependencies")
    stub.require_api_key = lambda: "test-key"  # noqa: E731
    sys.modules["guardian.core.dependencies"] = stub

    module_path = (
        Path(__file__).resolve().parents[1] / "guardian" / "routes" / "flows.py"
    )
    spec = importlib.util.spec_from_file_location(
        "flows_router_test_module", module_path
    )
    assert spec is not None and spec.loader is not None
    try:
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
    finally:
        if previous_dependencies_module is None:
            sys.modules.pop("guardian.core.dependencies", None)
        else:
            sys.modules[
                "guardian.core.dependencies"
            ] = previous_dependencies_module

    module._FLOWS.clear()
    module._FLOW_RUNS.clear()
    module._RUN_INDEX.clear()

    app = FastAPI()
    app.include_router(module.router)
    client = TestClient(app)
    return module, client


def test_flows_router_test_client_restores_dependencies_module():
    previous_dependencies_module = sys.modules.get("guardian.core.dependencies")
    _module, _client = _build_flows_router_test_client()
    if previous_dependencies_module is None:
        assert "guardian.core.dependencies" not in sys.modules
    else:
        assert (
            sys.modules.get("guardian.core.dependencies")
            is previous_dependencies_module
        )


def test_flowspec_validation_rejects_duplicate_step_ids():
    spec = _base_flow_spec()
    spec["steps"][1]["step_id"] = "ctx"
    try:
        FlowSpec.model_validate(spec)
    except ValidationError:
        return
    raise AssertionError(
        "Expected FlowSpec validation to fail on duplicate step_id"
    )


def test_primitive_param_validation_rejects_unknown_field():
    registry = PrimitiveRegistry.default()
    try:
        registry.validate_params(
            "summarize",
            {
                "schema_name": "summary_v1",
                "instructions": ["ok"],
                "extra_field": "not allowed",
            },
        )
    except ValidationError:
        return
    raise AssertionError("Expected ValidationError for unknown summarize param")


def test_compile_flow_adds_warning_for_side_effect_policy():
    spec = _base_flow_spec()
    spec["policy"]["allow_side_effects_without_confirmation"] = False
    spec["steps"].append(
        {
            "step_id": "thread",
            "primitive": "create_thread",
            "params": {
                "title_template": "Test {{date}}",
                "body_template": {"format": "markdown", "sections": []},
            },
        }
    )
    compiled = compile_flow(spec)
    assert compiled.warnings
    assert compiled.requires_confirmation is True


def test_compile_flow_requires_confirmation_even_if_threshold_toggle_disabled():
    spec = _base_flow_spec()
    spec["policy"]["allow_side_effects_without_confirmation"] = False
    spec["policy"]["require_confirmation_below_threshold"] = False
    spec["steps"].append(
        {
            "step_id": "thread",
            "primitive": "create_thread",
            "params": {
                "title_template": "Test {{date}}",
                "body_template": {"format": "markdown", "sections": []},
            },
        }
    )
    compiled = compile_flow(spec)
    assert compiled.warnings
    assert compiled.requires_confirmation is True


def test_nl_compiler_low_confidence_requires_confirmation():
    draft = draft_flow_from_text("summarize")
    result = compile_draft_with_gating(draft)
    assert 0.0 <= draft.confidence <= 1.0
    assert result.needs_confirmation is True
    assert result.clarifying_questions


def test_run_flow_minimal_path_and_idempotency_cache():
    clear_run_cache()
    compiled = compile_flow(_base_flow_spec())
    first = run_flow(
        compiled, context={"date": "2026-02-12", "confirmed": True}
    )
    second = run_flow(
        compiled, context={"date": "2026-02-12", "confirmed": True}
    )

    assert first.status == "success"
    assert len(first.step_results) == 2
    assert second.status == "cached"


def test_patch_flow_rejects_flow_id_mutation():
    _module, client = _build_flows_router_test_client()
    headers = {"X-API-Key": "test-key"}
    flow_spec = _base_flow_spec()

    created = client.post("/api/flows", json=flow_spec, headers=headers)
    assert created.status_code == 201

    patched = client.patch(
        "/api/flows/unit_test_flow_v1",
        json={"flow_id": "mutated_flow_v2"},
        headers=headers,
    )
    assert patched.status_code == 400
    assert "flow_id cannot be changed" in patched.json()["detail"]

    old_flow = client.get("/api/flows/unit_test_flow_v1", headers=headers)
    assert old_flow.status_code == 200
    assert old_flow.json()["flow"]["flow_id"] == "unit_test_flow_v1"

    missing_new = client.get("/api/flows/mutated_flow_v2", headers=headers)
    assert missing_new.status_code == 404
