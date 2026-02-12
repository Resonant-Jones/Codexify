#!/usr/bin/env python3
"""Smoke test for flow create/validate/run/run-trace route path."""

from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _load_flows_router(repo_root: Path):
    # Avoid heavy side-effects from importing full dependency stack.
    stub = types.ModuleType("guardian.core.dependencies")
    stub.require_api_key = lambda: "smoke-key"  # noqa: E731
    sys.modules["guardian.core.dependencies"] = stub

    module_path = repo_root / "guardian" / "routes" / "flows.py"
    spec = importlib.util.spec_from_file_location("flows_router_module", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load flows router module from {module_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.router


def _assert_ok(response, action: str) -> None:
    if response.status_code >= 400:
        raise RuntimeError(
            f"{action} failed with status={response.status_code}: {response.text}"
        )


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    examples_path = repo_root / "docs" / "examples" / "flowspec_examples.json"
    examples_doc = json.loads(examples_path.read_text(encoding="utf-8"))
    flow_spec = examples_doc["examples"][0]["flow_spec"]
    flow_id = flow_spec["flow_id"]

    app = FastAPI()
    app.include_router(_load_flows_router(repo_root))
    client = TestClient(app)
    headers = {"X-API-Key": "smoke-key"}

    created = client.post("/api/flows", json=flow_spec, headers=headers)
    _assert_ok(created, "create flow")

    validated = client.post(f"/api/flows/{flow_id}/validate", headers=headers)
    _assert_ok(validated, "validate flow")

    ran = client.post(
        f"/api/flows/{flow_id}/run",
        json={"context": {"date": "2026-02-12"}, "confirmed": True},
        headers=headers,
    )
    _assert_ok(ran, "run flow")
    run_id = ran.json()["run"]["run_id"]

    list_runs = client.get(f"/api/flows/{flow_id}/runs", headers=headers)
    _assert_ok(list_runs, "list flow runs")
    run_ids = {item["run_id"] for item in list_runs.json()["runs"]}
    if run_id not in run_ids:
        raise RuntimeError("run id missing from flow run list")

    get_run = client.get(f"/api/flows/runs/{run_id}", headers=headers)
    _assert_ok(get_run, "get run trace")

    print("FLOW_SMOKE_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
