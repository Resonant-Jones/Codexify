import os
from guardian.core.orchestrator import pulse_orchestrator as po
from guardian.core.orchestrator.pulse_orchestrator import _get_effective_timeout


def test_timeout_env_ignored_when_empty(monkeypatch):
    # Ensure settings doesn't override the fallback for this guard test
    monkeypatch.setattr(po, "settings", type("S", (), {"AGENT_TIMEOUT_SECONDS": None})())
    monkeypatch.delenv("FORESIGHT_TIMEOUT", raising=False)
    assert _get_effective_timeout() == 2.0
    monkeypatch.setenv("FORESIGHT_TIMEOUT", "")
    assert _get_effective_timeout() == 2.0
    monkeypatch.setenv("FORESIGHT_TIMEOUT", "1.5")
    assert _get_effective_timeout() == 1.5
