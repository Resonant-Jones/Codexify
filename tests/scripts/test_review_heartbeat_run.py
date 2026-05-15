"""Tests for the heartbeat review script."""

from __future__ import annotations

import datetime
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "content" / "review_heartbeat_run.py"

sys.path.insert(0, str(ROOT))
from scripts.content import review_heartbeat_run as review_mod  # noqa: E402


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def _make_report(
    tmp_path: Path,
    date_str: str,
    *,
    steps: str = "",
    artifacts: str = "",
    extra: str = "",
) -> Path:
    """Write a heartbeat report with the given contents."""
    content = f"""# Heartbeat Orchestrator — {date_str}

**Date:** {date_str}
**Generated:** {date_str}T12:00:00Z

## Repo Status

- **Branch:** `main`
- **Head:** `abc123`
- **Worktree clean:** yes

## Run Summary

| Step | Status | Artifacts | Notes |
|------|--------|-----------|-------|
{steps}

## Generated Artifacts

{artifacts}
{extra}"""
    p = tmp_path / f"{date_str}-heartbeat.md"
    p.write_text(content, encoding="utf-8")
    return p


def _make_artifacts(tmp_path: Path, *names: str) -> dict[str, Path]:
    """Create fake artifact files and return a mapping."""
    result: dict[str, Path] = {}
    for name in names:
        p = tmp_path / name
        p.write_text("x", encoding="utf-8")
        result[name] = p
    return result


# ---------------------------------------------------------------------------
# passing review with valid report and existing artifacts
# ---------------------------------------------------------------------------


def test_valid_report_passes(tmp_path: Path) -> None:
    arts = _make_artifacts(tmp_path, "sentinel.md", "blog.md", "insight.md")
    _make_report(
        tmp_path,
        "2026-05-13",
        steps=f"| Beta Release Sentinel | `passed` | {arts['sentinel.md']} | — |\n| Daily Dev Blog Ingestion | `passed` | {arts['blog.md']} | ok |\n| Resonant Constructs Daily Insight | `passed` | {arts['insight.md']} | ok |",
        artifacts=f"- `{arts['sentinel.md']}`\n- `{arts['blog.md']}`\n- `{arts['insight.md']}`",
    )

    result = _run_cli(
        "--date", "2026-05-13", "--heartbeat-dir", str(tmp_path), "--json"
    )
    d = json.loads(result.stdout)
    assert d["status"] == "passed"
    assert len(d["issues"]) == 0
    assert d["heartbeat_report"] is not None
    assert all(d["checks"].values())


# ---------------------------------------------------------------------------
# missing heartbeat report fails
# ---------------------------------------------------------------------------


def test_missing_report_is_warning(tmp_path: Path) -> None:
    result = _run_cli("--date", "2026-01-01", "--heartbeat-dir", str(tmp_path))
    assert result.returncode != 0
    assert (
        "NOT FOUND" in result.stdout
        or "no heartbeat report" in result.stdout.lower()
    )


def test_missing_report_strict_is_failed(tmp_path: Path) -> None:
    result = _run_cli(
        "--date",
        "2026-01-01",
        "--heartbeat-dir",
        str(tmp_path),
        "--strict",
        "--json",
    )
    d = json.loads(result.stdout)
    assert d["status"] == "failed"
    assert d["heartbeat_report"] is None


# ---------------------------------------------------------------------------
# failed steps detected
# ---------------------------------------------------------------------------


def test_failed_step_is_warning(tmp_path: Path) -> None:
    arts = _make_artifacts(tmp_path, "sentinel.md")
    _make_report(
        tmp_path,
        "2026-05-13",
        steps=f"| Beta Release Sentinel | `failed` | {arts['sentinel.md']} | Exit code 1 |",
        artifacts=f"- `{arts['sentinel.md']}`",
    )

    result = _run_cli(
        "--date", "2026-05-13", "--heartbeat-dir", str(tmp_path), "--json"
    )
    d = json.loads(result.stdout)
    assert d["status"] == "warning"
    assert any("failed" in i.lower() for i in d["issues"])


# ---------------------------------------------------------------------------
# skipped steps: ok without strict, warning/failed with strict
# ---------------------------------------------------------------------------


def test_skipped_step_ok_without_strict(tmp_path: Path) -> None:
    arts = _make_artifacts(tmp_path, "sentinel.md")
    _make_report(
        tmp_path,
        "2026-05-13",
        steps=f"| Beta Release Sentinel | `passed` | {arts['sentinel.md']} | — |\n| Daily Dev Blog Ingestion | `skipped` | — | skipped |",
        artifacts=f"- `{arts['sentinel.md']}`",
    )

    result = _run_cli(
        "--date", "2026-05-13", "--heartbeat-dir", str(tmp_path), "--json"
    )
    d = json.loads(result.stdout)
    assert d["status"] == "passed"


