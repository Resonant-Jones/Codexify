from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "audit_platform_readiness.py"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def test_json_mode_emits_parseable_json_only() -> None:
    completed = _run("--json")

    assert completed.returncode == 0
    assert completed.stdout.strip().startswith("{")
    assert completed.stdout.strip().endswith("}")
    assert "Codexify Platform Readiness Audit" not in completed.stdout

    payload = json.loads(completed.stdout)
    assert set(payload) >= {
        "mode",
        "repo",
        "summary",
        "domains",
        "warnings",
        "failures",
    }
    assert payload["mode"] == "json"
    assert isinstance(payload["domains"], list)
    assert isinstance(payload["summary"], dict)
    assert "head" in payload["repo"]
    assert "branch" in payload["repo"]


def test_plain_mode_emits_human_readable_report() -> None:
    completed = _run()

    assert completed.returncode == 0
    assert completed.stdout.startswith("Codexify Platform Readiness Audit")
    assert "Final Summary" in completed.stdout
    assert "PASS:" in completed.stdout
    assert "WARN:" in completed.stdout
