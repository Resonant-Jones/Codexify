from __future__ import annotations

import json
from pathlib import Path

import pytest
import runner


def test_run_provider_exec_dispatches_to_codex(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict[str, object] = {}

    def fake_codex(
        repo_root: Path,
        *,
        prompt_text: str,
        output_schema: Path,
        output_path: Path,
        model: str | None,
        configs: list[str],
        debug: bool,
    ) -> None:
        observed["repo_root"] = repo_root
        observed["prompt_text"] = prompt_text
        observed["output_schema"] = output_schema
        observed["output_path"] = output_path
        observed["model"] = model
        observed["configs"] = list(configs)
        observed["debug"] = debug

    monkeypatch.setattr(runner, "run_codex_exec", fake_codex)

    runner.run_provider_exec(
        Path("/repo"),
        provider="codex",
        prompt_text="prompt",
        output_schema=Path("schema.json"),
        output_path=Path("output.json"),
        model="o3",
        settings=["approval_policy=never"],
        debug=True,
    )

    assert observed["repo_root"] == Path("/repo")
    assert observed["prompt_text"] == "prompt"
    assert observed["output_schema"] == Path("schema.json")
    assert observed["output_path"] == Path("output.json")
    assert observed["model"] == "o3"
    assert observed["configs"] == ["approval_policy=never"]
    assert observed["debug"] is True


def test_run_provider_exec_dispatches_to_claude(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict[str, object] = {}

    def fake_claude(
        repo_root: Path,
        *,
        prompt_text: str,
        output_schema: Path,
        output_path: Path,
        model: str | None,
        settings: list[str],
        debug: bool,
    ) -> None:
        observed["repo_root"] = repo_root
        observed["prompt_text"] = prompt_text
        observed["output_schema"] = output_schema
        observed["output_path"] = output_path
        observed["model"] = model
        observed["settings"] = list(settings)
        observed["debug"] = debug

    monkeypatch.setattr(runner, "run_claude_exec", fake_claude)

    runner.run_provider_exec(
        Path("/repo"),
        provider="claude",
        prompt_text="prompt",
        output_schema=Path("schema.json"),
        output_path=Path("output.json"),
        model="sonnet",
        settings=["/tmp/claude-settings.json"],
        debug=False,
    )

    assert observed["repo_root"] == Path("/repo")
    assert observed["prompt_text"] == "prompt"
    assert observed["output_schema"] == Path("schema.json")
    assert observed["output_path"] == Path("output.json")
    assert observed["model"] == "sonnet"
    assert observed["settings"] == ["/tmp/claude-settings.json"]
    assert observed["debug"] is False


def test_ensure_provider_available_missing_binary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runner, "shutil_which", lambda _binary: None)
    with pytest.raises(runner.RunnerError, match="not found on PATH"):
        runner.ensure_provider_available("codex")


def test_ensure_provider_available_unknown_provider() -> None:
    with pytest.raises(runner.RunnerError, match="Unsupported provider"):
        runner.ensure_provider_available("unknown")


def test_provider_model_for_stage() -> None:
    class Args:
        provider = "claude"
        codex_model = ""
        codex_model_audit = ""
        codex_model_compiler = ""
        codex_model_task = ""
        claude_model = "sonnet"
        claude_model_audit = ""
        claude_model_compiler = "compiler-model"
        claude_model_task = ""

    assert runner.provider_model_for_stage(Args, "audit") == "sonnet"
    assert runner.provider_model_for_stage(Args, "compiler") == "compiler-model"


def test_run_claude_exec_builds_expected_command(
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
    ):
        observed["args"] = list(args)
        observed["cwd"] = cwd
        return runner.subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout='{"result":{"status":"success"}}',
            stderr="",
        )

    monkeypatch.setattr(runner, "run_cmd", fake_run_cmd)

    runner.run_claude_exec(
        tmp_path,
        prompt_text="hello",
        output_schema=schema_path,
        output_path=output_path,
        model="sonnet",
        settings=["/tmp/claude-settings.json"],
        debug=False,
    )

    cmd = observed["args"]
    assert isinstance(cmd, list)
    assert cmd[0] == "claude"
    assert "-p" in cmd
    assert "--output-format" in cmd
    assert "json" in cmd
    assert "--json-schema" in cmd
    assert "--settings" in cmd
    assert "/tmp/claude-settings.json" in cmd
    assert "--model" in cmd
    assert "sonnet" in cmd
    assert output_path.exists()


