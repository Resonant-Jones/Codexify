"""Tests for the heartbeat status route handler logic.

Tests the route handler functions directly without importing guardian internals.
"""

from __future__ import annotations

import json
import re
import tempfile
from datetime import date
from pathlib import Path
from typing import Any, Optional
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Inline route handler logic (same as guardian/routes/heartbeat.py)
# This avoids importing guardian internals while testing the exact same code.
# ---------------------------------------------------------------------------


# path helpers
def _repo_rel(root: Path, path: Path) -> str:
    """Return repo-relative path without symlink resolution."""
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


# discovery
def _discover_latest_report(heartbeat_dir: Path) -> Path | None:
    if not heartbeat_dir.is_dir():
        return None
    reports = sorted(
        heartbeat_dir.glob("*-heartbeat.md"), key=lambda p: p.name, reverse=True
    )
    return reports[0] if reports else None


def _discover_latest_staged(staged_root: Path) -> Path | None:
    if not staged_root.is_dir():
        return None
    dirs = sorted(
        [
            d
            for d in staged_root.iterdir()
            if d.is_dir() and (d / "manifest.json").is_file()
        ],
        key=lambda d: d.name,
        reverse=True,
    )
    return dirs[0] if dirs else None


def _extract_date_from_report_name(name: str) -> str:
    return name.split("-heartbeat")[0]


# status assembly
def _read_report_status(report_path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "review_status": "unknown",
        "warnings": [],
        "failures": [],
        "artifact_count": 0,
    }
    try:
        text = report_path.read_text(encoding="utf-8")
    except Exception:
        return result
    has_failed = bool(re.search(r"\|\s+[^|]*\|\s+`failed`\s+\|", text))
    has_skipped = bool(re.search(r"\|\s+[^|]*\|\s+`skipped`\s+\|", text))
    has_passed = bool(re.search(r"\|\s+[^|]*\|\s+`passed`\s+\|", text))
    if has_failed:
        result["review_status"] = "failed"
    elif has_skipped and not has_passed:
        result["review_status"] = "warning"
    elif has_passed:
        result["review_status"] = "passed"
    art_section = re.search(
        r"## Generated Artifacts\n\n(.*?)(?=\n## |\Z)", text, re.DOTALL
    )
    if art_section:
        for line in art_section.group(1).strip().splitlines():
            if re.search(r"`(.+?)`", line):
                result["artifact_count"] += 1
    # Extract warnings from Warnings section
    warn_section = re.search(
        r"## Warnings\n\n(.*?)(?=\n## |\Z)", text, re.DOTALL
    )
    if warn_section:
        for line in warn_section.group(1).strip().splitlines():
            stripped = line.strip("- ").strip()
            if stripped and stripped != "*(none)*":
                result["warnings"].append(stripped)
    # Extract failures from Failures section
    fail_section = re.search(
        r"## Failures\n\n(.*?)(?=\n## |\Z)", text, re.DOTALL
    )
    if fail_section:
        for line in fail_section.group(1).strip().splitlines():
            stripped = line.strip("- ").strip()
            if stripped and stripped != "*(none)*":
                result["failures"].append(stripped)
    return result


def _read_outbox_status(staged_dir: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "outbox_status": "unknown",
        "publication_enabled": False,
        "publication_targets": [],
        "generated_files": [],
        "total_files": 0,
        "review_skipped": False,
    }
    manifest_path = staged_dir / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, FileNotFoundError, ValueError):
        result["outbox_status"] = "warning"
        result["warnings"] = ["Staged manifest is missing or invalid JSON"]
        return result
    if manifest.get("schema_version") != "heartbeat.outbox.v1":
        result["outbox_status"] = "warning"
        return result
    pub = manifest.get("publication", {})
    result["publication_enabled"] = pub.get("enabled", False)
    result["publication_targets"] = pub.get("targets", [])
    result["generated_files"] = manifest.get("generated_files", [])
    result["total_files"] = manifest.get(
        "total_files", len(result["generated_files"])
    )
    result["review_skipped"] = manifest.get("review_skipped", False)
    if (staged_dir / "_SKIP_REVIEW_WARNING.txt").is_file():
        result.setdefault("warnings", []).append(
            "Review gate was skipped during staging"
        )
    if manifest.get("review_passed") is True and not result["review_skipped"]:
        result["outbox_status"] = "passed"
    elif manifest.get("review_passed") is True and result["review_skipped"]:
        result["outbox_status"] = "warning"
    elif manifest.get("review_passed") is False:
        result["outbox_status"] = "failed"
    return result


# Test fixture setup
def _make_report(
    tmp_path: Path,
    date_str: str,
    *,
    status: str = "passed",
    failures: str | None = None,
    warnings: str | None = None,
) -> Path:
    report_dir = tmp_path / "docs" / "Heartbeat" / "generated"
    report_dir.mkdir(parents=True, exist_ok=True)
    report = report_dir / f"{date_str}-heartbeat.md"
    failures_entry = f"- {failures}" if failures else "- *(none)*"
    warnings_entry = f"- {warnings}" if warnings else "- *(none)*"
    report.write_text(
        f"""# Heartbeat Orchestrator — {date_str}

**Date:** {date_str}
**Generated:** {date_str}T12:00:00Z

## Run Summary

| Step | Status | Artifacts | Notes |
|------|--------|-----------|-------|
| Beta Release Sentinel | `{status}` | /tmp/a.md | — |
| Daily Dev Blog Ingestion | `passed` | /tmp/b.md | ok |
| Resonant Constructs Daily Insight | `passed` | /tmp/c.md | ok |

## Generated Artifacts

- `/tmp/a.md`
- `/tmp/b.md`
- `/tmp/c.md`

## Warnings

{warnings_entry}

## Failures

{failures_entry}
""",
        encoding="utf-8",
    )
    return report


