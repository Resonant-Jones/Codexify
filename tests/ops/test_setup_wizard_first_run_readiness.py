from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from guardian.ops import setup_wizard


def _write_env(path: Path, **values: str) -> None:
    path.write_text(
        "\n".join(f"{key}={value}" for key, value in values.items()) + "\n",
        encoding="utf-8",
    )


def _valid_env() -> dict[str, str]:
    return {
        "GUARDIAN_API_KEY": "a" * 64,
        "AI_BACKEND": "ollama",
        "LLM_PROVIDER": "local",
        "LOCAL_BASE_URL": "http://host.docker.internal:11434",
        "LOCAL_CHAT_MODEL": "llama3.2:latest",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASS": "not-a-placeholder",
    }


def test_normalizer_creates_missing_env_with_local_beta_posture(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"

    setup_wizard.write_env_file(env_path, {"LOCAL_CHAT_MODEL": "llama3.2:latest"})
    env = setup_wizard.read_env_file(env_path)

    assert len(env["GUARDIAN_API_KEY"]) == 64
    assert env["AI_BACKEND"] == "ollama"
    assert env["LLM_PROVIDER"] == "local"
    assert env["CODEXIFY_LOCAL_ONLY_MODE"] == "true"
    assert env["ALLOW_CLOUD_PROVIDERS"] == "false"
    assert env["LOCAL_BASE_URL"] == "http://host.docker.internal:11434"
    assert env["NEO4J_USER"] == "neo4j"
    assert env["NEO4J_PASS"]


def test_placeholder_guardian_api_key_is_replaced(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    _write_env(env_path, GUARDIAN_API_KEY="change-me", LOCAL_CHAT_MODEL="llama3.2:latest")

    setup_wizard.write_env_file(env_path, setup_wizard.read_env_file(env_path))
    env = setup_wizard.read_env_file(env_path)

    assert env["GUARDIAN_API_KEY"] != "change-me"
    assert len(env["GUARDIAN_API_KEY"]) == 64


def test_invalid_local_provider_split_is_normalized() -> None:
    result = setup_wizard.normalize_local_beta_config_values(
        {
            **_valid_env(),
            "AI_BACKEND": "local",
            "LLM_PROVIDER": "ollama",
        }
    )

    assert result.values["AI_BACKEND"] == "ollama"
    assert result.values["LLM_PROVIDER"] == "local"
    assert "AI_BACKEND" in result.conflict_keys
    assert "LLM_PROVIDER" in result.conflict_keys


def test_csp_value_is_preserved_as_valid_dotenv(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    csp = "default-src 'self'; script-src 'self' 'unsafe-inline'; img-src 'self' data: https:;"

    setup_wizard.write_env_file(
        env_path,
        {
            **_valid_env(),
            "GUARDIAN_CSP_POLICY": csp,
        },
    )

    written = env_path.read_text(encoding="utf-8")
    assert 'GUARDIAN_CSP_POLICY="' in written
    assert setup_wizard.read_env_file(env_path)["GUARDIAN_CSP_POLICY"] == csp


def test_secret_diagnostics_are_redacted() -> None:
    diagnostics = setup_wizard.redacted_config_diagnostics(
        {
            "GUARDIAN_API_KEY": "super-secret",
            "NEO4J_PASS": "also-secret",
            "LOCAL_CHAT_MODEL": "llama3.2:latest",
        }
    )

    assert diagnostics["GUARDIAN_API_KEY"] == "<redacted>"
    assert diagnostics["NEO4J_PASS"] == "<redacted>"
    assert diagnostics["LOCAL_CHAT_MODEL"] == "llama3.2:latest"
    assert "super-secret" not in json.dumps(diagnostics)


def test_classifies_missing_config(tmp_path: Path) -> None:
    summary = setup_wizard.classify_setup_readiness(tmp_path)

    assert summary.state == setup_wizard.SetupReadinessState.MISSING_CONFIG


def test_classifies_missing_docker(tmp_path: Path, monkeypatch: Any) -> None:
    _write_env(tmp_path / ".env", **_valid_env())
    monkeypatch.setattr(
        setup_wizard,
        "detect_dependency",
        lambda binary, display, custom_path=None: setup_wizard.DepStatus(
            name=display,
            is_present=False,
            found_path=None,
            help_text=f"{display} missing",
        )
        if binary == "docker"
        else setup_wizard.DepStatus(display, True, binary, "ok"),
    )

    summary = setup_wizard.classify_setup_readiness(tmp_path)

    assert summary.state == setup_wizard.SetupReadinessState.DOCKER_MISSING


def test_classifies_docker_unavailable(tmp_path: Path, monkeypatch: Any) -> None:
    _write_env(tmp_path / ".env", **_valid_env())
    monkeypatch.setattr(
        setup_wizard,
        "detect_dependency",
        lambda binary, display, custom_path=None: setup_wizard.DepStatus(
            display, True, binary, "ok"
        ),
    )

    def runner(args: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args, 1, "", "daemon unavailable")

    summary = setup_wizard.classify_setup_readiness(tmp_path, runner=runner)

    assert summary.state == setup_wizard.SetupReadinessState.DOCKER_NOT_RUNNING


def test_classifies_ollama_unavailable(tmp_path: Path, monkeypatch: Any) -> None:
    _write_env(tmp_path / ".env", **_valid_env())
    monkeypatch.setattr(
        setup_wizard,
        "detect_dependency",
        lambda binary, display, custom_path=None: setup_wizard.DepStatus(
            display, True, binary, "ok"
        ),
    )

    def runner(args: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args, 0, "ok", "")

    def http_getter(url: str, timeout: float) -> tuple[int, str]:
        if "11434" in url:
            raise ConnectionError("ollama stopped")
        return 200, '{"status":"ok"}'

    summary = setup_wizard.classify_setup_readiness(
        tmp_path, runner=runner, http_getter=http_getter
    )

    assert summary.state == setup_wizard.SetupReadinessState.OLLAMA_NOT_RUNNING


def test_classifies_selected_model_missing(tmp_path: Path, monkeypatch: Any) -> None:
    _write_env(tmp_path / ".env", **_valid_env())
    monkeypatch.setattr(
        setup_wizard,
        "detect_dependency",
        lambda binary, display, custom_path=None: setup_wizard.DepStatus(
            display, True, binary, "ok"
        ),
    )

    def runner(args: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args, 0, "ok", "")

    def http_getter(url: str, timeout: float) -> tuple[int, str]:
        if "11434" in url:
            return 200, '{"models":[{"name":"other:latest"}]}'
        return 200, '{"status":"ok"}'

    summary = setup_wizard.classify_setup_readiness(
        tmp_path, runner=runner, http_getter=http_getter
    )

    assert summary.state == setup_wizard.SetupReadinessState.MODEL_MISSING


def test_classifies_compose_config_invalid(tmp_path: Path, monkeypatch: Any) -> None:
    _write_env(tmp_path / ".env", **_valid_env())
    monkeypatch.setattr(
        setup_wizard,
        "detect_dependency",
        lambda binary, display, custom_path=None: setup_wizard.DepStatus(
            display, True, binary, "ok"
        ),
    )

    def runner(args: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
        if args[-2:] == ["compose", "config"]:
            return subprocess.CompletedProcess(args, 1, "", "bad compose")
        return subprocess.CompletedProcess(args, 0, "ok", "")

    def http_getter(url: str, timeout: float) -> tuple[int, str]:
        return 200, '{"models":[{"name":"llama3.2:latest"}]}'

    summary = setup_wizard.classify_setup_readiness(
        tmp_path, runner=runner, http_getter=http_getter
    )

    assert summary.state == setup_wizard.SetupReadinessState.COMPOSE_CONFIG_INVALID
    assert "bad compose" in summary.details


def test_classifies_frontend_not_running(tmp_path: Path, monkeypatch: Any) -> None:
    _write_env(tmp_path / ".env", **_valid_env())
    monkeypatch.setattr(
        setup_wizard,
        "detect_dependency",
        lambda binary, display, custom_path=None: setup_wizard.DepStatus(
            display, True, binary, "ok"
        ),
    )

    def runner(args: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args, 0, "", "")

    def http_getter(url: str, timeout: float) -> tuple[int, str]:
        if "11434" in url:
            return 200, '{"models":[{"name":"llama3.2:latest"}]}'
        if "5173" in url:
            raise ConnectionError("frontend stopped")
        return 200, '{"status":"ok"}'

    summary = setup_wizard.classify_setup_readiness(
        tmp_path, runner=runner, http_getter=http_getter
    )

    assert summary.state == setup_wizard.SetupReadinessState.FRONTEND_NOT_RUNNING


def test_classifies_ready(tmp_path: Path, monkeypatch: Any) -> None:
    _write_env(tmp_path / ".env", **_valid_env())
    monkeypatch.setattr(
        setup_wizard,
        "detect_dependency",
        lambda binary, display, custom_path=None: setup_wizard.DepStatus(
            display, True, binary, "ok"
        ),
    )

    def runner(args: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args, 0, "", "")

    def http_getter(url: str, timeout: float) -> tuple[int, str]:
        if "11434" in url:
            return 200, '{"models":[{"name":"llama3.2:latest"}]}'
        return 200, '{"status":"ok"}'

    summary = setup_wizard.classify_setup_readiness(
        tmp_path, runner=runner, http_getter=http_getter
    )

    assert summary.state == setup_wizard.SetupReadinessState.READY