def test_skipped_step_fails_in_strict_mode(tmp_path: Path) -> None:
    arts = _make_artifacts(tmp_path, "sentinel.md")
    _make_report(
        tmp_path,
        "2026-05-13",
        steps=f"| Beta Release Sentinel | `passed` | {arts['sentinel.md']} | — |\n| Daily Dev Blog Ingestion | `skipped` | — | skipped |",
        artifacts=f"- `{arts['sentinel.md']}`",
    )

    result = _run_cli(
        "--date",
        "2026-05-13",
        "--heartbeat-dir",
        str(tmp_path),
        "--strict",
        "--json",
    )
    d = json.loads(result.stdout)
    assert d["status"] == "failed"
    assert any("not passed" in i.lower() for i in d["issues"])


# ---------------------------------------------------------------------------
# title mismatch
# ---------------------------------------------------------------------------


def test_title_date_mismatch_is_warning(tmp_path: Path) -> None:
    arts = _make_artifacts(tmp_path, "sentinel.md")
    _make_report(
        tmp_path,
        "2026-05-13",
        steps=f"| Beta Release Sentinel | `passed` | {arts['sentinel.md']} | — |",
        artifacts=f"- `{arts['sentinel.md']}`",
    )
    # Write report for 2026-05-13 but check with date 2026-05-14
    # To trigger title mismatch, we need to patch the report content
    report_path = tmp_path / "2026-05-14-heartbeat.md"
    content = (tmp_path / "2026-05-13-heartbeat.md").read_text()
    report_path.write_text(content)
    (tmp_path / "2026-05-13-heartbeat.md").unlink()

    result = _run_cli(
        "--date", "2026-05-14", "--heartbeat-dir", str(tmp_path), "--json"
    )
    d = json.loads(result.stdout)
    assert d["status"] == "warning"
    assert any("title" in i.lower() for i in d["issues"])


# ---------------------------------------------------------------------------
# missing artifact
# ---------------------------------------------------------------------------


def test_missing_artifact_is_warning(tmp_path: Path) -> None:
    _make_report(
        tmp_path,
        "2026-05-13",
        steps=f"| Beta Release Sentinel | `passed` | /nonexistent/path.md | — |",
        artifacts=f"- `/nonexistent/path.md`",
    )

    result = _run_cli(
        "--date", "2026-05-13", "--heartbeat-dir", str(tmp_path), "--json"
    )
    d = json.loads(result.stdout)
    assert d["status"] == "warning"
    assert any("not found" in i.lower() for i in d["issues"])
    assert d["checks"]["/nonexistent/path.md"] is False


# ---------------------------------------------------------------------------
# secret-like value detection
# ---------------------------------------------------------------------------


def test_secret_like_value_detected(tmp_path: Path) -> None:
    arts = _make_artifacts(tmp_path, "sentinel.md")
    _make_report(
        tmp_path,
        "2026-05-13",
        steps=f"| Beta Release Sentinel | `passed` | {arts['sentinel.md']} | — |",
        artifacts=f"- `{arts['sentinel.md']}`",
        extra="\n## Failures\n\napi_key=sk-abcdefghijklmnopqrstuvwxyz123456 was found\n",  # gitleaks:allow
    )

    result = _run_cli(
        "--date", "2026-05-13", "--heartbeat-dir", str(tmp_path), "--json"
    )
    d = json.loads(result.stdout)
    assert d["status"] == "warning"
    assert any("secret" in i.lower() for i in d["issues"])


# ---------------------------------------------------------------------------
# JSON output structure
# ---------------------------------------------------------------------------


def test_json_output_has_required_keys(tmp_path: Path) -> None:
    arts = _make_artifacts(tmp_path, "sentinel.md")
    _make_report(
        tmp_path,
        "2026-05-13",
        steps=f"| Beta Release Sentinel | `passed` | {arts['sentinel.md']} | — |",
        artifacts=f"- `{arts['sentinel.md']}`",
    )

    result = _run_cli(
        "--date", "2026-05-13", "--heartbeat-dir", str(tmp_path), "--json"
    )
    d = json.loads(result.stdout)

    assert "date" in d
    assert "heartbeat_report" in d
    assert "status" in d
    assert "checks" in d
    assert "issues" in d
    assert "warnings" in d
    assert "parsed" in d
    assert d["status"] in ("passed", "warning", "failed")


# ---------------------------------------------------------------------------
# default date
# ---------------------------------------------------------------------------


def test_default_date_omits_arg(tmp_path: Path) -> None:
    today = datetime.date.today().isoformat()
    arts = _make_artifacts(tmp_path, "sentinel.md")
    _make_report(
        tmp_path,
        today,
        steps=f"| Beta Release Sentinel | `passed` | {arts['sentinel.md']} | — |",
        artifacts=f"- `{arts['sentinel.md']}`",
    )

    result = _run_cli("--heartbeat-dir", str(tmp_path), "--json")
    d = json.loads(result.stdout)
    assert d["date"] == today


# ---------------------------------------------------------------------------
# invalid date
# ---------------------------------------------------------------------------


def test_invalid_date_fails(tmp_path: Path) -> None:
    result = _run_cli("--date", "not-a-date", "--heartbeat-dir", str(tmp_path))
    assert result.returncode != 0
    assert "invalid date" in result.stderr.lower()
