"""Real Codex CLI executor binding for delegation tasks."""

from __future__ import annotations

import json
import logging
import os
import shlex
import shutil
import subprocess
import threading
import time
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
    DELEGATION_SUMMARY_OUTCOME_TYPE,
    DelegationJobStatus,
    ErrorCode,
    ExecutorEventType,
)

logger = logging.getLogger(__name__)

_PROCESS_POLL_SECONDS = 0.1
_TERMINATION_GRACE_SECONDS = 5.0


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_text_list(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, (list, tuple, set)):
        items = raw
    elif isinstance(raw, str):
        items = raw.split(",") if "," in raw else [raw]
    else:
        items = [raw]
    result: list[str] = []
    for item in items:
        text = _normalize_text(item)
        if text and text not in result:
            result.append(text)
    return result


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


def _split_structured_lines(text: str) -> dict[str, list[str] | str | None]:
    stripped = text.strip()
    parsed: dict[str, list[str] | str | None] = {
        "title": None,
        "summary": None,
        "files_changed": [],
        "commands_run": [],
        "key_changes": [],
        "unresolved_questions": [],
        "tags": [],
        "outcome_type": DELEGATION_SUMMARY_OUTCOME_TYPE,
    }
    if not stripped:
        return parsed

    try:
        decoded = json.loads(stripped)
    except Exception:
        decoded = None

    if isinstance(decoded, dict):
        parsed["title"] = (
            _normalize_text(decoded.get("title") or decoded.get("name")) or None
        )
        parsed["summary"] = (
            _normalize_text(
                decoded.get("summary")
                or decoded.get("final_text")
                or decoded.get("text")
            )
            or None
        )
        parsed["files_changed"] = _normalize_text_list(
            decoded.get("files_changed") or decoded.get("filesChanged")
        )
        parsed["commands_run"] = _normalize_text_list(
            decoded.get("commands_run") or decoded.get("commandsRun")
        )
        parsed["key_changes"] = _normalize_text_list(
            decoded.get("key_changes") or decoded.get("keyChanges")
        )
        parsed["unresolved_questions"] = _normalize_text_list(
            decoded.get("unresolved_questions")
            or decoded.get("unresolvedQuestions")
        )
        parsed["tags"] = _normalize_text_list(decoded.get("tags"))
        parsed["outcome_type"] = (
            _normalize_text(
                decoded.get("outcome_type")
                or decoded.get("outcomeType")
                or DELEGATION_SUMMARY_OUTCOME_TYPE
            )
            or DELEGATION_SUMMARY_OUTCOME_TYPE
        )
        return parsed

    section_map = {
        "title": "title",
        "summary": "summary",
        "files changed": "files_changed",
        "files_changed": "files_changed",
        "commands run": "commands_run",
        "commands_run": "commands_run",
        "key changes": "key_changes",
        "key_changes": "key_changes",
        "unresolved questions": "unresolved_questions",
        "unresolved_questions": "unresolved_questions",
        "tags": "tags",
        "outcome type": "outcome_type",
        "outcome_type": "outcome_type",
    }
    sections: dict[str, list[str]] = {
        "files_changed": [],
        "commands_run": [],
        "key_changes": [],
        "unresolved_questions": [],
        "tags": [],
    }
    current: str | None = None
    summary_lines: list[str] = []

    for raw_line in stripped.splitlines():
        line = raw_line.rstrip()
        normalized = line.strip().lower()
        header = None
        if ":" in normalized:
            candidate = normalized.split(":", 1)[0].strip()
            header = section_map.get(candidate)
        if header:
            current = header
            remainder = line.split(":", 1)[1].strip() if ":" in line else ""
            if remainder:
                if header == "title":
                    parsed["title"] = _normalize_text(remainder) or None
                elif header == "summary":
                    summary_lines.append(remainder)
                elif header == "outcome_type":
                    parsed["outcome_type"] = (
                        _normalize_text(remainder)
                        or DELEGATION_SUMMARY_OUTCOME_TYPE
                    )
                else:
                    sections[header].append(remainder)
            continue

        if current == "summary":
            summary_lines.append(line)
        elif current in sections:
            sections[current].append(line)

    def _flatten_section(values: list[str]) -> list[str]:
        items: list[str] = []
        for line in values:
            candidate = line.strip()
            if not candidate:
                continue
            candidate = candidate.lstrip("-*• ").strip()
            if not candidate:
                continue
            if "," in candidate and "\n" not in candidate:
                candidates = [part.strip() for part in candidate.split(",")]
            else:
                candidates = [candidate]
            for item in candidates:
                normalized_item = _normalize_text(item)
                if not normalized_item:
                    continue
                if normalized_item.lower() in {"none", "n/a", "na"}:
                    continue
                if normalized_item not in items:
                    items.append(normalized_item)
        return items

    parsed["files_changed"] = _flatten_section(sections["files_changed"])
    parsed["commands_run"] = _flatten_section(sections["commands_run"])
    parsed["key_changes"] = _flatten_section(sections["key_changes"])
    parsed["unresolved_questions"] = _flatten_section(
        sections["unresolved_questions"]
    )
    parsed["tags"] = _flatten_section(sections["tags"])
    if summary_lines:
        parsed["summary"] = (
            "\n".join(line for line in summary_lines if line).strip() or None
        )
    if parsed["summary"] is None:
        parsed["summary"] = stripped
    if parsed["title"] is None:
        parsed["title"] = None
    return parsed


