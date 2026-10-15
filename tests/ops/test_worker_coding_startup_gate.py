from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from guardian.agents.pi_readiness import PiReadinessCheck, PiReadinessReport


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "backend/scripts/docker/run_worker_coding.py"


def _load_startup_module():
    spec = importlib.util.spec_from_file_location(
        "run_worker_coding_under_test", SCRIPT
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_blocked_worker_exits_before_proxy_or_queue_consumer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_startup_module()
    report = PiReadinessReport(
        status="blocked",
        effective_provider="anthropic",
        effective_model="claude-sonnet-4-6",
        checks=(
            PiReadinessCheck(
                name="pi_sdk_runtime",
                state="blocked",
                reason="pi_sdk_build_missing",
            ),
        ),
        reasons=("pi_sdk_build_missing",),
        warnings=(),
    )

    monkeypatch.setattr(module, "evaluate_pi_readiness", lambda: report)
    monkeypatch.setattr(
        module,
        "_start_proxy",
        lambda: pytest.fail("proxy started while Pi readiness was blocked"),
    )
    monkeypatch.setattr(
        module.subprocess,
        "Popen",
        lambda *_args, **_kwargs: pytest.fail(
            "coding worker started while Pi readiness was blocked"
        ),
    )

    assert module.main() == 78
