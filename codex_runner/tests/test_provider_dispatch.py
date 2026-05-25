from __future__ import annotations

import json
from pathlib import Path

import pytest
import runner


def test_run_provider_exec_dispatches_to_pi(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict[str, object] = {}

    def fake_pi(
        repo_root: Path,
        *,
        stage: str,
        prompt_text: str,
        output_schema: Path,
        output_path: Path,
        model: str | None,
        settings: list[str],
        debug: bool,
    ) -> None:
        observed["repo_root"] = repo_root
        observed["stage"] = stage
        observed["prompt_text"] = prompt_text
        observed["output_schema"] = output_schema
        observed["output_path"] = output_path
        observed["model"] = model
        observed["settings"] = list(settings)
        observed["debug"] = debug

    monkeypatch.setattr(runner, "run_pi_exec", fake_pi)

    runner.run_provider_exec(
        Path("/repo"),
        provider="pi",
        stage="audit",
        prompt_text="prompt",
        output_schema=Path("schema.json"),
        output_path=Path("output.json"),
        model="sonnet",
        settings=["pi_provider=anthropic", "pi_thinking=medium"],
        debug=True,
    )

    assert observed["repo_root"] == Path("/repo")
    assert observed["stage"] == "audit"
    assert observed["prompt_text"] == "prompt"
    assert observed["output_schema"] == Path("schema.json")
    assert observed["output_path"] == Path("output.json")
    assert observed["model"] == "sonnet"
    assert observed["settings"] == [
        "pi_provider=anthropic",
        "pi_thinking=medium",
    ]
    assert observed["debug"] is True


def test_run_provider_exec_rejects_legacy_direct_provider() -> None:
    with pytest.raises(
        runner.RunnerError,
        match="Direct Codex/Claude execution is unsupported",
    ):
        runner.run_provider_exec(
            Path("/repo"),
            provider="codex",
            stage="task",
            prompt_text="prompt",
            output_schema=Path("schema.json"),
            output_path=Path("output.json"),
            model=None,
            settings=[],
            debug=False,
        )


def test_ensure_provider_available_missing_node(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    wrapper = tmp_path / "agent-wrapper.js"
    wrapper.write_text("// wrapper", encoding="utf-8")
    monkeypatch.setattr(runner, "PI_WRAPPER_PATH", wrapper)
    monkeypatch.setattr(runner, "shutil_which", lambda _binary: None)
    with pytest.raises(runner.RunnerError, match="requires Node.js"):
        runner.ensure_provider_available("pi")


def test_ensure_provider_available_unknown_provider() -> None:
    with pytest.raises(runner.RunnerError, match="Unsupported provider"):
        runner.ensure_provider_available("unknown")


def test_provider_model_for_stage() -> None:
    class Args:
        provider = "pi"
        pi_model = "sonnet"
        pi_model_audit = ""
        pi_model_compiler = "compiler-model"
        pi_model_task = ""
        pi_provider = "anthropic"
        pi_thinking = "medium"

    assert runner.provider_model_for_stage(Args, "audit") == "sonnet"
    assert runner.provider_model_for_stage(Args, "compiler") == "compiler-model"


def test_run_pi_exec_builds_expected_command(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    schema_path = tmp_path / "schema.json"
    output_path = tmp_path / "out.json"
    schema_path.write_text(
        '{"type":"object","required":["status"],"properties":{"status":{"type":"string"}}}',
        encoding="utf-8",
    )

    observed: dict[str, object] = {}

    def fake_run(
        args: list[str],
        *,
        cwd: str,
        env: dict[str, str],
        text: bool,
        capture_output: bool,
        check: bool,
    ):
        observed["args"] = list(args)
        observed["cwd"] = cwd
        observed["env"] = env
        observed["text"] = text
        observed["capture_output"] = capture_output
        observed["check"] = check
        return runner.subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout='{"status":"success"}',
            stderr="",
        )

    monkeypatch.setattr(runner.subprocess, "run", fake_run)

    runner.run_pi_exec(
        tmp_path,
        stage="task",
        prompt_text="hello",
        output_schema=schema_path,
        output_path=output_path,
        model="sonnet",
        settings=["pi_provider=anthropic", "pi_thinking=high"],
        debug=False,
    )

    cmd = observed["args"]
    assert isinstance(cmd, list)
    assert cmd[0] == "node"
    assert cmd[1] == str(runner.PI_WRAPPER_PATH)
    assert cmd[2] == "task"
    assert cmd[3] == "hello"
    env = observed["env"]
    assert env["PI_MODEL"] == "sonnet"
    assert env["PI_PROVIDER"] == "anthropic"
    assert env["PI_THINKING"] == "high"
    assert output_path.exists()


def test_sanitize_provider_settings_redacts_sensitive_values() -> None:
    settings = [
        "pi_provider=anthropic",
        "api_token=abc123",
        "pi_thinking=medium",
        "secret_path=/tmp/secret.json",
    ]
    sanitized = runner.sanitize_provider_settings(settings)
    assert sanitized[0] == "pi_provider=anthropic"
    assert sanitized[1] == "api_token=<redacted>"
    assert sanitized[2] == "pi_thinking=medium"
    assert sanitized[3] == "secret_path=<redacted>"


def test_write_run_meta_contains_provider_context(tmp_path: Path) -> None:
    output = tmp_path / "run_meta.json"
    prompt = tmp_path / "prompt.md"
    schema = tmp_path / "schema.json"
    compiler = tmp_path / "compiler.md"
    campaign_schema = tmp_path / "campaign.schema.json"
    for path in (prompt, schema, compiler, campaign_schema):
        path.write_text("{}", encoding="utf-8")

    runner.write_run_meta(
        output,
        run_id="abc123",
        audit_id="AUDIT_abc123",
        base_ref_sha="deadbeef",
        hashes=runner.StageHashes(
            audit_prompt_sha256="a",
            audit_schema_sha256="b",
            compiler_prompt_sha256="c",
            campaign_set_schema_sha256="d",
        ),
        audit_prompt_file=prompt,
        audit_schema_file=schema,
        compiler_prompt_file=compiler,
        campaign_set_schema_file=campaign_schema,
        cli_args=["--provider", "pi"],
        preflight_clean=True,
        selected_campaign="campaign-1",
        selection_rationale={"rule": "test"},
        termination_reason="dry_run_selected_campaign_materialized",
        provider="pi",
        provider_models={
            "default": "sonnet",
            "audit": "sonnet",
            "compiler": "sonnet",
            "task": "sonnet",
        },
        provider_settings_sanitized=["api_token=<redacted>"],
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["provider"]["name"] == "pi"
    assert payload["provider"]["models"]["audit"] == "sonnet"
    assert payload["provider"]["settings"] == ["api_token=<redacted>"]
