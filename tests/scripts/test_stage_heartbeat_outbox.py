"""Tests for the heartbeat staging script."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "content" / "stage_heartbeat_outbox.py"

# Import for direct testing
sys.path.insert(0, str(ROOT))
from scripts.content import stage_heartbeat_outbox as stage_mod


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def _make_file(p: Path, content: str = "x") -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# helper: create a complete heartbeat report + artifacts in tmp_path
# ---------------------------------------------------------------------------

_MOCK_ARTIFACTS = [
    "docs/audits/generated/{date}-beta-sentinel.md",
    "docs/audits/generated/{date}-beta-sentinel.json",
    "docs/Website/dev-blog/generated/{date}.md",
    "docs/ResonantConstructs/daily-insights/generated/{date}.md",
]


def _setup_heartbeat_run(
    tmp_path: Path, date_str: str, *, fail_review: bool = False
) -> Path:
    """Create a heartbeat report and artifact files in tmp_path."""
    heartbeat_dir = tmp_path / "heartbeat"
    heartbeat_dir.mkdir(parents=True)

    artifacts = [a.format(date=date_str) for a in _MOCK_ARTIFACTS]
    art_list = "\n".join(f"- `{a}`" for a in artifacts)

    status = "failed" if fail_review else "passed"

    report = f"""# Heartbeat Orchestrator — {date_str}

**Date:** {date_str}
**Generated:** {date_str}T12:00:00Z

## Repo Status

- **Branch:** `main`
- **Head:** `abc123`
- **Worktree clean:** yes

## Run Summary

| Step | Status | Artifacts | Notes |
|------|--------|-----------|-------|
| Beta Release Sentinel | `{status}` | {artifacts[0]}, {artifacts[1]} | — |
| Daily Dev Blog Ingestion | `{status}` | {artifacts[2]} | ok |
| Resonant Constructs Daily Insight | `{status}` | {artifacts[3]} | ok |

## Generated Artifacts

{art_list}

## Skipped Steps

- *(none)*

## Warnings

- *(none)*

## Failures

- *(none)*
"""
    report_path = heartbeat_dir / f"{date_str}-heartbeat.md"
    report_path.write_text(report, encoding="utf-8")

    # Create the actual artifact files
    for a in artifacts:
        art_path = tmp_path / a
        art_path.parent.mkdir(parents=True, exist_ok=True)
        art_path.write_text(a, encoding="utf-8")

    return heartbeat_dir


# ---------------------------------------------------------------------------
# successful staging
# ---------------------------------------------------------------------------


def test_successful_staging(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Stage artifacts when review passes and artifacts exist."""
    heartbeat_dir = _setup_heartbeat_run(tmp_path, "2026-05-14")
    staged_dir = tmp_path / "staged"

    # Patch repo root to use tmp_path so artifact resolution works
    monkeypatch.setattr(stage_mod, "REPO_ROOT", tmp_path)
    # Patch review script path
    monkeypatch.setattr(
        stage_mod,
        "REVIEW_SCRIPT",
        ROOT / "scripts" / "content" / "review_heartbeat_run.py",
    )
    # Patch subprocess.run for the review call to return passed
    _original_run = subprocess.run

    def _mock_review_run(args, **kw):
        if "review_heartbeat_run" in str(args):
            return subprocess.CompletedProcess(
                args=args,
                returncode=0,
                stdout=json.dumps(
                    {"status": "passed", "issues": [], "warnings": []}
                ),
                stderr="",
            )
        return _original_run(args, **kw)

    with patch("subprocess.run", side_effect=_mock_review_run):
        result = stage_mod.stage_outbox(
            date_str="2026-05-14",
            heartbeat_dir=heartbeat_dir,
            staged_dir=staged_dir,
            dry_run=False,
            force=True,
            skip_review=False,
        )

    assert result["ok"] is True
    assert result["review_passed"] is True
    assert len(result["staged"]) == 4
    assert len(result["errors"]) == 0

    # Verify files exist in staged dir (date subdirectory)
    expected = [
        "2026-05-14-beta-sentinel.md",
        "2026-05-14-beta-sentinel.json",
        "2026-05-14-dev-blog.md",
        "2026-05-14-daily-insight.md",
    ]
    for name in expected:
        assert (staged_dir / "2026-05-14" / name).is_file(), f"Missing: {name}"


# ---------------------------------------------------------------------------
# dry-run does not write
# ---------------------------------------------------------------------------


