from __future__ import annotations

import json
from pathlib import Path

from scripts.release import beta_release_sentinel as sentinel


def _write_file(root: Path, relative_path: str, content: str) -> Path:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_run_platform_readiness_consumes_valid_json(tmp_path, monkeypatch) -> None:
    audit_script = _write_file(
        tmp_path,
        "audit_probe.py",
        """from __future__ import annotations\n\nimport json\n\nprint(json.dumps({\"summary\": {\"overall_status\": \"pass\", \"pass\": 1, \"warn\": 0, \"fail\": 0}, \"warnings\": [], \"failures\": []}))\n""",
    )
    monkeypatch.setattr(sentinel, "AUDIT_SCRIPT_PATH", audit_script)

    payload = sentinel.run_platform_readiness()

    assert payload["summary"]["overall_status"] == "pass"
    gates = sentinel.build_release_gates(
        [{"mark": "x", "label": "Supported profile remains local-only"}],
        payload,
        None,
    )
    assert gates[-1].status == "proven"
    assert gates[-1].evidence == "scripts/audit_platform_readiness.py"


def test_main_writes_beta_artifacts_and_preserves_conservative_claims(
    tmp_path, monkeypatch
) -> None:
    current_state = _write_file(
        tmp_path,
        "docs/architecture/00-current-state.md",
        """## Release definition right now\n- [x] Supported-profile flags match the local-only beta contract.\n- [x] Fresh live evidence exists on the current main tip for the supported path.\n""",
    )
    output_dir = tmp_path / "generated"
    changelog = tmp_path / "CHANGELOG.beta.md"

    monkeypatch.setattr(sentinel, "CURRENT_STATE_PATH", current_state)
    monkeypatch.setattr(
        sentinel,
        "collect_repo_status",
        lambda: {
            "branch": "main",
            "head": "abc123",
            "dirty": False,
            "status_lines": [],
            "status_error": "",
        },
    )
    monkeypatch.setattr(sentinel, "discover_previous_report", lambda *_: None)
    monkeypatch.setattr(
        sentinel, "commit_subjects_since", lambda _previous: ["fix: audit json mode"]
    )
    monkeypatch.setattr(
        sentinel,
        "run_platform_readiness",
        lambda: {
            "mode": "json",
            "repo": {"branch": "main", "head": "abc123"},
            "summary": {
                "pass": 10,
                "warn": 0,
                "fail": 0,
                "overall_status": "pass",
                "strongest_domains": ["Core Loop Integrity"],
                "weakest_domains": ["Governance Readiness"],
            },
            "domains": [],
            "warnings": [],
            "failures": [],
        },
    )

    exit_code = sentinel.main(
        [
            "--date",
            "2026-05-15",
            "--output-dir",
            str(output_dir),
            "--changelog",
            str(changelog),
        ]
    )

    assert exit_code == 0

    json_path = output_dir / "2026-05-15-beta-sentinel.json"
    md_path = output_dir / "2026-05-15-beta-sentinel.md"
    assert json_path.exists()
    assert md_path.exists()
    assert changelog.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["audit"]["summary"]["overall_status"] == "pass"
    assert payload["release_gates"][-1]["status"] == "proven"
    assert payload["generated"]["json"].endswith(
        "2026-05-15-beta-sentinel.json"
    )

    markdown = md_path.read_text(encoding="utf-8")
    assert "Local-first beta hardening." in markdown
    assert "Supported path: local Docker Compose." in markdown
    assert "cloud-provider beta support" in markdown
