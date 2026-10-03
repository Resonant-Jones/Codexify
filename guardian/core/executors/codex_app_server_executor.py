"""Bounded one-thread, one-turn Codex App Server executor."""

from __future__ import annotations

import json
import logging
import os
import queue
import shlex
import shutil
import subprocess
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from guardian.core.config import get_settings
from guardian.core.executors.base import (
    CodeExecutor,
    CodexifyExecutorRequest,
    ExecutorFailure,
    ExecutorProgressEvent,
    ExecutorStreamEvent,
    ExecutorTerminalResult,
)
from guardian.protocol_tokens import (
    CodexAppServerFailureKind,
    CodexAppServerProtocolVersion,
    CodexAppServerShutdownStatus,
    CodexExecutionInterface,
    DelegationJobStatus,
    ErrorCode,
    ExecutionEvidenceStatus,
    ExecutorEventType,
    ExecutorId,
)

logger = logging.getLogger(__name__)

_POLL_SECONDS = 0.05
_TERMINATION_GRACE_SECONDS = 1.5
_INTERRUPT_GRACE_SECONDS = 1.0
_MAX_PROTOCOL_LINE_CHARS = 1024 * 1024
_MAX_PROTOCOL_EVENTS_CHARS = 256 * 1024
_MAX_STDERR_CHARS = 64 * 1024
_MAX_PROGRESS_EVENTS = 512
_STDOUT_QUEUE_SIZE = 128

_EOF = object()


class _ReadFailure:
    def __init__(self, message: str) -> None:
        self.message = message


class _AppServerFault(Exception):
    def __init__(
        self,
        *,
        kind: CodexAppServerFailureKind,
        error_code: ErrorCode,
        message: str,
        stage: str,
        details: dict[str, Any] | None = None,
        timed_out: bool = False,
        spawn_failed: bool = False,
    ) -> None:
        super().__init__(message)
        self.kind = kind
        self.error_code = error_code
        self.message = message
        self.stage = stage
        self.details = dict(details or {})
        self.timed_out = timed_out
        self.spawn_failed = spawn_failed


class _BoundedText:
    def __init__(self, limit: int) -> None:
        self.limit = limit
        self._parts: deque[str] = deque()
        self._length = 0
        self.truncated = False

    def append(self, value: str) -> None:
        if not value:
            return
        if len(value) >= self.limit:
            self._parts.clear()
            self._parts.append(value[-self.limit :])
            self._length = self.limit
            self.truncated = True
            return
        self._parts.append(value)
        self._length += len(value)
        while self._length > self.limit and self._parts:
            excess = self._length - self.limit
            first = self._parts.popleft()
            self._length -= len(first)
            if len(first) > excess:
                kept = first[excess:]
                self._parts.appendleft(kept)
                self._length += len(kept)
            self.truncated = True

    def text(self) -> str:
        return "".join(self._parts)


class _StdoutReader:
    """Read bounded JSONL lines without blocking cancellation polling."""

    def __init__(self, stream: Any) -> None:
        self._stream = stream
        self.items: queue.Queue[Any] = queue.Queue(maxsize=_STDOUT_QUEUE_SIZE)
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._read, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def _put(self, item: Any) -> bool:
        while not self._stop.is_set():
            try:
                self.items.put(item, timeout=0.1)
                return True
            except queue.Full:
                continue
        return False

    def _read(self) -> None:
        try:
            while not self._stop.is_set():
                line = self._stream.readline(_MAX_PROTOCOL_LINE_CHARS + 1)
                if not line:
                    self._put(_EOF)
                    return
                if len(line) > _MAX_PROTOCOL_LINE_CHARS:
                    self._put(
                        _ReadFailure(
                            "Codex App Server emitted a protocol line over the size limit"
                        )
                    )
                    return
                if not self._put(line):
                    return
        except Exception as exc:  # pragma: no cover - OS stream failure
            self._put(_ReadFailure(str(exc)))

    def close(self) -> None:
        self._stop.set()
        self._thread.join(timeout=_TERMINATION_GRACE_SECONDS)


@dataclass(slots=True)
class _RunState:
    request: CodexifyExecutorRequest
    executable: str
    command: list[str]
    timeout_seconds: float | None
    started_at: str = field(default_factory=lambda: _utc_now_iso())
    native_thread_id: str | None = None
    native_session_id: str | None = None
    native_turn_id: str | None = None
    provider_id: str | None = None
    configured_model_id: str | None = None
    actual_model_id: str | None = None
    turn_terminal: dict[str, Any] | None = None
    agent_messages: list[tuple[str | None, str]] = field(default_factory=list)
    assistant_text: _BoundedText = field(
        default_factory=lambda: _BoundedText(_MAX_PROTOCOL_EVENTS_CHARS)
    )
    stderr: _BoundedText = field(
        default_factory=lambda: _BoundedText(_MAX_STDERR_CHARS)
    )
    commands_run: list[str] = field(default_factory=list)
    files_changed: list[str] = field(default_factory=list)
    output_chunks: list[ExecutorProgressEvent] = field(default_factory=list)
    event_lines: list[str] = field(default_factory=list)
    event_chars: int = 0
    event_log_truncated: bool = False
    completed_item_ids: set[str] = field(default_factory=set)
    sequence: int = 0
    cancel_requested: bool = False
    process_exit_code: int | None = None
    shutdown_status: CodexAppServerShutdownStatus = (
        CodexAppServerShutdownStatus.NOT_STARTED
    )

    def record_event(self, payload: dict[str, Any]) -> None:
        line = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        if self.event_chars + len(line) + 1 > _MAX_PROTOCOL_EVENTS_CHARS:
            self.event_log_truncated = True
            return
        self.event_lines.append(line)
        self.event_chars += len(line) + 1

    @property
    def raw_transcript(self) -> str:
        return "\n".join(self.event_lines)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