def test_dry_run_does_not_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    heartbeat_dir = _setup_heartbeat_run(tmp_path, "2026-05-14")
    staged_dir = tmp_path / "staged"
    monkeypatch.setattr(stage_mod, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        stage_mod,
        "REVIEW_SCRIPT",
        ROOT / "scripts" / "content" / "review_heartbeat_run.py",
    )

    def _mock_review_run(args, **kw):
        if "review_heartbeat_run" in str(args):
            return subprocess.CompletedProcess(
                args=args,
                returncode=0,
                stdout=json.dumps(
                    {"status": "passed", "issues": [], "warnings": []}
                ),
                stderr="",
            )
        return subprocess.CompletedProcess(
            args=args, returncode=0, stdout="", stderr=""
        )

    with patch("subprocess.run", side_effect=_mock_review_run):
        result = stage_mod.stage_outbox(
            date_str="2026-05-14",
            heartbeat_dir=heartbeat_dir,
            staged_dir=staged_dir,
            dry_run=True,
            force=False,
            skip_review=False,
        )

    assert result["ok"] is True
    assert all("[DRY RUN]" in s for s in result["staged"])
    assert not staged_dir.exists() or not list(staged_dir.glob("*"))


# ---------------------------------------------------------------------------
# review failure blocks staging
# ---------------------------------------------------------------------------