def test_run_codex_exec_strips_allof_schema_for_compatibility(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    schema_path = tmp_path / "schema.json"
    output_path = tmp_path / "out.json"
    schema_path.write_text(
        json.dumps(
            {
                "type": "object",
                "required": ["campaigns"],
                "properties": {
                    "campaigns": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": [
                                "tasks",
                                "discovery_reason",
                            ],
                            "properties": {
                                "tasks": {"type": "array"},
                                "discovery_reason": {"type": "string"},
                            },
                            "allOf": [
                                {
                                    "if": {
                                        "properties": {"tasks": {"maxItems": 0}}
                                    },
                                    "then": {"required": ["discovery_reason"]},
                                }
                            ],
                        },
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    observed: dict[str, object] = {}

    def fake_run_cmd(
        args: list[str],
        *,
        cwd: Path,
        capture_output: bool = False,
        debug: bool = False,
    ):
        observed["args"] = list(args)
        schema_index = args.index("--output-schema") + 1
        schema_arg = Path(args[schema_index])
        observed["schema_arg"] = schema_arg
        observed["schema_payload"] = json.loads(
            schema_arg.read_text(encoding="utf-8")
        )
        return runner.subprocess.CompletedProcess(
            args=args, returncode=0, stdout="", stderr=""
        )

    monkeypatch.setattr(runner, "run_cmd", fake_run_cmd)

    runner.run_codex_exec(
        tmp_path,
        prompt_text="hello",
        output_schema=schema_path,
        output_path=output_path,
        model=None,
        configs=[],
        debug=False,
    )

    schema_payload = observed["schema_payload"]
    assert isinstance(schema_payload, dict)
    items = schema_payload["properties"]["campaigns"]["items"]
    assert "allOf" not in items
    assert observed["schema_arg"] != schema_path


def test_run_codex_exec_rejects_incompatible_response_format_schema(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    schema_path = tmp_path / "schema.json"
    output_path = tmp_path / "out.json"
    schema_path.write_text(
        json.dumps(
            {
                "type": "object",
                "properties": {
                    "campaigns": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "tasks": {"type": "array"},
                                "discovery_reason": {"type": "string"},
                            },
                        },
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    def fake_run_cmd(
        args: list[str],
        *,
        cwd: Path,
        capture_output: bool = False,
        debug: bool = False,
    ):
        raise AssertionError(
            "run_cmd should not be called for incompatible schema"
        )

    monkeypatch.setattr(runner, "run_cmd", fake_run_cmd)

    with pytest.raises(
        runner.RunnerError,
        match="Schema is incompatible with OpenAI response_format",
    ):
        runner.run_codex_exec(
            tmp_path,
            prompt_text="hello",
            output_schema=schema_path,
            output_path=output_path,
            model=None,
            configs=[],
            debug=False,
        )


def test_default_campaign_set_schema_is_response_format_compatible() -> None:
    schema = runner.json_read(runner.DEFAULT_CAMPAIGN_SET_SCHEMA_PATH)
    schema_for_codex, _removed = runner.codex_compat_schema(schema)
    runner.ensure_response_format_schema_compat(schema_for_codex)


def test_run_codex_exec_uses_original_schema_when_compatible(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    schema_path = tmp_path / "schema.json"
    output_path = tmp_path / "out.json"
    schema_path.write_text(
        json.dumps(
            {
                "type": "object",
                "required": ["status"],
                "properties": {"status": {"type": "string"}},
            }
        ),
        encoding="utf-8",
    )

    observed: dict[str, object] = {}

    def fake_run_cmd(
        args: list[str],
        *,
        cwd: Path,
        capture_output: bool = False,
        debug: bool = False,
    ):
        observed["args"] = list(args)
        return runner.subprocess.CompletedProcess(
            args=args, returncode=0, stdout="", stderr=""
        )

    monkeypatch.setattr(runner, "run_cmd", fake_run_cmd)

    runner.run_codex_exec(
        tmp_path,
        prompt_text="hello",
        output_schema=schema_path,
        output_path=output_path,
        model="gpt-5.3-codex",
        configs=["approval_policy=never"],
        debug=False,
    )

    cmd = observed["args"]
    assert isinstance(cmd, list)
    schema_index = cmd.index("--output-schema") + 1
    assert Path(cmd[schema_index]) == schema_path


def test_sanitize_provider_settings_redacts_sensitive_values() -> None:
    settings = [
        "approval_policy=never",
        "api_token=abc123",
        "/tmp/regular-settings.json",
        "secret_path=/tmp/secret.json",
    ]
    sanitized = runner.sanitize_provider_settings(settings)
    assert sanitized[0] == "approval_policy=never"
    assert sanitized[1] == "api_token=<redacted>"
    assert sanitized[2] == "/tmp/regular-settings.json"
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
        cli_args=["--provider", "claude"],
        preflight_clean=True,
        selected_campaign="campaign-1",
        selection_rationale={"rule": "test"},
        termination_reason="dry_run_selected_campaign_materialized",
        provider="claude",
        provider_models={
            "default": "sonnet",
            "audit": "sonnet",
            "compiler": "sonnet",
            "task": "sonnet",
        },
        provider_settings_sanitized=["api_token=<redacted>"],
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["provider"]["name"] == "claude"
    assert payload["provider"]["models"]["audit"] == "sonnet"
    assert payload["provider"]["settings"] == ["api_token=<redacted>"]
