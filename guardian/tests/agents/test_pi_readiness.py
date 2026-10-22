from __future__ import annotations

import json
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
) -> dict[str, str]:
    wrapper_path = tmp_path / "codex_runner" / "src" / "agent-wrapper.js"
    package_root = (
        tmp_path / "pi-sdk" / "node_modules" / "@earendil-works" / "pi-coding-agent"
    )
    node_modules = tmp_path / "pi-sdk" / "node_modules"
    if wrapper:
        wrapper_path.parent.mkdir(parents=True)
        wrapper_path.write_text("// fixture\n", encoding="utf-8")
    if sdk:
        (package_root / "dist").mkdir(parents=True)
        (package_root / "dist" / "index.js").write_text(
            "// fixture\n", encoding="utf-8"
        )
        pi_ai_dist = node_modules / "@earendil-works" / "pi-ai" / "dist"
        pi_ai_dist.mkdir(parents=True)
        (pi_ai_dist / "index.js").write_text("// fixture\n", encoding="utf-8")
    return {
        "PATH": os.environ.get("PATH", ""),
        "PI_WRAPPER_PATH": str(wrapper_path),
        "PI_CODING_AGENT_PACKAGE_ROOT": str(package_root),
        "PI_CODING_AGENT_NODE_MODULES": str(node_modules),
    }


def _git_probe(
    *,
    available: bool = True,
    reason: str | None = None,
):
    """A Git probe with a fixed outcome, so no test depends on local Git."""

    def probe(_environment: Mapping[str, str]) -> Mapping[str, object]:
        if available:
            return {"git_available": True}
        return {"git_available": False, "git_reason": reason or "git_missing"}

    return probe


def _probe(
    *,
    initialized: bool = True,
    invocation_scoped: bool = True,
):
    def probe(
        _node: str,
        _wrapper: Path,
        _environment: Mapping[str, str],
    ) -> Mapping[str, object]:
        return {
            "adapter_initialized": initialized,
            "harness_id": "pi-coding-agent",
            "harness_version": "0.82.1",
            "credential_authority": (
                "invocation_scoped" if invocation_scoped else "ambient"
            ),
        }

    return probe


def test_readiness_tokens_are_bounded() -> None:
    assert PI_READINESS_STATES == {"ready", "blocked", "degraded"}
    assert PI_READINESS_REASONS == {
        "node_missing",
        "wrapper_missing",
        "pi_sdk_build_missing",
        "adapter_initialization_failed",
        "git_missing",
        "git_probe_failed",
        "git_probe_timeout",
    }


def test_missing_sdk_build_blocks_before_probe(tmp_path: Path) -> None:
    environment = _fixture_environment(tmp_path, sdk=False)

    def probe_must_not_run(*_args: object) -> Mapping[str, object]:
        pytest.fail("missing runtime files must block before invoking Node")

    report = evaluate_pi_readiness(
        environ=environment,
        adapter_probe=probe_must_not_run,
        git_probe=_git_probe(),
    )

    assert report.status == "blocked"
    assert "pi_sdk_build_missing" in report.reasons
    assert report.can_consume_tasks is False


def test_startup_does_not_require_or_report_ambient_model_and_auth(
    tmp_path: Path,
) -> None:
    environment = _fixture_environment(tmp_path)
    secret = "worker-must-not-read-this-provider-secret"
    environment.update(
        {
            "PI_PROVIDER": "ambient-provider",
            "PI_MODEL": "ambient-model",
            "ANTHROPIC_API_KEY": secret,
            "OPENAI_API_KEY": secret,
        }
    )
    observed: dict[str, str] = {}

    def probe(
        _node: str,
        _wrapper: Path,
        passed_environment: Mapping[str, str],
    ) -> Mapping[str, object]:
        observed.update(passed_environment)
        return _probe()(_node, _wrapper, passed_environment)

    report = evaluate_pi_readiness(
        environ=environment,
        adapter_probe=probe,
        git_probe=_git_probe(),
    )
    rendered = report.to_json() + report.to_human()

    assert report.status == "ready"
    assert report.harness_id == "pi-coding-agent"
    assert report.harness_version == "0.82.1"
    assert "ambient-provider" not in rendered
    assert "ambient-model" not in rendered
    assert secret not in rendered
    assert "PI_PROVIDER" not in observed
    assert "PI_MODEL" not in observed
    assert "ANTHROPIC_API_KEY" not in observed
    assert "OPENAI_API_KEY" not in observed
    assert report.to_dict()["provider_model_authority"] == (
        "invocation_scoped_guardian_binding"
    )


