from __future__ import annotations

import builtins
from pathlib import Path
from types import SimpleNamespace

import pytest
import runner

MINIMAL_ARGS = [
    "--repo-root",
    "/tmp/repo",
    "--audit-prompt-file",
    "/tmp/audit.md",
    "--audit-schema-file",
    "/tmp/audit.schema.json",
    "--compiler-prompt-file",
    "/tmp/compiler.md",
    "--campaign-set-schema-file",
    "/tmp/campaign.schema.json",
    "--task-result-schema-file",
    "/tmp/task.schema.json",
    "--dry-run",
]


def test_resolve_entry_argv_no_args_launches_tui(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict[str, object] = {"initial": None}

    def fake_launch(initial: list[str]) -> list[str]:
        observed["initial"] = initial
        return ["--repo-root", "/repo"]

    monkeypatch.setattr(runner, "launch_tui", fake_launch)
    monkeypatch.setattr(runner, "is_interactive_terminal", lambda: True)

    resolved = runner.resolve_entry_argv([])

    assert observed["initial"] == []
    assert resolved == ["--repo-root", "/repo"]


def test_resolve_entry_argv_with_flags_skips_tui(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called = {"launch": False}

    def fake_launch(_initial: list[str]) -> list[str]:
        called["launch"] = True
        return ["--repo-root", "/repo"]

    monkeypatch.setattr(runner, "launch_tui", fake_launch)

    resolved = runner.resolve_entry_argv(["--repo-root", "/repo"])

    assert resolved == ["--repo-root", "/repo"]
    assert called["launch"] is False


def test_resolve_entry_argv_no_args_non_interactive_skips_tui(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called = {"launch": False}

    def fake_launch(_initial: list[str]) -> list[str]:
        called["launch"] = True
        return ["--repo-root", "/repo"]

    monkeypatch.setattr(runner, "launch_tui", fake_launch)
    monkeypatch.setattr(runner, "is_interactive_terminal", lambda: False)

    resolved = runner.resolve_entry_argv([])

    assert resolved == []
    assert called["launch"] is False


def test_resolve_entry_argv_tui_non_interactive_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runner, "is_interactive_terminal", lambda: False)
    with pytest.raises(
        runner.RunnerError, match="requires an interactive terminal"
    ):
        runner.resolve_entry_argv(["--tui"])


def test_launch_tui_missing_textual_raises_runner_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):  # type: ignore[no-untyped-def]
        if name == "tui_app":
            raise ImportError("No module named textual")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(runner.RunnerError, match="install Textual"):
        runner.launch_tui([])


def test_main_returns_zero_when_tui_cancelled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runner, "resolve_entry_argv", lambda _argv: None)
    assert runner.main([]) == 0


def test_main_uses_resolved_cli_args(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    args = SimpleNamespace(
        provider="codex",
        repo_root=Path("/tmp/repo"),
        debug=False,
        base_ref="HEAD",
        passes=1,
    )

    monkeypatch.setattr(
        runner, "resolve_entry_argv", lambda _argv: MINIMAL_ARGS
    )
    monkeypatch.setattr(runner, "parse_args", lambda _argv: args)
    monkeypatch.setattr(runner, "ensure_repo_root", lambda *_args, **_kw: None)
    monkeypatch.setattr(
        runner,
        "ensure_provider_available",
        lambda _provider: None,
    )
    monkeypatch.setattr(
        runner,
        "git_resolve_ref",
        lambda *_args, **_kw: "deadbeef",
    )

    observed: dict[str, object] = {"cli_args": None}

    def fake_run_pass(
        run_args: SimpleNamespace,
        *,
        pass_index: int,
        base_ref_sha: str,
        cli_args: list[str],
    ) -> None:
        observed["args"] = run_args
        observed["pass_index"] = pass_index
        observed["base_ref_sha"] = base_ref_sha
        observed["cli_args"] = cli_args

    monkeypatch.setattr(runner, "run_pass", fake_run_pass)

    exit_code = runner.main([])

    assert exit_code == 0
    assert observed["pass_index"] == 1
    assert observed["base_ref_sha"] == "deadbeef"
    assert observed["cli_args"] == MINIMAL_ARGS


def test_parse_args_legacy_codex_flags_still_work(tmp_path: Path) -> None:
    audit_prompt = tmp_path / "audit.md"
    audit_schema = tmp_path / "audit.schema.json"
    compiler_prompt = tmp_path / "compiler.md"
    campaign_schema = tmp_path / "campaign.schema.json"
    task_schema = tmp_path / "task.schema.json"
    for path in (
        audit_prompt,
        audit_schema,
        compiler_prompt,
        campaign_schema,
        task_schema,
    ):
        path.write_text("{}", encoding="utf-8")

    args = runner.parse_args(
        [
            "--repo-root",
            str(tmp_path),
            "--audit-prompt-file",
            str(audit_prompt),
            "--audit-schema-file",
            str(audit_schema),
            "--compiler-prompt-file",
            str(compiler_prompt),
            "--campaign-set-schema-file",
            str(campaign_schema),
            "--task-result-schema-file",
            str(task_schema),
            "--codex-model",
            "o3",
            "--codex-config",
            "approval_policy=never",
            "--dry-run",
        ]
    )

    assert args.provider == "codex"
    assert args.codex_model == "o3"
    assert args.codex_config == ["approval_policy=never"]
    assert args.execute is False
    assert args.dry_run is True
