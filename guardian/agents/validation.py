"""Guardian/Coding Loop validation-command execution primitive.

This module executes exactly one validation attempt. Retry policy remains in
the caller so a consumer can use the same bounded command seam without
inheriting Coding Worker retry behavior.
"""

from __future__ import annotations

import shlex
import subprocess
import time
from pathlib import Path

from guardian.agents.test_results import (
    NormalizedTestResult,
    normalize_subprocess_test_result,
)

VALIDATION_TIMEOUT_CAP_SECONDS = 120
_VALIDATION_ERROR_PREVIEW_LIMIT = 480


def _build_validation_error_result(
    *,
    command: str,
    stdout: str = "",
    stderr: str = "",
    error_message: str,
    duration_seconds: float | None = None,
) -> NormalizedTestResult:
    return NormalizedTestResult(
        status="error",
        command=command,
        exit_code=None,
        tests_total=None,
        tests_passed=None,
        tests_failed=None,
        fail_signature=None,
        stdout_preview=stdout[:_VALIDATION_ERROR_PREVIEW_LIMIT],
        stderr_preview=stderr[:_VALIDATION_ERROR_PREVIEW_LIMIT],
        duration_seconds=duration_seconds,
        error_message=error_message,
    )


def validation_timeout_seconds(task_timeout_seconds: int) -> int:
    """Apply the established one-shot Coding Worker validation timeout cap."""
    return max(1, min(int(task_timeout_seconds or 0), VALIDATION_TIMEOUT_CAP_SECONDS))


def run_validation_command(
    *,
    command: str,
    cwd: str | Path,
    timeout_seconds: int,
) -> NormalizedTestResult:
    """Run one shell-free validation command in an explicit working directory."""
    try:
        argv = shlex.split(command)
    except ValueError as exc:
        return _build_validation_error_result(
            command=command,
            error_message=f"validation_command_parse_failed: {exc}",
        )
    if not argv:
        return _build_validation_error_result(
            command=command,
            error_message="validation_command_empty",
        )

    try:
        resolved_timeout = validation_timeout_seconds(timeout_seconds)
    except (TypeError, ValueError, OverflowError):
        return _build_validation_error_result(
            command=command,
            error_message="validation_timeout_invalid",
        )

    started = time.monotonic()
    try:
        completed = subprocess.run(
            argv,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=False,
            timeout=resolved_timeout,
        )
    except subprocess.TimeoutExpired:
        elapsed = time.monotonic() - started
        return _build_validation_error_result(
            command=command,
            error_message="validation_command_timeout",
            duration_seconds=elapsed,
        )
    except Exception as exc:
        elapsed = time.monotonic() - started
        return _build_validation_error_result(
            command=command,
            error_message=f"validation_command_error: {type(exc).__name__}",
            duration_seconds=elapsed,
        )

    elapsed = time.monotonic() - started
    return normalize_subprocess_test_result(
        command=command,
        exit_code=completed.returncode,
        stdout=completed.stdout or "",
        stderr=completed.stderr or "",
        duration_seconds=elapsed,
    )


__all__ = [
    "VALIDATION_TIMEOUT_CAP_SECONDS",
    "run_validation_command",
    "validation_timeout_seconds",
]
