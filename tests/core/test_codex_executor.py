from __future__ import annotations

import io
import json
import subprocess
from dataclasses import dataclass
from typing import Any

from guardian.core.executors.base import ExecutorRequest
from guardian.core.executors.codex_executor import CodexExecutor
from guardian.protocol_tokens import DelegationJobStatus, ErrorCode


@dataclass
class FakeProcess:
    stdout_text: str = ""
    stderr_text: str = ""
    configured_returncode: int = 0
    raise_timeout: bool = False

    def __post_init__(self) -> None:
        self.stdout = io.StringIO(self.stdout_text)
        self.stderr = io.StringIO(self.stderr_text)
        self.returncode: int | None = None
        self.terminated = False
        self.killed = False
        self.command: list[str] | None = None

    def wait(self, timeout: float | None = None) -> int:
        _ = timeout
        if self.raise_timeout and not self.terminated and not self.killed:
            raise subprocess.TimeoutExpired(
                cmd=self.command or ["codex"],
                timeout=timeout,
            )
        if self.returncode is None:
            self.returncode = self.configured_returncode
        return self.returncode

    def terminate(self) -> None:
        self.terminated = True
        if self.returncode is None:
            self.returncode = -15

    def kill(self) -> None:
        self.killed = True
        if self.returncode is None:
            self.returncode = -9

    def poll(self) -> int | None:
        return self.returncode


def _request() -> ExecutorRequest:
    return ExecutorRequest(
        delegation_id="delegation-1",
        task_id="task-1",
        repo_path="/workspace/codexify",
        executor="codex",
        task_prompt="Return a structured task summary.",
        context={"thread_id": 42},
        tags=["backend", "delegation"],
        thread_id=42,
        project_id=9,
    )


def test_codex_executor_success_returns_structured_result(monkeypatch) -> None:
    stdout_payload = json.dumps(
        {
            "outcomeType": "task_summary",
            "summary": "Codex normalized the delegation lane.",
            "files_changed": ["guardian/core/delegation_service.py"],
            "commands_run": ["pytest -v tests/core/test_codex_executor.py"],
        }
    )
    fake_process = FakeProcess(
        stdout_text=f"{stdout_payload}\n",
        stderr_text="codex: using local workspace\n",
        configured_returncode=0,
    )
    popen_calls: list[tuple[list[str], dict[str, Any]]] = []

    monkeypatch.setattr(
        "guardian.core.executors.codex_executor.shutil.which",
        lambda _binary: "/usr/bin/codex",
    )

    def fake_popen(cmd, **kwargs):  # type: ignore[no-untyped-def]
        popen_calls.append((list(cmd), dict(kwargs)))
        fake_process.command = list(cmd)
        return fake_process

    monkeypatch.setattr(
        "guardian.core.executors.codex_executor.subprocess.Popen",
        fake_popen,
    )

    executor = CodexExecutor(timeout_seconds=30)
    chunks: list[Any] = []
    result = executor.execute(_request(), on_output=chunks.append)

    assert popen_calls
    assert popen_calls[0][0] == [
        "codex",
        "exec",
        "Return a structured task summary.",
    ]
    assert result.status == DelegationJobStatus.COMPLETED.value
    assert result.summary == stdout_payload
    assert result.final_text == stdout_payload
    assert result.files_changed == ["guardian/core/delegation_service.py"]
    assert result.commands_run == [
        "pytest -v tests/core/test_codex_executor.py"
    ]
    assert result.raw_transcript
    assert "[stdout]" in result.raw_transcript
    assert "[stderr]" in result.raw_transcript
    assert chunks and chunks[0].stream == "stdout"
    assert result.result["parsed_output"]["summary"] == (
        "Codex normalized the delegation lane."
    )


def test_codex_executor_missing_binary_becomes_not_found(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "guardian.core.executors.codex_executor.shutil.which",
        lambda _binary: None,
    )

    executor = CodexExecutor(timeout_seconds=30)
    result = executor.execute(_request())

    assert result.status == DelegationJobStatus.FAILED.value
    assert result.failure is not None
    assert (
        result.failure.error_code
        == ErrorCode.DELEGATION_EXECUTOR_NOT_FOUND.value
    )
    assert result.failure.failure_class == "FileNotFoundError"
    assert result.error_message == "Codex binary not found: codex"


def test_codex_executor_timeout_becomes_timeout_failure(monkeypatch) -> None:
    fake_process = FakeProcess(
        stdout_text="working\n",
        configured_returncode=0,
        raise_timeout=True,
    )
    monotonic_values = iter([0.0, 0.2, 0.4, 0.6, 0.8])

    monkeypatch.setattr(
        "guardian.core.executors.codex_executor.shutil.which",
        lambda _binary: "/usr/bin/codex",
    )
    monkeypatch.setattr(
        "guardian.core.executors.codex_executor.time.monotonic",
        lambda: next(monotonic_values),
    )

    def fake_popen(cmd, **kwargs):  # type: ignore[no-untyped-def]
        fake_process.command = list(cmd)
        return fake_process

    monkeypatch.setattr(
        "guardian.core.executors.codex_executor.subprocess.Popen",
        fake_popen,
    )

    executor = CodexExecutor(timeout_seconds=0.1)
    result = executor.execute(_request())

    assert result.status == DelegationJobStatus.FAILED.value
    assert result.failure is not None
    assert (
        result.failure.error_code == ErrorCode.DELEGATION_EXECUTOR_TIMEOUT.value
    )
    assert result.failure.timed_out is True
    assert result.error_message == "Codex execution timed out after 0.1s"


def test_codex_executor_nonzero_exit_becomes_failure(monkeypatch) -> None:
    fake_process = FakeProcess(
        stdout_text="partial output\n",
        stderr_text="codex exited\n",
        configured_returncode=17,
    )
    monkeypatch.setattr(
        "guardian.core.executors.codex_executor.shutil.which",
        lambda _binary: "/usr/bin/codex",
    )

    def fake_popen(cmd, **kwargs):  # type: ignore[no-untyped-def]
        fake_process.command = list(cmd)
        return fake_process

    monkeypatch.setattr(
        "guardian.core.executors.codex_executor.subprocess.Popen",
        fake_popen,
    )

    executor = CodexExecutor(timeout_seconds=30)
    result = executor.execute(_request())

    assert result.status == DelegationJobStatus.FAILED.value
    assert result.failure is not None
    assert (
        result.failure.error_code
        == ErrorCode.DELEGATION_EXECUTOR_NONZERO_EXIT.value
    )
    assert result.failure.returncode == 17
    assert result.error_message == "Codex exited with code 17"


def test_codex_executor_spawn_failure_becomes_spawn_failure(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "guardian.core.executors.codex_executor.shutil.which",
        lambda _binary: "/usr/bin/codex",
    )

    def fake_popen(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        raise OSError("boom")

    monkeypatch.setattr(
        "guardian.core.executors.codex_executor.subprocess.Popen",
        fake_popen,
    )

    executor = CodexExecutor(timeout_seconds=30)
    result = executor.execute(_request())

    assert result.status == DelegationJobStatus.FAILED.value
    assert result.failure is not None
    assert (
        result.failure.error_code
        == ErrorCode.DELEGATION_EXECUTOR_SPAWN_FAILED.value
    )
    assert result.failure.failure_class == "OSError"
    assert result.error_message == "boom"
