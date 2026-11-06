"""The worker-to-adapter ``reasoning_effort`` handoff.

The effort reaches the harness through one route only: the execution binding
Guardian minted. These cases pin that route end to end at the seams that can
be observed without a provider:

- the worker forwards the binding's level verbatim and selects none itself;
- the adapter hands the harness exactly the level it was given;
- a caller-supplied task-level ``reasoning_effort`` cannot override the
  binding, because the task contract does not carry one;
- a binding whose level is not one its lane validated is refused before
  anything executes;
- the governed lane's level is one the harness can actually report back, which
  is why the harness default is not a safe fallback on that lane.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from guardian.agents.adapters import pi_codex_runner
from guardian.agents.adapters.base import (
    AgentExecutionIdentity,
    AgentExecutionRequest,
)
from guardian.agents.coding_agent_contracts import (
    CODING_EXECUTION_REASONING_EFFORT_LANES,
    CodingExecutionBinding,
    coding_execution_reasoning_effort_lane,
)
from guardian.tasks.types import CodingExecutionTask
from guardian.workers.coding_worker import (
    _authorized_reasoning_effort_kwargs,
    _validate_task_execution_binding,
)

GOVERNED_PROVIDER_ID = "deepseek"
GOVERNED_MODEL_ID = "deepseek-v4-flash"

#: The vendored Pi model catalogue the harness resolves its thinking levels
#: from. The wrapper refuses an invocation whose effective thinking level
#: differs from the requested one, so a level the model maps to ``null`` can
#: never be honoured and never reaches provider execution.
_PI_MODEL_CATALOGUE = (
    Path(__file__).resolve().parents[2]
    / "codex_runner"
    / "vendor"
    / "pi-coding-agent"
    / "node_modules"
    / "@earendil-works"
    / "pi-ai"
    / "dist"
    / "providers"
    / "data"
    / "deepseek.json"
)


def _credential(provider_id: str) -> dict[str, object]:
    return {
        "credential_ref": "credential-account-a",
        "owner_scope": "account",
        "owner_id": "account-a",
        "provider_id": provider_id,
        "credential_type": "api_key",
        "funding_route": "user_byok",
        "source_class": "account_api_key",
        "usage_policy_ref": None,
    }


def _governed_binding() -> CodingExecutionBinding:
    return CodingExecutionBinding.authorized(
        harness_id="pi",
        harness_selection_mode="default",
        provider_id=GOVERNED_PROVIDER_ID,
        model_id=GOVERNED_MODEL_ID,
        placement="container",
        credential=_credential(GOVERNED_PROVIDER_ID),
        user_id="account-a",
        project_id=None,
        thread_id="thread-a",
        source_message_id="message-a",
        coding_task_id="coding-task-a",
        attempt_id="attempt-a",
        max_attempts=1,
    )


def test_the_worker_forwards_the_governed_level_verbatim() -> None:
    """The worker hands the harness the level the binding governs.

    The worker never selects a level of its own — not from the model
    identity, not from ambient process configuration.
    """
    binding = _governed_binding()

    assert binding.reasoning_effort == "off"
    assert _authorized_reasoning_effort_kwargs(binding) == {"reasoning_effort": "off"}


def test_the_worker_forwards_no_level_for_an_ungoverned_binding() -> None:
    """A binding that does not govern the effort forwards no value at all.

    Those lanes keep the harness default exactly as before the contract
    existed; the worker does not restate it as an authorized value.
    """
    binding = CodingExecutionBinding.authorized(
        harness_id="pi",
        harness_selection_mode="default",
        provider_id="test-provider",
        model_id="test-model",
        placement="container",
        credential=_credential("test-provider"),
        user_id="account-a",
        project_id=None,
        thread_id="thread-a",
        source_message_id="message-a",
        coding_task_id="coding-task-a",
        attempt_id="attempt-a",
        max_attempts=1,
    )

    assert binding.reasoning_effort is None
    assert _authorized_reasoning_effort_kwargs(binding) == {}


def test_the_harness_receives_exactly_the_authorized_level(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The adapter gives the harness the level it was handed, unchanged.

    This is the last seam before the wrapper: the value the adapter puts in
    the subprocess environment is the value the harness is asked for, so the
    level that reaches the provider is the level Guardian authorized.
    """
    captured: dict[str, Any] = {}

    def _fake_run(cmd: list[str], **kwargs: Any) -> Any:
        captured["cmd"] = cmd
        captured["env"] = dict(kwargs.get("env") or {})
        captured["stdin"] = kwargs.get("input")
        raise pi_codex_runner.subprocess.TimeoutExpired(cmd, 1)

    monkeypatch.setattr(pi_codex_runner.subprocess, "run", _fake_run)

    identity = AgentExecutionIdentity(
        provider_id=GOVERNED_PROVIDER_ID,
        model_id=GOVERNED_MODEL_ID,
        harness_id="pi",
        harness_version="0.82.1",
        binding_id="xeb-test",
    )
    pi_codex_runner.PiCodexRunnerAdapter().execute_authorized(
        AgentExecutionRequest(prompt="Do the thing.", timeout_seconds=5),
        identity,
        credential_material="sk-test",
        read_only=True,
        reasoning_effort="off",
    )

    assert captured["env"]["PI_THINKING"] == "off"
    assert captured["env"]["PI_PROVIDER"] == GOVERNED_PROVIDER_ID
    assert captured["env"]["PI_MODEL"] == GOVERNED_MODEL_ID
    # The credential reaches the harness over stdin, never as an argument.
    assert captured["stdin"] is not None
    assert "sk-test" not in json.dumps(captured["cmd"])


