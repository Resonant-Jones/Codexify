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
    }


def test_missing_sdk_build_blocks_before_probe(tmp_path: Path) -> None:
    environment = _fixture_environment(tmp_path, sdk=False)

    def probe_must_not_run(*_args: object) -> Mapping[str, object]:
        pytest.fail("missing runtime files must block before invoking Node")

    report = evaluate_pi_readiness(environ=environment, adapter_probe=probe_must_not_run)

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

    report = evaluate_pi_readiness(environ=environment, adapter_probe=probe)
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
    report = evaluate_pi_readiness(environ=environment, adapter_probe=_probe())

    assert report.status == "ready"
    assert report.credential_validity == "checked_by_guardian_per_invocation"
    assert {check.name for check in report.checks} == {
        "node_executable",
        "guardian_pi_wrapper",
        "pi_sdk_runtime",
        "adapter_initialization",
    }


def test_ambient_credential_authority_is_rejected(
    tmp_path: Path,
) -> None:
    environment = _fixture_environment(tmp_path)
    report = evaluate_pi_readiness(
        environ=environment,
        adapter_probe=_probe(invocation_scoped=False),
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
