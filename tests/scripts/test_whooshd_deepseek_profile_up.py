"""Contract checks for the bounded Whoosh'd startup proof script."""

from pathlib import Path

SCRIPT = Path("scripts/whooshd_deepseek_profile_up.sh")


def test_startup_script_polls_readiness_after_kickstart() -> None:
    content = SCRIPT.read_text()

    assert "WHOOSHD_READINESS_TIMEOUT_SECONDS" in content
    assert "while time.monotonic() < deadline:" in content
    assert "time.sleep(2)" in content


def test_startup_script_polls_codexify_worker_readiness() -> None:
    content = SCRIPT.read_text()

    assert "CODEXIFY_READINESS_TIMEOUT_SECONDS" in content
    assert "Codexify did not become ready within" in content
    assert "health_payloads" in content


def test_concurrent_gate_validates_completion_bodies() -> None:
    content = SCRIPT.read_text()

    assert "body = json.load(response)" in content
    assert "expected_results = [(200, 'LOAD-1'), (200, 'LOAD-2')]" in content
    assert "normalized_results != expected_results" in content
