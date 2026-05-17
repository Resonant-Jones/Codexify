"""Tests for the heartbeat outbox inspector."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "content" / "inspect_heartbeat_outbox.py"

sys.path.insert(0, str(ROOT))
from scripts.content import inspect_heartbeat_outbox as inspect_mod


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def _setup_staged_dir(
    tmp_path: Path, date_str: str, *, review_skipped: bool = False
) -> Path:
    """Create a minimal staged outbox directory with manifest."""
    staged_dir = tmp_path / date_str
    staged_dir.mkdir(parents=True)

    manifest = {
        "schema_version": "heartbeat.outbox.v1",
        "date": date_str,
        "generated_at": f"{date_str}T12:00:00Z",
        "review_required": not review_skipped,
        "review_passed": True,
        "review_status": "passed",
        "review_skipped": review_skipped,
        "source_heartbeat_report": "/tmp/report.md",
        "source_artifacts": ["/tmp/a.md"],
        "generated_files": ["artifact.md", "release-summary.md"],
        "total_files": 2,
        "publication": {"enabled": False, "targets": []},
        "warnings": [],
    }
    (staged_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    (staged_dir / "artifact.md").write_text("artifact", encoding="utf-8")
    (staged_dir / "release-summary.md").write_text(
        "# Summary", encoding="utf-8"
    )

    if review_skipped:
        (staged_dir / "_SKIP_REVIEW_WARNING.txt").write_text(
            "SKIPPED", encoding="utf-8"
        )

    return staged_dir


# ---------------------------------------------------------------------------
# valid outbox passes
# ---------------------------------------------------------------------------


def test_valid_outbox_passes(tmp_path: Path) -> None:
    _setup_staged_dir(tmp_path, "2026-05-14")

    result = _run_cli(
        "--date", "2026-05-14", "--staged-dir", str(tmp_path), "--json"
    )
    d = json.loads(result.stdout)
    assert d["status"] == "passed"
    assert len(d["failures"]) == 0
    assert "artifact.md" in d["artifacts"]


# ---------------------------------------------------------------------------
# missing staged dir fails
# ---------------------------------------------------------------------------


def test_missing_staged_dir_fails(tmp_path: Path) -> None:
    result = _run_cli(
        "--date", "2026-01-01", "--staged-dir", str(tmp_path), "--json"
    )
    d = json.loads(result.stdout)
    assert d["status"] == "failed"
    assert any("no staged outbox" in i.lower() for i in d["failures"])


# ---------------------------------------------------------------------------
# missing manifest warns
# ---------------------------------------------------------------------------


def test_missing_staged_dir_strict_fails(tmp_path: Path) -> None:
    result = _run_cli(
        "--date",
        "2026-01-01",
        "--staged-dir",
        str(tmp_path),
        "--strict",
        "--json",
    )
    d = json.loads(result.stdout)
    assert d["status"] == "failed"


def test_publication_targets_nonempty_fails(tmp_path: Path) -> None:
    staged_dir = _setup_staged_dir(tmp_path, "2026-05-14")
    manifest = json.loads((staged_dir / "manifest.json").read_text())
    manifest["publication"]["targets"] = ["substack"]
    (staged_dir / "manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )

    result = _run_cli(
        "--date", "2026-05-14", "--staged-dir", str(tmp_path), "--json"
    )
    d = json.loads(result.stdout)
    assert d["status"] == "failed"


def test_missing_expected_file_fails(tmp_path: Path) -> None:
    staged_dir = _setup_staged_dir(tmp_path, "2026-05-14")
    manifest = json.loads((staged_dir / "manifest.json").read_text())
    manifest["generated_files"].append("nonexistent.md")
    (staged_dir / "manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )

    result = _run_cli(
        "--date", "2026-05-14", "--staged-dir", str(tmp_path), "--json"
    )
    d = json.loads(result.stdout)
    # Missing file from manifest is a failure
    assert any("missing" in i.lower() for i in d["failures"])


def test_missing_expected_file_strict_fails(tmp_path: Path) -> None:
    staged_dir = _setup_staged_dir(tmp_path, "2026-05-14")
    manifest = json.loads((staged_dir / "manifest.json").read_text())
    manifest["generated_files"].append("nonexistent.md")
    (staged_dir / "manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )

    result = _run_cli(
        "--date",
        "2026-05-14",
        "--staged-dir",
        str(tmp_path),
        "--strict",
        "--json",
    )
    d = json.loads(result.stdout)
    assert d["status"] == "failed"
    d = json.loads(result.stdout)
    assert any("manifest" in i.lower() for i in d["failures"])


def test_invalid_manifest_json_fails(tmp_path: Path) -> None:
    staged_dir = tmp_path / "2026-05-14"
    staged_dir.mkdir(parents=True)
    (staged_dir / "manifest.json").write_text(
        "not valid json {{{{{", encoding="utf-8"
    )

    result = _run_cli(
        "--date", "2026-05-14", "--staged-dir", str(tmp_path), "--json"
    )
    d = json.loads(result.stdout)
    assert any("manifest" in i.lower() for i in d["failures"])


# ---------------------------------------------------------------------------
# schema_version check
# ---------------------------------------------------------------------------


def test_wrong_schema_version_fails(tmp_path: Path) -> None:
    staged_dir = _setup_staged_dir(tmp_path, "2026-05-14")
    manifest = json.loads((staged_dir / "manifest.json").read_text())
    manifest["schema_version"] = "wrong.version"
    (staged_dir / "manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )

    result = _run_cli(
        "--date", "2026-05-14", "--staged-dir", str(tmp_path), "--json"
    )
    d = json.loads(result.stdout)
    assert d["status"] == "failed"
    assert any("schema_version" in i.lower() for i in d["failures"])


# ---------------------------------------------------------------------------
# date mismatch check
# ---------------------------------------------------------------------------


def test_date_mismatch_fails(tmp_path: Path) -> None:
    staged_dir = _setup_staged_dir(tmp_path, "2026-05-14")
    manifest = json.loads((staged_dir / "manifest.json").read_text())
    manifest["date"] = "2026-05-13"
    (staged_dir / "manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )

    result = _run_cli(
        "--date", "2026-05-14", "--staged-dir", str(tmp_path), "--json"
    )
    d = json.loads(result.stdout)
    assert d["status"] == "failed"
    assert any("date" in i.lower() for i in d["failures"])


# ---------------------------------------------------------------------------
# publication checks
# ---------------------------------------------------------------------------


def test_publication_enabled_fails(tmp_path: Path) -> None:
    staged_dir = _setup_staged_dir(tmp_path, "2026-05-14")
    manifest = json.loads((staged_dir / "manifest.json").read_text())
    manifest["publication"]["enabled"] = True
    (staged_dir / "manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )

    result = _run_cli(
        "--date", "2026-05-14", "--staged-dir", str(tmp_path), "--json"
    )
    d = json.loads(result.stdout)
    assert d["status"] == "failed"


# ---------------------------------------------------------------------------
# review_skipped flag
# ---------------------------------------------------------------------------


def test_review_skipped_is_detected(tmp_path: Path) -> None:
    _setup_staged_dir(tmp_path, "2026-05-14", review_skipped=True)

    result = _run_cli(
        "--date", "2026-05-14", "--staged-dir", str(tmp_path), "--json"
    )
    d = json.loads(result.stdout)
    assert d["review_skipped"] is True
    assert any("skip" in w.lower() for w in d.get("warnings", []))


# ---------------------------------------------------------------------------
# JSON output has required keys
# ---------------------------------------------------------------------------


def test_json_output_has_required_keys(tmp_path: Path) -> None:
    _setup_staged_dir(tmp_path, "2026-05-14")

    result = _run_cli(
        "--date", "2026-05-14", "--staged-dir", str(tmp_path), "--json"
    )
    d = json.loads(result.stdout)

    for key in (
        "date",
        "staged_dir",
        "status",
        "manifest",
        "files",
        "drafts",
        "artifacts",
        "warnings",
        "failures",
    ):
        assert key in d, f"Missing key: {key}"


# ---------------------------------------------------------------------------
# default date
# ---------------------------------------------------------------------------


def test_default_date(tmp_path: Path) -> None:
    import datetime

    today = datetime.date.today().isoformat()
    _setup_staged_dir(tmp_path, today)

    result = _run_cli("--staged-dir", str(tmp_path), "--json")
    d = json.loads(result.stdout)
    assert d["status"] == "passed"