def test_worker_only_reads_pi_runtime_prerequisites(tmp_path: Path) -> None:
    environment = _fixture_environment(tmp_path)
    report = evaluate_pi_readiness(
        environ=environment,
        adapter_probe=_probe(),
        git_probe=_git_probe(),
    )

    assert report.status == "ready"
    assert report.credential_validity == "checked_by_guardian_per_invocation"
    assert {check.name for check in report.checks} == {
        "node_executable",
        "guardian_pi_wrapper",
        "pi_sdk_runtime",
        "git_executable",
        "adapter_initialization",
    }


def test_ambient_credential_authority_is_rejected(
    tmp_path: Path,
) -> None:
    environment = _fixture_environment(tmp_path)
    report = evaluate_pi_readiness(
        environ=environment,
        adapter_probe=_probe(invocation_scoped=False),
        git_probe=_git_probe(),
    )

    assert report.status == "blocked"
    assert report.reasons == ("adapter_initialization_failed",)


def test_adapter_initialization_failure_is_stable_and_secret_free(
    tmp_path: Path,
) -> None:
    environment = _fixture_environment(tmp_path)
    environment["ANTHROPIC_API_KEY"] = "fixture-not-a-real-secret"

    report = evaluate_pi_readiness(
        environ=environment,
        adapter_probe=_probe(initialized=False),
        git_probe=_git_probe(),
    )

    assert report.status == "blocked"
    assert report.reasons == ("adapter_initialization_failed",)
    assert "fixture-not-a-real-secret" not in report.to_json()


def test_node_probe_uses_new_selection_free_mode_and_sanitized_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    environment = _fixture_environment(tmp_path)
    environment.update(
        {
            "PI_PROVIDER": "ambient-provider",
            "PI_MODEL": "ambient-model",
            "ANTHROPIC_API_KEY": "ambient-secret",
        }
    )
    observed: dict[str, object] = {}

    class Completed:
        returncode = 0
        stdout = json.dumps(
            {
                "adapter_initialized": True,
                "harness_id": "pi-coding-agent",
                "harness_version": "0.82.1",
                "credential_authority": "invocation_scoped",
            }
        )

    def fake_run(command: list[str], **kwargs: object) -> Completed:
        observed["command"] = command
        observed["environment"] = kwargs["env"]
        return Completed()

    monkeypatch.setattr(pi_readiness.subprocess, "run", fake_run)
    report = evaluate_pi_readiness(environ=environment)

    assert report.status == "ready"
    assert observed["command"][-1] == "coding-worker-readiness"
    probe_environment = observed["environment"]
    assert isinstance(probe_environment, dict)
    assert "PI_PROVIDER" not in probe_environment
    assert "PI_MODEL" not in probe_environment
    assert "ANTHROPIC_API_KEY" not in probe_environment
    assert "HOME" not in probe_environment


# ---------------------------------------------------------------------------
# Git prerequisite.
#
# Guardian's repository-binding authority and the coding worker's mutation
# enforcement both need an executable Git CLI. A runtime without one cannot
# perform an authorized repository operation, so the worker must refuse to
# consume tasks rather than report ready.
# ---------------------------------------------------------------------------


def test_git_available_keeps_readiness_ready(tmp_path: Path) -> None:
    environment = _fixture_environment(tmp_path)

    report = evaluate_pi_readiness(
        environ=environment,
        adapter_probe=_probe(),
        git_probe=_git_probe(),
    )

    assert report.status == "ready"
    assert report.can_consume_tasks is True
    git_check = next(
        check for check in report.checks if check.name == "git_executable"
    )
    assert git_check.state == "available"
    assert git_check.reason is None


