"""Provider-free bounded Evaluator verdict adapter checks."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from guardian.agents.adapters.base import AgentExecutionIdentity, AgentExecutionRequest
from guardian.agents.adapters.pi_codex_runner import PiCodexRunnerAdapter
from guardian.pi.evaluator_result import validate_evaluator_result
from guardian.pi.tokens import PI_AUTHORIZED_EVALUATOR_RESULT_CONTRACT


def _verdict():
    return {
        "verdict": "passed", "summary": "The bounded fixture passes.",
        "structured_acceptance_results": [{
            "criterion_id": "fixture", "verdict": "pass",
            "evidence_refs": ["bounded-diff"], "basis": "The exact marker is present.",
        }],
    }


def _frame():
    return {
        "status": "ok", "summary": "bounded",
        "actual_runtime_identity": {
            "actual_provider_id": "deepseek", "actual_model_id": "deepseek-v4-pro",
            "actual_harness_id": "pi-coding-agent", "actual_harness_version": "0.82.1",
        },
        "runtime_identity_established": True, "session_initialized": True,
        "provider_request_started": True,
        "reasoning_effort": {"requested": "medium", "effective": "medium"},
        "automatic_retries_disabled": True,
        "tool_telemetry": {
            "effective_tool_names": [], "write_tool_available": False,
            "tool_execution_start_count": 0, "tool_execution_end_count": 0,
            "executed_tool_names": [], "assistant_tool_call_count": 0,
            "assistant_message_count": 1, "assistant_content_block_types": ["text"],
            "assistant_message_event_types": ["start", "done"],
            "assistant_tool_call_event_count": 0,
        },
        "evaluator_result": _verdict(),
    }


def test_adapter_projects_explicit_contract_and_strips_ambient(tmp_path: Path) -> None:
    observed = {}

    def fake_run(cmd, *, cwd, env, capture_output, text, timeout):
        observed.update(env)
        return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps(_frame()), stderr="")

    with patch.dict(os.environ, {"PI_GUARDIAN_RESULT_CONTRACT": "ambient-other"}):
        with patch("subprocess.run", side_effect=fake_run):
            result = PiCodexRunnerAdapter().execute_authorized(
                AgentExecutionRequest(prompt="Evaluate only", cwd=str(tmp_path), timeout_seconds=10),
                AgentExecutionIdentity(provider_id="deepseek", model_id="deepseek-v4-pro", harness_id="pi-coding-agent", harness_version="0.82.1"),
                read_only=True, reasoning_effort="medium",
                evaluator_result_contract=PI_AUTHORIZED_EVALUATOR_RESULT_CONTRACT,
            )
    assert observed["PI_GUARDIAN_RESULT_CONTRACT"] == PI_AUTHORIZED_EVALUATOR_RESULT_CONTRACT
    assert observed["PI_DISABLE_TOOLS"] == "1"
    assert observed["PI_THINKING"] == "medium"
    assert result.status == "ok"
    assert result.evaluator_result == _verdict()
    assert result.automatic_retries_disabled is True


def test_adapter_rejects_missing_result_without_raw_response() -> None:
    frame = _frame()
    del frame["evaluator_result"]
    parsed = PiCodexRunnerAdapter()._parse_result(
        subprocess.CompletedProcess(["node"], 0, stdout=json.dumps(frame), stderr=""),
        require_runtime_identity=True, require_tool_telemetry=True,
        expected_reasoning_effort="medium",
        evaluator_result_contract=PI_AUTHORIZED_EVALUATOR_RESULT_CONTRACT,
    )
    assert parsed.status == "error"
    assert parsed.failure_stage == "evaluation_result"
    assert parsed.evaluator_result is None


def test_python_result_validator_rejects_extra_content_and_credential_shape() -> None:
    assert validate_evaluator_result(_verdict()) == _verdict()
    with pytest.raises(ValueError):
        validate_evaluator_result({**_verdict(), "reasoning": "unbounded"})
    with pytest.raises(ValueError):
        validate_evaluator_result({**_verdict(), "summary": "Bearer abcdefgh12345678"})