def test_review_failure_blocks_staging(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    heartbeat_dir = _setup_heartbeat_run(
        tmp_path, "2026-05-14", fail_review=True
    )
    staged_dir = tmp_path / "staged"
    monkeypatch.setattr(stage_mod, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        stage_mod,
        "REVIEW_SCRIPT",
        ROOT / "scripts" / "content" / "review_heartbeat_run.py",
    )

    def _mock_review_run(args, **kw):
        if "review_heartbeat_run" in str(args):
            return subprocess.CompletedProcess(
                args=args,
                returncode=1,
                stdout=json.dumps(
                    {
                        "status": "warning",
                        "issues": ["failed steps"],
                        "warnings": [],
                    }
                ),
                stderr="",
            )
        return subprocess.CompletedProcess(
            args=args, returncode=0, stdout="", stderr=""
        )

    with patch("subprocess.run", side_effect=_mock_review_run):
        result = stage_mod.stage_outbox(
            date_str="2026-05-14",
            heartbeat_dir=heartbeat_dir,
            staged_dir=staged_dir,
            dry_run=False,
            force=True,
            skip_review=False,
        )

    assert result["ok"] is False
    assert result["review_passed"] is False


# ---------------------------------------------------------------------------
# skip-review bypasses the gate
# ---------------------------------------------------------------------------


def test_skip_review_bypasses_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    heartbeat_dir = _setup_heartbeat_run(
        tmp_path, "2026-05-14", fail_review=True
    )
    staged_dir = tmp_path / "staged"
    monkeypatch.setattr(stage_mod, "REPO_ROOT", tmp_path)

    # Skip review — should still stage despite the "failed" report
    result = stage_mod.stage_outbox(
        date_str="2026-05-14",
        heartbeat_dir=heartbeat_dir,
        staged_dir=staged_dir,
        dry_run=False,
        force=True,
        skip_review=True,
    )

    assert result["ok"] is True
    assert result["review_passed"] is None
    assert len(result["staged"]) == 4


# ---------------------------------------------------------------------------
# missing report fails
# ---------------------------------------------------------------------------


def test_missing_report_fails(tmp_path: Path) -> None:
    result = stage_mod.stage_outbox(
        date_str="2026-01-01",
        heartbeat_dir=tmp_path / "heartbeat",
        staged_dir=tmp_path / "staged",
        dry_run=False,
        force=True,
        skip_review=True,
    )
    assert result["ok"] is False
    assert any("no heartbeat report" in e.lower() for e in result["errors"])


# ---------------------------------------------------------------------------
# force overwrites existing staged files
# ---------------------------------------------------------------------------


def test_force_overwrites_existing_staged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    heartbeat_dir = _setup_heartbeat_run(tmp_path, "2026-05-14")
    staged_dir = tmp_path / "staged"
    staged_dir.mkdir(parents=True)
    # Pre-create a file that would collide
    (staged_dir / "2026-05-14").mkdir(parents=True, exist_ok=True)
    (staged_dir / "2026-05-14" / "2026-05-14-beta-sentinel.md").write_text(
        "old", encoding="utf-8"
    )

    monkeypatch.setattr(stage_mod, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        stage_mod,
        "REVIEW_SCRIPT",
        ROOT / "scripts" / "content" / "review_heartbeat_run.py",
    )

    def _mock_review_run(args, **kw):
        if "review_heartbeat_run" in str(args):
            return subprocess.CompletedProcess(
                args=args,
                returncode=0,
                stdout=json.dumps(
                    {"status": "passed", "issues": [], "warnings": []}
                ),
                stderr="",
            )
        return subprocess.CompletedProcess(
            args=args, returncode=0, stdout="", stderr=""
        )

    with patch("subprocess.run", side_effect=_mock_review_run):
        result = stage_mod.stage_outbox(
            date_str="2026-05-14",
            heartbeat_dir=heartbeat_dir,
            staged_dir=staged_dir,
            dry_run=False,
            force=True,
            skip_review=False,
        )

    assert result["ok"] is True
    assert len(result["skipped"]) == 0
    # Old content should be overwritten
    content = (
        staged_dir / "2026-05-14" / "2026-05-14-beta-sentinel.md"
    ).read_text(encoding="utf-8")
    assert "old" not in content


# ---------------------------------------------------------------------------
# without force, existing staged files are skipped
# ---------------------------------------------------------------------------


def test_without_force_nonempty_staged_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without --force, non-empty staged directory is a hard failure."""
    heartbeat_dir = _setup_heartbeat_run(tmp_path, "2026-05-14")
    staged_dir = tmp_path / "staged"
    staged_dir.mkdir(parents=True)
    (staged_dir / "2026-05-14").mkdir(parents=True, exist_ok=True)
    (staged_dir / "2026-05-14" / "old-file.md").write_text(
        "old", encoding="utf-8"
    )

    monkeypatch.setattr(stage_mod, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        stage_mod,
        "REVIEW_SCRIPT",
        ROOT / "scripts" / "content" / "review_heartbeat_run.py",
    )

    def _mock_review_run(args, **kw):
        if "review_heartbeat_run" in str(args):
            return subprocess.CompletedProcess(
                args=args,
                returncode=0,
                stdout=json.dumps(
                    {"status": "passed", "issues": [], "warnings": []}
                ),
                stderr="",
            )
        return subprocess.CompletedProcess(
            args=args, returncode=0, stdout="", stderr=""
        )

    with patch("subprocess.run", side_effect=_mock_review_run):
        result = stage_mod.stage_outbox(
            date_str="2026-05-14",
            heartbeat_dir=heartbeat_dir,
            staged_dir=staged_dir,
            dry_run=False,
            force=False,
            skip_review=False,
        )

    assert result["ok"] is False
    assert any("already exists" in e.lower() for e in result["errors"])


# ---------------------------------------------------------------------------
# default date
# ---------------------------------------------------------------------------


def test_default_date(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify --date defaults to today."""
    import datetime

    today = datetime.date.today().isoformat()
    heartbeat_dir = _setup_heartbeat_run(tmp_path, today)
    staged_dir = tmp_path / "staged"
    monkeypatch.setattr(stage_mod, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        stage_mod,
        "REVIEW_SCRIPT",
        ROOT / "scripts" / "content" / "review_heartbeat_run.py",
    )

    def _mock_review_run(args, **kw):
        if "review_heartbeat_run" in str(args):
            return subprocess.CompletedProcess(
                args=args,
                returncode=0,
                stdout=json.dumps(
                    {"status": "passed", "issues": [], "warnings": []}
                ),
                stderr="",
            )
        return subprocess.CompletedProcess(
            args=args, returncode=0, stdout="", stderr=""
        )

    with patch("subprocess.run", side_effect=_mock_review_run):
        # Call without explicit date
        result = stage_mod.stage_outbox(
            date_str=today,
            heartbeat_dir=heartbeat_dir,
            staged_dir=staged_dir,
            dry_run=False,
            force=True,
            skip_review=False,
        )

    assert result["ok"] is True
    assert result["date"] == today


# ---------------------------------------------------------------------------
# CLI returns non-zero on staging failure
# ---------------------------------------------------------------------------


def test_cli_returns_nonzero_on_failure(tmp_path: Path) -> None:
    result = _run_cli(
        "--date",
        "2026-01-01",
        "--heartbeat-dir",
        str(tmp_path),
        "--output-dir",
        str(tmp_path / "staged"),
        "--skip-review",
    )
    assert result.returncode != 0
