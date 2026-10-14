from __future__ import annotations

import json
import shlex
import signal
import sys
from pathlib import Path
from typing import Any

import pytest

from guardian.core.executors.base import (
    CodeExecutor,
    CodexifyExecutorRequest,
    ExecutorTerminalResult,
)
from guardian.core.executors.codex_app_server_executor import (
    CodexAppServerExecutor,
)
from guardian.protocol_tokens import (
    CodexAppServerFailureKind,
    CodexAppServerShutdownStatus,
    DelegationJobStatus,
    ErrorCode,
    ExecutorId,
    ExecutionEvidenceStatus,
)


_FAKE_APP_SERVER = r"""\
import json
import signal
import sys
import time
from pathlib import Path

marker = Path(sys.argv[1])
mode = sys.argv[2]
if mode == "timeout":
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
methods = []
client_responses = []
server_requests = {}
thread_id = "native-thread-123"
turn_id = "native-turn-456"

def send(value):
    print(json.dumps(value), flush=True)

def finish():
    marker.write_text(json.dumps({
        "methods": methods,
        "client_responses": client_responses,
        "server_requests": server_requests,
    }))

try:
    for raw_line in sys.stdin:
        message = json.loads(raw_line)
        method = message.get("method")
        if method is None:
            client_responses.append(message)
            continue
        methods.append(method)
        server_requests[method] = message.get("params")
        request_id = message.get("id")

        if method == "initialize":
            if mode == "malformed":
                print("not-json", flush=True)
                continue
            if mode == "init_error":
                send({"id": request_id, "error": {"code": -32000, "message": "init rejected"}})
                continue
            send({"id": request_id, "result": {"userAgent": "fixture"}})
        elif method == "initialized":
            continue
        elif method == "thread/start":
            if mode == "thread_error":
                send({"id": request_id, "error": {"code": -32000, "message": "thread rejected"}})
                continue
            send({
                "id": request_id,
                "result": {"thread": {
                    "id": thread_id,
                    "sessionId": "native-session-789",
                    "modelProvider": "fixture-provider",
                    "model": "configured-model",
                }},
            })
        elif method == "turn/start":
            if mode == "turn_error":
                send({"id": request_id, "error": {"code": -32000, "message": "turn rejected"}})
                continue
            send({"id": request_id, "result": {"turn": {"id": turn_id, "status": "inProgress", "items": []}}})
            if mode == "premature":
                break
            if mode == "timeout":
                time.sleep(4)
                continue
            if mode == "unsupported":
                send({
                    "id": "server-request-1",
                    "method": "item/commandExecution/requestApproval",
                    "params": {"threadId": thread_id, "turnId": turn_id, "itemId": "cmd-1"},
                })
                continue
            if mode == "cancel":
                send({
                    "method": "item/agentMessage/delta",
                    "params": {"threadId": thread_id, "turnId": turn_id, "itemId": "msg-1", "delta": "partial output"},
                })
                continue
            if mode == "terminal_failed":
                send({
                    "method": "turn/completed",
                    "params": {"threadId": thread_id, "turn": {"id": turn_id, "status": "failed", "error": {"message": "turn failed"}}},
                })
                continue

            send({
                "method": "item/agentMessage/delta",
                "params": {"threadId": thread_id, "turnId": turn_id, "itemId": "msg-1", "delta": "fixture answer"},
            })
            send({
                "method": "item/completed",
                "params": {"threadId": thread_id, "turnId": turn_id, "item": {
                    "id": "msg-1", "type": "agentMessage", "phase": "final_answer", "text": "fixture answer"
                }},
            })
            send({
                "method": "item/completed",
                "params": {"threadId": thread_id, "turnId": turn_id, "item": {
                    "id": "cmd-1", "type": "commandExecution", "status": "completed", "command": "cat fixture.txt"
                }},
            })
            send({
                "method": "item/completed",
                "params": {"threadId": thread_id, "turnId": turn_id, "item": {
                    "id": "change-1", "type": "fileChange", "status": "completed", "changes": [{"path": "fixture.txt", "kind": "update", "diff": ""}]
                }},
            })
            send({
                "method": "model/rerouted",
                "params": {"threadId": thread_id, "turnId": turn_id, "fromModel": "configured-model", "toModel": "observed-model"},
            })
            send({
                "method": "turn/completed",
                "params": {"threadId": thread_id, "turn": {"id": turn_id, "status": "completed", "items": []}},
            })
        elif method == "turn/interrupt":
            send({"id": request_id, "result": {"interrupted": True}})
            send({
                "method": "turn/completed",
                "params": {"threadId": thread_id, "turn": {"id": turn_id, "status": "interrupted", "items": []}},
            })
        else:
            send({"id": request_id, "result": {}})
finally:
    finish()
"""


