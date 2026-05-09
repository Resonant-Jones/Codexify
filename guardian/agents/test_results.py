"""Normalized test-result contracts for coding-worker convergence."""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from guardian.agents.retry_policy import build_fail_signature

NormalizedTestStatus = Literal["passed", "failed", "error", "not_run"]

_PREVIEW_LIMIT = 480
_SIGNATURE_LINE_LIMIT = 20

_MEMORY_ADDRESS_RE = re.compile(r"0x[0-9a-fA-F]+")
_TIMESTAMP_RE = re.compile(
    r"\b\d{4}-\d{2}-\d{2}[T ]"
    r"\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?\b"
)
_LINE_NUMBER_RE = re.compile(r"(?<=[:(,])\d+(?=[:),\s])")
_TEMP_PATH_RE = re.compile(
    r"(?P<path>(?:/private/var/folders|/var/folders|/tmp|/var/tmp)"
    r"/[^\s:'\"]+)"
)
_FAILED_TEST_RE = re.compile(r"^(?:FAILED|ERROR)\s+([^\s]+(?:::[^\s]+)*)")
_PYTEST_SHORT_SUMMARY_RE = re.compile(
    r"^(?:FAILED|ERROR)\s+([^\s]+(?:::[^\s]+)*)"
)
_COUNT_PATTERNS = {
    "passed": re.compile(r"(\d+)\s+passed\b"),
    "failed": re.compile(r"(\d+)\s+failed\b"),
    "error": re.compile(r"(\d+)\s+error(?:s)?\b"),
}


class NormalizedTestResult(BaseModel):
    status: NormalizedTestStatus
    command: str | None = None
    exit_code: int | None = None
    tests_total: int | None = None
    tests_passed: int | None = None
    tests_failed: int | None = None
    fail_signature: str | None = None
    stdout_preview: str = Field(default="")
    stderr_preview: str = Field(default="")
    duration_seconds: float | None = None
    error_message: str | None = None

    model_config = ConfigDict(extra="forbid")


def _bound_preview(raw: Any) -> str:
    text = "" if raw is None else str(raw)
    if len(text) <= _PREVIEW_LIMIT:
        return text
    return text[: _PREVIEW_LIMIT - 1] + "…"


def _scrub_volatile_text(raw: Any) -> str:
    text = "" if raw is None else str(raw)
    text = _MEMORY_ADDRESS_RE.sub("0xADDR", text)
    text = _TIMESTAMP_RE.sub("TIMESTAMP", text)
    text = _TEMP_PATH_RE.sub("/TMPPATH", text)
    text = _LINE_NUMBER_RE.sub("LINE", text)
    text = " ".join(text.split())
    return text


def _signature_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw_line in text.splitlines():
        clean = " ".join(raw_line.strip().split())
        if clean:
            lines.append(clean)
    return lines[:_SIGNATURE_LINE_LIMIT]


def _extract_failing_tests(stdout: str, stderr: str) -> list[str]:
    candidates: list[str] = []
    for line in f"{stdout}\n{stderr}".splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        match = _FAILED_TEST_RE.match(stripped)
        if match:
            candidates.append(match.group(1))
            continue
        short_summary = _PYTEST_SHORT_SUMMARY_RE.match(stripped)
        if short_summary:
            candidates.append(short_summary.group(1))
    deduped: list[str] = []
    for item in candidates:
        if item not in deduped:
            deduped.append(item)
    return sorted(deduped)


def _extract_counts(text: str, *, kind: str) -> int | None:
    match = _COUNT_PATTERNS[kind].search(text)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def _first_meaningful_line(*texts: str) -> str | None:
    for text in texts:
        for line in text.splitlines():
            clean = " ".join(line.strip().split())
            if clean:
                return clean
    return None


def normalize_subprocess_test_result(
    command: str,
    exit_code: int,
    stdout: str,
    stderr: str,
    duration_seconds: float | None = None,
) -> NormalizedTestResult:
    command_text = str(command or "").strip()
    stdout_text = "" if stdout is None else str(stdout)
    stderr_text = "" if stderr is None else str(stderr)
    stdout_preview = _bound_preview(stdout_text)
    stderr_preview = _bound_preview(stderr_text)

    if not command_text:
        return NormalizedTestResult(
            status="error",
            command=None,
            exit_code=exit_code if isinstance(exit_code, int) else None,
            stdout_preview=stdout_preview,
            stderr_preview=stderr_preview,
            duration_seconds=duration_seconds,
            error_message="invalid_test_command",
        )

    if not isinstance(exit_code, int):
        return NormalizedTestResult(
            status="error",
            command=command_text,
            exit_code=None,
            stdout_preview=stdout_preview,
            stderr_preview=stderr_preview,
            duration_seconds=duration_seconds,
            error_message="invalid_exit_code",
        )

    if exit_code == 0:
        passed = _extract_counts(stdout_text, kind="passed")
        failed = _extract_counts(stdout_text, kind="failed")
        total = None
        if passed is not None or failed is not None:
            total = (passed or 0) + (failed or 0)
        return NormalizedTestResult(
            status="passed",
            command=command_text,
            exit_code=exit_code,
            tests_total=total,
            tests_passed=passed,
            tests_failed=failed,
            fail_signature=None,
            stdout_preview=stdout_preview,
            stderr_preview=stderr_preview,
            duration_seconds=duration_seconds,
            error_message=None,
        )

    failing_tests = _extract_failing_tests(stdout_text, stderr_text)
    scrubbed_text = _scrub_volatile_text(f"{stdout_text}\n{stderr_text}")
    signature_lines = _signature_lines(scrubbed_text)
    fail_signature = build_fail_signature(failing_tests, signature_lines)
    failed = _extract_counts(stdout_text, kind="failed")
    errors = _extract_counts(stdout_text, kind="error")
    passed = _extract_counts(stdout_text, kind="passed")
    tests_failed = (
        failed
        if failed is not None
        else (len(failing_tests) if failing_tests else errors)
    )
    total = None
    if any(value is not None for value in (passed, tests_failed, errors)):
        total = sum(value or 0 for value in (passed, tests_failed, errors))
    return NormalizedTestResult(
        status="failed",
        command=command_text,
        exit_code=exit_code,
        tests_total=total,
        tests_passed=passed,
        tests_failed=tests_failed,
        fail_signature=fail_signature,
        stdout_preview=stdout_preview,
        stderr_preview=stderr_preview,
        duration_seconds=duration_seconds,
        error_message=_first_meaningful_line(stderr_text, stdout_text),
    )


def not_run_test_result(
    reason: str,
    command: str | None = None,
) -> NormalizedTestResult:
    reason_text = str(reason or "").strip() or "test_not_run"
    command_text = str(command or "").strip() or None
    return NormalizedTestResult(
        status="not_run",
        command=command_text,
        exit_code=None,
        tests_total=None,
        tests_passed=None,
        tests_failed=None,
        fail_signature=None,
        stdout_preview="",
        stderr_preview="",
        duration_seconds=None,
        error_message=reason_text,
    )
