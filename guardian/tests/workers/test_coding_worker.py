from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Any

from guardian.agents.adapters.base import AgentRunEnvelope
from guardian.agents.coding_agent_contracts import CodingAgentPermissionPolicy
from guardian.tasks.types import CodingExecutionTask
from guardian.workers.coding_worker import (
    CodingWorker,
    resolve_max_validation_attempts,
)


@dataclass
class _FakeStore:
    coding_results: list[dict[str, Any]]
    run_statuses: list[dict[str, Any]]

    def store_coding_result(self, **kwargs: Any) -> dict[str, Any]:
        self.coding_results.append(dict(kwargs))
        return dict(kwargs)

    def update_run_status(self, **kwargs: Any) -> None:
        self.run_statuses.append(dict(kwargs))


@dataclass
class _FakePublisher:
    events: list[dict[str, Any]]

    def emit(
        self,
        *,
        run_id: str,
        event_type: str,
        payload: dict[str, Any] | None = None,
        run_step_id: int | None = None,
        attempt_id: int | None = None,
    ) -> None:
        self.events.append(
            {
                "run_id": run_id,
                "event_type": event_type,
                "payload": dict(payload or {}),
                "run_step_id": run_step_id,
                "attempt_id": attempt_id,
            }
        )


class _FakeAdapter:
    def __init__(self, responses: list[AgentRunEnvelope]) -> None:
        self.responses = list(responses)
        self.prompts: list[str] = []

    def execute(self, request: Any) -> AgentRunEnvelope:
        self.prompts.append(str(request.prompt))
        if not self.responses:
            raise AssertionError("adapter was called too many times")
        return self.responses.pop(0)


def _task(
    *,
    validation_command: str | None = "pytest -q",
    max_validation_attempts: int | None = 3,
    allow_shell: bool = True,
    adapter_kind: str = "mock",
) -> CodingExecutionTask:
    return CodingExecutionTask(
        run_id="run-123",
        coding_task_id="coding-task-123",
        thread_id="thread-123",
        source_message_id="message-123",
        attempt_id="attempt-123",
        user_id="local",
        project_id=None,
        adapter_kind=adapter_kind,
        instructions="Fix the failing parser.",
        repo_root="/workspace/repo",
        context_summary="Working on the parser regression.",
        permission_policy=CodingAgentPermissionPolicy(
            allow_shell=allow_shell,
            allow_network=False,
            allow_write=True,
            allowed_paths=("/workspace/repo",),
            max_runtime_seconds=30,
        ),
        validation_command=validation_command,
        max_validation_attempts=max_validation_attempts,
    )


def _response(status: str, summary: str) -> AgentRunEnvelope:
    return AgentRunEnvelope(status=status, summary=summary)