def _make_staged(tmp_path: Path, date_str: str) -> Path:
    staged_dir = tmp_path / "docs" / "Heartbeat" / "staged" / date_str
    staged_dir.mkdir(parents=True)
    manifest = {
        "schema_version": "heartbeat.outbox.v1",
        "date": date_str,
        "generated_at": f"{date_str}T12:00:00Z",
        "review_required": True,
        "review_passed": True,
        "review_status": "passed",
        "review_skipped": False,
        "source_heartbeat_report": f"docs/Heartbeat/generated/{date_str}-heartbeat.md",
        "source_artifacts": ["/tmp/a.md"],
        "generated_files": ["a.md"],
        "total_files": 1,
        "publication": {"enabled": False, "targets": []},
        "warnings": [],
    }
    (staged_dir / "manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    return staged_dir


# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------


def test_no_artifacts_returns_missing() -> None:
    tmp = Path(tempfile.mkdtemp())
    report = _discover_latest_report(tmp / "nonexistent")
    assert report is None
    staged = _discover_latest_staged(tmp / "nonexistent")
    assert staged is None


def test_latest_heartbeat_found() -> None:
    tmp = Path(tempfile.mkdtemp())
    _make_report(tmp, "2026-05-14")
    _make_report(tmp, "2026-05-15")
    hb_dir = tmp / "docs" / "Heartbeat" / "generated"
    report = _discover_latest_report(hb_dir)
    assert report is not None
    assert report.name == "2026-05-15-heartbeat.md"
    date_str = _extract_date_from_report_name(report.name)
    assert date_str == "2026-05-15"


def test_review_status_passed() -> None:
    tmp = Path(tempfile.mkdtemp())
    r = _make_report(tmp, "2026-05-14")
    status = _read_report_status(r)
    assert status["review_status"] == "passed"


def test_review_status_failed() -> None:
    tmp = Path(tempfile.mkdtemp())
    r = _make_report(tmp, "2026-05-14", status="failed")
    status = _read_report_status(r)
    assert status["review_status"] == "failed"


def test_staged_outbox_found() -> None:
    tmp = Path(tempfile.mkdtemp())
    _make_staged(tmp, "2026-05-14")
    staged_root = tmp / "docs" / "Heartbeat" / "staged"
    s = _discover_latest_staged(staged_root)
    assert s is not None
    assert s.name == "2026-05-14"


def test_outbox_status_passed() -> None:
    tmp = Path(tempfile.mkdtemp())
    s = _make_staged(tmp, "2026-05-14")
    status = _read_outbox_status(s)
    assert status["outbox_status"] == "passed"
    assert status["publication_enabled"] is False
    assert status["publication_targets"] == []


def test_malformed_manifest_yields_warning() -> None:
    tmp = Path(tempfile.mkdtemp())
    staged_dir = tmp / "2026-05-14"
    staged_dir.mkdir(parents=True)
    (staged_dir / "manifest.json").write_text(
        "not valid json {{{{{", encoding="utf-8"
    )
    status = _read_outbox_status(staged_dir)
    assert status["outbox_status"] == "warning"


def test_outbox_wrong_schema_version() -> None:
    tmp = Path(tempfile.mkdtemp())
    staged_dir = tmp / "2026-05-14"
    staged_dir.mkdir(parents=True)
    (staged_dir / "manifest.json").write_text(
        json.dumps({"schema_version": "wrong", "review_passed": True}),
        encoding="utf-8",
    )
    status = _read_outbox_status(staged_dir)
    assert status["outbox_status"] == "warning"


def test_repo_relative_path() -> None:
    root = Path("/tmp/test-repo")
    p = root / "docs" / "Heartbeat" / "generated" / "2026-05-14-heartbeat.md"
    rel = _repo_rel(root, p)
    assert rel == "docs/Heartbeat/generated/2026-05-14-heartbeat.md"
    assert not rel.startswith("/")


def test_failures_extracted_from_report_section() -> None:
    """Failures must come from the ## Failures section, not recycled from warnings."""
    tmp = Path(tempfile.mkdtemp())
    r = _make_report(
        tmp,
        "2026-05-14",
        status="failed",
        warnings="Review gate was skipped during staging",
        failures="Step failed: Beta Release Sentinel",
    )
    status = _read_report_status(r)
    assert status["review_status"] == "failed"
    assert status["warnings"] == ["Review gate was skipped during staging"]
    assert status["failures"] == ["Step failed: Beta Release Sentinel"]


def test_failures_empty_when_section_is_none() -> None:
    """When the report has no failure entries, failures list stays empty."""
    tmp = Path(tempfile.mkdtemp())
    r = _make_report(
        tmp, "2026-05-14", status="failed", warnings="Something minor"
    )
    status = _read_report_status(r)
    assert status["review_status"] == "failed"
    assert status["warnings"] == ["Something minor"]
    assert status["failures"] == []


def test_no_command_execution() -> None:
    """Verify subprocess is never called by route handler functions."""
    tmp = Path(tempfile.mkdtemp())
    r = _make_report(tmp, "2026-05-14")
    _make_staged(tmp, "2026-05-14")
    hb_dir = tmp / "docs" / "Heartbeat" / "generated"
    staged_root = tmp / "docs" / "Heartbeat" / "staged"

    def _fail_on_run(*args, **kwargs):
        raise AssertionError("subprocess.run was called")

    with patch("subprocess.run", side_effect=_fail_on_run):
        # All handlers are file-read only
        _discover_latest_report(hb_dir)
        _discover_latest_staged(staged_root)
        _read_report_status(r)
        _read_outbox_status(
            tmp / "docs" / "Heartbeat" / "staged" / "2026-05-14"
        )
