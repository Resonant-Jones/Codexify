"""Normalization helpers for coding-worker test truth.

The contract is intentionally small: turn raw subprocess output into a bounded,
deterministic result object so orchestration can reason from structured test
truth instead of raw stdout/stderr blobs.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from guardian.agents.retry_policy import build_fail_signature
from guardian.protocol_tokens import TestResultStatus

NormalizedTestStatus = Literal[
    TestResultStatus.PASSED.value,
    TestResultStatus.FAILED.value,
    TestResultStatus.ERROR.value,
    TestResultStatus.NOT_RUN.value,
]

_PREVIEW_LIMIT = 2048
_SIGNATURE_LINE_LIMIT = 20

_MEMORY_ADDRESS_RE = re.compile(r"0x[0-9a-fA-F]+")
_TIMESTAMP_RE = re.compile(
    r"\b\d{4}-\d{2}-\d{2}[T ]"
    r"\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?\b"
)
_TEMP_PATH_RE = re.compile(
    r"(?:/private/var/folders|/var/folders|/private/tmp|/var/tmp|/tmp)"
    r"(?:/[^\s:'\"`]+)+"
)
_ABS_PATH_RE = re.compile(r"(?<!\w)(?:[A-Za-z]:[\\/]|/)(?:[^\s'\"`]+)")
_LINE_COL_RE = re.compile(r":\d+(?::\d+)?")
_LINE_NUMBER_RE = re.compile(r"(?<=[:(,])\d+(?=[:),\s])")
_LINE_WORD_RE = re.compile(r"\bline\s+\d+\b", re.IGNORECASE)
_COL_WORD_RE = re.compile(r"\bcol(?:umn)?\s+\d+\b", re.IGNORECASE)
_PYTEST_FAIL_RE = re.compile(
    r"^\s*(?:FAILED|ERROR)\s+(?P<nodeid>.+?)(?:\s+-\s+.*)?$"
)
_SUMMARY_COUNT_RE = re.compile(
    r"(?P<count>\d+)\s+"
    r"(?P<label>failed|passed|errors?|skipped|xfailed|xpassed)\b",
    re.IGNORECASE,
)
_SUMMARY_LINE_RE = re.compile(
    r"^\s*=+.*(?:failed|passed|error|skipped|xfailed|xpassed).*=+\s*$",
    re.IGNORECASE,
)


class NormalizedTestResult(BaseModel):
    """Structured test result emitted by Guardian-mediated coding work."""

    status: NormalizedTestStatus
    command: str | None = None
    exit_code: int | None = None
    tests_total: int | None = None
    tests_passed: int | None = None
    tests_failed: int | None = None
    failing_tests: list[str] = Field(default_factory=list)
    fail_signature: str | None = None
    stdout_preview: str = ""
    stderr_preview: str = ""
    duration_seconds: float | None = None
    error_message: str | None = None

    model_config = ConfigDict(extra="forbid")


def _bound_preview(raw: object | None) -> str:
    text = "" if raw is None else str(raw)
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if len(text) <= _PREVIEW_LIMIT:
        return text
    return text[: _PREVIEW_LIMIT - 1] + "…"


def _preview(text: str | None) -> str:
    return _bound_preview(text)


def _scrub_volatile_text(raw: object | None) -> str:
    text = "" if raw is None else str(raw)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _MEMORY_ADDRESS_RE.sub("0xADDR", text)
    text = _TIMESTAMP_RE.sub("TIMESTAMP", text)
    text = _TEMP_PATH_RE.sub("/TMPPATH", text)
    text = _ABS_PATH_RE.sub("/ABSPATH", text)
    text = _LINE_COL_RE.sub(":LINE", text)
    text = _LINE_NUMBER_RE.sub("LINE", text)
    text = _LINE_WORD_RE.sub("line LINE", text)
    text = _COL_WORD_RE.sub("col LINE", text)
    return " ".join(text.split())


def _normalize_signature_text(text: str) -> str:
    return _scrub_volatile_text(text)


def _signature_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw_line in text.splitlines():
        clean = " ".join(raw_line.strip().split())
        if clean and clean not in lines:
            lines.append(clean)
    return lines[:_SIGNATURE_LINE_LIMIT]


def _signature_excerpt(stdout: str, stderr: str) -> list[str]:
    lines: list[str] = []
    for text in (stderr, stdout):
        for raw_line in text.splitlines():
            line = _normalize_signature_text(raw_line)
            if not line:
                continue
            if line not in lines:
                lines.append(line)
            if len(lines) >= _SIGNATURE_LINE_LIMIT:
                return lines
    return lines


def _collect_summary_counts(
    stdout: str, stderr: str
) -> tuple[int | None, int | None, int | None]:
    totals = {
        "passed": 0,
        "failed": 0,
        "error": 0,
        "skipped": 0,
        "xfailed": 0,
        "xpassed": 0,
    }
    matched = False
    for text in (stdout, stderr):
        for line in text.splitlines():
            normalized = line.lower()
            if not _SUMMARY_LINE_RE.match(line) and " in " not in normalized:
                continue
            for count, label in _SUMMARY_COUNT_RE.findall(line):
                matched = True
                key = label.lower()
                if key == "errors":
                    key = "error"
                totals[key] += int(count)
    if not matched:
        return None, None, None
    tests_passed = totals["passed"]
    tests_failed = totals["failed"] + totals["error"]
    tests_total = sum(totals.values())
    return tests_total, tests_passed, tests_failed


def _extract_failing_tests(stdout: str, stderr: str) -> list[str]:
    discovered: list[str] = []
    for text in (stderr, stdout):
        for line in text.splitlines():
            match = _PYTEST_FAIL_RE.match(line)
            if not match:
                continue
            nodeid = " ".join(match.group("nodeid").strip().split())
            if nodeid and nodeid not in discovered:
                discovered.append(nodeid)
    return discovered


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
    normalized_command = str(command or "").strip() or None
    stdout_text = "" if stdout is None else str(stdout)
    stderr_text = "" if stderr is None else str(stderr)
    stdout_preview = _preview(stdout_text)
    stderr_preview = _preview(stderr_text)

    if normalized_command is None:
        return NormalizedTestResult(
            status=TestResultStatus.ERROR.value,
            command=None,
            exit_code=exit_code,
            stdout_preview=stdout_preview,
            stderr_preview=stderr_preview,
            duration_seconds=duration_seconds,
            error_message="invalid_test_command",
        )

    if not isinstance(exit_code, int):
        return NormalizedTestResult(
            status=TestResultStatus.ERROR.value,
            command=normalized_command,
            exit_code=None,
            stdout_preview=stdout_preview,
            stderr_preview=stderr_preview,
            duration_seconds=duration_seconds,
            error_message="invalid_exit_code",
        )

    if exit_code == 0:
        tests_total, tests_passed, tests_failed = _collect_summary_counts(
            stdout_text, stderr_text
        )
        return NormalizedTestResult(
            status=TestResultStatus.PASSED.value,
            command=normalized_command,
            exit_code=exit_code,
            tests_total=tests_total,
            tests_passed=tests_passed,
            tests_failed=tests_failed,
            failing_tests=[],
            fail_signature=None,
            stdout_preview=stdout_preview,
            stderr_preview=stderr_preview,
            duration_seconds=duration_seconds,
            error_message=None,
        )

    if exit_code < 0:
        return NormalizedTestResult(
            status=TestResultStatus.ERROR.value,
            command=normalized_command,
            exit_code=exit_code,
            stdout_preview=stdout_preview,
            stderr_preview=stderr_preview,
            duration_seconds=duration_seconds,
            error_message=f"process terminated by signal {-exit_code}",
        )

    failing_tests = _extract_failing_tests(stdout_text, stderr_text)
    tests_total, tests_passed, tests_failed = _collect_summary_counts(
        stdout_text, stderr_text
    )
    if tests_failed is None and failing_tests:
        tests_failed = len(failing_tests)
    if (
        tests_total is None
        and tests_passed is not None
        and tests_failed is not None
    ):
        tests_total = tests_passed + tests_failed
    fail_signature = build_fail_signature(
        failing_tests,
        _signature_lines(_scrub_volatile_text(f"{stdout_text}\n{stderr_text}")),
    )
    return NormalizedTestResult(
        status=TestResultStatus.FAILED.value,
        command=normalized_command,
        exit_code=exit_code,
        tests_total=tests_total,
        tests_passed=tests_passed,
        tests_failed=tests_failed,
        failing_tests=failing_tests,
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
        status=TestResultStatus.NOT_RUN.value,
        command=command_text,
        exit_code=None,
        tests_total=None,
        tests_passed=None,
        tests_failed=None,
        failing_tests=[],
        fail_signature=None,
        stdout_preview="",
        stderr_preview="",
        duration_seconds=None,
        error_message=reason_text,
    )


__all__ = [
    "NormalizedTestResult",
    "normalize_subprocess_test_result",
    "not_run_test_result",
]