def test_a_caller_supplied_task_level_cannot_override_the_binding() -> None:
    """A task-level ``reasoning_effort`` never reaches the harness.

    The task contract does not carry an effort, so a caller-supplied field is
    dropped at the queue boundary and the binding stays the only carrier.
    """
    binding = _governed_binding()
    task = CodingExecutionTask.from_dict(
        {
            "type": "coding_execution",
            "run_id": "run-a",
            "deployment_id": "deployment-a",
            "coding_task_id": "coding-task-a",
            "attempt_id": "attempt-a",
            "thread_id": "thread-a",
            "source_message_id": "message-a",
            "user_id": "account-a",
            "instructions": "Do the thing.",
            "reasoning_effort": "high",
            "execution_binding": binding.to_dict(),
        }
    )

    assert not hasattr(task, "reasoning_effort")
    assert _authorized_reasoning_effort_kwargs(binding) == {"reasoning_effort": "off"}


def test_the_worker_refuses_a_binding_whose_level_is_off_lane() -> None:
    """A binding that carries an off-lane level is refused before execution.

    The binding is compared with the persisted deployment specification and
    then validated against its own lane, so a level Guardian never authorized
    for that lane stops the attempt before the harness runs.
    """
    binding = _governed_binding()
    payload = binding.to_dict()
    payload["reasoning_effort"] = "medium"
    task = CodingExecutionTask.from_dict(
        {
            "type": "coding_execution",
            "run_id": "run-a",
            "deployment_id": "deployment-a",
            "coding_task_id": "coding-task-a",
            "attempt_id": "attempt-a",
            "thread_id": "thread-a",
            "source_message_id": "message-a",
            "user_id": "account-a",
            "instructions": "Do the thing.",
            "execution_binding": payload,
        }
    )
    spec = {
        "user_id": "account-a",
        "execution_binding": payload,
    }

    with pytest.raises(ValueError) as excinfo:
        _validate_task_execution_binding(task, spec)

    assert str(excinfo.value) == "execution_binding_reasoning_effort_unsupported"


def test_the_governed_lane_default_is_a_level_the_harness_can_honour() -> None:
    """The lane's default is honourable on that lane; the harness default is not.

    The wrapper refuses an invocation whose effective thinking level differs
    from the requested one. The vendored model catalogue maps a level to
    ``null`` when the model cannot report it back, and those levels are
    exactly the ones that fail before provider execution.
    """
    catalogue = json.loads(_PI_MODEL_CATALOGUE.read_text(encoding="utf-8"))
    models = catalogue.get("openai-completions", {})
    assert GOVERNED_MODEL_ID in models
    thinking_level_map = models[GOVERNED_MODEL_ID].get("thinkingLevelMap") or {}

    def _honourable(level: str) -> bool:
        # A level the catalogue maps to null can never be reported back, so
        # the wrapper's effective-vs-requested gate rejects it.
        return thinking_level_map.get(level) is not None

    for lane in CODING_EXECUTION_REASONING_EFFORT_LANES:
        if lane.provider_id != GOVERNED_PROVIDER_ID:
            continue
        assert _honourable(lane.default) or lane.default not in thinking_level_map

    # The harness default the adapter would otherwise substitute is exactly
    # the level this lane cannot honour.
    assert thinking_level_map.get("medium") is None
    assert not _honourable("medium")


def test_the_governed_lane_is_the_one_the_binding_resolves() -> None:
    """The lane the worker is given is the lane the binding governs."""
    lane = coding_execution_reasoning_effort_lane(
        GOVERNED_PROVIDER_ID, GOVERNED_MODEL_ID
    )
    assert lane is not None
    assert lane.default == "off"
    assert lane.compatible == frozenset({"off", "high"})
