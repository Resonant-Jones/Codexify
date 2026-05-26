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
        pi_provider: str,
        pi_route: str,
        pi_thinking: str,
        require_backend_receipt: bool,
        debug: bool,
    ) -> dict[str, object]:
        observed["repo_root"] = repo_root
        observed["stage"] = stage
        observed["prompt_text"] = prompt_text
        observed["output_schema"] = output_schema
        observed["output_path"] = output_path
        observed["model"] = model
        observed["pi_provider"] = pi_provider
        observed["pi_route"] = pi_route
        observed["pi_thinking"] = pi_thinking
        observed["require_backend_receipt"] = require_backend_receipt
        observed["debug"] = debug
        return {"backend_provider": "pi"}

    monkeypatch.setattr(runner, "run_pi_exec", fake_pi)

    receipt = runner.run_provider_exec(
        Path("/repo"),
        stage="audit",
        provider="pi",
        prompt_text="prompt",
        output_schema=Path("schema.json"),
        output_path=Path("output.json"),
        model="sonnet",
        pi_provider="anthropic",
        pi_route="default",
        pi_thinking="medium",
        require_backend_receipt=True,
        debug=True,
    )

    assert receipt == {"backend_provider": "pi"}
    assert observed["repo_root"] == Path("/repo")
    assert observed["stage"] == "audit"
    assert observed["prompt_text"] == "prompt"
    assert observed["output_schema"] == Path("schema.json")
    assert observed["output_path"] == Path("output.json")
    assert observed["model"] == "sonnet"
    assert observed["pi_provider"] == "anthropic"
    assert observed["pi_route"] == "default"
    assert observed["pi_thinking"] == "medium"
    assert observed["require_backend_receipt"] is True
    assert observed["debug"] is True


def test_ensure_provider_available_missing_binary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runner, "shutil_which", lambda _binary: None)
    with pytest.raises(runner.RunnerError, match="Node.js"):
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

    def fake_run_cmd(
        args: list[str],
        *,
        cwd: Path,
        capture_output: bool = False,
        debug: bool = False,
        env: dict[str, str] | None = None,
    ):
        observed["args"] = list(args)
        observed["cwd"] = cwd
        observed["env"] = dict(env or {})
        return runner.subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout='{"result":{"status":"success"}}',
            stderr="",
        )

    monkeypatch.setattr(runner, "run_cmd", fake_run_cmd)
    monkeypatch.setattr(
        runner,
        "_pi_backend_version",
        lambda: "0.1.0",
    )

    receipt = runner.run_pi_exec(
        tmp_path,
        stage="task",
        prompt_text="hello",
        output_schema=schema_path,
        output_path=output_path,
        model="sonnet",
        pi_provider="anthropic",
        pi_route="default",
        pi_thinking="medium",
        require_backend_receipt=True,
        debug=False,
    )

    cmd = observed["args"]
    assert isinstance(cmd, list)
    assert cmd[0] == "node"
    assert cmd[2] == "task"
    assert cmd[3] == "hello"
    assert observed["env"]["CAMPAIGN_RUNNER_PROVIDER_ADAPTER"] == "pi"
    assert output_path.exists()
    assert receipt["backend_provider"] == "pi"
    assert receipt["resolved_provider"] == "anthropic"
    assert receipt["resolved_model"] == "sonnet"


def test_sanitize_provider_settings_redacts_sensitive_values() -> None:
    settings = [
        "route=default",
        "api_token=abc123",
        "provider=anthropic",
        "secret_path=/tmp/secret.json",
    ]
    sanitized = runner.sanitize_provider_settings(settings)
    assert sanitized[0] == "route=default"
    assert sanitized[1] == "api_token=<redacted>"
    assert sanitized[2] == "provider=anthropic"
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
        backend_receipts={"audit": {"backend_provider": "pi"}},
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["provider"]["name"] == "pi"
    assert payload["provider"]["models"]["audit"] == "sonnet"
    assert payload["provider"]["settings"] == ["api_token=<redacted>"]
    assert payload["backend_receipts"]["audit"]["backend_provider"] == "pi"