class CodexExecutor(CodeExecutor):
    """Execute the configured Codex CLI and stream output incrementally."""

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
        command_prefix = _command_prefix(self._codex_bin)
        executable = command_prefix[0]
        command = [*command_prefix, "exec", request.task_prompt]
        base_metadata = {
            "request_id": request.request_id,
            "delegation_id": request.delegation_id,
            "task_id": request.task_id,
            "thread_id": request.thread_id,
            "source_message_id": request.source_message_id,
            "project_id": request.project_id,
            "executor_id": request.executor_id,
            "title": request.title,
            "tags": list(request.tags),
            "binary": executable,
            "command": command,
            "cwd": request.repo_path,
            "timeout_seconds": timeout_seconds,
            "executor": request.executor,
            "canonical_task_prompt": request.canonical_task_prompt,
        }

        if not _binary_exists(executable):
            failure = ExecutorFailure(
                error_code=ErrorCode.DELEGATION_EXECUTOR_NOT_FOUND.value,
                failure_class="FileNotFoundError",
                message=f"Codex binary not found: {executable}",
                request_id=request.request_id,
                thread_id=request.thread_id,
                source_message_id=request.source_message_id,
                project_id=request.project_id,
                executor_id=request.executor_id,
                kind="missing_binary",
                binary=executable,
                command=command,
                timeout_seconds=timeout_seconds,
                stdout="",
                stderr="",
                details={"cwd": request.repo_path},
                provenance={
                    "request_id": request.request_id,
                    "delegation_id": request.delegation_id,
                    "task_id": request.task_id,
                    "thread_id": request.thread_id,
                    "source_message_id": request.source_message_id,
                    "project_id": request.project_id,
                    "executor_id": request.executor_id,
                    "kind": "missing_binary",
                },
            )
            return ExecutorTerminalResult(
                request_id=request.request_id,
                delegation_id=request.delegation_id,
                task_id=request.task_id,
                thread_id=request.thread_id,
                source_message_id=request.source_message_id,
                project_id=request.project_id,
                executor_id=request.executor_id,
                title=request.title,
                status=DelegationJobStatus.FAILED.value,
                summary=failure.message,
                final_text="",
                tags=list(request.tags),
                result={
                    **base_metadata,
                    "files_changed": [],
                    "commands_run": [],
                    "raw_transcript": "",
                    "parsed_output": {},
                    "failure": failure.to_dict(),
                    "timed_out": False,
                    "cancelled": False,
                },
                metadata={**base_metadata, "missing_binary": True},
                failure=failure,
                error_message=failure.message,
            )

        stdout_chunks: list[str] = []
        stderr_chunks: list[str] = []
        transcript_chunks: list[str] = []
        stream_events: list[ExecutorProgressEvent] = []
        sequence = 0
        lock = threading.Lock()

        proc: subprocess.Popen[str] | None = None
        try:
            proc = subprocess.Popen(
                command,
                cwd=request.repo_path or None,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                text=True,
                bufsize=1,
            )
        except Exception as exc:
            failure = ExecutorFailure(
                error_code=ErrorCode.DELEGATION_EXECUTOR_SPAWN_FAILED.value,
                failure_class=exc.__class__.__name__,
                message=str(exc),
                request_id=request.request_id,
                thread_id=request.thread_id,
                source_message_id=request.source_message_id,
                project_id=request.project_id,
                executor_id=request.executor_id,
                kind="spawn_failed",
                binary=executable,
                command=command,
                timeout_seconds=timeout_seconds,
                spawn_failed=True,
                stdout="",
                stderr="",
                details={"cwd": request.repo_path},
                provenance={
                    "request_id": request.request_id,
                    "delegation_id": request.delegation_id,
                    "task_id": request.task_id,
                    "thread_id": request.thread_id,
                    "source_message_id": request.source_message_id,
                    "project_id": request.project_id,
                    "executor_id": request.executor_id,
                    "kind": "spawn_failed",
                },
            )
            return ExecutorTerminalResult(
                request_id=request.request_id,
                delegation_id=request.delegation_id,
                task_id=request.task_id,
                thread_id=request.thread_id,
                source_message_id=request.source_message_id,
                project_id=request.project_id,
                executor_id=request.executor_id,
                title=request.title,
                status=DelegationJobStatus.FAILED.value,
                summary=failure.message,
                final_text="",
                tags=list(request.tags),
                result={
                    **base_metadata,
                    "files_changed": [],
                    "commands_run": [],
                    "raw_transcript": "",
                    "parsed_output": {},
                    "failure": failure.to_dict(),
                    "timed_out": False,
                    "cancelled": False,
                },
                metadata={**base_metadata, "spawn_failed": True},
                failure=failure,
                error_message=failure.message,
            )

        assert proc.stdout is not None
        assert proc.stderr is not None

        def _record_chunk(stream: str, raw_line: str) -> None:
            nonlocal sequence
            text = raw_line.rstrip("\r\n")
            if not text:
                return
            with lock:
                chunk = ExecutorProgressEvent(
                    stream=stream,
                    text=text,
                    sequence=sequence,
                    event_type=ExecutorEventType.PROGRESS.value,
                    request_id=request.request_id,
                    thread_id=request.thread_id,
                    source_message_id=request.source_message_id,
                    project_id=request.project_id,
                    executor_id=request.executor_id,
                    title=request.title,
                    tags=list(request.tags),
                    metadata={
                        "stream": stream,
                        "cwd": request.repo_path,
                        "binary": executable,
                        "request_id": request.request_id,
                        "delegation_id": request.delegation_id,
                        "task_id": request.task_id,
                        "executor_id": request.executor_id,
                    },
                )
                sequence += 1
                stream_events.append(chunk)
                if stream == "stdout":
                    stdout_chunks.append(raw_line)
                else:
                    stderr_chunks.append(raw_line)
                transcript_chunks.append(f"[{stream}] {raw_line}")
            if on_output is not None:
                try:
                    on_output(chunk)
                except Exception:
                    logger.exception("[codex-executor] output callback failed")

        def _read_stream(stream: Any, stream_name: str) -> None:
            try:
                while True:
                    raw_line = stream.readline()
                    if raw_line == "":
                        break
                    _record_chunk(stream_name, raw_line)
            finally:
                try:
                    stream.close()
                except Exception:
                    pass

        stdout_thread = threading.Thread(
            target=_read_stream,
            args=(proc.stdout, "stdout"),
            daemon=True,
        )
        stderr_thread = threading.Thread(
            target=_read_stream,
            args=(proc.stderr, "stderr"),
            daemon=True,
        )
        stdout_thread.start()
        stderr_thread.start()

        cancelled = False
        timed_out = False
        returncode: int | None = None
        deadline = (
            time.monotonic() + timeout_seconds
            if timeout_seconds is not None
            else None
        )

        try:
            while True:
                if should_stop is not None and should_stop():
                    cancelled = True
                    self._terminate_process(proc)
                    break
                try:
                    returncode = proc.wait(timeout=_PROCESS_POLL_SECONDS)
                    break
                except subprocess.TimeoutExpired:
                    if deadline is not None and time.monotonic() >= deadline:
                        timed_out = True
                        self._terminate_process(proc)
                        break

            if returncode is None:
                try:
                    returncode = proc.wait(timeout=_TERMINATION_GRACE_SECONDS)
                except subprocess.TimeoutExpired:
                    timed_out = True
                    self._kill_process(proc)
                    returncode = proc.poll()

            stdout_thread.join(timeout=_TERMINATION_GRACE_SECONDS)
            stderr_thread.join(timeout=_TERMINATION_GRACE_SECONDS)
        except Exception as exc:
            self._kill_process(proc)
            stdout_thread.join(timeout=_TERMINATION_GRACE_SECONDS)
            stderr_thread.join(timeout=_TERMINATION_GRACE_SECONDS)
            failure = ExecutorFailure(
                error_code=ErrorCode.DELEGATION_EXECUTOR_SPAWN_FAILED.value,
                failure_class=exc.__class__.__name__,
                message=str(exc),
                request_id=request.request_id,
                thread_id=request.thread_id,
                source_message_id=request.source_message_id,
                project_id=request.project_id,
                executor_id=request.executor_id,
                kind="spawn_failed",
                binary=executable,
                command=command,
                timeout_seconds=timeout_seconds,
                spawn_failed=True,
                stdout="".join(stdout_chunks),
                stderr="".join(stderr_chunks),
                details={"cwd": request.repo_path},
                provenance={
                    "request_id": request.request_id,
                    "delegation_id": request.delegation_id,
                    "task_id": request.task_id,
                    "thread_id": request.thread_id,
                    "source_message_id": request.source_message_id,
                    "project_id": request.project_id,
                    "executor_id": request.executor_id,
                    "kind": "spawn_failed",
                },
            )
            return ExecutorTerminalResult(
                delegation_id=request.delegation_id,
                task_id=request.task_id,
                status=DelegationJobStatus.FAILED.value,
                summary=failure.message,
                final_text="".join(stdout_chunks).strip(),
                stdout="".join(stdout_chunks),
                stderr="".join(stderr_chunks),
                raw_transcript="".join(transcript_chunks),
                result={
                    **base_metadata,
                    "files_changed": [],
                    "commands_run": [],
                    "raw_transcript": "".join(transcript_chunks),
                    "parsed_output": {},
                    "failure": failure.to_dict(),
                    "timed_out": False,
                    "cancelled": False,
                },
                metadata={**base_metadata, "spawn_failed": True},
                failure=failure,
                error_message=failure.message,
            )

        stdout_text = "".join(stdout_chunks)
        stderr_text = "".join(stderr_chunks)
        raw_transcript = "".join(transcript_chunks)
        final_text = (
            _normalize_text(stdout_text)
            or _normalize_text(stderr_text)
            or _normalize_text(raw_transcript)
        )
        parsed = _split_structured_lines(final_text or raw_transcript)
        files_changed = _normalize_text_list(parsed.get("files_changed"))
        commands_run = _normalize_text_list(parsed.get("commands_run"))
        signal = (
            abs(returncode)
            if isinstance(returncode, int) and returncode < 0
            else None
        )

        failure: ExecutorFailure | None = None
        status = DelegationJobStatus.COMPLETED.value
        error_message: str | None = None
        if cancelled:
            status = DelegationJobStatus.CANCELLED.value
            error_message = "codex execution cancelled"
        elif timed_out:
            status = DelegationJobStatus.FAILED.value
            error_message = (
                f"Codex execution timed out after {timeout_seconds}s"
            )
            failure = ExecutorFailure(
                error_code=ErrorCode.DELEGATION_EXECUTOR_TIMEOUT.value,
                failure_class="TimeoutExpired",
                message=error_message,
                request_id=request.request_id,
                thread_id=request.thread_id,
                source_message_id=request.source_message_id,
                project_id=request.project_id,
                executor_id=request.executor_id,
                kind="timeout",
                binary=executable,
                command=command,
                returncode=returncode,
                signal=signal,
                timeout_seconds=timeout_seconds,
                timed_out=True,
                stdout=stdout_text,
                stderr=stderr_text,
                details={"cwd": request.repo_path},
                provenance={
                    "request_id": request.request_id,
                    "delegation_id": request.delegation_id,
                    "task_id": request.task_id,
                    "thread_id": request.thread_id,
                    "source_message_id": request.source_message_id,
                    "project_id": request.project_id,
                    "executor_id": request.executor_id,
                    "kind": "timeout",
                },
            )
        elif returncode not in (None, 0):
            status = DelegationJobStatus.FAILED.value
            error_message = f"Codex exited with code {returncode}"
            failure = ExecutorFailure(
                error_code=ErrorCode.DELEGATION_EXECUTOR_NONZERO_EXIT.value,
                failure_class="NonZeroExit",
                message=error_message,
                request_id=request.request_id,
                thread_id=request.thread_id,
                source_message_id=request.source_message_id,
                project_id=request.project_id,
                executor_id=request.executor_id,
                kind="nonzero_exit",
                binary=executable,
                command=command,
                returncode=returncode,
                signal=signal,
                timeout_seconds=timeout_seconds,
                stdout=stdout_text,
                stderr=stderr_text,
                details={"cwd": request.repo_path},
                provenance={
                    "request_id": request.request_id,
                    "delegation_id": request.delegation_id,
                    "task_id": request.task_id,
                    "thread_id": request.thread_id,
                    "source_message_id": request.source_message_id,
                    "project_id": request.project_id,
                    "executor_id": request.executor_id,
                    "kind": "nonzero_exit",
                },
            )

        result_payload = {
            **base_metadata,
            "returncode": returncode,
            "signal": signal,
            "timed_out": timed_out,
            "cancelled": cancelled,
            "files_changed": files_changed,
            "commands_run": commands_run,
            "final_text": final_text,
            "stdout": stdout_text,
            "stderr": stderr_text,
            "raw_transcript": raw_transcript,
            "parsed_output": parsed,
            "output_chunks": [chunk.to_dict() for chunk in stream_events],
            "failure": failure.to_dict() if failure is not None else None,
        }
        metadata = {
            **base_metadata,
            "returncode": returncode,
            "signal": signal,
            "timed_out": timed_out,
            "cancelled": cancelled,
            "stdout_line_count": len(stdout_chunks),
            "stderr_line_count": len(stderr_chunks),
            "raw_transcript_length": len(raw_transcript),
        }
        if failure is not None:
            metadata["failure"] = failure.to_dict()

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
            summary=final_text or error_message,
            final_text=final_text,
            stdout=stdout_text,
            stderr=stderr_text,
            raw_transcript=raw_transcript,
            tags=list(request.tags),
            files_changed=files_changed,
            commands_run=commands_run,
            output_chunks=stream_events,
            result=result_payload,
            metadata=metadata,
            failure=failure,
            error_message=error_message,
            created_at=_utc_now_iso(),
            completed_at=_utc_now_iso(),
        )

    @staticmethod
    def _terminate_process(proc: subprocess.Popen[str]) -> None:
        try:
            proc.terminate()
        except Exception:
            pass

    @staticmethod
    def _kill_process(proc: subprocess.Popen[str]) -> None:
        try:
            proc.kill()
        except Exception:
            pass


__all__ = ["CodexExecutor"]