def _validation_proc(
    returncode: int,
    stdout: str = "",
    stderr: str = "",
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args="pytest -q",
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


def _event_types(events: list[dict[str, Any]]) -> list[str]:
    return [event["event_type"] for event in events]


def test_validation_limit_one_preserves_fail_closed_behavior() -> None:
    store = _FakeStore(coding_results=[], run_statuses=[])
    publisher = _FakePublisher(events=[])
    adapter = _FakeAdapter([_response("ok", "adapter ok")])
    worker = CodingWorker(
        store=store,
        event_publisher=publisher,
        adapter_resolver=lambda _kind: adapter,
        validation_runner=lambda *_args: _validation_proc(
            1, stdout="FAILED tests/test_parser.py::test_parser"
        ),
        env={"CODING_WORKER_MAX_VALIDATION_ATTEMPTS": "9"},
    )

    outcome = worker._process_task(_task(max_validation_attempts=1))

    assert outcome.status == "failed"
    assert outcome.attempts == 1
    assert len(adapter.prompts) == 1
    assert len(store.coding_results) == 0
    assert (
        len(
            [
                event
                for event in publisher.events
                if event["event_type"] == "task.retrying"
            ]
        )
        == 0
    )
    assert outcome.error_code == "VALIDATION_FAILED"


def test_validation_failure_then_pass_retries_exactly_once_and_completes() -> (
    None
):
    store = _FakeStore(coding_results=[], run_statuses=[])
    publisher = _FakePublisher(events=[])
    adapter = _FakeAdapter(
        [_response("ok", "adapter ok"), _response("ok", "adapter ok again")]
    )
    validation_results = [
        _validation_proc(
            1,
            stdout=(
                "=========================== short test summary info ===========================\n"
                "FAILED tests/test_parser.py::test_parser - AssertionError: mismatch\n"
                "1 failed, 2 passed in 0.20s\n"
            ),
            stderr="E   AssertionError: mismatch\n",
        ),
        _validation_proc(0, stdout="3 passed in 0.11s", stderr=""),
    ]
    worker = CodingWorker(
        store=store,
        event_publisher=publisher,
        adapter_resolver=lambda _kind: adapter,
        validation_runner=lambda *_args: validation_results.pop(0),
    )

    outcome = worker._process_task(_task(max_validation_attempts=3))

    assert outcome.status == "completed"
    assert outcome.attempts == 2
    assert len(adapter.prompts) == 2
    assert "Validation failed" in adapter.prompts[1]
    assert "Fail signature:" in adapter.prompts[1]
    assert len(store.coding_results) == 1
    stored = store.coding_results[0]["result_json"]
    assert stored["validation_result"]["status"] == "passed"
    assert stored["attempt_count"] == 2
    assert "task.retrying" in _event_types(publisher.events)
    assert "task.completed" in _event_types(publisher.events)


def test_validation_failure_across_all_attempts_emits_terminal_failure() -> (
    None
):
    store = _FakeStore(coding_results=[], run_statuses=[])
    publisher = _FakePublisher(events=[])
    adapter = _FakeAdapter([_response("ok", "adapter ok")] * 3)
    worker = CodingWorker(
        store=store,
        event_publisher=publisher,
        adapter_resolver=lambda _kind: adapter,
        validation_runner=lambda *_args: _validation_proc(
            1,
            stdout=(
                "FAILED tests/test_parser.py::test_parser - AssertionError: mismatch\n"
                "1 failed, 2 passed in 0.20s\n"
            ),
            stderr="E   AssertionError: mismatch\n",
        ),
    )

    outcome = worker._process_task(_task(max_validation_attempts=2))

    assert outcome.status == "failed"
    assert outcome.attempts == 2
    assert outcome.error_code == "VALIDATION_FAILED"
    assert len(store.coding_results) == 0
    failed_events = [
        event
        for event in publisher.events
        if event["event_type"] == "task.failed"
    ]
    assert failed_events
    payload = failed_events[-1]["payload"]
    assert payload["attempt_count"] == 2
    assert payload["validation_result"]["status"] == "failed"
    assert payload["best_validation_result"]["status"] == "failed"


def test_retry_prompt_includes_bounded_normalized_failure_feedback() -> None:
    store = _FakeStore(coding_results=[], run_statuses=[])
    publisher = _FakePublisher(events=[])
    adapter = _FakeAdapter(
        [_response("ok", "adapter ok"), _response("ok", "adapter ok again")]
    )
    very_long_stdout = "stdout-line " + ("x" * 5000)
    very_long_stderr = "stderr-line " + ("y" * 5000)
    worker = CodingWorker(
        store=store,
        event_publisher=publisher,
        adapter_resolver=lambda _kind: adapter,
        validation_runner=lambda *_args: _validation_proc(
            1,
            stdout=very_long_stdout,
            stderr=very_long_stderr,
        ),
    )

    worker._process_task(_task(max_validation_attempts=2))

    assert len(adapter.prompts) == 2
    retry_prompt = adapter.prompts[1]
    assert "Validation command: pytest -q" in retry_prompt
    assert "Fail signature:" in retry_prompt
    assert "stdout-line" in retry_prompt
    assert "stderr-line" in retry_prompt
    assert ("x" * 3000) not in retry_prompt
    assert ("y" * 3000) not in retry_prompt


def test_validation_is_not_retried_when_shell_permission_is_false() -> None:
    store = _FakeStore(coding_results=[], run_statuses=[])
    publisher = _FakePublisher(events=[])
    adapter = _FakeAdapter([_response("ok", "adapter ok")])
    validation_calls: list[tuple[str, str | None, int | None]] = []

    def validation_runner(
        command: str, cwd: str | None, timeout_seconds: int | None
    ) -> subprocess.CompletedProcess[str]:
        validation_calls.append((command, cwd, timeout_seconds))
        return _validation_proc(1)

    worker = CodingWorker(
        store=store,
        event_publisher=publisher,
        adapter_resolver=lambda _kind: adapter,
        validation_runner=validation_runner,
    )

    outcome = worker._process_task(
        _task(allow_shell=False, max_validation_attempts=3)
    )

    assert outcome.status == "failed"
    assert validation_calls == []
    assert len(adapter.prompts) == 1
    assert "task.retrying" not in _event_types(publisher.events)


def test_validation_is_not_retried_when_no_validation_command_exists() -> None:
    store = _FakeStore(coding_results=[], run_statuses=[])
    publisher = _FakePublisher(events=[])
    adapter = _FakeAdapter([_response("ok", "adapter ok")])
    validation_calls: list[tuple[str, str | None, int | None]] = []

    def validation_runner(
        command: str, cwd: str | None, timeout_seconds: int | None
    ) -> subprocess.CompletedProcess[str]:
        validation_calls.append((command, cwd, timeout_seconds))
        return _validation_proc(0)

    worker = CodingWorker(
        store=store,
        event_publisher=publisher,
        adapter_resolver=lambda _kind: adapter,
        validation_runner=validation_runner,
    )

    outcome = worker._process_task(
        _task(validation_command=None, max_validation_attempts=3)
    )

    assert outcome.status == "completed"
    assert validation_calls == []
    assert len(store.coding_results) == 1
    assert "task.retrying" not in _event_types(publisher.events)


def test_adapter_failure_does_not_enter_validation_retry_loop() -> None:
    store = _FakeStore(coding_results=[], run_statuses=[])
    publisher = _FakePublisher(events=[])
    adapter = _FakeAdapter([_response("error", "adapter failed")])
    validation_calls: list[tuple[str, str | None, int | None]] = []

    def validation_runner(
        command: str, cwd: str | None, timeout_seconds: int | None
    ) -> subprocess.CompletedProcess[str]:
        validation_calls.append((command, cwd, timeout_seconds))
        return _validation_proc(0)

    worker = CodingWorker(
        store=store,
        event_publisher=publisher,
        adapter_resolver=lambda _kind: adapter,
        validation_runner=validation_runner,
    )

    outcome = worker._process_task(_task(max_validation_attempts=3))

    assert outcome.status == "failed"
    assert validation_calls == []
    assert len(store.coding_results) == 0
    assert outcome.error_code == "DELEGATION_EXECUTOR_NONZERO_EXIT"


def test_unknown_adapter_fails_closed() -> None:
    store = _FakeStore(coding_results=[], run_statuses=[])
    publisher = _FakePublisher(events=[])
    worker = CodingWorker(
        store=store,
        event_publisher=publisher,
        adapter_resolver=lambda _kind: None,
    )

    outcome = worker._process_task(_task(adapter_kind="missing"))

    assert outcome.status == "failed"
    assert outcome.error_code == "CODING_ADAPTER_NOT_FOUND"
    assert len(store.coding_results) == 0
    assert "task.failed" in _event_types(publisher.events)


def test_final_failure_event_includes_validation_result_and_attempt_count() -> (
    None
):
    store = _FakeStore(coding_results=[], run_statuses=[])
    publisher = _FakePublisher(events=[])
    adapter = _FakeAdapter(
        [_response("ok", "adapter ok"), _response("ok", "adapter ok again")]
    )
    worker = CodingWorker(
        store=store,
        event_publisher=publisher,
        adapter_resolver=lambda _kind: adapter,
        validation_runner=lambda *_args: _validation_proc(
            1,
            stdout="FAILED tests/test_parser.py::test_parser - AssertionError\n1 failed, 2 passed in 0.20s\n",
            stderr="E   AssertionError: mismatch\n",
        ),
    )

    worker._process_task(_task(max_validation_attempts=2))

    failed_event = next(
        event
        for event in reversed(publisher.events)
        if event["event_type"] == "task.failed"
    )
    assert failed_event["payload"]["attempt_count"] == 2
    assert failed_event["payload"]["validation_result"]["status"] == "failed"
    assert (
        failed_event["payload"]["best_validation_result"]["status"] == "failed"
    )


def test_completed_event_includes_validation_result_evidence() -> None:
    store = _FakeStore(coding_results=[], run_statuses=[])
    publisher = _FakePublisher(events=[])
    adapter = _FakeAdapter([_response("ok", "adapter ok")])
    worker = CodingWorker(
        store=store,
        event_publisher=publisher,
        adapter_resolver=lambda _kind: adapter,
        validation_runner=lambda *_args: _validation_proc(
            0, stdout="3 passed in 0.11s"
        ),
    )

    outcome = worker._process_task(_task(max_validation_attempts=3))

    assert outcome.status == "completed"
    completed_event = next(
        event
        for event in reversed(publisher.events)
        if event["event_type"] == "task.completed"
    )
    assert completed_event["payload"]["attempt_count"] == 1
    assert completed_event["payload"]["validation_result"]["status"] == "passed"
    assert (
        store.coding_results[0]["result_json"]["validation_result"]["status"]
        == "passed"
    )


def test_validation_attempt_limit_parsing_clamps_safely() -> None:
    assert resolve_max_validation_attempts(env_value="0") == 1
    assert resolve_max_validation_attempts(env_value="4") == 4
    assert resolve_max_validation_attempts(env_value="999") == 10
    assert resolve_max_validation_attempts(env_value="bad") == 3