def test_missing_git_blocks_readiness(tmp_path: Path) -> None:
    environment = _fixture_environment(tmp_path)

    report = evaluate_pi_readiness(
        environ=environment,
        adapter_probe=_probe(),
        git_probe=_git_probe(available=False, reason="git_missing"),
    )

    assert report.status == "blocked"
    assert report.reasons == ("git_missing",)
    assert report.can_consume_tasks is False
    git_check = next(
        check for check in report.checks if check.name == "git_executable"
    )
    assert git_check.state == "blocked"
    assert git_check.reason == "git_missing"


def test_unusable_git_blocks_readiness(tmp_path: Path) -> None:
    environment = _fixture_environment(tmp_path)

    report = evaluate_pi_readiness(
        environ=environment,
        adapter_probe=_probe(),
        git_probe=_git_probe(available=False, reason="git_probe_failed"),
    )

    assert report.status == "blocked"
    assert report.reasons == ("git_probe_failed",)
    assert report.can_consume_tasks is False


def test_git_probe_timeout_blocks_readiness(tmp_path: Path) -> None:
    environment = _fixture_environment(tmp_path)

    report = evaluate_pi_readiness(
        environ=environment,
        adapter_probe=_probe(),
        git_probe=_git_probe(available=False, reason="git_probe_timeout"),
    )

    assert report.status == "blocked"
    assert report.reasons == ("git_probe_timeout",)
    assert report.can_consume_tasks is False


def test_git_probe_resolves_through_path_and_runs_only_version(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The probe runs ``git --version`` on a resolved executable, bounded.

    It must not touch a repository, invoke a model, or modify a workspace.
    """
    environment = _fixture_environment(tmp_path)
    environment["PATH"] = "/fixture/bin"
    observed: dict[str, object] = {}

    class Completed:
        returncode = 0
        stdout = "git version 2.47.3\n"
        stderr = ""

    def fake_run(command: list[str], **kwargs: object) -> Completed:
        observed["command"] = command
        observed["timeout"] = kwargs.get("timeout")
        observed["environment"] = kwargs.get("env")
        observed["cwd"] = kwargs.get("cwd")
        return Completed()

    monkeypatch.setattr(
        pi_readiness.shutil,
        "which",
        lambda name, path=None: (
            "/fixture/bin/git" if name == "git" else "/fixture/bin/node"
        ),
    )
    monkeypatch.setattr(pi_readiness.subprocess, "run", fake_run)

    result = pi_readiness._default_git_probe(environment)

    assert result == {"git_available": True}
    assert observed["command"] == ["/fixture/bin/git", "--version"]
    assert observed["timeout"] == pi_readiness.GIT_READINESS_PROBE_TIMEOUT_SECONDS
    assert observed["timeout"] is not None
    # No repository access and no workspace mutation.
    assert observed["cwd"] is None


def test_git_probe_reports_missing_when_path_has_no_git(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    environment = _fixture_environment(tmp_path)

    monkeypatch.setattr(
        pi_readiness.shutil,
        "which",
        lambda name, path=None: None if name == "git" else "/fixture/bin/node",
    )

    result = pi_readiness._default_git_probe(environment)

    assert result == {"git_available": False, "git_reason": "git_missing"}


def test_git_probe_never_receives_provider_or_credential_environment(
    tmp_path: Path,
) -> None:
    """Git availability must not depend on provider, model, or credentials."""
    environment = _fixture_environment(tmp_path)
    environment.update(
        {
            "PI_PROVIDER": "ambient-provider",
            "PI_MODEL": "ambient-model",
            "ANTHROPIC_API_KEY": "ambient-secret",
            "OPENAI_API_KEY": "ambient-secret",
            "DEEPSEEK_API_KEY": "ambient-secret",
        }
    )
    observed: dict[str, object] = {}

    def probe(passed_environment: Mapping[str, str]) -> Mapping[str, object]:
        observed.update(passed_environment)
        return {"git_available": True}

    report = evaluate_pi_readiness(
        environ=environment,
        adapter_probe=_probe(),
        git_probe=probe,
    )

    assert report.status == "ready"
    assert "PI_PROVIDER" not in observed
    assert "PI_MODEL" not in observed
    assert "ANTHROPIC_API_KEY" not in observed
    assert "OPENAI_API_KEY" not in observed
    assert "DEEPSEEK_API_KEY" not in observed
    assert "HOME" not in observed
    rendered = report.to_json() + report.to_human()
    assert "ambient-secret" not in rendered
    assert "ambient-provider" not in rendered
