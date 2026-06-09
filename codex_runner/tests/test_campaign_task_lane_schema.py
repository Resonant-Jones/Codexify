from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

import runner


SCHEMA_PATH = (
    Path(__file__).resolve().parents[1]
    / "schemas"
    / "campaign_set.schema.json"
)


def _validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _minimal_payload(task_lane: str = "standard") -> dict[str, Any]:
    return {
        "audit_id": "AUDIT_abc123def456",
        "generated_at": "2026-06-09T00:00:00Z",
        "campaigns": [
            {
                "campaign_id": "2026-06-09::task_lane::001",
                "campaign_slug": "task_lane",
                "depends_on": [],
                "campaign_markdown": "# Campaign\n",
                "tasks": [
                    {
                        "id": "TASK-001",
                        "slug": "alpha",
                        "task_lane": task_lane,
                        "area": "backend",
                        "risk": "LOW",
                        "files": ["codex_runner/runner.py"],
                        "tests": ["pytest -q codex_runner/tests"],
                        "commit_message": "Add alpha",
                        "task_artifact_markdown": "# Task\n",
                        "activation_prompt": "Do task.",
                        "dependencies": [],
                    }
                ],
            }
        ],
    }


def _errors(payload: dict[str, Any]) -> list[str]:
    return [error.message for error in _validator().iter_errors(payload)]


def test_standard_task_lane_passes_schema_validation() -> None:
    assert _errors(_minimal_payload("standard")) == []


def test_architecture_impact_task_lane_passes_schema_validation() -> None:
    assert _errors(_minimal_payload("architecture_impact")) == []


def test_missing_task_lane_fails_schema_validation() -> None:
    payload = _minimal_payload()
    task = payload["campaigns"][0]["tasks"][0]
    del task["task_lane"]

    assert any(
        "'task_lane' is a required property" in msg
        for msg in _errors(payload)
    )


def test_unknown_task_lane_fails_schema_validation() -> None:
    payload = deepcopy(_minimal_payload())
    payload["campaigns"][0]["tasks"][0]["task_lane"] = "autonomous"

    assert any(
        "'autonomous' is not one of" in msg for msg in _errors(payload)
    )


def test_runner_preserves_task_lane_metadata_for_valid_tasks() -> None:
    task = _minimal_payload("proof_runbook")["campaigns"][0]["tasks"][0]

    normalized = runner.normalize_task(task, "task_lane")

    assert normalized["task_lane"] == "proof_runbook"