def _command_prefix(spec: str) -> list[str]:
    command = shlex.split(spec.strip()) if spec and spec.strip() else []
    return command or ["codex"]


def _binary_exists(binary: str) -> bool:
    if not binary:
        return False
    path = Path(binary)
    if path.exists() and os.access(path, os.X_OK):
        return True
    return shutil.which(binary) is not None


def _dedupe_append(values: list[str], value: str) -> None:
    if value and value not in values:
        values.append(value)


class CodexAppServerExecutor(CodeExecutor):
    """Run one explicit Codex App Server thread and turn over local stdio."""

    def __init__(
        self,
        *,
        codex_bin: str | None = None,
        timeout_seconds: float | int | None = None,
    ) -> None:
        settings = get_settings()
        self._codex_bin = (
            _normalize_text(codex_bin or settings.CODEXIFY_CODEX_BIN) or "codex"
        )
        self._timeout_seconds = (
            float(timeout_seconds)
            if timeout_seconds is not None
            else float(settings.CODEXIFY_CODEX_TIMEOUT_SECONDS)
        )

    def execute(
        self,
        request: CodexifyExecutorRequest,
        *,
        on_output: Callable[[ExecutorStreamEvent], None] | None = None,
        should_stop: Callable[[], bool] | None = None,
    ) -> ExecutorTerminalResult:
        timeout_seconds = (
            float(request.timeout_seconds)
            if request.timeout_seconds is not None
            else self._timeout_seconds
        )
        try:
            command_prefix = _command_prefix(self._codex_bin)
        except ValueError as exc:
            command_prefix = [self._codex_bin]
            parse_fault = _AppServerFault(
                kind=CodexAppServerFailureKind.SPAWN_FAILED,
                error_code=ErrorCode.DELEGATION_EXECUTOR_SPAWN_FAILED,
                message=f"Invalid Codex executable command: {exc}",
                stage="spawn",
                spawn_failed=True,
            )
        else:
            parse_fault = None

        executable = command_prefix[0]
        command = [*command_prefix, "app-server", "--stdio"]
        state = _RunState(
            request=request,
            executable=executable,
            command=command,
            timeout_seconds=timeout_seconds,
        )

        if request.executor_id != ExecutorId.CODEX.value:
            parse_fault = _AppServerFault(
                kind=CodexAppServerFailureKind.EXECUTION_INTERFACE_UNSUPPORTED,
                error_code=ErrorCode.DELEGATION_EXECUTION_INTERFACE_UNSUPPORTED,
                message=(
                    "Codex App Server execution requires the codex executor channel"
                ),
                stage="selection",
            )
        if parse_fault is not None:
            return self._failure_result(state, parse_fault)

        if not _binary_exists(executable):
            return self._failure_result(
                state,
                _AppServerFault(
                    kind=CodexAppServerFailureKind.BINARY_NOT_FOUND,
                    error_code=ErrorCode.DELEGATION_EXECUTOR_NOT_FOUND,
                    message=f"Codex executable not found on PATH: {executable}",
                    stage="spawn",
                    details={"binary": executable},
                ),
            )

        process: subprocess.Popen[str] | None = None
        reader: _StdoutReader | None = None
        stderr_thread: threading.Thread | None = None
        fault: _AppServerFault | None = None
        final_text: str | None = None
        run_status = DelegationJobStatus.FAILED.value
        deadline = (
            time.monotonic() + timeout_seconds if timeout_seconds is not None else None
        )
        try:
            try:
                process = subprocess.Popen(
                    command,
                    cwd=request.repo_path or None,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
                )
            except Exception as exc:
                raise self._fault(
                    CodexAppServerFailureKind.SPAWN_FAILED,
                    ErrorCode.DELEGATION_EXECUTOR_SPAWN_FAILED,
                    str(exc) or "Could not start Codex App Server",
                    "spawn",
                    {"cwd": request.repo_path},
                    spawn_failed=True,
                ) from exc
            assert process.stdin is not None
            assert process.stdout is not None
            assert process.stderr is not None
            reader = _StdoutReader(process.stdout)
            reader.start()
            stderr_thread = threading.Thread(
                target=self._capture_stderr,
                args=(process.stderr, state.stderr),
                daemon=True,
            )
            stderr_thread.start()

            self._send_request(
                process,
                state,
                request_id=1,
                method="initialize",
                params={
                    "clientInfo": {
                        "name": "codexify_guardian",
                        "title": "Codexify Guardian",
                        "version": "0.1.0",
                    }
                },
            )
            self._wait_for_response(
                process,
                reader,
                state,
                request_id=1,
                stage="initialize",
                deadline=deadline,
                should_stop=should_stop,
                on_output=on_output,
            )
            self._send_notification(process, state, method="initialized", params={})

            thread_params: dict[str, Any] = {}
            if request.repo_path:
                thread_params["cwd"] = request.repo_path
            # This first bounded interface is deliberately read-only. A later
            # permission-mapping slice can expose broader workspace access.
            thread_params["sandbox"] = "read-only"
            self._send_request(
                process,
                state,
                request_id=2,
                method="thread/start",
                params=thread_params,
            )
            thread_result = self._wait_for_response(
                process,
                reader,
                state,
                request_id=2,
                stage="thread_start",
                deadline=deadline,
                should_stop=should_stop,
                on_output=on_output,
            )
            thread = thread_result.get("thread")
            if not isinstance(thread, dict) or not _normalize_text(thread.get("id")):
                raise self._fault(
                    CodexAppServerFailureKind.MALFORMED_PROTOCOL,
                    ErrorCode.CODEX_APP_SERVER_PROTOCOL_ERROR,
                    "Codex App Server thread/start response omitted thread.id",
                    "thread_start",
                )
            state.native_thread_id = _normalize_text(thread.get("id"))
            state.native_session_id = _optional_text(thread.get("sessionId"))
            state.provider_id = _optional_text(thread.get("modelProvider"))
            state.configured_model_id = _optional_text(thread.get("model"))
            state.record_event(
                {
                    "direction": "server",
                    "response": "thread/start",
                    "native_thread_id": state.native_thread_id,
                    "native_session_id": state.native_session_id,
                    "provider_id": state.provider_id,
                    "configured_model_id": state.configured_model_id,
                }
            )

            self._send_request(
                process,
                state,
                request_id=3,
                method="turn/start",
                params={
                    "threadId": state.native_thread_id,
                    "input": [{"type": "text", "text": request.task_prompt}],
                },
            )
            turn_result = self._wait_for_response(
                process,
                reader,
                state,
                request_id=3,
                stage="turn_start",
                deadline=deadline,
                should_stop=should_stop,
                on_output=on_output,
            )
            turn = turn_result.get("turn")
            if not isinstance(turn, dict) or not _normalize_text(turn.get("id")):
                raise self._fault(
                    CodexAppServerFailureKind.MALFORMED_PROTOCOL,
                    ErrorCode.CODEX_APP_SERVER_PROTOCOL_ERROR,
                    "Codex App Server turn/start response omitted turn.id",
                    "turn_start",
                )
            started_turn_id = _normalize_text(turn.get("id"))
            if state.native_turn_id and state.native_turn_id != started_turn_id:
                raise self._fault(
                    CodexAppServerFailureKind.MALFORMED_PROTOCOL,
                    ErrorCode.CODEX_APP_SERVER_PROTOCOL_ERROR,
                    "Codex App Server turn/start response did not match turn/started",
                    "turn_start",
                    {"started_turn_id": state.native_turn_id},
                )
            state.native_turn_id = started_turn_id
            state.record_event(
                {
                    "direction": "server",
                    "response": "turn/start",
                    "native_thread_id": state.native_thread_id,
                    "native_turn_id": state.native_turn_id,
                }
            )

            if state.turn_terminal is None:
                self._wait_for_turn(
                    process,
                    reader,
                    state,
                    deadline=deadline,
                    should_stop=should_stop,
                    on_output=on_output,
                )
            if state.cancel_requested and state.turn_terminal is None:
                raise self._fault(
                    CodexAppServerFailureKind.CANCELLED,
                    ErrorCode.DELEGATION_EXECUTOR_CANCELLED,
                    "Codex App Server turn was cancelled",
                    "turn",
                )

            terminal = state.turn_terminal or {}
            terminal_status = _normalize_text(terminal.get("status"))
            if state.cancel_requested or terminal_status == "interrupted":
                raise self._fault(
                    CodexAppServerFailureKind.CANCELLED,
                    ErrorCode.DELEGATION_EXECUTOR_CANCELLED,
                    "Codex App Server turn was cancelled",
                    "turn",
                )
            if terminal_status == "failed":
                error_payload = terminal.get("error")
                error_message = (
                    _normalize_text(error_payload.get("message"))
                    if isinstance(error_payload, dict)
                    else ""
                )
                raise self._fault(
                    CodexAppServerFailureKind.TURN_FAILED,
                    ErrorCode.CODEX_APP_SERVER_TURN_FAILED,
                    error_message or "Codex App Server turn failed",
                    "turn",
                    {"terminal_error": error_payload},
                )
            if terminal_status != "completed":
                raise self._fault(
                    CodexAppServerFailureKind.TURN_FAILED,
                    ErrorCode.CODEX_APP_SERVER_TURN_FAILED,
                    "Codex App Server returned an unsupported terminal turn status",
                    "turn",
                    {"terminal_status": terminal_status},
                )

            final_text = self._final_agent_text(state)
            if not final_text:
                raise self._fault(
                    CodexAppServerFailureKind.MALFORMED_PROTOCOL,
                    ErrorCode.CODEX_APP_SERVER_PROTOCOL_ERROR,
                    "Codex App Server completed the turn without a final agent message",
                    "turn",
                )
            run_status = DelegationJobStatus.COMPLETED.value
        except _AppServerFault as exc:
            fault = exc
            run_status = (
                DelegationJobStatus.CANCELLED.value
                if exc.kind == CodexAppServerFailureKind.CANCELLED
                else DelegationJobStatus.FAILED.value
            )
        except Exception as exc:  # pragma: no cover - defensive process boundary
            logger.exception("[codex-app-server] executor boundary failed")
            fault = self._fault(
                CodexAppServerFailureKind.MALFORMED_PROTOCOL,
                ErrorCode.CODEX_APP_SERVER_PROTOCOL_ERROR,
                f"Codex App Server execution failed: {exc}",
                "internal",
                {"exception_class": exc.__class__.__name__},
            )
            run_status = DelegationJobStatus.FAILED.value
        finally:
            state.process_exit_code, state.shutdown_status = self._shutdown(
                process,
                reader,
                stderr_thread,
                state,
            )

        if (
            fault is None
            and run_status == DelegationJobStatus.COMPLETED.value
            and (
                state.shutdown_status != CodexAppServerShutdownStatus.CLEAN_EXIT
                or state.process_exit_code != 0
            )
        ):
            fault = self._fault(
                CodexAppServerFailureKind.SHUTDOWN_FAILED,
                ErrorCode.CODEX_APP_SERVER_SHUTDOWN_FAILED,
                "Codex App Server did not exit cleanly after stdin was closed",
                "shutdown",
                {
                    "process_exit_code": state.process_exit_code,
                    "shutdown_status": state.shutdown_status.value,
                },
            )
            run_status = DelegationJobStatus.FAILED.value

        if fault is not None:
            return self._failure_result(state, fault, status=run_status)
        return self._success_result(state, final_text or "")

    @staticmethod
    def _capture_stderr(stream: Any, buffer: _BoundedText) -> None:
        try:
            while True:
                chunk = stream.read(4096)
                if not chunk:
                    return
                buffer.append(chunk)
        except Exception:  # pragma: no cover - OS stream failure
            return

    @staticmethod
    def _fault(
        kind: CodexAppServerFailureKind,
        error_code: ErrorCode,
        message: str,
        stage: str,
        details: dict[str, Any] | None = None,
        *,
        timed_out: bool = False,
        spawn_failed: bool = False,
    ) -> _AppServerFault:
        return _AppServerFault(
            kind=kind,
            error_code=error_code,
            message=message,
            stage=stage,
            details=details,
            timed_out=timed_out,
            spawn_failed=spawn_failed,
        )

    def _send_request(
        self,
        process: subprocess.Popen[str],
        state: _RunState,
        *,
        request_id: int,
        method: str,
        params: dict[str, Any],
    ) -> None:
        self._write_message(
            process,
            state,
            {"id": request_id, "method": method, "params": params},
            event={
                "direction": "client",
                "method": method,
                "request_id": request_id,
            },
        )

    def _send_notification(
        self,
        process: subprocess.Popen[str],
        state: _RunState,
        *,
        method: str,
        params: dict[str, Any],
    ) -> None:
        self._write_message(
            process,
            state,
            {"method": method, "params": params},
            event={"direction": "client", "method": method},
        )

    @staticmethod
    def _write_message(
        process: subprocess.Popen[str],
        state: _RunState,
        message: dict[str, Any],
        *,
        event: dict[str, Any],
    ) -> None:
        if process.stdin is None:
            raise CodexAppServerExecutor._fault(
                CodexAppServerFailureKind.MALFORMED_PROTOCOL,
                ErrorCode.CODEX_APP_SERVER_PROTOCOL_ERROR,
                "Codex App Server stdin is unavailable",
                "protocol_write",
            )
        try:
            process.stdin.write(
                json.dumps(message, ensure_ascii=False, separators=(",", ":")) + "\n"
            )
            process.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            raise CodexAppServerExecutor._fault(
                CodexAppServerFailureKind.PREMATURE_PROCESS_EXIT,
                ErrorCode.CODEX_APP_SERVER_PROTOCOL_ERROR,
                f"Codex App Server closed its input unexpectedly: {exc}",
                "protocol_write",
            ) from exc
        state.record_event(event)

    def _wait_for_response(
        self,
        process: subprocess.Popen[str],
        reader: _StdoutReader,
        state: _RunState,
        *,
        request_id: int,
        stage: str,
        deadline: float | None,
        should_stop: Callable[[], bool] | None,
        on_output: Callable[[ExecutorStreamEvent], None] | None,
    ) -> dict[str, Any]:
        while True:
            if self._should_stop(should_stop):
                raise self._fault(
                    CodexAppServerFailureKind.CANCELLED,
                    ErrorCode.DELEGATION_EXECUTOR_CANCELLED,
                    "Codex App Server execution cancelled",
                    stage,
                )
            self._check_deadline(deadline, stage)
            message = self._read_message(
                process, reader, state, deadline=deadline, stage=stage
            )
            if message is None:
                continue
            if "method" in message:
                if "id" in message:
                    raise self._unsupported_interaction(message)
                self._handle_notification(state, message, on_output)
                continue
            if "id" not in message or message.get("id") != request_id:
                raise self._fault(
                    CodexAppServerFailureKind.MALFORMED_PROTOCOL,
                    ErrorCode.CODEX_APP_SERVER_PROTOCOL_ERROR,
                    "Codex App Server returned an unexpected JSON-RPC response",
                    stage,
                    {"expected_request_id": request_id},
                )
            if "error" in message:
                raise self._rpc_error(stage, message.get("error"))
            result = message.get("result")
            if not isinstance(result, dict):
                raise self._fault(
                    CodexAppServerFailureKind.MALFORMED_PROTOCOL,
                    ErrorCode.CODEX_APP_SERVER_PROTOCOL_ERROR,
                    "Codex App Server JSON-RPC response omitted an object result",
                    stage,
                )
            return result

    def _wait_for_turn(
        self,
        process: subprocess.Popen[str],
        reader: _StdoutReader,
        state: _RunState,
        *,
        deadline: float | None,
        should_stop: Callable[[], bool] | None,
        on_output: Callable[[ExecutorStreamEvent], None] | None,
    ) -> None:
        interrupt_request_id: int | None = None
        interrupt_deadline: float | None = None
        while state.turn_terminal is None:
            if not state.cancel_requested and self._should_stop(should_stop):
                state.cancel_requested = True
                interrupt_request_id = 4
                interrupt_deadline = time.monotonic() + _INTERRUPT_GRACE_SECONDS
                try:
                    self._send_request(
                        process,
                        state,
                        request_id=interrupt_request_id,
                        method="turn/interrupt",
                        params={
                            "threadId": state.native_thread_id,
                            "turnId": state.native_turn_id,
                        },
                    )
                except _AppServerFault:
                    logger.info(
                        "[codex-app-server] turn interrupt could not be sent; closing the process"
                    )
                    break
            if state.cancel_requested:
                if (
                    interrupt_deadline is not None
                    and time.monotonic() >= interrupt_deadline
                ):
                    break
            else:
                self._check_deadline(deadline, "turn")

            message = self._read_message(
                process,
                reader,
                state,
                deadline=(interrupt_deadline if state.cancel_requested else deadline),
                stage="turn",
                allow_eof=state.cancel_requested,
            )
            if message is None:
                continue
            if "method" in message:
                if "id" in message:
                    raise self._unsupported_interaction(message)
                self._handle_notification(state, message, on_output)
                continue
            if (
                "id" in message
                and interrupt_request_id is not None
                and message.get("id") == interrupt_request_id
            ):
                state.record_event(
                    {
                        "direction": "server",
                        "response": "turn/interrupt",
                        "error": message.get("error"),
                    }
                )
                continue
            raise self._fault(
                CodexAppServerFailureKind.MALFORMED_PROTOCOL,
                ErrorCode.CODEX_APP_SERVER_PROTOCOL_ERROR,
                "Codex App Server returned an unexpected response while the turn was active",
                "turn",
            )

    def _read_message(
        self,
        process: subprocess.Popen[str],
        reader: _StdoutReader,
        state: _RunState,
        *,
        deadline: float | None,
        stage: str,
        allow_eof: bool = False,
    ) -> dict[str, Any] | None:
        timeout = _POLL_SECONDS
        if deadline is not None:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                if allow_eof:
                    return None
                self._check_deadline(deadline, stage)
            timeout = min(timeout, max(remaining, 0.001))
        try:
            item = reader.items.get(timeout=timeout)
        except queue.Empty:
            return None
        if item is _EOF:
            if allow_eof:
                return None
            raise self._fault(
                CodexAppServerFailureKind.PREMATURE_PROCESS_EXIT,
                ErrorCode.CODEX_APP_SERVER_PROTOCOL_ERROR,
                "Codex App Server closed stdout before the turn reached a terminal state",
                stage,
                {"process_exit_code": process.poll()},
            )
        if isinstance(item, _ReadFailure):
            raise self._fault(
                CodexAppServerFailureKind.MALFORMED_PROTOCOL,
                ErrorCode.CODEX_APP_SERVER_PROTOCOL_ERROR,
                item.message,
                stage,
            )
        if not isinstance(item, str):
            raise self._fault(
                CodexAppServerFailureKind.MALFORMED_PROTOCOL,
                ErrorCode.CODEX_APP_SERVER_PROTOCOL_ERROR,
                "Codex App Server emitted a non-text protocol line",
                stage,
            )
        try:
            message = json.loads(item)
        except json.JSONDecodeError as exc:
            raise self._fault(
                CodexAppServerFailureKind.MALFORMED_PROTOCOL,
                ErrorCode.CODEX_APP_SERVER_PROTOCOL_ERROR,
                "Codex App Server emitted malformed JSONL",
                stage,
                {"line_number": len(state.event_lines) + 1},
            ) from exc
        if not isinstance(message, dict):
            raise self._fault(
                CodexAppServerFailureKind.MALFORMED_PROTOCOL,
                ErrorCode.CODEX_APP_SERVER_PROTOCOL_ERROR,
                "Codex App Server emitted a non-object JSON-RPC message",
                stage,
            )
        return message

    def _handle_notification(
        self,
        state: _RunState,
        message: dict[str, Any],
        on_output: Callable[[ExecutorStreamEvent], None] | None,
    ) -> None:
        method = message.get("method")
        params = message.get("params")
        if not isinstance(method, str) or not method:
            raise self._fault(
                CodexAppServerFailureKind.MALFORMED_PROTOCOL,
                ErrorCode.CODEX_APP_SERVER_PROTOCOL_ERROR,
                "Codex App Server notification omitted method",
                "notification",
            )
        if params is None:
            params = {}
        if not isinstance(params, dict):
            raise self._fault(
                CodexAppServerFailureKind.MALFORMED_PROTOCOL,
                ErrorCode.CODEX_APP_SERVER_PROTOCOL_ERROR,
                "Codex App Server notification params were not an object",
                "notification",
                {"method": method},
            )

        event_turn = params.get("turn")
        event_turn_id = params.get("turnId")
        if isinstance(event_turn, dict):
            event_turn_id = event_turn.get("id") or event_turn_id
        if not self._matches_scope(state, params, event_turn_id):
            return

        if method == "turn/started":
            if isinstance(event_turn, dict):
                started_id = _optional_text(event_turn.get("id"))
                if started_id:
                    state.native_turn_id = started_id
            state.record_event(
                {
                    "direction": "server",
                    "method": method,
                    "native_thread_id": state.native_thread_id,
                    "native_turn_id": state.native_turn_id,
                }
            )
            return

        if method == "item/agentMessage/delta":
            delta = params.get("delta")
            if isinstance(delta, str) and delta:
                state.assistant_text.append(delta)
                self._emit_progress(state, delta, on_output)
            state.record_event(
                {
                    "direction": "server",
                    "method": method,
                    "native_thread_id": state.native_thread_id,
                    "native_turn_id": state.native_turn_id,
                    "item_id": params.get("itemId"),
                    "delta_chars": len(delta) if isinstance(delta, str) else 0,
                }
            )
            return

        if method == "item/completed":
            item = params.get("item")
            if not isinstance(item, dict):
                raise self._fault(
                    CodexAppServerFailureKind.MALFORMED_PROTOCOL,
                    ErrorCode.CODEX_APP_SERVER_PROTOCOL_ERROR,
                    "Codex App Server item/completed omitted item",
                    "turn",
                )
            self._capture_completed_item(state, item)
            state.record_event(
                {
                    "direction": "server",
                    "method": method,
                    "native_thread_id": state.native_thread_id,
                    "native_turn_id": state.native_turn_id,
                    "item_id": item.get("id"),
                    "item_type": item.get("type"),
                    "status": item.get("status"),
                }
            )
            return

        if method == "turn/completed":
            turn = params.get("turn")
            if not isinstance(turn, dict):
                raise self._fault(
                    CodexAppServerFailureKind.MALFORMED_PROTOCOL,
                    ErrorCode.CODEX_APP_SERVER_PROTOCOL_ERROR,
                    "Codex App Server turn/completed omitted turn",
                    "turn",
                )
            terminal_id = _optional_text(turn.get("id"))
            if (
                terminal_id
                and state.native_turn_id
                and terminal_id != state.native_turn_id
            ):
                return
            if terminal_id:
                state.native_turn_id = terminal_id
            items = turn.get("items")
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict):
                        self._capture_completed_item(state, item)
            state.turn_terminal = turn
            state.record_event(
                {
                    "direction": "server",
                    "method": method,
                    "native_thread_id": state.native_thread_id,
                    "native_turn_id": state.native_turn_id,
                    "status": turn.get("status"),
                }
            )
            return

        if method == "model/rerouted":
            target_model = _optional_text(params.get("toModel"))
            if target_model:
                state.actual_model_id = target_model
            state.record_event(
                {
                    "direction": "server",
                    "method": method,
                    "native_turn_id": state.native_turn_id,
                    "from_model": params.get("fromModel"),
                    "to_model": target_model,
                }
            )
            return

        state.record_event(
            {
                "direction": "server",
                "method": method,
                "native_thread_id": state.native_thread_id,
                "native_turn_id": state.native_turn_id,
            }
        )

    @staticmethod
    def _matches_scope(
        state: _RunState,
        params: dict[str, Any],
        event_turn_id: Any,
    ) -> bool:
        event_thread_id = params.get("threadId")
        if (
            event_thread_id is not None
            and state.native_thread_id is not None
            and str(event_thread_id) != state.native_thread_id
        ):
            return False
        if (
            event_turn_id is not None
            and state.native_turn_id is not None
            and str(event_turn_id) != state.native_turn_id
        ):
            return False
        return True

    @staticmethod
    def _capture_completed_item(
        state: _RunState,
        item: dict[str, Any],
    ) -> None:
        item_id = _optional_text(item.get("id"))
        if item_id and item_id in state.completed_item_ids:
            return
        if item_id:
            state.completed_item_ids.add(item_id)
        item_type = item.get("type")
        if item_type == "agentMessage":
            text = item.get("text")
            if isinstance(text, str) and text.strip():
                state.agent_messages.append(
                    (_optional_text(item.get("phase")), text.strip())
                )
            return
        if item_type == "commandExecution" and item.get("status") == "completed":
            command = item.get("command")
            if isinstance(command, list):
                command_text = shlex.join([str(part) for part in command])
            else:
                command_text = _normalize_text(command)
            _dedupe_append(state.commands_run, command_text)
            return
        if item_type == "fileChange" and item.get("status") == "completed":
            changes = item.get("changes")
            if isinstance(changes, list):
                for change in changes:
                    if isinstance(change, dict):
                        _dedupe_append(
                            state.files_changed,
                            _normalize_text(change.get("path")),
                        )

    def _emit_progress(
        self,
        state: _RunState,
        text: str,
        on_output: Callable[[ExecutorStreamEvent], None] | None,
    ) -> None:
        chunk = ExecutorProgressEvent(
            stream="stdout",
            text=text,
            sequence=state.sequence,
            event_type=ExecutorEventType.PROGRESS.value,
            request_id=state.request.request_id,
            thread_id=state.request.thread_id,
            source_message_id=state.request.source_message_id,
            project_id=state.request.project_id,
            executor_id=state.request.executor_id,
            title=state.request.title,
            tags=list(state.request.tags),
            metadata={
                "execution_channel": ExecutorId.CODEX.value,
                "execution_interface": CodexExecutionInterface.APP_SERVER.value,
                "native_codex_thread_id": state.native_thread_id,
                "native_codex_turn_id": state.native_turn_id,
            },
        )
        state.sequence += 1
        if len(state.output_chunks) < _MAX_PROGRESS_EVENTS:
            state.output_chunks.append(chunk)
        if on_output is not None:
            try:
                on_output(chunk)
            except Exception:
                logger.exception("[codex-app-server] output callback failed")

    def _final_agent_text(self, state: _RunState) -> str:
        final_answers = [
            text for phase, text in state.agent_messages if phase == "final_answer"
        ]
        if final_answers:
            return final_answers[-1].strip()
        if state.agent_messages:
            return state.agent_messages[-1][1].strip()
        return state.assistant_text.text().strip()

    def _unsupported_interaction(self, message: dict[str, Any]) -> _AppServerFault:
        return self._fault(
            CodexAppServerFailureKind.UNSUPPORTED_INTERACTION,
            ErrorCode.CODEX_APP_SERVER_UNSUPPORTED_INTERACTION,
            "Codex App Server requested an unsupported client interaction",
            "server_request",
            {"method": message.get("method")},
        )

    def _rpc_error(self, stage: str, error: Any) -> _AppServerFault:
        error_payload = error if isinstance(error, dict) else {}
        message = _normalize_text(error_payload.get("message")) or (
            "Codex App Server rejected a JSON-RPC request"
        )
        if stage == "initialize":
            return self._fault(
                CodexAppServerFailureKind.INITIALIZATION_FAILED,
                ErrorCode.CODEX_APP_SERVER_PROTOCOL_ERROR,
                message,
                stage,
                {"json_rpc_error": error_payload},
            )
        kind = (
            CodexAppServerFailureKind.THREAD_START_FAILED
            if stage == "thread_start"
            else CodexAppServerFailureKind.TURN_START_FAILED
            if stage == "turn_start"
            else CodexAppServerFailureKind.TURN_FAILED
        )
        code = (
            ErrorCode.CODEX_APP_SERVER_TURN_FAILED
            if stage == "turn"
            else ErrorCode.CODEX_APP_SERVER_REQUEST_FAILED
        )
        return self._fault(
            kind,
            code,
            message,
            stage,
            {"json_rpc_error": error_payload},
        )

    @staticmethod
    def _should_stop(should_stop: Callable[[], bool] | None) -> bool:
        if should_stop is None:
            return False
        try:
            return bool(should_stop())
        except Exception:
            logger.exception("[codex-app-server] cancellation check failed")
            return False

    def _check_deadline(self, deadline: float | None, stage: str) -> None:
        if deadline is not None and time.monotonic() >= deadline:
            raise self._fault(
                CodexAppServerFailureKind.TIMEOUT,
                ErrorCode.DELEGATION_EXECUTOR_TIMEOUT,
                "Codex App Server execution timed out",
                stage,
                timed_out=True,
            )

    def _shutdown(
        self,
        process: subprocess.Popen[str] | None,
        reader: _StdoutReader | None,
        stderr_thread: threading.Thread | None,
        state: _RunState,
    ) -> tuple[int | None, CodexAppServerShutdownStatus]:
        if process is None:
            if reader is not None:
                reader.close()
            return None, CodexAppServerShutdownStatus.NOT_STARTED

        was_exited = process.poll() is not None
        if process.stdin is not None:
            try:
                process.stdin.close()
            except (BrokenPipeError, OSError):
                pass

        shutdown_status: CodexAppServerShutdownStatus
        try:
            process.wait(timeout=_TERMINATION_GRACE_SECONDS)
            shutdown_status = (
                CodexAppServerShutdownStatus.EXITED_BEFORE_CLOSE
                if was_exited and state.turn_terminal is None
                else CodexAppServerShutdownStatus.CLEAN_EXIT
            )
        except subprocess.TimeoutExpired:
            try:
                process.terminate()
                process.wait(timeout=_TERMINATION_GRACE_SECONDS)
                shutdown_status = CodexAppServerShutdownStatus.TERMINATED
            except subprocess.TimeoutExpired:
                try:
                    process.kill()
                    process.wait(timeout=_TERMINATION_GRACE_SECONDS)
                except Exception:
                    pass
                shutdown_status = CodexAppServerShutdownStatus.KILLED
            except Exception:
                shutdown_status = CodexAppServerShutdownStatus.KILLED
                try:
                    process.kill()
                    process.wait(timeout=_TERMINATION_GRACE_SECONDS)
                except Exception:
                    pass

        if reader is not None:
            reader.close()
        if stderr_thread is not None:
            stderr_thread.join(timeout=_TERMINATION_GRACE_SECONDS)
        return process.poll(), shutdown_status

    def _failure_result(
        self,
        state: _RunState,
        fault: _AppServerFault,
        *,
        status: str = DelegationJobStatus.FAILED.value,
    ) -> ExecutorTerminalResult:
        request = state.request
        message = fault.message
        failure = ExecutorFailure(
            error_code=fault.error_code.value,
            failure_class=f"CodexAppServer{fault.kind.value.title().replace('_', '')}",
            message=message,
            request_id=request.request_id,
            thread_id=request.thread_id,
            source_message_id=request.source_message_id,
            project_id=request.project_id,
            executor_id=request.executor_id,
            kind=fault.kind.value,
            binary=state.executable,
            command=list(state.command),
            returncode=state.process_exit_code,
            timeout_seconds=state.timeout_seconds,
            timed_out=fault.timed_out,
            spawn_failed=fault.spawn_failed,
            stdout=state.assistant_text.text(),
            stderr=state.stderr.text(),
            details={
                "stage": fault.stage,
                "cwd": request.repo_path,
                "process_exit_code": state.process_exit_code,
                "shutdown_status": state.shutdown_status.value,
                "event_log_truncated": state.event_log_truncated,
                **fault.details,
            },
            provenance=self._lineage(state),
        )
        return self._result(
            state,
            status=status,
            summary=message,
            final_text=state.assistant_text.text().strip() or None,
            failure=failure,
            error_message=message,
        )

    def _success_result(
        self,
        state: _RunState,
        final_text: str,
    ) -> ExecutorTerminalResult:
        return self._result(
            state,
            status=DelegationJobStatus.COMPLETED.value,
            summary=final_text,
            final_text=final_text,
        )

    def _result(
        self,
        state: _RunState,
        *,
        status: str,
        summary: str,
        final_text: str | None,
        failure: ExecutorFailure | None = None,
        error_message: str | None = None,
    ) -> ExecutorTerminalResult:
        request = state.request
        provider_status = (
            ExecutionEvidenceStatus.OBSERVED.value
            if state.provider_id
            else ExecutionEvidenceStatus.UNAVAILABLE.value
        )
        if state.actual_model_id:
            model_status = ExecutionEvidenceStatus.OBSERVED.value
        elif state.configured_model_id:
            model_status = ExecutionEvidenceStatus.CONFIGURED_ONLY.value
        else:
            model_status = ExecutionEvidenceStatus.UNAVAILABLE.value
        inference_route = {
            "provider_id": state.provider_id,
            "evidence_status": provider_status,
            "evidence_source": "thread/start response",
        }
        model_identity = {
            "actual_model_id": state.actual_model_id,
            "configured_model_id": state.configured_model_id,
            "evidence_status": model_status,
            "evidence_source": (
                "model/rerouted notification"
                if state.actual_model_id
                else "thread/start response"
            ),
            "unavailable_reason": (
                None
                if state.actual_model_id
                else "App Server did not emit per-turn model identity evidence"
            ),
        }
        funding_route = {
            "route_id": None,
            "evidence_status": ExecutionEvidenceStatus.UNKNOWN.value,
            "reason": (
                "The one-turn App Server protocol exchange does not establish "
                "who funds or owns the inference entitlement."
            ),
        }
        metadata = {
            **request.metadata,
            **self._lineage(state),
            "execution_channel": ExecutorId.CODEX.value,
            "execution_interface": CodexExecutionInterface.APP_SERVER.value,
            "app_server_protocol_version": (CodexAppServerProtocolVersion.V2.value),
            "inference_route": inference_route,
            "model_identity": model_identity,
            "funding_route": funding_route,
            "native_codex_thread_id": state.native_thread_id,
            "native_codex_session_id": state.native_session_id,
            "native_codex_turn_id": state.native_turn_id,
            "configured_model_id": state.configured_model_id,
            "actual_model_id": state.actual_model_id,
            "process_exit_code": state.process_exit_code,
            "shutdown_status": state.shutdown_status.value,
            "event_log_truncated": state.event_log_truncated,
            "event_count": len(state.event_lines),
        }
        raw_transcript = state.raw_transcript
        result = {
            **metadata,
            "title": request.title,
            "status": status,
            "summary": summary,
            "final_text": final_text,
            "stdout": final_text or state.assistant_text.text(),
            "stderr": state.stderr.text(),
            "raw_transcript": raw_transcript,
            "files_changed": list(state.files_changed),
            "commands_run": list(state.commands_run),
            "failure": failure.to_dict() if failure is not None else None,
            "error_message": error_message,
        }
        return ExecutorTerminalResult(
            request_id=request.request_id,
            delegation_id=request.delegation_id,
            task_id=request.task_id,
            thread_id=request.thread_id,
            source_message_id=request.source_message_id,
            project_id=request.project_id,
            executor_id=request.executor_id,
            title=request.title,
            status=status,
            summary=summary,
            final_text=final_text,
            stdout=final_text or state.assistant_text.text(),
            stderr=state.stderr.text(),
            raw_transcript=raw_transcript,
            tags=list(request.tags),
            files_changed=list(state.files_changed),
            commands_run=list(state.commands_run),
            output_chunks=list(state.output_chunks),
            result=result,
            metadata=metadata,
            failure=failure,
            error_message=error_message,
            created_at=state.started_at,
            completed_at=_utc_now_iso(),
        )

    @staticmethod
    def _lineage(state: _RunState) -> dict[str, Any]:
        request = state.request
        return {
            "request_id": request.request_id,
            "delegation_id": request.delegation_id,
            "task_id": request.task_id,
            "thread_id": request.thread_id,
            "source_message_id": request.source_message_id,
            "project_id": request.project_id,
            "executor_id": request.executor_id,
            "native_codex_thread_id": state.native_thread_id,
            "native_codex_session_id": state.native_session_id,
            "native_codex_turn_id": state.native_turn_id,
        }


def _optional_text(value: Any) -> str | None:
    text = _normalize_text(value)
    return text or None


__all__ = ["CodexAppServerExecutor"]