def _request(workspace: Path) -> CodexifyExecutorRequest:
    return CodexifyExecutorRequest(
        request_id="delegation-1",
        delegation_id="delegation-1",
        task_id="task-1",
        thread_id=42,
        source_message_id=77,
        project_id=9,
        executor_id=ExecutorId.CODEX.value,
        title="Inspect fixture",
        canonical_task_prompt="Read fixture.txt and report its contents.",
        repo_path=str(workspace),
        task_prompt="Read fixture.txt and report its contents.",
        context={"execution_interface": "app_server"},
        metadata={"request_id": "delegation-1"},
    )


def _executor(
    tmp_path: Path,
    *,
    mode: str = "success",
    timeout_seconds: float = 2.0,
) -> tuple[CodexAppServerExecutor, Path]:
    script = tmp_path / "fake_app_server.py"
    marker = tmp_path / "server_receipt.json"
    script.write_text(_FAKE_APP_SERVER, encoding="utf-8")
    command = shlex.join([sys.executable, str(script), str(marker), mode])
    return (
        CodexAppServerExecutor(
            codex_bin=command,
            timeout_seconds=timeout_seconds,
        ),
        marker,
    )


def _receipt(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_app_server_one_turn_normalizes_result_and_shuts_down_cleanly(
    tmp_path: Path,
) -> None:
    (tmp_path / "fixture.txt").write_text("fixture content", encoding="utf-8")
    executor, marker = _executor(tmp_path)
    request = _request(tmp_path)

    result = executor.execute(request)

    assert isinstance(executor, CodeExecutor)
    assert isinstance(result, ExecutorTerminalResult)
    assert result.status == DelegationJobStatus.COMPLETED.value
    assert result.summary == "fixture answer"
    assert result.files_changed == ["fixture.txt"]
    assert result.commands_run == ["cat fixture.txt"]
    assert result.request_id == "delegation-1"
    assert result.delegation_id == "delegation-1"
    assert result.task_id == "task-1"
    assert result.thread_id == 42
    assert result.source_message_id == 77
    assert result.project_id == 9
    assert result.executor_id == ExecutorId.CODEX.value
    assert result.metadata["execution_channel"] == "codex"
    assert result.metadata["execution_interface"] == "app_server"
    assert result.metadata["app_server_protocol_version"] == "v2"
    assert result.metadata["native_codex_thread_id"] == "native-thread-123"
    assert result.metadata["native_codex_session_id"] == "native-session-789"
    assert result.metadata["native_codex_turn_id"] == "native-turn-456"
    assert result.metadata["thread_id"] == 42
    assert result.metadata["source_message_id"] == 77
    assert result.metadata["inference_route"] == {
        "provider_id": "fixture-provider",
        "evidence_status": ExecutionEvidenceStatus.OBSERVED.value,
        "evidence_source": "thread/start response",
    }
    assert result.metadata["model_identity"]["configured_model_id"] == (
        "configured-model"
    )
    assert result.metadata["model_identity"]["actual_model_id"] == ("observed-model")
    assert result.metadata["funding_route"]["route_id"] is None
    assert result.metadata["funding_route"]["evidence_status"] == (
        ExecutionEvidenceStatus.UNKNOWN.value
    )
    assert result.metadata["process_exit_code"] == 0
    assert result.metadata["shutdown_status"] == (
        CodexAppServerShutdownStatus.CLEAN_EXIT.value
    )
    assert '"method":"initialize"' in result.raw_transcript
    assert '"method":"turn/start"' in result.raw_transcript
    receipt = _receipt(marker)
    assert receipt["methods"].count("thread/start") == 1
    assert receipt["methods"].count("turn/start") == 1
    assert receipt["server_requests"]["thread/start"]["sandbox"] == "read-only"
    assert "exec" not in receipt["methods"]
    assert receipt["client_responses"] == []


@pytest.mark.parametrize(
    ("mode", "expected_kind", "expected_code"),
    [
        (
            "malformed",
            CodexAppServerFailureKind.MALFORMED_PROTOCOL,
            ErrorCode.CODEX_APP_SERVER_PROTOCOL_ERROR,
        ),
        (
            "premature",
            CodexAppServerFailureKind.PREMATURE_PROCESS_EXIT,
            ErrorCode.CODEX_APP_SERVER_PROTOCOL_ERROR,
        ),
        (
            "unsupported",
            CodexAppServerFailureKind.UNSUPPORTED_INTERACTION,
            ErrorCode.CODEX_APP_SERVER_UNSUPPORTED_INTERACTION,
        ),
        (
            "init_error",
            CodexAppServerFailureKind.INITIALIZATION_FAILED,
            ErrorCode.CODEX_APP_SERVER_PROTOCOL_ERROR,
        ),
        (
            "thread_error",
            CodexAppServerFailureKind.THREAD_START_FAILED,
            ErrorCode.CODEX_APP_SERVER_REQUEST_FAILED,
        ),
        (
            "turn_error",
            CodexAppServerFailureKind.TURN_START_FAILED,
            ErrorCode.CODEX_APP_SERVER_REQUEST_FAILED,
        ),
        (
            "terminal_failed",
            CodexAppServerFailureKind.TURN_FAILED,
            ErrorCode.CODEX_APP_SERVER_TURN_FAILED,
        ),
    ],
)
def test_app_server_protocol_failures_are_structured_and_never_fallback(
    tmp_path: Path,
    mode: str,
    expected_kind: CodexAppServerFailureKind,
    expected_code: ErrorCode,
) -> None:
    executor, marker = _executor(tmp_path, mode=mode)

    result = executor.execute(_request(tmp_path))

    assert result.status == DelegationJobStatus.FAILED.value
    assert result.failure is not None
    assert result.failure.kind == expected_kind.value
    assert result.failure.error_code == expected_code.value
    assert result.metadata["execution_interface"] == "app_server"
    assert result.metadata["execution_channel"] == "codex"
    assert "exec" not in _receipt(marker)["methods"]
    if mode == "unsupported":
        assert _receipt(marker)["client_responses"] == []


def test_app_server_timeout_is_bounded_and_structured(tmp_path: Path) -> None:
    executor, marker = _executor(
        tmp_path,
        mode="timeout",
        timeout_seconds=0.15,
    )

    result = executor.execute(_request(tmp_path))

    assert result.status == DelegationJobStatus.FAILED.value
    assert result.failure is not None
    assert result.failure.kind == CodexAppServerFailureKind.TIMEOUT.value
    assert result.failure.error_code == ErrorCode.DELEGATION_EXECUTOR_TIMEOUT.value
    assert result.failure.timed_out is True
    assert "exec" not in _receipt(marker)["methods"]


def test_app_server_cancellation_interrupts_then_closes_process(
    tmp_path: Path,
) -> None:
    executor, marker = _executor(tmp_path, mode="cancel")
    stop = False

    def on_output(_event: Any) -> None:
        nonlocal stop
        stop = True

    result = executor.execute(
        _request(tmp_path),
        on_output=on_output,
        should_stop=lambda: stop,
    )

    assert result.status == DelegationJobStatus.CANCELLED.value
    assert result.failure is not None
    assert result.failure.kind == CodexAppServerFailureKind.CANCELLED.value
    assert result.metadata["shutdown_status"] == (
        CodexAppServerShutdownStatus.CLEAN_EXIT.value
    )
    assert _receipt(marker)["methods"].count("turn/interrupt") == 1


def test_missing_binary_and_spawn_failure_are_distinguished(tmp_path: Path) -> None:
    missing = CodexAppServerExecutor(
        codex_bin=str(tmp_path / "missing-codex"),
        timeout_seconds=1,
    ).execute(_request(tmp_path))
    assert missing.failure is not None
    assert missing.failure.kind == CodexAppServerFailureKind.BINARY_NOT_FOUND.value
    assert missing.failure.error_code == ErrorCode.DELEGATION_EXECUTOR_NOT_FOUND.value

    executor, _marker = _executor(tmp_path)
    spawn_failure = executor.execute(
        CodexifyExecutorRequest(
            request_id="spawn-failure",
            delegation_id="spawn-failure",
            executor_id=ExecutorId.CODEX.value,
            repo_path=str(tmp_path / "missing-working-directory"),
            task_prompt="This will not start.",
        )
    )
    assert spawn_failure.failure is not None
    assert spawn_failure.failure.kind == CodexAppServerFailureKind.SPAWN_FAILED.value
    assert (
        spawn_failure.failure.error_code
        == ErrorCode.DELEGATION_EXECUTOR_SPAWN_FAILED.value
    )
