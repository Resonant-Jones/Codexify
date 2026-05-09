"""Normalization helpers for coding-worker test truth.

The contract is intentionally small: turn raw subprocess output into a bounded,
deterministic result object so future orchestration can reason from structured
test truth instead of raw stdout/stderr blobs.
"""

from __future__ import annotations

import hashlib
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

NormalizedTestStatus = Literal["passed", "failed", "error", "not_run"]

_PREVIEW_LIMIT = 2048
_SIGNATURE_EXCERPT_LIMIT = 8

_HEX_ADDRESS_RE = re.compile(r"\b0x[0-9a-fA-F]+\b")
_ISO_TIMESTAMP_RE = re.compile(
    r"\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}"
    r"(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?\b"
)
_TEMP_PATH_RE = re.compile(
    r"(?:/private/var/folders|/var/folders|/private/tmp|/var/tmp|/tmp)"
    r"(?:/[^\s'\"`]+)+"
)
_ABS_PATH_RE = re.compile(r"(?<!\w)(?:[A-Za-z]:[\\/]|/)(?:[^\s'\"`]+)")
_LINE_COL_RE = re.compile(r":\d+(?::\d+)?")
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


def _preview(text: str | None) -> str:
    value = str(text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if len(value) <= _PREVIEW_LIMIT:
        return value
    return value[:_PREVIEW_LIMIT]


def _normalize_signature_text(text: str) -> str:
    value = text.replace("\r\n", "\n").replace("\r", "\n")
    value = _HEX_ADDRESS_RE.sub("0xADDR", value)
    value = _ISO_TIMESTAMP_RE.sub("<timestamp>", value)
    value = _TEMP_PATH_RE.sub("<temp_path>", value)
    value = _ABS_PATH_RE.sub("<path>", value)
    value = _LINE_COL_RE.sub(":<line>", value)
    value = _LINE_WORD_RE.sub("line <line>", value)
    value = _COL_WORD_RE.sub("col <col>", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


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


def _signature_excerpt(stdout: str, stderr: str) -> list[str]:
    lines: list[str] = []
    for text in (stderr, stdout):
        for raw_line in text.splitlines():
            line = _normalize_signature_text(raw_line)
            if not line:
                continue
            if line not in lines:
                lines.append(line)
            if len(lines) >= _SIGNATURE_EXCERPT_LIMIT:
                return lines
    return lines


def _build_fail_signature(
    *,
    exit_code: int,
    failing_tests: list[str],
    stdout: str,
    stderr: str,
) -> str:
    payload_lines = [f"exit={exit_code}"]
    payload_lines.extend(
        f"test={item}"
        for item in sorted(
            {test.strip() for test in failing_tests if test.strip()}
        )
    )
    payload_lines.append("---")
    payload_lines.extend(_signature_excerpt(stdout, stderr))
    payload = "\n".join(payload_lines)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return digest[:24]


def normalize_subprocess_test_result(
    command: str,
    exit_code: int,
    stdout: str,
    stderr: str,
    duration_seconds: float | None = None,
) -> NormalizedTestResult:
    normalized_command = str(command or "").strip() or None
    stdout_text = str(stdout or "")
    stderr_text = str(stderr or "")
    stdout_preview = _preview(stdout_text)
    stderr_preview = _preview(stderr_text)

    if normalized_command is None:
        return NormalizedTestResult(
            status="error",
            command=None,
            exit_code=exit_code,
            stdout_preview=stdout_preview,
            stderr_preview=stderr_preview,
            duration_seconds=duration_seconds,
            error_message="command is empty",
        )

    if exit_code == 0:
        tests_total, tests_passed, tests_failed = _collect_summary_counts(
            stdout_text, stderr_text
        )
        if tests_passed is None and tests_total is None:
            tests_passed = None
            tests_failed = None
        return NormalizedTestResult(
            status="passed",
            command=normalized_command,
            exit_code=exit_code,
            tests_total=tests_total,
            tests_passed=tests_passed,
            tests_failed=tests_failed,
            failing_tests=[],
            stdout_preview=stdout_preview,
            stderr_preview=stderr_preview,
            duration_seconds=duration_seconds,
        )

    if exit_code < 0:
        return NormalizedTestResult(
            status="error",
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
    fail_signature = _build_fail_signature(
        exit_code=exit_code,
        failing_tests=failing_tests,
        stdout=stdout_text,
        stderr=stderr_text,
    )
    return NormalizedTestResult(
        status="failed",
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
    )


def not_run_test_result(
    reason: str,
    command: str | None = None,
) -> NormalizedTestResult:
    return NormalizedTestResult(
        status="not_run",
        command=str(command).strip()
        if command and str(command).strip()
        else None,
        stdout_preview="",
        stderr_preview="",
        error_message=str(reason).strip() or "not run",
    )


__all__ = [
    "NormalizedTestResult",
    "NormalizedTestStatus",
    "normalize_subprocess_test_result",
    "not_run_test_result",
]
