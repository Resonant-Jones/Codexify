from __future__ import annotations

from pathlib import Path

import pytest

from guardian.ops import setup_wizard


def _make_executable(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    path.chmod(0o755)
    return path


@pytest.mark.parametrize(
    ("binary_name", "display_name"),
    [("docker", "Docker"), ("ollama", "Ollama")],
)
def test_custom_path_wins_over_path_and_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    binary_name: str,
    display_name: str,
) -> None:
    custom_exec = _make_executable(tmp_path / "custom" / binary_name)
    path_exec = _make_executable(tmp_path / "path" / binary_name)
    fallback_exec = _make_executable(tmp_path / "fallback" / binary_name)

    monkeypatch.setenv("PATH", str(path_exec.parent))
    monkeypatch.setattr(
        setup_wizard,
        "_macos_fallback_binary_paths",
        lambda name: (fallback_exec,) if name == binary_name else (),
    )

    status = setup_wizard.detect_dependency(
        binary_name,
        display_name,
        custom_path=str(custom_exec),
    )

    assert status.is_present is True
    assert status.found_path == str(custom_exec.resolve())
    assert status.resolution_source == "custom path"
    assert "Resolved via custom path" in status.help_text


@pytest.mark.parametrize(
    ("binary_name", "display_name"),
    [("docker", "Docker"), ("ollama", "Ollama")],
)
def test_path_discovery_still_works(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    binary_name: str,
    display_name: str,
) -> None:
    path_exec = _make_executable(tmp_path / "path" / binary_name)
    monkeypatch.setenv("PATH", str(path_exec.parent))

    status = setup_wizard.detect_dependency(binary_name, display_name)

    assert status.is_present is True
    assert status.found_path == str(path_exec.resolve())
    assert status.resolution_source == "PATH"
    assert "Resolved via PATH" in status.help_text


def test_macos_fallback_finds_binaries_with_reduced_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docker_exec = _make_executable(tmp_path / "fallback" / "docker")
    ollama_exec = _make_executable(tmp_path / "fallback" / "ollama")

    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    monkeypatch.setattr(setup_wizard.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(setup_wizard.shutil, "which", lambda _: None)
    monkeypatch.setattr(
        setup_wizard,
        "_macos_fallback_binary_paths",
        lambda name: (docker_exec,) if name == "docker" else (ollama_exec,),
    )

    deps = setup_wizard.detect_core_dependencies()

    assert deps["docker"].is_present is True
    assert deps["docker"].found_path == str(docker_exec.resolve())
    assert deps["docker"].resolution_source == "macOS fallback"
    assert "Resolved via macOS fallback" in deps["docker"].help_text

    assert deps["ollama"].is_present is True
    assert deps["ollama"].found_path == str(ollama_exec.resolve())
    assert deps["ollama"].resolution_source == "macOS fallback"
    assert "Resolved via macOS fallback" in deps["ollama"].help_text


def test_missing_binaries_return_truthful_missing_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    monkeypatch.setattr(setup_wizard.shutil, "which", lambda _: None)
    monkeypatch.setattr(
        setup_wizard,
        "_macos_fallback_binary_paths",
        lambda _name: (),
    )

    deps = setup_wizard.detect_core_dependencies()

    assert deps["docker"].is_present is False
    assert deps["docker"].found_path is None
    assert deps["docker"].resolution_source is None
    assert (
        "Not found via PATH or macOS fallback probe" in deps["docker"].help_text
    )

    assert deps["ollama"].is_present is False
    assert deps["ollama"].found_path is None
    assert deps["ollama"].resolution_source is None
    assert (
        "Not found via PATH or macOS fallback probe" in deps["ollama"].help_text
    )
