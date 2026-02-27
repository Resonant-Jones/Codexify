from __future__ import annotations

import asyncio
from pathlib import Path

from textual.widgets import Input, Static
from tui_app import CampaignRunnerTUI
from tui_state import RunnerSettings


def test_tui_has_command_binding() -> None:
    keys = [binding.key for binding in CampaignRunnerTUI.BINDINGS]
    assert "/" in keys


def test_slash_focuses_command_input() -> None:
    async def run_check() -> None:
        app = CampaignRunnerTUI()
        async with app.run_test() as pilot:
            await pilot.press("/")
            await pilot.pause()
            command_input = app.query_one("#command-input", Input)
            assert command_input.has_focus

    asyncio.run(run_check())


def test_staged_changes_and_apply() -> None:
    app = CampaignRunnerTUI()
    app.staged_settings = RunnerSettings()
    app.active_settings = RunnerSettings()
    app._execute_command("/set provider claude", instant=False)
    assert app.staged_settings.provider == "claude"
    assert app.active_settings.provider == "codex"


def test_run_blocked_when_staged_exists() -> None:
    app = CampaignRunnerTUI()
    app.active_settings = RunnerSettings()
    app.staged_settings = RunnerSettings()
    app.staged_settings.provider = "claude"
    app.has_staged_changes = True
    app._try_run(strict=True, instant=False)
    assert app._pending_run_args is None


def test_validate_settings_blocks_missing_repo() -> None:
    app = CampaignRunnerTUI()
    settings = RunnerSettings(
        provider="codex",
        repo_root="/tmp/does-not-exist-runner",
        audit_prompt_file="/tmp/missing-audit.md",
        audit_schema_file="/tmp/missing-audit.schema.json",
        compiler_prompt_file="/tmp/missing-compiler.md",
        campaign_set_schema_file="/tmp/missing-campaign.schema.json",
        task_result_schema_file="/tmp/missing-task.schema.json",
    )
    errors = app._validate_settings(settings)
    assert any("Repo root does not exist" in error for error in errors)


def test_validate_settings_accepts_valid_repo_and_paths(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir(parents=True, exist_ok=True)
    for name in (
        "audit.md",
        "audit.schema.json",
        "compiler.md",
        "campaign.schema.json",
        "task.schema.json",
    ):
        (tmp_path / name).write_text("{}", encoding="utf-8")

    app = CampaignRunnerTUI()

    def fake_validate_git(*_args, **_kwargs):
        class Result:
            returncode = 0
            stdout = str(tmp_path)

        return Result()

    import tui_app as _tui_app

    original = _tui_app.subprocess.run
    _tui_app.subprocess.run = fake_validate_git  # type: ignore[assignment]
    try:
        settings = RunnerSettings(
            provider="claude",
            repo_root=str(tmp_path),
            audit_prompt_file=str(tmp_path / "audit.md"),
            audit_schema_file=str(tmp_path / "audit.schema.json"),
            compiler_prompt_file=str(tmp_path / "compiler.md"),
            campaign_set_schema_file=str(tmp_path / "campaign.schema.json"),
            task_result_schema_file=str(tmp_path / "task.schema.json"),
            passes=1,
        )
        errors = app._validate_settings(settings)
        assert errors == []
    finally:
        _tui_app.subprocess.run = original  # type: ignore[assignment]


def test_command_submission_updates_suggestions() -> None:
    async def run_check() -> None:
        app = CampaignRunnerTUI()
        async with app.run_test() as pilot:
            command_input = app.query_one("#command-input", Input)
            command_input.value = "/set pro"
            await pilot.pause()
            suggestions = app.query_one("#suggestions", Static).renderable
            assert "provider" in str(suggestions)

    asyncio.run(run_check())


def test_instant_run_auto_applies_staged_and_exits() -> None:
    app = CampaignRunnerTUI()
    app.active_settings = RunnerSettings()
    app.staged_settings = RunnerSettings(provider="claude")
    app.has_staged_changes = True

    captured: dict[str, object] = {}

    def fake_exit(value):  # type: ignore[no-untyped-def]
        captured["value"] = value

    app.exit = fake_exit  # type: ignore[assignment]
    app._try_run(strict=False, instant=True)

    assert app.active_settings.provider == "claude"
    assert isinstance(captured.get("value"), list)


def test_strict_run_blocks_validation_errors() -> None:
    app = CampaignRunnerTUI()
    app.active_settings = RunnerSettings(repo_root="/tmp/missing-repo")
    app.staged_settings = RunnerSettings(repo_root="/tmp/missing-repo")
    app.has_staged_changes = False

    shown: dict[str, object] = {}

    def fake_show(errors: list[str]) -> None:
        shown["errors"] = errors

    app._show_validation_errors = fake_show  # type: ignore[assignment]
    app._try_run(strict=True, instant=False)
    assert "errors" in shown


def test_instant_run_binding_exists() -> None:
    keys = [binding.key for binding in CampaignRunnerTUI.BINDINGS]
    assert "meta+enter" in keys
    assert "ctrl+enter" in keys
