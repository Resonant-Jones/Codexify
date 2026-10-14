from __future__ import annotations

from guardian.agents.test_results import NormalizedTestResult
from guardian.workers import coding_worker


def test_coding_worker_validation_wrapper_uses_shared_runner(monkeypatch, tmp_path) -> None:
    expected = NormalizedTestResult(status="passed", command="pytest -q", exit_code=0)
    calls = []

    def shared_runner(**kwargs):
        calls.append(kwargs)
        return expected

    monkeypatch.setattr(coding_worker, "run_validation_command", shared_runner)
    result = coding_worker._run_validation_command(
        command="pytest -q",
        cwd=str(tmp_path),
        timeout_seconds=45,
    )

    assert result is expected
    assert calls == [{
        "command": "pytest -q",
        "cwd": str(tmp_path),
        "timeout_seconds": 45,
    }]


def test_coding_worker_timeout_uses_shared_cap() -> None:
    assert coding_worker._validation_timeout_seconds(900) == 120
