from __future__ import annotations

from pathlib import Path

import tui_state


def test_profile_round_trip(tmp_path: Path, monkeypatch) -> None:
    profile_path = tmp_path / "settings.toml"
    monkeypatch.setattr(tui_state, "PROFILE_PATH", profile_path)

    settings = tui_state.default_settings(cwd=tmp_path)
    settings.provider = "claude"
    settings.passes = 3
    settings.verify = True
    settings.branch_per_campaign = False
    settings.codex_config = ["approval_policy=never"]
    settings.claude_settings = ["/tmp/claude-settings.json"]

    profile = tui_state.ProfileData(
        settings=settings, presets={"fast": {"passes": 2}}, warnings=[]
    )
    tui_state.save_profile_data(profile)
    loaded = tui_state.load_profile_data(cwd=tmp_path)

    assert loaded.settings.provider == "claude"
    assert loaded.settings.passes == 3
    assert loaded.settings.verify is True
    assert loaded.settings.branch_per_campaign is False
    assert loaded.settings.codex_config == ["approval_policy=never"]
    assert loaded.settings.claude_settings == ["/tmp/claude-settings.json"]
    assert loaded.presets["fast"]["passes"] == 2


def test_unknown_preset_keys_are_ignored(tmp_path: Path, monkeypatch) -> None:
    profile_path = tmp_path / "settings.toml"
    monkeypatch.setattr(tui_state, "PROFILE_PATH", profile_path)
    profile_path.write_text(
        """
provider = "codex"

[presets.fast]
passes = 2
unknown = "value"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    loaded = tui_state.load_profile_data(cwd=tmp_path)
    assert "unknown" not in loaded.presets["fast"]
    assert any("unknown preset key" in warning for warning in loaded.warnings)


def test_to_cli_args_includes_verify_and_branch_flags(tmp_path: Path) -> None:
    settings = tui_state.default_settings(cwd=tmp_path)
    settings.verify = False
    settings.branch_per_campaign = False
    settings.execute_mode = "dry-run"
    settings.provider = "claude"

    args = tui_state.to_cli_args(settings)

    assert "--provider" in args
    assert "claude" in args
    assert "--no-verify" in args
    assert "--no-branch-per-campaign" in args
    assert "--dry-run" in args


def test_to_cli_args_execute_mode(tmp_path: Path) -> None:
    settings = tui_state.default_settings(cwd=tmp_path)
    settings.execute_mode = "execute"

    args = tui_state.to_cli_args(settings)

    assert "--execute" in args
    assert "--dry-run" not in args
