from __future__ import annotations

import subprocess
from types import SimpleNamespace

import pytest

from guardian.agents import validation


def test_validation_runner_uses_direct_argv_and_explicit_cwd(monkeypatch, tmp_path) -> None:
    calls = []

    def fake_run(argv, **kwargs):
        calls.append((argv, kwargs))
        return SimpleNamespace(returncode=0, stdout="2 passed\n", stderr="")

    monkeypatch.setattr(validation.subprocess, "run", fake_run)
    result = validation.run_validation_command(
        command='python -c "print(\'two words\')"',
        cwd=tmp_path,
        timeout_seconds=900,
    )

    assert result.status == "passed"
    assert result.exit_code == 0
    assert calls[0][0] == ["python", "-c", "print('two words')"]
    assert calls[0][1]["cwd"] == str(tmp_path)
    assert calls[0][1]["timeout"] == validation.VALIDATION_TIMEOUT_CAP_SECONDS
    assert calls[0][1]["capture_output"] is True
    assert "shell" not in calls[0][1]


def test_validation_runner_normalizes_failure_and_bounds_previews(monkeypatch, tmp_path) -> None:
    def fake_run(argv, **kwargs):
        return SimpleNamespace(
            returncode=1,
            stdout="x" * 5000,
            stderr="FAILED test_sample\n" + "y" * 5000,
        )

    monkeypatch.setattr(validation.subprocess, "run", fake_run)
    result = validation.run_validation_command(
        command="pytest -q",
        cwd=tmp_path,
        timeout_seconds=5,
    )

    assert result.status == "failed"
    assert result.exit_code == 1
    assert len(result.stdout_preview) <= 2048
    assert len(result.stderr_preview) <= 2048
    assert result.failing_tests == ["test_sample"]


def test_validation_runner_preserves_parse_timeout_and_execution_errors(
    monkeypatch, tmp_path
) -> None:
    calls = []

    def fake_run(argv, **kwargs):
        calls.append(argv)
        raise subprocess.TimeoutExpired(argv, kwargs["timeout"])

    monkeypatch.setattr(validation.subprocess, "run", fake_run)
    parse_error = validation.run_validation_command(
        command='python "unterminated', cwd=tmp_path, timeout_seconds=5
    )
    timeout = validation.run_validation_command(
        command="pytest -q", cwd=tmp_path, timeout_seconds=5
    )
    assert parse_error.status == "error"
    assert parse_error.error_message.startswith("validation_command_parse_failed:")
    assert timeout.status == "error"
    assert timeout.error_message == "validation_command_timeout"
    assert len(calls) == 1

    def execution_error(argv, **kwargs):
        raise FileNotFoundError("hidden path detail")

    monkeypatch.setattr(validation.subprocess, "run", execution_error)
    execution = validation.run_validation_command(
        command="missing-command", cwd=tmp_path, timeout_seconds=5
    )
    assert execution.status == "error"
    assert execution.error_message == "validation_command_error: FileNotFoundError"


@pytest.mark.parametrize("timeout", [None, 0, -4])
def test_validation_timeout_keeps_existing_floor(timeout) -> None:
    assert validation.validation_timeout_seconds(timeout) == 1


def test_validation_timeout_preserves_invalid_value_error() -> None:
    with pytest.raises(ValueError):
        validation.validation_timeout_seconds("bad")
