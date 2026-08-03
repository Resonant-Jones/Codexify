from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping

import pytest

from guardian.agents import pi_readiness
from guardian.agents.pi_readiness import (
    PI_READINESS_REASONS,
    PI_READINESS_STATES,
    evaluate_pi_readiness,
)


def _fixture_environment(
    tmp_path: Path,
    *,
    wrapper: bool = True,
    sdk: bool = True,
    auth: bool = True,
) -> dict[str, str]:
    home = tmp_path / "home"
    wrapper_path = tmp_path / "codex_runner" / "src" / "agent-wrapper.js"
    package_root = (
        tmp_path / "pi-sdk" / "node_modules" / "@mariozechner" / "pi-coding-agent"
    )
    node_modules = tmp_path / "pi-sdk" / "node_modules"
    home.mkdir(parents=True)
    if wrapper:
        wrapper_path.parent.mkdir(parents=True)
        wrapper_path.write_text("// fixture\n", encoding="utf-8")
    if sdk:
        (package_root / "dist").mkdir(parents=True)
        (package_root / "dist" / "index.js").write_text(
            "// fixture\n", encoding="utf-8"
        )
        pi_ai_dist = node_modules / "@mariozechner" / "pi-ai" / "dist"
        pi_ai_dist.mkdir(parents=True)
        (pi_ai_dist / "index.js").write_text("// fixture\n", encoding="utf-8")
    if auth:
        auth_path = home / ".pi" / "agent" / "auth.json"
        auth_path.parent.mkdir(parents=True)
        auth_path.write_text("{}\n", encoding="utf-8")
        auth_path.chmod(0o600)
    return {
        "HOME": str(home),
        "PATH": os.environ.get("PATH", ""),
        "PI_WRAPPER_PATH": str(wrapper_path),
        "PI_CODING_AGENT_PACKAGE_ROOT": str(package_root),
        "PI_CODING_AGENT_NODE_MODULES": str(node_modules),
        "PI_PROVIDER": "anthropic",
        "PI_MODEL": "claude-sonnet-4-20250514",
    }


def _probe(
    *,
    initialized: bool = True,
    resolved: bool = True,
    credential: bool = True,
):
    def probe(
        _node: str,
        _wrapper: Path,
        _environment: Mapping[str, str],
    ) -> Mapping[str, object]:
        return {
            "adapter_initialized": initialized,
            "provider_resolved": resolved,
            "provider_credential_available": credential,
            "effective_provider": "anthropic",
            "effective_model": "claude-sonnet-4-20250514",
        }

    return probe


def test_readiness_tokens_are_bounded() -> None:
    assert PI_READINESS_STATES == {"ready", "blocked", "degraded"}
    assert {
        "node_missing",
        "wrapper_missing",
        "pi_sdk_build_missing",
        "worker_home_unavailable",
        "worker_home_read_only",
        "pi_auth_missing",
        "pi_auth_unreadable",
        "pi_auth_permissions_open",
        "provider_unresolved",
        "provider_credential_missing",
        "adapter_initialization_failed",
    } == PI_READINESS_REASONS


def test_missing_sdk_build_reports_blocked(tmp_path: Path) -> None:
    environment = _fixture_environment(tmp_path, sdk=False)

    report = evaluate_pi_readiness(environ=environment, adapter_probe=_probe())

    assert report.status == "blocked"
    assert "pi_sdk_build_missing" in report.reasons
    assert report.can_consume_tasks is False


def test_missing_pi_auth_reports_blocked(tmp_path: Path) -> None:
    environment = _fixture_environment(tmp_path, auth=False)

    def probe_must_not_run(
        _node: str,
        _wrapper: Path,
        _environment: Mapping[str, str],
    ) -> Mapping[str, object]:
        pytest.fail("adapter initialization must not create missing auth material")

    report = evaluate_pi_readiness(
        environ=environment,
        adapter_probe=probe_must_not_run,
    )

    assert report.status == "blocked"
    assert "pi_auth_missing" in report.reasons


def test_unreadable_pi_auth_reports_distinct_reason(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    environment = _fixture_environment(tmp_path)
    monkeypatch.setattr(pi_readiness, "_auth_file_state", lambda _path: "unreadable")

    report = evaluate_pi_readiness(environ=environment, adapter_probe=_probe())

    assert report.status == "blocked"
    assert "pi_auth_unreadable" in report.reasons


def test_read_only_worker_home_reports_blocked(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    environment = _fixture_environment(tmp_path)
    worker_home = Path(environment["HOME"])
    real_access = pi_readiness.os.access

    def access(path: os.PathLike[str] | str, mode: int) -> bool:
        if Path(path) == worker_home and mode == os.W_OK:
            return False
        return real_access(path, mode)

    monkeypatch.setattr(pi_readiness.os, "access", access)

    report = evaluate_pi_readiness(environ=environment, adapter_probe=_probe())

    assert report.status == "blocked"
    assert report.reasons == ("worker_home_read_only",)
    assert report.can_consume_tasks is False


def test_overly_open_auth_permissions_report_degraded(tmp_path: Path) -> None:
    environment = _fixture_environment(tmp_path)
    (Path(environment["HOME"]) / ".pi/agent/auth.json").chmod(0o644)

    report = evaluate_pi_readiness(environ=environment, adapter_probe=_probe())

    assert report.status == "degraded"
    assert report.warnings == ("pi_auth_permissions_open",)
    assert report.can_consume_tasks is True


def test_missing_provider_credential_reports_blocked(tmp_path: Path) -> None:
    environment = _fixture_environment(tmp_path)

    report = evaluate_pi_readiness(
        environ=environment,
        adapter_probe=_probe(credential=False),
    )

    assert report.status == "blocked"
    assert "provider_credential_missing" in report.reasons


def test_wrapper_only_state_cannot_report_ready(tmp_path: Path) -> None:
    environment = _fixture_environment(tmp_path, sdk=False, auth=False)

    report = evaluate_pi_readiness(environ=environment, adapter_probe=_probe())

    assert report.status == "blocked"
    assert {"pi_sdk_build_missing", "pi_auth_missing"} <= set(report.reasons)


def test_complete_prerequisite_fixture_reports_ready_without_leaking_secret(
    tmp_path: Path,
) -> None:
    environment = _fixture_environment(tmp_path)
    fake_secret = "fixture-not-a-real-secret"
    environment["ANTHROPIC_API_KEY"] = fake_secret

    report = evaluate_pi_readiness(environ=environment, adapter_probe=_probe())
    rendered = report.to_json() + report.to_human()

    assert report.status == "ready"
    assert report.can_consume_tasks is True
    assert report.credential_validity == "unproven"
    assert fake_secret not in rendered


def test_adapter_initialization_failure_is_stable_and_secret_free(
    tmp_path: Path,
) -> None:
    environment = _fixture_environment(tmp_path)
    environment["ANTHROPIC_API_KEY"] = "fixture-not-a-real-secret"

    report = evaluate_pi_readiness(
        environ=environment,
        adapter_probe=_probe(initialized=False),
    )

    assert report.status == "blocked"
    assert report.reasons == ("adapter_initialization_failed",)
    assert "fixture-not-a-real-secret" not in report.to_json()


def test_provider_resolution_failure_is_reported_separately(tmp_path: Path) -> None:
    environment = _fixture_environment(tmp_path)

    report = evaluate_pi_readiness(
        environ=environment,
        adapter_probe=_probe(resolved=False, credential=False),
    )

    assert report.status == "blocked"
    assert "provider_unresolved" in report.reasons
    assert "provider_credential_missing" not in report.reasons
