from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.release import beta_release_sentinel as sentinel


def _write_current_state(path: Path) -> None:
    path.write_text(
        """## Release definition right now
- [x] Supported-profile flags match the local-only beta contract.
- [ ] Coding results return through Guardian into the source thread.
""",
        encoding="utf-8",
    )


def test_status_vocabulary_validation() -> None:
    gates = [sentinel.Gate(name="x", status="proven", evidence="a", notes="n")]
    sentinel.validate_gate_statuses(gates)
    with pytest.raises(ValueError):
        sentinel.validate_gate_statuses(
            [sentinel.Gate(name="x", status="go", evidence="a", notes="n")]
        )


def test_generation_with_clean_audit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    current_state = tmp_path / "00-current-state.md"
    _write_current_state(current_state)
    monkeypatch.setattr(sentinel, "CURRENT_STATE_PATH", current_state)
    monkeypatch.setattr(
        sentinel,
        "run_git",
        lambda args: {
            "branch --show-current": "main\n",
            "rev-parse HEAD": "abc123\n",
            "status --short --untracked-files=all": "",
        }.get(" ".join(args), "feat one\nfeat two\n"),
    )
    monkeypatch.setattr(
        sentinel,
        "run_platform_readiness",
        lambda: ({"summary_counts": {"pass": 1, "warn": 0, "fail": 0}}, None),
    )

    out = tmp_path / "generated"
    changelog = tmp_path / "CHANGELOG.beta.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "beta_release_sentinel.py",
            "--date",
            "2026-05-13",
            "--output-dir",
            str(out),
            "--changelog",
            str(changelog),
        ],
    )
    assert sentinel.main() == 0
    payload = json.loads(
        (out / "2026-05-13-beta-sentinel.json").read_text(encoding="utf-8")
    )
    assert payload["date"] == "2026-05-13"
    assert payload["branch"] == "main"
    assert payload["head"] == "abc123"
    assert "release_gates" in payload
    assert payload["audit_summary"]["summary_counts"]["pass"] == 1


def test_generation_when_audit_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    current_state = tmp_path / "00-current-state.md"
    _write_current_state(current_state)
    monkeypatch.setattr(sentinel, "CURRENT_STATE_PATH", current_state)
    monkeypatch.setattr(
        sentinel,
        "run_git",
        lambda args: {
            "branch --show-current": "main\n",
            "rev-parse HEAD": "abc123\n",
            "status --short --untracked-files=all": "",
        }.get(" ".join(args), "feat one\n"),
    )
    monkeypatch.setattr(
        sentinel,
        "run_platform_readiness",
        lambda: (None, "Platform readiness audit failed with exit code 2."),
    )
    out = tmp_path / "generated"
    changelog = tmp_path / "CHANGELOG.beta.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "beta_release_sentinel.py",
            "--date",
            "2026-05-13",
            "--output-dir",
            str(out),
            "--changelog",
            str(changelog),
        ],
    )
    sentinel.main()
    payload = json.loads(
        (out / "2026-05-13-beta-sentinel.json").read_text(encoding="utf-8")
    )
    assert payload["audit_summary"] is None
    assert any("failed" in w.lower() for w in payload["warnings"])


def test_changelog_append_behavior(tmp_path: Path) -> None:
    changelog = tmp_path / "CHANGELOG.beta.md"
    changelog.write_text("# Beta Changelog\n\nExisting.\n", encoding="utf-8")
    sentinel.update_changelog(
        changelog, "2026-05-13", ["one"], ["blocker"], ["warning"]
    )
    text = changelog.read_text(encoding="utf-8")
    assert "Existing." in text
    assert "## 2026-05-13" in text
    assert "- one" in text


def test_json_shape_and_not_promised(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    current_state = tmp_path / "00-current-state.md"
    _write_current_state(current_state)
    monkeypatch.setattr(sentinel, "CURRENT_STATE_PATH", current_state)
    monkeypatch.setattr(
        sentinel,
        "run_git",
        lambda args: {
            "branch --show-current": "main\n",
            "rev-parse HEAD": "abc123\n",
            "status --short --untracked-files=all": "",
        }.get(" ".join(args), "feat one\n"),
    )
    monkeypatch.setattr(
        sentinel, "run_platform_readiness", lambda: ({"ok": True}, None)
    )
    out = tmp_path / "generated"
    changelog = tmp_path / "CHANGELOG.beta.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "beta_release_sentinel.py",
            "--date",
            "2026-05-13",
            "--output-dir",
            str(out),
            "--changelog",
            str(changelog),
        ],
    )
    sentinel.main()
    payload = json.loads(
        (out / "2026-05-13-beta-sentinel.json").read_text(encoding="utf-8")
    )
    expected = {
        "date",
        "branch",
        "head",
        "worktree_clean",
        "release_gates",
        "blockers",
        "warnings",
        "not_promised",
        "changelog_items",
        "audit_summary",
        "generated_files",
    }
    assert expected.issubset(payload.keys())
    joined = " ".join(payload["not_promised"]).lower()
    assert "cloud-provider beta support" in joined
    assert "desktop" in joined
