from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LIFECYCLE = ROOT / "scripts/ops/codexify_tester.sh"
INSTALLER = ROOT / "scripts/ops/install_codexify_tester_launchagent.sh"
PLIST = ROOT / "config/launchd/com.resonant.codexify-tester.plist.template"


def test_lifecycle_script_has_explicit_desired_state_commands() -> None:
    text = LIFECYCLE.read_text(encoding="utf-8")

    assert "TESTER_ENABLED_MARKER" in text
    assert "set_desired_up" in text
    assert "clear_desired_up" in text
    assert "command_auto_start" in text
    assert "compose down" in text


def test_intentional_down_clears_marker_before_compose_down() -> None:
    text = LIFECYCLE.read_text(encoding="utf-8")

    clear_index = text.index("clear_desired_up")
    down_index = text.index("compose down", clear_index)
    assert clear_index < down_index


def test_launchagent_is_run_at_load_without_keepalive_loop() -> None:
    text = PLIST.read_text(encoding="utf-8")

    assert "<string>/bin/bash</string>" in text
    assert "__CODEXIFY_TESTER_RUNNER__" in text
    assert "CODEXIFY_TESTER_REPO_ROOT" in text
    assert "<key>RunAtLoad</key>" in text
    assert "<true/>" in text
    assert "<key>KeepAlive</key>" not in text
    assert "<key>WorkingDirectory</key>" in text
    assert "<string>/</string>" in text
    assert "auto-start" in text


def test_installer_uses_user_launchagent_domain() -> None:
    text = INSTALLER.read_text(encoding="utf-8")

    assert "Library/LaunchAgents" in text
    assert 'GUI_DOMAIN="gui/$(id -u)"' in text
    assert "launchctl bootstrap" in text
